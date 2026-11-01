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
            p_data = json.loads(row['data'])
            if "upgrades" not in p_data: p_data["upgrades"] = {"tap": 0, "max_energy": 0, "regen": 0}
            if "selectedMedal" not in p_data: p_data["selectedMedal"] = "none"
            if "selectedFrame" not in p_data: p_data["selectedFrame"] = "default"
            if "selectedNickAnim" not in p_data: p_data["selectedNickAnim"] = "default"
            if "unlockedMedals" not in p_data: p_data["unlockedMedals"] = []
            if "unlockedFrames" not in p_data: p_data["unlockedFrames"] = ["default"]
            if "unlockedAnims" not in p_data: p_data["unlockedAnims"] = ["default"]
            if "friends" not in p_data: p_data["friends"] = []
            players[row['id']] = p_data
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

HTML_CONTENT = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Panda Game 36.3</title>
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
        
        .nick-default { color: #fff; }
        .nick-gold { background: linear-gradient(90deg, #ffd700, #ff8c00, #ffd700); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: goldShine 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,215,0,0.5)); }
        .nick-fire { color: #ff4500; text-shadow: 0 0 5px #ff4500, 0 0 15px #ff0000; animation: fireFlicker 1.5s infinite alternate; }
        .nick-rainbow { background: linear-gradient(90deg, #ff0000, #ff8c00, #ffff00, #00ff00, #00e5ff, #0000ff, #ff00ff); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: rainbowMove 3s linear infinite; filter: drop-shadow(0 0 2px rgba(255,255,255,0.3)); }
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
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 12px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .card-icon { font-size: 32px; margin-bottom: 6px; }
        .card-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .card-desc { font-size: 11px; color: #8892b0; margin-bottom: 8px; }
        .card-price { background: rgba(0,0,0,0.5); padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 900; width: 100%; color: #ffd700; border: 1px solid rgba(255,215,0,0.3); cursor: pointer; }
        .card-price:active { background: rgba(255,215,0,0.2); }
        
        /* Profile Card Fixes */
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

        .bottom-nav { background: rgba(10, 18, 14, 0.98); border-top: 1px solid rgba(46, 125, 50, 0.4); padding: 8px 5px 22px 5px; display: flex; justify-content: space-around; z-index: 30; position: relative; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; background: none; border: none; color: #666; font-size: 9px; font-weight: 900; cursor: pointer; width: 16.6%; transition: 0.2s; }
        .nav-btn.active { color: #81c784; }
        .nav-btn span { font-size: 22px; margin-bottom: 2px; filter: grayscale(1); transition: 0.2s; }
        .nav-btn.active span { filter: drop-shadow(0 0 6px #81c784) grayscale(0); }
    </style>
</head>
<body>
    <div class="bg-container bg-base">
        <div class="bg-moon"></div>
        <div class="bg-mountains"><svg viewBox="0 0 400 200" preserveAspectRatio="none"><path d="M0,200 L50,80 L120,120 L180,40 L260,90 L340,60 L400,150 L400,200 Z" fill="#1e293b"/><path d="M0,200 L70,110 L150,150 L240,80 L320,130 L400,200 Z" fill="#334155"/></svg></div>
        <div class="bg-bamboo"><div class="stalk" style="height: 70%; left: 5%;"></div><div class="stalk" style="height: 90%; left: 20%;"></div><div class="stalk" style="height: 60%; right: 15%;"></div><div class="stalk" style="height: 80%; right: 5%;"></div></div>
        <div class="bg-ground"></div>
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
                            <ellipse cx="100" cy="105" rx="8" ry="5" fill="#111" />
                            <ellipse cx="45" cy="145" rx="18" ry="22" fill="#1a1a1a" /><ellipse cx="155" cy="145" rx="18" ry="22" fill="#1a1a1a" />
                        </svg>
                    </div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-friends">
            <div class="content">
                <div class="section-title">Друзья 👥</div>
                <div style="display:flex; gap:10px; margin-bottom:15px;">
                    <input type="text" id="search-input" placeholder="Ник или ID..." style="flex:1; padding:10px; border-radius:8px; border:none; background:rgba(255,255,255,0.1); color:#fff;">
                    <button onclick="searchPlayers()" style="background:#2196f3; color:#fff; border:none; padding:10px 15px; border-radius:8px; font-weight:900; cursor:pointer;">Найти</button>
                </div>
                <div id="search-results" class="friend-list"></div>
                <div style="margin-top:20px; background: rgba(255,215,0,0.1); border: 1px solid #ffd700; padding: 15px; border-radius: 12px;">
                    <div class="section-title" style="font-size:16px; margin-bottom:10px;">Совместное Лобби (Семья/Братаны)</div>
                    <p style="font-size:12px; color:#aaa; margin-bottom:10px;">Здесь появится ваш общий малыш, когда вы будете играть вдвоем.</p>
                    <div style="font-weight:900; color:#4caf50; font-size:18px; text-align:center;">Вы один</div>
                </div>
                <div class="friend-list" id="friends-list" style="margin-top:20px;"><p style="text-align:center; color:#888;">Загрузка...</p></div>
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
                    <div style="font-size:16px; font-weight:900; margin-bottom:5px; z-index:2;">ID: <span id="my-game-id" style="color:#00e5ff;">...</span></div>
                    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 15px; font-size: 12px; color: #aaa; width: 100%;">
                        <div>Монеты <span id="stat-coins" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
                        <div>Гемы <span id="stat-gems" style="font-weight: 900; color: #fff; display: block; font-size: 16px;">0</span></div>
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

    <script>
        window.onerror = function(msg, url, line) { return false; };
        const tg = window.Telegram.WebApp; tg.expand();
        const myId = String(tg.initDataUnsafe?.user?.id || Math.floor(Math.random() * 10000));
        const WS_URL = window.location.origin.replace('https://', 'wss://');
        let ws;
        let state = { coins: 500, gems: 0, tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 1, upgrades: { tap: 0, max_energy: 0, regen: 0 }, nickname: '', selectedMedal: 'none', selectedFrame: 'default', selectedNickAnim: 'default', avatarUrl: tg.initDataUnsafe?.user?.photo_url || '', gameId: '', unlockedMedals: [], unlockedFrames: ['default'], unlockedAnims: ['default'] };
        
        let currentBet = 10000;
        let isSpinning = false;

        const allMedals = [{ id: 'bronze', name: 'Бронза', req: 30, emoji: '🥉' }, { id: 'silver', name: 'Серебро', req: 90, emoji: '🥈' }, { id: 'gold', name: 'Золото', req: 180, emoji: '🥇' }, { id: 'epic', name: 'Эпик', req: 365, emoji: '💎' }, { id: 'mythic', name: 'Мифик', req: 730, emoji: '👑' }];
        const allFrames = [{ id: 'default', name: 'Новичок', cssClass: 'default', price: 0 }, { id: 'millionaire', name: 'Богач', cssClass: 'millionaire', price: 0 }, { id: 'legend', name: 'Легенда', cssClass: 'legend', price: 0 }, { id: 'neon', name: 'Неон', cssClass: 'neon', price: 50000 }, { id: 'nature', name: 'Природа', cssClass: 'nature', price: 75000 }, { id: 'fire', name: 'Огонь', cssClass: 'fire', price: 100000 }];
        const allAnims = [{ id: 'default', name: 'Обычный', cssClass: 'nick-default' }, { id: 'gold', name: 'Золото', cssClass: 'nick-gold' }, { id: 'fire', name: 'Огонь', cssClass: 'nick-fire' }, { id: 'rainbow', name: 'Радуга', cssClass: 'nick-rainbow' }];

        function connectWS() {
            ws = new WebSocket(`${WS_URL}/ws/main/${myId}`);
            ws.onopen = () => { document.getElementById('conn-status').innerText = "🟢 Онлайн"; ws.send(JSON.stringify({ type: "init" })); };
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
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            if (tabId === 'friends') fetchFriends();
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
                document.getElementById('search-results').innerHTML = data.map(p => `<div style="display:flex; justify-content:space-between; background:rgba(255,255,255,0.1); padding:10px; border-radius:8px; margin-bottom:5px;"><span>${p.name}</span><button onclick="addFriend('${p.id}')" style="background:#4caf50; border:none; padding:5px 10px; border-radius:5px; color:#fff; cursor:pointer;">Добавить</button></div>`).join('');
            } catch(e) {}
        }
        
        async function fetchFriends() {
            try {
                const res = await fetch(`${window.location.origin}/api/friends/${myId}`);
                const data = await res.json();
                if(data.length > 0) {
                    document.getElementById('friends-list').innerHTML = data.map(f => `<div style="display:flex; align-items:center; gap:10px; background:rgba(255,255,255,0.1); padding:10px; border-radius:8px; margin-bottom:5px;"><div style="width:30px; height:30px; border-radius:50%; background:#333; display:flex; justify-content:center; align-items:center; overflow:hidden;">${f.avatar ? `<img src="${f.avatar}" style="width:100%; height:100%;">` : '🐼'}</div><span>${f.name}</span></div>`).join('');
                } else {
                    document.getElementById('friends-list').innerHTML = '<p style="text-align:center; color:#888;">Нет друзей.</p>';
                }
            } catch(e) {}
        }

        setInterval(() => {
            if (state.energy < state.maxEnergy) {
                state.energy = Math.min(state.maxEnergy, state.energy + state.regen);
                if(document.getElementById('energy')) document.getElementById('energy').innerText = Math.floor(state.energy);
                if(document.getElementById('energy-fill')) document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            }
        }, 1000);

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
            "selectedMedal": "none", "selectedFrame": "default", "selectedNickAnim": "default",
            "unlockedMedals": [], "unlockedFrames": ["default"], "unlockedAnims": ["default"],
            "friends": [], "last_active": time.time()
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
            
            if msg.get("type") == "tap":
                players_db[user_id]["coins"] += msg.get("power", 1)
                players_db[user_id]["energy"] = max(0, players_db[user_id]["energy"] - 1)
                players_db[user_id]["last_active"] = time.time()
                if random.random() < 0.1: save_player(user_id, players_db[user_id])
                
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

    except WebSocketDisconnect:
        save_player(user_id, players_db[user_id])
        if user_id in active_connections: del active_connections[user_id]

@app.get("/api/friends/{user_id}")
async def get_friends(user_id: str):
    if user_id not in players_db: return []
    friends_list = []
    for f_id in players_db[user_id].get("friends", []):
        if f_id in players_db: friends_list.append({"id": f_id, "name": players_db[f_id]["name"], "avatar": players_db[f_id].get("avatar", "")})
    return friends_list

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
