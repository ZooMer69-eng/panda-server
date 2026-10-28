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

rooms: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, user_id: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = []
    rooms[room_id].append(websocket)
    
    await broadcast(room_id, {
        "type": "player_joined",
        "user_id": user_id,
        "players_count": len(rooms[room_id])
    })

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "tap":
                await broadcast(room_id, {
                    "type": "player_tapped",
                    "user_id": user_id,
                    "power": message.get("power", 1)
                }, exclude=websocket)
    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        if len(rooms[room_id]) == 0:
            del rooms[room_id]
        else:
            await broadcast(room_id, {
                "type": "player_left",
                "user_id": user_id,
                "players_count": len(rooms[room_id])
            })

async def broadcast(room_id: str, message: dict, exclude: WebSocket = None):
    if room_id in rooms:
        for connection in rooms[room_id]:
            if connection != exclude:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
