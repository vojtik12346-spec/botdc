#!/usr/bin/env python3
"""
Discord Quiz & Math Bot
- Quiz otázky a matematické minihry
- Vlastní XP systém s žebříčkem
- Slash i prefix příkazy
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import uuid

load_dotenv()

# MongoDB setup
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'quiz_bot')
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[db_name]

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ============== QUIZ DATA ==============

QUIZ_QUESTIONS = {
    "easy": [
        {"q": "Kolik má rok měsíců?", "options": ["10", "11", "12", "13"], "answer": "12"},
        {"q": "Jaké je hlavní město České republiky?", "options": ["Brno", "Praha", "Ostrava", "Plzeň"], "answer": "Praha"},
        {"q": "Kolik nohou má pavouk?", "options": ["6", "8", "10", "4"], "answer": "8"},
        {"q": "Jaká barva vznikne smícháním modré a žluté?", "options": ["Oranžová", "Zelená", "Fialová", "Hnědá"], "answer": "Zelená"},
        {"q": "Kolik dní má týden?", "options": ["5", "6", "7", "8"], "answer": "7"},
        {"q": "Kolik minut má hodina?", "options": ["30", "60", "90", "100"], "answer": "60"},
        {"q": "Jaké zvíře říká 'haf'?", "options": ["Kočka", "Pes", "Kráva", "Prase"], "answer": "Pes"},
    ],
    "medium": [
        {"q": "Ve kterém roce padla Berlínská zeď?", "options": ["1987", "1989", "1991", "1985"], "answer": "1989"},
        {"q": "Jaká je chemická značka zlata?", "options": ["Ag", "Au", "Fe", "Cu"], "answer": "Au"},
        {"q": "Kdo napsal Hamleta?", "options": ["Dickens", "Shakespeare", "Goethe", "Čapek"], "answer": "Shakespeare"},
        {"q": "Kolik kostí má dospělý člověk?", "options": ["186", "206", "226", "256"], "answer": "206"},
        {"q": "Jaká planeta je nejblíže Slunci?", "options": ["Venuše", "Mars", "Merkur", "Země"], "answer": "Merkur"},
        {"q": "Kolik strun má klasická kytara?", "options": ["4", "5", "6", "7"], "answer": "6"},
        {"q": "Jaký je nejdelší řeka světa?", "options": ["Amazonka", "Nil", "Dunaj", "Mississippi"], "answer": "Nil"},
    ],
    "hard": [
        {"q": "V jakém roce byla založena OSN?", "options": ["1942", "1945", "1948", "1950"], "answer": "1945"},
        {"q": "Jaká je nejvyšší hora Afriky?", "options": ["Mount Kenya", "Kilimandžáro", "Mount Stanley", "Atlas"], "answer": "Kilimandžáro"},
        {"q": "Kolik planet ve sluneční soustavě má prstence?", "options": ["1", "2", "3", "4"], "answer": "4"},
        {"q": "Jaký prvek má atomové číslo 79?", "options": ["Stříbro", "Platina", "Zlato", "Měď"], "answer": "Zlato"},
        {"q": "Kdo formuloval teorii relativity?", "options": ["Newton", "Einstein", "Hawking", "Bohr"], "answer": "Einstein"},
        {"q": "Kolik chromosomů má člověk?", "options": ["23", "46", "48", "44"], "answer": "46"},
    ]
}

# ============== MATH GENERATORS ==============

def generate_math_calc(difficulty: str) -> dict:
    if difficulty == "easy":
        a, b = random.randint(1, 20), random.randint(1, 20)
        op = random.choice(["+", "-"])
    elif difficulty == "medium":
        a, b = random.randint(10, 50), random.randint(1, 20)
        op = random.choice(["+", "-", "*"])
    else:
        a, b = random.randint(20, 100), random.randint(2, 15)
        op = random.choice(["+", "-", "*", "//"])
    
    if op == "+":
        answer = a + b
        question = f"{a} + {b} = ?"
    elif op == "-":
        if a < b: a, b = b, a
        answer = a - b
        question = f"{a} - {b} = ?"
    elif op == "*":
        answer = a * b
        question = f"{a} × {b} = ?"
    else:
        a = b * random.randint(2, 10)
        answer = a // b
        question = f"{a} ÷ {b} = ?"
    
    options = [str(answer)]
    while len(options) < 4:
        fake = answer + random.randint(-10, 10)
        if fake != answer and str(fake) not in options and fake >= 0:
            options.append(str(fake))
    random.shuffle(options)
    return {"q": question, "options": options, "answer": str(answer)}

def generate_math_equation(difficulty: str) -> dict:
    if difficulty == "easy":
        x = random.randint(1, 10)
        b = random.randint(1, 10)
        result = x + b
        question = f"x + {b} = {result}, x = ?"
    elif difficulty == "medium":
        x = random.randint(2, 12)
        a = random.randint(2, 5)
        result = a * x
        question = f"{a}x = {result}, x = ?"
    else:
        x = random.randint(1, 10)
        a = random.randint(2, 5)
        b = random.randint(1, 10)
        result = a * x + b
        question = f"{a}x + {b} = {result}, x = ?"
    
    options = [str(x)]
    while len(options) < 4:
        fake = x + random.randint(-5, 5)
        if fake != x and str(fake) not in options and fake > 0:
            options.append(str(fake))
    random.shuffle(options)
    return {"q": question, "options": options, "answer": str(x)}

def generate_math_puzzle(difficulty: str) -> dict:
    puzzles = {
        "easy": [
            {"q": "Jaké číslo následuje: 2, 4, 6, 8, ?", "options": ["9", "10", "11", "12"], "answer": "10"},
            {"q": "5 + 5 ÷ 5 = ?", "options": ["2", "6", "10", "1"], "answer": "6"},
            {"q": "Kolik je polovina z 50?", "options": ["20", "25", "30", "15"], "answer": "25"},
        ],
        "medium": [
            {"q": "Jaké číslo následuje: 1, 1, 2, 3, 5, 8, ?", "options": ["11", "12", "13", "14"], "answer": "13"},
            {"q": "3² + 4² = ?", "options": ["12", "25", "49", "7"], "answer": "25"},
            {"q": "√144 = ?", "options": ["10", "11", "12", "14"], "answer": "12"},
        ],
        "hard": [
            {"q": "Jaké číslo následuje: 2, 6, 12, 20, 30, ?", "options": ["40", "42", "44", "46"], "answer": "42"},
            {"q": "2⁵ = ?", "options": ["16", "32", "64", "25"], "answer": "32"},
            {"q": "Kolik je 15% z 200?", "options": ["25", "30", "35", "40"], "answer": "30"},
        ]
    }
    return random.choice(puzzles[difficulty])

# ============== XP SYSTEM ==============

XP_REWARDS = {"easy": 10, "medium": 25, "hard": 50}
TIME_LIMITS = {"easy": 30, "medium": 20, "hard": 15}

async def get_or_create_user(user_id: int, username: str, guild_id: int):
    user = await db.users.find_one({"user_id": user_id, "guild_id": guild_id}, {"_id": 0})
    if not user:
        user = {
            "user_id": user_id,
            "guild_id": guild_id,
            "username": username,
            "xp": 0,
            "level": 1,
            "games_played": 0,
            "correct_answers": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user)
    return user

async def add_xp(user_id: int, guild_id: int, xp_amount: int):
    user = await db.users.find_one({"user_id": user_id, "guild_id": guild_id})
    if user:
        new_xp = user.get("xp", 0) + xp_amount
        new_level = 1 + (new_xp // 100)  # Level up every 100 XP
        await db.users.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {"$set": {"xp": new_xp, "level": new_level}, "$inc": {"correct_answers": 1}}
        )
        level_up = new_level > user.get("level", 1)
        return new_xp, new_level, level_up
    return 0, 1, False

async def increment_games(user_id: int, guild_id: int):
    await db.users.update_one(
        {"user_id": user_id, "guild_id": guild_id},
        {"$inc": {"games_played": 1}}
    )

# ============== GAME VIEW (BUTTONS) ==============

class QuizView(discord.ui.View):
    def __init__(self, question_data: dict, difficulty: str, user_id: int, guild_id: int, game_type: str):
        super().__init__(timeout=TIME_LIMITS[difficulty])
        self.question_data = question_data
        self.difficulty = difficulty
        self.user_id = user_id
        self.guild_id = guild_id
        self.game_type = game_type
        self.answered = False
        self.message = None
        
        # Add buttons for each option
        for i, option in enumerate(question_data["options"]):
            button = discord.ui.Button(
                label=f"{chr(65+i)}. {option}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"option_{i}"
            )
            button.callback = self.make_callback(option)
            self.add_item(button)
    
    def make_callback(self, option: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Toto není tvá hra!", ephemeral=True)
                return
            
            if self.answered:
                await interaction.response.send_message("❌ Už jsi odpověděl!", ephemeral=True)
                return
            
            self.answered = True
            correct = option == self.question_data["answer"]
            
            # Update buttons to show result
            for child in self.children:
                child.disabled = True
                if self.question_data["answer"] in child.label:
                    child.style = discord.ButtonStyle.success
                elif option in child.label and not correct:
                    child.style = discord.ButtonStyle.danger
            
            if correct:
                xp_reward = XP_REWARDS[self.difficulty]
                new_xp, new_level, level_up = await add_xp(self.user_id, self.guild_id, xp_reward)
                
                result_text = f"✅ **SPRÁVNĚ!** +{xp_reward} XP\n"
                result_text += f"📊 Celkem XP: **{new_xp}** | Level: **{new_level}**"
                
                if level_up:
                    result_text += f"\n🎉 **LEVEL UP!** Jsi nyní level {new_level}!"
                
                embed = discord.Embed(
                    title="🎉 Správná odpověď!",
                    description=result_text,
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="❌ Špatná odpověď!",
                    description=f"Správná odpověď: **{self.question_data['answer']}**",
                    color=discord.Color.red()
                )
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(embed=embed)
            self.stop()
        
        return callback
    
    async def on_timeout(self):
        if not self.answered:
            for child in self.children:
                child.disabled = True
                if self.question_data["answer"] in child.label:
                    child.style = discord.ButtonStyle.success
            
            if self.message:
                try:
                    await self.message.edit(view=self)
                    embed = discord.Embed(
                        title="⏰ Čas vypršel!",
                        description=f"Správná odpověď: **{self.question_data['answer']}**",
                        color=discord.Color.orange()
                    )
                    await self.message.reply(embed=embed)
                except:
                    pass

# ============== COMMANDS ==============

@bot.event
async def on_ready():
    print(f'🤖 Bot {bot.user} je online!', flush=True)
    print(f'📊 Připojen k {len(bot.guilds)} serverům', flush=True)
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synchronizováno {len(synced)} slash příkazů', flush=True)
    except Exception as e:
        print(f'❌ Chyba při synchronizaci: {e}', flush=True)

# ---------- QUIZ COMMANDS ----------

async def start_quiz(ctx_or_interaction, difficulty: str = "medium"):
    """Start a quiz game"""
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_interaction:
        user = ctx_or_interaction.user
        guild_id = ctx_or_interaction.guild_id
        send = ctx_or_interaction.response.send_message
        followup = ctx_or_interaction.followup.send
    else:
        user = ctx_or_interaction.author
        guild_id = ctx_or_interaction.guild.id
        send = ctx_or_interaction.send
        followup = ctx_or_interaction.send
    
    await get_or_create_user(user.id, user.display_name, guild_id)
    await increment_games(user.id, guild_id)
    
    question_data = random.choice(QUIZ_QUESTIONS.get(difficulty, QUIZ_QUESTIONS["medium"]))
    
    embed = discord.Embed(
        title="🧠 KVÍZ",
        description=f"**{question_data['q']}**",
        color=discord.Color.purple()
    )
    embed.add_field(name="Obtížnost", value=difficulty.upper(), inline=True)
    embed.add_field(name="XP Reward", value=f"+{XP_REWARDS[difficulty]}", inline=True)
    embed.add_field(name="Čas", value=f"{TIME_LIMITS[difficulty]}s", inline=True)
    embed.set_footer(text=f"Hráč: {user.display_name}")
    
    view = QuizView(question_data, difficulty, user.id, guild_id, "quiz")
    
    if is_interaction:
        await send(embed=embed, view=view)
        msg = await ctx_or_interaction.original_response()
    else:
        msg = await send(embed=embed, view=view)
    
    view.message = msg

@bot.tree.command(name="quiz", description="Zahraj si kvíz!")
@app_commands.describe(difficulty="Vyber obtížnost")
@app_commands.choices(difficulty=[
    app_commands.Choice(name="Lehká", value="easy"),
    app_commands.Choice(name="Střední", value="medium"),
    app_commands.Choice(name="Těžká", value="hard"),
])
async def slash_quiz(interaction: discord.Interaction, difficulty: str = "medium"):
    await start_quiz(interaction, difficulty)

@bot.command(name="quiz", aliases=["kviz", "q"])
async def prefix_quiz(ctx, difficulty: str = "medium"):
    """!quiz [easy/medium/hard] - Zahraj si kvíz"""
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"
    await start_quiz(ctx, difficulty)

# ---------- MATH COMMANDS ----------

async def start_math(ctx_or_interaction, math_type: str = "calc", difficulty: str = "medium"):
    """Start a math game"""
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_interaction:
        user = ctx_or_interaction.user
        guild_id = ctx_or_interaction.guild_id
        send = ctx_or_interaction.response.send_message
    else:
        user = ctx_or_interaction.author
        guild_id = ctx_or_interaction.guild.id
        send = ctx_or_interaction.send
    
    await get_or_create_user(user.id, user.display_name, guild_id)
    await increment_games(user.id, guild_id)
    
    if math_type == "calc":
        question_data = generate_math_calc(difficulty)
        title = "🔢 POČÍTÁNÍ"
    elif math_type == "equation":
        question_data = generate_math_equation(difficulty)
        title = "📐 ROVNICE"
    else:
        question_data = generate_math_puzzle(difficulty)
        title = "🧩 HLAVOLAM"
    
    embed = discord.Embed(
        title=title,
        description=f"**{question_data['q']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Obtížnost", value=difficulty.upper(), inline=True)
    embed.add_field(name="XP Reward", value=f"+{XP_REWARDS[difficulty]}", inline=True)
    embed.add_field(name="Čas", value=f"{TIME_LIMITS[difficulty]}s", inline=True)
    embed.set_footer(text=f"Hráč: {user.display_name}")
    
    view = QuizView(question_data, difficulty, user.id, guild_id, "math")
    
    if is_interaction:
        await send(embed=embed, view=view)
        msg = await ctx_or_interaction.original_response()
    else:
        msg = await send(embed=embed, view=view)
    
    view.message = msg

@bot.tree.command(name="math", description="Zahraj si matematickou minihru!")
@app_commands.describe(
    typ="Typ matematické hry",
    difficulty="Vyber obtížnost"
)
@app_commands.choices(
    typ=[
        app_commands.Choice(name="Počítání", value="calc"),
        app_commands.Choice(name="Rovnice", value="equation"),
        app_commands.Choice(name="Hlavolam", value="puzzle"),
    ],
    difficulty=[
        app_commands.Choice(name="Lehká", value="easy"),
        app_commands.Choice(name="Střední", value="medium"),
        app_commands.Choice(name="Těžká", value="hard"),
    ]
)
async def slash_math(interaction: discord.Interaction, typ: str = "calc", difficulty: str = "medium"):
    await start_math(interaction, typ, difficulty)

@bot.command(name="math", aliases=["matematika", "m"])
async def prefix_math(ctx, math_type: str = "calc", difficulty: str = "medium"):
    """!math [calc/equation/puzzle] [easy/medium/hard] - Matematická minihra"""
    if math_type not in ["calc", "equation", "puzzle"]:
        math_type = "calc"
    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"
    await start_math(ctx, math_type, difficulty)

# ---------- LEADERBOARD COMMANDS ----------

async def show_leaderboard(ctx_or_interaction):
    """Show server leaderboard"""
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_interaction:
        guild_id = ctx_or_interaction.guild_id
        guild_name = ctx_or_interaction.guild.name
        send = ctx_or_interaction.response.send_message
    else:
        guild_id = ctx_or_interaction.guild.id
        guild_name = ctx_or_interaction.guild.name
        send = ctx_or_interaction.send
    
    users = await db.users.find(
        {"guild_id": guild_id},
        {"_id": 0}
    ).sort("xp", -1).limit(10).to_list(10)
    
    if not users:
        embed = discord.Embed(
            title="🏆 Žebříček",
            description="Zatím žádní hráči! Začni hrát s `/quiz` nebo `/math`",
            color=discord.Color.gold()
        )
        await send(embed=embed)
        return
    
    medals = ["🥇", "🥈", "🥉"]
    leaderboard_text = ""
    
    for i, user in enumerate(users):
        medal = medals[i] if i < 3 else f"**{i+1}.**"
        leaderboard_text += f"{medal} **{user['username']}** - {user['xp']} XP (Lv.{user['level']})\n"
    
    embed = discord.Embed(
        title=f"🏆 Žebříček - {guild_name}",
        description=leaderboard_text,
        color=discord.Color.gold()
    )
    embed.set_footer(text="Získej XP hraním /quiz a /math!")
    
    await send(embed=embed)

@bot.tree.command(name="leaderboard", description="Zobraz žebříček serveru")
async def slash_leaderboard(interaction: discord.Interaction):
    await show_leaderboard(interaction)

@bot.command(name="leaderboard", aliases=["lb", "top", "zebricek"])
async def prefix_leaderboard(ctx):
    """!leaderboard - Zobraz žebříček"""
    await show_leaderboard(ctx)

# ---------- PROFILE COMMAND ----------

async def show_profile(ctx_or_interaction, target_user=None):
    """Show user profile"""
    is_interaction = isinstance(ctx_or_interaction, discord.Interaction)
    
    if is_interaction:
        user = target_user or ctx_or_interaction.user
        guild_id = ctx_or_interaction.guild_id
        send = ctx_or_interaction.response.send_message
    else:
        user = target_user or ctx_or_interaction.author
        guild_id = ctx_or_interaction.guild.id
        send = ctx_or_interaction.send
    
    db_user = await db.users.find_one(
        {"user_id": user.id, "guild_id": guild_id},
        {"_id": 0}
    )
    
    if not db_user:
        embed = discord.Embed(
            title="❌ Profil nenalezen",
            description="Tento uživatel ještě nehrál! Začni s `/quiz` nebo `/math`",
            color=discord.Color.red()
        )
        await send(embed=embed)
        return
    
    xp_to_next = 100 - (db_user['xp'] % 100)
    progress = (db_user['xp'] % 100) / 100 * 100
    progress_bar = "█" * int(progress // 10) + "░" * (10 - int(progress // 10))
    
    embed = discord.Embed(
        title=f"📊 Profil - {user.display_name}",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="🎖️ Level", value=str(db_user['level']), inline=True)
    embed.add_field(name="⭐ XP", value=str(db_user['xp']), inline=True)
    embed.add_field(name="🎮 Her", value=str(db_user['games_played']), inline=True)
    embed.add_field(name="✅ Správných", value=str(db_user['correct_answers']), inline=True)
    
    accuracy = 0
    if db_user['games_played'] > 0:
        accuracy = round(db_user['correct_answers'] / db_user['games_played'] * 100, 1)
    embed.add_field(name="🎯 Úspěšnost", value=f"{accuracy}%", inline=True)
    embed.add_field(name="📈 Progress", value=f"`{progress_bar}` {xp_to_next} XP do levelu", inline=False)
    
    await send(embed=embed)

@bot.tree.command(name="profile", description="Zobraz svůj profil nebo profil jiného hráče")
@app_commands.describe(user="Uživatel k zobrazení (volitelné)")
async def slash_profile(interaction: discord.Interaction, user: discord.Member = None):
    await show_profile(interaction, user)

@bot.command(name="profile", aliases=["profil", "stats", "p"])
async def prefix_profile(ctx, user: discord.Member = None):
    """!profile [@user] - Zobraz profil"""
    await show_profile(ctx, user)

# ---------- GIVE XP COMMAND (ADMIN ONLY) ----------

@bot.tree.command(name="givexp", description="Dej XP hráči (pouze admin)")
@app_commands.describe(user="Komu dát XP", amount="Kolik XP")
@app_commands.default_permissions(administrator=True)
async def slash_givexp(interaction: discord.Interaction, user: discord.Member, amount: int):
    if amount <= 0 or amount > 1000:
        await interaction.response.send_message("❌ Množství musí být 1-1000 XP!", ephemeral=True)
        return
    
    await get_or_create_user(user.id, user.display_name, interaction.guild_id)
    new_xp, new_level, level_up = await add_xp(user.id, interaction.guild_id, amount)
    
    embed = discord.Embed(
        title="🎁 XP Uděleno!",
        description=f"{user.mention} dostal **+{amount} XP**!\n\nCelkem: **{new_xp} XP** | Level: **{new_level}**",
        color=discord.Color.green()
    )
    
    if level_up:
        embed.add_field(name="🎉 Level Up!", value=f"Nový level: **{new_level}**", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.command(name="givexp", aliases=["gxp"])
@commands.has_permissions(administrator=True)
async def prefix_givexp(ctx, user: discord.Member, amount: int):
    """!givexp @user amount - Dej XP hráči (admin)"""
    if amount <= 0 or amount > 1000:
        await ctx.send("❌ Množství musí být 1-1000 XP!")
        return
    
    await get_or_create_user(user.id, user.display_name, ctx.guild.id)
    new_xp, new_level, level_up = await add_xp(user.id, ctx.guild.id, amount)
    
    embed = discord.Embed(
        title="🎁 XP Uděleno!",
        description=f"{user.mention} dostal **+{amount} XP**!\n\nCelkem: **{new_xp} XP** | Level: **{new_level}**",
        color=discord.Color.green()
    )
    
    if level_up:
        embed.add_field(name="🎉 Level Up!", value=f"Nový level: **{new_level}**", inline=False)
    
    await ctx.send(embed=embed)

# ---------- HELP COMMAND ----------

@bot.tree.command(name="help", description="Zobraz seznam příkazů")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Quiz Bot - Příkazy",
        description="Všechny dostupné příkazy:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🎮 Hry",
        value="""
`/quiz [obtížnost]` - Kvízová otázka
`/math [typ] [obtížnost]` - Matematická minihra
        """,
        inline=False
    )
    
    embed.add_field(
        name="📊 Statistiky",
        value="""
`/leaderboard` - Žebříček serveru
`/profile [@user]` - Profil hráče
        """,
        inline=False
    )
    
    embed.add_field(
        name="👑 Admin",
        value="""
`/givexp @user amount` - Dej XP hráči
        """,
        inline=False
    )
    
    embed.add_field(
        name="⏰ Utility",
        value="""
`/odpocet [čas] [důvod]` - Spusť odpočet (např. 2m, 1h)
        """,
        inline=False
    )
    
    embed.add_field(
        name="💡 Prefix příkazy",
        value="Můžeš také použít `!` prefix: `!quiz`, `!math`, `!lb`, `!profile`",
        inline=False
    )
    
    embed.set_footer(text="Získej XP správnými odpověďmi a staň se #1!")
    
    await interaction.response.send_message(embed=embed)

@bot.command(name="pomoc", aliases=["commands", "prikazy"])
async def prefix_help_custom(ctx):
    """!pomoc - Zobraz příkazy"""
    embed = discord.Embed(
        title="📖 Quiz Bot - Příkazy",
        description="Prefix: `!`",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🎮 Hry",
        value="""
`!quiz [easy/medium/hard]` - Kvíz
`!math [calc/equation/puzzle] [obtížnost]` - Matematika
        """,
        inline=False
    )
    
    embed.add_field(
        name="📊 Statistiky",
        value="""
`!leaderboard` / `!lb` - Žebříček
`!profile` / `!p` - Profil
        """,
        inline=False
    )
    
    embed.add_field(
        name="👑 Admin",
        value="`!givexp @user amount` - Dej XP",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ---------- COUNTDOWN COMMAND ----------

import re

def parse_time(time_str: str) -> int:
    """Parse time string like 2m, 5m, 1h, 30s into seconds"""
    time_str = time_str.lower().strip()
    
    # Pattern: number followed by unit (s, m, h, d)
    pattern = r'^(\d+)([smhd])$'
    match = re.match(pattern, time_str)
    
    if not match:
        return None
    
    value = int(match.group(1))
    unit = match.group(2)
    
    multipliers = {
        's': 1,          # seconds
        'm': 60,         # minutes
        'h': 3600,       # hours
        'd': 86400       # days
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
            return  # Cancelled
        
        if active_countdowns[countdown_id].get("cancelled"):
            return
        
        remaining = end_time - int(datetime.now(timezone.utc).timestamp())
        
        if remaining <= 0:
            break
        
        # Update embed
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
        
        # Update interval based on remaining time
        if remaining > 3600:
            await asyncio.sleep(60)  # Update every minute for long countdowns
        elif remaining > 60:
            await asyncio.sleep(10)  # Update every 10 seconds
        else:
            await asyncio.sleep(1)   # Update every second for last minute
    
    # Countdown finished!
    if countdown_id in active_countdowns:
        del active_countdowns[countdown_id]
    
    # Final embed
    embed = discord.Embed(
        title="🎉 ODPOČET SKONČIL!",
        description=f"**{reason}**" if reason else "Čas vypršel!",
        color=discord.Color.green()
    )
    embed.add_field(name="👤 Spustil", value=author.mention, inline=True)
    
    # Disable button
    view = discord.ui.View()
    disabled_btn = discord.ui.Button(label="Dokončeno", style=discord.ButtonStyle.success, disabled=True, emoji="✅")
    view.add_item(disabled_btn)
    
    try:
        await message.edit(embed=embed, view=view)
    except:
        pass
    
    # Send ping notification
    await channel.send(f"🔔 **ODPOČET SKONČIL!** {author.mention}\n{'📢 ' + reason if reason else ''}")

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
    
    if seconds > 86400 * 7:  # Max 7 days
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
    
    # Start countdown task
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

# ============== RUN BOT ==============

if __name__ == "__main__":
    import sys
    # Force unbuffered output for supervisor
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
    
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ DISCORD_BOT_TOKEN není nastaven!", flush=True)
        exit(1)
    
    print("🚀 Spouštím Quiz Bot...", flush=True)
    bot.run(token)
