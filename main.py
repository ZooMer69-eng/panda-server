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

BOT_TOKEN = "9244645218:AAFopJ-hOND0D5dQx9qzZurAUTbAWQpKs3A" # Токен для отправки счета

# --- ПОДКЛЮЧЕНИЕ К SUPABASE ---
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

# --- НОВЫЙ МАРШРУТ: СЕРВЕР САМ ОТПРАВЛЯЕТ СЧЕТ ---
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

# ... (ДАЛЬШЕ ИДЕТ HTML_CONTENT, ОН НЕ МЕНЯЕТСЯ, НО Я ДАМ ЕГО ЦЕЛИКОМ ЧУТЬ НИЖЕ, ЧТОБЫ ТЫ ПРОСТО СКОПИРОВАЛ) ...

# Так как HTML огромный, я скрыл его для удобства, но тебе нужно скопировать весь код.
# Прокрути вниз, я дам полный файл в следующем блоке.
