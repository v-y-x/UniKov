from discord.ext import commands
import random
import json

import state

# event.py cog. temporary cog file for the university event
# this allows the bot to reload the file independetly from the rest of the bot. essentially, a hot reload.

q = None
original_user = None
current_msg_count = 0
EXPIRE_COUNT = 100

def load_questions():
    with open('data/trivia.json', encoding='utf-8') as f:
        return json.load(f)

questions = load_questions() # load and fill questions on start
    
class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user) # 24h cooldown, per-user cooldown
    async def trivia(self, ctx):
        """Get asked a random trivia question."""
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
                        coins = random.randint(100, 500)
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