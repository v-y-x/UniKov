import os
import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.ext import tasks
import markovify
import random
import logging
import random
import time
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

# commands #

@bot.command()
@has_permissions(administrator=True) # prevent from executing unless the user has admin 
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
    
@bot.command()
async def token(ctx): # i don't even know why i made this
    """Shows the bot token"""
    await ctx.send(f"OPSEC LEVEL: SIGMA DEMON. NO TOKEN FOR U BLUD")
    await ctx.author.timeout(timedelta(minutes=1)) 

@bot.command()
async def total(ctx):
    """Shows total message count in current server"""
    count = state.globalMsg.get(ctx.guild.id, 0)
    await ctx.send(f"my current message count is {count}")

@bot.command()
async def hello(ctx): # hello!
    """Hello!"""
    await ctx.channel.send('Hello!')

@bot.command()
@commands.is_owner()
async def reload(ctx, extension: str):
    """Hot-reloads a cog extension. Only executable by bot owner."""
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
                    sentence = model.make_short_sentence(80, tries=100) # 80 char limit
                    if sentence:
                        await message.reply(sentence)
                        state.last_reply_time = now

        if random.random() < 0.01: # 1% chance
            sentence = model.make_short_sentence(140, tries=100)
            if sentence:
                await message.channel.send(sentence)
    
    if message.content:
        if not message.author.bot and not message.content.startswith(('&', '!', '.', '?')):
            state.store_message(message.content, message.guild.id)
            state.globalMsg[message.guild.id] = state.globalMsg.get(message.guild.id, 0) + 1 # add to message count for this server

    await bot.process_commands(message)

# command errors #

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"command on cooldown! try in {error.retry_after:.1f}s")
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
            guild_id = int(filename.removesuffix('.txt'))
            with open(state.get_file(guild_id), encoding="utf-8") as f:
                text = f.read()
                if text.strip(): # skip empty files cause otherwise bot will crash 
                    state.text_models[guild_id] = markovify.Text(text)

# start-up
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    rebuild.start()

async def main():
    async with bot:
        await bot.load_extension('cogs.chaos')
        await bot.start(bot_token) #type: ignore

discord.utils.setup_logging(handler=handler)
asyncio.run(main())