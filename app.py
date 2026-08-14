import os
from flask import Flask, redirect, request, session, jsonify
import requests
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

import state

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "https://unikov.v-y-x.xyz/callback"

def load_items():
    with open('data/shop_items.json', encoding='utf-8') as f:
        return json.load(f)

shop_items = load_items()

@app.route('/login')
def login():
    next_page = request.args.get('next', '/')
    discord_auth_url = (
        f'https://discord.com/api/oauth2/authorize'
        f'?client_id={CLIENT_ID}'
        f'&redirect_uri={REDIRECT_URI}'
        f'&response_type=code'
        f'&scope=identify'
        f'&state={next_page}'
    )
    return redirect(discord_auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    next_page = request.args.get('state', '/')
    if not code:
        return "no code provided", 400

    token_respone = requests.post('https://discord.com/api/oauth2/token', data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
    })
    token_data = token_respone.json()
    access_token = token_data['access_token']

    user_response = requests.get('https://discord.com/api/users/@me', headers={
        'Authorization': f'Bearer {access_token}'
    })
    user_data = user_response.json()

    session['user_id'] = user_data['id']
    session['username'] = user_data['username']
    if user_data.get('avatar'):
        ext = 'gif' if user_data['avatar'].startswith('a_') else 'png'
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.{ext}"
    else:
        default_index = (int(user_data['id']) >> 22) % 6
        avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"
    session['avatar'] = avatar_url

    return redirect(f'https://unikov.v-y-x.xyz{next_page}')


@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "username": session.get('username'),
        "avatar": session.get('avatar'),
        "balance": state.get_balance(int(int(session['user_id'])))
    })

@app.route('/api/buy', methods=['POST'])
def buy():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in",}), 401

    user_id = int(session['user_id'])
    data = request.get_json()
    item_id = data.get('item_id')

    item = next((i for i in shop_items if i['id'] == item_id), None)
    if not item:
        return jsonify({"error": "item not found"}), 404

    balance = state.get_balance(user_id)
    if balance < item['price']:
        return jsonify({"error": "you have insufficient balance!"}), 400

    state.add_balance(user_id, -item['price'])
    state.add_item(user_id, item_id)

    return jsonify({'success': True, "new_balance": balance - item['price']})

@app.route('/api/inventory')
def get_inventory():
    if 'user_id' not in session:
        return jsonify({"items": []})

    user_id = int(session['user_id'])
    owned = state.get_inventory(user_id)

    result = []
    for item_id, quantity in owned:
        item = next((i for i in shop_items if i['id'] == item_id), None)
        if item:
            result.append({**item, "quantity": quantity})

    return jsonify({"items": result})

@app.route('/api/use', methods=["POST"])
def use_item():
    if 'user_id' not in session:
        return jsonify({"error": "not logged in"}), 401

    source = 1 # execute coming from site frontend 
    user_id = int(session['user_id'])
    item_id = request.get_json().get('item_id')

    result = asyncio.run(state.use_item(user_id, item_id, shop_items, source))
    return jsonify(result)

if __name__ == '__main__':
    app.run(port=5000)