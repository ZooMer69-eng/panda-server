from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict
from pydantic import BaseModel
import json
import os
import time
import random
import string
import psycopg2
from psycopg2.extras import RealDictCursor
import aiohttp

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = "9244645218:AAFopJ-hOND0D5dQx9qzZurAUTbAWQpKs3A"
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_ID = "6877882967"

def get_db():
    try:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, sslmode='require')
    except Exception as e:
        print(f"DB CONNECTION ERROR: {e}")
        return None

def init_db():
    conn = get_db()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, data TEXT)''')
        conn.commit()
        conn.close()
    except Exception as e: print(f"DB Init Error: {e}")

def load_players():
    players = {}
    conn = get_db()
    if not conn: return players
    try:
        c = conn.cursor()
        c.execute("SELECT id, data FROM players")
        for row in c.fetchall():
            uid = row['id']
            p_data = json.loads(row['data'])
            
            if "upgrades" not in p_data: p_data["upgrades"] = {"tap": 0, "max_energy": 0, "regen": 0}
            if "selectedMedal" not in p_data: p_data["selectedMedal"] = "none"
            if "selectedFrame" not in p_data: p_data["selectedFrame"] = "default"
            if "selectedNickAnim" not in p_data: p_data["selectedNickAnim"] = "default"
            if "unlockedMedals" not in p_data: p_data["unlockedMedals"] = []
            if "unlockedFrames" not in p_data: p_data["unlockedFrames"] = ["default"]
            if "unlockedAnims" not in p_data: p_data["unlockedAnims"] = ["default"]
            if "friends" not in p_data: p_data["friends"] = []
            if "bamboos" not in p_data: p_data["bamboos"] = [{"id": 1, "stage": 0, "planted": 0}, {"id": 2, "stage": 0, "planted": 0}, {"id": 3, "stage": 0, "planted": 0}]
            if "lobby_partner" not in p_data: p_data["lobby_partner"] = None
            if "lobby_partner_name" not in p_data: p_data["lobby_partner_name"] = None
            if "gifts" not in p_data: p_data["gifts"] = 0
            if "gift_history" not in p_data: p_data["gift_history"] = []
            
            if "gender" not in p_data: p_data["gender"] = random.choice(["male", "female"])
            if "house_level" not in p_data: p_data["house_level"] = 1
            if "is_pregnant" not in p_data: p_data["is_pregnant"] = False
            if "pregnancy_end" not in p_data: p_data["pregnancy_end"] = 0
            if "has_baby" not in p_data: p_data["has_baby"] = False
            if "baby_hunger" not in p_data: p_data["baby_hunger"] = 100
            
            if uid == ADMIN_ID:
                p_data["verified"] = True
                p_data["unlockedMedals"] = ['bronze', 'silver', 'gold', 'epic', 'mythic']
                p_data["unlockedFrames"] = ['default', 'millionaire', 'legend', 'neon', 'nature', 'fire']
                p_data["unlockedAnims"] = ['default', 'gold', 'fire', 'rainbow']
            
            players[uid] = p_data
        conn.close()
    except Exception as e: print(f"DB Load Error: {e}")
    return players

def save_player(user_id, data):
    conn = get_db()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("INSERT INTO players (id, data) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data", (user_id, json.dumps(data)))
        conn.commit()
        conn.close()
    except Exception as e: print(f"DB Save Error: {e}")

init_db()
players_db: Dict[str, dict] = load_players()
active_connections: Dict[str, WebSocket] = {}

class GemPurchase(BaseModel):
    user_id: str
    amount: int

class InvoiceRequest(BaseModel):
    user_id: str
    stars: int
    gems: int

@app.post("/api/add_gems")
async def add_gems(data: GemPurchase):
    if data.user_id in players_db:
        players_db[data.user_id]["gems"] += data.amount
        save_player(data.user_id, players_db[data.user_id])
        if data.user_id in active_connections:
            try: await active_connections[data.user_id].send_text(json.dumps({"type": "update_stats", "gems": players_db[data.user_id]["gems"], "coins": players_db[data.user_id]["coins"]}))
            except: pass
        return {"status": "ok"}
    return {"status": "error"}

@app.post("/api/create_invoice")
async def create_invoice(req: InvoiceRequest):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendInvoice"
    payload = {
        "chat_id": req.user_id, "title": f"Покупка {req.gems} гемов 💎",
        "description": "Пополнение баланса игры Panda Game",
        "payload": f"gems_{req.gems}", "provider_token": "", "currency": "XTR",
        "prices": [{"label": f"{req.gems} гемов", "amount": req.stars}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp: return await resp.json()

@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def serve_game():
    response = HTMLResponse(content=HTML_CONTENT)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.get("/api/search_players")
async def search_players(q: str, my_id: str):
    results = []
    q = q.lower()
    for uid, data in players_db.items():
        if uid == my_id: continue
        if q in data["name"].lower() or q in data.get("game_id", "").lower():
            results.append({"id": uid, "name": data["name"], "game_id": data.get("game_id", "N/A"), "avatar": data.get("avatar", ""), "online": (time.time() - data["last_active"]) < 120})
            if len(results) >= 15: break
    return results

@app.get("/api/friends/{user_id}")
async def get_friends(user_id: str):
    if user_id not in players_db: return []
    friends_list = []
    for f_id in players_db[user_id].get("friends", []):
        if f_id in players_db:
            f_data = players_db[f_id]
            friends_list.append({
                "id": f_id, "name": f_data["name"], "avatar": f_data.get("avatar", ""),
                "coins": f_data["coins"], "gems": f_data["gems"], "frame": f_data.get("selectedFrame", "default"),
                "medal": f_data.get("selectedMedal", "none"), "nick_style": f_data.get("selectedNickAnim", "nick-default"),
                "verified": f_data.get("verified", False), "gifts": f_data.get("gifts", 0), "gift_history": f_data.get("gift_history", []),
                "online": (time.time() - f_data["last_active"]) < 120
            })
    return friends_list

HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Panda Game 41.0</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        body { background: #0a120e; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        
        .bg-container { position: absolute; inset: 0; z-index: 1; overflow: hidden; }
        .bg-base { background: linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #334155 70%, #475569 100%); }
        .bg-moon { position: absolute; top: 10%; right: 15%; width: 80px; height: 80px; background: radial-gradient(circle, #fef08a 10%, #fde047 40%, transparent 70%); border-radius: 50%; filter: blur(2px); box-shadow: 0 0 40px rgba(253, 224, 71, 0.4); }
        .bg-mountains { position: absolute; bottom: 20%; left: 0; width: 100%; height: 45%; }
        .bg-mountains svg { width: 100%; height: 100%; filter: drop-shadow(0 -5px 10px rgba(0,0,0,0.5)); }
        .bg-bamboo { position: absolute; bottom: 0; left: 0; width: 100%; height: 85%; display: flex; justify-content: space-around; align-items: flex-end; z-index: 2; }
        .stalk { position: relative; width: 22px; background: linear-gradient(90deg, #064e3b 0%, #10b981 20%, #34d399 50%, #10b981 80%, #064e3b 100%); border-radius: 10px; box-shadow: 5px 0 15px rgba(0,0,0,0.5); }
        .stalk::before { content: ''; position: absolute; inset: 0; background: repeating-linear-gradient(180deg, transparent 0 100px, #022c22 100px 106px); border-radius: 10px; }
        .bg-ground { position: absolute; bottom: 0; left: 0; width: 100%; height: 25%; background: linear-gradient(to top, #022c22 0%, #064e3b 100%); z-index: 3; box-shadow: inset 0 10px 30px rgba(0,0,0,0.5); }
        
        /* Ambient Effects */
        .bg-effects { position: absolute; inset: 0; pointer-events: none; z-index: 4; overflow: hidden;}
        .firefly { position: absolute; width: 4px; height: 4px; background: #ffd700; border-radius: 50%; box-shadow: 0 0 10px #ffd700, 0 0 20px #ffd700; opacity: 0; animation: fly linear infinite; }
        @keyframes fly { 0% { transform: translate(0, 0); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translate(100px, -100px); opacity: 0; } }
        .butterfly { position: absolute; font-size: 20px; animation: flutter linear infinite; }
        @keyframes flutter { 0% { transform: translate(0, 0) rotate(0deg); opacity: 0; } 10% { opacity: 1; } 50% { transform: translate(150px, -50px) rotate(20deg); } 90% { opacity: 1; } 100% { transform: translate(300px, -100px) rotate(-20deg); opacity: 0; } }

        .header { padding: 12px 15px; display: flex; justify-content: space-between; align-items: flex-start; z-index: 10; position: relative; }
        .user-info-block { display: flex; align-items: center; gap: 10px; }
        .avatar-wrap { position: relative; width: 50px; height: 50px; cursor: pointer; }
        .profile-avatar-mini { width: 100%; height: 100%; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; font-size: 24px; overflow: hidden; border: 2px solid #fff; z-index: 2; position: relative; }
        .profile-avatar-mini img { width: 100%; height: 100%; object-fit: cover; display: block; }
        
        .avatar-frame { position: absolute; inset: -4px; border-radius: 50%; z-index: 1; border: 3px solid transparent; }
        .avatar-frame.default { border-color: #fff; }
        .avatar-frame.millionaire { border-color: #ffd700; box-shadow: 0 0 10px #ffd700; }
        .avatar-frame.legend { border-color: #00e5ff; box-shadow: 0 0 20px #00e5ff; animation: spin 4s linear infinite; }
        .avatar-frame.neon { border-color: #ff00ff; box-shadow: 0 0 15px #ff00ff, inset 0 0 10px #ff00ff; }
        .avatar-frame.nature { border-color: #8bc34a; box-shadow: 0 0 15px #8bc34a, inset 0 0 10px #8bc34a; animation: pulse 2s infinite alternate; }
        .avatar-frame.fire { border-color: #ff5722; box-shadow: 0 0 15px #ff5722, inset 0 0 10px #ff5722; animation: fireFlicker 1.5s infinite alternate; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        @keyframes pulse { 0% { opacity: 0.7; } 100% { opacity: 1; } }
        @keyframes fireFlicker { 0% { transform: scale(1); opacity: 0.9; } 100% { transform: scale(1.02); opacity: 1; } }
        
        .name-medal-block { display: flex; flex-direction: column; cursor: pointer; }
        .name-row { display: flex; align-items: center; gap: 5px; }
        .header-nick { font-size: 16px; font-weight: 900; text-shadow: 2px 2px 0 #000; }
        
        .nick-default { color: #fff; display: inline-block; }
        .nick-gold { background: linear-gradient(90deg, #ffd700, #ff8c00, #ffd700); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: goldShine 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,215,0,0.5)); display: inline-block; }
        .nick-fire { color: #ff4500; text-shadow: 0 0 5px #ff4500, 0 0 15px #ff0000; animation: fireFlicker 1.5s infinite alternate; display: inline-block; }
        .nick-rainbow { background: linear-gradient(90deg, #ff0000, #ff8c00, #ffff00, #00ff00, #00e5ff, #0000ff, #ff00ff); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: rainbowMove 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,255,255,0.3)); display: inline-block; }
        @keyframes goldShine { to { background-position: 200% center; } }
        @keyframes rainbowMove { to { background-position: 200% center; } }
        
        .res-row { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
        .coins-box { font-size: 18px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 3px; }
        .gems-box { font-size: 14px; font-weight: 900; color: #00e5ff; display: flex; align-items: center; gap: 3px; cursor: pointer; }
        .icon-coin { display: inline-block; width: 16px; height: 16px; background: radial-gradient(circle at 30% 30%, #fff000, #ffb300, #b26a00); border-radius: 50%; border: 1px solid #e6a800; box-shadow: 0 1px 3px rgba(0,0,0,0.5); text-align: center; line-height: 14px; font-size: 10px; font-weight: 900; color: #8a5100; vertical-align: middle; margin-left: 2px; }
        .icon-gem { display: inline-block; font-size: 16px; filter: drop-shadow(0 0 3px #00e5ff); margin-left: 2px; }
        .energy-box { display: flex; flex-direction: column; align-items: flex-end; cursor: pointer; }
        .energy-bar { width: 70px; height: 8px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; border: 1px solid rgba(255,255,255,0.4); margin-top: 3px; }
        .energy-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #007bff); width: 100%; transition: width 0.3s; }

        .screens { flex: 1; position: relative; z-index: 5; overflow: hidden; }
        .screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; flex-direction: column; }
        .screen.active { display: flex; }
        .content { flex: 1; padding: 15px; overflow-y: auto; background: rgba(10, 18, 14, 0.95); backdrop-filter: blur(10px); z-index: 20; }
        .section-title { font-size: 18px; font-weight: 900; margin-bottom: 15px; color: #fff; text-align: center; }
        
        .tap-area { flex: 1; display: flex; justify-content: center; align-items: flex-end; gap: 20px; position: relative; padding-bottom: 10px; z-index: 5; }
        .panda-wrapper { position: relative; width: 190px; height: 210px; transform-origin: center bottom; cursor: pointer; transition: transform 1s ease-in-out; z-index: 10; }
        .panda-wrapper:active { transform: scale(0.95); }
        .panda-wrapper.hit { animation: jump 0.25s ease-out; }
        @keyframes jump { 0% { transform: translateY(0); } 30% { transform: translateY(-15px) scale(1.05); } 100% { transform: translateY(0); } }
        
        .particle-coin { position: absolute; font-size: 24px; font-weight: 900; color: #ffd700; pointer-events: none; animation: popCoin 0.9s ease-out forwards; z-index: 20; text-shadow: 0 0 10px #ffd700; }
        @keyframes popCoin { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 100% { transform: translateY(-100px) scale(1.2); opacity: 0; } }
        .particle-heart { position: absolute; font-size: 24px; pointer-events: none; animation: popHeart 1s ease-out forwards; z-index: 20; }
        @keyframes popHeart { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 50% { transform: translateY(-50px) scale(1.2); opacity: 1; } 100% { transform: translateY(-100px) scale(1); opacity: 0; } }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 12px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .card-icon { font-size: 32px; margin-bottom: 6px; }
        .card-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .card-desc { font-size: 11px; color: #8892b0; margin-bottom: 8px; }
        .card-price { background: rgba(0,0,0,0.5); padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 900; width: 100%; color: #ffd700; border: 1px solid rgba(255,215,0,0.3); cursor: pointer; }
        .card-price:active { background: rgba(255,215,0,0.2); }
        
        .profile-card { background: #1a2e22; border-radius: 15px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 15px; display: flex; flex-direction: column; align-items: center; }
        .profile-avatar-large { width: 80px; height: 80px; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; font-size: 40px; position: relative; overflow: hidden; border: 2px solid #fff; z-index: 2; flex-shrink: 0; }
        .profile-avatar-large img { width: 100%; height: 100%; object-fit: cover; display: block; }
        
        .inventory-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 10px; margin-bottom: 20px; }
        .inv-item { background: rgba(255,255,255,0.05); border-radius: 10px; padding: 10px; text-align: center; border: 2px solid transparent; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .inv-item.selected { border-color: #4caf50; background: rgba(76, 175, 80, 0.2); box-shadow: 0 0 10px #4caf50; }
        .inv-icon { font-size: 24px; margin-bottom: 5px; filter: grayscale(1); }
        .inv-item.owned .inv-icon { filter: none; }
        .medal-emoji { font-size: 18px; }
        
        .casino-box { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px; }
        .wheel-container { position: relative; width: 220px; height: 220px; }
        .wheel-pointer { position: absolute; top: -15px; left: 50%; transform: translateX(-50%); font-size: 40px; z-index: 10; text-shadow: 0 2px 5px #000; }
        .wheel { width: 100%; height: 100%; border-radius: 50%; border: 6px solid #ffd700; box-shadow: 0 0 20px rgba(255,215,0,0.4); transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99); overflow: hidden; position: relative; background: conic-gradient(#e53935 0deg 60deg, #1e88e5 60deg 120deg, #43a047 120deg 180deg, #fdd835 180deg 240deg, #8e24aa 240deg 300deg, #fb8c00 300deg 360deg); }
        .bet-buttons { display: flex; gap: 10px; margin-top: 20px; }
        .bet-btn { background: #333; padding: 10px 15px; border-radius: 8px; border: 1px solid #555; font-weight: 900; cursor: pointer; color: #fff; }
        .bet-btn.active { background: #4caf50; border-color: #81c784; }
        .bet-btn.disabled { opacity: 0.5; pointer-events: none; }

        .tab-btn { flex: 1; background: rgba(255,255,255,0.1); border: none; color: #aaa; padding: 8px; border-radius: 8px; font-weight: 900; cursor: pointer; }
        .tab-btn.active { background: #4caf50; color: #fff; }
        
        .friend-item { display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; margin-bottom: 10px;}
        .friend-avatar { width: 35px; height: 35px; border-radius: 50%; background: #333; display: flex; justify-content: center; align-items: center; overflow: hidden; }
        .friend-avatar img { width: 100%; height: 100%; object-fit: cover; }
        .verified-badge { display: inline-flex; justify-content: center; align-items: center; width: 16px; height: 16px; background: #2196f3; border-radius: 50%; color: #fff; font-size: 10px; margin-left: 5px;}

        .bottom-nav { background: rgba(10, 18, 14, 0.98); border-top: 1px solid rgba(46, 125, 50, 0.4); padding: 8px 5px 22px 5px; display: flex; justify-content: space-around; z-index: 30; position: relative; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; background: none; border: none; color: #666; font-size: 9px; font-weight: 900; cursor: pointer; width: 16.6%; transition: 0.2s; }
        .nav-btn.active { color: #81c784; }
        .nav-btn span { font-size: 22px; margin-bottom: 2px; filter: grayscale(1); transition: 0.2s; }
        .nav-btn.active span { filter: drop-shadow(0 0 6px #81c784) grayscale(0); }

        .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.85); z-index: 1000; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px; backdrop-filter: blur(5px); }
        .modal.active { display: flex; }
        .modal-box { background: #1a2e22; border: 2px solid #4caf50; border-radius: 20px; padding: 25px; width: 90%; max-width: 350px; position: relative; }
        
        .gift-history-item { display: flex; align-items: center; gap: 10px; background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 8px; margin-bottom: 5px; font-size: 12px; text-align: left; }
        .gift-history-icon { font-size: 20px; }

        /* Lobby Styles */
        .lobby-active-view { display: none; flex-direction: column; align-items: center; justify-content: flex-start; text-align: center; width: 100%; height: 100%; position: relative;}
        
        .house-bg-1 { background: transparent; }
        .house-bg-2 { background: rgba(78, 52, 46, 0.4); border: 2px solid #8d6e63; border-radius: 15px; }
        .house-bg-3 { background: rgba(26, 35, 126, 0.4); border: 2px solid #ffd700; box-shadow: inset 0 0 20px #ffd700; border-radius: 15px; }
        
        .room-container { width: 100%; height: 280px; position: relative; margin-top: 10px; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 20px; gap: 15px; transition: all 0.5s; }
        
        .duo-panda { position: relative; text-align: center; transition: transform 0.3s; display: flex; flex-direction: column; align-items: center; cursor: pointer; }
        .duo-panda:active { transform: scale(0.95) !important; }
        .duo-panda.hit { animation: jump 0.25s ease-out; }
        
        .duo-panda.baby { transform: scale(0.65); transform-origin: bottom center; margin-left:-10px; margin-right:-10px;}
        .duo-panda svg { width: 110px; height: 120px; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5)); }
        .duo-name { font-size: 14px; font-weight: 900; text-shadow: 2px 2px 0 #000; margin-top: -10px; z-index: 2; position: relative;}
        
        .baby-stats { width: 100%; background: rgba(0,0,0,0.5); padding: 10px; border-radius: 10px; margin-top: 15px; border: 1px solid #ff9800;}
        .baby-bar-bg { width: 100%; height: 10px; background: #333; border-radius: 5px; overflow: hidden; margin-top: 5px; }
        .baby-bar-fill { height: 100%; background: #ff9800; width: 100%; transition: width 0.3s; }
        
        .pregnancy-alert { background: rgba(255, 182, 193, 0.2); border: 1px solid #ff69b4; padding: 10px; border-radius: 10px; margin-top: 10px; color: #ff69b4; font-weight: 900; }
        .baby-mood { position: absolute; top: -20px; left: 50%; transform: translateX(-50%); font-size: 30px; animation: float 2s infinite alternate; }
        @keyframes float { 0% { transform: translate(-50%, 0); } 100% { transform: translate(-50%, -10px); } }
    </style>
</head>
<body>
    <div class="bg-container bg-base">
        <div class="bg-moon"></div>
        <div class="bg-mountains"><svg viewBox="0 0 400 200" preserveAspectRatio="none"><path d="M0,200 L50,80 L120,120 L180,40 L260,90 L340,60 L400,150 L400,200 Z" fill="#1e293b"/><path d="M0,200 L70,110 L150,150 L240,80 L320,130 L400,200 Z" fill="#334155"/></svg></div>
        <div class="bg-bamboo"><div class="stalk" style="height: 70%; left: 5%;"></div><div class="stalk" style="height: 90%; left: 20%;"></div><div class="stalk" style="height: 60%; right: 15%;"></div><div class="stalk" style="height: 80%; right: 5%;"></div></div>
        <div class="bg-ground"></div>
        <div class="bg-effects" id="ambient-effects"></div>
    </div>

    <div class="header">
        <div class="user-info-block">
            <div class="avatar-wrap" onclick="switchTab('profile', document.querySelectorAll('.nav-btn')[5])">
                <div class="avatar-frame default" id="header-frame"></div>
                <div class="profile-avatar-mini" id="mini-avatar"><span>🐼</span></div>
            </div>
            <div>
                <div class="name-medal-block" onclick="switchTab('profile', document.querySelectorAll('.nav-btn')[5])">
                    <div class="name-row"><span class="header-nick nick-default" id="my-name">Ник</span><div class="header-medal" id="header-medal" style="display:none;"></div></div>
                    <div class="streak-badge" id="streak-badge" style="font-size:10px; color:#ff6b00; font-weight:900; margin-top:2px;">🔥 Серия: 0</div>
                </div>
                <div class="res-row">
                    <div class="coins-box"><span id="coins">0</span> <span class="icon-coin">$</span></div>
                    <div class="gems-box" onclick="switchTab('shop', document.querySelectorAll('.nav-btn')[4])"><span id="gems">0</span> <span class="icon-gem">💎</span></div>
                </div>
            </div>
        </div>
        <div class="energy-box"><div style="font-size:10px; font-weight:700;"><span id="energy">1000</span>/<span id="max-energy">1000</span> ⚡</div><div class="energy-bar"><div class="energy-fill" id="energy-fill"></div></div><div style="font-size:10px; color:#fff; margin-top:5px;" id="conn-status">Подключение...</div></div>
    </div>

    <div class="screens">
        <div class="screen active" id="screen-tap">
            <div class="tap-area">
                <div style="text-align: center; position: relative;">
                    <div class="panda-wrapper" id="panda-wrapper">
                        <svg viewBox="0 0 200 220" style="width:100%; height:100%; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));">
                            <ellipse cx="100" cy="205" rx="75" ry="15" fill="rgba(0,0,0,0.35)" />
                            <ellipse cx="55" cy="175" rx="24" ry="18" fill="#1a1a1a" /><ellipse cx="145" cy="175" rx="24" ry="18" fill="#1a1a1a" />
                            <ellipse cx="100" cy="140" rx="62" ry="55" fill="#fff" />
                            <circle cx="45" cy="45" r="20" fill="#1a1a1a" /><circle cx="155" cy="45" r="20" fill="#1a1a1a" />
                            <ellipse cx="100" cy="90" rx="65" ry="58" fill="#fff" />
                            <ellipse cx="70" cy="85" rx="18" ry="23" fill="#111" /><ellipse cx="130" cy="85" rx="18" ry="23" fill="#111" />
                            <circle cx="70" cy="85" r="9" fill="#fff" /><circle cx="70" cy="85" r="6" fill="#111" />
                            <circle cx="130" cy="85" r="9" fill="#fff" /><circle cx="130" cy="85" r="6" fill="#111" />
                            <ellipse cx="45" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
                            <ellipse cx="155" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
                            <path id="mouth-path" d="M 92 112 Q 100 118 108 112" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" />
                            <ellipse cx="100" cy="105" rx="8" ry="5" fill="#111" />
                            <ellipse cx="45" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="155" cy="145" rx="18" ry="22" fill="#1a1a1a" />
                        </svg>
                    </div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-friends">
            <div class="content" id="friends-content" style="padding: 0; background: transparent; backdrop-filter: none;">
                
                <!-- Default view (not in lobby) -->
                <div id="default-friends-view" style="padding: 15px; background: rgba(10,18,14,0.95); backdrop-filter: blur(10px); height: 100%;">
                    <div class="section-title">Друзья 👥</div>
                    <div class="tabs-sub" style="display:flex; gap:10px; margin-bottom:15px;">
                        <button class="tab-btn active" onclick="switchFriendsTab('list', this)">Мои друзья</button>
                        <button class="tab-btn" onclick="switchFriendsTab('top', this)">Топ 50</button>
                    </div>

                    <div id="friends-list-container">
                        <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <input type="text" id="search-input" placeholder="Ник или ID..." style="flex:1; padding:10px; border-radius:8px; border:none; background:rgba(255,255,255,0.1); color:#fff;">
                            <button onclick="searchPlayers()" style="background:#2196f3; color:#fff; border:none; padding:10px 15px; border-radius:8px; font-weight:900; cursor:pointer;">Найти</button>
                        </div>
                        <div id="search-results" class="friend-list"></div>
                        <div class="friend-list" id="friends-list" style="margin-top:20px;"><p style="text-align:center; color:#888;">Загрузка...</p></div>
                    </div>

                    <div id="leaderboard-container" style="display:none;">
                        <div id="leaderboard-list"></div>
                    </div>
                </div>

                <!-- Lobby Active View -->
                <div id="lobby-active-view" class="lobby-active-view">
                    <div class="section-title" style="color:#ffd700; margin-bottom:0; padding-top:15px; text-shadow: 2px 2px 4px #000;">Наше Лобби 🏠</div>
                    <p style="font-size:12px; color:#ddd; text-shadow: 1px 1px 2px #000;">Уровень Дома: <span id="house-level-text">1</span></p>
                    
                    <div id="room-bg" class="room-container house-bg-1">
                        <div class="duo-panda" id="duo-me" onclick="lobbyTap('me', event)">
                            <div id="lobby-my-svg"></div>
                            <div class="duo-name" id="lobby-my-name">Ты</div>
                        </div>
                        <div class="duo-panda" id="duo-partner" onclick="lobbyTap('partner', event)">
                            <div id="lobby-partner-svg"></div>
                            <div class="duo-name" id="lobby-partner-name">Партнер</div>
                        </div>
                        <!-- Baby will be inserted here -->
                        <div class="duo-panda baby" id="duo-baby" style="display:none;" onclick="lobbyTap('baby', event)">
                            <div class="baby-mood" id="baby-mood-icon" style="display:none;">😭</div>
                            <div id="lobby-baby-svg"></div>
                            <div class="duo-name">Малыш</div>
                        </div>
                    </div>

                    <div style="width: 100%; padding: 0 15px;">
                        <div id="pregnancy-alert" class="pregnancy-alert" style="display:none;">
                            🤰 Панда беременна! Осталось: <span id="preg-time">0</span> сек.
                        </div>

                        <div class="baby-stats" id="baby-care" style="display:none;">
                            <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:900;">
                                <span>Сытость малыша</span>
                                <span id="baby-hunger-text">100%</span>
                            </div>
                            <div class="baby-bar-bg"><div class="baby-bar-fill" id="baby-hunger-bar"></div></div>
                        </div>

                        <div class="card" style="margin-top: 15px; padding: 10px; background: rgba(10,18,14,0.9);">
                            <button class="card-price" style="background:#ff9800; color:#fff; margin-bottom:8px;" onclick="hugPartner()">Обнять 🤗 (+1000)</button>
                            
                            <button id="btn-make-baby" class="card-price" style="background:#ff69b4; color:#fff; margin-bottom:8px; display:none;" onclick="makePregnant()">Забеременеть 🤰</button>
                            
                            <button id="btn-feed-baby" class="card-price" style="background:#4caf50; color:#fff; margin-bottom:8px; display:none;" onclick="feedBaby()">Покормить (10,000)</button>

                            <button class="card-price" style="background:#e53935; color:#fff;" onclick="leaveLobby()">Выйти из лобби</button>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <div class="screen" id="screen-farm">
            <div class="content">
                <div class="section-title">Ферма бамбука 🎋</div>
                <div class="grid" id="farm-grid"></div>
            </div>
        </div>

        <div class="screen" id="screen-casino">
            <div class="content">
                <div class="section-title">Казино 🎰</div>
                <div class="casino-box">
                    <div class="wheel-container">
                        <div class="wheel-pointer">▼</div>
                        <div class="wheel" id="casino-wheel"></div>
                    </div>
                    <div class="bet-buttons" id="bet-buttons">
                        <div class="bet-btn" onclick="setBet(1000)">1K</div>
                        <div class="bet-btn active" onclick="setBet(10000)">10K</div>
                        <div class="bet-btn" onclick="setBet(100000)">100K</div>
                    </div>
                    <button class="card-price" id="spin-btn" style="background:#e53935; color:#fff; margin-top:20px; font-size:18px; padding:15px;" onclick="spinCasino()">Крутить!</button>
                    <div id="casino-result" style="margin-top: 15px; font-size: 20px; font-weight: 900; height: 24px;"></div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-shop">
            <div class="content">
                <div class="section-title">Магазин 🛍️</div>
                
                <div class="section-title" style="font-size:14px; color:#aaa; text-align:left;">Дом</div>
                <div class="card" style="margin-bottom:15px;">
                    <div class="card-icon">🏠</div>
                    <div class="card-title">Улучшить Дом (Ур. <span id="shop-house-level">1</span>)</div>
                    <div class="card-desc">Дает уют в лобби</div>
                    <button id="shop-btn-upgrade-house" class="card-price" onclick="upgradeHouse()">Нужно лобби</button>
                </div>

                <div class="section-title" style="font-size:14px; color:#aaa; text-align:left;">Улучшения</div>
                <div class="grid" id="upgrades-grid"></div>
                <div class="section-title" style="font-size:14px; color:#aaa; text-align:left; margin-top:20px;">Гемы 💎</div>
                <div class="grid">
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">100 Гемов</div><button class="card-price" onclick="buyGems(50)">50 ⭐</button></div>
                    <div class="card"><div class="card-icon">💎</div><div class="card-title">500 Гемов</div><button class="card-price" onclick="buyGems(200)">200 ⭐</button></div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-profile">
            <div class="content">
                <div class="profile-card">
                    <div style="position: relative; width: 90px; height: 90px; display: flex; justify-content: center; align-items: center; margin-bottom: 10px;">
                        <div class="avatar-frame default" id="profile-frame"></div>
                        <div id="my-avatar-large" class="profile-avatar-large">🐼</div>
                    </div>
                    <div id="my-name-profile" class="nick-default" style="font-size: 22px; font-weight: 900; margin-bottom: 5px; z-index: 2;">Загрузка...</div>
                    <div style="font-size:16px; font-weight:900; margin-bottom:5px; z-index:2;">ID: <span id="my-game-id" onclick="copyId()" style="color:#00e5ff; text-decoration:underline; cursor:pointer;">...</span></div>
                    
                    <div style="margin-top:10px; margin-bottom:10px;">
                        <button class="card-price" style="width:auto; padding:5px 15px; background:#555;" onclick="toggleGender()">Сменить пол (Текущий: <span id="my-gender">...</span>)</button>
                    </div>

                    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 10px; font-size: 12px; color: #aaa; width: 100%;">
                        <div>Монеты <span id="stat-coins" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                        <div>Гемы <span id="stat-gems" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                        <div>Подарки <span id="stat-gifts" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                    </div>
                </div>
                <div class="section-title">Стиль ника</div>
                <div class="inventory-grid" id="anims-grid"></div>
                <div class="section-title">Мои медали</div>
                <div class="inventory-grid" id="medals-grid"></div>
                <div class="section-title">Мои рамки</div>
                <div class="inventory-grid" id="frames-grid"></div>
            </div>
        </div>
    </div>

    <div class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('tap', this)"><span>👆</span>Панда</button>
        <button class="nav-btn" onclick="switchTab('friends', this)"><span>👥</span>Друзья</button>
        <button class="nav-btn" onclick="switchTab('farm', this)"><span>🌱</span>Ферма</button>
        <button class="nav-btn" onclick="switchTab('casino', this)"><span>🎰</span>Казино</button>
        <button class="nav-btn" onclick="switchTab('shop', this)"><span>🛍️</span>Магазин</button>
        <button class="nav-btn" onclick="switchTab('profile', this)"><span>👤</span>Профиль</button>
    </div>

    <!-- Modals ... (same as previous) -->
    <div class="modal" id="view-profile-modal">
        <div class="modal-box" style="text-align:center;">
            <div style="position: relative; width: 90px; height: 90px; display: flex; justify-content: center; align-items: center; margin:0 auto 10px;">
                <div class="avatar-frame default" id="vp-frame"></div>
                <div class="profile-avatar-large" id="vp-avatar">🐼</div>
            </div>
            <div class="profile-name" id="vp-name" style="font-size:22px; font-weight:900; margin-bottom:5px;">Ник</div>
            <div style="font-size:16px; font-weight:900; margin-bottom:5px;">ID: <span id="vp-id" style="color:#00e5ff;">...</span></div>
            <div class="medal-emoji large" id="vp-medal" style="display:none; margin:0 auto 10px;"></div>
            
            <div style="display: flex; justify-content: center; gap: 20px; margin-top: 15px; font-size: 12px; color: #aaa; width: 100%; margin-bottom: 15px;">
                <div>Монеты <span id="vp-coins" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                <div>Гемы <span id="vp-gems" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                <div>Подарки <span id="vp-gifts" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
            </div>
            
            <button class="card-price" style="background:#ff9800; color:#fff; margin-bottom:10px;" onclick="openGiftModal()">Подарить 🎁</button>
            <button class="card-price" style="background:#2196f3; color:#fff; margin-bottom:10px;" onclick="showGiftHistory()">История подарков</button>
            <button class="card-price" style="background:#4caf50; color:#fff; margin-bottom:10px;" onclick="inviteToLobby()">Пригласить в Лобби</button>
            <button class="card-price" style="background:#555; color:#fff;" onclick="document.getElementById('view-profile-modal').classList.remove('active')">Закрыть</button>
        </div>
    </div>

    <div class="modal" id="gift-modal">
        <div class="modal-box" style="text-align:center;">
            <h2 style="color:#ffd700; margin-bottom:15px;">Подарить подарок</h2>
            <div style="display:flex; justify-content:space-around; margin-bottom:20px;">
                <div onclick="sendGift('🌹', 10)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🌹</div><div style="font-size:10px; color:#00e5ff;">10 💎</div></div>
                <div onclick="sendGift('🎂', 50)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🎂</div><div style="font-size:10px; color:#00e5ff;">50 💎</div></div>
                <div onclick="sendGift('🧸', 100)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">🧸</div><div style="font-size:10px; color:#00e5ff;">100 💎</div></div>
                <div onclick="sendGift('👑', 500)" style="cursor:pointer; text-align:center;"><div style="font-size:30px;">👑</div><div style="font-size:10px; color:#00e5ff;">500 💎</div></div>
            </div>
            <button class="card-price" style="background:#555; color:#fff;" onclick="document.getElementById('gift-modal').classList.remove('active')">Отмена</button>
        </div>
    </div>

    <div class="modal" id="gift-history-modal">
        <div class="modal-box">
            <h2 style="color:#ffd700; margin-bottom:15px;">История подарков</h2>
            <div id="gift-history-list" style="max-height:200px; overflow-y:auto; text-align:left; margin-bottom:15px;"></div>
            <button class="card-price" style="background:#555; color:#fff;" onclick="document.getElementById('gift-history-modal').classList.remove('active')">Закрыть</button>
        </div>
    </div>

    <div class="modal" id="invite-modal">
        <div class="modal-box">
            <h2 style="color:#ffd700; margin-bottom:15px;">Приглашение в Лобби</h2>
            <p id="invite-text" style="margin-bottom:20px; font-size:16px;">Игрок приглашает вас!</p>
            <button class="card-price" style="background:#4caf50; color:#fff; margin-bottom:10px;" onclick="acceptInvite()">Принять</button>
            <button class="card-price" style="background:#e53935; color:#fff;" onclick="document.getElementById('invite-modal').classList.remove('active')">Отклонить</button>
        </div>
    </div>

    <script>
        window.onerror = function(msg, url, line) { return false; };
        const tg = window.Telegram.WebApp; tg.expand();
        const myId = String(tg.initDataUnsafe?.user?.id || Math.floor(Math.random() * 10000));
        const WS_URL = window.location.origin.replace('https://', 'wss://');
        
        const pandaSVG = `<svg viewBox="0 0 200 220" style="width:100%; height:100%; filter: drop-shadow(0 10px 15px rgba(0,0,0,0.5));">
            <ellipse cx="100" cy="205" rx="75" ry="15" fill="rgba(0,0,0,0.35)" />
            <ellipse cx="55" cy="175" rx="24" ry="18" fill="#1a1a1a" /><ellipse cx="145" cy="175" rx="24" ry="18" fill="#1a1a1a" />
            <ellipse cx="100" cy="140" rx="62" ry="55" fill="#fff" />
            <circle cx="45" cy="45" r="20" fill="#1a1a1a" /><circle cx="155" cy="45" r="20" fill="#1a1a1a" />
            <ellipse cx="100" cy="90" rx="65" ry="58" fill="#fff" />
            <ellipse cx="70" cy="85" rx="18" ry="23" fill="#111" /><ellipse cx="130" cy="85" rx="18" ry="23" fill="#111" />
            <circle cx="70" cy="85" r="9" fill="#fff" /><circle cx="70" cy="85" r="6" fill="#111" />
            <circle cx="130" cy="85" r="9" fill="#fff" /><circle cx="130" cy="85" r="6" fill="#111" />
            <ellipse cx="45" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
            <ellipse cx="155" cy="105" rx="14" ry="8" fill="rgba(255,100,150,0.5)" />
            <path id="mouth-path" d="M 92 112 Q 100 118 108 112" fill="none" stroke="#111" stroke-width="2" stroke-linecap="round" />
            <ellipse cx="100" cy="105" rx="8" ry="5" fill="#111" />
            <ellipse cx="45" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="155" cy="145" rx="18" ry="22" fill="#1a1a1a" />
        </svg>`;

        let ws;
        let state = { coins: 500, gems: 0, tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 1, upgrades: { tap: 0, max_energy: 0, regen: 0 }, bamboos: [{ id: 1, stage: 0, planted: 0 }, { id: 2, stage: 0, planted: 0 }, { id: 3, stage: 0, planted: 0 }], nickname: '', selectedMedal: 'none', selectedFrame: 'default', selectedNickAnim: 'default', avatarUrl: tg.initDataUnsafe?.user?.photo_url || '', gameId: '', unlockedMedals: [], unlockedFrames: ['default'], unlockedAnims: ['default'], friends: [], lobby_partner: null, lobby_partner_name: null, gifts: 0, gift_history: [], gender: 'male', house_level: 1, is_pregnant: false, pregnancy_end: 0, has_baby: false, baby_hunger: 100 };
        
        let currentBet = 10000;
        let isSpinning = false;
        let currentViewPlayerId = null;
        let currentInviterId = null;
        let currentFriendProfileData = null;

        const allMedals = [{ id: 'bronze', name: 'Бронза', req: 30, emoji: '🥉' }, { id: 'silver', name: 'Серебро', req: 90, emoji: '🥈' }, { id: 'gold', name: 'Золото', req: 180, emoji: '🥇' }, { id: 'epic', name: 'Эпик', req: 365, emoji: '💎' }, { id: 'mythic', name: 'Мифик', req: 730, emoji: '👑' }];
        const allFrames = [{ id: 'default', name: 'Новичок', cssClass: 'default', price: 0 }, { id: 'millionaire', name: 'Богач', cssClass: 'millionaire', price: 0 }, { id: 'legend', name: 'Легенда', cssClass: 'legend', price: 0 }, { id: 'neon', name: 'Неон', cssClass: 'neon', price: 50000 }, { id: 'nature', name: 'Природа', cssClass: 'nature', price: 75000 }, { id: 'fire', name: 'Огонь', cssClass: 'fire', price: 100000 }];
        const allAnims = [{ id: 'default', name: 'Обычный', cssClass: 'nick-default' }, { id: 'gold', name: 'Золото', cssClass: 'nick-gold' }, { id: 'fire', name: 'Огонь', cssClass: 'nick-fire' }, { id: 'rainbow', name: 'Радуга', cssClass: 'nick-rainbow' }];

        function spawnAmbient() {
            const container = document.getElementById('ambient-effects');
            if(!container) return;
            setInterval(() => {
                const isFirefly = Math.random() > 0.5;
                const el = document.createElement('div');
                if (isFirefly) {
                    el.className = 'firefly';
                    el.style.left = Math.random() * 100 + '%';
                    el.style.top = Math.random() * 100 + '%';
                    el.style.animationDuration = (Math.random() * 3 + 2) + 's';
                } else {
                    el.className = 'butterfly';
                    el.innerText = ['🦋', '🦋', '🌸'][Math.floor(Math.random() * 3)];
                    el.style.left = '-50px';
                    el.style.top = Math.random() * 80 + 10 + '%';
                    el.style.animationDuration = (Math.random() * 5 + 4) + 's';
                }
                container.appendChild(el);
                setTimeout(() => el.remove(), isFirefly ? 5000 : 9000);
            }, 1500);
        }

        function connectWS() {
            ws = new WebSocket(`${WS_URL}/ws/main/${myId}`);
            ws.onopen = () => { 
                document.getElementById('conn-status').innerText = "🟢 Онлайн"; 
                ws.send(JSON.stringify({ type: "init" })); 
                if (state.avatarUrl) ws.send(JSON.stringify({ type: "update_avatar", avatar: state.avatarUrl }));
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'sync') {
                    state = { ...state, ...data.data };
                    if (!state.nickname) state.nickname = state.name || 'Panda';
                    updateUI();
                } else if (data.type === 'casino_result') {
                    isSpinning = false;
                    document.getElementById('spin-btn').classList.remove('disabled');
                    document.getElementById('bet-buttons').classList.remove('disabled');
                    
                    const wheel = document.getElementById('casino-wheel');
                    let targetDeg = 1800; 
                    if(data.multiplier === 0) targetDeg += 120; 
                    if(data.multiplier === 1.5) targetDeg += 240; 
                    if(data.multiplier === 2) targetDeg += 60; 
                    if(data.multiplier === 5) targetDeg += 300; 
                    if(data.multiplier === 10) targetDeg += 180; 
                    
                    wheel.style.transform = `rotate(${targetDeg}deg)`;
                    
                    setTimeout(() => {
                        document.getElementById('casino-result').innerText = data.text;
                        document.getElementById('casino-result').style.color = data.win ? '#4caf50' : '#e53935';
                        state.coins = data.newCoins;
                        updateUI();
                    }, 4000);
                    
                } else if (data.type === 'error') {
                    isSpinning = false;
                    document.getElementById('spin-btn').classList.remove('disabled');
                    document.getElementById('bet-buttons').classList.remove('disabled');
                    tg.showAlert(data.message);
                } else if (data.type === 'lobby_invite') {
                    currentInviterId = data.from_id;
                    document.getElementById('invite-text').innerText = `${data.from_name} приглашает вас в лобби!`;
                    document.getElementById('invite-modal').classList.add('active');
                } else if (data.type === 'lobby_joined') {
                    state.lobby_partner = data.partner_id;
                    state.lobby_partner_name = data.partner_name;
                    tg.showAlert(`Вы в лобби с ${data.partner_name}!`);
                    updateUI();
                    switchTab('friends', document.querySelectorAll('.nav-btn')[1]);
                } else if (data.type === 'gift_received') {
                    tg.showAlert(`🎁 Тебе подарили ${data.gift} от ${data.from_name}!`);
                } else if (data.type === 'hug_received') {
                    tg.showAlert(`🤗 ${data.from_name} тебя обнял! Ты получил 1000 монет бонусом!`);
                    state.coins += 1000;
                    updateUI();
                }
            };
            ws.onclose = () => { document.getElementById('conn-status').innerText = "🔴 Оффлайн"; setTimeout(connectWS, 2000); };
        }

        document.getElementById('panda-wrapper').addEventListener('pointerdown', (e) => {
            if (state.energy <= 0) return;
            state.energy -= 1; state.coins += state.tapPower;
            const p = document.getElementById('panda-wrapper');
            p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
            const coin = document.createElement('div'); coin.className = 'particle-coin'; coin.innerText = `+${state.tapPower}`;
            coin.style.left = (e.clientX - 15) + 'px'; coin.style.top = (e.clientY - 20) + 'px';
            document.body.appendChild(coin); setTimeout(() => coin.remove(), 900);
            if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "tap", power: state.tapPower }));
            updateUI();
        });

        function lobbyTap(who, e) {
            const p = e.currentTarget;
            p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
            
            const particle = document.createElement('div');
            particle.className = 'particle-heart';
            particle.innerText = who === 'baby' ? '🍼' : '❤️';
            particle.style.left = (e.clientX - 15) + 'px'; 
            particle.style.top = (e.clientY - 20) + 'px';
            document.body.appendChild(particle); 
            setTimeout(() => particle.remove(), 1000);
        }

        function updateUI() {
            if(document.getElementById('coins')) document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString();
            if(document.getElementById('gems')) document.getElementById('gems').innerText = Math.floor(state.gems).toLocaleString();
            if(document.getElementById('energy')) document.getElementById('energy').innerText = Math.floor(state.energy);
            if(document.getElementById('max-energy')) document.getElementById('max-energy').innerText = state.maxEnergy;
            if(document.getElementById('energy-fill')) document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            
            const frame = allFrames.find(f => f.id === state.selectedFrame)?.cssClass || 'default';
            const animCss = allAnims.find(a => a.id === state.selectedNickAnim)?.cssClass || 'nick-default';
            
            if(document.getElementById('header-frame')) document.getElementById('header-frame').className = `avatar-frame ${frame}`;
            if(document.getElementById('my-name')) { document.getElementById('my-name').className = `header-nick ${animCss}`; document.getElementById('my-name').innerText = state.nickname; }
            if(document.getElementById('profile-frame')) document.getElementById('profile-frame').className = `avatar-frame ${frame}`;
            if(document.getElementById('my-name-profile')) { document.getElementById('my-name-profile').className = `${animCss}`; document.getElementById('my-name-profile').innerText = state.nickname; }
            
            if(document.getElementById('my-game-id')) document.getElementById('my-game-id').innerText = state.gameId || '...';
            if(document.getElementById('my-gender')) document.getElementById('my-gender').innerText = state.gender === 'male' ? 'Мужской 👦' : 'Женский 👧';
            
            const med = allMedals.find(m => m.id === state.selectedMedal);
            if(document.getElementById('header-medal')) {
                if (med) { document.getElementById('header-medal').style.display = 'inline-flex'; document.getElementById('header-medal').innerText = med.emoji; } 
                else document.getElementById('header-medal').style.display = 'none'; 
            }
            
            if (state.avatarUrl) {
                if(document.getElementById('mini-avatar')) document.getElementById('mini-avatar').innerHTML = `<img src="${state.avatarUrl}" style="width:100%;height:100%;object-fit:cover;display:block;">`;
                if(document.getElementById('my-avatar-large')) document.getElementById('my-avatar-large').innerHTML = `<img src="${state.avatarUrl}" style="width:100%;height:100%;object-fit:cover;display:block;">`;
            } else {
                if(document.getElementById('mini-avatar')) document.getElementById('mini-avatar').innerHTML = `<span>🐼</span>`;
                if(document.getElementById('my-avatar-large')) document.getElementById('my-avatar-large').innerHTML = `🐼`;
            }

            if(document.getElementById('stat-coins')) document.getElementById('stat-coins').innerText = Math.floor(state.coins).toLocaleString();
            if(document.getElementById('stat-gems')) document.getElementById('stat-gems').innerText = Math.floor(state.gems).toLocaleString();
            if(document.getElementById('stat-gifts')) document.getElementById('stat-gifts').innerText = state.gifts || 0;

            const u = state.upgrades || {tap:0, max_energy:0, regen:0};
            const shopHTML = `
                <div class="card">
                    <div class="card-icon">🐾</div><div class="card-title">Сила (Ур.${u.tap})</div>
                    <button class="card-price" onclick="buyUpgrade('tap')">${Math.floor(100 * Math.pow(1.5, u.tap))} $</button>
                </div>
                <div class="card">
                    <div class="card-icon">⚡</div><div class="card-title">Энергия (Ур.${u.max_energy})</div>
                    <button class="card-price" onclick="buyUpgrade('max_energy')">${Math.floor(500 * Math.pow(1.6, u.max_energy))} $</button>
                </div>
                <div class="card">
                    <div class="card-icon">🍃</div><div class="card-title">Реген (Ур.${u.regen})</div>
                    <button class="card-price" onclick="buyUpgrade('regen')">${Math.floor(1000 * Math.pow(1.8, u.regen))} $</button>
                </div>
            `;
            if(document.getElementById('upgrades-grid')) document.getElementById('upgrades-grid').innerHTML = shopHTML;

            // House in Shop
            if(document.getElementById('shop-house-level')) document.getElementById('shop-house-level').innerText = state.house_level;
            const shopHouseBtn = document.getElementById('shop-btn-upgrade-house');
            if (shopHouseBtn) {
                if (!state.lobby_partner) {
                    shopHouseBtn.innerText = "Нужно лобби";
                    shopHouseBtn.style.background = "#555";
                    shopHouseBtn.onclick = () => tg.showAlert("Сначала создайте лобби с другом!");
                } else if (state.house_level >= 3) {
                    shopHouseBtn.innerText = "Макс. уровень";
                    shopHouseBtn.style.background = "#4caf50";
                    shopHouseBtn.onclick = null;
                } else {
                    const hCost = state.house_level * 50000;
                    shopHouseBtn.innerText = `${hCost.toLocaleString()} $`;
                    shopHouseBtn.style.background = "#2196f3";
                    shopHouseBtn.onclick = upgradeHouse;
                }
            }

            if(document.getElementById('anims-grid')) {
                let aHtml = '';
                allAnims.forEach(a => {
                    const o = state.unlockedAnims.includes(a.id);
                    const s = state.selectedNickAnim === a.id;
                    aHtml += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('NickAnim','${a.id}')" style="${o?'':'opacity:0.3;'}"><div class="inv-icon ${a.cssClass}" style="font-weight:900; font-size:20px; filter:none;">Aa</div><div style="font-size:10px;">${a.name}</div></div>`;
                });
                document.getElementById('anims-grid').innerHTML = aHtml;
            }
            if(document.getElementById('medals-grid')) {
                let mHtml = '';
                allMedals.forEach(m => {
                    const o = state.unlockedMedals.includes(m.id);
                    const s = state.selectedMedal === m.id;
                    mHtml += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('Medal','${m.id}')" style="${o?'':'opacity:0.3;'}"><div class="medal-emoji">${m.emoji}</div><div style="font-size:10px;">${m.name}</div></div>`;
                });
                document.getElementById('medals-grid').innerHTML = mHtml;
            }
            if(document.getElementById('frames-grid')) {
                let fHtml = '';
                allFrames.forEach(f => {
                    const o = state.unlockedFrames.includes(f.id);
                    const s = state.selectedFrame === f.id;
                    fHtml += `<div class="inv-item ${o?'owned':''} ${s?'selected':''}" onclick="equip('Frame','${f.id}')" style="${o?'':'opacity:0.3;'}"><div class="inv-icon" style="border:4px solid #fff; border-radius:50%; width:30px; height:30px; margin:0 auto; ${f.id==='millionaire'?'border-color:#ffd700; box-shadow:0 0 10px #ffd700;':f.id==='legend'?'border-color:#00e5ff; box-shadow:0 0 15px #00e5ff;':f.id==='neon'?'border-color:#ff00ff; box-shadow:0 0 10px #ff00ff;':f.id==='nature'?'border-color:#8bc34a; box-shadow:0 0 10px #8bc34a;':f.id==='fire'?'border-color:#ff5722; box-shadow:0 0 10px #ff5722;':''}"></div><div style="font-size:10px;">${f.name}</div></div>`;
                });
                document.getElementById('frames-grid').innerHTML = fHtml;
            }
            
            renderLobbyUI();
        }

        function renderLobbyUI() {
            if (state.lobby_partner) {
                document.getElementById('default-friends-view').style.display = 'none';
                document.getElementById('lobby-active-view').style.display = 'flex';
                
                document.getElementById('lobby-my-name').innerText = state.nickname;
                document.getElementById('lobby-partner-name').innerText = state.lobby_partner_name || 'Партнер';
                
                if (!document.getElementById('lobby-my-svg').hasChildNodes()) document.getElementById('lobby-my-svg').innerHTML = pandaSVG;
                if (!document.getElementById('lobby-partner-svg').hasChildNodes()) document.getElementById('lobby-partner-svg').innerHTML = pandaSVG;
                if (!document.getElementById('lobby-baby-svg').hasChildNodes()) document.getElementById('lobby-baby-svg').innerHTML = pandaSVG;

                const roomBg = document.getElementById('room-bg');
                roomBg.className = `room-container house-bg-${state.house_level}`;
                document.getElementById('house-level-text').innerText = state.house_level;

                const pregAlert = document.getElementById('pregnancy-alert');
                const babyCare = document.getElementById('baby-care');
                const babyVisual = document.getElementById('duo-baby');
                const btnMakeBaby = document.getElementById('btn-make-baby');
                const btnFeedBaby = document.getElementById('btn-feed-baby');
                const babyMoodIcon = document.getElementById('baby-mood-icon');

                if (state.has_baby) {
                    babyVisual.style.display = 'flex';
                    babyCare.style.display = 'block';
                    pregAlert.style.display = 'none';
                    btnMakeBaby.style.display = 'none';
                    btnFeedBaby.style.display = 'block';
                    
                    document.getElementById('baby-hunger-text').innerText = state.baby_hunger + '%';
                    document.getElementById('baby-hunger-bar').style.width = state.baby_hunger + '%';
                    
                    if (state.baby_hunger < 30) {
                        babyMoodIcon.style.display = 'block';
                        babyMoodIcon.innerText = '😭';
                    } else {
                        babyMoodIcon.style.display = 'none';
                    }
                } else if (state.is_pregnant) {
                    babyVisual.style.display = 'none';
                    babyCare.style.display = 'none';
                    btnMakeBaby.style.display = 'none';
                    btnFeedBaby.style.display = 'none';
                    
                    pregAlert.style.display = 'block';
                    const left = Math.max(0, Math.floor((state.pregnancy_end - Date.now())/1000));
                    document.getElementById('preg-time').innerText = left;
                    if(left === 0) {
                        if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "check_baby" }));
                    }
                } else {
                    babyVisual.style.display = 'none';
                    babyCare.style.display = 'none';
                    pregAlert.style.display = 'none';
                    
                    if (state.gender === 'female') {
                        btnMakeBaby.style.display = 'block';
                        btnMakeBaby.innerText = "Забеременеть 🤰";
                        btnMakeBaby.onclick = makePregnant;
                        btnMakeBaby.disabled = false;
                        btnMakeBaby.style.background = "#ff69b4";
                    } else {
                        btnMakeBaby.style.display = 'block';
                        btnMakeBaby.innerText = "Ждем потомство от партнера...";
                        btnMakeBaby.disabled = true;
                        btnMakeBaby.style.background = "#555";
                    }
                    
                    btnFeedBaby.style.display = 'none';
                }

            } else {
                document.getElementById('default-friends-view').style.display = 'block';
                document.getElementById('lobby-active-view').style.display = 'none';
            }
        }

        function copyId() {
            const idText = state.gameId;
            const idEl = document.getElementById('my-game-id');
            if (navigator.clipboard) {
                navigator.clipboard.writeText(idText).then(() => {
                    idEl.innerText = "✅ Скопировано!";
                    setTimeout(() => idEl.innerText = idText, 1500);
                });
            }
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            if (tabId === 'friends') { fetchFriends(); renderLobbyUI(); }
            if (tabId === 'farm') renderFarm();
        }

        function switchFriendsTab(tab, btn) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            if (tab === 'list') {
                document.getElementById('friends-list-container').style.display = 'block';
                document.getElementById('leaderboard-container').style.display = 'none';
                fetchFriends();
            } else {
                document.getElementById('friends-list-container').style.display = 'none';
                document.getElementById('leaderboard-container').style.display = 'block';
                fetchLeaderboard();
            }
        }

        function renderFarm() {
            const grid = document.getElementById('farm-grid'); if(!grid) return;
            grid.innerHTML = '';
            state.bamboos.forEach(b => {
                let s = "Пусто", btn = "Посадить", icon = "🟫", dis = false;
                if (b.stage === 1) {
                    const t = Math.ceil((60000 - (Date.now() - b.planted)) / 1000);
                    s = t > 0 ? `Растет... ${t}с` : "Созрел!";
                    btn = "Ждем"; icon = "🌱"; dis = t > 0;
                } else if (b.stage === 2) {
                    s = "Созрел!"; btn = "Собрать"; icon = "🎋";
                } else if (b.stage === 3) {
                    s = "Сгнил!"; btn = "Убрать"; icon = "🥀";
                }
                grid.innerHTML += `<div class="card"><div class="card-icon">${icon}</div><div class="card-title">Участок ${b.id}</div><div class="card-desc">${s}</div><button class="card-price" ${dis ? 'disabled' : ''} onclick="handleFarmClick(${b.id})">${btn}</button></div>`;
            });
        }

        function handleFarmClick(id) {
            const b = state.bamboos.find(x => x.id === id);
            if (b.stage === 0) { b.planted = Date.now(); b.stage = 1; }
            else if (b.stage === 2) { state.coins += 500; b.stage = 0; tg.showAlert("+500 монет!"); }
            else if (b.stage === 3) { b.stage = 0; }
            updateUI();
            if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "farm_click", id: id }));
        }

        function buyUpgrade(type) {
            const u = state.upgrades;
            let cost = 0;
            if(type==='tap') cost = Math.floor(100 * Math.pow(1.5, u.tap));
            if(type==='max_energy') cost = Math.floor(500 * Math.pow(1.6, u.max_energy));
            if(type==='regen') cost = Math.floor(1000 * Math.pow(1.8, u.regen));
            
            if(state.coins >= cost) {
                state.coins -= cost; u[type]++;
                if(type==='tap') state.tapPower++;
                if(type==='max_energy') state.maxEnergy += 100;
                if(type==='regen') state.regen++;
                updateUI();
                if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "buy_upgrade", upgrade: type }));
            } else {
                tg.showAlert("Недостаточно монет!");
            }
        }

        function equip(type, id) {
            if(type==='Medal') state.selectedMedal = id;
            if(type==='Frame') state.selectedFrame = id;
            if(type==='NickAnim') state.selectedNickAnim = id;
            updateUI();
            if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "equip", category: type, item_id: id }));
        }

        function toggleGender() {
            if(ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "toggle_gender" }));
        }

        function setBet(amount) {
            if (isSpinning) return;
            currentBet = amount;
            document.querySelectorAll('.bet-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
        }

        function spinCasino() {
            if (isSpinning) return;
            if (state.coins < currentBet) { tg.showAlert("Недостаточно монет!"); return; }
            if (!ws || ws.readyState !== WebSocket.OPEN) { tg.showAlert("Ожидание соединения..."); return; }
            
            isSpinning = true;
            document.getElementById('spin-btn').classList.add('disabled');
            document.getElementById('bet-buttons').classList.add('disabled');
            document.getElementById('casino-result').innerText = "Крутим...";
            document.getElementById('casino-result').style.color = "#fff";

            state.coins -= currentBet;
            updateUI();

            ws.send(JSON.stringify({ type: "casino", bet: currentBet }));
        }

        function buyGems(starsPrice) {
            const gemsAmount = starsPrice * 2;
            fetch(`${window.location.origin}/api/create_invoice`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: myId, stars: starsPrice, gems: gemsAmount })
            }).then(res => res.json()).then(data => {
                if (data.ok) tg.close(); else tg.showAlert("Ошибка при создании счета.");
            }).catch(e => tg.showAlert("Ошибка сети."));
        }
        
        async function searchPlayers() {
            const query = document.getElementById('search-input').value.trim();
            if (!query) return;
            try {
                const res = await fetch(`${window.location.origin}/api/search_players?q=${encodeURIComponent(query)}&my_id=${myId}`);
                const data = await res.json();
                if (data.length === 0) { document.getElementById('search-results').innerHTML = '<p style="text-align:center; color:#888;">Не найдено.</p>'; return; }
                document.getElementById('search-results').innerHTML = data.map(p => `<div class="friend-item" style="background: rgba(33, 150, 243, 0.1); border-color: #2196f3;"><div class="friend-avatar">${p.avatar ? `<img src="${p.avatar}">` : '🐼'}</div><div class="friend-name-box"><div class="friend-name-row"><span>${p.name}</span></div></div><button class="add-friend-btn" style="background:#ff9800; border:none; padding:5px 10px; border-radius:5px; color:#fff; cursor:pointer;" onclick="addFriend('${p.id}')">Заявка</button></div>`).join('');
            } catch(e) {}
        }

        function addFriend(id) {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "add_friend", friend_id: id }));
                tg.showAlert("Заявка отправлена!");
            }
        }
        
        async function fetchFriends() {
            try {
                const res = await fetch(`${window.location.origin}/api/friends/${myId}`);
                const data = await res.json();
                state.friends = data;
                if(data.length > 0) {
                    document.getElementById('friends-list').innerHTML = data.map(f => {
                        const frameData = allFrames.find(fr => fr.id === f.frame) || allFrames[0];
                        const medData = allMedals.find(m => m.id === f.medal);
                        const verifiedIcon = f.verified ? '<span class="verified-badge">✔</span>' : '';
                        const medalHtml = medData ? `<span class="medal-emoji" style="font-size:14px; margin-left:5px;">${medData.emoji}</span>` : '';
                        return `
                        <div class="friend-item" onclick="viewFriendProfile('${f.id}')">
                            <div class="avatar-wrap" style="width:35px; height:35px; margin-right:10px;">
                                <div class="avatar-frame ${frameData.cssClass}" style="inset:-2px; border-width:2px;"></div>
                                <div class="profile-avatar-mini" style="border-width:1px;">${f.avatar ? `<img src="${f.avatar}">` : '🐼'}</div>
                            </div>
                            <div class="friend-name-box">
                                <div class="friend-name-row">
                                    <span class="${f.nick_style}">${f.name}</span>
                                    ${medalHtml} ${verifiedIcon}
                                </div>
                                <div class="friend-sub"><span class="status-dot ${f.online ? 'status-online' : 'status-offline'}"></span> ${f.online ? 'В сети' : 'Не в сети'}</div>
                            </div>
                            <div class="friend-coins">${f.coins.toLocaleString()} <span class="icon-coin">$</span></div>
                        </div>`;
                    }).join('');
                } else {
                    document.getElementById('friends-list').innerHTML = '<p style="text-align:center; color:#888;">Нет друзей.</p>';
                }
            } catch(e) {}
        }

        async function fetchLeaderboard() {
            try {
                const res = await fetch(`${window.location.origin}/api/leaderboard`);
                const data = await res.json();
                document.getElementById('leaderboard-list').innerHTML = data.map((p, i) => {
                    const frameData = allFrames.find(fr => fr.id === p.frame) || allFrames[0];
                    const medData = allMedals.find(m => m.id === p.medal);
                    const verifiedIcon = p.verified ? '<span class="verified-badge">✔</span>' : '';
                    const medalHtml = medData ? `<span class="medal-emoji" style="font-size:14px; margin-left:5px;">${medData.emoji}</span>` : '';
                    return `
                    <div class="friend-item" onclick="viewFriendProfile('${p.id}')">
                        <span style="font-weight:900; color:#ffd700; width:20px;">${i+1}.</span>
                        <div class="avatar-wrap" style="width:35px; height:35px; margin-right:10px;">
                            <div class="avatar-frame ${frameData.cssClass}" style="inset:-2px; border-width:2px;"></div>
                            <div class="profile-avatar-mini" style="border-width:1px;">${p.avatar ? `<img src="${p.avatar}">` : '🐼'}</div>
                        </div>
                        <div class="friend-name-row" style="flex:1;">
                            <span class="${p.nick_style}">${p.name}</span>
                            ${medalHtml} ${verifiedIcon}
                        </div>
                        <span style="color:#ffd700; font-weight:900;">${p.coins.toLocaleString()} $</span>
                    </div>`;
                }).join('');
            } catch(e) {}
        }

        function viewFriendProfile(id) {
            const friend = state.friends.find(f => f.id === id) || window.leaderboardData?.find(p => p.id === id);
            if(!friend) return;
            currentViewPlayerId = id;
            currentFriendProfileData = friend;
            
            document.getElementById('vp-name').innerText = friend.name;
            document.getElementById('vp-name').className = `${friend.nick_style}`;
            document.getElementById('vp-id').innerText = friend.id;
            document.getElementById('vp-coins').innerText = friend.coins.toLocaleString();
            document.getElementById('vp-gems').innerText = friend.gems ? friend.gems.toLocaleString() : '0';
            document.getElementById('vp-gifts').innerText = friend.gifts || 0;
            
            const frameData = allFrames.find(fr => fr.id === friend.frame) || allFrames[0];
            document.getElementById('vp-frame').className = `avatar-frame ${frameData.cssClass}`;
            
            const medData = allMedals.find(m => m.id === friend.medal);
            if(medData) { document.getElementById('vp-medal').style.display = 'block'; document.getElementById('vp-medal').innerText = medData.emoji; }
            else document.getElementById('vp-medal').style.display = 'none';

            if (friend.avatar) document.getElementById('vp-avatar').innerHTML = `<img src="${friend.avatar}" style="width:100%;height:100%;object-fit:cover;">`;
            else document.getElementById('vp-avatar').innerText = '🐼';
            
            document.getElementById('view-profile-modal').classList.add('active');
        }

        function openGiftModal() {
            document.getElementById('gift-modal').classList.add('active');
        }

        function sendGift(emoji, price) {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "send_gift", target_id: currentViewPlayerId, gift: emoji, cost: price }));
                document.getElementById('gift-modal').classList.remove('active');
                tg.showAlert("Подарок отправлен!");
            }
        }

        function showGiftHistory() {
            if(!currentFriendProfileData) return;
            const history = currentFriendProfileData.gift_history || [];
            const listEl = document.getElementById('gift-history-list');
            if (history.length === 0) {
                listEl.innerHTML = '<div style="color:#888; text-align:center;">Подарков пока нет</div>';
            } else {
                listEl.innerHTML = history.map(g => `<div class="gift-history-item"><span class="gift-history-icon">${g.gift}</span> <span>от <b>${g.from}</b></span></div>`).join('');
            }
            document.getElementById('gift-history-modal').classList.add('active');
        }

        function inviteToLobby() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "invite_lobby", friend_id: currentViewPlayerId }));
                document.getElementById('view-profile-modal').classList.remove('active');
                tg.showAlert("Приглашение отправлено! Ждем ответа...");
            }
        }

        function acceptInvite() {
            document.getElementById('invite-modal').classList.remove('active');
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "accept_lobby", inviter_id: currentInviterId }));
            }
        }

        function hugPartner() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "hug_partner" }));
            }
        }

        function leaveLobby() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "leave_lobby" }));
                state.lobby_partner = null;
                state.lobby_partner_name = null;
                updateUI();
            }
        }

        function upgradeHouse() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "upgrade_house" }));
            }
        }

        function makePregnant() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "make_pregnant" }));
            }
        }

        function feedBaby() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "feed_baby" }));
            }
        }

        setInterval(() => {
            if (state.energy < state.maxEnergy) {
                state.energy = Math.min(state.maxEnergy, state.energy + state.regen);
                if(document.getElementById('energy')) document.getElementById('energy').innerText = Math.floor(state.energy);
                if(document.getElementById('energy-fill')) document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            }
            if (document.getElementById('screen-farm').classList.contains('active')) {
                renderFarm();
            }
            if (state.is_pregnant) {
                const left = Math.max(0, Math.floor((state.pregnancy_end - Date.now())/1000));
                if(document.getElementById('preg-time')) document.getElementById('preg-time').innerText = left;
            }
        }, 1000);

        spawnAmbient();
        connectWS();
    </script>
</body>
</html>
"""

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    active_connections[user_id] = websocket
    
    if user_id not in players_db:
        players_db[user_id] = {
            "name": f"Panda_{user_id[:4]}", "coins": 500, "gems": 0, "tapPower": 1, "energy": 1000, "maxEnergy": 1000, "regen": 1,
            "upgrades": {"tap": 0, "max_energy": 0, "regen": 0},
            "bamboos": [{"id": 1, "stage": 0, "planted": 0}, {"id": 2, "stage": 0, "planted": 0}, {"id": 3, "stage": 0, "planted": 0}],
            "selectedMedal": "none", "selectedFrame": "default", "selectedNickAnim": "default",
            "unlockedMedals": [], "unlockedFrames": ["default"], "unlockedAnims": ["default"],
            "friends": [], "verified": True if user_id == ADMIN_ID else False, "last_active": time.time(), 
            "lobby_partner": None, "lobby_partner_name": None, "lobby_partner_avatar": "", "gifts": 0, "gift_history": [],
            "gender": random.choice(["male", "female"]), "house_level": 1, "is_pregnant": False, "pregnancy_end": 0, "has_baby": False, "baby_hunger": 100
        }
    if "game_id" not in players_db[user_id]: 
        players_db[user_id]["game_id"] = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    save_player(user_id, players_db[user_id])
    sync_data = players_db[user_id]
    sync_data["gameId"] = players_db[user_id]["game_id"]
    await websocket.send_text(json.dumps({"type": "sync", "data": sync_data}))

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "update_avatar":
                players_db[user_id]["avatar"] = msg.get("avatar")
                save_player(user_id, players_db[user_id])
                
            elif msg.get("type") == "tap":
                players_db[user_id]["coins"] += msg.get("power", 1)
                players_db[user_id]["energy"] = max(0, players_db[user_id]["energy"] - 1)
                players_db[user_id]["last_active"] = time.time()
                if random.random() < 0.1: save_player(user_id, players_db[user_id])
                
            elif msg.get("type") == "farm_click":
                b_id = msg.get("id")
                for b in players_db[user_id]["bamboos"]:
                    if b["id"] == b_id:
                        if b["stage"] == 0: b["planted"] = time.time(); b["stage"] = 1
                        elif b["stage"] == 2: b["stage"] = 0
                        elif b["stage"] == 3: b["stage"] = 0
                        break
                save_player(user_id, players_db[user_id])

            elif msg.get("type") == "buy_upgrade":
                upg_type = msg.get("upgrade")
                u = players_db[user_id]["upgrades"]
                cost = 0
                if upg_type == 'tap': cost = int(100 * (1.5 ** u['tap']))
                elif upg_type == 'max_energy': cost = int(500 * (1.6 ** u['max_energy']))
                elif upg_type == 'regen': cost = int(1000 * (1.8 ** u['regen']))
                
                if players_db[user_id]["coins"] >= cost:
                    players_db[user_id]["coins"] -= cost
                    u[upg_type] += 1
                    if upg_type == 'tap': players_db[user_id]["tapPower"] += 1
                    elif upg_type == 'max_energy': players_db[user_id]["maxEnergy"] += 100
                    elif upg_type == 'regen': players_db[user_id]["regen"] += 1
                    save_player(user_id, players_db[user_id])

            elif msg.get("type") == "casino":
                bet = int(msg.get("bet"))
                if players_db[user_id]["coins"] >= bet:
                    players_db[user_id]["coins"] -= bet
                    roll = random.random()
                    if roll < 0.5: multiplier = 0
                    elif roll < 0.75: multiplier = 1.5
                    elif roll < 0.90: multiplier = 2
                    elif roll < 0.99: multiplier = 5
                    else: multiplier = 10
                    
                    winAmount = int(bet * multiplier)
                    players_db[user_id]["coins"] += winAmount
                    if multiplier == 10: players_db[user_id]["gems"] += 1
                    
                    save_player(user_id, players_db[user_id])
                    
                    if multiplier > 0:
                        await websocket.send_text(json.dumps({"type": "casino_result", "win": True, "multiplier": multiplier, "text": f"ВЫИГРЫШ x{multiplier}!" + (" (+1 💎)" if multiplier==10 else ""), "newCoins": players_db[user_id]["coins"]}))
                    else:
                        await websocket.send_text(json.dumps({"type": "casino_result", "win": False, "multiplier": 0, "text": "ПРОИГРЫШ", "newCoins": players_db[user_id]["coins"]}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Недостаточно монет!"}))

            elif msg.get("type") == "equip":
                cat = msg.get("category"); item = msg.get("item_id")
                if cat == 'Medal': players_db[user_id]["selectedMedal"] = item
                elif cat == 'Frame': players_db[user_id]["selectedFrame"] = item
                elif cat == 'NickAnim': players_db[user_id]["selectedNickAnim"] = item
                save_player(user_id, players_db[user_id])

            elif msg.get("type") == "add_friend":
                fid = msg.get("friend_id")
                if fid not in players_db[user_id]["friends"]:
                    players_db[user_id]["friends"].append(fid)
                    save_player(user_id, players_db[user_id])
                    
            elif msg.get("type") == "send_gift":
                target_id = msg.get("target_id")
                gift = msg.get("gift")
                cost = int(msg.get("cost"))
                if target_id in players_db and players_db[user_id]["gems"] >= cost:
                    players_db[user_id]["gems"] -= cost
                    players_db[target_id]["gifts"] = players_db[target_id].get("gifts", 0) + 1
                    if "gift_history" not in players_db[target_id]: players_db[target_id]["gift_history"] = []
                    players_db[target_id]["gift_history"].append({"from": players_db[user_id]["name"], "gift": gift, "time": time.time()})
                    
                    save_player(user_id, players_db[user_id])
                    save_player(target_id, players_db[target_id])
                    
                    sync_data = players_db[user_id]; sync_data["gameId"] = players_db[user_id]["game_id"]
                    await websocket.send_text(json.dumps({"type": "sync", "data": sync_data}))
                    
                    if target_id in active_connections:
                        try: await active_connections[target_id].send_text(json.dumps({"type": "gift_received", "from_name": players_db[user_id]["name"], "gift": gift}))
                        except: pass
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Недостаточно гемов!"}))
                    
            elif msg.get("type") == "invite_lobby":
                fid = msg.get("friend_id")
                if fid in active_connections:
                    try: await active_connections[fid].send_text(json.dumps({"type": "lobby_invite", "from_id": user_id, "from_name": players_db[user_id]["name"]}))
                    except: pass
                    
            elif msg.get("type") == "accept_lobby":
                inviter_id = msg.get("inviter_id")
                if inviter_id in players_db and inviter_id in active_connections:
                    players_db[user_id]["lobby_partner"] = inviter_id
                    players_db[user_id]["lobby_partner_name"] = players_db[inviter_id]["name"]
                    players_db[inviter_id]["lobby_partner"] = user_id
                    players_db[inviter_id]["lobby_partner_name"] = players_db[user_id]["name"]
                    
                    save_player(user_id, players_db[user_id])
                    save_player(inviter_id, players_db[inviter_id])
                    
                    sync_u = players_db[user_id]; sync_u["gameId"] = players_db[user_id]["game_id"]
                    sync_i = players_db[inviter_id]; sync_i["gameId"] = players_db[inviter_id]["game_id"]
                    
                    await websocket.send_text(json.dumps({"type": "sync", "data": sync_u}))
                    await websocket.send_text(json.dumps({"type": "lobby_joined", "partner_id": inviter_id, "partner_name": players_db[inviter_id]["name"]}))
                    try: 
                        await active_connections[inviter_id].send_text(json.dumps({"type": "sync", "data": sync_i}))
                        await active_connections[inviter_id].send_text(json.dumps({"type": "lobby_joined", "partner_id": user_id, "partner_name": players_db[user_id]["name"]}))
                    except: pass

            elif msg.get("type") == "hug_partner":
                partner_id = players_db[user_id].get("lobby_partner")
                if partner_id and partner_id in players_db:
                    players_db[user_id]["coins"] += 1000
                    players_db[partner_id]["coins"] += 1000
                    save_player(user_id, players_db[user_id])
                    save_player(partner_id, players_db[partner_id])
                    
                    await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))
                    if partner_id in active_connections:
                        try: await active_connections[partner_id].send_text(json.dumps({"type": "hug_received", "from_name": players_db[user_id]["name"]}))
                        except: pass

            elif msg.get("type") == "leave_lobby":
                partner_id = players_db[user_id].get("lobby_partner")
                players_db[user_id]["lobby_partner"] = None
                players_db[user_id]["lobby_partner_name"] = None
                save_player(user_id, players_db[user_id])
                
                if partner_id and partner_id in players_db:
                    players_db[partner_id]["lobby_partner"] = None
                    players_db[partner_id]["lobby_partner_name"] = None
                    save_player(partner_id, players_db[partner_id])
                    if partner_id in active_connections:
                        try: await active_connections[partner_id].send_text(json.dumps({"type": "sync", "data": players_db[partner_id]}))
                        except: pass

            elif msg.get("type") == "toggle_gender":
                players_db[user_id]["gender"] = "female" if players_db[user_id]["gender"] == "male" else "male"
                save_player(user_id, players_db[user_id])
                await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))

            elif msg.get("type") == "upgrade_house":
                h_level = players_db[user_id].get("house_level", 1)
                cost = h_level * 50000
                if h_level < 3 and players_db[user_id]["coins"] >= cost:
                    players_db[user_id]["coins"] -= cost
                    players_db[user_id]["house_level"] += 1
                    save_player(user_id, players_db[user_id])
                    await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Недостаточно монет или максимальный уровень!"}))

            elif msg.get("type") == "make_pregnant":
                if players_db[user_id]["gender"] == 'female' and not players_db[user_id].get("is_pregnant") and not players_db[user_id].get("has_baby"):
                    players_db[user_id]["is_pregnant"] = True
                    players_db[user_id]["pregnancy_end"] = int(time.time() * 1000) + 180000
                    save_player(user_id, players_db[user_id])
                    
                    partner_id = players_db[user_id].get("lobby_partner")
                    await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))
                    if partner_id and partner_id in active_connections:
                        try: await active_connections[partner_id].send_text(json.dumps({"type": "sync", "data": players_db[partner_id]}))
                        except: pass

            elif msg.get("type") == "check_baby":
                if players_db[user_id].get("is_pregnant"):
                    if int(time.time() * 1000) >= players_db[user_id]["pregnancy_end"]:
                        players_db[user_id]["is_pregnant"] = False
                        players_db[user_id]["has_baby"] = True
                        players_db[user_id]["baby_hunger"] = 100
                        save_player(user_id, players_db[user_id])
                        await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))
                        await websocket.send_text(json.dumps({"type": "error", "message": "🎉 У вас родился малыш!"}))
                        
                        partner_id = players_db[user_id].get("lobby_partner")
                        if partner_id and partner_id in players_db:
                            players_db[partner_id]["is_pregnant"] = False
                            players_db[partner_id]["has_baby"] = True
                            players_db[partner_id]["baby_hunger"] = 100
                            save_player(partner_id, players_db[partner_id])
                            if partner_id in active_connections:
                                try: await active_connections[partner_id].send_text(json.dumps({"type": "sync", "data": players_db[partner_id]}))
                                except: pass

            elif msg.get("type") == "feed_baby":
                if players_db[user_id].get("has_baby"):
                    if players_db[user_id]["coins"] >= 10000:
                        players_db[user_id]["coins"] -= 10000
                        players_db[user_id]["baby_hunger"] = min(100, players_db[user_id].get("baby_hunger", 0) + 20)
                        save_player(user_id, players_db[user_id])
                        await websocket.send_text(json.dumps({"type": "sync", "data": players_db[user_id]}))
                    else:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Нужно 10,000 монет!"}))

    except WebSocketDisconnect:
        partner_id = players_db[user_id].get("lobby_partner")
        if partner_id and partner_id in players_db:
            players_db[partner_id]["lobby_partner"] = None
            players_db[partner_id]["lobby_partner_name"] = None
            save_player(partner_id, players_db[partner_id])
            if partner_id in active_connections:
                try: await active_connections[partner_id].send_text(json.dumps({"type": "sync", "data": players_db[partner_id]}))
                except: pass
                
        players_db[user_id]["lobby_partner"] = None
        players_db[user_id]["lobby_partner_name"] = None
        save_player(user_id, players_db[user_id])
        
        if user_id in active_connections: del active_connections[user_id]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
