from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Dict, List
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
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor, sslmode='require')
        return conn
    except Exception as e:
        print(f"DB CONNECTION ERROR: {e}")
        return None

def init_db():
    conn = get_db()
    if not conn: return
    try:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS players (id TEXT PRIMARY KEY, data TEXT)")
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
        for row in c.fetchall(): players[row['id']] = json.loads(row['data'])
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
rooms: Dict[str, dict] = {}
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
        "chat_id": req.user_id,
        "title": f"Покупка {req.gems} гемов 💎",
        "description": "Пополнение баланса игры Panda Game",
        "payload": f"gems_{req.gems}",
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": f"{req.gems} гемов", "amount": req.stars}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()

@app.api_route("/", methods=["GET", "HEAD"])
@app.api_route("/health", methods=["GET", "HEAD"])
async def serve_game():
    response = HTMLResponse(content=HTML_CONTENT)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
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
    <title>Panda Game 35.0</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Nunito', sans-serif; user-select: none; -webkit-tap-highlight-color: transparent; }
        body { background: #0a120e; color: #fff; height: 100vh; display: flex; flex-direction: column; overflow: hidden; position: relative; }
        .bg-container { position: absolute; inset: 0; z-index: 1; overflow: hidden; transition: background 1.5s; }
        .bg-base { background: linear-gradient(180deg, #0f172a 0%, #1e293b 40%, #334155 70%, #475569 100%); }
        .bg-sky { position: absolute; inset: 0; }
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
        .profile-avatar-mini img { width: 100%; height: 100%; object-fit: cover; }
        .name-medal-block { display: flex; flex-direction: column; cursor: pointer; }
        .header-nick { font-size: 16px; font-weight: 900; text-shadow: 2px 2px 0 #000; }
        .res-row { display: flex; align-items: center; gap: 10px; margin-top: 5px; }
        .coins-box { font-size: 18px; font-weight: 900; color: #fff; display: flex; align-items: center; gap: 3px; }
        .gems-box { font-size: 14px; font-weight: 900; color: #00e5ff; display: flex; align-items: center; gap: 3px; cursor: pointer; }
        .icon-coin { display: inline-block; width: 16px; height: 16px; background: radial-gradient(circle at 30% 30%, #fff000, #ffb300, #b26a00); border-radius: 50%; border: 1px solid #e6a800; box-shadow: 0 1px 3px rgba(0,0,0,0.5); text-align: center; line-height: 14px; font-size: 10px; font-weight: 900; color: #8a5100; vertical-align: middle; margin-left: 2px; }
        .energy-box { display: flex; flex-direction: column; align-items: flex-end; cursor: pointer; }
        .energy-bar { width: 70px; height: 8px; background: rgba(0,0,0,0.5); border-radius: 5px; overflow: hidden; border: 1px solid rgba(255,255,255,0.4); margin-top: 3px;}
        .energy-fill { height: 100%; background: linear-gradient(90deg, #00e5ff, #007bff); width: 100%; transition: width 0.3s; }
        
        .screens { flex: 1; position: relative; z-index: 5; overflow: hidden; }
        .screen { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: none; flex-direction: column; }
        .screen.active { display: flex; }
        
        .tap-area { flex: 1; display: flex; justify-content: center; align-items: flex-end; gap: 20px; position: relative; padding-bottom: 10px; z-index: 5; }
        .panda-wrapper { position: relative; width: 190px; height: 210px; transform-origin: center bottom; cursor: pointer; transition: transform 1s ease-in-out; z-index: 10; }
        .panda-wrapper:active { transform: scale(0.95); }
        .panda-wrapper.hit { animation: jump 0.25s ease-out; }
        @keyframes jump { 0% { transform: translateY(0); } 30% { transform: translateY(-15px) scale(1.05); } 100% { transform: translateY(0); } }
        .particle-coin { position: absolute; font-size: 24px; font-weight: 900; color: #ffd700; pointer-events: none; animation: popCoin 0.9s ease-out forwards; z-index: 20; text-shadow: 0 0 10px #ffd700; }
        @keyframes popCoin { 0% { transform: translateY(0) scale(0.4); opacity: 1; } 100% { transform: translateY(-100px) scale(1.2); opacity: 0; } }
        
        .content { flex: 1; padding: 15px; overflow-y: auto; background: rgba(10, 18, 14, 0.85); backdrop-filter: blur(5px); z-index: 20; }
        .section-title { font-size: 18px; font-weight: 900; margin-bottom: 15px; color: #fff; text-align: center; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 15px; padding: 12px; display: flex; flex-direction: column; align-items: center; text-align: center; }
        .card-icon { font-size: 32px; margin-bottom: 6px; }
        .card-title { font-size: 14px; font-weight: 900; margin-bottom: 4px; }
        .card-desc { font-size: 11px; color: #8892b0; margin-bottom: 8px; }
        .card-price { background: rgba(0,0,0,0.5); padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 900; width: 100%; color: #ffd700; border: 1px solid rgba(255,215,0,0.3); cursor: pointer; }
        .card-price:active { background: rgba(255,215,0,0.2); }
        
        .casino-box { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: 20px;}
        .wheel { width: 200px; height: 200px; border-radius: 50%; border: 6px solid #ffd700; transition: transform 3s cubic-bezier(0.17, 0.67, 0.12, 0.99); background: conic-gradient(#e53935 0deg 60deg, #1e88e5 60deg 120deg, #43a047 120deg 180deg, #fdd835 180deg 240deg, #8e24aa 240deg 300deg, #fb8c00 300deg 360deg); box-shadow: 0 0 20px rgba(255,215,0,0.4); position: relative; }
        .wheel-pointer { font-size: 40px; position: absolute; top: -20px; z-index: 10; filter: drop-shadow(0 2px 4px #000); }
        .bet-buttons { display: flex; gap: 10px; margin-top: 20px; }
        .bet-btn { background: #333; padding: 10px 15px; border-radius: 8px; border: 1px solid #555; font-weight: 900; cursor: pointer; }
        .bet-btn.active { background: #4caf50; border-color: #81c784; }
        
        .lobby-card { background: rgba(0,0,0,0.6); border: 2px solid #4caf50; border-radius: 20px; padding: 20px; text-align: center; display: flex; flex-direction: column; align-items: center;}
        .baby-stats { width: 100%; margin-top: 15px; background: rgba(255,255,255,0.1); border-radius: 10px; padding: 10px; }
        .baby-bar { height: 10px; background: #333; border-radius: 5px; margin-top: 5px; overflow: hidden; }
        .baby-fill { height: 100%; background: #ff9800; width: 100%; }
        
        .bottom-nav { background: rgba(10, 18, 14, 0.98); border-top: 1px solid rgba(46, 125, 50, 0.4); padding: 8px 5px 22px 5px; display: flex; justify-content: space-around; z-index: 30; position: relative; }
        .nav-btn { display: flex; flex-direction: column; align-items: center; background: none; border: none; color: #666; font-size: 9px; font-weight: 900; cursor: pointer; width: 20%; transition: 0.2s; }
        .nav-btn.active { color: #81c784; }
        .nav-btn span { font-size: 22px; margin-bottom: 2px; filter: grayscale(1); transition: 0.2s; }
        .nav-btn.active span { filter: drop-shadow(0 0 6px #81c784) grayscale(0); }
    </style>
</head>
<body>
    <div class="bg-container bg-base">
        <div class="bg-sky"><div class="bg-moon"></div></div>
        <div class="bg-mountains"><svg viewBox="0 0 400 200" preserveAspectRatio="none"><path d="M0,200 L50,80 L120,120 L180,40 L260,90 L340,60 L400,150 L400,200 Z" fill="#1e293b"/><path d="M0,200 L70,110 L150,150 L240,80 L320,130 L400,200 Z" fill="#334155"/></svg></div>
        <div class="bg-bamboo"><div class="stalk" style="height: 70%; left: 5%;"></div><div class="stalk" style="height: 90%; left: 20%;"></div><div class="stalk" style="height: 60%; right: 15%;"></div><div class="stalk" style="height: 80%; right: 5%;"></div></div>
        <div class="bg-ground"></div>
    </div>

    <div class="header">
        <div class="user-info-block">
            <div class="avatar-wrap" onclick="switchTab('profile', document.querySelectorAll('.nav-btn')[4])"><div class="profile-avatar-mini" id="mini-avatar"><span>🐼</span></div></div>
            <div>
                <div class="name-medal-block"><div class="header-nick" id="my-name">Ник</div></div>
                <div class="res-row"><div class="coins-box"><span id="coins">0</span> <span class="icon-coin">$</span></div><div class="gems-box" onclick="switchTab('shop', document.querySelectorAll('.nav-btn')[3])"><span id="gems">0</span> 💎</div></div>
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

        <div class="screen" id="screen-lobby">
            <div class="content">
                <div class="section-title">Лобби 👥</div>
                <div class="lobby-card">
                    <div id="lobby-status" style="font-size: 18px; font-weight: 900; color: #4caf50; margin-bottom: 10px;">Вы один</div>
                    <p style="color: #aaa; font-size: 12px; margin-bottom: 15px;">Пригласите друга в лобби, чтобы создать семью или играть за братанов!</p>
                    
                    <div id="baby-section" style="display:none; width: 100%;">
                        <div style="font-size: 40px; margin: 10px 0;">👶</div>
                        <div class="baby-stats">
                            <div style="display:flex; justify-content:space-between; font-size: 12px;"><span>Сытость</span> <span id="baby-hunger-text">100%</span></div>
                            <div class="baby-bar"><div class="baby-fill" id="baby-hunger-bar" style="background:#ff9800;"></div></div>
                            <button class="card-price" style="margin-top: 10px; background:#4caf50; color:#fff;" onclick="feedBaby()">Покормить (10,000 монет)</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-casino">
            <div class="content">
                <div class="section-title">Казино 🎰</div>
                <div class="casino-box">
                    <div style="position: relative;">
                        <div class="wheel-pointer">▼</div>
                        <div class="wheel" id="casino-wheel"></div>
                    </div>
                    <div class="bet-buttons">
                        <div class="bet-btn" onclick="setBet(1000)">1K</div>
                        <div class="bet-btn active" onclick="setBet(10000)">10K</div>
                        <div class="bet-btn" onclick="setBet(100000)">100K</div>
                    </div>
                    <button class="card-price" style="background:#e53935; color:#fff; margin-top:20px; font-size:18px; padding:15px;" onclick="spinCasino()">Крутить!</button>
                    <div id="casino-result" style="margin-top: 15px; font-size: 20px; font-weight: 900;"></div>
                </div>
            </div>
        </div>

        <div class="screen" id="screen-shop">
            <div class="content">
                <div class="section-title">Улучшения 🛍️</div>
                <div class="grid" id="upgrades-grid"></div>
            </div>
        </div>

        <div class="screen" id="screen-profile">
            <div class="content">
                <div class="section-title">Профиль 👤</div>
                <div class="card" style="margin-bottom: 15px;">
                    <div class="card-title">ID: <span id="game-id">...</span></div>
                    <div class="card-desc" style="margin-top:10px;">Уровень клика: <b id="stat-tap">1</b> | Макс. Энергия: <b id="stat-max-energy">1000</b></div>
                </div>
            </div>
        </div>
    </div>

    <div class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('tap', this)"><span>👆</span>Панда</button>
        <button class="nav-btn" onclick="switchTab('lobby', this)"><span>👥</span>Лобби</button>
        <button class="nav-btn" onclick="switchTab('casino', this)"><span>🎰</span>Казино</button>
        <button class="nav-btn" onclick="switchTab('shop', this)"><span>🛍️</span>Улучшения</button>
        <button class="nav-btn" onclick="switchTab('profile', this)"><span>👤</span>Профиль</button>
    </div>

    <script>
        const tg = window.Telegram.WebApp; tg.expand();
        const myId = String(tg.initDataUnsafe?.user?.id || Math.floor(Math.random() * 10000));
        const WS_URL = window.location.origin.replace('https://', 'wss://');
        let ws;
        let state = {
            coins: 500, gems: 0, tapPower: 1, energy: 1000, maxEnergy: 1000, regen: 1,
            houseLevel: 1, babyHunger: 100, hasBaby: false, isPregnant: false,
            upgrades: { tap: 0, max_energy: 0, regen: 0 }
        };
        let currentBet = 10000;

        function connectWS() {
            ws = new WebSocket(`${WS_URL}/ws/main/${myId}`);
            ws.onopen = () => { document.getElementById('conn-status').innerText = "🟢 Онлайн"; ws.send(JSON.stringify({ type: "init" })); };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'sync') {
                    state = { ...state, ...data.data };
                    document.getElementById('game-id').innerText = state.gameId || '...';
                    updateUI();
                } else if (data.type === 'casino_result') {
                    document.getElementById('casino-result').innerText = data.text;
                    document.getElementById('casino-result').style.color = data.win ? '#4caf50' : '#e53935';
                    if (data.win) {
                        state.coins = data.newCoins;
                        updateUI();
                    }
                } else if (data.type === 'error') {
                    tg.showAlert(data.message);
                }
            };
            ws.onclose = () => { document.getElementById('conn-status').innerText = "🔴 Оффлайн"; setTimeout(connectWS, 3000); };
        }

        document.getElementById('panda-wrapper').addEventListener('pointerdown', (e) => {
            if (state.energy <= 0) return;
            state.energy -= 1;
            state.coins += state.tapPower;
            
            const p = document.getElementById('panda-wrapper');
            p.classList.remove('hit'); void p.offsetWidth; p.classList.add('hit');
            
            const coin = document.createElement('div'); coin.className = 'particle-coin'; coin.innerText = `+${state.tapPower}`;
            coin.style.left = (e.clientX - 15) + 'px'; coin.style.top = (e.clientY - 20) + 'px';
            document.body.appendChild(coin); setTimeout(() => coin.remove(), 900);
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: "tap", power: state.tapPower }));
            }
            updateUI();
        });

        function updateUI() {
            document.getElementById('coins').innerText = Math.floor(state.coins).toLocaleString();
            document.getElementById('gems').innerText = Math.floor(state.gems).toLocaleString();
            document.getElementById('energy').innerText = Math.floor(state.energy);
            document.getElementById('max-energy').innerText = state.maxEnergy;
            document.getElementById('energy-fill').style.width = (state.energy / state.maxEnergy * 100) + '%';
            document.getElementById('my-name').innerText = state.name || 'Ник';
            document.getElementById('stat-tap').innerText = state.tapPower;
            document.getElementById('stat-max-energy').innerText = state.maxEnergy;

            const u = state.upgrades;
            const shopHTML = `
                <div class="card">
                    <div class="card-icon">🐾</div>
                    <div class="card-title">Сила клика (Ур.${u.tap})</div>
                    <div class="card-desc">+1 к монетам за клик</div>
                    <button class="card-price" onclick="buyUpgrade('tap')">${(100 * Math.pow(1.5, u.tap)).toFixed(0)} $</button>
                </div>
                <div class="card">
                    <div class="card-icon">⚡</div>
                    <div class="card-title">Энергия (Ур.${u.max_energy})</div>
                    <div class="card-desc">+100 к макс. энергии</div>
                    <button class="card-price" onclick="buyUpgrade('max_energy')">${(500 * Math.pow(1.6, u.max_energy)).toFixed(0)} $</button>
                </div>
                <div class="card">
                    <div class="card-icon">🍃</div>
                    <div class="card-title">Регенерация (Ур.${u.regen})</div>
                    <div class="card-desc">+1 энергии в секунду</div>
                    <button class="card-price" onclick="buyUpgrade('regen')">${(1000 * Math.pow(1.8, u.regen)).toFixed(0)} $</button>
                </div>
            `;
            document.getElementById('upgrades-grid').innerHTML = shopHTML;

            if (state.hasBaby) {
                document.getElementById('baby-section').style.display = 'block';
                document.getElementById('lobby-status').innerText = "Семья";
                document.getElementById('baby-hunger-text').innerText = state.babyHunger + '%';
                document.getElementById('baby-hunger-bar').style.width = state.babyHunger + '%';
            }
        }

        function switchTab(tabId, btn) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('screen-' + tabId).classList.add('active');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }

        function buyUpgrade(type) { ws.send(JSON.stringify({ type: "buy_upgrade", upgrade: type })); }

        function setBet(amount) {
            currentBet = amount;
            document.querySelectorAll('.bet-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
        }

        function spinCasino() {
            if (state.coins < currentBet) { tg.showAlert("Недостаточно монет!"); return; }
            const wheel = document.getElementById('casino-wheel');
            wheel.style.transform = `rotate(${Math.floor(Math.random() * 360) + 1800}deg)`;
            document.getElementById('casino-result').innerText = "Крутим...";
            setTimeout(() => { ws.send(JSON.stringify({ type: "casino", bet: currentBet })); }, 3000);
        }

        function feedBaby() { ws.send(JSON.stringify({ type: "feed_baby" })); }

        setInterval(() => {
            if (state.energy < state.maxEnergy) { state.energy = Math.min(state.maxEnergy, state.energy + state.regen); updateUI(); }
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
    if room_id not in rooms: rooms[room_id] = {"players": {}}
    
    if user_id not in players_db:
        players_db[user_id] = {
            "name": f"Panda_{user_id[:4]}", "coins": 500, "gems": 0, 
            "tapPower": 1, "energy": 1000, "maxEnergy": 1000, "regen": 1,
            "houseLevel": 1, "babyHunger": 100, "hasBaby": False, "isPregnant": False,
            "upgrades": {"tap": 0, "max_energy": 0, "regen": 0},
            "last_active": time.time()
        }
    if "game_id" not in players_db[user_id]: 
        players_db[user_id]["game_id"] = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    save_player(user_id, players_db[user_id])
    rooms[room_id]["players"][user_id] = websocket
    
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
                if random.random() < 0.1: save_player(user_id, players_db[user_id])
                
            elif msg.get("type") == "buy_upgrade":
                upg_type = msg.get("upgrade")
                u = players_db[user_id]["upgrades"]
                cost = 0
                if upg_type == 'tap': cost = 100 * (1.5 ** u['tap'])
                elif upg_type == 'max_energy': cost = 500 * (1.6 ** u['max_energy'])
                elif upg_type == 'regen': cost = 1000 * (1.8 ** u['regen'])
                
                if players_db[user_id]["coins"] >= cost:
                    players_db[user_id]["coins"] -= cost
                    u[upg_type] += 1
                    if upg_type == 'tap': players_db[user_id]["tapPower"] += 1
                    elif upg_type == 'max_energy': players_db[user_id]["maxEnergy"] += 100
                    elif upg_type == 'regen': players_db[user_id]["regen"] += 1
                    
                    save_player(user_id, players_db[user_id])
                    sync_data = players_db[user_id]; sync_data["gameId"] = players_db[user_id]["game_id"]
                    await websocket.send_text(json.dumps({"type": "sync", "data": sync_data}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Недостаточно монет!"}))

            elif msg.get("type") == "casino":
                bet = int(msg.get("bet"))
                if players_db[user_id]["coins"] >= bet:
                    players_db[user_id]["coins"] -= bet
                    roll = random.random()
                    multiplier = 0
                    if roll < 0.5: multiplier = 0
                    elif roll < 0.75: multiplier = 1.5
                    elif roll < 0.90: multiplier = 2
                    elif roll < 0.99: multiplier = 10
                    else: multiplier = 50
                    
                    winAmount = int(bet * multiplier)
                    players_db[user_id]["coins"] += winAmount
                    
                    save_player(user_id, players_db[user_id])
                    
                    if multiplier > 0:
                        await websocket.send_text(json.dumps({"type": "casino_result", "win": True, "text": f"ВЫИГРЫШ x{multiplier}!", "newCoins": players_db[user_id]["coins"]}))
                    else:
                        await websocket.send_text(json.dumps({"type": "casino_result", "win": False, "text": "ПРОИГРЫШ"}))
                        sync_data = players_db[user_id]; sync_data["gameId"] = players_db[user_id]["game_id"]
                        await websocket.send_text(json.dumps({"type": "sync", "data": sync_data}))
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Недостаточно монет для ставки!"}))

            elif msg.get("type") == "feed_baby":
                if players_db[user_id]["hasBaby"]:
                    if players_db[user_id]["coins"] >= 10000:
                        players_db[user_id]["coins"] -= 10000
                        players_db[user_id]["babyHunger"] = min(100, players_db[user_id]["babyHunger"] + 20)
                        save_player(user_id, players_db[user_id])
                        sync_data = players_db[user_id]; sync_data["gameId"] = players_db[user_id]["game_id"]
                        await websocket.send_text(json.dumps({"type": "sync", "data": sync_data}))
                    else:
                        await websocket.send_text(json.dumps({"type": "error", "message": "Нужно 10,000 монет!"}))
    except WebSocketDisconnect:
        if user_id in active_connections: del active_connections[user_id]
        if user_id in rooms.get(room_id, {}).get("players", {}): 
            del rooms[room_id]["players"][user_id]

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
