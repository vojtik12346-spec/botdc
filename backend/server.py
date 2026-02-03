from fastapi import FastAPI, APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import httpx

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============== Auth Models ==============

class UserSession(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    session_token: str
    expires_at: datetime

class DashboardUser(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    discord_id: Optional[str] = None

class GuildSettings(BaseModel):
    guild_id: str
    guild_name: str
    quiz_time: int = 60
    quiz_rounds: int = 5
    poll_enabled: bool = True
    countdown_enabled: bool = True

# ============== Auth Helpers ==============

async def get_current_user(request: Request) -> Optional[DashboardUser]:
    """Get current user from session token cookie or Authorization header"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        return None
    
    session = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session:
        return None
    
    # Check expiry
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user = await db.dashboard_users.find_one(
        {"user_id": session["user_id"]},
        {"_id": 0}
    )
    
    if not user:
        return None
    
    return DashboardUser(**user)

# ============== Auth Routes ==============

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id for session_token"""
    data = await request.json()
    session_id = data.get("session_id")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    
    # Call Emergent Auth API
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": session_id}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            
            auth_data = auth_response.json()
        except Exception as e:
            logger.error(f"Auth error: {e}")
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    # Create or update user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    existing_user = await db.dashboard_users.find_one({"email": auth_data["email"]}, {"_id": 0})
    
    if existing_user:
        user_id = existing_user["user_id"]
        await db.dashboard_users.update_one(
            {"email": auth_data["email"]},
            {"$set": {
                "name": auth_data["name"],
                "picture": auth_data.get("picture"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    else:
        await db.dashboard_users.insert_one({
            "user_id": user_id,
            "email": auth_data["email"],
            "name": auth_data["name"],
            "picture": auth_data.get("picture"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Create session
    session_token = auth_data.get("session_token", f"session_{uuid.uuid4().hex}")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user = await db.dashboard_users.find_one({"user_id": user_id}, {"_id": 0})
    return user

@api_router.get("/auth/me")
async def get_me(request: Request):
    """Get current authenticated user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout and clear session"""
    session_token = request.cookies.get("session_token")
    
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ============== Bot Settings Routes ==============

@api_router.get("/settings")
async def get_all_settings(request: Request):
    """Get all guild settings"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    settings = await db.guild_settings.find({}, {"_id": 0}).to_list(100)
    return settings

@api_router.get("/settings/{guild_id}")
async def get_guild_settings(guild_id: str, request: Request):
    """Get settings for a specific guild"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    settings = await db.guild_settings.find_one({"guild_id": guild_id}, {"_id": 0})
    
    if not settings:
        # Return defaults
        return {
            "guild_id": guild_id,
            "guild_name": "Unknown",
            "quiz_time": 60,
            "quiz_rounds": 5,
            "poll_enabled": True,
            "countdown_enabled": True
        }
    
    return settings

@api_router.post("/settings/{guild_id}")
async def update_guild_settings(guild_id: str, request: Request):
    """Update settings for a guild"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await request.json()
    
    # Validate
    if "quiz_time" in data:
        if data["quiz_time"] < 30 or data["quiz_time"] > 300:
            raise HTTPException(status_code=400, detail="quiz_time must be 30-300")
    
    if "quiz_rounds" in data:
        if data["quiz_rounds"] < 1 or data["quiz_rounds"] > 20:
            raise HTTPException(status_code=400, detail="quiz_rounds must be 1-20")
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    data["updated_by"] = user.user_id
    
    await db.guild_settings.update_one(
        {"guild_id": guild_id},
        {"$set": data},
        upsert=True
    )
    
    settings = await db.guild_settings.find_one({"guild_id": guild_id}, {"_id": 0})
    return settings

# ============== Stats Routes ==============

@api_router.get("/stats")
async def get_stats(request: Request):
    """Get bot statistics"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get counts
    total_users = await db.quiz_users.count_documents({})
    total_quizzes = await db.quiz_logs.count_documents({})
    total_polls = await db.poll_logs.count_documents({})
    
    # Get leaderboard
    leaderboard = await db.quiz_users.find(
        {},
        {"_id": 0}
    ).sort("score", -1).limit(10).to_list(10)
    
    return {
        "total_users": total_users,
        "total_quizzes": total_quizzes,
        "total_polls": total_polls,
        "leaderboard": leaderboard
    }

@api_router.get("/songs")
async def get_songs(request: Request):
    """Get all songs in quiz database"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Return predefined songs from bot
    songs = {
        "rap": [
            {"artist": "Yzomandias", "song": "Po svým"},
            {"artist": "Viktor Sheen", "song": "Barvy"},
            {"artist": "Calin", "song": "Jednou"},
            {"artist": "Nik Tendo", "song": "Stovky"},
            {"artist": "Sergei Barracuda", "song": "Nahoře"},
            {"artist": "Hasan", "song": "Makám"},
        ],
        "pop": [
            {"artist": "Mirai", "song": "Holky z naší školky"},
            {"artist": "Slza", "song": "Když nemůžeš spát"},
            {"artist": "Pokáč", "song": "Půlnoční"},
            {"artist": "Ewa Farna", "song": "Ty víš"},
            {"artist": "Marek Ztracený", "song": "Léta"},
        ],
        "rock": [
            {"artist": "Kryštof", "song": "Jinej člověk"},
            {"artist": "Kabát", "song": "Sním svůj sen"},
            {"artist": "Chinaski", "song": "Hvězdy"},
            {"artist": "Lucie", "song": "Pojď blíž"},
        ],
        "classic": [
            {"artist": "Karel Gott", "song": "Lady Carneval"},
            {"artist": "Ivan Mládek", "song": "Jožin z bažin"},
            {"artist": "Karel Kryl", "song": "Bratříčku"},
            {"artist": "Marta Kubišová", "song": "Modlitba pro Martu"},
        ]
    }
    
    return songs

@api_router.get("/logs")
async def get_logs(request: Request, limit: int = 50):
    """Get command logs"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logs = await db.command_logs.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return logs

# ============== Health Check ==============

@api_router.get("/")
async def root():
    return {"message": "Bot Dashboard API", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
