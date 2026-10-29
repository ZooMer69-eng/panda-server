from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
import os
import time

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# База данных в памяти (для теста)
# В реальном проекте тут должна быть SQLite или PostgreSQL
players_db: Dict[str, dict] = {}  # user_id -> {name, coins, last_active}
rooms: Dict[str, Dict[str, WebSocket]] = {}

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    
    # Регистрируем игрока
    if user_id not in players_db:
        players_db[user_id] = {"name": f"Panda_{user_id}", "coins": 0, "last_active": time.time()}
    else:
        players_db[user_id]["last_active"] = time.time()
        
    if room_id not in rooms:
        rooms[room_id] = {}
    rooms[room_id][user_id] = websocket
    
    await broadcast_room_state(room_id)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                players_db[user_id]["last_active"] = time.time()
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
            
            if message.get("type") == "update_stats":
                players_db[user_id]["coins"] = message.get("coins", 0)
                players_db[user_id]["last_active"] = time.time()
                continue
                
            if message.get("type") == "tap":
                await broadcast(room_id, {
                    "type": "player_tapped",
                    "user_id": user_id,
                    "power": message.get("power", 1)
                }, exclude_user=user_id)
                
    except WebSocketDisconnect:
        if user_id in rooms[room_id]:
            del rooms[room_id][user_id]
        
        if len(rooms[room_id]) == 0:
            del rooms[room_id]
        else:
            await broadcast_room_state(room_id)

@app.get("/api/leaderboard")
async def get_leaderboard():
    # Возвращаем топ 50 игроков по монетам
    sorted_players = sorted(players_db.items(), key=lambda x: x[1]["coins"], reverse=True)[:50]
    result = []
    for uid, data in sorted_players:
        # Онлайн, если активность была меньше 2 минут назад
        is_online = (time.time() - data["last_active"]) < 120
        result.append({"id": uid, "name": data["name"], "coins": data["coins"], "online": is_online})
    return result

@app.get("/api/friends/{user_id}")
async def get_friends(user_id: str):
    # Здесь мы имитируем друзей. В реальном проекте они бы хранились в БД.
    # Пока просто вернем фейковый список для теста.
    fake_friends = [
        {"id": "111", "name": "Милашка", "coins": 15000, "online": True},
        {"id": "222", "name": "Братан", "coins": 5000, "online": False},
        {"id": "333", "name": "Панда_Мастер", "coins": 120000, "online": True}
    ]
    return fake_friends

async def broadcast_room_state(room_id: str):
    if room_id in rooms:
        players_list = list(rooms[room_id].keys())
        await broadcast(room_id, {"type": "room_state", "players": players_list})

async def broadcast(room_id: str, message: dict, exclude_user: str = None):
    if room_id in rooms:
        for uid, connection in list(rooms[room_id].items()):
            if uid != exclude_user:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
