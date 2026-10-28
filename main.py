from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import json
import os

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms: Dict[str, Dict[str, WebSocket]] = {}

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = {}
    rooms[room_id][user_id] = websocket
    
    await broadcast(room_id, {
        "type": "player_joined",
        "user_id": user_id,
        "players_count": len(rooms[room_id])
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
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
            await broadcast(room_id, {
                "type": "player_left",
                "user_id": user_id,
                "players_count": len(rooms[room_id])
            })

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
