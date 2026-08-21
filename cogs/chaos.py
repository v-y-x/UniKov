import discord
from discord.ext import commands
import random
from datetime import timedelta

import state

# chaos.py cog. a class file that groups commands together into one file.
# this allows the bot to reload the file independetly from the rest of the bot. essentially, a hot reload.

class Chaos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 5400, commands.BucketType.member) # 1.5 hour, per-user per-server cooldown
    async def plant(self, ctx, user: str):
        """ [user id/mention] | Plants a bomb on targeted user. 90 minute cooldown"""
        bot_member = ctx.guild.me # get object data of the bot
    
        if not bot_member.guild_permissions.moderate_members: # fall back for no permissions
            ctx.command.reset_cooldown(ctx)
            await ctx.send('i\'m missing permissions to time people out!')
            return
    
        if user.lower() == 'random':
            messages = await state.get_chat_history(ctx, 30) # grab a random user from the past 30 messages
            randMsg = random.choice(messages)
            member = randMsg.author
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, user)
            except commands.MemberNotFound:
                ctx.command.reset_cooldown(ctx)
                await ctx.send('couldn\'t find member, re-check ID or mention.')
                return
    
        if member.top_role >= bot_member.top_role: # prevent planting if the user has a higher role than the bot, failsafe
            try:
                await ctx.author.timeout(timedelta(minutes=1))
                await ctx.send(f'{ctx.author.mention} tried planting a bomb on {member.mention}, but it backfired! 💥 timed out for 1 minute') # lol
                return
            except discord.Forbidden:
                ctx.command.reset_cooldown(ctx)
                await ctx.send(f'Why are you planting on staff, as a staff?') # fall back when staff on staff violence
                return
    
        if member.id not in state.user_flags:
            state.user_flags[member.id] = {"planted": 0, "set_by": []}
    
        state.user_flags[member.id]["planted"] += 1
        state.user_flags[member.id]["set_by"].append(ctx.author.id)
    
        await ctx.send(f'bomb planted on {member}. they currently have {state.user_flags[member.id]["planted"]} bomb(s)')
        print(f'bomb planted on {member} by {ctx.author}.')

    @commands.Cog.listener()
    async def on_message(self, message): # triggers on any message sent in any accessible channel
        if message.author.bot: # ignore if message is a bot
            return

        if state.rocketActive > 0:
            if message.mentions:
                target = message.mentions[0]
                try:
                    await target.timeout(timedelta(minutes=3))
                    await message.channel.send(f'{target} was blown up by a rocket!')
                except discord.Forbidden:
                    await message.channel.send(f'{target} dodged a rocket!')
                state.rocketActive -= 1

        if random.random() < 0.001: # .1% chance
            try:
                roll = random.random()
                if roll < .20: # 15% chance
                    await message.author.timeout(timedelta(minutes=3))
                    await message.channel.send(f'{message.author.mention} stepped on a super landmine! 💥 timed out for 3m')
                    return

                elif roll < .05: # 5% chance
                    await message.author.timeout(timedelta(minutes=1))
                    await message.channel.send(f'{message.author.mention} stepped on a nuke!! ☢️💥 5 people are timed out for 1m')

                    messages = await state.get_chat_history(message, 5)
                    for msg in messages:
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

        if state.user_flags.get(message.author.id, {}).get("planted", 0) > 0: # checks if they have the planted flag
            if not message.guild.me.guild_permissions.moderate_members:
                await message.channel.send(f'{message.author.mention} would have been bombed, but i am lacking timeout permissions!')
                del state.user_flags[message.author.id] # remove ID after execution
                return

            bombs_planted = state.user_flags[message.author.id]["planted"]
            setters = state.user_flags[message.author.id]["set_by"]

            timeout_time = 60

            if bombs_planted > 1: 
                timeout_time = timeout_time * bombs_planted * (1 + (bombs_planted / 20)) # e.g. 60 * 2 * ( 1 + ( 2 / 20 )) = 132s 
                await message.author.timeout(timedelta(seconds=timeout_time))

                header = f'{message.author.mention} had {bombs_planted} bombs go off!! 💥 they are timed out for {int(timeout_time / 60)}m. the bombs were planted by '
                mentions = [f'<@{sid}>' for sid in setters] # gets all the IDs of the planters

                chunk = header
                for mention in mentions:
                    if len(chunk) + len(mention) + 2 > 2000:
                        await message.channel.send(chunk)
                        chunk = mention
                    else:
                        chunk += (', ' if chunk != header else '') + mention

                await message.channel.send(chunk)

            else:
                await message.author.timeout(timedelta(seconds=timeout_time))
                await message.channel.send(f'{message.author.mention} has been bombed! 💥 they are timed out for 1m. the bomb was planted by <@{setters[0]}>')

            del state.user_flags[message.author.id] # remove ID after execution

async def setup(bot): # required for discord.py to reach the cog when running reload commands
    await bot.add_cog(Chaos(bot))