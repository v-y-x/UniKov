from discord.ext import commands
import random
import json
from random_unicode_emoji import random_emoji
from datetime import timedelta

import state

# fun.py cog. cog file for silly and fun commands

q = None
original_user = None
current_msg_count = 0
EXPIRE_COUNT = 100
chest_count = 2

def load_questions():
    with open('data/trivia.json', encoding='utf-8') as f:
        return json.load(f)

questions = load_questions() # load and fill questions on start
    
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 7200, commands.BucketType.user) # 2h per-user cooldown
    async def openChest(self, ctx):
        global chest_count
        if chest_count <= 0:
            await ctx.send("no chests available, try &searchChest")
            return
        key = state.check_item(ctx.author.id, "key")
        if not key:
            await ctx.send("it seems like you don't have a key. visit the shop!")
            return
        
        roll = random.random()
        if roll <= 1:
            reward = random.randint(2000, 12000)
            state.add_balance(ctx.author.id, reward)
            await ctx.send(f"you got {reward} coins from the chest!")
        elif roll < 0.15:
            loss = random.randint(1500, 4000)
            state.add_balance(ctx.author.id, -loss)
            await ctx.send(f"the chest was booby-trapped and you lost {loss} coins.")
            if roll < 0.05:
                ctx.author.timeout(timedelta(minutes=3))
                await ctx.send(f"the chest had a landmine in it! {ctx.author.mention} is timed out for 3 minutes.")
        state.remove_item(ctx.author.id, "key")
        chest_count =- 1

    @commands.command()
    @commands.cooldown(1, 1800, commands.BucketType.guild) # 30m server cooldown
    async def searchChest(self,ctx):
        global chest_count
        roll = random.random()
        if roll > 0.35:
            chest_count =+ 1
            await ctx.send(f"chest found! {chest_count} chests are available.")
        else:
            await ctx.send("unable to find chest.")
    
    @commands.command()
    async def betCoinflip(self, ctx, bet: str, amount: int):
        """[heads/tails] [amount] | Bet on a random coinflip!"""
        check_list = []

        for p in state.heads:
            check_list.append(p['user_id'])
        for p in state.tails:
            check_list.append(p['user_id'])

        if ctx.author.id in check_list:
            await ctx.send('you already bet on the current coinflip, no going back now!')
            return
        
        if amount <= 0:
            await ctx.send('bet at least 1 coin!')
            ctx.command.reset_cooldown(ctx)
            return

        current_bal = state.get_balance(ctx.author.id)
        if current_bal < amount:
            await ctx.send('you do not have enough coins!')
            ctx.command.reset_cooldown(ctx)
            return

        prediction = {"user_id": ctx.author.id, "amount": amount}

        bet = bet.lower()
        
        if bet == 'heads':
            state.heads.append(prediction)
        elif bet == 'tails':
            state.tails.append(prediction)
        else:
            await ctx.send('bet on either heads or tails!')
            ctx.command.reset_cooldown(ctx)
            return

        print(f'{ctx.author} bet {amount} on {bet}')
        state.add_balance(ctx.author.id, -amount)
        await ctx.send(f"you bet {amount} on {bet}!")

    @commands.command()
    @commands.cooldown(1, 10800, commands.BucketType.user) # 3h, per-user cooldown
    async def trivia(self, ctx):
        """Get asked a random trivia question for a chance to win coins!"""
        global q, correctAnswer, original_user
        if q:
            await ctx.send('wait till someone else answers their trivia first!')
            ctx.command.reset_cooldown(ctx)
            return

        if ctx.author.bot:
            return
        
        original_user = ctx.author.id
        
        q = random.choice(questions)
        print(q)
        question = q["question"]
        answers = q["answers"]
        correctAnswer = q["correct"]
        await ctx.send(f'# Trivia for {ctx.author.mention}!\n{question}\nA: {answers[0]}\nB: {answers[1]}\nC: {answers[2]}\n-# answer in capital letters!')


    @commands.Cog.listener()
    async def on_message(self, message):
        roll = random.random()
        print(roll)
        if roll < 0.05: # 5% chance
            emoji = random_emoji()
            print(f'printed emoji {emoji[0]}')
            await message.add_reaction(emoji[0])

        if roll < 0.01: # 1% chance
            if message.author.bot:
                return
            
            state.add_item(message.author.id, "key", 1)
            await message.channel.send(f"{message.author.mention} has found a key!")

        global q, correctAnswer, original_user, current_msg_count
        if q:
            current_msg_count += 1
            if current_msg_count > EXPIRE_COUNT:
                await message.channel.send(f'<@{original_user}> did not answer their trivia in time!')
                q = None
                current_msg_count = 0
                original_user = None
                return
            if message.author.id == original_user:
                if message.content in ['A', 'B', 'C']:
                    if message.content == correctAnswer:
                        coins = random.randint(350, 1200)
                        state.add_balance(original_user, coins)
                        await message.channel.send(f'correct! you earned {coins} coins.')
                        q = None
                        current_msg_count = 0
                        original_user = None
                        print(f'added {coins} coins to {message.author.id}.')
                        return
                    else:
                        await message.channel.send(f'incorrect! the answer was {correctAnswer}')
                        q = None
                        current_msg_count = 0
                        original_user = None
                        return

async def setup(bot): # required for discord.py to reach the cog when running reload commands
    await bot.add_cog(Fun(bot))