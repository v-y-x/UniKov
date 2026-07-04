import os
import discord
from discord.ext import commands
from discord.ext import tasks
import markovify
import logging
import random
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

bot_token = os.getenv("BOT_KEY")
assert bot_token is not None, "Token not found in .env"

def store_message(message):
    print(f"storing: {message[:50]}")
    with open("messages.txt", 'a', encoding='utf-8') as f:
        f.write(f"{message}\n")

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='&', intents=intents)
globalMsg = 57300

@bot.command()
async def scrape(ctx, amount : int = 1000):
    if ctx.author.id != 548578270808113173:
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
async def token(ctx):
    await ctx.send(f"OPSEC LEVEL: SIGMA DEMON. NO TOKEN FOR U BLUD")
    await ctx.author.timeout(timedelta(minutes=1))

@bot.command()
async def total(ctx):
    global globalMsg
    await ctx.send(f"my current message count is {globalMsg}")

@bot.command()
@commands.cooldown(1, 180, commands.BucketType.default)
async def markov(ctx):
    sentence = text_model.make_sentence(tries=100)
    print(repr(sentence))
    if sentence:
        await ctx.send(sentence)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.reference and message.reference.resolved: # is the message a reply to something?
        replied_to = message.reference.resolved 

        if bot.user and replied_to.author.id == bot.user.id: # is the reply directed towards the bot?
            sentence = text_model.make_short_sentence(80, tries=100)
            if sentence:
                await message.reply(sentence)

    global globalMsg
    if message.content:
        store_message(message.content)
        globalMsg += 1
        
    if random.random() < 0.02:
        sentence = text_model.make_short_sentence(140, tries=100)
        print(repr(sentence))
        if sentence:
            await message.channel.send(sentence)

    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"command on cooldown! try in {error.retry_after:.1f}s")
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

@tasks.loop(minutes=5)
async def rebuild():
    global text_model
    with open("messages.txt", encoding="utf-8") as f:
        text = f.read()
        text_model = markovify.Text(text)


bot.run(bot_token, log_handler=handler)
