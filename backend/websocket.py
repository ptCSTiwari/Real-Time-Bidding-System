import json
from fastapi import WebSocket, WebSocketDisconnect
from redis_client import r
from auth import verify_token
from database import AsyncSessionLocal
from models import Auction
from sqlalchemy.future import select


async def auction_ws(websocket: WebSocket, auction_id: int):

    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = verify_token(token)
    except:
        await websocket.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Auction).where(Auction.id == auction_id)
        )
        auction = result.scalar()

        if not auction:
            await websocket.close(code=1008)
            return

    await websocket.accept()

    # send initial state
    await websocket.send_text(json.dumps({
        "price": auction.current_price,
        "dealer_id": None
    }))

    pubsub = r.pubsub()
    await pubsub.subscribe(f"auction_{auction_id}")

    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0
            )

            if message:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode()

                await websocket.send_text(data)

    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"auction_{auction_id}")
        await pubsub.close()