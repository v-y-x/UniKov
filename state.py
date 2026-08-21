import os
import sqlite3
import requests
import time
import datetime as dt
import discord
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_KEY")
GUILD_ID = 1381807209092223006

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
        """CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER,
        item_id INTEGER,
        quantity INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, item_id)
        )
    """)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS temp_roles (
        user_id INTEGER,
        role_id INTEGER,
        expires_at INTEGER,
        PRIMARY KEY (user_id, role_id)
        )
    """)
    con.commit()
    con.close()

# reusable commands

def add_item(user_id, item_id, quantity=1):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO inventory (user_id, item_id, quantity)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_id) DO UPDATE SET quantity = quantity + 1
    """, (user_id, item_id, quantity))
    con.commit()
    con.close()
    
def remove_item(user_id, item_id):
    con = sqlite3.connect('database.db')
    con.execute("""
        UPDATE inventory SET quantity = quantity - 1
        WHERE user_id = ? AND item_id = ?
    """, (user_id, item_id))
    con.execute('DELETE FROM inventory WHERE quantity <= 0')
    con.commit()
    con.close()

def get_inventory(user_id):
    con = sqlite3.connect('database.db')
    cur = con.cursor()
    cur.execute("SELECT item_id, quantity FROM inventory WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    con.close()
    return rows

def get_balance(user_id):
    con = sqlite3.connect('database.db')
    cursor = con.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?", (user_id,)
    )
    row = cursor.fetchone()
    con.close()
    return row[0] if row else 0 

def add_balance(user_id, amount):
    con = sqlite3.connect('database.db')
    con.execute("""
        INSERT INTO users (user_id, balance)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
    """, (user_id, amount, amount))
    con.commit()
    con.close()

heads = [] # {'user_id': int, 'amount': int}
tails = [] # {'user_id': int, 'amount': int}

# item functions

rocketActive = 0

async def use_item(user_id, item_id, shop_items, source, target_id = None, src = None):
    owned = dict(get_inventory(user_id)) # {item_id: quantity}

    item = next((i for i in shop_items if i['id'] == item_id), None)
    if not item:
        return {"success": False, "error": "this item does not exist."}

    if item.get('discord_only') and source == 1:
        return {"success": False, "error": "use this item in discord!"}

    if item.get('requires_target') and target_id is None:
        return {"success": False, "error": "you need to mention someone or give a user ID."}

    if owned.get(item_id, 0) <= 0:
        return {"success": False, "error": "you do not own this item!"}

    effect = item.get('effect')
    if effect == 'plant_bomb':
        if target_id not in user_flags:
            user_flags[target_id.id] = {"planted": 0, "set_by": []} #type: ignore
        user_flags[target_id.id]["planted"] += 1 #type: ignore
        user_flags[target_id.id]["set_by"].append(user_id) #type: ignore
        message = f"bomb planted on <@{target_id}>! they currently have {user_flags[target_id.id]['planted']} bomb(s)." #type: ignore
    elif effect == 'nuke_chat':
        targets = await get_chat_history(src, 5)
        for id in targets:
            url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{id.author.id}"
            headers = {
                "Authorization": f"Bot {BOT_TOKEN}",
                "Content-Type": "application/json"
            }
            until = (dt.datetime.utcnow() + dt.timedelta(minutes=1)).isoformat() + 'Z'
            response = requests.patch(url, headers=headers, json={"communication_disabled_until": until})
            print(response.status_code)
        message = f"a nuke has been set off by <@{user_id}>!"
    elif effect == 'coin_boost':
        add_balance(user_id, item['effect_value'])
        message = f"gained {item['effect_value']} coins!"
    elif effect == 'rocket_launcher':
        global rocketActive
        rocketActive += 3
        message = f"rocket launcher activated!"
    elif effect == 'add_role':
        role_id = item.get('role_id')
        url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/members/{user_id}/roles/{role_id}"
        headers = {
            "Authorization": f"Bot {BOT_TOKEN}"
        }

        response = requests.put(url, headers=headers)

        if response.status_code == 204:
            message = "role applied!"
        else:
            return {"success": False, "error": f"discord API error: {response.status_code}"}

        if item.get('duration'):
            expires_at = int(time.time()) + item.get('duration')
            con = sqlite3.connect('database.db')
            con.execute("""
                INSERT INTO temp_roles (user_id, role_id, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT (user_id, role_id) DO UPDATE SET expires_at = ?
                """, (user_id, role_id, expires_at, expires_at)
            )
            con.commit()
            con.close()
    else:
        return {"success": False, "error": f"item did not have an effect (sorry!)"}

    remove_item(user_id, item_id)
    return {"success": True, "message": message}

init_db()
