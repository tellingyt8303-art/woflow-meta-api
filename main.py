from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from webhook.receiver import router as webhook_router
from api.routes import router as api_router
from database.db import init_firebase
from followups.scheduler import process_due_followups

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    print("✅ Firebase initialized")
    scheduler.add_job(process_due_followups, "interval", minutes=15, id="followup_job")
    scheduler.start()
    print("✅ Scheduler started — follow-ups every 15 min")
    yield
    scheduler.shutdown()

app = FastAPI(
    title="WaFlow — WhatsApp SaaS",
    description="Multi-client WhatsApp automation using Meta Cloud API + Firebase",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
app.include_router(api_router,     prefix="/api",     tags=["API"])

@app.get("/")
async def root():
    return {
        "service": "WaFlow WhatsApp SaaS",
        "api":     "Meta Cloud API v19.0",
        "db":      "Firebase Firestore",
        "docs":    "/docs",
    }
