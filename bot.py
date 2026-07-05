import os
import discord
from discord.ext import commands
from discord.ext import tasks
import markovify
import asyncio
import random
import logging
import random
import time
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

user_flags = {}

bot_token = os.getenv("BOT_KEY")
assert bot_token is not None, "Token not found in .env"

def store_message(message): # stores messages from chats
    print(f"storing: {message[:50]}")
    with open("messages.txt", 'a', encoding='utf-8') as f:
        f.write(f"{message}\n")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='&', intents=intents)

def get_line_count(): # get the current global message count, equal to the amount of lines in messages.txt
    if not os.path.exists('messages.txt'):
        return 0
    with open('messages.txt', encoding='utf-8') as f:
        return sum(1 for _ in f)

globalMsg = get_line_count()

@bot.command()
async def scrape(ctx, amount : int = 1000):
    if ctx.author.id != 548578270808113173: # prevent anyone except me from executing
        await ctx.send('not authorized')
        return

    global globalMsg
    progMsg =  await ctx.send("scraping... [░░░░░░░░░░░░░░░░░░░░] 0%")
    msgCount = 0
    update_every = max(1, amount // 20)

    async for msg in ctx.channel.history(limit=amount):
        print(f"checking: {msg.content[:30]!r}, author bot: {msg.author.bot}")
        if not msg.author.bot and not msg.content.startswith('&'):
            store_message(msg.content)   
            msgCount += 1
            globalMsg += 1

            if msgCount % update_every == 0 or msgCount == amount:
                percent = int((msgCount / amount) * 100)
                filled = int(percent / 5 )
                bar = "█" * filled + "░" * (20 - filled)
                await progMsg.edit(content=f"scraping... [{bar}] {percent}%")
    
    await progMsg.edit(content=f"{msgCount} messages scraped! current total: {globalMsg}")
    
@bot.command()
async def token(ctx): # i don't even know why i made this
    await ctx.send(f"OPSEC LEVEL: SIGMA DEMON. NO TOKEN FOR U BLUD")
    await ctx.author.timeout(timedelta(minutes=1)) 

@bot.command()
async def total(ctx):
    global globalMsg
    await ctx.send(f"my current message count is {globalMsg}")

@bot.command()
@commands.cooldown(1, 240, commands.BucketType.default) # 4 minute cooldown
async def markov(ctx):
    global text_model
    sentence = text_model.make_sentence(tries=100)
    print(repr(sentence))
    if sentence:
        await ctx.send(sentence)

last_reply_time = 0
REPLY_CD = 5

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    global text_model, last_reply_time

    if message.reference and message.reference.resolved: # is the message a reply to something?
        replied_to = message.reference.resolved 
        if bot.user and replied_to.author.id == bot.user.id: # is the reply directed towards the bot?
            now = time.time()
            if now - last_reply_time >= REPLY_CD: # checks whether the last replying message is more than REPLY_CD seconds ago
                sentence = text_model.make_short_sentence(80, tries=100)
                if sentence:
                    await message.reply(sentence)
                    last_reply_time = now

    global globalMsg
    if message.content:
        store_message(message.content)
        globalMsg += 1
        
    if random.random() < 0.02: # 2% chance
        sentence = text_model.make_short_sentence(140, tries=100)
        print(repr(sentence))
        if sentence:
            await message.channel.send(sentence)

    if random.random() < 0.005: # .5% chance
        try:
            roll = random.random()
            if roll < .05: # 5% chance
                await message.author.timeout(timedelta(minutes=3))
                await message.channel.send(f'{message.author.mention} stepped on a super landmine! 💥 timed out for 3m')
                return

            elif roll < .20: # 15% chance
                await message.author.timeout(timedelta(minutes=1))
                await message.channel.send(f'{message.author.mention} stepped on a nuke!! ☢️💥 5 people are timed out for 1m')

                messages = []
                async for msg in message.channel.history(limit=5):
                    if msg.author.id != message.author.id or msg.author.id != message.guild.me:
                        messages.append(msg)

                for msg in reversed(messages):
                    if msg.author.id == message.author.id: # skip the user that triggered this, cause they're already muted from earlier
                        continue
                    try:
                        await msg.author.timeout(timedelta(minutes=1))
                        await message.channel.send(f'{msg.author.mention} is poisoned by fallout! ☢️')
                    except discord.Forbidden:
                        await message.channel.send(f'{msg.author.mention} is immune to fallout! ☢️') # fall back if no perms to timeout
                return

            else: # 80% chance
                await message.author.timeout(timedelta(minutes=1))
                await message.channel.send(f'{message.author.mention} stepped on a landmine! 💥 timed out for 1m')
        except discord.Forbidden:
            await message.channel.send(f'{message.author.mention} stepped on a land mine 💥, but is immune!') # fall back if no perms to timeout

    if user_flags.get(message.author.id, {}).get("planted", 0) > 0: # checks if they have the planted flag
        bombs_planted = user_flags[message.author.id]["planted"]
        setters = user_flags[message.author.id]["set_by"]

        timeout_time = 60
    
        if bombs_planted > 1: 
            setter_mentions = ", ".join(f'<@{sid}>' for sid in setters) # gets all the IDs of the planters
            timeout_time = timeout_time * bombs_planted * 1.2 # 60 * 2(minimum) * 1.2
            await message.author.timeout(timedelta(seconds=timeout_time))
            await message.channel.send(f'{message.author.mention} had {bombs_planted} bombs go off!! 💥 they are timed out for {int(timeout_time)}s. the bombs were planted by {setter_mentions}')
        
        else:
            await message.author.timeout(timedelta(seconds=timeout_time))
            await message.channel.send(f'{message.author.mention} has been bombed! 💥 they are timed out for 1m. the bomb was planted by <@{setters[0]}>')
        
        del user_flags[message.author.id] # remove ID after execution

    await bot.process_commands(message) 

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"command on cooldown! try in {error.retry_after:.1f}s")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('couldn\'t find that member, recheck the ID or mention')
        ctx.command.reset_cooldown(ctx)
    elif isinstance(error, commands.MissingRequiredArgument):
        ctx.command.reset_cooldown(ctx)
        await ctx.send('you must input all fields in the command.')
    else:
        print(f"Unhandled error: {error}")
        raise error

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    rebuild.start()

@bot.command()
async def hello(ctx):
      await ctx.channel.send('Hello!')
      
@bot.command()
@commands.cooldown(1, 5400, commands.BucketType.user) # 1.5 hour cooldown
async def plant(ctx, user: discord.Member):
    bot_member = ctx.guild.me # get object data of the bot

    if user.top_role >= bot_member.top_role: # prevent planting if the user has a higher role than the bot, failsafe
        await ctx.author.timeout(timedelta(minutes=1))
        await ctx.send(f'{ctx.author.mention} tried planting a bomb on {user.mention}, but it backfired! 💥 timed out for 1 minute') # lol
        return

    if user.id not in user_flags:
        user_flags[user.id] = {"planted": 0, "set_by": []}

    user_flags[user.id]["planted"] += 1
    user_flags[user.id]["set_by"].append(ctx.author.id)

    await ctx.send(f'bomb planted on {user}. they currently have {user_flags[user.id]["planted"]} bomb(s)')

@tasks.loop(minutes=5) # task loop that refreshes markov model every 5 minutes
async def rebuild():
    global text_model
    with open("messages.txt", encoding="utf-8") as f:
        text = f.read()
        text_model = markovify.Text(text)

bot.run(bot_token, log_handler=handler)
