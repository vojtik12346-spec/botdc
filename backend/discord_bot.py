#!/usr/bin/env python3
"""
Valhalla Bot - Discord kvízy a XP systém
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import os
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import uuid
import math

# Auto-install FFmpeg if not present
def ensure_ffmpeg():
    """Ensure FFmpeg is installed"""
    if not shutil.which('ffmpeg'):
        print("⚠️ FFmpeg not found, installing...", flush=True)
        try:
            subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
            subprocess.run(['apt-get', 'install', '-y', 'ffmpeg'], check=True, capture_output=True)
            print("✅ FFmpeg installed successfully!", flush=True)
        except Exception as e:
            print(f"❌ Failed to install FFmpeg: {e}", flush=True)
    else:
        print("✅ FFmpeg is available", flush=True)

ensure_ffmpeg()

load_dotenv()

# MongoDB setup for XP system
from pymongo import MongoClient

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "quiz_bot")
mongo_client = MongoClient(mongo_url)
db = mongo_client[db_name]
users_collection = db["game_users"]
server_stats_collection = db["server_stats"]  # Pro statistiky serveru

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True  # Pro sledování her
intents.members = True    # Pro sledování členů
intents.voice_states = True  # Pro sledování voice aktivity

bot = commands.Bot(command_prefix='!', intents=intents)

# ============== COMMAND LOGGING ==============

@bot.event
async def on_app_command_completion(interaction: discord.Interaction, command: discord.app_commands.Command):
    """Logování všech slash příkazů"""
    channel_name = interaction.channel.name if interaction.channel else "DM"
    user_name = interaction.user.display_name
    guild_name = interaction.guild.name if interaction.guild else "DM"
    
    # Získej parametry příkazu
    params = ""
    if interaction.namespace:
        param_list = []
        for key, value in vars(interaction.namespace).items():
            if value is not None:
                param_list.append(f"{key}={value}")
        if param_list:
            params = f" ({', '.join(param_list)})"
    
    print(f"[CMD] /{command.name}{params} | {user_name} | #{channel_name} | {guild_name}", flush=True)

# ============== GAME TRACKING SYSTEM ==============

# Bonusové hry - při prvním hraní dostane hráč +25 XP bonus
BONUS_GAMES = {
    # Populární hry
    "Counter-Strike 2": {"emoji": "🎯", "category": "FPS"},
    "Minecraft": {"emoji": "⛏️", "category": "Sandbox"},
    "Fortnite": {"emoji": "🏝️", "category": "Battle Royale"},
    "League of Legends": {"emoji": "⚔️", "category": "MOBA"},
    "VALORANT": {"emoji": "🔫", "category": "FPS"},
    "Apex Legends": {"emoji": "🦊", "category": "Battle Royale"},
    "Rocket League": {"emoji": "🚗", "category": "Sport"},
    "GTA V": {"emoji": "🚔", "category": "Akce"},
    "Grand Theft Auto V": {"emoji": "🚔", "category": "Akce"},
    "Roblox": {"emoji": "🧱", "category": "Sandbox"},
    "Overwatch 2": {"emoji": "🦸", "category": "FPS"},
    "Dota 2": {"emoji": "🗡️", "category": "MOBA"},
    "Call of Duty": {"emoji": "💣", "category": "FPS"},
    "Warzone": {"emoji": "💣", "category": "Battle Royale"},
    "FIFA 24": {"emoji": "⚽", "category": "Sport"},
    "EA SPORTS FC 24": {"emoji": "⚽", "category": "Sport"},
    "Destiny 2": {"emoji": "🌌", "category": "MMO"},
    "World of Warcraft": {"emoji": "🐉", "category": "MMO"},
    "Diablo IV": {"emoji": "😈", "category": "RPG"},
    "Path of Exile": {"emoji": "⚡", "category": "RPG"},
    "Elden Ring": {"emoji": "🗡️", "category": "RPG"},
    "Hogwarts Legacy": {"emoji": "🧙", "category": "RPG"},
    "Cyberpunk 2077": {"emoji": "🤖", "category": "RPG"},
    "The Witcher 3": {"emoji": "🐺", "category": "RPG"},
    "Baldur's Gate 3": {"emoji": "🎲", "category": "RPG"},
    "Terraria": {"emoji": "🌳", "category": "Sandbox"},
    "Stardew Valley": {"emoji": "🌾", "category": "Simulace"},
    "Among Us": {"emoji": "🚀", "category": "Party"},
    "Phasmophobia": {"emoji": "👻", "category": "Horor"},
    "Dead by Daylight": {"emoji": "🔪", "category": "Horor"},
    "Rust": {"emoji": "🏚️", "category": "Survival"},
    "ARK: Survival Evolved": {"emoji": "🦖", "category": "Survival"},
    "Sea of Thieves": {"emoji": "🏴‍☠️", "category": "Dobrodružství"},
    "Euro Truck Simulator 2": {"emoji": "🚛", "category": "Simulace"},
    "Cities: Skylines": {"emoji": "🏙️", "category": "Simulace"},
    "The Sims 4": {"emoji": "🏠", "category": "Simulace"},
    "Spotify": {"emoji": "🎵", "category": "Hudba"},
    "YouTube": {"emoji": "📺", "category": "Video"},
    "Visual Studio Code": {"emoji": "💻", "category": "Kódování"},
    "Escape from Tarkov": {"emoji": "🎒", "category": "FPS"},
    "Rainbow Six Siege": {"emoji": "🛡️", "category": "FPS"},
    "Lethal Company": {"emoji": "💀", "category": "Horor"},
    "Palworld": {"emoji": "🐾", "category": "Survival"},
    "Helldivers 2": {"emoji": "🪖", "category": "Akce"},
    "FiveM": {"emoji": "🚔", "category": "RP"},
}

# Úkoly pro každou hru - {minuty: {"name": název, "xp": odměna}}
GAME_QUESTS = {
    # Každá hra má stejné základní úkoly podle času hraní
    "default": [
        {"minutes": 60, "name": "Nováček", "xp": 50, "emoji": "🌟"},
        {"minutes": 180, "name": "Hráč", "xp": 100, "emoji": "⭐"},
        {"minutes": 300, "name": "Veterán", "xp": 150, "emoji": "🏅"},
        {"minutes": 600, "name": "Expert", "xp": 250, "emoji": "🎖️"},
        {"minutes": 1200, "name": "Mistr", "xp": 400, "emoji": "👑"},
        {"minutes": 3000, "name": "Legenda", "xp": 750, "emoji": "🏆"},
        {"minutes": 6000, "name": "Bůh", "xp": 1500, "emoji": "⚡"},
    ],
    # Speciální úkoly pro konkrétní hry
    "Counter-Strike 2": [
        {"minutes": 60, "name": "První mise", "xp": 50, "emoji": "🎯"},
        {"minutes": 180, "name": "Střelec", "xp": 100, "emoji": "🔫"},
        {"minutes": 300, "name": "Taktik", "xp": 150, "emoji": "🗺️"},
        {"minutes": 600, "name": "Elite", "xp": 250, "emoji": "💎"},
        {"minutes": 1200, "name": "Global Elite", "xp": 400, "emoji": "🌍"},
        {"minutes": 3000, "name": "CS Veterán", "xp": 750, "emoji": "🎖️"},
        {"minutes": 6000, "name": "CS Legenda", "xp": 1500, "emoji": "👑"},
    ],
    "Minecraft": [
        {"minutes": 60, "name": "Kopáč", "xp": 50, "emoji": "⛏️"},
        {"minutes": 180, "name": "Stavitel", "xp": 100, "emoji": "🏠"},
        {"minutes": 300, "name": "Průzkumník", "xp": 150, "emoji": "🗺️"},
        {"minutes": 600, "name": "Dračí lovec", "xp": 250, "emoji": "🐉"},
        {"minutes": 1200, "name": "Mistr stavitel", "xp": 400, "emoji": "🏰"},
        {"minutes": 3000, "name": "Minecraft Veterán", "xp": 750, "emoji": "💎"},
        {"minutes": 6000, "name": "Minecraft Bůh", "xp": 1500, "emoji": "⚡"},
    ],
    "League of Legends": [
        {"minutes": 60, "name": "Summoner", "xp": 50, "emoji": "⚔️"},
        {"minutes": 180, "name": "Ranked Warrior", "xp": 100, "emoji": "🛡️"},
        {"minutes": 300, "name": "Diamant", "xp": 150, "emoji": "💎"},
        {"minutes": 600, "name": "Master", "xp": 250, "emoji": "🏅"},
        {"minutes": 1200, "name": "Grandmaster", "xp": 400, "emoji": "👑"},
        {"minutes": 3000, "name": "Challenger", "xp": 750, "emoji": "🏆"},
        {"minutes": 6000, "name": "LoL Legenda", "xp": 1500, "emoji": "⚡"},
    ],
    "Fortnite": [
        {"minutes": 60, "name": "Přistání", "xp": 50, "emoji": "🪂"},
        {"minutes": 180, "name": "Přeživší", "xp": 100, "emoji": "🏝️"},
        {"minutes": 300, "name": "Stavitel", "xp": 150, "emoji": "🏗️"},
        {"minutes": 600, "name": "Victory Royale", "xp": 250, "emoji": "🏆"},
        {"minutes": 1200, "name": "Fortnite Pro", "xp": 400, "emoji": "👑"},
        {"minutes": 3000, "name": "Fortnite Veterán", "xp": 750, "emoji": "🎖️"},
        {"minutes": 6000, "name": "Fortnite Legenda", "xp": 1500, "emoji": "⚡"},
    ],
    "VALORANT": [
        {"minutes": 60, "name": "Agent", "xp": 50, "emoji": "🔫"},
        {"minutes": 180, "name": "Taktik", "xp": 100, "emoji": "🎯"},
        {"minutes": 300, "name": "Radiant hráč", "xp": 150, "emoji": "💎"},
        {"minutes": 600, "name": "Immortal", "xp": 250, "emoji": "🏅"},
        {"minutes": 1200, "name": "Radiant", "xp": 400, "emoji": "👑"},
        {"minutes": 3000, "name": "Valorant Pro", "xp": 750, "emoji": "🏆"},
        {"minutes": 6000, "name": "Valorant Legenda", "xp": 1500, "emoji": "⚡"},
    ],
    "GTA V": [
        {"minutes": 60, "name": "Gangster", "xp": 50, "emoji": "🚗"},
        {"minutes": 180, "name": "Zločinec", "xp": 100, "emoji": "💰"},
        {"minutes": 300, "name": "Šéf gangu", "xp": 150, "emoji": "🔫"},
        {"minutes": 600, "name": "Kingpin", "xp": 250, "emoji": "👑"},
        {"minutes": 1200, "name": "Los Santos Boss", "xp": 400, "emoji": "🏆"},
        {"minutes": 3000, "name": "GTA Veterán", "xp": 750, "emoji": "🎖️"},
        {"minutes": 6000, "name": "GTA Legenda", "xp": 1500, "emoji": "⚡"},
    ],
    "Rocket League": [
        {"minutes": 60, "name": "Rookie", "xp": 50, "emoji": "🚗"},
        {"minutes": 180, "name": "Pro", "xp": 100, "emoji": "⚽"},
        {"minutes": 300, "name": "Veteran", "xp": 150, "emoji": "🏅"},
        {"minutes": 600, "name": "Champion", "xp": 250, "emoji": "🏆"},
        {"minutes": 1200, "name": "Grand Champion", "xp": 400, "emoji": "👑"},
        {"minutes": 3000, "name": "Supersonic", "xp": 750, "emoji": "🚀"},
        {"minutes": 6000, "name": "RL Legenda", "xp": 1500, "emoji": "⚡"},
    ],
}

# Game XP settings
GAME_XP_PER_10_MIN = 5
GAME_XP_DAILY_LIMIT = 200
GAME_UNLOCK_BONUS = 25
GAME_NOTIFICATION_CHANNEL = 1468355022159872073  # Kanál pro herní notifikace
GAME_PING_ROLE = 485172457544744972  # Role pro ping při splnění

# Track active gaming sessions {user_id: {"game": name, "start": datetime, "guild_id": id}}
active_gaming_sessions = {}

# Collection pro persistentní herní sessions
game_sessions_collection = db["game_sessions"]

def save_game_session(user_id: int, guild_id: int, game: str, user_name: str):
    """Ulož herní session do databáze"""
    game_sessions_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "guild_id": guild_id,
            "game": game,
            "user_name": user_name,
            "start": datetime.now(timezone.utc)
        }},
        upsert=True
    )

def get_game_session(user_id: int) -> dict:
    """Načti herní session z databáze"""
    return game_sessions_collection.find_one({"user_id": user_id})

def delete_game_session(user_id: int):
    """Smaž herní session z databáze"""
    game_sessions_collection.delete_one({"user_id": user_id})

# Collection pro nastavení serveru
guild_settings_collection = db["guild_bot_settings"]

def get_guild_settings(guild_id: int) -> dict:
    """Získej nastavení pro server z databáze"""
    settings = guild_settings_collection.find_one({"guild_id": str(guild_id)})
    if not settings:
        # Výchozí nastavení
        return {
            "cmdHudba": True,
            "cmdFilm": True,
            "cmdPravda": True,
            "cmdGamelevel": False,
            "cmdTop": False,
            "cmdDaily": False,
            "cmdHry": False,
            "cmdUkoly": False,
            "cmdHerniinfo": True
        }
    return settings

def is_command_admin_only(guild_id: int, command_name: str) -> bool:
    """Zkontroluj zda příkaz vyžaduje admin oprávnění"""
    settings = get_guild_settings(guild_id)
    key = f"cmd{command_name.capitalize()}"
    return settings.get(key, False)

async def check_command_permission(interaction: discord.Interaction, command_name: str) -> bool:
    """Zkontroluj oprávnění pro příkaz. Vrátí True pokud může pokračovat."""
    if is_command_admin_only(interaction.guild_id, command_name):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Tento příkaz může použít pouze administrátor!",
                ephemeral=True
            )
            return False
    return True

# ============== XP/LEVEL SYSTEM ==============

def calculate_level(xp: int) -> int:
    """Calculate level from XP (level = sqrt(xp/100))"""
    if xp <= 0:
        return 1
    return max(1, int(math.sqrt(xp / 100)) + 1)

def xp_for_level(level: int) -> int:
    """Calculate XP needed for a specific level"""
    if level <= 1:
        return 0
    return ((level - 1) ** 2) * 100

def get_user_data(guild_id: int, user_id: int) -> dict:
    """Get or create user data"""
    user = users_collection.find_one({"guild_id": guild_id, "user_id": user_id})
    if not user:
        user = {
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": 0,
            "total_correct": 0,
            "total_games": 0,
            "streak": 0,
            "last_daily": None,
            "daily_game_xp": 0,
            "last_game_xp_reset": None,
            "unlocked_games": [],
            "completed_quests": {},  # {game_name: [completed_quest_indices]}
            "game_times": {},  # {game_name: minutes}
            "total_game_time": 0,  # v minutách
            "created_at": datetime.now(timezone.utc)
        }
        users_collection.insert_one(user)
    return user

def get_game_quests(game_name: str) -> list:
    """Get quests for a specific game"""
    if game_name in GAME_QUESTS:
        return GAME_QUESTS[game_name]
    return GAME_QUESTS["default"]

def get_game_time(guild_id: int, user_id: int, game_name: str) -> int:
    """Get total time played for a specific game"""
    user = get_user_data(guild_id, user_id)
    return user.get("game_times", {}).get(game_name, 0)

async def check_and_complete_quests(guild_id: int, user_id: int, user_name: str, game_name: str, total_minutes: int, channel=None):
    """Check if any quests are completed and give rewards"""
    user = get_user_data(guild_id, user_id)
    completed = user.get("completed_quests", {}).get(game_name, [])
    quests = get_game_quests(game_name)
    
    newly_completed = []
    total_xp = 0
    
    for i, quest in enumerate(quests):
        if i not in completed and total_minutes >= quest["minutes"]:
            newly_completed.append(i)
            total_xp += quest["xp"]
    
    if newly_completed:
        # Update completed quests
        users_collection.update_one(
            {"guild_id": guild_id, "user_id": user_id},
            {"$set": {f"completed_quests.{game_name}": completed + newly_completed}}
        )
        
        # Add XP
        await add_xp(guild_id, user_id, user_name, total_xp, None)
        
        # Send notification to game channel
        notify_channel = channel
        if not notify_channel:
            notify_channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
        
        if notify_channel:
            for i in newly_completed:
                quest = quests[i]
                game_emoji = BONUS_GAMES.get(game_name, {}).get("emoji", "🎮")
                
                embed = discord.Embed(
                    title=f"🎯 ÚKOL SPLNĚN!",
                    description=f"**{user_name}** splnil/a úkol v **{game_name}**!",
                    color=discord.Color.gold()
                )
                embed.add_field(name=f"{quest['emoji']} Úkol", value=quest["name"], inline=True)
                embed.add_field(name="✨ Odměna", value=f"+{quest['xp']} XP", inline=True)
                embed.add_field(name="⏱️ Čas", value=f"{total_minutes // 60}h {total_minutes % 60}m", inline=True)
                embed.set_footer(text="⚔️ Valhalla Bot • Plň další úkoly a získávej XP!")
                await notify_channel.send(f"<@&{GAME_PING_ROLE}>", embed=embed)
    
    return total_xp

def get_daily_game_xp(guild_id: int, user_id: int) -> int:
    """Get how much game XP user earned today"""
    user = get_user_data(guild_id, user_id)
    last_reset = user.get("last_game_xp_reset")
    
    if last_reset:
        if isinstance(last_reset, str):
            last_reset = datetime.fromisoformat(last_reset.replace('Z', '+00:00'))
        
        # Ensure timezone aware
        if last_reset.tzinfo is None:
            last_reset = last_reset.replace(tzinfo=timezone.utc)
        
        # Reset if new day
        if (datetime.now(timezone.utc) - last_reset).days >= 1:
            users_collection.update_one(
                {"guild_id": guild_id, "user_id": user_id},
                {"$set": {"daily_game_xp": 0, "last_game_xp_reset": datetime.now(timezone.utc).isoformat()}}
            )
            return 0
    
    return user.get("daily_game_xp", 0)

async def add_game_xp(guild_id: int, user_id: int, user_name: str, minutes: int, game_name: str = None, channel=None):
    """Add XP for gaming time"""
    # Calculate XP (5 XP per 10 minutes)
    xp_earned = (minutes // 10) * GAME_XP_PER_10_MIN
    
    if xp_earned <= 0:
        return 0
    
    # Check daily limit
    daily_xp = get_daily_game_xp(guild_id, user_id)
    remaining = GAME_XP_DAILY_LIMIT - daily_xp
    
    if remaining <= 0:
        return 0
    
    # Cap XP at remaining limit
    xp_earned = min(xp_earned, remaining)
    
    # Update daily game XP and game-specific time
    update_query = {
        "$inc": {"daily_game_xp": xp_earned, "total_game_time": minutes},
        "$set": {"last_game_xp_reset": datetime.now(timezone.utc).isoformat()}
    }
    
    if game_name:
        update_query["$inc"][f"game_times.{game_name}"] = minutes
    
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        update_query
    )
    
    # Add to total XP
    await add_xp(guild_id, user_id, user_name, xp_earned, channel)
    
    # Check for quest completion
    if game_name:
        user = get_user_data(guild_id, user_id)
        total_game_time = user.get("game_times", {}).get(game_name, 0) + minutes
        await check_and_complete_quests(guild_id, user_id, user_name, game_name, total_game_time, channel)
    
    return xp_earned

async def unlock_game(guild_id: int, user_id: int, user_name: str, game_name: str, channel=None) -> bool:
    """Unlock a bonus game and give bonus XP. Returns True if newly unlocked."""
    user = get_user_data(guild_id, user_id)
    unlocked = user.get("unlocked_games", [])
    
    if game_name in unlocked:
        return False
    
    # Unlock the game
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$push": {"unlocked_games": game_name}}
    )
    
    # Give bonus XP
    await add_xp(guild_id, user_id, user_name, GAME_UNLOCK_BONUS, None)
    
    # Send notification with role ping - VŽDY do správného kanálu
    notify_channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
    if notify_channel and game_name in BONUS_GAMES:
        game_info = BONUS_GAMES[game_name]
        embed = discord.Embed(
            title="🎮 HRA ODEMČENA!",
            description=f"**{user_name}** odemkl/a hru **{game_name}**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="🏷️ Kategorie", value=game_info["category"], inline=True)
        embed.add_field(name="✨ Bonus", value=f"+{GAME_UNLOCK_BONUS} XP", inline=True)
        embed.set_footer(text="Hraj více her a odemykej achievementy!")
        await notify_channel.send(f"<@&{GAME_PING_ROLE}>", embed=embed)
    
    return True

async def add_xp(guild_id: int, user_id: int, user_name: str, xp_amount: int, channel=None) -> bool:
    """Add XP to user and check for level up. Returns True if leveled up."""
    user = get_user_data(guild_id, user_id)
    old_level = calculate_level(user["xp"])
    new_xp = user["xp"] + xp_amount
    new_level = calculate_level(new_xp)
    
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": {"xp": new_xp, "name": user_name}}
    )
    
    # Level up notification - vždy do správného kanálu
    if new_level > old_level:
        notify_channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
        if notify_channel:
            embed = discord.Embed(
                title="🎉 LEVEL UP!",
                description=f"**{user_name}** dosáhl/a **Level {new_level}**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="✨ XP", value=f"{new_xp} XP", inline=True)
            embed.add_field(name="📈 Další level", value=f"{xp_for_level(new_level + 1)} XP", inline=True)
            await notify_channel.send(embed=embed)
        return True
    return False

def increment_stats(guild_id: int, user_id: int, correct: bool = False):
    """Increment user game statistics"""
    update = {"$inc": {"total_games": 1}}
    if correct:
        update["$inc"]["total_correct"] = 1
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        update
    )

# XP rewards
XP_REWARDS = {
    "quiz_correct": 25,      # Správná odpověď v kvízu
    "quiz_win": 50,          # Výhra v kvízu (nejvíc bodů)
    "truth_correct": 15,     # Správná odpověď pravda/lež
    "daily": 100,            # Denní bonus
    "streak_bonus": 10,      # Bonus za streak (per den)
}

# ============== COUNTDOWN FUNCTIONS ==============

def parse_time(time_str: str) -> int:
    """Parse time string like 2m, 5m, 1h into seconds"""
    time_str = time_str.lower().strip()
    
    pattern = r'^(\d+)([smhd])$'
    match = re.match(pattern, time_str)
    
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    return value * multipliers[unit]

def format_time(seconds: int) -> str:
    """Format seconds into readable string"""
    if seconds <= 0:
        return "0s"
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)

# Auto-delete helper
async def delete_after(message, seconds: int = 60):
    """Delete message after specified seconds (default 1 min)"""
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass

# Store active countdowns
active_countdowns = {}

class CountdownView(discord.ui.View):
    def __init__(self, countdown_id: str, user_id: int):
        super().__init__(timeout=None)
        self.countdown_id = countdown_id
        self.user_id = user_id
    
    @discord.ui.button(label="Zrušit", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Pouze autor nebo admin může zrušit odpočet!", ephemeral=True)
            return
        
        if self.countdown_id in active_countdowns:
            active_countdowns[self.countdown_id]["cancelled"] = True
            del active_countdowns[self.countdown_id]
        
        button.disabled = True
        button.label = "Zrušeno"
        
        embed = discord.Embed(
            title="❌ Odpočet zrušen!",
            description=f"Odpočet byl zrušen uživatelem {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

async def run_countdown(channel, message, end_time: int, countdown_id: str, author: discord.Member, reason: str):
    """Run the countdown and update message"""
    
    while True:
        if countdown_id not in active_countdowns:
            return
        
        if active_countdowns[countdown_id].get("cancelled"):
            return
        
        remaining = end_time - int(datetime.now(timezone.utc).timestamp())
        
        if remaining <= 0:
            break
        
        embed = discord.Embed(
            title="⏰ ODPOČET",
            description=f"**{reason}**" if reason else "Odpočet běží...",
            color=discord.Color.blue()
        )
        embed.add_field(name="⏳ Zbývá", value=f"**{format_time(remaining)}**", inline=True)
        embed.add_field(name="👤 Spustil", value=author.mention, inline=True)
        embed.set_footer(text=f"Končí: {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
        
        try:
            await message.edit(embed=embed)
        except:
            pass
        
        if remaining > 3600:
            await asyncio.sleep(60)
        elif remaining > 60:
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(1)
    
    # Countdown finished!
    if countdown_id in active_countdowns:
        del active_countdowns[countdown_id]
    
    embed = discord.Embed(
        title="🎉 ODPOČET SKONČIL!",
        description=f"**{reason}**" if reason else "Čas vypršel!",
        color=discord.Color.green()
    )
    embed.add_field(name="👤 Spustil", value=author.mention, inline=True)
    
    view = discord.ui.View()
    disabled_btn = discord.ui.Button(label="Dokončeno", style=discord.ButtonStyle.success, disabled=True, emoji="✅")
    view.add_item(disabled_btn)
    
    try:
        await message.edit(embed=embed, view=view)
    except:
        pass
    
    # Ping notification
    await channel.send(f"🔔 **ODPOČET SKONČIL!** {author.mention}\n{'📢 ' + reason if reason else ''}")

# ============== EVENTS ==============

@bot.event
async def on_ready():
    print(f'🤖 Bot {bot.user} je online!', flush=True)
    print(f'📊 Připojen k {len(bot.guilds)} serverům', flush=True)
    
    # Načti aktivní herní sessions z databáze
    stored_sessions = list(game_sessions_collection.find({}))
    for session in stored_sessions:
        user_id = session.get("user_id")
        if user_id:
            active_gaming_sessions[user_id] = {
                "game": session.get("game"),
                "start": session.get("start"),
                "guild_id": session.get("guild_id"),
                "user_name": session.get("user_name")
            }
    print(f'🎮 Načteno {len(stored_sessions)} aktivních herních sessions', flush=True)
    
    # Uložit statistiky bota do databáze
    users_collection.database.bot_stats.update_one(
        {"type": "global"},
        {"$set": {
            "guild_count": len(bot.guilds),
            "bot_name": str(bot.user),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    # Uložit seznam serverů
    for guild in bot.guilds:
        users_collection.database.bot_guilds.update_one(
            {"id": str(guild.id)},
            {"$set": {
                "id": str(guild.id),
                "name": guild.name,
                "icon": str(guild.icon.url) if guild.icon else None,
                "memberCount": guild.member_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synchronizováno {len(synced)} slash příkazů', flush=True)
    except Exception as e:
        print(f'❌ Chyba při synchronizaci: {e}', flush=True)

# ============== SERVER STATS SYSTEM ==============

# Voice tracking - kdo kdy vstoupil do voice
voice_sessions = {}  # {user_id: {"join_time": datetime, "channel_id": int, "guild_id": int}}

def get_server_stats(guild_id: int) -> dict:
    """Získej nebo vytvoř statistiky serveru"""
    stats = server_stats_collection.find_one({"guild_id": guild_id})
    if not stats:
        stats = {
            "guild_id": guild_id,
            "total_messages": 0,
            "total_voice_minutes": 0,
            "user_messages": {},  # {user_id: count}
            "user_voice": {},     # {user_id: minutes}
            "daily_messages": 0,
            "daily_voice": 0,
            "last_reset": datetime.now(timezone.utc).isoformat()
        }
        server_stats_collection.insert_one(stats)
    return stats

def increment_message_count(guild_id: int, user_id: int, user_name: str):
    """Přidej zprávu do statistik"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    server_stats_collection.update_one(
        {"guild_id": guild_id},
        {
            "$inc": {
                "total_messages": 1,
                "daily_messages": 1,
                f"user_messages.{user_id}": 1,
                f"daily_user_messages.{today}.{user_id}": 1
            },
            "$set": {
                f"user_names.{user_id}": user_name
            }
        },
        upsert=True
    )

def add_voice_time(guild_id: int, user_id: int, user_name: str, minutes: int):
    """Přidej voice čas do statistik"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    server_stats_collection.update_one(
        {"guild_id": guild_id},
        {
            "$inc": {
                "total_voice_minutes": minutes,
                "daily_voice": minutes,
                f"user_voice.{user_id}": minutes,
                f"daily_user_voice.{today}.{user_id}": minutes
            },
            "$set": {
                f"user_names.{user_id}": user_name
            }
        },
        upsert=True
    )

@bot.event
async def on_voice_state_update(member, before, after):
    """Sledování voice aktivity"""
    if member.bot:
        return
    
    user_id = member.id
    guild_id = member.guild.id
    
    # Uživatel vstoupil do voice kanálu
    if before.channel is None and after.channel is not None:
        voice_sessions[user_id] = {
            "join_time": datetime.now(timezone.utc),
            "channel_id": after.channel.id,
            "guild_id": guild_id
        }
        print(f"[VOICE] {member.display_name} vstoupil do {after.channel.name}", flush=True)
    
    # Uživatel opustil voice kanál
    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions:
            session = voice_sessions[user_id]
            duration = datetime.now(timezone.utc) - session["join_time"]
            minutes = int(duration.total_seconds() / 60)
            
            if minutes > 0:
                add_voice_time(guild_id, user_id, member.display_name, minutes)
                print(f"[VOICE] {member.display_name} byl ve voice {minutes} minut", flush=True)
            
            del voice_sessions[user_id]
    
    # Uživatel přešel do jiného kanálu
    elif before.channel != after.channel:
        if user_id in voice_sessions:
            session = voice_sessions[user_id]
            duration = datetime.now(timezone.utc) - session["join_time"]
            minutes = int(duration.total_seconds() / 60)
            
            if minutes > 0:
                add_voice_time(guild_id, user_id, member.display_name, minutes)
            
            voice_sessions[user_id] = {
                "join_time": datetime.now(timezone.utc),
                "channel_id": after.channel.id,
                "guild_id": guild_id
            }

class ServerStatsView(discord.ui.View):
    def __init__(self, guild_id: int, period: int = 1):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.period = period  # 1, 7, 30 dnů
    
    @discord.ui.button(label="1 den", style=discord.ButtonStyle.secondary, custom_id="stats_1d", emoji="📊")
    async def stats_1d(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = 1
        await self.update_stats(interaction)
    
    @discord.ui.button(label="7 dní", style=discord.ButtonStyle.secondary, custom_id="stats_7d", emoji="📈")
    async def stats_7d(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = 7
        await self.update_stats(interaction)
    
    @discord.ui.button(label="30 dní", style=discord.ButtonStyle.secondary, custom_id="stats_30d", emoji="📉")
    async def stats_30d(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.period = 30
        await self.update_stats(interaction)
    
    @discord.ui.button(label="Obnovit", style=discord.ButtonStyle.primary, custom_id="stats_refresh", emoji="🔄")
    async def stats_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_stats(interaction)
    
    async def update_stats(self, interaction: discord.Interaction):
        embed = await create_stats_embed(interaction.guild, self.period)
        
        # Update button styles
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == f"stats_{self.period}d":
                    child.style = discord.ButtonStyle.success
                elif child.custom_id != "stats_refresh":
                    child.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(embed=embed, view=self)

async def create_stats_embed(guild, period: int = 1) -> discord.Embed:
    """Vytvoří embed se statistikami"""
    stats = get_server_stats(guild.id)
    
    # Základní statistiky
    total_members = guild.member_count
    online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
    total_messages = stats.get("total_messages", 0)
    total_voice = stats.get("total_voice_minutes", 0)
    daily_messages = stats.get("daily_messages", 0)
    daily_voice = stats.get("daily_voice", 0)
    
    # Období text
    period_text = f"Posledních {period} {'den' if period == 1 else 'dní'}"
    
    # Formátování voice času
    voice_hours = total_voice // 60
    voice_mins = total_voice % 60
    daily_voice_hours = daily_voice // 60
    daily_voice_mins = daily_voice % 60
    
    # Top 5 pisatelů
    user_messages = stats.get("user_messages", {})
    user_names = stats.get("user_names", {})
    sorted_messages = sorted(user_messages.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Top 5 voice aktivita
    user_voice = stats.get("user_voice", {})
    sorted_voice = sorted(user_voice.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Vytvoř embed
    embed = discord.Embed(
        title=f"📊 Server Lookback: {period_text}",
        description=f"**{guild.name}**",
        color=discord.Color.blue()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    # Základní stats
    embed.add_field(
        name="👥 Členové",
        value=f"```\n{total_members} celkem\n{online_members} online\n```",
        inline=True
    )
    embed.add_field(
        name="💬 Zprávy",
        value=f"```\n{total_messages:,} celkem\n{daily_messages:,} dnes\n```",
        inline=True
    )
    embed.add_field(
        name="🎤 Voice",
        value=f"```\n{voice_hours}h {voice_mins}m celkem\n{daily_voice_hours}h {daily_voice_mins}m dnes\n```",
        inline=True
    )
    
    # Top pisatelé
    if sorted_messages:
        top_writers = []
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, (uid, count) in enumerate(sorted_messages):
            name = user_names.get(uid, f"User {uid}")[:15]
            top_writers.append(f"{medals[i]} **{name}**: {count:,}")
        embed.add_field(
            name="✍️ TOP Pisatelé",
            value="\n".join(top_writers),
            inline=True
        )
    
    # Top voice
    if sorted_voice:
        top_voice = []
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, (uid, mins) in enumerate(sorted_voice):
            name = user_names.get(uid, f"User {uid}")[:15]
            h = mins // 60
            m = mins % 60
            time_str = f"{h}h {m}m" if h > 0 else f"{m}m"
            top_voice.append(f"{medals[i]} **{name}**: {time_str}")
        embed.add_field(
            name="🎤 TOP Voice",
            value="\n".join(top_voice),
            inline=True
        )
    
    # Aktivní ve voice právě teď
    voice_now = sum(1 for vc in guild.voice_channels for m in vc.members if not m.bot)
    embed.add_field(
        name="🔊 Právě ve voice",
        value=f"**{voice_now}** členů",
        inline=True
    )
    
    embed.set_footer(text=f"⚔️ Valhalla Bot • Aktualizováno: {datetime.now().strftime('%H:%M:%S')}")
    
    return embed

@bot.tree.command(name="serverstats", description="Zobraz statistiky serveru (jen admin)")
@app_commands.checks.has_permissions(administrator=True)
async def server_stats_command(interaction: discord.Interaction):
    """Zobrazí statistiky serveru s interaktivními tlačítky"""
    embed = await create_stats_embed(interaction.guild, 1)
    view = ServerStatsView(interaction.guild.id, 1)
    
    # Nastav první tlačítko jako aktivní
    view.children[0].style = discord.ButtonStyle.success
    
    await interaction.response.send_message(embed=embed, view=view)

@server_stats_command.error
async def server_stats_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Tento příkaz může použít pouze administrátor!", ephemeral=True)

# ============== MUSIC SYSTEM ==============

import yt_dlp
import subprocess
import os
import aiohttp

# Poznámka: YouTube je blokovaný na cloudových serverech
# Tento systém podporuje přímé audio URL a některé další zdroje

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '/tmp/music_%(id)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'extract_flat': False,
}

FFMPEG_OPTIONS = {
    'options': '-vn',
}

FFMPEG_EXECUTABLE = '/usr/bin/ffmpeg'

# Předdefinované radio streamy
RADIO_STREAMS = {
    # České stanice
    "evropa2": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/EVROPA2.mp3", "name": "🇨🇿 Evropa 2", "category": "cz"},
    "frekvence1": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/FREKVENCE1.mp3", "name": "🇨🇿 Frekvence 1", "category": "cz"},
    "impuls": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/IMPULS.mp3", "name": "🇨🇿 Rádio Impuls", "category": "cz"},
    "kiss": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/KISS_CZAAC.aac", "name": "🇨🇿 Kiss Rádio", "category": "cz"},
    "blanik": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/BLANIK.mp3", "name": "🇨🇿 Rádio Blaník", "category": "cz"},
    "beat": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/BEAT.mp3", "name": "🇨🇿 Radio Beat", "category": "cz"},
    "country": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/COUNTRY_RADIO.mp3", "name": "🇨🇿 Country Radio", "category": "cz"},
    "rockzone": {"url": "https://playerservices.streamtheworld.com/api/livestream-redirect/ROCKZONE_128.mp3", "name": "🇨🇿 Rock Zone", "category": "cz"},
    
    # Lo-Fi & Chill
    "lofi": {"url": "https://streams.ilovemusic.de/iloveradio17.mp3", "name": "😴 Lo-Fi Hip Hop", "category": "chill"},
    "chillout": {"url": "https://streams.ilovemusic.de/iloveradio7.mp3", "name": "🌴 Chill Out", "category": "chill"},
    "sleep": {"url": "https://streams.ilovemusic.de/iloveradio18.mp3", "name": "😴 Sleep", "category": "chill"},
    "spa": {"url": "http://149.56.155.73:80/RELAXATION", "name": "🧘 Spa & Relax", "category": "chill"},
    
    # Electronic & Dance
    "dance": {"url": "https://streams.ilovemusic.de/iloveradio2.mp3", "name": "💃 Dance", "category": "electronic"},
    "techno": {"url": "https://streams.ilovemusic.de/iloveradio6.mp3", "name": "🎛️ Techno", "category": "electronic"},
    "trance": {"url": "http://trance.stream.laut.fm/trance", "name": "🌀 Trance", "category": "electronic"},
    "house": {"url": "https://streams.ilovemusic.de/iloveradio23.mp3", "name": "🏠 House", "category": "electronic"},
    "edm": {"url": "https://streams.ilovemusic.de/iloveradio109.mp3", "name": "⚡ EDM Hits", "category": "electronic"},
    "hardstyle": {"url": "https://streams.ilovemusic.de/iloveradio21.mp3", "name": "💥 Hardstyle", "category": "electronic"},
    
    # Rock & Metal
    "rock": {"url": "https://streams.ilovemusic.de/iloveradio16.mp3", "name": "🎸 Rock", "category": "rock"},
    "metal": {"url": "http://stream.laut.fm/metal", "name": "🤘 Metal", "category": "rock"},
    "classicrock": {"url": "https://streams.ilovemusic.de/iloveradio108.mp3", "name": "🎸 Classic Rock", "category": "rock"},
    
    # Hip Hop & Rap
    "hiphop": {"url": "https://streams.ilovemusic.de/iloveradio3.mp3", "name": "🎤 Hip Hop", "category": "hiphop"},
    "rap": {"url": "https://streams.ilovemusic.de/iloveradio13.mp3", "name": "🔥 Rap", "category": "hiphop"},
    "oldschool": {"url": "https://streams.ilovemusic.de/iloveradio12.mp3", "name": "📼 Old School Rap", "category": "hiphop"},
    
    # Pop & Charts
    "top100": {"url": "https://streams.ilovemusic.de/iloveradio1.mp3", "name": "📊 Top 100", "category": "pop"},
    "pop": {"url": "https://streams.ilovemusic.de/iloveradio14.mp3", "name": "🎵 Pop", "category": "pop"},
    "charts": {"url": "https://streams.ilovemusic.de/iloveradio109.mp3", "name": "📈 Charts", "category": "pop"},
    "2000s": {"url": "https://streams.ilovemusic.de/iloveradio4.mp3", "name": "💿 2000s Hits", "category": "pop"},
    "90s": {"url": "https://streams.ilovemusic.de/iloveradio5.mp3", "name": "💽 90s Hits", "category": "pop"},
    "80s": {"url": "https://streams.ilovemusic.de/iloveradio8.mp3", "name": "📻 80s Hits", "category": "pop"},
    
    # Other
    "jazz": {"url": "http://streaming.radio.co/s3c5f5e27a/listen", "name": "🎷 Jazz", "category": "other"},
    "classical": {"url": "http://149.56.155.73:80/CLASSIC", "name": "🎻 Classical", "category": "other"},
    "reggae": {"url": "http://stream.laut.fm/reggae", "name": "🇯🇲 Reggae", "category": "other"},
    "latina": {"url": "https://streams.ilovemusic.de/iloveradio24.mp3", "name": "💃 Latino", "category": "other"},
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.filename = data.get('filename')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        
        # Stáhnout soubor místo streamování (kvůli 403)
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=True))
        except Exception as e:
            print(f"[MUSIC] Download error: {e}", flush=True)
            raise e

        if 'entries' in data:
            data = data['entries'][0]

        filename = ytdl.prepare_filename(data)
        data['filename'] = filename
        
        return cls(discord.FFmpegPCMAudio(filename, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS), data=data)

# Music queues per guild
music_queues = {}  # {guild_id: {"queue": [], "current": None, "loop": False}}

def get_music_queue(guild_id: int) -> dict:
    if guild_id not in music_queues:
        music_queues[guild_id] = {"queue": [], "current": None, "loop": False, "volume": 0.5}
    return music_queues[guild_id]

def format_duration(seconds: int) -> str:
    if not seconds:
        return "Neznámá délka"
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"

async def play_next(guild_id: int, voice_client):
    """Přehraje další písničku z fronty"""
    queue_data = get_music_queue(guild_id)
    
    if queue_data["loop"] and queue_data["current"]:
        # Opakovat aktuální
        try:
            source = await YTDLSource.from_url(queue_data["current"]["url"], stream=False)
            source.volume = queue_data["volume"]
            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(guild_id, voice_client), bot.loop))
        except Exception as e:
            print(f"[MUSIC] Error playing: {e}", flush=True)
        return
    
    if not queue_data["queue"]:
        queue_data["current"] = None
        return
    
    next_song = queue_data["queue"].pop(0)
    queue_data["current"] = next_song
    
    try:
        source = await YTDLSource.from_url(next_song["url"], stream=False)
        source.volume = queue_data["volume"]
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(guild_id, voice_client), bot.loop))
        print(f"[MUSIC] Now playing: {next_song['title']}", flush=True)
    except Exception as e:
        print(f"[MUSIC] Error playing: {e}", flush=True)
        await play_next(guild_id, voice_client)

@bot.tree.command(name="radio", description="Přehraj rádio stanici")
@app_commands.describe(stanice="Vyber rádio stanici")
@app_commands.choices(stanice=[
    app_commands.Choice(name="🇨🇿 Evropa 2", value="evropa2"),
    app_commands.Choice(name="🇨🇿 Frekvence 1", value="frekvence1"),
    app_commands.Choice(name="🇨🇿 Rádio Impuls", value="impuls"),
    app_commands.Choice(name="🇨🇿 Kiss Rádio", value="kiss"),
    app_commands.Choice(name="🇨🇿 Rock Zone", value="rockzone"),
    app_commands.Choice(name="😴 Lo-Fi Hip Hop", value="lofi"),
    app_commands.Choice(name="🌴 Chill Out", value="chillout"),
    app_commands.Choice(name="💃 Dance", value="dance"),
    app_commands.Choice(name="🎛️ Techno", value="techno"),
    app_commands.Choice(name="🎸 Rock", value="rock"),
    app_commands.Choice(name="🎤 Hip Hop", value="hiphop"),
    app_commands.Choice(name="📊 Top 100", value="top100"),
])
async def radio_command(interaction: discord.Interaction, stanice: str):
    """Přehraje české rádio"""
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Musíš být ve voice kanálu!", ephemeral=True)
        return
    
    if stanice not in RADIO_STREAMS:
        await interaction.response.send_message("❌ Neznámá stanice!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    radio = RADIO_STREAMS[stanice]
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client
    
    # Připojit se k voice - vylepšená logika
    try:
        if voice_client:
            # Bot je už někde připojený
            if voice_client.is_playing():
                voice_client.stop()
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
        else:
            # Bot není připojený - připoj se
            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Nepodařilo se připojit k voice kanálu (timeout). Zkus to znovu.", ephemeral=True)
        return
    except Exception as e:
        # Zkus odpojit a znovu připojit
        try:
            if voice_client:
                await voice_client.disconnect(force=True)
            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
        except:
            await interaction.followup.send(f"❌ Chyba připojení k voice: {e}", ephemeral=True)
            return
    
    # Zastavit aktuální přehrávání
    if voice_client.is_playing():
        voice_client.stop()
    
    queue_data = get_music_queue(interaction.guild_id)
    queue_data["current"] = {"title": radio["name"], "url": radio["url"], "duration": 0, "requester": interaction.user.display_name}
    
    try:
        source = discord.FFmpegPCMAudio(radio["url"], executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=queue_data["volume"])
        voice_client.play(source)
        
        embed = discord.Embed(
            title="📻 Rádio hraje",
            description=f"**{radio['name']}**",
            color=discord.Color.red()
        )
        embed.add_field(name="🎧 Požádal", value=interaction.user.display_name, inline=True)
        embed.add_field(name="📡 Typ", value="Živé vysílání", inline=True)
        embed.set_footer(text="⚔️ Valhalla Bot • /musicstop pro zastavení")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Chyba: {e}", ephemeral=True)

@bot.tree.command(name="radiolist", description="Zobraz všechny dostupné rádio stanice")
async def radiolist_command(interaction: discord.Interaction):
    """Zobrazí seznam všech rádií podle kategorie"""
    embed = discord.Embed(
        title="📻 Dostupné rádio stanice",
        description="Použij `/radio [stanice]` pro přehrání",
        color=discord.Color.blue()
    )
    
    categories = {
        "cz": "🇨🇿 České stanice",
        "chill": "😴 Chill & Lo-Fi",
        "electronic": "⚡ Electronic & Dance",
        "rock": "🎸 Rock & Metal",
        "hiphop": "🎤 Hip Hop & Rap",
        "pop": "🎵 Pop & Charts",
        "other": "🎷 Ostatní"
    }
    
    for cat_key, cat_name in categories.items():
        stations = [f"`{k}` - {v['name']}" for k, v in RADIO_STREAMS.items() if v.get('category') == cat_key]
        if stations:
            embed.add_field(name=cat_name, value="\n".join(stations[:6]), inline=True)
    
    embed.set_footer(text="⚔️ Valhalla Bot • Celkem 35+ stanic")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="play", description="Přehraj hudbu (URL streamu nebo rádio)")
@app_commands.describe(url="Přímý URL na audio stream")
async def play_command(interaction: discord.Interaction, url: str):
    """Přehraje audio z přímého URL"""
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Musíš být ve voice kanálu!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client
    
    # Připojit se k voice
    if not voice_client:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)
    
    # Zastavit aktuální přehrávání
    if voice_client.is_playing():
        voice_client.stop()
    
    queue_data = get_music_queue(interaction.guild_id)
    
    # Zkusit přehrát přímo jako stream
    try:
        song = {
            "title": url.split("/")[-1] or "Stream",
            "url": url,
            "duration": 0,
            "requester": interaction.user.display_name
        }
        queue_data["current"] = song
        
        source = discord.FFmpegPCMAudio(url, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=queue_data["volume"])
        voice_client.play(source)
        
        embed = discord.Embed(
            title="🎵 Nyní hraje",
            description=f"**{song['title']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="🎧 Požádal", value=song['requester'], inline=True)
        embed.set_footer(text="⚔️ Valhalla Bot • /musicstop pro zastavení\n💡 Tip: Použij /radio pro české stanice!")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Nepodařilo se přehrát: {e}\n\n💡 **Tip:** YouTube je na tomto serveru blokovaný. Použij `/radio` pro české stanice nebo přímý URL na audio soubor.")

@bot.tree.command(name="skip", description="Přeskoč aktuální písničku")
async def skip_command(interaction: discord.Interaction):
    """Přeskočí aktuální písničku"""
    voice_client = interaction.guild.voice_client
    
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("❌ Bot není ve voice kanálu!", ephemeral=True)
        return
    
    if voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("⏭️ Přeskočeno!")
    else:
        await interaction.response.send_message("❌ Nic nehraje!", ephemeral=True)

@bot.tree.command(name="musicstop", description="Zastav hudbu a opusť voice kanál")
async def stop_music_command(interaction: discord.Interaction):
    """Zastaví hudbu a odpojí bota"""
    voice_client = interaction.guild.voice_client
    
    if not voice_client:
        await interaction.response.send_message("❌ Bot není ve voice kanálu!", ephemeral=True)
        return
    
    queue_data = get_music_queue(interaction.guild_id)
    queue_data["queue"] = []
    queue_data["current"] = None
    
    await voice_client.disconnect()
    await interaction.response.send_message("🛑 Hudba zastavena, bot odpojen!")

@bot.tree.command(name="pause", description="Pozastav hudbu")
async def pause_command(interaction: discord.Interaction):
    """Pozastaví přehrávání"""
    voice_client = interaction.guild.voice_client
    
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ Hudba pozastavena!")
    else:
        await interaction.response.send_message("❌ Nic nehraje!", ephemeral=True)

@bot.tree.command(name="resume", description="Pokračuj v přehrávání")
async def resume_command(interaction: discord.Interaction):
    """Pokračuje v přehrávání"""
    voice_client = interaction.guild.voice_client
    
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ Pokračuji v přehrávání!")
    else:
        await interaction.response.send_message("❌ Hudba není pozastavena!", ephemeral=True)

@bot.tree.command(name="queue", description="Zobraz frontu písniček")
async def queue_command(interaction: discord.Interaction):
    """Zobrazí frontu písniček"""
    queue_data = get_music_queue(interaction.guild_id)
    
    embed = discord.Embed(
        title="🎵 Fronta písniček",
        color=discord.Color.purple()
    )
    
    # Aktuální písnička
    if queue_data["current"]:
        current = queue_data["current"]
        embed.add_field(
            name="▶️ Nyní hraje",
            value=f"**{current['title']}** ({format_duration(current['duration'])})",
            inline=False
        )
    
    # Fronta
    if queue_data["queue"]:
        queue_list = []
        for i, song in enumerate(queue_data["queue"][:10], 1):
            queue_list.append(f"`{i}.` **{song['title']}** ({format_duration(song['duration'])})")
        
        embed.add_field(
            name=f"📋 Další v pořadí ({len(queue_data['queue'])})",
            value="\n".join(queue_list),
            inline=False
        )
        
        if len(queue_data["queue"]) > 10:
            embed.set_footer(text=f"...a dalších {len(queue_data['queue']) - 10} písniček")
    else:
        if not queue_data["current"]:
            embed.description = "Fronta je prázdná! Použij `/play` pro přidání hudby."
    
    # Loop status
    if queue_data["loop"]:
        embed.add_field(name="🔁 Opakování", value="Zapnuto", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="loop", description="Zapni/vypni opakování aktuální písničky")
async def loop_command(interaction: discord.Interaction):
    """Zapne/vypne opakování"""
    queue_data = get_music_queue(interaction.guild_id)
    queue_data["loop"] = not queue_data["loop"]
    
    if queue_data["loop"]:
        await interaction.response.send_message("🔁 Opakování zapnuto!")
    else:
        await interaction.response.send_message("➡️ Opakování vypnuto!")

@bot.tree.command(name="volume", description="Nastav hlasitost (0-100)")
@app_commands.describe(level="Hlasitost 0-100")
async def volume_command(interaction: discord.Interaction, level: int):
    """Nastaví hlasitost"""
    if level < 0 or level > 100:
        await interaction.response.send_message("❌ Hlasitost musí být 0-100!", ephemeral=True)
        return
    
    queue_data = get_music_queue(interaction.guild_id)
    queue_data["volume"] = level / 100
    
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.source:
        voice_client.source.volume = level / 100
    
    await interaction.response.send_message(f"🔊 Hlasitost nastavena na **{level}%**")

@bot.tree.command(name="nowplaying", description="Zobraz co právě hraje")
async def nowplaying_command(interaction: discord.Interaction):
    """Zobrazí aktuální písničku"""
    queue_data = get_music_queue(interaction.guild_id)
    
    if not queue_data["current"]:
        await interaction.response.send_message("❌ Nic nehraje!", ephemeral=True)
        return
    
    song = queue_data["current"]
    embed = discord.Embed(
        title="🎵 Nyní hraje",
        description=f"**{song['title']}**",
        color=discord.Color.green()
    )
    embed.add_field(name="⏱️ Délka", value=format_duration(song['duration']), inline=True)
    embed.add_field(name="🎧 Požádal", value=song['requester'], inline=True)
    embed.add_field(name="🔁 Loop", value="Ano" if queue_data["loop"] else "Ne", inline=True)
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    embed.set_footer(text="⚔️ Valhalla Bot")
    
    await interaction.response.send_message(embed=embed)

# ============== SOUNDCLOUD MUSIC SEARCH ==============

SOUNDCLOUD_CLIENT_ID = os.environ.get("SOUNDCLOUD_CLIENT_ID", "")
SOUNDCLOUD_CLIENT_SECRET = os.environ.get("SOUNDCLOUD_CLIENT_SECRET", "")
SOUNDCLOUD_API_URL = "https://api.soundcloud.com"

# Cache pro SoundCloud access token
soundcloud_token_cache = {"token": None, "expires": None}

async def get_soundcloud_token() -> str:
    """Získej OAuth2 access token pro SoundCloud"""
    global soundcloud_token_cache
    
    # Zkontroluj cache
    if soundcloud_token_cache["token"] and soundcloud_token_cache["expires"]:
        if datetime.now(timezone.utc) < soundcloud_token_cache["expires"]:
            return soundcloud_token_cache["token"]
    
    if not SOUNDCLOUD_CLIENT_ID or not SOUNDCLOUD_CLIENT_SECRET:
        print("[SOUNDCLOUD] Missing credentials!", flush=True)
        return None
    
    async with aiohttp.ClientSession() as session:
        url = f"{SOUNDCLOUD_API_URL}/oauth2/token"
        data = {
            "client_id": SOUNDCLOUD_CLIENT_ID,
            "client_secret": SOUNDCLOUD_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        try:
            async with session.post(url, data=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    token = result.get("access_token")
                    # Token vyprší za 1 hodinu, refreshneme za 50 minut
                    soundcloud_token_cache["token"] = token
                    soundcloud_token_cache["expires"] = datetime.now(timezone.utc) + timedelta(minutes=50)
                    print("[SOUNDCLOUD] Got new access token", flush=True)
                    return token
                else:
                    print(f"[SOUNDCLOUD] Token error: {resp.status}", flush=True)
        except Exception as e:
            print(f"[SOUNDCLOUD] Token error: {e}", flush=True)
    return None

async def search_soundcloud(query: str, limit: int = 5) -> list:
    """Vyhledej písničky na SoundCloud API"""
    token = await get_soundcloud_token()
    if not token:
        print("[SOUNDCLOUD] No token available!", flush=True)
        return []
    
    async with aiohttp.ClientSession() as session:
        url = f"{SOUNDCLOUD_API_URL}/tracks"
        params = {"q": query, "limit": limit}
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"[SOUNDCLOUD] Found {len(data)} tracks for '{query}'", flush=True)
                    return data
                else:
                    print(f"[SOUNDCLOUD] API error: {resp.status}", flush=True)
        except Exception as e:
            print(f"[SOUNDCLOUD] Search error: {e}", flush=True)
    return []

async def get_soundcloud_stream_url(track: dict) -> str:
    """Získej stream URL pro SoundCloud track"""
    token = await get_soundcloud_token()
    if not token:
        return None
    
    track_id = track.get("id")
    if not track_id:
        return None
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Použij /streams endpoint pro získání MP3 URL
        streams_url = f"{SOUNDCLOUD_API_URL}/tracks/{track_id}/streams"
        try:
            async with session.get(streams_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # Preferuj http_mp3_128_url, pak hls varianty
                    stream_api_url = (
                        data.get("http_mp3_128_url") or 
                        data.get("hls_mp3_128_url") or 
                        data.get("hls_aac_160_url")
                    )
                    if stream_api_url:
                        # Musíme získat skutečnou CDN URL pomocí Authorization header
                        try:
                            async with session.get(stream_api_url, headers=headers, allow_redirects=True) as stream_resp:
                                if stream_resp.status == 200:
                                    # Finální URL po redirectu je skutečná stream URL
                                    final_url = str(stream_resp.url)
                                    print(f"[SOUNDCLOUD] Got CDN stream URL for track {track_id}", flush=True)
                                    return final_url
                                else:
                                    print(f"[SOUNDCLOUD] Stream redirect error: {stream_resp.status}", flush=True)
                        except Exception as e:
                            print(f"[SOUNDCLOUD] Stream redirect error: {e}", flush=True)
                else:
                    print(f"[SOUNDCLOUD] Streams API error: {resp.status}", flush=True)
        except Exception as e:
            print(f"[SOUNDCLOUD] Stream error: {e}", flush=True)
    
    return None

class SoundCloudSearchView(discord.ui.View):
    def __init__(self, tracks: list, requester: discord.Member, guild_id: int):
        super().__init__(timeout=120)
        self.tracks = tracks
        self.requester = requester
        self.guild_id = guild_id
        
        # Přidej tlačítka pro každý track (max 5)
        for i, track in enumerate(tracks[:5]):
            button = discord.ui.Button(
                label=f"{i+1}",
                style=discord.ButtonStyle.primary,
                custom_id=f"sc_play_{i}"
            )
            button.callback = self.create_callback(i)
            self.add_item(button)
    
    def create_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            await self.play_track(interaction, index)
        return callback
    
    async def play_track(self, interaction: discord.Interaction, index: int):
        track = self.tracks[index]
        
        # Zkontroluj voice
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Musíš být ve voice kanálu!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        voice_channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        
        # Připojit se k voice - vylepšená logika
        try:
            if voice_client:
                if voice_client.is_playing():
                    voice_client.stop()
                if voice_client.channel != voice_channel:
                    await voice_client.move_to(voice_channel)
            else:
                voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Nepodařilo se připojit k voice kanálu (timeout).", ephemeral=True)
            return
        except Exception as e:
            try:
                if voice_client:
                    await voice_client.disconnect(force=True)
                voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
            except:
                await interaction.followup.send(f"❌ Chyba připojení: {e}", ephemeral=True)
                return
        
        queue_data = get_music_queue(interaction.guild_id)
        
        # Získej stream URL
        stream_url = await get_soundcloud_stream_url(track)
        
        if not stream_url:
            await interaction.followup.send("❌ Tato písnička není dostupná pro streaming!", ephemeral=True)
            return
        
        duration_ms = track.get("duration", 0)
        duration_sec = duration_ms // 1000
        
        song = {
            "title": f"{track.get('user', {}).get('username', 'Unknown')} - {track['title']}",
            "url": stream_url,
            "duration": duration_sec,
            "requester": interaction.user.display_name,
            "thumbnail": track.get("artwork_url")
        }
        queue_data["current"] = song
        
        try:
            source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=queue_data["volume"])
            voice_client.play(source)
            
            embed = discord.Embed(
                title="🎵 Nyní hraje",
                description=f"**{track['title']}**",
                color=discord.Color.orange()
            )
            embed.add_field(name="🎤 Umělec", value=track.get('user', {}).get('username', 'Unknown'), inline=True)
            embed.add_field(name="⏱️ Délka", value=f"{duration_sec // 60}:{duration_sec % 60:02d}", inline=True)
            embed.add_field(name="🎧 Požádal", value=interaction.user.display_name, inline=True)
            
            if track.get("artwork_url"):
                embed.set_thumbnail(url=track["artwork_url"])
            
            embed.set_footer(text="⚔️ Valhalla Bot • Powered by SoundCloud")
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.edit_original_response(view=self)
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"[SOUNDCLOUD] Play error: {e}", flush=True)
            await interaction.followup.send(f"❌ Chyba přehrávání: {e}", ephemeral=True)

@bot.tree.command(name="search", description="Vyhledej a přehraj písničku ze SoundCloud")
@app_commands.describe(query="Název písničky nebo interpreta")
async def search_command(interaction: discord.Interaction, query: str):
    """Vyhledá písničky na SoundCloud a nabídne výběr"""
    await interaction.response.defer()
    
    tracks = await search_soundcloud(query, limit=5)
    
    if not tracks:
        await interaction.followup.send(f"❌ Nic nenalezeno pro: **{query}**", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"🔍 Výsledky pro: {query}",
        description="Klikni na číslo pro přehrání:",
        color=discord.Color.orange()
    )
    
    for i, track in enumerate(tracks[:5]):
        duration_ms = track.get("duration", 0)
        duration_sec = duration_ms // 1000
        duration_str = f"{duration_sec // 60}:{duration_sec % 60:02d}"
        artist = track.get('user', {}).get('username', 'Unknown')
        embed.add_field(
            name=f"{i+1}. {track['title'][:50]}",
            value=f"🎤 {artist} • ⏱️ {duration_str}",
            inline=False
        )
    
    if tracks[0].get("artwork_url"):
        embed.set_thumbnail(url=tracks[0]["artwork_url"])
    
    embed.set_footer(text="⚔️ Valhalla Bot • Powered by SoundCloud")
    
    view = SoundCloudSearchView(tracks, interaction.user, interaction.guild_id)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="playtrack", description="Rychle přehraj první výsledek vyhledávání")
@app_commands.describe(query="Název písničky nebo interpreta")
async def playtrack_command(interaction: discord.Interaction, query: str):
    """Přehraje první výsledek vyhledávání ze SoundCloud"""
    if not interaction.user.voice:
        await interaction.response.send_message("❌ Musíš být ve voice kanálu!", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    tracks = await search_soundcloud(query, limit=1)
    
    if not tracks:
        await interaction.followup.send(f"❌ Nic nenalezeno pro: **{query}**", ephemeral=True)
        return
    
    track = tracks[0]
    
    # Získej stream URL
    stream_url = await get_soundcloud_stream_url(track)
    
    if not stream_url:
        await interaction.followup.send("❌ Tato písnička není dostupná pro streaming!", ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client
    
    # Připojit se k voice - vylepšená logika
    try:
        if voice_client:
            if voice_client.is_playing():
                voice_client.stop()
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
        else:
            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Nepodařilo se připojit k voice kanálu (timeout).", ephemeral=True)
        return
    except Exception as e:
        try:
            if voice_client:
                await voice_client.disconnect(force=True)
            voice_client = await voice_channel.connect(timeout=10.0, reconnect=True)
        except:
            await interaction.followup.send(f"❌ Chyba připojení: {e}", ephemeral=True)
            return
    
    queue_data = get_music_queue(interaction.guild_id)
    
    duration_ms = track.get("duration", 0)
    duration_sec = duration_ms // 1000
    
    song = {
        "title": f"{track.get('user', {}).get('username', 'Unknown')} - {track['title']}",
        "url": stream_url,
        "duration": duration_sec,
        "requester": interaction.user.display_name,
        "thumbnail": track.get("artwork_url")
    }
    queue_data["current"] = song
    
    try:
        source = discord.FFmpegPCMAudio(stream_url, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=queue_data["volume"])
        voice_client.play(source)
        
        embed = discord.Embed(
            title="🎵 Nyní hraje",
            description=f"**{track['title']}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="🎤 Umělec", value=track.get('user', {}).get('username', 'Unknown'), inline=True)
        embed.add_field(name="⏱️ Délka", value=f"{duration_sec // 60}:{duration_sec % 60:02d}", inline=True)
        embed.add_field(name="🎧 Požádal", value=interaction.user.display_name, inline=True)
        
        if track.get("artwork_url"):
            embed.set_thumbnail(url=track["artwork_url"])
        
        embed.set_footer(text="⚔️ Valhalla Bot • Powered by SoundCloud")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"[SOUNDCLOUD] Play error: {e}", flush=True)
        await interaction.followup.send(f"❌ Chyba přehrávání: {e}")

# ============== REACTION ROLES SYSTEM ==============

reaction_roles_collection = db["reaction_roles"]

class ReactionRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

@bot.tree.command(name="reactionrole", description="Vytvoř zprávu pro získání role kliknutím na reakci (Admin)")
@app_commands.describe(
    role="Role kterou uživatelé získají",
    emoji="Emoji pro reakci (např. 🎮 nebo custom emoji)",
    title="Nadpis zprávy",
    description="Popis zprávy"
)
@app_commands.default_permissions(administrator=True)
async def reactionrole_command(
    interaction: discord.Interaction, 
    role: discord.Role,
    emoji: str,
    title: str = "Získej roli!",
    description: str = "Klikni na reakci níže pro získání role!"
):
    """Vytvoří zprávu s reakcí pro získání role"""
    
    # Zkontroluj že bot může přidělit tuto roli
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message(
            "❌ Nemohu přidělovat tuto roli - je výše než moje role!",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"🎭 {title}",
        description=f"{description}\n\nReaguj s {emoji} pro získání role **{role.name}**",
        color=role.color if role.color != discord.Color.default() else discord.Color.blue()
    )
    embed.set_footer(text="⚔️ Valhalla Bot • Reaction Roles")
    
    await interaction.response.send_message("✅ Vytvářím reaction role zprávu...", ephemeral=True)
    
    # Pošli zprávu do kanálu
    message = await interaction.channel.send(embed=embed)
    
    # Přidej reakci
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        await interaction.followup.send(f"❌ Neplatné emoji: {emoji}", ephemeral=True)
        await message.delete()
        return
    
    # Ulož do databáze
    reaction_roles_collection.update_one(
        {"message_id": message.id},
        {"$set": {
            "message_id": message.id,
            "channel_id": interaction.channel_id,
            "guild_id": interaction.guild_id,
            "role_id": role.id,
            "emoji": emoji,
            "created_by": interaction.user.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    await interaction.followup.send(f"✅ Reaction role vytvořena! Uživatelé mohou kliknout na {emoji} pro získání role **{role.name}**", ephemeral=True)

@bot.tree.command(name="multireactionrole", description="Vytvoř zprávu s více rolemi (Admin)")
@app_commands.describe(
    title="Nadpis zprávy",
    description="Popis zprávy"
)
@app_commands.default_permissions(administrator=True)
async def multireactionrole_command(
    interaction: discord.Interaction,
    title: str = "Vyber si role!",
    description: str = "Klikni na reakce pro získání rolí"
):
    """Vytvoří zprávu pro více reaction roles - role přidáš pomocí /addrole"""
    
    embed = discord.Embed(
        title=f"🎭 {title}",
        description=f"{description}\n\n*Použij `/addrole` pro přidání rolí k této zprávě*",
        color=discord.Color.purple()
    )
    embed.set_footer(text="⚔️ Valhalla Bot • Reaction Roles")
    
    await interaction.response.send_message("✅ Vytvářím multi-role zprávu...", ephemeral=True)
    
    message = await interaction.channel.send(embed=embed)
    
    # Ulož základní zprávu
    reaction_roles_collection.insert_one({
        "message_id": message.id,
        "channel_id": interaction.channel_id,
        "guild_id": interaction.guild_id,
        "type": "multi",
        "roles": [],  # Bude se přidávat pomocí /addrole
        "created_by": interaction.user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    await interaction.followup.send(f"✅ Multi-role zpráva vytvořena! ID zprávy: `{message.id}`\nPoužij `/addrole {message.id} @role 🎮` pro přidání rolí.", ephemeral=True)

@bot.tree.command(name="addrole", description="Přidej roli k existující reaction role zprávě (Admin)")
@app_commands.describe(
    message_id="ID zprávy (zkopíruj pravým kliknutím na zprávu)",
    role="Role k přidání",
    emoji="Emoji pro tuto roli"
)
@app_commands.default_permissions(administrator=True)
async def addrole_command(
    interaction: discord.Interaction,
    message_id: str,
    role: discord.Role,
    emoji: str
):
    """Přidá roli k existující reaction role zprávě"""
    
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Neplatné ID zprávy!", ephemeral=True)
        return
    
    # Najdi zprávu v databázi
    rr_data = reaction_roles_collection.find_one({"message_id": msg_id, "guild_id": interaction.guild_id})
    
    if not rr_data:
        await interaction.response.send_message("❌ Tato zpráva není reaction role zpráva!", ephemeral=True)
        return
    
    # Najdi zprávu na Discordu
    try:
        channel = interaction.guild.get_channel(rr_data["channel_id"])
        message = await channel.fetch_message(msg_id)
    except:
        await interaction.response.send_message("❌ Zprávu se nepodařilo najít!", ephemeral=True)
        return
    
    # Přidej reakci
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        await interaction.response.send_message(f"❌ Neplatné emoji: {emoji}", ephemeral=True)
        return
    
    # Aktualizuj databázi
    if rr_data.get("type") == "multi":
        # Multi-role zpráva
        reaction_roles_collection.update_one(
            {"message_id": msg_id},
            {"$push": {"roles": {"role_id": role.id, "emoji": emoji}}}
        )
    else:
        # Převeď na multi pokud přidáváme další roli
        existing_role = {"role_id": rr_data.get("role_id"), "emoji": rr_data.get("emoji")}
        reaction_roles_collection.update_one(
            {"message_id": msg_id},
            {"$set": {
                "type": "multi",
                "roles": [existing_role, {"role_id": role.id, "emoji": emoji}]
            },
            "$unset": {"role_id": "", "emoji": ""}}
        )
    
    # Aktualizuj embed
    embed = message.embeds[0] if message.embeds else discord.Embed(title="🎭 Role")
    
    # Přidej roli do popisu
    roles_text = ""
    updated_data = reaction_roles_collection.find_one({"message_id": msg_id})
    if updated_data.get("type") == "multi":
        for r in updated_data.get("roles", []):
            role_obj = interaction.guild.get_role(r["role_id"])
            if role_obj:
                roles_text += f"{r['emoji']} → **{role_obj.name}**\n"
    
    if roles_text:
        embed.description = f"Klikni na reakci pro získání role:\n\n{roles_text}"
    
    await message.edit(embed=embed)
    
    await interaction.response.send_message(f"✅ Role **{role.name}** přidána s emoji {emoji}!", ephemeral=True)

@bot.tree.command(name="listreactionroles", description="Zobraz všechny reaction role zprávy (Admin)")
@app_commands.default_permissions(administrator=True)
async def listreactionroles_command(interaction: discord.Interaction):
    """Zobrazí seznam všech reaction role zpráv na serveru"""
    
    rr_list = list(reaction_roles_collection.find({"guild_id": interaction.guild_id}))
    
    if not rr_list:
        await interaction.response.send_message("📋 Na tomto serveru nejsou žádné reaction role zprávy.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=f"Celkem {len(rr_list)} zpráv",
        color=discord.Color.purple()
    )
    
    for rr in rr_list[:10]:  # Max 10
        channel = interaction.guild.get_channel(rr.get("channel_id"))
        channel_name = channel.name if channel else "Neznámý"
        
        if rr.get("type") == "multi":
            roles_count = len(rr.get("roles", []))
            embed.add_field(
                name=f"ID: {rr['message_id']}",
                value=f"Kanál: #{channel_name}\nRolí: {roles_count}",
                inline=True
            )
        else:
            role = interaction.guild.get_role(rr.get("role_id"))
            role_name = role.name if role else "Neznámá"
            embed.add_field(
                name=f"ID: {rr['message_id']}",
                value=f"Kanál: #{channel_name}\nRole: {role_name}\nEmoji: {rr.get('emoji')}",
                inline=True
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="deletereactionrole", description="Smaž reaction role zprávu (Admin)")
@app_commands.describe(message_id="ID zprávy ke smazání")
@app_commands.default_permissions(administrator=True)
async def deletereactionrole_command(interaction: discord.Interaction, message_id: str):
    """Smaže reaction role zprávu"""
    
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Neplatné ID zprávy!", ephemeral=True)
        return
    
    # Najdi a smaž z databáze
    result = reaction_roles_collection.delete_one({"message_id": msg_id, "guild_id": interaction.guild_id})
    
    if result.deleted_count == 0:
        await interaction.response.send_message("❌ Reaction role zpráva nenalezena!", ephemeral=True)
        return
    
    await interaction.response.send_message(f"✅ Reaction role smazána! (Zprávu na Discordu můžeš smazat ručně)", ephemeral=True)

# Event handlers pro reaction roles
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    """Když uživatel přidá reakci"""
    if payload.user_id == bot.user.id:
        return
    
    # Najdi reaction role
    rr_data = reaction_roles_collection.find_one({"message_id": payload.message_id})
    
    if not rr_data:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member:
        return
    
    emoji_str = str(payload.emoji)
    
    # Najdi správnou roli
    role_id = None
    
    if rr_data.get("type") == "multi":
        for r in rr_data.get("roles", []):
            if r["emoji"] == emoji_str:
                role_id = r["role_id"]
                break
    else:
        if rr_data.get("emoji") == emoji_str:
            role_id = rr_data.get("role_id")
    
    if role_id:
        role = guild.get_role(role_id)
        if role and role not in member.roles:
            try:
                await member.add_roles(role, reason="Reaction Role")
                print(f"[REACTION ROLE] {member.display_name} získal roli {role.name}", flush=True)
            except discord.Forbidden:
                print(f"[REACTION ROLE] Nelze přidat roli {role.name} - chybí oprávnění", flush=True)

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    """Když uživatel odebere reakci"""
    if payload.user_id == bot.user.id:
        return
    
    # Najdi reaction role
    rr_data = reaction_roles_collection.find_one({"message_id": payload.message_id})
    
    if not rr_data:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member:
        return
    
    emoji_str = str(payload.emoji)
    
    # Najdi správnou roli
    role_id = None
    
    if rr_data.get("type") == "multi":
        for r in rr_data.get("roles", []):
            if r["emoji"] == emoji_str:
                role_id = r["role_id"]
                break
    else:
        if rr_data.get("emoji") == emoji_str:
            role_id = rr_data.get("role_id")
    
    if role_id:
        role = guild.get_role(role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="Reaction Role removed")
                print(f"[REACTION ROLE] {member.display_name} ztratil roli {role.name}", flush=True)
            except discord.Forbidden:
                print(f"[REACTION ROLE] Nelze odebrat roli {role.name} - chybí oprávnění", flush=True)

# ============== GIVEAWAY SYSTEM ==============

active_giveaways = {}

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: str, prize: str, end_time: datetime, host_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
        self.prize = prize
        self.end_time = end_time
        self.host_id = host_id
        self.participants = set()
    
    @discord.ui.button(label="🎉 Zúčastnit se", style=discord.ButtonStyle.green, custom_id="giveaway_join")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        if user_id in self.participants:
            self.participants.discard(user_id)
            await interaction.response.send_message("❌ Odhlásil ses ze soutěže!", ephemeral=True)
        else:
            self.participants.add(user_id)
            await interaction.response.send_message("✅ Jsi přihlášen do soutěže! Hodně štěstí! 🍀", ephemeral=True)
        
        # Update embed with participant count
        await self.update_embed(interaction.message)
    
    async def update_embed(self, message):
        embed = message.embeds[0]
        embed.set_field_at(1, name="👥 Účastníků", value=str(len(self.participants)), inline=True)
        await message.edit(embed=embed)

@bot.tree.command(name="giveaway", description="Vytvoř novou soutěž (jen admin)")
@app_commands.describe(
    cas="Doba trvání soutěže (např. 1h, 1d, 7d)",
    vyhry="Počet výherců",
    cena="Co se vyhrává"
)
@app_commands.checks.has_permissions(administrator=True)
async def giveaway_command(interaction: discord.Interaction, cas: str, vyhry: int, cena: str):
    """Vytvoří novou giveaway soutěž"""
    seconds = parse_time(cas)
    
    if seconds is None:
        await interaction.response.send_message("❌ Neplatný formát času! Použij např. 1h, 1d, 7d", ephemeral=True)
        return
    
    if vyhry < 1:
        await interaction.response.send_message("❌ Počet výherců musí být alespoň 1!", ephemeral=True)
        return
    
    end_time = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    giveaway_id = f"{interaction.guild_id}_{interaction.channel_id}_{int(datetime.now().timestamp())}"
    
    # Create embed
    embed = discord.Embed(
        title="🎁 GIVEAWAY!",
        description=f"**{cena}**",
        color=discord.Color.gold()
    )
    embed.add_field(name="🏆 Počet výherců", value=str(vyhry), inline=True)
    embed.add_field(name="👥 Účastníků", value="0", inline=True)
    embed.add_field(name="⏰ Končí", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
    embed.add_field(name="🎮 Hostitel", value=interaction.user.mention, inline=False)
    embed.set_footer(text="Klikni na tlačítko pro účast!")
    
    # Create view
    view = GiveawayView(giveaway_id, cena, end_time, interaction.user.id)
    view.winners_count = vyhry
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    # Store giveaway
    active_giveaways[giveaway_id] = {
        "message_id": message.id,
        "channel_id": interaction.channel_id,
        "guild_id": interaction.guild_id,
        "prize": cena,
        "winners_count": vyhry,
        "end_time": end_time,
        "host_id": interaction.user.id,
        "view": view
    }
    
    # Schedule end
    bot.loop.create_task(end_giveaway_after(giveaway_id, seconds))

async def end_giveaway_after(giveaway_id: str, seconds: int):
    """End giveaway after specified time"""
    await asyncio.sleep(seconds)
    await end_giveaway(giveaway_id)

async def end_giveaway(giveaway_id: str):
    """End a giveaway and pick winners"""
    if giveaway_id not in active_giveaways:
        return
    
    giveaway = active_giveaways[giveaway_id]
    view = giveaway["view"]
    
    channel = bot.get_channel(giveaway["channel_id"])
    if not channel:
        return
    
    try:
        message = await channel.fetch_message(giveaway["message_id"])
    except:
        return
    
    participants = list(view.participants)
    winners_count = min(giveaway["winners_count"], len(participants))
    
    if winners_count == 0:
        # No participants
        embed = discord.Embed(
            title="🎁 GIVEAWAY UKONČEN",
            description=f"**{giveaway['prize']}**\n\n😢 Nikdo se nezúčastnil!",
            color=discord.Color.red()
        )
        await message.edit(embed=embed, view=None)
    else:
        # Pick winners
        import random
        winners = random.sample(participants, winners_count)
        winners_mentions = ", ".join([f"<@{w}>" for w in winners])
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY UKONČEN!",
            description=f"**{giveaway['prize']}**",
            color=discord.Color.green()
        )
        embed.add_field(name="🏆 Výherci", value=winners_mentions, inline=False)
        embed.add_field(name="👥 Celkem účastníků", value=str(len(participants)), inline=True)
        
        await message.edit(embed=embed, view=None)
        
        # Announce winners
        await channel.send(f"🎉 Gratulujeme {winners_mentions}! Vyhráli jste **{giveaway['prize']}**!")
    
    # Remove from active
    del active_giveaways[giveaway_id]

@bot.tree.command(name="greroll", description="Znovu vylosuj výherce (jen admin)")
@app_commands.describe(message_id="ID zprávy s giveaway")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway_reroll(interaction: discord.Interaction, message_id: str):
    """Reroll giveaway winners"""
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message("❌ Zpráva nenalezena!", ephemeral=True)
        return
    
    # Find giveaway in history or just pick random from reactions
    await interaction.response.send_message("🎲 Funkce reroll bude brzy dostupná!", ephemeral=True)

@giveaway_command.error
async def giveaway_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Pouze administrátor může vytvářet soutěže!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Chyba: {error}", ephemeral=True)

# ============== COUNTDOWN COMMANDS ==============

@bot.tree.command(name="odpocet", description="Spusť odpočet (např. 2m, 5m, 1h)")
@app_commands.describe(
    cas="Čas odpočtu (např. 30s, 2m, 1h, 1d)",
    duvod="Důvod/popis odpočtu (volitelné)"
)
async def slash_odpocet(interaction: discord.Interaction, cas: str, duvod: str = None):
    seconds = parse_time(cas)
    
    if seconds is None:
        await interaction.response.send_message(
            "❌ Neplatný formát času! Použij např. `30s`, `2m`, `1h`, `1d`",
            ephemeral=True
        )
        return
    
    if seconds < 5:
        await interaction.response.send_message("❌ Minimální čas je 5 sekund!", ephemeral=True)
        return
    
    if seconds > 86400 * 7:
        await interaction.response.send_message("❌ Maximální čas je 7 dní!", ephemeral=True)
        return
    
    countdown_id = str(uuid.uuid4())
    end_time = int(datetime.now(timezone.utc).timestamp()) + seconds
    
    embed = discord.Embed(
        title="⏰ ODPOČET",
        description=f"**{duvod}**" if duvod else "Odpočet běží...",
        color=discord.Color.blue()
    )
    embed.add_field(name="⏳ Zbývá", value=f"**{format_time(seconds)}**", inline=True)
    embed.add_field(name="👤 Spustil", value=interaction.user.mention, inline=True)
    embed.set_footer(text=f"Končí: {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
    
    view = CountdownView(countdown_id, interaction.user.id)
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    active_countdowns[countdown_id] = {"cancelled": False}
    
    asyncio.create_task(run_countdown(
        interaction.channel,
        message,
        end_time,
        countdown_id,
        interaction.user,
        duvod
    ))

@bot.command(name="odpocet", aliases=["countdown", "timer"])
async def prefix_odpocet(ctx, cas: str, *, duvod: str = None):
    """!odpocet 2m [důvod] - Spusť odpočet"""
    seconds = parse_time(cas)
    
    if seconds is None:
        await ctx.send("❌ Neplatný formát času! Použij např. `30s`, `2m`, `1h`, `1d`")
        return
    
    if seconds < 5:
        await ctx.send("❌ Minimální čas je 5 sekund!")
        return
    
    if seconds > 86400 * 7:
        await ctx.send("❌ Maximální čas je 7 dní!")
        return
    
    countdown_id = str(uuid.uuid4())
    end_time = int(datetime.now(timezone.utc).timestamp()) + seconds
    
    embed = discord.Embed(
        title="⏰ ODPOČET",
        description=f"**{duvod}**" if duvod else "Odpočet běží...",
        color=discord.Color.blue()
    )
    embed.add_field(name="⏳ Zbývá", value=f"**{format_time(seconds)}**", inline=True)
    embed.add_field(name="👤 Spustil", value=ctx.author.mention, inline=True)
    embed.set_footer(text=f"Končí: {datetime.fromtimestamp(end_time).strftime('%H:%M:%S')}")
    
    view = CountdownView(countdown_id, ctx.author.id)
    
    message = await ctx.send(embed=embed, view=view)
    
    active_countdowns[countdown_id] = {"cancelled": False}
    
    asyncio.create_task(run_countdown(
        ctx.channel,
        message,
        end_time,
        countdown_id,
        ctx.author,
        duvod
    ))

@bot.tree.command(name="help", description="Zobraz nápovědu")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚔️ Valhalla Bot - Příkazy",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="⏰ Odpočet",
        value="`/odpocet [čas] [důvod]`",
        inline=False
    )
    embed.add_field(
        name="📊 Ankety",
        value="`/poll [otázka] [možnosti] [čas]`",
        inline=False
    )
    embed.add_field(
        name="🎵 Hudební kvíz",
        value="`/hudba [žánr]` - rap, pop, rock, classic",
        inline=False
    )
    embed.add_field(
        name="🎬 Filmový kvíz",
        value="`/film [žánr]` - české, hollywood, komedie, akční, horor, scifi",
        inline=False
    )
    embed.add_field(
        name="🤔 Pravda/Lež",
        value="`/pravda [kategorie]` - zvířata, věda, historie, tělo, jídlo, česko, bizarní",
        inline=False
    )
    embed.add_field(
        name="🛑 Zastavit kvíz",
        value="`/stop` - zastaví běžící kvíz",
        inline=False
    )
    embed.add_field(
        name="⏱️ Formáty času",
        value="`30s`, `2m`, `1h`, `1d`",
        inline=False
    )
    embed.add_field(
        name="🏆 Level systém",
        value="`/gamelevel` `/top` `/daily` `/hry` `/ukoly`",
        inline=False
    )
    embed.add_field(
        name="🎵 Hudba & Rádio",
        value="`/search [název]` - vyhledej na SoundCloud\n`/playtrack [název]` - rychlé přehrání\n`/radio [stanice]` - přehraj rádio\n`/radiolist` - seznam stanic",
        inline=False
    )
    embed.add_field(
        name="🎭 Reaction Roles (Admin)",
        value="`/reactionrole` - vytvoř reakci pro získání role\n`/multireactionrole` - více rolí v jedné zprávě\n`/addrole` - přidej roli ke zprávě\n`/listreactionroles` - seznam všech\n`/deletereactionrole` - smaž reakci",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="pomoc")
async def prefix_help(ctx):
    """!pomoc - Zobraz nápovědu"""
    embed = discord.Embed(
        title="⚔️ Valhalla Bot - Příkazy",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="⏰ Odpočet",
        value="`!odpocet [čas] [důvod]`",
        inline=False
    )
    embed.add_field(
        name="📊 Ankety",
        value="`!poll 5m Otázka? | Možnost1, Možnost2`",
        inline=False
    )
    embed.add_field(
        name="🎵 Hudební kvíz",
        value="`!hudba [rap/pop/rock/classic]`",
        inline=False
    )
    embed.add_field(
        name="🎬 Filmový kvíz",
        value="`!film [ceske/hollywood/komedie/akcni/horor/scifi]`",
        inline=False
    )
    embed.add_field(
        name="🤔 Pravda/Lež",
        value="`!pravda [kategorie]` - zvirata, veda, historie, telo, jidlo, cesko, bizarni",
        inline=False
    )
    embed.add_field(
        name="🛑 Zastavit kvíz",
        value="`!stop` - zastaví běžící kvíz",
        inline=False
    )
    embed.add_field(
        name="🏆 Level systém",
        value="`!level` `!top` `!daily` `!hry` `!ukoly`",
        inline=False
    )
    msg = await ctx.send(embed=embed)
    asyncio.create_task(delete_after(msg, 60))  # Smaže po 5 min

@bot.command(name="prikazy")
@commands.has_permissions(administrator=True)
async def send_commands_info(ctx):
    """!prikazy - Pošle trvalou zprávu s přehledem příkazů (jen admin)"""
    
    # Delete the command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Main embed
    embed = discord.Embed(
        title="⚔️ VALHALLA BOT - PŘÍKAZY",
        description="Kompletní přehled všech dostupných příkazů",
        color=discord.Color.blue()
    )
    
    # Kvízy
    embed.add_field(
        name="🎵 HUDEBNÍ KVÍZ",
        value="```/hudba [žánr]\n!hudba [rap/pop/rock/classic]```\nHádej interpreta podle textu písně!\n**+25 XP** za správnou odpověď",
        inline=False
    )
    
    embed.add_field(
        name="🎬 FILMOVÝ KVÍZ",
        value="```/film [žánr]\n!film [ceske/hollywood/komedie/akcni/horor/scifi]```\nHádej film podle slavné hlášky!\n**+25 XP** za správnou odpověď",
        inline=False
    )
    
    embed.add_field(
        name="🤔 PRAVDA NEBO LEŽ",
        value="```/pravda [kategorie]\n!pravda [zvirata/veda/historie/telo/jidlo/cesko/bizarni]```\nJe tento fakt pravdivý?\n**+15 XP** za správnou odpověď",
        inline=False
    )
    
    # Level systém
    embed.add_field(
        name="📊 LEVEL SYSTÉM",
        value="```/gamelevel nebo !level``` Zobraz svůj level a statistiky\n```/top nebo !top``` Žebříček TOP 10 hráčů\n```/daily nebo !daily``` Denní bonus **+100 XP** + streak",
        inline=False
    )
    
    # Herní systém
    embed.add_field(
        name="🎮 HRY NA PC",
        value="```/hry nebo !hry``` Tvé odemčené hry a čas hraní\n```/ukoly [hra] nebo !ukoly [hra]``` Úkoly pro konkrétní hru\n\n**Automatické XP za hraní:**\n• +5 XP za 10 minut hraní\n• Max 200 XP/den\n• +25 XP za odemčení nové hry",
        inline=False
    )
    
    # Utility
    embed.add_field(
        name="⏰ UTILITY",
        value="```/odpocet [čas] [důvod]\n!odpocet 5m Přestávka```\nSpustí odpočet s notifikací\n```/poll [otázka] [možnosti] [čas]\n!poll 5m Otázka? | Ano, Ne```\nVytvoří anketu s hlasováním",
        inline=False
    )
    
    embed.add_field(
        name="🛑 OSTATNÍ",
        value="```/stop nebo !stop``` Zastaví běžící kvíz\n```/help nebo !pomoc``` Zobrazí nápovědu",
        inline=False
    )
    
    embed.set_footer(text="💡 Valhalla Bot • Hraj hry, plň úkoly a staň se legendou!")
    
    await ctx.send(embed=embed)
    
    # Second embed - XP info
    xp_embed = discord.Embed(
        title="✨ JAK ZÍSKAT XP",
        color=discord.Color.gold()
    )
    
    xp_embed.add_field(
        name="🎯 Kvízy",
        value="• Hudební/Filmový kvíz: **+25 XP**\n• Pravda/Lež: **+15 XP**",
        inline=True
    )
    
    xp_embed.add_field(
        name="🎮 Hraní her",
        value="• 10 minut hraní: **+5 XP**\n• Odemčení hry: **+25 XP**\n• Max denně: **200 XP**",
        inline=True
    )
    
    xp_embed.add_field(
        name="🎁 Bonusy",
        value="• Denní bonus: **+100 XP**\n• Streak bonus: **+10 XP/den**\n• Splněný úkol: **+50-1500 XP**",
        inline=True
    )
    
    xp_embed.add_field(
        name="📈 LEVELY",
        value="🌱 Lvl 1 → 🌿 Lvl 2 → 🌳 Lvl 3 → ⭐ Lvl 4 → 🌟 Lvl 5 → 💫 Lvl 10 → 🔥 Lvl 15 → 💎 Lvl 20 → 👑 Lvl 25 → 🏆 Lvl 30",
        inline=False
    )
    
    await ctx.send(embed=xp_embed)

@bot.command(name="herniinfo")
@commands.has_permissions(administrator=True)
async def send_game_info(ctx):
    """!herniinfo - Pošle trvalou zprávu s herními příkazy do kanálu 1468355022159872073 (jen admin)"""
    
    # Delete the command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Získání cílového kanálu
    target_channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
    if not target_channel:
        await ctx.send("❌ Nepodařilo se najít cílový kanál!", delete_after=10)
        return
    
    # === HLAVNÍ EMBED - HERNÍ PŘÍKAZY ===
    main_embed = discord.Embed(
        title="🎮 HERNÍ SYSTÉM - PŘÍKAZY",
        description="Kompletní přehled herních příkazů a jak získat XP",
        color=discord.Color.green()
    )
    
    main_embed.add_field(
        name="📊 `/gamelevel` nebo `!level`",
        value="**Zobrazí tvůj herní profil:**\n"
              "• Aktuální level a XP\n"
              "• Počet odehraných kvízů\n"
              "• Přesnost odpovědí\n"
              "• Aktuální streak\n"
              "• Progress do dalšího levelu\n"
              "💡 *Můžeš zadat i jiného hráče: `/gamelevel @hrac`*",
        inline=False
    )
    
    main_embed.add_field(
        name="🏆 `/top` nebo `!top`",
        value="**Zobrazí žebříček TOP 10 hráčů:**\n"
              "• Seřazeno podle XP\n"
              "• Vidíš level, XP a badge každého hráče\n"
              "• Soutěž s ostatními o první místo!",
        inline=False
    )
    
    main_embed.add_field(
        name="🎁 `/daily` nebo `!daily`",
        value="**Denní bonus - získej ZDARMA:**\n"
              "• **+100 XP** každý den\n"
              "• **+10 XP bonus** za každý den streak\n"
              "• Streak = po sobě jdoucí dny\n"
              "• Reset streaku = vynechaný den\n"
              "⏰ *Resetuje se o půlnoci*",
        inline=False
    )
    
    main_embed.add_field(
        name="🕹️ `/hry` nebo `!hry`",
        value="**Zobrazí tvé odemčené hry:**\n"
              "• Seznam her které jsi hrál\n"
              "• Celkový čas hraní každé hry\n"
              "• Počet odemčených her\n"
              "• Emoji podle kategorie hry",
        inline=False
    )
    
    main_embed.add_field(
        name="📋 `/ukoly [hra]` nebo `!ukoly [hra]`",
        value="**Zobrazí úkoly pro konkrétní hru:**\n"
              "• Úkoly podle odehraného času\n"
              "• XP odměny za splnění\n"
              "• Vidíš které úkoly máš hotové ✅\n"
              "• Příklad: `/ukoly Minecraft`",
        inline=False
    )
    
    main_embed.set_footer(text="Tyto odpovědi se automaticky mažou po 1 minutě")
    
    # === DRUHÝ EMBED - JAK ZÍSKAT XP ===
    xp_embed = discord.Embed(
        title="✨ JAK ZÍSKAT XP",
        description="Všechny způsoby jak rychle levelovat",
        color=discord.Color.gold()
    )
    
    xp_embed.add_field(
        name="🎵 Hudební kvíz `/hudba`",
        value="**+25 XP** za správnou odpověď\n*Hádej interpreta podle textu*",
        inline=True
    )
    
    xp_embed.add_field(
        name="🎬 Filmový kvíz `/film`",
        value="**+25 XP** za správnou odpověď\n*Hádej film podle hlášky*",
        inline=True
    )
    
    xp_embed.add_field(
        name="🤔 Pravda/Lež `/pravda`",
        value="**+15 XP** za správnou odpověď\n*Je fakt pravdivý?*",
        inline=True
    )
    
    xp_embed.add_field(
        name="🎮 Hraní her na PC",
        value="**+5 XP** za každých 10 minut hraní\n"
              "**+25 XP** bonus za odemčení nové hry\n"
              "**Max 200 XP/den** z hraní\n"
              "*Automaticky detekuje hry přes Discord*",
        inline=False
    )
    
    xp_embed.add_field(
        name="🎁 Denní bonus",
        value="**+100 XP** každý den\n"
              "**+10 XP** bonus za streak",
        inline=True
    )
    
    xp_embed.add_field(
        name="🏅 Splněné úkoly",
        value="**+50 až +1500 XP**\n"
              "Podle náročnosti úkolu",
        inline=True
    )
    
    # === TŘETÍ EMBED - LEVEL SYSTÉM ===
    level_embed = discord.Embed(
        title="📈 LEVEL SYSTÉM",
        description="Čím víc XP, tím vyšší level a lepší badge!",
        color=discord.Color.purple()
    )
    
    level_embed.add_field(
        name="🏅 Odznaky podle levelu",
        value="🌱 **Lvl 1** → Nováček\n"
              "🌿 **Lvl 2** → Začátečník\n"
              "🌳 **Lvl 3** → Hráč\n"
              "⭐ **Lvl 4** → Pokročilý\n"
              "🌟 **Lvl 5** → Zkušený\n"
              "💫 **Lvl 10** → Veterán\n"
              "🔥 **Lvl 15** → Expert\n"
              "💎 **Lvl 20** → Mistr\n"
              "👑 **Lvl 25** → Šampion\n"
              "🏆 **Lvl 30** → Legenda",
        inline=True
    )
    
    level_embed.add_field(
        name="📊 XP potřebné pro level",
        value="**Lvl 2:** 100 XP\n"
              "**Lvl 3:** 400 XP\n"
              "**Lvl 5:** 1,600 XP\n"
              "**Lvl 10:** 8,100 XP\n"
              "**Lvl 15:** 19,600 XP\n"
              "**Lvl 20:** 36,100 XP\n"
              "**Lvl 25:** 57,600 XP\n"
              "**Lvl 30:** 84,100 XP",
        inline=True
    )
    
    level_embed.add_field(
        name="💡 TIPY",
        value="• Hraj kvízy každý den pro rychlé XP\n"
              "• Nezapomeň na `/daily` bonus\n"
              "• Hraj hry na PC pro pasivní XP\n"
              "• Plň úkoly pro velké bonusy",
        inline=False
    )
    
    level_embed.set_footer(text="⚔️ Valhalla Bot • Hraj, sbírej XP a staň se legendou!")
    
    # Odeslání všech embedů do cílového kanálu (trvalé zprávy)
    await target_channel.send(embed=main_embed)
    await target_channel.send(embed=xp_embed)
    await target_channel.send(embed=level_embed)
    
    # Potvrzení v původním kanálu
    await ctx.send(f"✅ Herní info bylo odesláno do kanálu <#{GAME_NOTIFICATION_CHANNEL}>!", delete_after=10)

@send_game_info.error
async def send_game_info_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tento příkaz může použít pouze administrátor!", delete_after=10)
    else:
        print(f"[ERROR] herniinfo: {error}", flush=True)
        await ctx.send(f"❌ Nastala chyba: {error}", delete_after=10)

# ============== GAME LEVEL SYSTEM ==============

LEVEL_BADGES = {
    1: "🌱", 2: "🌿", 3: "🌳", 4: "⭐", 5: "🌟",
    10: "💫", 15: "🔥", 20: "💎", 25: "👑", 30: "🏆",
    40: "🎯", 50: "🚀", 75: "🌈", 100: "🏅"
}

def get_badge(level: int) -> str:
    """Get badge for level"""
    badge = "🌱"
    for lvl, b in sorted(LEVEL_BADGES.items()):
        if level >= lvl:
            badge = b
    return badge

def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Create a visual progress bar"""
    if total == 0:
        return "▓" * length
    filled = int((current / total) * length)
    empty = length - filled
    return "▓" * filled + "░" * empty

@bot.tree.command(name="gamelevel", description="Zobraz svůj herní level a statistiky")
async def slash_gamelevel(interaction: discord.Interaction, hrac: discord.Member = None):
    # Check permission from database
    if not await check_command_permission(interaction, "gamelevel"):
        return
    
    target = hrac or interaction.user
    user_data = get_user_data(interaction.guild_id, target.id)
    
    level = calculate_level(user_data["xp"])
    current_level_xp = xp_for_level(level)
    next_level_xp = xp_for_level(level + 1)
    xp_progress = user_data["xp"] - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    
    badge = get_badge(level)
    progress_bar = create_progress_bar(xp_progress, xp_needed, 12)
    
    # Přesnost kvízů
    accuracy = 0
    if user_data.get("total_games", 0) > 0:
        accuracy = (user_data.get("total_correct", 0) / user_data["total_games"]) * 100
    
    # Herní statistiky
    unlocked_games = user_data.get("unlocked_games", [])
    total_game_time = user_data.get("total_game_time", 0)
    game_times = user_data.get("game_times", {})
    
    # Formátování času
    hours = total_game_time // 60
    minutes = total_game_time % 60
    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    
    embed = discord.Embed(
        title=f"{badge} {target.display_name}",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    # Základní statistiky
    embed.add_field(
        name="📊 Level",
        value=f"**Level {level}**",
        inline=True
    )
    embed.add_field(
        name="✨ XP",
        value=f"**{user_data['xp']:,}** XP",
        inline=True
    )
    embed.add_field(
        name="🔥 Streak",
        value=f"**{user_data.get('streak', 0)}** dnů",
        inline=True
    )
    
    # Progress bar
    embed.add_field(
        name=f"📈 Progress ({xp_progress:,}/{xp_needed:,} XP)",
        value=f"`{progress_bar}`",
        inline=False
    )
    
    # Kvízové statistiky
    embed.add_field(
        name="🎮 Kvízů",
        value=f"**{user_data.get('total_games', 0)}**",
        inline=True
    )
    embed.add_field(
        name="✅ Správně",
        value=f"**{user_data.get('total_correct', 0)}**",
        inline=True
    )
    embed.add_field(
        name="🎯 Přesnost",
        value=f"**{accuracy:.1f}%**",
        inline=True
    )
    
    # Herní statistiky (PC hry)
    embed.add_field(
        name="🕹️ Odemčené hry",
        value=f"**{len(unlocked_games)}** her",
        inline=True
    )
    embed.add_field(
        name="⏱️ Čas hraní",
        value=f"**{time_str}**",
        inline=True
    )
    embed.add_field(
        name="📅 Denní XP",
        value=f"**{user_data.get('daily_game_xp', 0)}/{GAME_XP_DAILY_LIMIT}**",
        inline=True
    )
    
    # Top 3 nejhranější hry
    if game_times:
        sorted_games = sorted(game_times.items(), key=lambda x: x[1], reverse=True)[:3]
        top_games = []
        for game, mins in sorted_games:
            g_hours = mins // 60
            g_mins = mins % 60
            g_time = f"{g_hours}h {g_mins}m" if g_hours > 0 else f"{g_mins}m"
            top_games.append(f"• **{game}**: {g_time}")
        
        if top_games:
            embed.add_field(
                name="🎮 Nejhranější hry",
                value="\n".join(top_games),
                inline=False
            )
    
    embed.set_footer(text="⚔️ Valhalla Bot • /hry pro všechny hry • /ukoly pro úkoly")
    
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    asyncio.create_task(delete_after(msg, 60))

@bot.command(name="level", aliases=["lvl", "gamelevel", "rank", "xp"])
async def prefix_gamelevel(ctx, hrac: discord.Member = None):
    """!level - Zobraz svůj level"""
    target = hrac or ctx.author
    user_data = get_user_data(ctx.guild.id, target.id)
    
    level = calculate_level(user_data["xp"])
    current_level_xp = xp_for_level(level)
    next_level_xp = xp_for_level(level + 1)
    xp_progress = user_data["xp"] - current_level_xp
    xp_needed = next_level_xp - current_level_xp
    
    badge = get_badge(level)
    progress_bar = create_progress_bar(xp_progress, xp_needed, 12)
    
    # Přesnost kvízů
    accuracy = 0
    if user_data.get("total_games", 0) > 0:
        accuracy = (user_data.get("total_correct", 0) / user_data["total_games"]) * 100
    
    # Herní statistiky
    unlocked_games = user_data.get("unlocked_games", [])
    total_game_time = user_data.get("total_game_time", 0)
    game_times = user_data.get("game_times", {})
    
    # Formátování času
    hours = total_game_time // 60
    minutes = total_game_time % 60
    time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
    
    embed = discord.Embed(
        title=f"{badge} {target.display_name}",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    
    # Základní statistiky
    embed.add_field(name="📊 Level", value=f"**Level {level}**", inline=True)
    embed.add_field(name="✨ XP", value=f"**{user_data['xp']:,}** XP", inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{user_data.get('streak', 0)}** dnů", inline=True)
    
    embed.add_field(name=f"📈 Progress ({xp_progress:,}/{xp_needed:,} XP)", value=f"`{progress_bar}`", inline=False)
    
    # Kvízové statistiky
    embed.add_field(name="🎮 Kvízů", value=f"**{user_data.get('total_games', 0)}**", inline=True)
    embed.add_field(name="✅ Správně", value=f"**{user_data.get('total_correct', 0)}**", inline=True)
    embed.add_field(name="🎯 Přesnost", value=f"**{accuracy:.1f}%**", inline=True)
    
    # Herní statistiky
    embed.add_field(name="🕹️ Odemčené hry", value=f"**{len(unlocked_games)}** her", inline=True)
    embed.add_field(name="⏱️ Čas hraní", value=f"**{time_str}**", inline=True)
    embed.add_field(name="📅 Denní XP", value=f"**{user_data.get('daily_game_xp', 0)}/{DAILY_XP_LIMIT}**", inline=True)
    
    # Top 3 nejhranější hry
    if game_times:
        sorted_games = sorted(game_times.items(), key=lambda x: x[1], reverse=True)[:3]
        top_games = []
        for game, mins in sorted_games:
            g_hours = mins // 60
            g_mins = mins % 60
            g_time = f"{g_hours}h {g_mins}m" if g_hours > 0 else f"{g_mins}m"
            top_games.append(f"• **{game}**: {g_time}")
        
        if top_games:
            embed.add_field(name="🎮 Nejhranější hry", value="\n".join(top_games), inline=False)
    
    embed.set_footer(text="⚔️ Valhalla Bot • /hry pro všechny hry • /ukoly pro úkoly")
    
    msg = await ctx.send(embed=embed)
    asyncio.create_task(delete_after(msg, 60))

@bot.tree.command(name="top", description="Zobraz žebříček hráčů")
async def slash_top(interaction: discord.Interaction):
    # Check permission from database
    if not await check_command_permission(interaction, "top"):
        return
    
    # Get top 10 users for this guild
    top_users = list(users_collection.find(
        {"guild_id": interaction.guild_id}
    ).sort("xp", -1).limit(10))
    
    if not top_users:
        await interaction.response.send_message("📊 Zatím nikdo nehrál! Začni s `/hudba` nebo `/film`", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏆 TOP HRÁČI",
        color=discord.Color.gold()
    )
    
    medals = ["🥇", "🥈", "🥉"]
    leaderboard = []
    
    for i, user in enumerate(top_users):
        level = calculate_level(user["xp"])
        badge = get_badge(level)
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        name = user.get("name", f"Hráč {user['user_id']}")
        leaderboard.append(f"{medal} {badge} **{name}** • Level {level} • {user['xp']} XP")
    
    embed.description = "\n".join(leaderboard)
    embed.set_footer(text="⚔️ Valhalla Bot • Získej XP hraním kvízů!")
    
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    asyncio.create_task(delete_after(msg, 60))

@bot.command(name="top", aliases=["leaderboard", "lb", "zebricek"])
async def prefix_top(ctx):
    """!top - Zobraz žebříček"""
    top_users = list(users_collection.find(
        {"guild_id": ctx.guild.id}
    ).sort("xp", -1).limit(10))
    
    if not top_users:
        msg = await ctx.send("📊 Zatím nikdo nehrál! Začni s `!hudba` nebo `!film`")
        asyncio.create_task(delete_after(msg, 60))
        return
    
    embed = discord.Embed(title="🏆 TOP HRÁČI", color=discord.Color.gold())
    
    medals = ["🥇", "🥈", "🥉"]
    leaderboard = []
    
    for i, user in enumerate(top_users):
        level = calculate_level(user["xp"])
        badge = get_badge(level)
        medal = medals[i] if i < 3 else f"`{i+1}.`"
        name = user.get("name", f"Hráč {user['user_id']}")
        leaderboard.append(f"{medal} {badge} **{name}** • Level {level} • {user['xp']} XP")
    
    embed.description = "\n".join(leaderboard)
    msg = await ctx.send(embed=embed)
    asyncio.create_task(delete_after(msg, 60))

@bot.tree.command(name="daily", description="Získej denní bonus XP!")
async def slash_daily(interaction: discord.Interaction):
    # Check permission from database
    if not await check_command_permission(interaction, "daily"):
        return
    
    guild_id = interaction.guild_id
    user_id = interaction.user.id
    user_data = get_user_data(guild_id, user_id)
    
    now = datetime.now(timezone.utc)
    last_daily = user_data.get("last_daily")
    
    if last_daily:
        if isinstance(last_daily, str):
            last_daily = datetime.fromisoformat(last_daily.replace('Z', '+00:00'))
        
        time_diff = now - last_daily
        if time_diff.total_seconds() < 86400:  # 24 hours
            remaining = 86400 - time_diff.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await interaction.response.send_message(
                f"⏰ Denní bonus už jsi dnes vybral/a!\nDalší za **{hours}h {minutes}m**",
                ephemeral=True
            )
            return
        
        # Check streak
        if time_diff.total_seconds() < 172800:  # 48 hours - streak continues
            new_streak = user_data.get("streak", 0) + 1
        else:
            new_streak = 1  # Streak reset
    else:
        new_streak = 1
    
    # Calculate bonus
    base_xp = XP_REWARDS["daily"]
    streak_bonus = min(new_streak - 1, 10) * XP_REWARDS["streak_bonus"]  # Max 10 days bonus
    total_xp = base_xp + streak_bonus
    
    # Update user
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {
            "$set": {"last_daily": now, "streak": new_streak},
            "$inc": {"xp": total_xp}
        }
    )
    
    new_xp = user_data["xp"] + total_xp
    new_level = calculate_level(new_xp)
    old_level = calculate_level(user_data["xp"])
    
    embed = discord.Embed(
        title="🎁 DENNÍ BONUS!",
        color=discord.Color.green()
    )
    embed.add_field(name="✨ Získáno", value=f"+**{total_xp}** XP", inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{new_streak}** dnů", inline=True)
    
    if streak_bonus > 0:
        embed.add_field(name="💫 Streak bonus", value=f"+{streak_bonus} XP", inline=True)
    
    embed.set_footer(text="Vrať se zítra pro další bonus!")
    
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    asyncio.create_task(delete_after(msg, 60))
    
    # Level up check
    if new_level > old_level:
        badge = get_badge(new_level)
        level_embed = discord.Embed(
            title="🎉 LEVEL UP!",
            description=f"**{interaction.user.display_name}** dosáhl/a **Level {new_level}** {badge}!",
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=level_embed)

@bot.command(name="daily", aliases=["denni", "bonus"])
async def prefix_daily(ctx):
    """!daily - Získej denní bonus"""
    guild_id = ctx.guild.id
    user_id = ctx.author.id
    user_data = get_user_data(guild_id, user_id)
    
    now = datetime.now(timezone.utc)
    last_daily = user_data.get("last_daily")
    
    if last_daily:
        if isinstance(last_daily, str):
            last_daily = datetime.fromisoformat(last_daily.replace('Z', '+00:00'))
        
        time_diff = now - last_daily
        if time_diff.total_seconds() < 86400:
            remaining = 86400 - time_diff.total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            await ctx.send(f"⏰ Denní bonus už jsi dnes vybral/a! Další za **{hours}h {minutes}m**")
            return
        
        if time_diff.total_seconds() < 172800:
            new_streak = user_data.get("streak", 0) + 1
        else:
            new_streak = 1
    else:
        new_streak = 1
    
    base_xp = XP_REWARDS["daily"]
    streak_bonus = min(new_streak - 1, 10) * XP_REWARDS["streak_bonus"]
    total_xp = base_xp + streak_bonus
    
    users_collection.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {
            "$set": {"last_daily": now, "streak": new_streak},
            "$inc": {"xp": total_xp}
        }
    )
    
    embed = discord.Embed(title="🎁 DENNÍ BONUS!", color=discord.Color.green())
    embed.add_field(name="✨ Získáno", value=f"+**{total_xp}** XP", inline=True)
    embed.add_field(name="🔥 Streak", value=f"**{new_streak}** dnů", inline=True)
    if streak_bonus > 0:
        embed.add_field(name="💫 Streak bonus", value=f"+{streak_bonus} XP", inline=True)
    embed.set_footer(text="Vrať se zítra pro další bonus!")
    
    msg = await ctx.send(embed=embed)
    asyncio.create_task(delete_after(msg, 60))

# ============== GAME TRACKING ==============

@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member):
    """Track when users start/stop playing games"""
    
    # Get the game activity
    before_game = None
    after_game = None
    
    for activity in before.activities:
        if activity.type == discord.ActivityType.playing:
            before_game = activity.name
            break
    
    for activity in after.activities:
        if activity.type == discord.ActivityType.playing:
            after_game = activity.name
            break
    
    # Skip if no change
    if before_game == after_game:
        return
    
    print(f"[GAME] {after.display_name}: '{before_game}' -> '{after_game}'", flush=True)
    
    user_id = after.id
    guild_id = after.guild.id
    
    # Started playing a game
    if after_game and not before_game:
        print(f"[GAME] ▶️ {after.display_name} začal hrát: {after_game}", flush=True)
        
        # Ulož do paměti i databáze
        active_gaming_sessions[user_id] = {
            "game": after_game,
            "start": datetime.now(timezone.utc),
            "guild_id": guild_id,
            "user_name": after.display_name
        }
        save_game_session(user_id, guild_id, after_game, after.display_name)
        
        # Get notification channel - VŽDY do správného kanálu
        channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
        
        # Check if it's a bonus game to unlock
        if after_game in BONUS_GAMES:
            await unlock_game(guild_id, user_id, after.display_name, after_game, channel)
    
    # Stopped playing a game
    elif before_game and not after_game:
        # Zkus načíst session z paměti nebo databáze
        session = active_gaming_sessions.get(user_id) or get_game_session(user_id)
        
        if session:
            start_time = session["start"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            minutes_played = int((datetime.now(timezone.utc) - start_time).total_seconds() / 60)
            
            print(f"[GAME] ⏹️ {session['user_name']} skončil hrát: {session['game']} ({minutes_played} min)", flush=True)
            
            if minutes_played >= 10:
                # Get notification channel - VŽDY do správného kanálu
                channel = bot.get_channel(GAME_NOTIFICATION_CHANNEL)
                
                xp_earned = await add_game_xp(
                    session["guild_id"],
                    user_id,
                    session["user_name"],
                    minutes_played,
                    session["game"],
                    channel
                )
                
                if xp_earned > 0 and channel:
                    embed = discord.Embed(
                        title="🎮 XP za hraní!",
                        description=f"**{session['user_name']}** hrál/a **{session['game']}**",
                        color=discord.Color.blue()
                    )
                    embed.add_field(name="⏱️ Čas", value=f"{minutes_played} min", inline=True)
                    embed.add_field(name="✨ XP", value=f"+{xp_earned} XP", inline=True)
                    
                    daily_xp = get_daily_game_xp(guild_id, user_id)
                    embed.add_field(name="📊 Denní limit", value=f"{daily_xp}/{GAME_XP_DAILY_LIMIT}", inline=True)
                    embed.set_footer(text="Hraj hry a získávej XP!")
                    await channel.send(embed=embed)
            
            # Smaž z paměti i databáze
            if user_id in active_gaming_sessions:
                del active_gaming_sessions[user_id]
            delete_game_session(user_id)
    
    # Changed game
    elif before_game and after_game and before_game != after_game:
        # End previous session - zkus z paměti nebo databáze
        session = active_gaming_sessions.get(user_id) or get_game_session(user_id)
        
        if session:
            start_time = session["start"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            minutes_played = int((datetime.now(timezone.utc) - start_time).total_seconds() / 60)
            
            if minutes_played >= 10:
                await add_game_xp(guild_id, user_id, after.display_name, minutes_played, session["game"], None)
        
        # Start new session - ulož do paměti i databáze
        active_gaming_sessions[user_id] = {
            "game": after_game,
            "start": datetime.now(timezone.utc),
            "guild_id": guild_id,
            "user_name": after.display_name
        }
        save_game_session(user_id, guild_id, after_game, after.display_name)
        
        # Check if new game is bonus game
        if after_game in BONUS_GAMES:
            channel = after.guild.system_channel
            if not channel:
                for ch in after.guild.text_channels:
                    if ch.permissions_for(after.guild.me).send_messages:
                        channel = ch
                        break
            await unlock_game(guild_id, user_id, after.display_name, after_game, channel)

@bot.tree.command(name="ukoly", description="Zobraz úkoly pro konkrétní hru")
@app_commands.describe(hra="Vyber hru pro zobrazení úkolů")
@app_commands.choices(hra=[
    app_commands.Choice(name="🎯 Counter-Strike 2", value="Counter-Strike 2"),
    app_commands.Choice(name="⛏️ Minecraft", value="Minecraft"),
    app_commands.Choice(name="⚔️ League of Legends", value="League of Legends"),
    app_commands.Choice(name="🏝️ Fortnite", value="Fortnite"),
    app_commands.Choice(name="🔫 VALORANT", value="VALORANT"),
    app_commands.Choice(name="🚔 GTA V", value="GTA V"),
    app_commands.Choice(name="🚗 Rocket League", value="Rocket League"),
])
async def slash_ukoly(interaction: discord.Interaction, hra: str):
    # Check permission from database
    if not await check_command_permission(interaction, "ukoly"):
        return
    
    user_data = get_user_data(interaction.guild_id, interaction.user.id)
    game_time = user_data.get("game_times", {}).get(hra, 0)
    completed = user_data.get("completed_quests", {}).get(hra, [])
    quests = get_game_quests(hra)
    
    game_emoji = BONUS_GAMES.get(hra, {}).get("emoji", "🎮")
    
    embed = discord.Embed(
        title=f"{game_emoji} Úkoly - {hra}",
        description=f"Tvůj čas: **{game_time // 60}h {game_time % 60}m**",
        color=discord.Color.purple()
    )
    
    quest_list = []
    total_xp = 0
    earned_xp = 0
    
    for i, quest in enumerate(quests):
        total_xp += quest["xp"]
        hours = quest["minutes"] // 60
        mins = quest["minutes"] % 60
        time_str = f"{hours}h" if hours > 0 else f"{mins}m"
        if hours > 0 and mins > 0:
            time_str = f"{hours}h {mins}m"
        
        if i in completed:
            quest_list.append(f"✅ {quest['emoji']} **{quest['name']}** - {time_str} (+{quest['xp']} XP)")
            earned_xp += quest["xp"]
        elif game_time >= quest["minutes"]:
            # Ready to claim (should auto-complete, but just in case)
            quest_list.append(f"🎁 {quest['emoji']} **{quest['name']}** - {time_str} (+{quest['xp']} XP)")
        else:
            progress = min(100, (game_time / quest["minutes"]) * 100)
            quest_list.append(f"🔒 {quest['emoji']} {quest['name']} - {time_str} (+{quest['xp']} XP) [{progress:.0f}%]")
    
    embed.add_field(name="📋 Úkoly", value="\n".join(quest_list), inline=False)
    embed.add_field(name="💰 Získáno XP", value=f"{earned_xp}/{total_xp} XP", inline=True)
    embed.add_field(name="✅ Splněno", value=f"{len(completed)}/{len(quests)}", inline=True)
    
    embed.set_footer(text="Hraj hru a úkoly se automaticky splní!")
    
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    asyncio.create_task(delete_after(msg, 60))

@bot.command(name="ukoly", aliases=["quests", "mise", "tasks"])
async def prefix_ukoly(ctx, *, hra: str = None):
    """!ukoly [hra] - Zobraz úkoly pro hru"""
    if not hra:
        # Show available games
        embed = discord.Embed(
            title="🎯 Herní úkoly",
            description="Vyber hru pro zobrazení úkolů:",
            color=discord.Color.purple()
        )
        games_with_quests = list(GAME_QUESTS.keys())
        games_with_quests.remove("default")
        
        game_list = []
        for game in games_with_quests:
            emoji = BONUS_GAMES.get(game, {}).get("emoji", "🎮")
            game_list.append(f"{emoji} `!ukoly {game}`")
        
        embed.add_field(name="Dostupné hry", value="\n".join(game_list), inline=False)
        embed.set_footer(text="Nebo hraj jakoukoli hru - budeš mít základní úkoly!")
        msg = await ctx.send(embed=embed)
        asyncio.create_task(delete_after(msg, 60))
        return
    
    # Find matching game
    game_name = None
    for name in GAME_QUESTS.keys():
        if name.lower() == hra.lower() or hra.lower() in name.lower():
            game_name = name
            break
    
    if not game_name or game_name == "default":
        # Use the input as game name with default quests
        game_name = hra
    
    user_data = get_user_data(ctx.guild.id, ctx.author.id)
    game_time = user_data.get("game_times", {}).get(game_name, 0)
    completed = user_data.get("completed_quests", {}).get(game_name, [])
    quests = get_game_quests(game_name)
    
    game_emoji = BONUS_GAMES.get(game_name, {}).get("emoji", "🎮")
    
    embed = discord.Embed(
        title=f"{game_emoji} Úkoly - {game_name}",
        description=f"Tvůj čas: **{game_time // 60}h {game_time % 60}m**",
        color=discord.Color.purple()
    )
    
    quest_list = []
    total_xp = 0
    earned_xp = 0
    
    for i, quest in enumerate(quests):
        total_xp += quest["xp"]
        hours = quest["minutes"] // 60
        mins = quest["minutes"] % 60
        time_str = f"{hours}h" if hours > 0 else f"{mins}m"
        
        if i in completed:
            quest_list.append(f"✅ {quest['emoji']} **{quest['name']}** (+{quest['xp']} XP)")
            earned_xp += quest["xp"]
        else:
            progress = min(100, (game_time / quest["minutes"]) * 100) if quest["minutes"] > 0 else 0
            quest_list.append(f"🔒 {quest['emoji']} {quest['name']} - {time_str} [{progress:.0f}%]")
    
    embed.add_field(name="📋 Úkoly", value="\n".join(quest_list), inline=False)
    embed.add_field(name="💰 XP", value=f"{earned_xp}/{total_xp}", inline=True)
    embed.add_field(name="✅ Splněno", value=f"{len(completed)}/{len(quests)}", inline=True)
    
    msg = await ctx.send(embed=embed)
    asyncio.create_task(delete_after(msg, 60))

# ============== POLL SYSTEM ==============

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

# Store active polls: {poll_id: {votes: {user_id: option_index}, names: {user_id: name}, ...}}
active_polls = {}

class PollView(discord.ui.View):
    def __init__(self, poll_id: str, options: list, author_id: int, end_time: int):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.options = options
        self.author_id = author_id
        self.end_time = end_time
        
        # Add buttons for each option
        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option[:50],  # Limit label length
                style=discord.ButtonStyle.secondary,
                emoji=NUMBER_EMOJIS[i],
                custom_id=f"poll_{poll_id}_{i}"
            )
            button.callback = self.make_vote_callback(i)
            self.add_item(button)
    
    def make_vote_callback(self, option_index: int):
        async def callback(interaction: discord.Interaction):
            poll_data = active_polls.get(self.poll_id)
            if not poll_data:
                await interaction.response.send_message("❌ Tato anketa již skončila!", ephemeral=True)
                return
            
            user_id = interaction.user.id
            user_name = interaction.user.display_name  # Get display name directly
            
            # Check if user already voted
            if user_id in poll_data["votes"]:
                previous_vote = poll_data["votes"][user_id]
                if previous_vote == option_index:
                    await interaction.response.send_message(
                        f"❌ Již jsi hlasoval pro **{self.options[option_index]}**!",
                        ephemeral=True
                    )
                    return
                else:
                    # Change vote
                    poll_data["votes"][user_id] = option_index
                    poll_data["names"][user_id] = user_name  # Update name
                    await interaction.response.send_message(
                        f"🔄 Změnil jsi hlas na **{self.options[option_index]}**!",
                        ephemeral=True
                    )
            else:
                # New vote
                poll_data["votes"][user_id] = option_index
                poll_data["names"][user_id] = user_name  # Store name
                await interaction.response.send_message(
                    f"✅ Hlasoval jsi pro **{self.options[option_index]}**!",
                    ephemeral=True
                )
        
        return callback

def get_poll_results(poll_id: str, options: list, guild) -> str:
    """Generate poll results text with voter names"""
    poll_data = active_polls.get(poll_id, {"votes": {}, "names": {}})
    votes = poll_data["votes"]
    names = poll_data.get("names", {})
    
    total_votes = len(votes)
    vote_counts = [0] * len(options)
    voters_by_option = [[] for _ in options]
    
    for user_id, option_index in votes.items():
        vote_counts[option_index] += 1
        # Get stored name
        user_name = names.get(user_id, f"User#{user_id}")
        voters_by_option[option_index].append(user_name)
    
    results = []
    for i, option in enumerate(options):
        count = vote_counts[i]
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 10)
        bar = "█" * bar_length + "░" * (10 - bar_length)
        
        # Format voter names
        if voters_by_option[i]:
            voter_names = ", ".join(voters_by_option[i][:10])  # Max 10 names
            if len(voters_by_option[i]) > 10:
                voter_names += f" +{len(voters_by_option[i]) - 10} dalších"
            voters_text = f"\n👤 {voter_names}"
        else:
            voters_text = ""
        
        results.append(f"{NUMBER_EMOJIS[i]} **{option}**\n`{bar}` {percentage:.1f}% ({count}){voters_text}")
    
    return "\n\n".join(results)

def get_live_options_text(options: list, poll_id: str, guild) -> str:
    """Generate options text with live vote counts and voter names"""
    poll_data = active_polls.get(poll_id, {"votes": {}, "names": {}})
    votes = poll_data["votes"]
    names = poll_data.get("names", {})
    total_votes = len(votes)
    vote_counts = [0] * len(options)
    voters_by_option = [[] for _ in options]
    
    for user_id, option_index in votes.items():
        vote_counts[option_index] += 1
        user_name = names.get(user_id, f"User#{user_id}")
        voters_by_option[option_index].append(user_name)
    
    lines = []
    for i, opt in enumerate(options):
        count = vote_counts[i]
        percentage = (count / total_votes * 100) if total_votes > 0 else 0
        bar_length = int(percentage / 5)
        bar = "▓" * bar_length + "░" * (20 - bar_length)
        
        # Show voter names (max 5 in live view)
        if voters_by_option[i]:
            voter_names = ", ".join(voters_by_option[i][:5])
            if len(voters_by_option[i]) > 5:
                voter_names += f" +{len(voters_by_option[i]) - 5}"
            voters_text = f"\n   👤 {voter_names}"
        else:
            voters_text = ""
        
        lines.append(f"{NUMBER_EMOJIS[i]} {opt}\n`{bar}` {percentage:.0f}% ({count}){voters_text}")
    
    return "\n".join(lines)

async def run_poll(channel, message, poll_id: str, options: list, author: discord.Member, question: str, end_time: int, guild):
    """Run the poll and end it when time expires"""
    
    while True:
        if poll_id not in active_polls:
            return
        
        remaining = end_time - int(datetime.now(timezone.utc).timestamp())
        
        if remaining <= 0:
            break
        
        # Update embed with current votes and time
        poll_data = active_polls.get(poll_id, {"votes": {}})
        total_votes = len(poll_data["votes"])
        
        options_text = get_live_options_text(options, poll_id, guild)
        
        embed = discord.Embed(
            title="📊 ANKETA",
            description=f"**{question}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Možnosti", value=options_text if options_text else "Žádné hlasy", inline=False)
        embed.add_field(name="⏰ Zbývá", value=f"**{format_time(remaining)}**", inline=True)
        embed.add_field(name="👥 Hlasů", value=f"**{total_votes}**", inline=True)
        embed.add_field(name="👤 Autor", value=author.mention, inline=True)
        embed.set_footer(text="Klikni na tlačítko pro hlasování • 1 hlas na osobu")
        
        try:
            await message.edit(embed=embed)
        except:
            pass
        
        # Update interval based on remaining time
        if remaining > 300:  # > 5 min
            await asyncio.sleep(30)
        elif remaining > 60:  # > 1 min
            await asyncio.sleep(10)
        else:
            await asyncio.sleep(3)
    
    # Poll ended - show final results
    if poll_id not in active_polls:
        return
    
    poll_data = active_polls[poll_id]
    total_votes = len(poll_data["votes"])
    
    results_text = get_poll_results(poll_id, options, guild)
    
    embed = discord.Embed(
        title="📊 ANKETA UKONČENA!",
        description=f"**{question}**",
        color=discord.Color.green()
    )
    embed.add_field(name="Výsledky", value=results_text if results_text else "Žádné hlasy", inline=False)
    embed.add_field(name="👥 Celkem hlasů", value=f"**{total_votes}**", inline=True)
    embed.add_field(name="👤 Autor", value=author.mention, inline=True)
    embed.set_footer(text="Anketa skončila")
    
    # Disable all buttons
    view = discord.ui.View()
    for i, option in enumerate(options):
        btn = discord.ui.Button(
            label=option[:50],
            style=discord.ButtonStyle.secondary,
            emoji=NUMBER_EMOJIS[i],
            disabled=True
        )
        view.add_item(btn)
    
    try:
        await message.edit(embed=embed, view=view)
    except:
        pass
    
    # Announce winner
    if total_votes > 0:
        vote_counts = [0] * len(options)
        for option_index in poll_data["votes"].values():
            vote_counts[option_index] += 1
        
        max_votes = max(vote_counts)
        winners = [options[i] for i, count in enumerate(vote_counts) if count == max_votes]
        
        if len(winners) == 1:
            winner_text = f"🏆 **Vítěz: {winners[0]}** s {max_votes} hlasy!"
        else:
            winner_text = f"🏆 **Remíza:** {', '.join(winners)} s {max_votes} hlasy!"
        
        await channel.send(f"📊 **Anketa skončila!** {author.mention}\n{winner_text}")
    
    # Cleanup
    del active_polls[poll_id]

@bot.tree.command(name="poll", description="Vytvoř anketu s více možnostmi")
@app_commands.describe(
    otazka="Otázka ankety",
    moznosti="Možnosti oddělené čárkou (max 10)",
    cas="Doba trvání ankety (např. 5m, 1h, 1d)"
)
async def slash_poll(interaction: discord.Interaction, otazka: str, moznosti: str, cas: str = "5m"):
    # Parse options
    options = [opt.strip() for opt in moznosti.split(",") if opt.strip()]
    
    if len(options) < 2:
        await interaction.response.send_message("❌ Musíš zadat alespoň 2 možnosti!", ephemeral=True)
        return
    
    if len(options) > 10:
        await interaction.response.send_message("❌ Maximum je 10 možností!", ephemeral=True)
        return
    
    # Parse time
    seconds = parse_time(cas)
    if seconds is None:
        await interaction.response.send_message(
            "❌ Neplatný formát času! Použij např. `5m`, `1h`, `1d`",
            ephemeral=True
        )
        return
    
    if seconds < 30:
        await interaction.response.send_message("❌ Minimální čas je 30 sekund!", ephemeral=True)
        return
    
    if seconds > 86400 * 7:
        await interaction.response.send_message("❌ Maximální čas je 7 dní!", ephemeral=True)
        return
    
    poll_id = str(uuid.uuid4())
    end_time = int(datetime.now(timezone.utc).timestamp()) + seconds
    
    # Create poll data
    active_polls[poll_id] = {"votes": {}, "names": {}, "options": options}
    
    # Build options text
    options_text = "\n".join([f"{NUMBER_EMOJIS[i]} {opt}" for i, opt in enumerate(options)])
    
    embed = discord.Embed(
        title="📊 ANKETA",
        description=f"**{otazka}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Možnosti", value=options_text, inline=False)
    embed.add_field(name="⏰ Končí za", value=format_time(seconds), inline=True)
    embed.add_field(name="👤 Autor", value=interaction.user.mention, inline=True)
    embed.set_footer(text="Klikni na tlačítko pro hlasování • 1 hlas na osobu")
    
    view = PollView(poll_id, options, interaction.user.id, end_time)
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    # Start poll task
    asyncio.create_task(run_poll(
        interaction.channel,
        message,
        poll_id,
        options,
        interaction.user,
        otazka,
        end_time,
        interaction.guild
    ))

@bot.command(name="poll", aliases=["anketa", "hlasovani"])
async def prefix_poll(ctx, cas: str, *, args: str):
    """!poll 5m Otázka? | Možnost1, Možnost2, Možnost3"""
    
    # Parse: question | options
    if "|" not in args:
        await ctx.send("❌ Použij formát: `!poll 5m Otázka? | Možnost1, Možnost2, Možnost3`")
        return
    
    parts = args.split("|")
    otazka = parts[0].strip()
    moznosti_str = parts[1].strip() if len(parts) > 1 else ""
    
    options = [opt.strip() for opt in moznosti_str.split(",") if opt.strip()]
    
    if len(options) < 2:
        await ctx.send("❌ Musíš zadat alespoň 2 možnosti!")
        return
    
    if len(options) > 10:
        await ctx.send("❌ Maximum je 10 možností!")
        return
    
    seconds = parse_time(cas)
    if seconds is None:
        await ctx.send("❌ Neplatný formát času! Použij např. `5m`, `1h`, `1d`")
        return
    
    if seconds < 30:
        await ctx.send("❌ Minimální čas je 30 sekund!")
        return
    
    if seconds > 86400 * 7:
        await ctx.send("❌ Maximální čas je 7 dní!")
        return
    
    poll_id = str(uuid.uuid4())
    end_time = int(datetime.now(timezone.utc).timestamp()) + seconds
    
    active_polls[poll_id] = {"votes": {}, "names": {}, "options": options}
    
    options_text = "\n".join([f"{NUMBER_EMOJIS[i]} {opt}" for i, opt in enumerate(options)])
    
    embed = discord.Embed(
        title="📊 ANKETA",
        description=f"**{otazka}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Možnosti", value=options_text, inline=False)
    embed.add_field(name="⏰ Končí za", value=format_time(seconds), inline=True)
    embed.add_field(name="👤 Autor", value=ctx.author.mention, inline=True)
    embed.set_footer(text="Klikni na tlačítko pro hlasování • 1 hlas na osobu")
    
    view = PollView(poll_id, options, ctx.author.id, end_time)
    
    message = await ctx.send(embed=embed, view=view)
    
    asyncio.create_task(run_poll(
        ctx.channel,
        message,
        poll_id,
        options,
        ctx.author,
        otazka,
        end_time,
        ctx.guild
    ))

# ============== MUSIC QUIZ ==============

# Czech music database - lyrics snippets with artist and song
CZECH_MUSIC = {
    "rap": [
        # Yzomandias
        {"lyrics": "Hele, víš co? Uděláme si to po svým", "artist": "Yzomandias", "song": "Po svým", "hint": "Y_______"},
        {"lyrics": "Přišel jsem z ničeho, teď mám všechno", "artist": "Yzomandias", "song": "Z ničeho", "hint": "Y_______"},
        {"lyrics": "Prodávám sny, lidi kupujou", "artist": "Yzomandias", "song": "Sny", "hint": "Y_______"},
        {"lyrics": "Celej block ví, že jsem number one", "artist": "Yzomandias", "song": "Block", "hint": "Y_______"},
        {"lyrics": "Runway, dneska letím vysoko", "artist": "Yzomandias", "song": "Runway", "hint": "Y_______"},
        {"lyrics": "Bohatství a sláva, to je ten sen", "artist": "Yzomandias", "song": "Bohatství", "hint": "Y_______"},
        {"lyrics": "Milion důvodů proč neskončit", "artist": "Yzomandias", "song": "Milion", "hint": "Y_______"},
        {"lyrics": "Nemůžu spát, myslím na cash", "artist": "Yzomandias", "song": "Cash", "hint": "Y_______"},
        # Viktor Sheen
        {"lyrics": "Můj svět je šedej, ale nebe je modrý", "artist": "Viktor Sheen", "song": "Barvy", "hint": "Viktor S____"},
        {"lyrics": "Nemám čas na fake love, mám čas na real shit", "artist": "Viktor Sheen", "song": "Real Shit", "hint": "Viktor S____"},
        {"lyrics": "Zlatý časy, stříbrný vzpomínky", "artist": "Viktor Sheen", "song": "Zlatý časy", "hint": "Viktor S____"},
        {"lyrics": "Noční město svítí, já jdu za svým", "artist": "Viktor Sheen", "song": "Noční město", "hint": "Viktor S____"},
        {"lyrics": "Černý Mercedes, jedu městem", "artist": "Viktor Sheen", "song": "Mercedes", "hint": "Viktor S____"},
        {"lyrics": "Nechci zpátky, jdu dopředu", "artist": "Viktor Sheen", "song": "Dopředu", "hint": "Viktor S____"},
        {"lyrics": "Láska je jed, co mi teče v žilách", "artist": "Viktor Sheen", "song": "Jed", "hint": "Viktor S____"},
        # Calin
        {"lyrics": "Jednou budem všichni v zemi, užij si ten den", "artist": "Calin", "song": "Jednou", "hint": "C____"},
        {"lyrics": "Jsem král svýho světa, nikdo mi neporučí", "artist": "Calin", "song": "Král", "hint": "C____"},
        {"lyrics": "Money na mým stole, stress v mojí hlavě", "artist": "Calin", "song": "Money", "hint": "C____"},
        {"lyrics": "Dream team, my jsme ti nejlepší", "artist": "Calin", "song": "Dream team", "hint": "C____"},
        {"lyrics": "Pohádka o klukovi z ulice", "artist": "Calin", "song": "Pohádka", "hint": "C____"},
        {"lyrics": "Diamanty na krku, zlato na ruce", "artist": "Calin", "song": "Diamanty", "hint": "C____"},
        # Nik Tendo
        {"lyrics": "Mám v kapse pár stovek a to mi stačí", "artist": "Nik Tendo", "song": "Stovky", "hint": "Nik T____"},
        {"lyrics": "V hlavě mám démony, co mě ženou dál", "artist": "Nik Tendo", "song": "Démoni", "hint": "Nik T____"},
        {"lyrics": "Neřeším co říkaj, dělám svý", "artist": "Nik Tendo", "song": "Svý", "hint": "Nik T____"},
        {"lyrics": "Mám stack v kapse, flex na maximum", "artist": "Nik Tendo", "song": "Stack", "hint": "Nik T____"},
        {"lyrics": "Psycho gang, nikdo nás nezastaví", "artist": "Nik Tendo", "song": "Psycho", "hint": "Nik T____"},
        {"lyrics": "Praha city, tady jsem vyrostl", "artist": "Nik Tendo", "song": "Praha", "hint": "Nik T____"},
        # Sergei Barracuda
        {"lyrics": "Začínal jsem dole, teď jsem nahoře", "artist": "Sergei Barracuda", "song": "Nahoře", "hint": "Sergei B_______"},
        {"lyrics": "Každej den hustluju, to je můj život", "artist": "Sergei Barracuda", "song": "Hustle", "hint": "Sergei B_______"},
        {"lyrics": "Rest in peace, vzpomínám na ty co odešli", "artist": "Sergei Barracuda", "song": "RIP", "hint": "Sergei B_______"},
        {"lyrics": "Southside repre, tohle je náš hood", "artist": "Sergei Barracuda", "song": "Southside", "hint": "Sergei B_______"},
        # Hasan
        {"lyrics": "Celej život makám, žádnej oddech", "artist": "Hasan", "song": "Makám", "hint": "H____"},
        {"lyrics": "Ztracený v hudbě, našel jsem se v ní", "artist": "Hasan", "song": "Hudba", "hint": "H____"},
        {"lyrics": "Moje máma pláče, když mě vidí v TV", "artist": "Hasan", "song": "Máma", "hint": "H____"},
        # Lvcas Dope
        {"lyrics": "Dope boys, tohle je naše doba", "artist": "Lvcas Dope", "song": "Dope Boys", "hint": "Lvcas D___"},
        {"lyrics": "Pálím jako oheň, svítím jako slunce", "artist": "Lvcas Dope", "song": "Oheň", "hint": "Lvcas D___"},
        {"lyrics": "Gang gang, celá crew je tu", "artist": "Lvcas Dope", "song": "Gang", "hint": "Lvcas D___"},
        # Yzomandias + others
        {"lyrics": "Nemám rád lidi, radši mám prachy", "artist": "Yzomandias", "song": "Prachy", "hint": "Y_______"},
        {"lyrics": "Trap house, tady se to děje", "artist": "Viktor Sheen", "song": "Trap House", "hint": "Viktor S____"},
        {"lyrics": "Ice na zápěstí, ice na krku", "artist": "Calin", "song": "Ice", "hint": "C____"},
        # Marpo
        {"lyrics": "Troublegang až do konce", "artist": "Marpo", "song": "Troublegang", "hint": "M____"},
        {"lyrics": "Nikdy se nevzdávám, bojuju dál", "artist": "Marpo", "song": "Bojuju", "hint": "M____"},
        {"lyrics": "Legendy nikdy neumírají", "artist": "Marpo", "song": "Legendy", "hint": "M____"},
        # Ben Cristovao
        {"lyrics": "Asio, asio, tancuj se mnou", "artist": "Ben Cristovao", "song": "Asio", "hint": "Ben C________"},
        {"lyrics": "Bomby, bomby padají kolem nás", "artist": "Ben Cristovao", "song": "Bomby", "hint": "Ben C________"},
        # Rest
        {"lyrics": "Pouliční hrdina z betonový džungle", "artist": "Rest", "song": "Hrdina", "hint": "R___"},
        {"lyrics": "Million dolarů v hlavě mám", "artist": "Rest", "song": "Million", "hint": "R___"},
        # Dollar Prync
        {"lyrics": "Balím jeden za druhým, to je ten vibe", "artist": "Dollar Prync", "song": "Vibe", "hint": "Dollar P____"},
        # Refew
        {"lyrics": "Královská hra, jsem na trůnu", "artist": "Refew", "song": "Královská hra", "hint": "R____"},
        {"lyrics": "Padouch s dobrým srdcem", "artist": "Refew", "song": "Padouch", "hint": "R____"},
    ],
    "pop": [
        # Mirai
        {"lyrics": "Holky z naší školky, chtěly by mě zpátky", "artist": "Mirai", "song": "Holky z naší školky", "hint": "M____"},
        {"lyrics": "Na konci dne to bude dobrý", "artist": "Mirai", "song": "Dobrý", "hint": "M____"},
        {"lyrics": "Slunce svítí, svět je krásnej", "artist": "Mirai", "song": "Slunce", "hint": "M____"},
        {"lyrics": "Padám, vstávám, jdu dál", "artist": "Mirai", "song": "Padám", "hint": "M____"},
        {"lyrics": "Když tě vidím, srdce mi buší", "artist": "Mirai", "song": "Srdce", "hint": "M____"},
        {"lyrics": "Celou noc jsem vzhůru, myslím na tebe", "artist": "Mirai", "song": "Celou noc", "hint": "M____"},
        {"lyrics": "Tady a teď, to je ten moment", "artist": "Mirai", "song": "Tady a teď", "hint": "M____"},
        # Slza
        {"lyrics": "Když nemůžeš spát a myslíš na mě", "artist": "Slza", "song": "Když nemůžeš spát", "hint": "S___"},
        {"lyrics": "Máme se rádi, tak proč to kazit", "artist": "Slza", "song": "Máme se rádi", "hint": "S___"},
        {"lyrics": "Věřím na zázraky, věřím na nás", "artist": "Slza", "song": "Zázraky", "hint": "S___"},
        {"lyrics": "Hořím pro tebe, shoř se mnou", "artist": "Slza", "song": "Hořím", "hint": "S___"},
        {"lyrics": "Nebe nad námi je nekonečný", "artist": "Slza", "song": "Nebe", "hint": "S___"},
        {"lyrics": "Dva lidi, jedna duše", "artist": "Slza", "song": "Dva lidi", "hint": "S___"},
        # Pokáč
        {"lyrics": "Půlnoční vlak mě veze domů", "artist": "Pokáč", "song": "Půlnoční", "hint": "P____"},
        {"lyrics": "Tancuj, tancuj, dokud můžeš", "artist": "Pokáč", "song": "Tancuj", "hint": "P____"},
        {"lyrics": "Každý ráno vstávám s úsměvem", "artist": "Pokáč", "song": "Ráno", "hint": "P____"},
        {"lyrics": "Kafe a cigárko, to je moje ráno", "artist": "Pokáč", "song": "Kafe", "hint": "P____"},
        {"lyrics": "Nakupuju v second handu", "artist": "Pokáč", "song": "Second hand", "hint": "P____"},
        {"lyrics": "Láska je jako pizza, nejlepší když je teplá", "artist": "Pokáč", "song": "Pizza", "hint": "P____"},
        # Ewa Farna
        {"lyrics": "Já vím, že ty víš, že já vím", "artist": "Ewa Farna", "song": "Ty víš", "hint": "Ewa F____"},
        {"lyrics": "Nikdy nevíš, co ti život přinese", "artist": "Ewa Farna", "song": "Nevíš", "hint": "Ewa F____"},
        {"lyrics": "Láska je válka, my jsme vojáci", "artist": "Ewa Farna", "song": "Válka", "hint": "Ewa F____"},
        {"lyrics": "Měls mě vůbec rád, nebo to byla jen hra", "artist": "Ewa Farna", "song": "Měls mě rád", "hint": "Ewa F____"},
        {"lyrics": "Ticho, křičím, ale nikdo neslyší", "artist": "Ewa Farna", "song": "Ticho", "hint": "Ewa F____"},
        {"lyrics": "Na ostří nože balancuju", "artist": "Ewa Farna", "song": "Na ostří nože", "hint": "Ewa F____"},
        # Marek Ztracený
        {"lyrics": "Celá léta jsem hledal tu pravou", "artist": "Marek Ztracený", "song": "Léta", "hint": "Marek Z_______"},
        {"lyrics": "Společně až na konec světa", "artist": "Marek Ztracený", "song": "Společně", "hint": "Marek Z_______"},
        {"lyrics": "Dívám se na hvězdy a vidím tě", "artist": "Marek Ztracený", "song": "Hvězdy", "hint": "Marek Z_______"},
        {"lyrics": "Až jednou nebudu, vzpomeň si na mě", "artist": "Marek Ztracený", "song": "Až jednou", "hint": "Marek Z_______"},
        # Aneta Langerová
        {"lyrics": "Voda živá, proudí v mých žilách", "artist": "Aneta Langerová", "song": "Voda živá", "hint": "Aneta L_______"},
        {"lyrics": "Pták v kleci zpívá o svobodě", "artist": "Aneta Langerová", "song": "Pták", "hint": "Aneta L_______"},
        # Tomáš Klus
        {"lyrics": "Já jdu dál a dál, nikdo mě nezastaví", "artist": "Tomáš Klus", "song": "Dál", "hint": "Tomáš K___"},
        {"lyrics": "Do nebe, chci letět do nebe", "artist": "Tomáš Klus", "song": "Do nebe", "hint": "Tomáš K___"},
        {"lyrics": "Ty a já, dva blázni v tomhle světě", "artist": "Tomáš Klus", "song": "Ty a já", "hint": "Tomáš K___"},
        # Thom Artway
        {"lyrics": "Running through the night, looking for the light", "artist": "Thom Artway", "song": "Running", "hint": "Thom A_____"},
        {"lyrics": "I will never let you go", "artist": "Thom Artway", "song": "Never", "hint": "Thom A_____"},
        # Mig 21
        {"lyrics": "Snadné je žít, těžké je být", "artist": "Mig 21", "song": "Snadné", "hint": "Mig __"},
        {"lyrics": "Žiju si svůj život a je mi dobře", "artist": "Mig 21", "song": "Život", "hint": "Mig __"},
        # Lenny
        {"lyrics": "Hell.o, can you hear me calling", "artist": "Lenny", "song": "Hell.o", "hint": "L____"},
        {"lyrics": "Dreaming about you every night", "artist": "Lenny", "song": "Dreaming", "hint": "L____"},
        # Rybičky 48
        {"lyrics": "Pořád ta samá, pořád ta samá", "artist": "Rybičky 48", "song": "Pořád ta samá", "hint": "Rybičky __"},
        {"lyrics": "Adéla, ty jsi moje láska", "artist": "Rybičky 48", "song": "Adéla", "hint": "Rybičky __"},
    ],
    "rock": [
        # Kryštof
        {"lyrics": "Až mě jednou potkáš, budu jinej člověk", "artist": "Kryštof", "song": "Jinej člověk", "hint": "K______"},
        {"lyrics": "Běžím po ulici a nevím kam", "artist": "Kryštof", "song": "Běžím", "hint": "K______"},
        {"lyrics": "Zůstaň se mnou ještě chvíli", "artist": "Kryštof", "song": "Zůstaň", "hint": "K______"},
        {"lyrics": "Dnes ještě ne, zítra možná jo", "artist": "Kryštof", "song": "Zítra", "hint": "K______"},
        {"lyrics": "Ty a já, dvě srdce jedno tělo", "artist": "Kryštof", "song": "Ty a já", "hint": "K______"},
        {"lyrics": "Sněhulák, co taje na slunci", "artist": "Kryštof", "song": "Sněhulák", "hint": "K______"},
        {"lyrics": "Cesta, po které jdu, nemá konce", "artist": "Kryštof", "song": "Cesta", "hint": "K______"},
        # Kabát
        {"lyrics": "Sním svůj sen a nechci se probudit", "artist": "Kabát", "song": "Sním svůj sen", "hint": "K____"},
        {"lyrics": "Máma mi vždycky říkala, ať si dávám pozor", "artist": "Kabát", "song": "Máma", "hint": "K____"},
        {"lyrics": "Malá bílá vrána letí k obloze", "artist": "Kabát", "song": "Bílá vrána", "hint": "K____"},
        {"lyrics": "Kdo nekrade, ten má", "artist": "Kabát", "song": "Kdo nekrade", "hint": "K____"},
        {"lyrics": "Pohoda, všechno je v pohodě", "artist": "Kabát", "song": "Pohoda", "hint": "K____"},
        {"lyrics": "Corrida, corrida, život je corrida", "artist": "Kabát", "song": "Corrida", "hint": "K____"},
        {"lyrics": "Dole v dole v údolí", "artist": "Kabát", "song": "Dole v dole", "hint": "K____"},
        {"lyrics": "Colorado, tam bych chtěl být", "artist": "Kabát", "song": "Colorado", "hint": "K____"},
        # Chinaski
        {"lyrics": "Dívám se na hvězdy a přemýšlím", "artist": "Chinaski", "song": "Hvězdy", "hint": "C______"},
        {"lyrics": "Chci žít svůj život naplno", "artist": "Chinaski", "song": "Naplno", "hint": "C______"},
        {"lyrics": "Cestou na jih, kde slunce zapadá", "artist": "Chinaski", "song": "Na jih", "hint": "C______"},
        {"lyrics": "Rock and roll je mrtvej, ale my hrajem dál", "artist": "Chinaski", "song": "Rock and roll", "hint": "C______"},
        {"lyrics": "Jsi můj nejlepší přítel", "artist": "Chinaski", "song": "Přítel", "hint": "C______"},
        {"lyrics": "Všechno co mám, všechno co chci", "artist": "Chinaski", "song": "Všechno", "hint": "C______"},
        # Lucie
        {"lyrics": "Pojď blíž, pojď blíž ke mně", "artist": "Lucie", "song": "Pojď blíž", "hint": "L____"},
        {"lyrics": "Amerika je daleko, ale sny jsou blízko", "artist": "Lucie", "song": "Amerika", "hint": "L____"},
        {"lyrics": "Černý andělé hlídaj můj sen", "artist": "Lucie", "song": "Černý andělé", "hint": "L____"},
        {"lyrics": "Šum silnice, to je má melodie", "artist": "Lucie", "song": "Šum", "hint": "L____"},
        {"lyrics": "Chci zas v tobě spát", "artist": "Lucie", "song": "Chci zas", "hint": "L____"},
        {"lyrics": "Medvídek, já jsem tvůj medvídek", "artist": "Lucie", "song": "Medvídek", "hint": "L____"},
        # Horkýže Slíže
        {"lyrics": "Vlak, co nikde nestaví", "artist": "Horkýže Slíže", "song": "Vlak", "hint": "Horkýže S____"},
        {"lyrics": "Silné reči, tie nezastavíš", "artist": "Horkýže Slíže", "song": "Silné reči", "hint": "Horkýže S____"},
        # Škwor
        {"lyrics": "Sám proti všem, tak to má být", "artist": "Škwor", "song": "Sám", "hint": "Š____"},
        {"lyrics": "Síla starejch vín", "artist": "Škwor", "song": "Síla", "hint": "Š____"},
        # Divokej Bill
        {"lyrics": "Čmelák, čmelák lítá nad loukou", "artist": "Divokej Bill", "song": "Čmelák", "hint": "Divokej B___"},
        {"lyrics": "Malování, to je moje hra", "artist": "Divokej Bill", "song": "Malování", "hint": "Divokej B___"},
        {"lyrics": "Ring ding dong, to je naše song", "artist": "Divokej Bill", "song": "Ring ding dong", "hint": "Divokej B___"},
        # Wohnout
        {"lyrics": "Svaz českých bohémů, to jsme my", "artist": "Wohnout", "song": "Svaz", "hint": "W______"},
        {"lyrics": "Piju jen když svítí slunce", "artist": "Wohnout", "song": "Piju", "hint": "W______"},
        # Tři sestry
        {"lyrics": "Punk rock rádio hraje celou noc", "artist": "Tři sestry", "song": "Punk rock rádio", "hint": "Tři s_____"},
        {"lyrics": "Alkohol, my ho máme rádi", "artist": "Tři sestry", "song": "Alkohol", "hint": "Tři s_____"},
    ],
    "classic": [
        # Karel Gott
        {"lyrics": "Lady Carneval, tančí dál a dál", "artist": "Karel Gott", "song": "Lady Carneval", "hint": "Karel G___"},
        {"lyrics": "Včelka Mája, ta si létá", "artist": "Karel Gott", "song": "Včelka Mája", "hint": "Karel G___"},
        {"lyrics": "Lásko voníš deštěm", "artist": "Karel Gott", "song": "Lásko", "hint": "Karel G___"},
        {"lyrics": "Když milenky pláčou, pláče celý svět", "artist": "Karel Gott", "song": "Když milenky pláčou", "hint": "Karel G___"},
        {"lyrics": "Okno mé lásky, zavři za sebou", "artist": "Karel Gott", "song": "Okno mé lásky", "hint": "Karel G___"},
        {"lyrics": "Bum bum bum, já mám tě rád", "artist": "Karel Gott", "song": "Bum bum bum", "hint": "Karel G___"},
        {"lyrics": "Být stále mlád, to je můj sen", "artist": "Karel Gott", "song": "Být stále mlád", "hint": "Karel G___"},
        {"lyrics": "Trezor, v něm jsou mé vzpomínky", "artist": "Karel Gott", "song": "Trezor", "hint": "Karel G___"},
        {"lyrics": "Pábitelé, to jsou naši lidi", "artist": "Karel Gott", "song": "Pábitelé", "hint": "Karel G___"},
        {"lyrics": "Čau lásko, už musím jít", "artist": "Karel Gott", "song": "Čau lásko", "hint": "Karel G___"},
        # Waldemar Matuška
        {"lyrics": "Holubí dům, tam kde jsem doma", "artist": "Waldemar Matuška", "song": "Holubí dům", "hint": "Waldemar M______"},
        {"lyrics": "Rosa na kolejích, vlak co nejede", "artist": "Waldemar Matuška", "song": "Rosa na kolejích", "hint": "Waldemar M______"},
        {"lyrics": "Pod tou naší starou lípou", "artist": "Waldemar Matuška", "song": "Pod lípou", "hint": "Waldemar M______"},
        {"lyrics": "Tisíc mil, to je cesta domů", "artist": "Waldemar Matuška", "song": "Tisíc mil", "hint": "Waldemar M______"},
        # Ivan Mládek
        {"lyrics": "Jožin z bažin měří přes dva metry", "artist": "Ivan Mládek", "song": "Jožin z bažin", "hint": "Ivan M_____"},
        {"lyrics": "Koukej, támhle finišuje báječnej chlap", "artist": "Ivan Mládek", "song": "Báječnej chlap", "hint": "Ivan M_____"},
        {"lyrics": "Mě to tady nebaví, já chci domů", "artist": "Ivan Mládek", "song": "Mě to nebaví", "hint": "Ivan M_____"},
        {"lyrics": "Nashledanou v lepších časech", "artist": "Ivan Mládek", "song": "Nashledanou", "hint": "Ivan M_____"},
        # Marta Kubišová
        {"lyrics": "Být stále mlád, to není žádnej věk", "artist": "Marta Kubišová", "song": "Být stále mlád", "hint": "Marta K______"},
        {"lyrics": "Modlitba pro Martu, ať žije dál", "artist": "Marta Kubišová", "song": "Modlitba pro Martu", "hint": "Marta K______"},
        {"lyrics": "Nechte zvony znít, nechte je znít", "artist": "Marta Kubišová", "song": "Zvony", "hint": "Marta K______"},
        # Olympic
        {"lyrics": "Těžkej den, všechno je špatně", "artist": "Olympic", "song": "Těžkej den", "hint": "O______"},
        {"lyrics": "Dej mi víc své lásky", "artist": "Olympic", "song": "Dej mi víc", "hint": "O______"},
        {"lyrics": "Jasná zpráva, to je ta co čekám", "artist": "Olympic", "song": "Jasná zpráva", "hint": "O______"},
        {"lyrics": "Želva, ta se nikam nespěchá", "artist": "Olympic", "song": "Želva", "hint": "O______"},
        # Karel Kryl
        {"lyrics": "Pane prezidente, kam to jdete", "artist": "Karel Kryl", "song": "Pane prezidente", "hint": "Karel K___"},
        {"lyrics": "Bratříčku zavírej vrátka", "artist": "Karel Kryl", "song": "Bratříčku", "hint": "Karel K___"},
        {"lyrics": "Anděl, co spadl z nebe", "artist": "Karel Kryl", "song": "Anděl", "hint": "Karel K___"},
        {"lyrics": "Slib, co jsem ti dal, platí pořád", "artist": "Karel Kryl", "song": "Slib", "hint": "Karel K___"},
        # Hana Zagorová
        {"lyrics": "Já nemám strach, já jdu dál", "artist": "Hana Zagorová", "song": "Nemám strach", "hint": "Hana Z_______"},
        {"lyrics": "Mimořádná linka lásky", "artist": "Hana Zagorová", "song": "Linka lásky", "hint": "Hana Z_______"},
        {"lyrics": "Maluj zase obrázky", "artist": "Hana Zagorová", "song": "Obrázky", "hint": "Hana Z_______"},
        # Helena Vondráčková
        {"lyrics": "Dlouhá noc, tak dlouhá noc", "artist": "Helena Vondráčková", "song": "Dlouhá noc", "hint": "Helena V________"},
        {"lyrics": "Přejdi Jordán a vrať se domů", "artist": "Helena Vondráčková", "song": "Jordán", "hint": "Helena V________"},
        {"lyrics": "Lásko má, já stůňu", "artist": "Helena Vondráčková", "song": "Lásko má", "hint": "Helena V________"},
        # Michal David
        {"lyrics": "Nonstop, tancujem nonstop", "artist": "Michal David", "song": "Nonstop", "hint": "Michal D____"},
        {"lyrics": "Discopříběh, to je naše doba", "artist": "Michal David", "song": "Discopříběh", "hint": "Michal D____"},
        {"lyrics": "Céčka, béčka, áčka, jedéééééém", "artist": "Michal David", "song": "Céčka", "hint": "Michal D____"},
        # Jaromír Nohavica
        {"lyrics": "Těšínská, tam kde je můj domov", "artist": "Jaromír Nohavica", "song": "Těšínská", "hint": "Jaromír N_______"},
        {"lyrics": "Mikymauz, to je starej známej", "artist": "Jaromír Nohavica", "song": "Mikymauz", "hint": "Jaromír N_______"},
        {"lyrics": "Ladovská zima, bílá a čistá", "artist": "Jaromír Nohavica", "song": "Ladovská zima", "hint": "Jaromír N_______"},
        {"lyrics": "Kometa, letí kometa oblohou", "artist": "Jaromír Nohavica", "song": "Kometa", "hint": "Jaromír N_______"},
    ]
}


# Active music quizzes
active_music_quiz = {}

# Quiz settings per guild
quiz_settings = {}  # {guild_id: {"time": 60}}
DEFAULT_QUIZ_TIME = 60  # 1 minuta

def normalize_answer(text: str) -> str:
    """Normalize text for comparison - remove accents, lowercase"""
    text = text.lower().strip()
    replacements = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i',
        'ň': 'n', 'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u',
        'ů': 'u', 'ý': 'y', 'ž': 'z'
    }
    for cz, en in replacements.items():
        text = text.replace(cz, en)
    return text

def get_quiz_time(guild_id: int) -> int:
    """Get quiz time for guild"""
    return quiz_settings.get(guild_id, {}).get("time", DEFAULT_QUIZ_TIME)

def get_quiz_rounds(guild_id: int) -> int:
    """Get number of quiz rounds for guild"""
    return quiz_settings.get(guild_id, {}).get("rounds", 5)

@bot.tree.command(name="hudba-nastaveni", description="Nastav hudební kvíz (pouze admin)")
@app_commands.describe(
    sekundy="Čas na odpověď v sekundách (30-300)",
    pocet="Počet otázek v kvízu (1-20)"
)
@app_commands.default_permissions(administrator=True)
async def slash_hudba_settings(interaction: discord.Interaction, sekundy: int = None, pocet: int = None):
    guild_id = interaction.guild_id
    if guild_id not in quiz_settings:
        quiz_settings[guild_id] = {}
    
    changes = []
    
    if sekundy is not None:
        if sekundy < 30 or sekundy > 300:
            await interaction.response.send_message("❌ Čas musí být mezi 30 a 300 sekundami!", ephemeral=True)
            return
        quiz_settings[guild_id]["time"] = sekundy
        changes.append(f"⏰ Čas: **{sekundy}s**")
    
    if pocet is not None:
        if pocet < 1 or pocet > 20:
            await interaction.response.send_message("❌ Počet otázek musí být mezi 1 a 20!", ephemeral=True)
            return
        quiz_settings[guild_id]["rounds"] = pocet
        changes.append(f"🔢 Počet otázek: **{pocet}**")
    
    if not changes:
        current_time = get_quiz_time(guild_id)
        current_rounds = get_quiz_rounds(guild_id)
        await interaction.response.send_message(
            f"📊 **Aktuální nastavení:**\n⏰ Čas: {current_time}s\n🔢 Počet otázek: {current_rounds}",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message(f"✅ Nastavení uloženo!\n" + "\n".join(changes))

@bot.tree.command(name="hudba", description="Spusť hudební kvíz - hádej písničku!")
@app_commands.describe(zanr="Vyber žánr hudby")
@app_commands.choices(zanr=[
    app_commands.Choice(name="🎤 Rap", value="rap"),
    app_commands.Choice(name="🎵 Pop", value="pop"),
    app_commands.Choice(name="🎸 Rock", value="rock"),
    app_commands.Choice(name="🎺 Klasika", value="classic"),
    app_commands.Choice(name="🎲 Náhodný", value="random"),
])
async def slash_hudba(interaction: discord.Interaction, zanr: str = "random"):
    # Check permission from database
    if not await check_command_permission(interaction, "hudba"):
        return
    
    channel_id = interaction.channel_id
    guild_id = interaction.guild_id
    
    # Check if quiz already active
    if channel_id in active_music_quiz and active_music_quiz[channel_id].get("active"):
        await interaction.response.send_message("❌ V tomto kanálu už běží kvíz! Počkej až skončí.", ephemeral=True)
        return
    
    quiz_time = get_quiz_time(guild_id)
    total_rounds = get_quiz_rounds(guild_id)
    
    # Initialize quiz session
    active_music_quiz[channel_id] = {
        "active": True,
        "genre": zanr,
        "current_round": 0,
        "total_rounds": total_rounds,
        "scores": {},  # {user_id: {"name": name, "score": score}}
        "current_question": None,
        "answered": False,
        "quiz_time": quiz_time,
        "guild_id": guild_id
    }
    
    # Send start message
    embed = discord.Embed(
        title="🎵 HUDEBNÍ KVÍZ ZAČÍNÁ!",
        description=f"**{total_rounds} otázek** | **{quiz_time}s na odpověď**",
        color=discord.Color.purple()
    )
    embed.add_field(name="🎸 Žánr", value=zanr.upper() if zanr != "random" else "NÁHODNÝ", inline=True)
    embed.add_field(name="📝 Pravidla", value="Napiš jméno interpreta do chatu!", inline=False)
    embed.set_footer(text="První otázka za 3 sekundy...")
    
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(3)
    
    # Start quiz rounds
    await run_music_quiz(interaction.channel, channel_id)

async def run_music_quiz(channel, channel_id: int):
    """Run multiple rounds of music quiz"""
    import random
    
    quiz_data = active_music_quiz.get(channel_id)
    if not quiz_data:
        return
    
    genre = quiz_data["genre"]
    total_rounds = quiz_data["total_rounds"]
    quiz_time = quiz_data["quiz_time"]
    genre_names = {"rap": "🎤 Rap", "pop": "🎵 Pop", "rock": "🎸 Rock", "classic": "🎺 Klasika"}
    
    for round_num in range(1, total_rounds + 1):
        if channel_id not in active_music_quiz:
            return  # Quiz was stopped
        
        quiz_data = active_music_quiz[channel_id]
        quiz_data["current_round"] = round_num
        quiz_data["answered"] = False
        
        # Select genre for this round
        current_genre = genre if genre != "random" else random.choice(list(CZECH_MUSIC.keys()))
        
        # Select random song
        song_data = random.choice(CZECH_MUSIC[current_genre])
        
        quiz_data["current_question"] = {
            "artist": song_data["artist"],
            "song": song_data["song"],
            "hint": song_data["hint"]
        }
        
        # Send question
        embed = discord.Embed(
            title=f"🎵 OTÁZKA {round_num}/{total_rounds}",
            description=f"**Hádej interpreta!**",
            color=discord.Color.purple()
        )
        embed.add_field(name="🎼 Text písně", value=f"*\"{song_data['lyrics']}\"*", inline=False)
        embed.add_field(name="💡 Nápověda", value=f"`{song_data['hint']}`", inline=True)
        embed.add_field(name="🎸 Žánr", value=genre_names.get(current_genre, current_genre), inline=True)
        embed.add_field(name="⏰ Čas", value=f"{quiz_time}s", inline=True)
        
        await channel.send(embed=embed)
        
        # Wait for answer or timeout - check every 0.5 seconds
        elapsed = 0
        while elapsed < quiz_time:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            
            # Check if quiz still exists and if answered
            quiz_data = active_music_quiz.get(channel_id)
            if not quiz_data:
                return
            if quiz_data.get("answered"):
                break  # Someone answered, move to next question
        
        # Check if answered
        quiz_data = active_music_quiz.get(channel_id)
        if not quiz_data:
            return
        
        if not quiz_data["answered"]:
            embed = discord.Embed(
                title="⏰ ČAS VYPRŠEL!",
                description=f"Správná odpověď: **{song_data['artist']}** - {song_data['song']}",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
        
        # Pause between rounds
        if round_num < total_rounds:
            await channel.send(f"⏳ **Další otázka za 3 sekundy...**")
            await asyncio.sleep(3)
    
    # Quiz finished - show final scores
    quiz_data = active_music_quiz.get(channel_id)
    if quiz_data:
        scores = quiz_data.get("scores", {})
        
        if scores:
            # Sort by score
            sorted_scores = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
            
            medals = ["🥇", "🥈", "🥉"]
            leaderboard = ""
            for i, (user_id, data) in enumerate(sorted_scores[:10]):
                medal = medals[i] if i < 3 else f"**{i+1}.**"
                leaderboard += f"{medal} {data['name']} - **{data['score']} bodů**\n"
            
            embed = discord.Embed(
                title="🏆 KVÍZ DOKONČEN!",
                description=f"**Výsledky z {total_rounds} otázek:**",
                color=discord.Color.gold()
            )
            embed.add_field(name="📊 Žebříček", value=leaderboard or "Nikdo neskóroval", inline=False)
            
            if sorted_scores:
                winner_id, winner_data = sorted_scores[0]
                embed.add_field(name="👑 Vítěz", value=f"**{winner_data['name']}** s {winner_data['score']} body!", inline=False)
        else:
            embed = discord.Embed(
                title="🏆 KVÍZ DOKONČEN!",
                description="Nikdo neuhodl žádnou otázku!",
                color=discord.Color.orange()
            )
        
        await channel.send(embed=embed)
        
        # Cleanup
        if channel_id in active_music_quiz:
            del active_music_quiz[channel_id]

@bot.command(name="hudba", aliases=["music", "hz"])
@commands.has_permissions(administrator=True)
async def prefix_hudba(ctx, zanr: str = "random"):
    """!hudba [rap/pop/rock/classic/random] - Hudební kvíz (Admin)"""
    channel_id = ctx.channel.id
    guild_id = ctx.guild.id
    
    if channel_id in active_music_quiz and active_music_quiz[channel_id].get("active"):
        await ctx.send("❌ V tomto kanálu už běží kvíz!")
        return
    
    # Validate genre
    if zanr not in ["rap", "pop", "rock", "classic", "random"]:
        zanr = "random"
    
    quiz_time = get_quiz_time(guild_id)
    total_rounds = get_quiz_rounds(guild_id)
    
    active_music_quiz[channel_id] = {
        "active": True,
        "genre": zanr,
        "current_round": 0,
        "total_rounds": total_rounds,
        "scores": {},
        "current_question": None,
        "answered": False,
        "quiz_time": quiz_time,
        "guild_id": guild_id
    }
    
    embed = discord.Embed(
        title="🎵 HUDEBNÍ KVÍZ ZAČÍNÁ!",
        description=f"**{total_rounds} otázek** | **{quiz_time}s na odpověď**",
        color=discord.Color.purple()
    )
    embed.add_field(name="🎸 Žánr", value=zanr.upper() if zanr != "random" else "NÁHODNÝ", inline=True)
    embed.add_field(name="📝 Pravidla", value="Napiš jméno interpreta do chatu!", inline=False)
    embed.set_footer(text="První otázka za 3 sekundy...")
    
    await ctx.send(embed=embed)
    await asyncio.sleep(3)
    
    await run_music_quiz(ctx.channel, channel_id)

# ============== FILM QUIZ ==============

FILM_DATABASE = {
    "ceske": [
        # Pelíšky
        {"quote": "Nechte zvířátka žít!", "film": "Pelíšky", "year": "1999", "hint": "P______"},
        {"quote": "Koho chleba jíš, toho píseň zpívej", "film": "Pelíšky", "year": "1999", "hint": "P______"},
        {"quote": "A hele, támhle leze hroch!", "film": "Pelíšky", "year": "1999", "hint": "P______"},
        {"quote": "Já mám rád demokracii!", "film": "Pelíšky", "year": "1999", "hint": "P______"},
        {"quote": "Takhle vypadá česká klasika!", "film": "Pelíšky", "year": "1999", "hint": "P______"},
        # Samotáři
        {"quote": "Ty vole, to je bomba!", "film": "Samotáři", "year": "2000", "hint": "S_______"},
        {"quote": "Láska je jako voda, musí téct", "film": "Samotáři", "year": "2000", "hint": "S_______"},
        {"quote": "Prostě blbá nálada, to je celý", "film": "Samotáři", "year": "2000", "hint": "S_______"},
        {"quote": "Život je pes a pak umřeš", "film": "Samotáři", "year": "2000", "hint": "S_______"},
        # Vratné lahve
        {"quote": "Víš co, tak já půjdu...", "film": "Vratné lahve", "year": "2007", "hint": "Vratné l____"},
        {"quote": "Člověk musí mít v životě štěstí", "film": "Vratné lahve", "year": "2007", "hint": "Vratné l____"},
        # Kolja
        {"quote": "To je ale kravina!", "film": "Kolja", "year": "1996", "hint": "K____"},
        {"quote": "Malej, pojď sem!", "film": "Kolja", "year": "1996", "hint": "K____"},
        {"quote": "Rusáci, to jsou svině", "film": "Kolja", "year": "1996", "hint": "K____"},
        # Obecná škola
        {"quote": "Děti, co byste chtěli k večeři?", "film": "Obecná škola", "year": "1991", "hint": "Obecná š____"},
        {"quote": "Dneska máme volno!", "film": "Obecná škola", "year": "1991", "hint": "Obecná š____"},
        # Vesničko má středisková
        {"quote": "Kubo, co to děláš?", "film": "Vesničko má středisková", "year": "1985", "hint": "Vesničko má s__________"},
        {"quote": "Pane předsedo, to nejde!", "film": "Vesničko má středisková", "year": "1985", "hint": "Vesničko má s__________"},
        {"quote": "Soudruhu, to je omyl!", "film": "Vesničko má středisková", "year": "1985", "hint": "Vesničko má s__________"},
        # Marečku, podejte mi pero
        {"quote": "Marečku, podejte mi pero!", "film": "Marečku, podejte mi pero", "year": "1976", "hint": "Marečku, p_____"},
        {"quote": "Kdo se směje naposled, ten se směje nejlíp", "film": "Marečku, podejte mi pero", "year": "1976", "hint": "Marečku, p_____"},
        {"quote": "To je síla, pane kolego!", "film": "Marečku, podejte mi pero", "year": "1976", "hint": "Marečku, p_____"},
        # Na samotě u lesa
        {"quote": "Láďo, co to děláš?", "film": "Na samotě u lesa", "year": "1976", "hint": "Na samotě u l___"},
        {"quote": "Takhle se chová slušnej člověk!", "film": "Na samotě u lesa", "year": "1976", "hint": "Na samotě u l___"},
        # S tebou mě baví svět
        {"quote": "Hele, támhle je pramen!", "film": "S tebou mě baví svět", "year": "1982", "hint": "S tebou mě b___ s___"},
        {"quote": "To je ale výlet!", "film": "S tebou mě baví svět", "year": "1982", "hint": "S tebou mě b___ s___"},
        # Slunce, seno
        {"quote": "Ty jsi ale kráva!", "film": "Slunce, seno, jahody", "year": "1983", "hint": "Slunce, seno, j_____"},
        {"quote": "Konečně prázdniny!", "film": "Slunce, seno, jahody", "year": "1983", "hint": "Slunce, seno, j_____"},
        {"quote": "To je ale vedro!", "film": "Slunce, seno, jahody", "year": "1983", "hint": "Slunce, seno, j_____"},
        # Bílá paní
        {"quote": "Pane purkmistr, ona mluví!", "film": "Bílá paní", "year": "1965", "hint": "Bílá p___"},
        # Limonádový Joe
        {"quote": "Piju jen limonádu!", "film": "Limonádový Joe", "year": "1964", "hint": "Limonádový J__"},
        {"quote": "Kolaloka zabíjí!", "film": "Limonádový Joe", "year": "1964", "hint": "Limonádový J__"},
        # Jáchyme, hoď ho do stroje
        {"quote": "Jáchyme, hoď ho do stroje!", "film": "Jáchyme, hoď ho do stroje", "year": "1974", "hint": "Jáchyme, h__ h_ d_ s_____"},
        {"quote": "Soudruhu řediteli!", "film": "Jáchyme, hoď ho do stroje", "year": "1974", "hint": "Jáchyme, h__ h_ d_ s_____"},
        # Kameňák
        {"quote": "Hele, támhle letí ptáček!", "film": "Kameňák", "year": "2003", "hint": "K______"},
        {"quote": "To je ale trapas!", "film": "Kameňák", "year": "2003", "hint": "K______"},
        # Další české filmy
        {"quote": "Život je boj a já jsem bojovník", "film": "Román pro ženy", "year": "2005", "hint": "Román pro ž___"},
        {"quote": "Tak co, holky, jdeme na to?", "film": "Účastníci zájezdu", "year": "2006", "hint": "Účastníci z______"},
        {"quote": "Musíš se na to dívat z nadhledu", "film": "Pupendo", "year": "2003", "hint": "P______"},
        {"quote": "Já jsem ten, kdo klepe!", "film": "Tmavomodrý svět", "year": "2001", "hint": "Tmavomodrý s___"},
        {"quote": "Země je kulatá a já jsem její střed", "film": "Želary", "year": "2003", "hint": "Ž_____"},
        {"quote": "Nemám čas na kecy, musím pracovat", "film": "Babovřesky", "year": "2013", "hint": "B________"},
        {"quote": "To je ale blbost, že jo?", "film": "Snowboarďáci", "year": "2004", "hint": "S__________"},
        {"quote": "Všechno bude dobrý, uvidíš", "film": "Horem pádem", "year": "2004", "hint": "Horem p____"},
        {"quote": "To je moje holka!", "film": "Musíme si pomáhat", "year": "2000", "hint": "Musíme si p______"},
        {"quote": "Nikdy neříkej nikdy", "film": "Grandhotel", "year": "2006", "hint": "G________"},
        {"quote": "Hele, támhle je Ježíšek!", "film": "Anděl Páně", "year": "2005", "hint": "Anděl P___"},
        {"quote": "Petroníle, co to děláš?", "film": "Anděl Páně", "year": "2005", "hint": "Anděl P___"},
        {"quote": "Uriáši, pozor!", "film": "Anděl Páně", "year": "2005", "hint": "Anděl P___"},
        {"quote": "Peklo je prázdné!", "film": "Anděl Páně 2", "year": "2016", "hint": "Anděl P___ _"},
        {"quote": "Já jsem princ!", "film": "Tři oříšky pro Popelku", "year": "1973", "hint": "Tři oříšky pro P______"},
        {"quote": "Popelko, kde jsi?", "film": "Tři oříšky pro Popelku", "year": "1973", "hint": "Tři oříšky pro P______"},
        {"quote": "Král je nahý!", "film": "Císařův pekař", "year": "1951", "hint": "Císařův p____"},
        {"quote": "To je ale voňavka!", "film": "Dívka na koštěti", "year": "1972", "hint": "Dívka na k______"},
    ],
    "hollywood": [
        {"quote": "Já se vrátím", "film": "Terminátor", "year": "1984", "hint": "T________"},
        {"quote": "Ať tě provází Síla", "film": "Star Wars", "year": "1977", "hint": "Star W___"},
        {"quote": "Na tebe se dívám, zlatíčko", "film": "Casablanca", "year": "1942", "hint": "C_________"},
        {"quote": "Na mě mluvíš?", "film": "Taxikář", "year": "1976", "hint": "T______"},
        {"quote": "Udělám mu nabídku, kterou nemůže odmítnout", "film": "Kmotr", "year": "1972", "hint": "K____"},
        {"quote": "Život je jako bonboniéra, nikdy nevíš co ochutnáš", "film": "Forrest Gump", "year": "1994", "hint": "Forrest G___"},
        {"quote": "Vidím mrtvé lidi", "film": "Šestý smysl", "year": "1999", "hint": "Šestý s____"},
        {"quote": "Pravdu neuneseš!", "film": "Pár správných chlapů", "year": "1992", "hint": "Pár správných c_____"},
        {"quote": "Není nad domov", "film": "Čaroděj ze země Oz", "year": "1939", "hint": "Čaroděj ze z___ O_"},
        {"quote": "Proč tak vážně?", "film": "Temný rytíř", "year": "2008", "hint": "Temný r_____"},
        {"quote": "Já jsem tvůj otec", "film": "Star Wars", "year": "1980", "hint": "Star W___"},
        {"quote": "Prostě plav dál", "film": "Hledá se Nemo", "year": "2003", "hint": "Hledá se N___"},
        {"quote": "Do nekonečna a ještě dál!", "film": "Toy Story", "year": "1995", "hint": "Toy S____"},
        {"quote": "Jsem král světa!", "film": "Titanic", "year": "1997", "hint": "T______"},
        {"quote": "Neprojdeš!", "film": "Pán prstenů", "year": "2001", "hint": "Pán p_______"},
        {"quote": "Můj miláček", "film": "Pán prstenů", "year": "2001", "hint": "Pán p_______"},
        {"quote": "Tady je Johnny!", "film": "Osvícení", "year": "1980", "hint": "O_______"},
        {"quote": "Nikdy tě nepustím, Jacku", "film": "Titanic", "year": "1997", "hint": "T______"},
        {"quote": "S velkou mocí přichází velká zodpovědnost", "film": "Spider-Man", "year": "2002", "hint": "Spider-M__"},
        {"quote": "Já jsem Iron Man", "film": "Iron Man", "year": "2008", "hint": "Iron M__"},
        {"quote": "Avengers, spojte se!", "film": "Avengers: Endgame", "year": "2019", "hint": "Avengers: E______"},
        {"quote": "Já jsem Groot", "film": "Strážci galaxie", "year": "2014", "hint": "Strážci g______"},
        {"quote": "Hakuna Matata - žádné starosti", "film": "Lví král", "year": "1994", "hint": "Lví k___"},
        {"quote": "Pusť to, nech to být!", "film": "Ledové království", "year": "2013", "hint": "Ledové k________"},
        {"quote": "Houstone, máme problém", "film": "Apollo 13", "year": "1995", "hint": "Apollo __"},
        {"quote": "Pozdrav mého malého kámoše!", "film": "Zjizvená tvář", "year": "1983", "hint": "Zjizvená t___"},
        {"quote": "Měl jsi mě už při ahoj", "film": "Jerry Maguire", "year": "1996", "hint": "Jerry M______"},
        {"quote": "Baby nikdo nestrčí do kouta", "film": "Hříšný tanec", "year": "1987", "hint": "Hříšný t____"},
        {"quote": "Cítím potřebu... potřebu rychlosti", "film": "Top Gun", "year": "1986", "hint": "Top G__"},
        # Nové Hollywood filmy
        {"quote": "Běž za svým snem", "film": "La La Land", "year": "2016", "hint": "La La L___"},
        {"quote": "Jmenuji se Bond. James Bond.", "film": "James Bond", "year": "1962", "hint": "James B___"},
        {"quote": "Protřepat, nemíchat", "film": "James Bond", "year": "1962", "hint": "James B___"},
        {"quote": "Franku, já ti to vrátím!", "film": "Rocky", "year": "1976", "hint": "R____"},
        {"quote": "Adriano!", "film": "Rocky", "year": "1976", "hint": "R____"},
        {"quote": "Jsi mi kamarád, příteli", "film": "Gladiátor", "year": "2000", "hint": "G_______"},
        {"quote": "Na moje znamení, rozpoutej peklo", "film": "Gladiátor", "year": "2000", "hint": "G_______"},
        {"quote": "Jsem Maximus Decimus Meridius", "film": "Gladiátor", "year": "2000", "hint": "G_______"},
        {"quote": "Jmenuji se Inigo Montoya", "film": "Princezna nevěsta", "year": "1987", "hint": "Princezna n______"},
        {"quote": "Jak si přeješ", "film": "Princezna nevěsta", "year": "1987", "hint": "Princezna n______"},
        {"quote": "Dneska je dobrý den umřít", "film": "Independence Day", "year": "1996", "hint": "Independence D__"},
        {"quote": "Vítejte na Zemi!", "film": "Independence Day", "year": "1996", "hint": "Independence D__"},
        {"quote": "Co je v krabici?!", "film": "Sedm", "year": "1995", "hint": "S____"},
        {"quote": "Pamatuješ si první pravidlo?", "film": "Klub rváčů", "year": "1999", "hint": "Klub r_____"},
        {"quote": "O Klubu rváčů se nemluví", "film": "Klub rváčů", "year": "1999", "hint": "Klub r_____"},
        {"quote": "Za svůj život jsem udělal tisíc chyb", "film": "Vykoupení z věznice Shawshank", "year": "1994", "hint": "Vykoupení z v______"},
        {"quote": "Buď zaneprázdněný životem, nebo umíráním", "film": "Vykoupení z věznice Shawshank", "year": "1994", "hint": "Vykoupení z v______"},
        {"quote": "Země se otočila", "film": "Počátek", "year": "2010", "hint": "P______"},
        {"quote": "Musíme jít hlouběji", "film": "Počátek", "year": "2010", "hint": "P______"},
        {"quote": "Nebudu ti lhát, jsou to vetřelci", "film": "Vetřelec", "year": "1979", "hint": "V______"},
        {"quote": "Ve vesmíru tě nikdo neslyší křičet", "film": "Vetřelec", "year": "1979", "hint": "V______"},
        {"quote": "Vzhůru do neznáma!", "film": "Vzhůru do oblak", "year": "2009", "hint": "Vzhůru do o_____"},
        {"quote": "Jsem legenda", "film": "Jsem legenda", "year": "2007", "hint": "Jsem l_____"},
        {"quote": "Zachraň vojína Ryana!", "film": "Zachraňte vojína Ryana", "year": "1998", "hint": "Zachraňte v_____ R____"},
        {"quote": "Zasloužíš si to", "film": "Zachraňte vojína Ryana", "year": "1998", "hint": "Zachraňte v_____ R____"},
    ],
    "komedie": [
        {"quote": "To ona řekla", "film": "The Office", "year": "2005", "hint": "The O_____"},
        {"quote": "Jsem docela velké zvíře", "film": "Zprávař", "year": "2004", "hint": "Z______"},
        {"quote": "Ty mě zabíjíš, člověče!", "film": "Sandlot", "year": "1993", "hint": "S______"},
        {"quote": "Dneska tu vůbec nemám být", "film": "Baráčníci", "year": "1994", "hint": "B________"},
        {"quote": "Ale jo, zlato, ale jo!", "film": "Austin Powers", "year": "1997", "hint": "Austin P_____"},
        {"quote": "Tak jo, fajn!", "film": "Ace Ventura", "year": "1994", "hint": "Ace V______"},
        {"quote": "Takže říkáš, že mám šanci?", "film": "Blbý a blbější", "year": "1994", "hint": "Blbý a b______"},
        {"quote": "Dám si to co ona", "film": "Když Harry potkal Sally", "year": "1989", "hint": "Když Harry p_____ S____"},
        {"quote": "To není nádor!", "film": "Policajt ve školce", "year": "1990", "hint": "Policajt ve š_____"},
        {"quote": "Jsem ve skleněné kleci emocí!", "film": "Zprávař", "year": "2004", "hint": "Z______"},
        {"quote": "Sedíš na trůnu lží", "film": "Vánoce po americku", "year": "2003", "hint": "Vánoce po a_______"},
        {"quote": "Já jsem Batman", "film": "Lego Batman", "year": "2017", "hint": "Lego B_____"},
        {"quote": "Osel!", "film": "Shrek", "year": "2001", "hint": "S____"},
        {"quote": "Vrstvy! Zlobři mají vrstvy!", "film": "Shrek", "year": "2001", "hint": "S____"},
        {"quote": "Jsme tam už?", "film": "Shrek", "year": "2001", "hint": "S____"},
        # Nové komedie
        {"quote": "Já ti věřím, člověče", "film": "Big Lebowski", "year": "1998", "hint": "Big L_______"},
        {"quote": "To je tvůj názor, člověče", "film": "Big Lebowski", "year": "1998", "hint": "Big L_______"},
        {"quote": "Koberec opravdu spojil místnost", "film": "Big Lebowski", "year": "1998", "hint": "Big L_______"},
        {"quote": "Bude to legendární!", "film": "Jak jsem poznal vaši matku", "year": "2005", "hint": "Jak jsem p_____ v___ m____"},
        {"quote": "Co se stane ve Vegas, zůstane ve Vegas", "film": "Pařba ve Vegas", "year": "2009", "hint": "Pařba ve V____"},
        {"quote": "Kde je tygr?", "film": "Pařba ve Vegas", "year": "2009", "hint": "Pařba ve V____"},
        {"quote": "Jeden z nás se oženil?!", "film": "Pařba ve Vegas", "year": "2009", "hint": "Pařba ve V____"},
        {"quote": "Čau, já jsem Andy", "film": "40 let panic", "year": "2005", "hint": "40 let p____"},
        {"quote": "Nechci být sám celý život", "film": "40 let panic", "year": "2005", "hint": "40 let p____"},
        {"quote": "Mluvíš se mnou?", "film": "Méďa", "year": "2012", "hint": "M___"},
        {"quote": "Hrom do police!", "film": "Méďa", "year": "2012", "hint": "M___"},
        {"quote": "Jsem příliš sexy pro tohle auto", "film": "Zoolander", "year": "2001", "hint": "Z________"},
        {"quote": "Tenhle pohled se jmenuje Modrá ocel", "film": "Zoolander", "year": "2001", "hint": "Z________"},
        {"quote": "Je to past!", "film": "Borat", "year": "2006", "hint": "B____"},
        {"quote": "Moc hezky!", "film": "Borat", "year": "2006", "hint": "B____"},
        {"quote": "Jsem Ron Burgundy?", "film": "Zprávař", "year": "2004", "hint": "Z______"},
        {"quote": "60% času to funguje pokaždé", "film": "Zprávař", "year": "2004", "hint": "Z______"},
        {"quote": "Dej mi mého syna!", "film": "Pěsti z oken", "year": "2000", "hint": "Pěsti z o___"},
        {"quote": "Jsem v tom až po uši", "film": "Notting Hill", "year": "1999", "hint": "Notting H___"},
        {"quote": "Jsem jen holka, co stojí před klukem", "film": "Notting Hill", "year": "1999", "hint": "Notting H___"},
        {"quote": "Nemám rád pondělky", "film": "Garfield", "year": "2004", "hint": "G______"},
        {"quote": "Kde je lasagne?", "film": "Garfield", "year": "2004", "hint": "G______"},
    ],
    "akcni": [
        {"quote": "Šťastné a veselé, kamaráde", "film": "Smrtonosná past", "year": "1988", "hint": "Smrtonosná p___"},
        {"quote": "K vrtulníku!", "film": "Predátor", "year": "1987", "hint": "P_______"},
        {"quote": "Já se vrátím", "film": "Terminátor 2", "year": "1991", "hint": "Terminátor _"},
        {"quote": "Hasta la vista, kámo", "film": "Terminátor 2", "year": "1991", "hint": "Terminátor _"},
        {"quote": "Vítej na večírku, kámo!", "film": "Smrtonosná past", "year": "1988", "hint": "Smrtonosná p___"},
        {"quote": "Já jsem zákon!", "film": "Soudce Dredd", "year": "1995", "hint": "Soudce D____"},
        {"quote": "Je čas na show!", "film": "Beetlejuice", "year": "1988", "hint": "B__________"},
        {"quote": "Žiju svůj život čtvrt míle za čtvrt míle", "film": "Rychle a zběsile", "year": "2001", "hint": "Rychle a z______"},
        {"quote": "Do Mordoru se jen tak nevejde", "film": "Pán prstenů", "year": "2001", "hint": "Pán p_______"},
        {"quote": "Tohle můžu dělat celý den", "film": "Captain America", "year": "2011", "hint": "Captain A______"},
        {"quote": "Wakanda navždy!", "film": "Black Panther", "year": "2018", "hint": "Black P______"},
        {"quote": "Jsem pořád naštvaný", "film": "Avengers", "year": "2012", "hint": "A_______"},
        {"quote": "My jsme Groot", "film": "Strážci galaxie", "year": "2014", "hint": "Strážci g______"},
        {"quote": "Nezáleží na tom kdo jsem, ale co dělám", "film": "Batman začíná", "year": "2005", "hint": "Batman z_____"},
        {"quote": "Nejsem tady zavřený s vámi, vy jste zavření se mnou", "film": "Watchmen", "year": "2009", "hint": "W_______"},
        # Nové akční filmy
        {"quote": "Rodina je všechno", "film": "Rychle a zběsile", "year": "2001", "hint": "Rychle a z______"},
        {"quote": "Jedna poslední jízda", "film": "Rychle a zběsile 7", "year": "2015", "hint": "Rychle a z______ _"},
        {"quote": "Nevyjednávám s teroristy", "film": "Smrtonosná past 2", "year": "1990", "hint": "Smrtonosná p___ _"},
        {"quote": "Jmenuju se John Wick", "film": "John Wick", "year": "2014", "hint": "John W___"},
        {"quote": "Zabili mého psa", "film": "John Wick", "year": "2014", "hint": "John W___"},
        {"quote": "Já jsem Matrix", "film": "Matrix Resurrections", "year": "2021", "hint": "Matrix R___________"},
        {"quote": "Buď připraven!", "film": "Lví král", "year": "1994", "hint": "Lví k___"},
        {"quote": "Tohle je Sparta!", "film": "300", "year": "2006", "hint": "3__"},
        {"quote": "Dnes večer večeříme v pekle!", "film": "300", "year": "2006", "hint": "3__"},
        {"quote": "Nenávidím hady", "film": "Indiana Jones", "year": "1981", "hint": "Indiana J____"},
        {"quote": "To patří do muzea!", "film": "Indiana Jones", "year": "1981", "hint": "Indiana J____"},
        {"quote": "Tvůj čas vypršel", "film": "Piráti z Karibiku", "year": "2003", "hint": "Piráti z K______"},
        {"quote": "Ale rum jste vzali, ne?", "film": "Piráti z Karibiku", "year": "2003", "hint": "Piráti z K______"},
        {"quote": "Jsem kapitán Jack Sparrow!", "film": "Piráti z Karibiku", "year": "2003", "hint": "Piráti z K______"},
        {"quote": "Já jsem Batman", "film": "Batman", "year": "1989", "hint": "B_____"},
        {"quote": "Volám se Neo", "film": "Matrix", "year": "1999", "hint": "M_____"},
    ],
    "horor": [
        {"quote": "Jsou tady!", "film": "Poltergeist", "year": "1982", "hint": "P__________"},
        {"quote": "Jaký je tvůj oblíbený strašidelný film?", "film": "Vřískot", "year": "1996", "hint": "V______"},
        {"quote": "Všichni tu dole plujeme", "film": "To", "year": "2017", "hint": "T_"},
        {"quote": "Tady je Johnny!", "film": "Osvícení", "year": "1980", "hint": "O_______"},
        {"quote": "Chci si zahrát hru", "film": "Saw", "year": "2004", "hint": "S__"},
        {"quote": "Dá si krém do košíku", "film": "Mlčení jehňátek", "year": "1991", "hint": "Mlčení j_______"},
        {"quote": "Jeden sčítač lidu mě chtěl testovat", "film": "Mlčení jehňátek", "year": "1991", "hint": "Mlčení j_______"},
        {"quote": "Jdou si pro tebe, Barbaro!", "film": "Noc oživlých mrtvol", "year": "1968", "hint": "Noc oživlých m_____"},
        {"quote": "Měj strach. Měj velký strach.", "film": "Moucha", "year": "1986", "hint": "M_____"},
        {"quote": "Ať děláš co děláš, neusni", "film": "Noční můra v Elm Street", "year": "1984", "hint": "Noční m___ v E__ S_____"},
        {"quote": "Je to živé! Je to živé!", "film": "Frankenstein", "year": "1931", "hint": "F___________"},
        {"quote": "Sedm dní", "film": "Kruh", "year": "2002", "hint": "K___"},
        {"quote": "Jsem tvůj největší fanoušek", "film": "Misery", "year": "1990", "hint": "M_____"},
        # Nové horory
        {"quote": "Nepodívej se, zůstaň zticha", "film": "Tiché místo", "year": "2018", "hint": "Tiché m____"},
        {"quote": "Jeden, dva, Freddy jde", "film": "Noční můra v Elm Street", "year": "1984", "hint": "Noční m___ v E__ S_____"},
        {"quote": "Chtěli jsme jen pomoct", "film": "Čelisti", "year": "1975", "hint": "Č______"},
        {"quote": "Budeme potřebovat větší loď", "film": "Čelisti", "year": "1975", "hint": "Č______"},
        {"quote": "Hej, pojď si hrát s námi", "film": "Osvícení", "year": "1980", "hint": "O_______"},
        {"quote": "Rudrum", "film": "Osvícení", "year": "1980", "hint": "O_______"},
        {"quote": "Zabiju tě, ty malá potvoro!", "film": "Dítě Rosemary", "year": "1968", "hint": "Dítě R_______"},
        {"quote": "On je tady", "film": "Paranormal Activity", "year": "2007", "hint": "Paranormal A_______"},
        {"quote": "Pomoz mi!", "film": "Vymítač ďábla", "year": "1973", "hint": "Vymítač ď_____"},
        {"quote": "Tvá matka vaří peklo v pekle!", "film": "Vymítač ďábla", "year": "1973", "hint": "Vymítač ď_____"},
        {"quote": "Něco tu není v pořádku", "film": "Sinister", "year": "2012", "hint": "S_______"},
        {"quote": "Já tě vidím", "film": "V zajetí démonů", "year": "2013", "hint": "V zajetí d_____"},
        {"quote": "Annabelle se vrací", "film": "Annabelle", "year": "2014", "hint": "A________"},
    ],
    "scifi": [
        {"quote": "Promiň Dave, to nemůžu udělat", "film": "2001: Vesmírná odysea", "year": "1968", "hint": "2001: Vesmírná o_____"},
        {"quote": "E.T. domů volat", "film": "E.T. Mimozemšťan", "year": "1982", "hint": "E.T. M__________"},
        {"quote": "Já se vrátím", "film": "Terminátor", "year": "1984", "hint": "T________"},
        {"quote": "Matrix tě má", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Žádná lžíce není", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Probuď se, Neo", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Odpor je marný", "film": "Star Trek", "year": "1996", "hint": "Star T___"},
        {"quote": "Žij dlouho a blaze", "film": "Star Trek", "year": "1966", "hint": "Star T___"},
        {"quote": "Ve vesmíru tě nikdo neslyší křičet", "film": "Vetřelec", "year": "1979", "hint": "V______"},
        {"quote": "Konec hry, chlape! Konec hry!", "film": "Vetřelci", "year": "1986", "hint": "V______"},
        {"quote": "Zůstaň na cíli!", "film": "Star Wars", "year": "1977", "hint": "Star W___"},
        {"quote": "Udělej nebo neudělej. Žádné zkusit není.", "film": "Star Wars", "year": "1980", "hint": "Star W___"},
        {"quote": "Tvůj nedostatek víry mě znepokojuje", "film": "Star Wars", "year": "1977", "hint": "Star W___"},
        {"quote": "Tohle nejsou ti droidi, které hledáte", "film": "Star Wars", "year": "1977", "hint": "Star W___"},
        {"quote": "Chytrá holka", "film": "Jurský park", "year": "1993", "hint": "Jurský p___"},
        {"quote": "Život si najde cestu", "film": "Jurský park", "year": "1993", "hint": "Jurský p___"},
        {"quote": "Držte se svých zadků", "film": "Jurský park", "year": "1993", "hint": "Jurský p___"},
        {"quote": "Já jsem nevyhnutelný", "film": "Avengers: Endgame", "year": "2019", "hint": "Avengers: E______"},
        {"quote": "Jsme v závěrečné hře", "film": "Avengers: Infinity War", "year": "2018", "hint": "Avengers: I_______ W__"},
        # Nové sci-fi
        {"quote": "Láska je jediná věc, co překoná čas", "film": "Interstellar", "year": "2014", "hint": "I___________"},
        {"quote": "Nežijeme ve tmě, jsme tma", "film": "Interstellar", "year": "2014", "hint": "I___________"},
        {"quote": "Murph!", "film": "Interstellar", "year": "2014", "hint": "I___________"},
        {"quote": "Zrodil jsem se připraven", "film": "Blade Runner", "year": "1982", "hint": "Blade R_____"},
        {"quote": "Viděl jsem věci, kterým byste nevěřili", "film": "Blade Runner", "year": "1982", "hint": "Blade R_____"},
        {"quote": "Čas zemřít", "film": "Blade Runner", "year": "1982", "hint": "Blade R_____"},
        {"quote": "Probuď se, samuráji", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Já vím kung-fu", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Sleduj bílého králíka", "film": "Matrix", "year": "1999", "hint": "M_____"},
        {"quote": "Toto je konec, příteli", "film": "Avatar", "year": "2009", "hint": "A_____"},
        {"quote": "Vidím tě", "film": "Avatar", "year": "2009", "hint": "A_____"},
        {"quote": "Propojíme se", "film": "Avatar", "year": "2009", "hint": "A_____"},
        {"quote": "Pošlu tě do minulosti", "film": "X-Men: Budoucí minulost", "year": "2014", "hint": "X-Men: B______ m_______"},
        {"quote": "Mutanti jsou budoucnost", "film": "X-Men", "year": "2000", "hint": "X-M__"},
        {"quote": "Tenhle kopec byl můj domov", "film": "WALL-E", "year": "2008", "hint": "WALL-_"},
        {"quote": "Eva!", "film": "WALL-E", "year": "2008", "hint": "WALL-_"},
    ]
}

# ============== PRAVDA/LEŽ KVÍZ ==============

FACTS_DATABASE = [
    # Zvířata - PRAVDA
    {"fact": "Srdce garnáta je v jeho hlavě", "answer": True, "category": "zvířata"},
    {"fact": "Krávy mají nejlepší kamarády a stresují se, když jsou od sebe odděleny", "answer": True, "category": "zvířata"},
    {"fact": "Chobotnice mají tři srdce", "answer": True, "category": "zvířata"},
    {"fact": "Hlemýždi mohou spát až 3 roky", "answer": True, "category": "zvířata"},
    {"fact": "Slon je jediné zvíře, které neumí skákat", "answer": True, "category": "zvířata"},
    {"fact": "Krokodýl nedokáže vypláznou jazyk", "answer": True, "category": "zvířata"},
    {"fact": "Motýli ochutnávají nohama", "answer": True, "category": "zvířata"},
    {"fact": "Plameňáci se rodí růžoví", "answer": False, "category": "zvířata"},
    {"fact": "Pštrosi strkají hlavu do písku, když mají strach", "answer": False, "category": "zvířata"},
    {"fact": "Netopýři jsou slepí", "answer": False, "category": "zvířata"},
    {"fact": "Zlaté rybky mají paměť jen 3 sekundy", "answer": False, "category": "zvířata"},
    {"fact": "Kočky mají 9 životů", "answer": False, "category": "zvířata"},
    {"fact": "Delfíni spí s jedním okem otevřeným", "answer": True, "category": "zvířata"},
    {"fact": "Koaly mají otisky prstů podobné lidským", "answer": True, "category": "zvířata"},
    {"fact": "Žirafy nemají hlasivky a jsou úplně němé", "answer": False, "category": "zvířata"},
    {"fact": "Včely umí rozpoznat lidské tváře", "answer": True, "category": "zvířata"},
    {"fact": "Tučňáci mají kolena", "answer": True, "category": "zvířata"},
    {"fact": "Pavouci mají 6 nohou", "answer": False, "category": "zvířata"},
    
    # Věda - PRAVDA
    {"fact": "Blesk může udeřit dvakrát na stejné místo", "answer": True, "category": "věda"},
    {"fact": "Lidské tělo obsahuje dost uhlíku na výrobu 9000 tužek", "answer": True, "category": "věda"},
    {"fact": "Voda může být současně v kapalném i plynném stavu", "answer": True, "category": "věda"},
    {"fact": "Banány jsou radioaktivní", "answer": True, "category": "věda"},
    {"fact": "Sklo je ve skutečnosti tekutina", "answer": False, "category": "věda"},
    {"fact": "Měsíc má vlastní světlo", "answer": False, "category": "věda"},
    {"fact": "Hvězda, kterou vidíme, už možná neexistuje", "answer": True, "category": "věda"},
    {"fact": "Na Venuši trvá den déle než rok", "answer": True, "category": "věda"},
    {"fact": "Lidé používají jen 10% svého mozku", "answer": False, "category": "věda"},
    {"fact": "Velká čínská zeď je vidět z vesmíru pouhým okem", "answer": False, "category": "věda"},
    {"fact": "Diamant lze zničit ohněm", "answer": True, "category": "věda"},
    {"fact": "Horká voda zamrzá rychleji než studená", "answer": True, "category": "věda"},
    {"fact": "Severní pól má pevninu pod ledem", "answer": False, "category": "věda"},
    {"fact": "Saturn by plaval ve vodě, kdyby byla dostatečně velká nádoba", "answer": True, "category": "věda"},
    {"fact": "Na Marsu jsou sopky větší než Mount Everest", "answer": True, "category": "věda"},
    {"fact": "Člověk může přežít ve vesmíru 2 minuty bez skafandru", "answer": False, "category": "věda"},
    
    # Historie
    {"fact": "Kleopatra žila blíže k přistání na Měsíci než ke stavbě pyramid", "answer": True, "category": "historie"},
    {"fact": "Vikingové nosili rohaté helmy", "answer": False, "category": "historie"},
    {"fact": "Napoleon byl velmi malý", "answer": False, "category": "historie"},
    {"fact": "Oxford univerzita je starší než Aztécká říše", "answer": True, "category": "historie"},
    {"fact": "Albert Einstein propadl z matematiky", "answer": False, "category": "historie"},
    {"fact": "Ve starověkém Římě existovala bohyně kanalizace", "answer": True, "category": "historie"},
    {"fact": "Pyramidy byly původně bílé a lesklé", "answer": True, "category": "historie"},
    {"fact": "Poslední poprava gilotinou ve Francii byla v roce 1977", "answer": True, "category": "historie"},
    {"fact": "Coca-Cola byla původně zelená", "answer": False, "category": "historie"},
    {"fact": "Titanic byl první loď, která použila SOS signál", "answer": False, "category": "historie"},
    {"fact": "Česká republika má více hradů na km² než jakákoli jiná země", "answer": True, "category": "historie"},
    {"fact": "První programátor na světě byla žena", "answer": True, "category": "historie"},
    {"fact": "Edison vynalezl žárovku", "answer": False, "category": "historie"},
    {"fact": "Čínská zeď je vidět z Měsíce", "answer": False, "category": "historie"},
    
    # Lidské tělo
    {"fact": "Lidský nos dokáže rozpoznat bilion různých vůní", "answer": True, "category": "tělo"},
    {"fact": "Nehty na rukou rostou rychleji než na nohou", "answer": True, "category": "tělo"},
    {"fact": "Žaludek vytváří novou výstelku každé 3-4 dny", "answer": True, "category": "tělo"},
    {"fact": "Člověk má víc než 5 smyslů", "answer": True, "category": "tělo"},
    {"fact": "Krev je modrá, dokud se nedostane do kontaktu s kyslíkem", "answer": False, "category": "tělo"},
    {"fact": "Vlasy rostou po smrti", "answer": False, "category": "tělo"},
    {"fact": "Jazyk je nejsilnější sval v těle", "answer": False, "category": "tělo"},
    {"fact": "Lidé mají unikátní otisk jazyka, jako otisky prstů", "answer": True, "category": "tělo"},
    {"fact": "Dospělý člověk má 206 kostí", "answer": True, "category": "tělo"},
    {"fact": "Novorozenec má více kostí než dospělý", "answer": True, "category": "tělo"},
    {"fact": "Mozek necítí bolest", "answer": True, "category": "tělo"},
    {"fact": "Člověk denně vytvoří 1-2 litry slin", "answer": True, "category": "tělo"},
    {"fact": "Srdce bije i mimo tělo", "answer": True, "category": "tělo"},
    {"fact": "Člověk se rodí bez koleních čéšek", "answer": True, "category": "tělo"},
    
    # Jídlo
    {"fact": "Med nikdy nezkazí", "answer": True, "category": "jídlo"},
    {"fact": "Rajčata jsou ovoce", "answer": True, "category": "jídlo"},
    {"fact": "Jahody nejsou bobule, ale banány ano", "answer": True, "category": "jídlo"},
    {"fact": "Arašídy jsou ořechy", "answer": False, "category": "jídlo"},
    {"fact": "Wasabi, které dostanete v restauraci, je obvykle křen s barvivem", "answer": True, "category": "jídlo"},
    {"fact": "Bílá čokoláda obsahuje čokoládu", "answer": False, "category": "jídlo"},
    {"fact": "Kečup byl kdysi prodáván jako lék", "answer": True, "category": "jídlo"},
    {"fact": "Muškátový oříšek ve velkém množství způsobuje halucinace", "answer": True, "category": "jídlo"},
    {"fact": "Avokádo je ovoce", "answer": True, "category": "jídlo"},
    {"fact": "Pomeranče se jmenují podle barvy", "answer": False, "category": "jídlo"},
    {"fact": "Pálivost chilli papriček se měří ve Scoville jednotkách", "answer": True, "category": "jídlo"},
    {"fact": "Brambory mají více chromozomů než člověk", "answer": True, "category": "jídlo"},
    
    # Česko
    {"fact": "Praha je starší než Vídeň", "answer": True, "category": "česko"},
    {"fact": "Češi pijí nejvíce piva na světě na osobu", "answer": True, "category": "česko"},
    {"fact": "Slovo robot vymyslel Karel Čapek", "answer": False, "category": "česko"},
    {"fact": "Kontaktní čočky vynalezl Čech", "answer": True, "category": "česko"},
    {"fact": "Česká republika nemá moře", "answer": True, "category": "česko"},
    {"fact": "Karlův most byl postaven za vlády Karla IV.", "answer": True, "category": "česko"},
    {"fact": "Semtex byl vynalezen v Česku", "answer": True, "category": "česko"},
    {"fact": "Kostka cukru byla vynalezena v Česku", "answer": True, "category": "česko"},
    {"fact": "Václavské náměstí je ve skutečnosti bulvár, ne náměstí", "answer": True, "category": "česko"},
    {"fact": "Česká hymna má jen jednu sloku", "answer": True, "category": "česko"},
    {"fact": "Pražský orloj je nejstarší fungující astronomické hodiny na světě", "answer": True, "category": "česko"},
    {"fact": "Slovo dolar pochází z českého tolaru", "answer": True, "category": "česko"},
    
    # Zábavné/Bizarní
    {"fact": "V Japonsku existuje ostrov plný králíků", "answer": True, "category": "bizarní"},
    {"fact": "Ve Švýcarsku je nelegální mít jen jednoho morčete", "answer": True, "category": "bizarní"},
    {"fact": "Kachny kvákání nevytváří ozvěnu", "answer": False, "category": "bizarní"},
    {"fact": "McDonald's prodává v Indii hovězí burgery", "answer": False, "category": "bizarní"},
    {"fact": "LEGO vyrábí více pneumatik ročně než jakákoli jiná firma", "answer": True, "category": "bizarní"},
    {"fact": "Twitter logo ptáček se jmenuje Larry", "answer": True, "category": "bizarní"},
    {"fact": "Barbie má příjmení Roberts", "answer": True, "category": "bizarní"},
    {"fact": "V angličtině existuje slovo pro strach z dlouhých slov", "answer": True, "category": "bizarní"},
    {"fact": "Jazykolam je hippopotomonstrosesquipedaliofóbie", "answer": True, "category": "bizarní"},
    {"fact": "Nintendo bylo založeno v roce 1889", "answer": True, "category": "bizarní"},
    {"fact": "Průměrný člověk sní za život 8 pavouků ve spánku", "answer": False, "category": "bizarní"},
    {"fact": "V Norsku existuje město s názvem Hell", "answer": True, "category": "bizarní"},
    {"fact": "Kečup teče rychlostí 40 km za hodinu", "answer": False, "category": "bizarní"},
    {"fact": "Emoji pro tvář s potem 😅 původně znamenalo úlevu, ne nervozitu", "answer": True, "category": "bizarní"},
]

# Active pravda/lež games
active_truth_games = {}

class TruthView(discord.ui.View):
    def __init__(self, channel_id: int, correct_answer: bool, fact_text: str):
        super().__init__(timeout=30)
        self.channel_id = channel_id
        self.correct_answer = correct_answer
        self.fact_text = fact_text
        self.answered_users = {}  # {user_id: {"name": name, "answer": bool}}
    
    @discord.ui.button(label="✅ PRAVDA", style=discord.ButtonStyle.success, custom_id="truth_true")
    async def truth_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, True)
    
    @discord.ui.button(label="❌ LEŽ", style=discord.ButtonStyle.danger, custom_id="truth_false")
    async def lie_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, False)
    
    async def handle_answer(self, interaction: discord.Interaction, user_answer: bool):
        user_id = interaction.user.id
        
        if user_id in self.answered_users:
            await interaction.response.send_message("❌ Už jsi odpověděl/a!", ephemeral=True)
            return
        
        self.answered_users[user_id] = {
            "name": interaction.user.display_name,
            "answer": user_answer
        }
        
        is_correct = user_answer == self.correct_answer
        
        if is_correct:
            await interaction.response.send_message("✅ Správně! Počkej na výsledky...", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Špatně! Počkej na výsledky...", ephemeral=True)
    
    async def on_timeout(self):
        # This is handled by the game loop
        pass

async def run_truth_game(channel, message, view: TruthView, fact_data: dict, guild_id: int):
    """Wait for answers and show results"""
    await asyncio.sleep(15)  # Wait 15 seconds for answers
    
    # Disable buttons
    for item in view.children:
        item.disabled = True
    
    # Count results and give XP
    correct_users = []
    wrong_users = []
    
    for user_id, data in view.answered_users.items():
        if data["answer"] == view.correct_answer:
            correct_users.append(data["name"])
            # Add XP for correct answer
            await add_xp(guild_id, user_id, data["name"], XP_REWARDS["truth_correct"], channel)
            increment_stats(guild_id, user_id, correct=True)
        else:
            wrong_users.append(data["name"])
            increment_stats(guild_id, user_id, correct=False)
    
    answer_text = "✅ PRAVDA" if view.correct_answer else "❌ LEŽ"
    
    embed = discord.Embed(
        title="🎯 VÝSLEDKY",
        description=f"**{view.fact_text}**",
        color=discord.Color.green() if view.correct_answer else discord.Color.red()
    )
    embed.add_field(name="Správná odpověď", value=answer_text, inline=False)
    
    if correct_users:
        embed.add_field(name=f"✅ Správně ({len(correct_users)}) +{XP_REWARDS['truth_correct']} XP", value=", ".join(correct_users[:15]) or "Nikdo", inline=True)
    if wrong_users:
        embed.add_field(name=f"❌ Špatně ({len(wrong_users)})", value=", ".join(wrong_users[:15]) or "Nikdo", inline=True)
    
    if not view.answered_users:
        embed.add_field(name="😢", value="Nikdo neodpověděl!", inline=False)
    
    embed.set_footer(text=f"Kategorie: {fact_data.get('category', 'obecné')}")
    
    try:
        await message.edit(embed=embed, view=view)
    except:
        pass
    
    # Cleanup
    if channel.id in active_truth_games:
        del active_truth_games[channel.id]

@bot.tree.command(name="pravda", description="Pravda nebo lež? Hádej jestli je fakt pravdivý!")
@app_commands.describe(kategorie="Vyber kategorii faktů")
@app_commands.choices(kategorie=[
    app_commands.Choice(name="🐾 Zvířata", value="zvířata"),
    app_commands.Choice(name="🔬 Věda", value="věda"),
    app_commands.Choice(name="📜 Historie", value="historie"),
    app_commands.Choice(name="🫀 Lidské tělo", value="tělo"),
    app_commands.Choice(name="🍕 Jídlo", value="jídlo"),
    app_commands.Choice(name="🇨🇿 Česko", value="česko"),
    app_commands.Choice(name="🤪 Bizarní", value="bizarní"),
    app_commands.Choice(name="🎲 Náhodné", value="random"),
])
async def slash_pravda(interaction: discord.Interaction, kategorie: str = "random"):
    # Check permission from database
    if not await check_command_permission(interaction, "pravda"):
        return
    
    import random
    
    channel_id = interaction.channel_id
    
    if channel_id in active_truth_games:
        await interaction.response.send_message("❌ V tomto kanálu už běží hra! Počkej na výsledky.", ephemeral=True)
        return
    
    # Filter facts by category
    if kategorie == "random":
        available_facts = FACTS_DATABASE
    else:
        available_facts = [f for f in FACTS_DATABASE if f.get("category") == kategorie]
    
    if not available_facts:
        available_facts = FACTS_DATABASE
    
    fact_data = random.choice(available_facts)
    
    active_truth_games[channel_id] = True
    
    view = TruthView(channel_id, fact_data["answer"], fact_data["fact"])
    
    category_names = {
        "zvířata": "🐾 Zvířata", "věda": "🔬 Věda", "historie": "📜 Historie",
        "tělo": "🫀 Lidské tělo", "jídlo": "🍕 Jídlo", "česko": "🇨🇿 Česko",
        "bizarní": "🤪 Bizarní"
    }
    
    embed = discord.Embed(
        title="🤔 PRAVDA NEBO LEŽ?",
        description=f"**{fact_data['fact']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="📁 Kategorie", value=category_names.get(fact_data.get("category"), "Obecné"), inline=True)
    embed.add_field(name="⏰ Čas", value="15 sekund", inline=True)
    embed.set_footer(text="Klikni na tlačítko pro odpověď!")
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    # Start game loop
    asyncio.create_task(run_truth_game(interaction.channel, message, view, fact_data, interaction.guild_id))

@bot.command(name="pravda", aliases=["pn", "fact", "fakt"])
async def prefix_pravda(ctx, kategorie: str = "random"):
    """!pravda [kategorie] - Pravda nebo lež hra"""
    import random
    
    channel_id = ctx.channel.id
    
    if channel_id in active_truth_games:
        await ctx.send("❌ V tomto kanálu už běží hra! Počkej na výsledky.")
        return
    
    # Map category aliases
    category_map = {
        "zvirata": "zvířata", "zvířata": "zvířata", "animals": "zvířata",
        "veda": "věda", "věda": "věda", "science": "věda",
        "historie": "historie", "history": "historie",
        "telo": "tělo", "tělo": "tělo", "body": "tělo",
        "jidlo": "jídlo", "jídlo": "jídlo", "food": "jídlo",
        "cesko": "česko", "česko": "česko", "cz": "česko",
        "bizarni": "bizarní", "bizarní": "bizarní", "weird": "bizarní",
        "random": "random", "nahodne": "random"
    }
    
    kategorie = category_map.get(kategorie.lower(), "random")
    
    if kategorie == "random":
        available_facts = FACTS_DATABASE
    else:
        available_facts = [f for f in FACTS_DATABASE if f.get("category") == kategorie]
    
    if not available_facts:
        available_facts = FACTS_DATABASE
    
    fact_data = random.choice(available_facts)
    
    active_truth_games[channel_id] = True
    
    view = TruthView(channel_id, fact_data["answer"], fact_data["fact"])
    
    category_names = {
        "zvířata": "🐾 Zvířata", "věda": "🔬 Věda", "historie": "📜 Historie",
        "tělo": "🫀 Lidské tělo", "jídlo": "🍕 Jídlo", "česko": "🇨🇿 Česko",
        "bizarní": "🤪 Bizarní"
    }
    
    embed = discord.Embed(
        title="🤔 PRAVDA NEBO LEŽ?",
        description=f"**{fact_data['fact']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="📁 Kategorie", value=category_names.get(fact_data.get("category"), "Obecné"), inline=True)
    embed.add_field(name="⏰ Čas", value="15 sekund", inline=True)
    embed.set_footer(text="Klikni na tlačítko pro odpověď!")
    
    message = await ctx.send(embed=embed, view=view)
    
    asyncio.create_task(run_truth_game(ctx.channel, message, view, fact_data, ctx.guild.id))

# Active film quizzes
active_film_quiz = {}

@bot.tree.command(name="film", description="Spusť filmový kvíz - hádej film!")
@app_commands.describe(zanr="Vyber žánr filmů")
@app_commands.choices(zanr=[
    app_commands.Choice(name="🇨🇿 České filmy", value="ceske"),
    app_commands.Choice(name="🎬 Hollywood", value="hollywood"),
    app_commands.Choice(name="😂 Komedie", value="komedie"),
    app_commands.Choice(name="💥 Akční", value="akcni"),
    app_commands.Choice(name="👻 Horor", value="horor"),
    app_commands.Choice(name="🚀 Sci-Fi", value="scifi"),
    app_commands.Choice(name="🎲 Náhodný", value="random"),
])
async def slash_film(interaction: discord.Interaction, zanr: str = "random"):
    # Check permission from database
    if not await check_command_permission(interaction, "film"):
        return
    
    channel_id = interaction.channel_id
    guild_id = interaction.guild_id
    
    if channel_id in active_film_quiz and active_film_quiz[channel_id].get("active"):
        await interaction.response.send_message("❌ V tomto kanálu už běží filmový kvíz!", ephemeral=True)
        return
    
    quiz_time = get_quiz_time(guild_id)
    total_rounds = get_quiz_rounds(guild_id)
    
    active_film_quiz[channel_id] = {
        "active": True,
        "genre": zanr,
        "current_round": 0,
        "total_rounds": total_rounds,
        "scores": {},
        "current_question": None,
        "answered": False,
        "quiz_time": quiz_time,
        "guild_id": guild_id
    }
    
    genre_names = {"ceske": "🇨🇿 České", "hollywood": "🎬 Hollywood", "komedie": "😂 Komedie", "akcni": "💥 Akční", "horor": "👻 Horor", "scifi": "🚀 Sci-Fi"}
    
    embed = discord.Embed(
        title="🎬 FILMOVÝ KVÍZ ZAČÍNÁ!",
        description=f"**{total_rounds} otázek** | **{quiz_time}s na odpověď**",
        color=discord.Color.red()
    )
    embed.add_field(name="🎞️ Žánr", value=genre_names.get(zanr, "NÁHODNÝ"), inline=True)
    embed.add_field(name="📝 Pravidla", value="Napiš název filmu do chatu!", inline=False)
    embed.set_footer(text="První otázka za 3 sekundy...")
    
    await interaction.response.send_message(embed=embed)
    await asyncio.sleep(3)
    
    await run_film_quiz(interaction.channel, channel_id)

async def run_film_quiz(channel, channel_id: int):
    """Run multiple rounds of film quiz"""
    import random
    
    quiz_data = active_film_quiz.get(channel_id)
    if not quiz_data:
        return
    
    genre = quiz_data["genre"]
    total_rounds = quiz_data["total_rounds"]
    quiz_time = quiz_data["quiz_time"]
    genre_names = {"ceske": "🇨🇿 České", "hollywood": "🎬 Hollywood", "komedie": "😂 Komedie", "akcni": "💥 Akční", "horor": "👻 Horor", "scifi": "🚀 Sci-Fi"}
    
    for round_num in range(1, total_rounds + 1):
        if channel_id not in active_film_quiz:
            return
        
        quiz_data = active_film_quiz[channel_id]
        quiz_data["current_round"] = round_num
        quiz_data["answered"] = False
        
        current_genre = genre if genre != "random" else random.choice(list(FILM_DATABASE.keys()))
        film_data = random.choice(FILM_DATABASE[current_genre])
        
        quiz_data["current_question"] = {
            "film": film_data["film"],
            "year": film_data["year"],
            "hint": film_data["hint"]
        }
        
        embed = discord.Embed(
            title=f"🎬 OTÁZKA {round_num}/{total_rounds}",
            description="**Hádej film!**",
            color=discord.Color.red()
        )
        embed.add_field(name="🎤 Slavná hláška", value=f"*\"{film_data['quote']}\"*", inline=False)
        embed.add_field(name="💡 Nápověda", value=f"`{film_data['hint']}`", inline=True)
        embed.add_field(name="📅 Rok", value=film_data['year'], inline=True)
        embed.add_field(name="🎞️ Žánr", value=genre_names.get(current_genre, current_genre), inline=True)
        embed.add_field(name="⏰ Čas", value=f"{quiz_time}s", inline=True)
        
        await channel.send(embed=embed)
        
        elapsed = 0
        while elapsed < quiz_time:
            await asyncio.sleep(0.5)
            elapsed += 0.5
            
            quiz_data = active_film_quiz.get(channel_id)
            if not quiz_data:
                return
            if quiz_data.get("answered"):
                break
        
        quiz_data = active_film_quiz.get(channel_id)
        if not quiz_data:
            return
        
        if not quiz_data["answered"]:
            embed = discord.Embed(
                title="⏰ ČAS VYPRŠEL!",
                description=f"Správná odpověď: **{film_data['film']}** ({film_data['year']})",
                color=discord.Color.orange()
            )
            await channel.send(embed=embed)
        
        if round_num < total_rounds:
            await channel.send(f"⏳ **Další otázka za 3 sekundy...**")
            await asyncio.sleep(3)
    
    # Quiz finished
    quiz_data = active_film_quiz.get(channel_id)
    if quiz_data:
        scores = quiz_data.get("scores", {})
        
        if scores:
            sorted_scores = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
            
            medals = ["🥇", "🥈", "🥉"]
            leaderboard = ""
            for i, (user_id, data) in enumerate(sorted_scores[:10]):
                medal = medals[i] if i < 3 else f"**{i+1}.**"
                leaderboard += f"{medal} {data['name']} - **{data['score']} bodů**\n"
            
            embed = discord.Embed(
                title="🏆 FILMOVÝ KVÍZ DOKONČEN!",
                description=f"**Výsledky z {total_rounds} otázek:**",
                color=discord.Color.gold()
            )
            embed.add_field(name="📊 Žebříček", value=leaderboard or "Nikdo neskóroval", inline=False)
            
            if sorted_scores:
                winner_id, winner_data = sorted_scores[0]
                embed.add_field(name="👑 Vítěz", value=f"**{winner_data['name']}** s {winner_data['score']} body!", inline=False)
        else:
            embed = discord.Embed(
                title="🏆 FILMOVÝ KVÍZ DOKONČEN!",
                description="Nikdo neuhodl žádnou otázku!",
                color=discord.Color.orange()
            )
        
        await channel.send(embed=embed)
        
        if channel_id in active_film_quiz:
            del active_film_quiz[channel_id]

@bot.command(name="film", aliases=["movie", "kino"])
@commands.has_permissions(administrator=True)
async def prefix_film(ctx, zanr: str = "random"):
    """!film [ceske/hollywood/komedie/akcni/horor/scifi/random] - Filmový kvíz (Admin)"""
    channel_id = ctx.channel.id
    guild_id = ctx.guild.id
    
    if channel_id in active_film_quiz and active_film_quiz[channel_id].get("active"):
        await ctx.send("❌ V tomto kanálu už běží filmový kvíz!")
        return
    
    if zanr not in ["ceske", "hollywood", "komedie", "akcni", "horor", "scifi", "random"]:
        zanr = "random"
    
    quiz_time = get_quiz_time(guild_id)
    total_rounds = get_quiz_rounds(guild_id)
    
    active_film_quiz[channel_id] = {
        "active": True,
        "genre": zanr,
        "current_round": 0,
        "total_rounds": total_rounds,
        "scores": {},
        "current_question": None,
        "answered": False,
        "quiz_time": quiz_time,
        "guild_id": guild_id
    }
    
    genre_names = {"ceske": "🇨🇿 České", "hollywood": "🎬 Hollywood", "komedie": "😂 Komedie", "akcni": "💥 Akční", "horor": "👻 Horor", "scifi": "🚀 Sci-Fi"}
    
    embed = discord.Embed(
        title="🎬 FILMOVÝ KVÍZ ZAČÍNÁ!",
        description=f"**{total_rounds} otázek** | **{quiz_time}s na odpověď**",
        color=discord.Color.red()
    )
    embed.add_field(name="🎞️ Žánr", value=genre_names.get(zanr, "NÁHODNÝ"), inline=True)
    embed.add_field(name="📝 Pravidla", value="Napiš název filmu do chatu!", inline=False)
    embed.set_footer(text="První otázka za 3 sekundy...")
    
    await ctx.send(embed=embed)
    await asyncio.sleep(3)
    
    await run_film_quiz(ctx.channel, channel_id)

@bot.tree.command(name="stop", description="Zastav běžící kvíz")
async def slash_stop(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    stopped = []
    
    if channel_id in active_music_quiz:
        del active_music_quiz[channel_id]
        stopped.append("🎵 Hudební kvíz")
    
    if channel_id in active_film_quiz:
        del active_film_quiz[channel_id]
        stopped.append("🎬 Filmový kvíz")
    
    if stopped:
        await interaction.response.send_message(f"🛑 Zastaveno: {', '.join(stopped)}")
    else:
        await interaction.response.send_message("❌ Žádný kvíz neběží v tomto kanálu.", ephemeral=True)

@bot.command(name="stop", aliases=["stophudba", "stopfilm"])
async def prefix_stop_quiz(ctx):
    """!stop - Zastav běžící kvíz"""
    channel_id = ctx.channel.id
    stopped = []
    
    if channel_id in active_music_quiz:
        del active_music_quiz[channel_id]
        stopped.append("🎵 Hudební kvíz")
    
    if channel_id in active_film_quiz:
        del active_film_quiz[channel_id]
        stopped.append("🎬 Filmový kvíz")
    
    if stopped:
        await ctx.send(f"🛑 Zastaveno: {', '.join(stopped)}")
    else:
        await ctx.send("❌ Žádný kvíz neběží v tomto kanálu.")

# Listen for quiz answers
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Sledování zpráv pro statistiky
    if message.guild:
        increment_message_count(message.guild.id, message.author.id, message.author.display_name)
    
    # Skip if message is a command
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    channel_id = message.channel.id
    
    # Check for active FILM quiz
    if channel_id in active_film_quiz:
        quiz_data = active_film_quiz[channel_id]
        
        if quiz_data.get("active") and quiz_data.get("current_question") and not quiz_data.get("answered"):
            user_answer = normalize_answer(message.content)
            correct_film = normalize_answer(quiz_data["current_question"]["film"])
            
            # Check if answer matches
            if len(user_answer) >= 3 and (correct_film in user_answer or user_answer in correct_film):
                quiz_data["answered"] = True
                
                # Add score
                user_id = message.author.id
                if user_id not in quiz_data["scores"]:
                    quiz_data["scores"][user_id] = {"name": message.author.display_name, "score": 0}
                quiz_data["scores"][user_id]["score"] += 1
                
                current_score = quiz_data["scores"][user_id]["score"]
                
                # Add XP
                guild_id = quiz_data.get("guild_id", message.guild.id)
                await add_xp(guild_id, user_id, message.author.display_name, XP_REWARDS["quiz_correct"], message.channel)
                increment_stats(guild_id, user_id, correct=True)
                
                embed = discord.Embed(
                    title="🎉 SPRÁVNĚ!",
                    description=f"**{message.author.display_name}** uhodl/a!",
                    color=discord.Color.green()
                )
                embed.add_field(name="🎬 Film", value=quiz_data["current_question"]["film"], inline=True)
                embed.add_field(name="📅 Rok", value=quiz_data["current_question"]["year"], inline=True)
                embed.add_field(name="📊 Skóre", value=f"{current_score} bodů", inline=True)
                embed.add_field(name="✨ XP", value=f"+{XP_REWARDS['quiz_correct']} XP", inline=True)
                embed.set_thumbnail(url=message.author.display_avatar.url)
                
                await message.channel.send(f"🏆 {message.author.mention}", embed=embed)
    
    # Check for active MUSIC quiz
    if channel_id in active_music_quiz:
        quiz_data = active_music_quiz[channel_id]
        
        if quiz_data.get("active") and quiz_data.get("current_question") and not quiz_data.get("answered"):
            user_answer = normalize_answer(message.content)
            correct_artist = normalize_answer(quiz_data["current_question"]["artist"])
            
            # Check if answer matches
            if len(user_answer) >= 3 and (correct_artist in user_answer or user_answer in correct_artist):
                quiz_data["answered"] = True
                
                # Add score
                user_id = message.author.id
                if user_id not in quiz_data["scores"]:
                    quiz_data["scores"][user_id] = {"name": message.author.display_name, "score": 0}
                quiz_data["scores"][user_id]["score"] += 1
                
                current_score = quiz_data["scores"][user_id]["score"]
                
                # Add XP
                guild_id = quiz_data.get("guild_id", message.guild.id)
                await add_xp(guild_id, user_id, message.author.display_name, XP_REWARDS["quiz_correct"], message.channel)
                increment_stats(guild_id, user_id, correct=True)
                
                embed = discord.Embed(
                    title="🎉 SPRÁVNĚ!",
                    description=f"**{message.author.display_name}** uhodl/a!",
                    color=discord.Color.green()
                )
                embed.add_field(name="🎤 Interpret", value=quiz_data["current_question"]["artist"], inline=True)
                embed.add_field(name="🎵 Píseň", value=quiz_data["current_question"]["song"], inline=True)
                embed.add_field(name="📊 Skóre", value=f"{current_score} bodů", inline=True)
                embed.add_field(name="✨ XP", value=f"+{XP_REWARDS['quiz_correct']} XP", inline=True)
                embed.set_thumbnail(url=message.author.display_avatar.url)
                
                await message.channel.send(f"🏆 {message.author.mention}", embed=embed)
    
    await bot.process_commands(message)

# ============== RUN BOT ==============

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_BOT_TOKEN není nastaven!", flush=True)
        exit(1)
    
    print("⚔️ Spouštím Valhalla Bot...", flush=True)
    bot.run(token)
