from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI()

# Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rooms = {}  # room_id -> {"video_url", "state", "time", "last_update", "clients", "chat"}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    if room_id not in rooms:
        rooms[room_id] = {
            "video_url": "",
            "state": "pause",
            "time": 0.0,
            "last_update": time.time(),
            "clients": set(),
            "chat": []
        }
    room = rooms[room_id]
    room["clients"].add(websocket)

    # Send initial state
    await websocket.send_json({
        "video_url": room["video_url"],
        "state": room["state"],
        "time": room["time"] + (time.time() - room["last_update"] if room["state"]=="play" else 0),
        "chat": room["chat"]
    })

    try:
        while True:
            data = await websocket.receive_json()
            now = time.time()
            action = data.get("action")

            if action == "update_video":
                room["video_url"] = data["video_url"]
                room["state"] = "pause"
                room["time"] = 0
                room["last_update"] = now
            elif action == "play":
                if room["state"]=="pause":
                    room["time"] += now - room["last_update"]
                room["state"]="play"
                room["last_update"]=now
            elif action == "pause":
                if room["state"]=="play":
                    room["time"] += now - room["last_update"]
                room["state"]="pause"
                room["last_update"]=now
            elif action == "seek":
                room["time"]=data["time"]
                room["last_update"]=now
            elif action == "chat":
                room["chat"].append({"user": data["user"], "msg": data["msg"]})

            # Broadcast updated state to all clients
            for client in room["clients"]:
                try:
                    await client.send_json({
                        "video_url": room["video_url"],
                        "state": room["state"],
                        "time": room["time"] + (time.time() - room["last_update"] if room["state"]=="play" else 0),
                        "chat": room["chat"]
                    })
                except:
                    pass
    except WebSocketDisconnect:
        room["clients"].remove(websocket)
