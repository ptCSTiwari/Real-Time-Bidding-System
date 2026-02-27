from fastapi import FastAPI, WebSocket, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database import engine, get_db
from fastapi import Query
from models import Base, User, Auction, UserCreate, BidCreate, AuctionCreate, Bid
from bidding import place_bid
from websocket import auction_ws
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from datetime import timedelta

from auth import (
    hash_password,
    verify_password,
    create_token,
    verify_token,
)

app = FastAPI(title="ReGrip Real-Time Bidding API")

# OAuth2 config for Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    try:
        payload = verify_token(token)
        user_id = payload.get("id")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@app.post("/signup")
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar():
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        email=user.email,
        password=hash_password(user.password),
        role=user.role.upper()
    )

    db.add(new_user)
    await db.commit()

    return {"message": "User created"}

@app.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    db_user = result.scalar()

    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"id": db_user.id, "role": db_user.role})

    return {
        "access_token": token,
        "token_type": "bearer"
    }

@app.get("/auction/{auction_id}")
async def get_auction(auction_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    return auction

@app.post("/admin/create-auction")
async def create_auction(
    auction: AuctionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    new_auction = Auction(
        product_name=auction.product_name,
        current_price=auction.current_price,
        status="CREATED",
        end_time=auction.end_time
    )

    db.add(new_auction)
    await db.commit()
    await db.refresh(new_auction)

    return new_auction

@app.post("/admin/start-auction/{auction_id}")
async def start_auction(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    auction.status = "LIVE"
    await db.commit()

    return {"message": "Auction started"}

@app.post("/admin/close-auction/{auction_id}")
async def close_auction(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(select(Auction).where(Auction.id == auction_id))
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    auction.status = "CLOSED"
    await db.commit()

    return {"message": "Auction closed"}

@app.post("/bid")
async def bid(
    bid: BidCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # if current_user.role != "DEALER":
    #     raise HTTPException(status_code=403, detail="Only dealers can bid")

    return await place_bid(
        auction_id=bid.auction_id,
        dealer_id=current_user.id,
        amount=bid.amount,
        idempotency_key=bid.idempotency_key,
        db=db
    )


@app.get("/admin/auction-stats/{auction_id}")
async def auction_stats(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    # Total bids
    total_bids_result = await db.execute(
        select(func.count(Bid.id)).where(Bid.auction_id == auction_id)
    )
    total_bids = total_bids_result.scalar()

    # Highest bidder
    highest_bid_result = await db.execute(
        select(Bid.dealer_id)
        .where(Bid.auction_id == auction_id)
        .order_by(Bid.amount.desc())
        .limit(1)
    )
    highest_bidder = highest_bid_result.scalar()

    return {
        "status": auction.status,
        "current_price": auction.current_price,
        "total_bids": total_bids,
        "highest_bidder": highest_bidder
    }

@app.post("/admin/pause-auction/{auction_id}")
async def pause_auction(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    auction.status = "PAUSED"
    await db.commit()

    return {"message": "Auction paused"}

@app.post("/admin/resume-auction/{auction_id}")
async def resume_auction(
    auction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    auction.status = "LIVE"
    await db.commit()

    return {"message": "Auction resumed"}

@app.post("/admin/extend-auction/{auction_id}")
async def extend_auction(
    auction_id: int,
    extra_minutes: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(
        select(Auction).where(Auction.id == auction_id)
    )
    auction = result.scalar()

    if not auction:
        raise HTTPException(status_code=404, detail="Auction not found")

    if auction.end_time:
        auction.end_time += timedelta(minutes=extra_minutes)
        await db.commit()

    return {"message": "Auction extended"}

@app.get("/admin/all-auctions")
async def admin_all_auctions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    result = await db.execute(select(Auction))
    auctions = result.scalars().all()

    return auctions
@app.get("/auctions")
async def list_auctions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Auction))
    auctions = result.scalars().all()
    return auctions


@app.websocket("/ws/{auction_id}")
async def ws(
    websocket: WebSocket,
    auction_id: int,
    token: str = Query(...)
):
    try:
        verify_token(token)
    except:
        await websocket.close(code=1008)
        return

    await auction_ws(websocket, auction_id)

app.mount("/assets", StaticFiles(directory="../frontend/assets"), name="assets")
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")