import os
import discord
import sqlite3
from discord.ext import commands
from discord.ext import tasks
import markovify
import random
import logging
import random
import time
import json
from datetime import timedelta
from dotenv import load_dotenv
import asyncio

import state

load_dotenv()

bot_token = os.getenv("BOT_KEY") # get token from .env file
assert bot_token is not None, "Token not found in .env" # pylance ignore

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='&', intents=intents)

def load_items():
    with open('data/shop_items.json', encoding='utf-8') as f:
        return json.load(f)

shop_items = load_items()

def find_item_by_name(name):
    name = name.lower()
    return next((i for i in shop_items if i['name'].lower() == name), None)

# commands #

@bot.command()
@commands.has_permissions(administrator=True) # prevent from executing unless the user has admin 
async def scrape(ctx, amount : int = 1000):
    """ [number] | Reads the chat history of the current channel"""

    progMsg =  await ctx.send("scraping... [░░░░░░░░░░░░░░░░░░░░] 0%")
    msgCount = 0
    update_every = max(1, amount // 20)

    async for msg in ctx.channel.history(limit=amount): # specialized chat history search function
        print(f"checking: {msg.content[:30]!r}, author bot: {msg.author.bot}")
        if not msg.author.bot and not msg.content.startswith(('&', '!', '.', '?')):
            state.store_message(msg.content, msg.guild.id)
            msgCount += 1
            state.globalMsg[msg.guild.id] = state.globalMsg.get(msg.guild.id, 0) + 1

            if msgCount % update_every == 0 or msgCount == amount:
                percent = int((msgCount / amount) * 100)
                filled = int(percent / 5 )
                bar = "█" * filled + "░" * (20 - filled)
                await progMsg.edit(content=f"scraping... [{bar}] {percent}%")
    
    await progMsg.edit(content=f"{msgCount} messages scraped! current total: {state.globalMsg.get(ctx.guild.id, 0)}")
    
# @bot.command()
# async def token(ctx): # i don't even know why i made this
#     """Shows the bot token"""
#     await ctx.send(f"OPSEC LEVEL: SIGMA DEMON. NO TOKEN FOR U BLUD")
#     await ctx.author.timeout(timedelta(minutes=1)) 

@bot.command()
async def total(ctx):
    """Shows total message count in current server"""
    count = state.globalMsg.get(ctx.guild.id, 0)
    await ctx.send(f"my current message count is {count}")

@bot.command()
async def hello(ctx): # hello!
    """Hello!"""
    await ctx.channel.send('Hello!')

@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx, extension: str):
    try:
        await bot.reload_extension(f'cogs.{extension}')
        await ctx.send(f'reloaded {extension}!')
    except Exception as e:
        await ctx.send(f'failed to reload {extension} cog: {e}')

# bot events #
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    model = state.text_models.get(message.guild.id)
    if model:
        if message.reference and message.reference.resolved: # is the message a reply to something?
            replied_to = message.reference.resolved 
            if bot.user and replied_to.author.id == bot.user.id: # is the reply directed towards the bot?
                now = time.time()
                if now - state.last_reply_time >= state.REPLY_CD: # checks whether the last replying message is more than REPLY_CD seconds ago
                    sentence = model.make_short_sentence(150, tries=500) # 120 char limit
                    if sentence:
                        await message.reply(sentence)
                        state.last_reply_time = now

        if random.random() < 0.01: # 1% chance
            sentence = model.make_short_sentence(180, tries=100) # 180 character limit
            if sentence:
                await message.channel.send(sentence)
    
    if message.content:
        if not message.author.bot and not message.content.startswith(('&', '!', '.', '?')):
            state.store_message(message.content, message.guild.id)
            state.globalMsg[message.guild.id] = state.globalMsg.get(message.guild.id, 0) + 1 # add to message count for this server

    await bot.process_commands(message)

@bot.command()
async def use(ctx, item_name: str, target: discord.Member = None): #type: ignore
    """[item] | Use an item"""
    item = find_item_by_name(item_name)

    source = 0 # source coming from discord
    result = await state.use_item(ctx.author.id, item['id'], shop_items, source, target, ctx) #type: ignore

    if result.get("success"):
        await ctx.send(result.get("message"))
    else:
        await ctx.send(f"unable to use item: {result.get('error')}")

bot.command()
async def inventory(ctx):
    """Check your inventory"""
    inventory = state.get_inventory(ctx.author.id)
    await ctx.send(inventory)

# command errors #

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        cd = error.retry_after
        if cd >= 60:
            await ctx.send(f"command on cooldown! try in {cd / 60:.1f}m")
        else:
            await ctx.send(f"command on cooldown! try in {cd:.1f}s")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send('couldn\'t find that member, recheck the ID or mention')
        ctx.command.reset_cooldown(ctx)
    elif isinstance(error, commands.MissingRequiredArgument):
        ctx.command.reset_cooldown(ctx)
        await ctx.send('missing arguments')
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('you are missing required permissions run the command')
    else:
        print(f"Unhandled error: {error}")
        raise error

# tasks #

@tasks.loop(minutes=5) # task loop that refreshes markov model every 5 minutes
async def rebuild():
    if not os.path.exists('messages'):
        return
    for filename in os.listdir('messages'):
        if filename.endswith('.txt'):
            guild_id = int(filename[:-4])
            with open(state.get_file(guild_id), encoding="utf-8") as f:
                text = f.read()
                if not text.strip():
                    continue # skip empty files cause otherwise bot will crash 
                try:
                    state.text_models[guild_id] = markovify.Text(text)
                except KeyError:
                    print(f'unable to build model for {guild_id} - likely not enough data\nLOG: {KeyError}')
                    continue

@tasks.loop(minutes=10)
async def expired_roles_check():
    now = int(time.time())
    con = sqlite3.connect('database.db')
    cursor = con.execute("SELECT user_id, role_id FROM temp_roles WHERE expires_at <= ?", (now, ))
    expired = cursor.fetchall()

    guild = bot.get_guild(state.GUILD_ID)
    for user_id, role_id in expired:
        member = guild.get_member(user_id) # type: ignore
        role = guild.get_role(role_id)  # type: ignore
        if member and role:
            try:
                await member.remove_roles(role)
                print(f'removed {role} role from {member}')
            except discord.Forbidden:
                print(f"couldn't remove role from {member}, missing permissions?")
        else:
            print(f'role and/or member turned out as None: {role} | {member}') 

        con.execute("DELETE FROM temp_roles WHERE user_id = ? AND role_id = ?", (user_id, role_id))

    con.commit()
    con.close()

@tasks.loop(minutes=1800)
async def coinflip():
    if not state.heads and not state.tails:
        print('nobody bet on current coinflip')
        return # nobody bet on coinflip

    result = random.choice(['heads', 'tails'])
    winners = state.heads if result == 'heads' else state.tails
    losers = state.tails if result == 'heads' else state.heads

    channel_id = bot.get_channel(1536364675636269076)

    total_winners_pot = sum(p['amount'] for p in winners)
    total_losers_pot = sum(p['amount'] for p in losers)

    if not winners:
        await channel_id.send(f"the coin landed on **{result}**. no one won!") #type: ignore
    else:
        for winner in winners:
            user_id = winner['user_id']
            payout = winner['amount'] * 2
            state.add_balance(user_id, payout)
        
        await channel_id.send(f"the coin landed on **{result}**. {len(winners)} winners got double their bet, for a total of {total_winners_pot * 2} coins!") #type: ignore
        if losers:
            await channel_id.send(f"the opposing side had {len(losers)} losers, totaling up to a loss of {total_losers_pot} coins!") #type: ignore

    print(f'{result} won, awarded {len(winners)} users.')
    state.heads.clear()
    state.tails.clear()
        
# start-up
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    rebuild.start()
    expired_roles_check.start()
    coinflip.start()

async def main():
    async with bot:
        await bot.load_extension('cogs.chaos')
        await bot.load_extension('cogs.econ')
        await bot.load_extension('cogs.fun')
        await bot.start(bot_token) #type: ignore

discord.utils.setup_logging(handler=handler)
asyncio.run(main())
