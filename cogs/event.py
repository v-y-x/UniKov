from discord.ext import commands
import random
import json

import state

# event.py cog. temporary cog file for the university event
# this allows the bot to reload the file independetly from the rest of the bot. essentially, a hot reload.

current_msg = 0
msg_goal = random.randint(10, 100)
q = None
EXPIRE_COUNT = 200
msgs_since_question = 0
incorrect_guesses = []

def load_questions():
    with open('data/trivia.json', encoding='utf-8') as f:
        return json.load(f)

questions = load_questions() # load and fill questions on start

def get_random_question():
    return random.choice(questions)
    
class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.member) # 5 seconds, per-user per-server cooldown
    async def addTokens(self, ctx, user: str, amount: int):
        """[user/id/mention] [amount] | Grant tokens to a user. Admin only."""
        try:
            member = await commands.MemberConverter().convert(ctx, user)
        except commands.MemberNotFound:
            await ctx.send('couldn\'t find member, re-check ID or mention.')
            return

        state.add_token(member.id, amount)
        await ctx.send(f'gave {amount} tokens to {member.mention}!')

    @commands.Cog.listener()
    async def on_message(self, message):
        global current_msg, msg_goal, msgs_since_question, incorrect_guesses, q, correctAnswer

        if message.author.bot:
            return

        if message.content.startswith(('&', '!', '.', '?')):
            return

        if message.channel.id != 1523481530121453700:
            return

        state.add_message_count(message.author.id)

        current_msg += 1
        print(f'trivia trigger in {msg_goal - current_msg} messages')

        if current_msg >= msg_goal:
            current_msg = 0
            msg_goal = random.randint(200, 500)
            print(f'new message goal: {msg_goal}')
            q = get_random_question()
            print(q)
            question = q["question"]
            answers = q["answers"]
            correctAnswer = q["correct"]
            await message.channel.send(f'# Trivia Time!\n{question}\nA: {answers[0]}\nB: {answers[1]}\nC: {answers[2]}\n-# answer in capital letters!')
            return

        if q:
            msgs_since_question += 1
            print(f'trivia expires in {EXPIRE_COUNT - msgs_since_question} messages')
            if msgs_since_question >= EXPIRE_COUNT:
                await message.channel.send(f'times up! the answer was {correctAnswer}')
                q = None
                incorrect_guesses = []
                msgs_since_question = 0
                return
            if message.author.id in incorrect_guesses:
                return
            if message.content in ['A', 'B', 'C']:
                if message.content == correctAnswer:
                    coins = random.randint(100, 500)
                    tokens = random.randint(1, 5)
                    state.add_balance(message.author.id, coins)
                    state.add_token(message.author.id, tokens)
                    await message.channel.send(f'correct! you earned {coins} gimmickoins and {tokens} university tokens.')
                    q = None
                    incorrect_guesses = []
                    msgs_since_question = 0
                    print(f'added {coins} coins and {tokens} tokens to {message.author.id}.')
                    return
                else:
                    await message.channel.send('incorrect!')
                    print(f'added {message.author.id} to incorrect guess list')
                    incorrect_guesses.append(message.author.id)

async def setup(bot): # required for discord.py to reach the cog when running reload commands
    await bot.add_cog(Event(bot))