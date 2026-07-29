import os
import sqlite3

# import this file the moment the bot starts at first
# state.py is used for keeping memory safe so it is never reloaded through cog extensions
# the memory will live through the cog reloads, but not through full bot restarts

user_flags = {} # {user_id: ["planted": int, "set_by": [user_id, guild_id]]} --- memory for planted bomb flags
text_models = {} # {guild_id: markovify.Text()} --- memory for markov models per server
globalMsg = {} # {guild_id: message_count} --- memory for message counts per server

last_reply_time = 0 # variable which has an assigned unix time when the bot is replied to
REPLY_CD = 7.5 # constant for a reply cd

# storage helpers 

def get_file(guild_id): # get server where message was sent
    os.makedirs('messages', exist_ok=True) # create folder in case it does not exist
    return f"messages/{guild_id}.txt" # return the relevant .txt file

def store_message(message, guild_id): # stores messages from chats to the relevant server
    with open(get_file(guild_id), 'a', encoding='utf-8') as f:
        f.write(f"{message}\n")
    print(f"storing: {message[:50]} in {guild_id}.txt, current total: {globalMsg.get(guild_id, 0)}")

def get_line_count(guild_id): # get the current global message count for each server, equal to the amount of lines in {guild_id}.txt
    path = get_file(guild_id)
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for _ in f)
    
def load_message_counts(): # scans the messages folder for each .txt file
    counts = {}
    if not os.path.exists("messages"):
        return counts
    for filename in os.listdir("messages"):
        if filename.endswith('.txt'):
            guild_id = int(filename[:-4])
            counts[guild_id] = get_line_count(guild_id)
    return counts

globalMsg = load_message_counts() # populates once at initial start-up

async def get_chat_history(src, amount): # general function for searching chat history
    messages = []
    async for msg in src.channel.history(limit=amount):
        if not msg.author.bot and msg.author.id != src.author.id: # filters out bots and person that triggered the command initially
            messages.append(msg)
    return messages

# SQLite database
def init_db():
    con = sqlite3.connect('database.db')
    con.execute(
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0
        )
    """)
    con.execute(
        """CREATE TABLE IF NOT EXISTS uniEvent (
            user_id INTEGER PRIMARY KEY,
            message_count INTEGER DEFAULT 0,
            bomb_count INTEGER DEFAULT 0,
            uni_tokens INTEGER DEFAULT 0
        )
    """)
    con.commit()
    con.close()

def get_balance(user_id):
    con = sqlite3.connect('database.db')
    cursor = con.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?", (user_id,)
    )
    row = cursor.fetchone()
    cursor.execute(
        "SELECT uni_tokens FROM uniEvent WHERE user_id = ?", (user_id,)
    )
    token_row = cursor.fetchone()
    con.close()
    return row[0] if row else 0, token_row[0] if token_row else 0 

def add_balance(user_id, amount):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO users (user_id, balance)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    """, (user_id, amount, amount))
    con.commit()
    con.close()

def add_token(user_id, amount):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO uniEvent (user_id, uni_tokens)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET uni_tokens = uni_tokens + ?
    """, (user_id, amount, amount))
    con.commit()
    con.close()

def add_message_count(user_id):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO uniEvent (user_id, message_count)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET message_count = message_count + 1
    """, (user_id, )
    )
    con.commit()
    con.close()

def add_bomb_count(user_id):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO uniEvent (user_id, bomb_count_count)
        VALUES (?, 1)
        ON CONFLICT(user_id) DO UPDATE SET bomb_count = bomb_count + 1
    """, (user_id, )
    )
    con.commit()
    con.close()

init_db()