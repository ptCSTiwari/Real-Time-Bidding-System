# import json
# from sqlalchemy.future import select
# from sqlalchemy.exc import IntegrityError
# from models import Auction, Bid
# from fastapi import HTTPException
# from redis_client import r
# from datetime import datetime

# MIN_INCREMENT = 10


# async def place_bid(
#     auction_id: int,
#     dealer_id: int,
#     amount: float,
#     idempotency_key: str,
#     db
# ):
#     if amount <= 0:
#         raise HTTPException(status_code=400, detail="Invalid bid amount")

#     try:
#         async with db.begin():

#             # 🔒 ROW LEVEL LOCK
#             result = await db.execute(
#                 select(Auction)
#                 .where(Auction.id == auction_id)
#                 .with_for_update()
#             )
#             auction = result.scalar()

#             if not auction:
#                 raise HTTPException(status_code=404, detail="Auction not found")

#             # Auto-close if expired
#             if auction.end_time and auction.end_time < datetime.utcnow():
#                 auction.status = "CLOSED"
#                 await db.flush()
#                 raise HTTPException(status_code=400, detail="Auction expired")

#             if auction.status != "LIVE":
#                 raise HTTPException(status_code=400, detail="Auction not live")

#             if amount <= auction.current_price:
#                 raise HTTPException(status_code=400, detail="Bid too low")

#             if amount < auction.current_price + MIN_INCREMENT:
#                 raise HTTPException(
#                     status_code=400,
#                     detail=f"Minimum increment is ₹{MIN_INCREMENT}"
#                 )

#             # Idempotency protection
#             existing = await db.execute(
#                 select(Bid).where(Bid.idempotency_key == idempotency_key)
#             )
#             if existing.scalar():
#                 return {"message": "Duplicate ignored"}

#             # Update auction price
#             auction.current_price = amount

#             bid = Bid(
#                 auction_id=auction_id,
#                 dealer_id=dealer_id,
#                 amount=amount,
#                 idempotency_key=idempotency_key
#             )
#             db.add(bid)

#     except IntegrityError:
#         raise HTTPException(status_code=400, detail="Duplicate bid detected")

#     # 📡 Publish AFTER commit
#     await r.publish(
#         f"auction_{auction_id}",
#         json.dumps({
#             "price": amount,
#             "dealer_id": dealer_id
#         })
#     )

#     return {"message": "Bid placed successfully"}


import json
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from models import Auction, Bid
from fastapi import HTTPException
from redis_client import r
from datetime import datetime

MIN_INCREMENT = 100


async def place_bid(
    auction_id: int,
    dealer_id: int,
    amount: float,
    idempotency_key: str,
    db
):

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid bid amount")

    # 🔒 Row level lock
    result = await db.execute(
        select(Auction)
        .where(Auction.id == auction_id)
        .with_for_update()
    )
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    if auction.status != "LIVE":
        raise HTTPException(status_code=400, detail="Auction not live")

    if amount <= auction.current_price:
        raise HTTPException(status_code=400, detail="Bid too low")

    if amount < auction.current_price + MIN_INCREMENT:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum increment is ₹{MIN_INCREMENT}"
        )

    # Idempotency check
    existing = await db.execute(
        select(Bid).where(Bid.idempotency_key == idempotency_key)
    )
    if existing.scalar():
        return {"message": "Duplicate ignored"}

    try:
        auction.current_price = amount

        bid = Bid(
            auction_id=auction_id,
            dealer_id=dealer_id,
            amount=amount,
            idempotency_key=idempotency_key
        )

        db.add(bid)
        await db.commit()

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate bid detected")

    # Publish to Redis
    await r.publish(
        f"auction_{auction_id}",
        json.dumps({
            "price": amount,
            "dealer_id": dealer_id
        })
    )

    return {"message": "Bid placed successfully"}