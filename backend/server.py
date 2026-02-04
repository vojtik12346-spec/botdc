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
    
    # Return predefined songs from bot - 150+ songs
    songs = {
        "rap": [
            {"artist": "Yzomandias", "song": "Po svým"},
            {"artist": "Yzomandias", "song": "Z ničeho"},
            {"artist": "Yzomandias", "song": "Sny"},
            {"artist": "Yzomandias", "song": "Block"},
            {"artist": "Yzomandias", "song": "Runway"},
            {"artist": "Yzomandias", "song": "Bohatství"},
            {"artist": "Yzomandias", "song": "Milion"},
            {"artist": "Yzomandias", "song": "Cash"},
            {"artist": "Viktor Sheen", "song": "Barvy"},
            {"artist": "Viktor Sheen", "song": "Real Shit"},
            {"artist": "Viktor Sheen", "song": "Zlatý časy"},
            {"artist": "Viktor Sheen", "song": "Noční město"},
            {"artist": "Viktor Sheen", "song": "Mercedes"},
            {"artist": "Viktor Sheen", "song": "Dopředu"},
            {"artist": "Viktor Sheen", "song": "Jed"},
            {"artist": "Calin", "song": "Jednou"},
            {"artist": "Calin", "song": "Král"},
            {"artist": "Calin", "song": "Money"},
            {"artist": "Calin", "song": "Dream team"},
            {"artist": "Calin", "song": "Pohádka"},
            {"artist": "Calin", "song": "Diamanty"},
            {"artist": "Nik Tendo", "song": "Stovky"},
            {"artist": "Nik Tendo", "song": "Démoni"},
            {"artist": "Nik Tendo", "song": "Svý"},
            {"artist": "Nik Tendo", "song": "Stack"},
            {"artist": "Nik Tendo", "song": "Psycho"},
            {"artist": "Nik Tendo", "song": "Praha"},
            {"artist": "Sergei Barracuda", "song": "Nahoře"},
            {"artist": "Sergei Barracuda", "song": "Hustle"},
            {"artist": "Sergei Barracuda", "song": "RIP"},
            {"artist": "Sergei Barracuda", "song": "Southside"},
            {"artist": "Hasan", "song": "Makám"},
            {"artist": "Hasan", "song": "Hudba"},
            {"artist": "Hasan", "song": "Máma"},
            {"artist": "Lvcas Dope", "song": "Dope Boys"},
            {"artist": "Lvcas Dope", "song": "Oheň"},
            {"artist": "Lvcas Dope", "song": "Gang"},
            {"artist": "Marpo", "song": "Troublegang"},
            {"artist": "Marpo", "song": "Bojuju"},
            {"artist": "Marpo", "song": "Legendy"},
            {"artist": "Ben Cristovao", "song": "Asio"},
            {"artist": "Ben Cristovao", "song": "Bomby"},
            {"artist": "Rest", "song": "Hrdina"},
            {"artist": "Rest", "song": "Million"},
            {"artist": "Dollar Prync", "song": "Vibe"},
            {"artist": "Refew", "song": "Královská hra"},
            {"artist": "Refew", "song": "Padouch"},
        ],
        "pop": [
            {"artist": "Mirai", "song": "Holky z naší školky"},
            {"artist": "Mirai", "song": "Dobrý"},
            {"artist": "Mirai", "song": "Slunce"},
            {"artist": "Mirai", "song": "Padám"},
            {"artist": "Mirai", "song": "Srdce"},
            {"artist": "Mirai", "song": "Celou noc"},
            {"artist": "Mirai", "song": "Tady a teď"},
            {"artist": "Slza", "song": "Když nemůžeš spát"},
            {"artist": "Slza", "song": "Máme se rádi"},
            {"artist": "Slza", "song": "Zázraky"},
            {"artist": "Slza", "song": "Hořím"},
            {"artist": "Slza", "song": "Nebe"},
            {"artist": "Slza", "song": "Dva lidi"},
            {"artist": "Pokáč", "song": "Půlnoční"},
            {"artist": "Pokáč", "song": "Tancuj"},
            {"artist": "Pokáč", "song": "Ráno"},
            {"artist": "Pokáč", "song": "Kafe"},
            {"artist": "Pokáč", "song": "Second hand"},
            {"artist": "Pokáč", "song": "Pizza"},
            {"artist": "Ewa Farna", "song": "Ty víš"},
            {"artist": "Ewa Farna", "song": "Nevíš"},
            {"artist": "Ewa Farna", "song": "Válka"},
            {"artist": "Ewa Farna", "song": "Měls mě rád"},
            {"artist": "Ewa Farna", "song": "Ticho"},
            {"artist": "Ewa Farna", "song": "Na ostří nože"},
            {"artist": "Marek Ztracený", "song": "Léta"},
            {"artist": "Marek Ztracený", "song": "Společně"},
            {"artist": "Marek Ztracený", "song": "Hvězdy"},
            {"artist": "Marek Ztracený", "song": "Až jednou"},
            {"artist": "Aneta Langerová", "song": "Voda živá"},
            {"artist": "Aneta Langerová", "song": "Pták"},
            {"artist": "Tomáš Klus", "song": "Dál"},
            {"artist": "Tomáš Klus", "song": "Do nebe"},
            {"artist": "Tomáš Klus", "song": "Ty a já"},
            {"artist": "Thom Artway", "song": "Running"},
            {"artist": "Thom Artway", "song": "Never"},
            {"artist": "Mig 21", "song": "Snadné"},
            {"artist": "Mig 21", "song": "Život"},
            {"artist": "Lenny", "song": "Hell.o"},
            {"artist": "Lenny", "song": "Dreaming"},
            {"artist": "Rybičky 48", "song": "Pořád ta samá"},
            {"artist": "Rybičky 48", "song": "Adéla"},
        ],
        "rock": [
            {"artist": "Kryštof", "song": "Jinej člověk"},
            {"artist": "Kryštof", "song": "Běžím"},
            {"artist": "Kryštof", "song": "Zůstaň"},
            {"artist": "Kryštof", "song": "Zítra"},
            {"artist": "Kryštof", "song": "Ty a já"},
            {"artist": "Kryštof", "song": "Sněhulák"},
            {"artist": "Kryštof", "song": "Cesta"},
            {"artist": "Kabát", "song": "Sním svůj sen"},
            {"artist": "Kabát", "song": "Máma"},
            {"artist": "Kabát", "song": "Bílá vrána"},
            {"artist": "Kabát", "song": "Kdo nekrade"},
            {"artist": "Kabát", "song": "Pohoda"},
            {"artist": "Kabát", "song": "Corrida"},
            {"artist": "Kabát", "song": "Dole v dole"},
            {"artist": "Kabát", "song": "Colorado"},
            {"artist": "Chinaski", "song": "Hvězdy"},
            {"artist": "Chinaski", "song": "Naplno"},
            {"artist": "Chinaski", "song": "Na jih"},
            {"artist": "Chinaski", "song": "Rock and roll"},
            {"artist": "Chinaski", "song": "Přítel"},
            {"artist": "Chinaski", "song": "Všechno"},
            {"artist": "Lucie", "song": "Pojď blíž"},
            {"artist": "Lucie", "song": "Amerika"},
            {"artist": "Lucie", "song": "Černý andělé"},
            {"artist": "Lucie", "song": "Šum"},
            {"artist": "Lucie", "song": "Chci zas"},
            {"artist": "Lucie", "song": "Medvídek"},
            {"artist": "Horkýže Slíže", "song": "Vlak"},
            {"artist": "Horkýže Slíže", "song": "Silné reči"},
            {"artist": "Škwor", "song": "Sám"},
            {"artist": "Škwor", "song": "Síla"},
            {"artist": "Divokej Bill", "song": "Čmelák"},
            {"artist": "Divokej Bill", "song": "Malování"},
            {"artist": "Divokej Bill", "song": "Ring ding dong"},
            {"artist": "Wohnout", "song": "Svaz"},
            {"artist": "Wohnout", "song": "Piju"},
            {"artist": "Tři sestry", "song": "Punk rock rádio"},
            {"artist": "Tři sestry", "song": "Alkohol"},
        ],
        "classic": [
            {"artist": "Karel Gott", "song": "Lady Carneval"},
            {"artist": "Karel Gott", "song": "Včelka Mája"},
            {"artist": "Karel Gott", "song": "Lásko"},
            {"artist": "Karel Gott", "song": "Když milenky pláčou"},
            {"artist": "Karel Gott", "song": "Okno mé lásky"},
            {"artist": "Karel Gott", "song": "Bum bum bum"},
            {"artist": "Karel Gott", "song": "Být stále mlád"},
            {"artist": "Karel Gott", "song": "Trezor"},
            {"artist": "Karel Gott", "song": "Pábitelé"},
            {"artist": "Karel Gott", "song": "Čau lásko"},
            {"artist": "Waldemar Matuška", "song": "Holubí dům"},
            {"artist": "Waldemar Matuška", "song": "Rosa na kolejích"},
            {"artist": "Waldemar Matuška", "song": "Pod lípou"},
            {"artist": "Waldemar Matuška", "song": "Tisíc mil"},
            {"artist": "Ivan Mládek", "song": "Jožin z bažin"},
            {"artist": "Ivan Mládek", "song": "Báječnej chlap"},
            {"artist": "Ivan Mládek", "song": "Mě to nebaví"},
            {"artist": "Ivan Mládek", "song": "Nashledanou"},
            {"artist": "Marta Kubišová", "song": "Být stále mlád"},
            {"artist": "Marta Kubišová", "song": "Modlitba pro Martu"},
            {"artist": "Marta Kubišová", "song": "Zvony"},
            {"artist": "Olympic", "song": "Těžkej den"},
            {"artist": "Olympic", "song": "Dej mi víc"},
            {"artist": "Olympic", "song": "Jasná zpráva"},
            {"artist": "Olympic", "song": "Želva"},
            {"artist": "Karel Kryl", "song": "Pane prezidente"},
            {"artist": "Karel Kryl", "song": "Bratříčku"},
            {"artist": "Karel Kryl", "song": "Anděl"},
            {"artist": "Karel Kryl", "song": "Slib"},
            {"artist": "Hana Zagorová", "song": "Nemám strach"},
            {"artist": "Hana Zagorová", "song": "Linka lásky"},
            {"artist": "Hana Zagorová", "song": "Obrázky"},
            {"artist": "Helena Vondráčková", "song": "Dlouhá noc"},
            {"artist": "Helena Vondráčková", "song": "Jordán"},
            {"artist": "Helena Vondráčková", "song": "Lásko má"},
            {"artist": "Michal David", "song": "Nonstop"},
            {"artist": "Michal David", "song": "Discopříběh"},
            {"artist": "Michal David", "song": "Céčka"},
            {"artist": "Jaromír Nohavica", "song": "Těšínská"},
            {"artist": "Jaromír Nohavica", "song": "Mikymauz"},
            {"artist": "Jaromír Nohavica", "song": "Ladovská zima"},
            {"artist": "Jaromír Nohavica", "song": "Kometa"},
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

# ============== Bot Settings API ==============

class BotSettings(BaseModel):
    notificationChannelId: str = "1468355022159872073"
    pingRoleId: str = "485172457544744972"
    xpPerQuiz: int = 25
    xpPerTruth: int = 15
    xpPer10Min: int = 5
    xpDailyLimit: int = 200
    xpUnlockBonus: int = 25
    dailyBonus: int = 100
    streakBonus: int = 10
    autoDeleteSeconds: int = 60
    adminOnlyQuiz: bool = True

@api_router.get("/bot/stats")
async def get_bot_stats():
    """Get bot statistics"""
    try:
        total_users = await db.game_users.count_documents({})
        
        # Get total XP
        pipeline = [{"$group": {"_id": None, "total_xp": {"$sum": "$xp"}}}]
        result = await db.game_users.aggregate(pipeline).to_list(1)
        total_xp = result[0]["total_xp"] if result else 0
        
        # Get total games
        pipeline2 = [{"$group": {"_id": None, "total_games": {"$sum": "$total_games"}}}]
        result2 = await db.game_users.aggregate(pipeline2).to_list(1)
        total_games = result2[0]["total_games"] if result2 else 0
        
        # Active today (simplified - users with recent activity)
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        active_today = await db.game_users.count_documents({
            "last_daily": {"$gte": today.isoformat()}
        })
        
        # Get guild count from bot stats
        bot_stats = await db.bot_stats.find_one({"type": "global"}, {"_id": 0})
        guild_count = bot_stats.get("guild_count", 0) if bot_stats else 0
        
        return {
            "totalUsers": total_users,
            "totalXp": total_xp,
            "totalGames": total_games,
            "activeToday": active_today,
            "guildCount": guild_count
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {
            "totalUsers": 0,
            "totalXp": 0,
            "totalGames": 0,
            "activeToday": 0,
            "guildCount": 0
        }

@api_router.get("/bot/settings")
async def get_bot_settings():
    """Get bot settings"""
    settings = await db.bot_settings.find_one({"type": "global"}, {"_id": 0})
    if not settings:
        return BotSettings().dict()
    return settings

@api_router.post("/bot/settings")
async def update_bot_settings(settings: BotSettings):
    """Update bot settings"""
    data = settings.dict()
    data["type"] = "global"
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.bot_settings.update_one(
        {"type": "global"},
        {"$set": data},
        upsert=True
    )
    
    return {"success": True, "message": "Nastavení uloženo"}

@api_router.get("/bot/guilds")
async def get_bot_guilds():
    """Get list of guilds where bot is active"""
    try:
        bot_stats = await db.bot_stats.find_one({"type": "global"}, {"_id": 0})
        guilds_data = await db.bot_guilds.find({}, {"_id": 0}).to_list(100)
        
        if guilds_data:
            return guilds_data
        
        # Fallback - return empty or mock data
        return []
    except Exception as e:
        logger.error(f"Guilds error: {e}")
        return []

# ============== Discord OAuth ==============

@api_router.post("/discord/callback")
async def discord_oauth_callback(request: Request):
    """Handle Discord OAuth callback"""
    data = await request.json()
    code = data.get("code")
    redirect_uri = data.get("redirect_uri")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")
    
    client_id = os.environ.get("DISCORD_CLIENT_ID", "1336454706620063826")
    client_secret = os.environ.get("DISCORD_CLIENT_SECRET", "")
    
    # Exchange code for token
    async with httpx.AsyncClient() as client:
        try:
            # Get access token
            token_response = await client.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token error: {token_response.text}")
                raise HTTPException(status_code=401, detail="Failed to get token")
            
            token_data = token_response.json()
            access_token = token_data["access_token"]
            
            # Get user info
            user_response = await client.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_data = user_response.json()
            
            # Get user guilds
            guilds_response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            guilds_data = guilds_response.json()
            
            # Format user
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_data['id']}/{user_data['avatar']}.png" if user_data.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"
            
            user = {
                "id": user_data["id"],
                "username": user_data["username"],
                "avatar": avatar_url,
                "discriminator": user_data.get("discriminator", "0")
            }
            
            return {
                "user": user,
                "guilds": guilds_data
            }
            
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/bot/settings/{guild_id}")
async def update_guild_bot_settings(guild_id: str, request: Request):
    """Update bot settings for specific guild"""
    data = await request.json()
    data["guild_id"] = guild_id
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.guild_bot_settings.update_one(
        {"guild_id": guild_id},
        {"$set": data},
        upsert=True
    )
    
    return {"success": True, "message": "Nastavení serveru uloženo"}

# ============== Health Check ==============

@api_router.get("/")
async def root():
    return {"message": "Bot Dashboard API", "status": "online"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ============== Leaderboard & Profiles ==============

@api_router.get("/leaderboard")
async def get_leaderboard(limit: int = 50):
    """Get top players across all servers"""
    try:
        players = await db.game_users.find(
            {},
            {"_id": 0, "user_id": 1, "name": 1, "xp": 1, "level": 1, "total_games": 1, "total_correct": 1, "streak": 1}
        ).sort("xp", -1).limit(limit).to_list(limit)
        
        return players
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return []

@api_router.get("/player/{user_id}")
async def get_player_profile(user_id: str):
    """Get detailed player profile"""
    try:
        player = await db.game_users.find_one(
            {"user_id": int(user_id)},
            {"_id": 0}
        )
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        return player
    except Exception as e:
        logger.error(f"Player profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/player/{user_id}/history")
async def get_player_history(user_id: str, limit: int = 20):
    """Get player quiz history"""
    try:
        history = await db.quiz_history.find(
            {"user_id": int(user_id)},
            {"_id": 0}
        ).sort("date", -1).limit(limit).to_list(limit)
        
        return history
    except Exception as e:
        logger.error(f"Player history error: {e}")
        return []

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
