from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.api.auth_routes import router as auth_router
from app.api.reviews import router as reviews_router
from app.api.billing_routes import router as billing_router
from app.api.google_routes import router as google_router
from app.api.amazon_routes import router as amazon_router
from app.api.flipkart_routes import router as flipkart_router
from app.api.myntra_routes import router as myntra_router
from app.api.extension_routes import router as extension_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add trial/billing columns to existing deployments
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS trial_ends_at TIMESTAMPTZ"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS paid_at TIMESTAMPTZ"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS payer_type VARCHAR(20)"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS paid_by_user_id INTEGER"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_order_id VARCHAR(255)"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS razorpay_payment_id VARCHAR(255)"
        ))
        await conn.execute(__import__("sqlalchemy").text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS account_type VARCHAR(20) DEFAULT 'seller'"
        ))
    yield


app = FastAPI(title="ReviewFlow API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(reviews_router, prefix="/api")
app.include_router(billing_router, prefix="/api")
app.include_router(google_router, prefix="/api")
app.include_router(amazon_router, prefix="/api")
app.include_router(flipkart_router, prefix="/api")
app.include_router(myntra_router, prefix="/api")
app.include_router(extension_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "reviewflow-api"}
