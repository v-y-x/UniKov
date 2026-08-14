from discord.ext import commands
import random
import time

import state

last_earn_time = {}
EARN_CD = 10

# chaos.py cog. a class file that groups commands together into one file.
# this allows the bot to reload the file independetly from the rest of the bot. essentially, a hot reload.

class Econ(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.member) # 5 seconds, per-user per-server cooldown
    async def addCoins(self, ctx, user: str, amount: int):
        """[user/id/mention] [amount] | Grant coins to a user. Admin only."""
        try:
            member = await commands.MemberConverter().convert(ctx, user)
        except commands.MemberNotFound:
            await ctx.send('couldn\'t find member, re-check ID or mention.')
            return

        state.add_balance(member.id, amount)
        await ctx.send(f'gave {amount} coins to {member.mention}!')

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.member) # 5 seconds, per-user per-server cooldown
    async def balance(self, ctx):
        """Check your current balance"""
        bal = state.get_balance(ctx.author.id)
        coins = bal
        await ctx.channel.send(f'you currently have {coins} coins')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
    
        now = time.time()
        last_time = last_earn_time.get(message.author.id, 0)

        if now - last_time >= EARN_CD:
            earned = random.randint(1, 5)
            state.add_balance(message.author.id, earned)
            last_earn_time[message.author.id] = now
            print(f'{message.author.id} earned {earned}')

async def setup(bot): # required for discord.py to reach the cog when running reload commands
    await bot.add_cog(Econ(bot))