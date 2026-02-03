#!/usr/bin/env python3
"""
Discord Countdown Bot
- Odpočet s ping notifikací
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import re
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import uuid

load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

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
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synchronizováno {len(synced)} slash příkazů', flush=True)
    except Exception as e:
        print(f'❌ Chyba při synchronizaci: {e}', flush=True)

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
        title="🤖 Bot Příkazy",
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
        name="⏱️ Formáty času",
        value="`30s`, `2m`, `1h`, `1d`",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="pomoc")
async def prefix_help(ctx):
    """!pomoc - Zobraz nápovědu"""
    embed = discord.Embed(
        title="🤖 Bot Příkazy",
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
        name="📊 Ankety",
        value="`!poll 5m Otázka? | Možnost1, Možnost2`",
        inline=False
    )
    embed.add_field(
        name="🎵 Hudební kvíz",
        value="`!hudba [rap/pop/rock/classic]`",
        inline=False
    )
    await ctx.send(embed=embed)

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
        {"lyrics": "Hele, víš co? Uděláme si to po svým", "artist": "Yzomandias", "song": "Po svým", "hint": "Y_______"},
        {"lyrics": "Můj svět je šedej, ale nebe je modrý", "artist": "Viktor Sheen", "song": "Barvy", "hint": "Viktor S____"},
        {"lyrics": "Jednou budem všichni v zemi, užij si ten den", "artist": "Calin", "song": "Jednou", "hint": "C____"},
        {"lyrics": "Mám v kapse pár stovek a to mi stačí", "artist": "Nik Tendo", "song": "Stovky", "hint": "Nik T____"},
        {"lyrics": "Přišel jsem z ničeho, teď mám všechno", "artist": "Yzomandias", "song": "Z ničeho", "hint": "Y_______"},
        {"lyrics": "Nemám čas na fake love, mám čas na real shit", "artist": "Viktor Sheen", "song": "Real Shit", "hint": "Viktor S____"},
        {"lyrics": "Začínal jsem dole, teď jsem nahoře", "artist": "Sergei Barracuda", "song": "Nahoře", "hint": "Sergei B_______"},
        {"lyrics": "Celej život makám, žádnej oddech", "artist": "Hasan", "song": "Makám", "hint": "H____"},
        {"lyrics": "V hlavě mám démony, co mě ženou dál", "artist": "Nik Tendo", "song": "Démoni", "hint": "Nik T____"},
        {"lyrics": "Jsem král svýho světa, nikdo mi neporučí", "artist": "Calin", "song": "Král", "hint": "C____"},
        {"lyrics": "Prodávám sny, lidi kupujou", "artist": "Yzomandias", "song": "Sny", "hint": "Y_______"},
        {"lyrics": "Neřeším co říkaj, dělám svý", "artist": "Nik Tendo", "song": "Svý", "hint": "Nik T____"},
        {"lyrics": "Zlatý časy, stříbrný vzpomínky", "artist": "Viktor Sheen", "song": "Zlatý časy", "hint": "Viktor S____"},
        {"lyrics": "Money na mým stole, stress v mojí hlavě", "artist": "Calin", "song": "Money", "hint": "C____"},
        {"lyrics": "Celej block ví, že jsem number one", "artist": "Yzomandias", "song": "Block", "hint": "Y_______"},
        {"lyrics": "Každej den hustluju, to je můj život", "artist": "Sergei Barracuda", "song": "Hustle", "hint": "Sergei B_______"},
        {"lyrics": "Mám stack v kapse, flex na maximum", "artist": "Nik Tendo", "song": "Stack", "hint": "Nik T____"},
        {"lyrics": "Noční město svítí, já jdu za svým", "artist": "Viktor Sheen", "song": "Noční město", "hint": "Viktor S____"},
        {"lyrics": "Ztracený v hudbě, našel jsem se v ní", "artist": "Hasan", "song": "Hudba", "hint": "H____"},
        {"lyrics": "Dream team, my jsme ti nejlepší", "artist": "Calin", "song": "Dream team", "hint": "C____"},
    ],
    "pop": [
        {"lyrics": "Holky z naší školky, chtěly by mě zpátky", "artist": "Mirai", "song": "Holky z naší školky", "hint": "M____"},
        {"lyrics": "Když nemůžeš spát a myslíš na mě", "artist": "Slza", "song": "Když nemůžeš spát", "hint": "S___"},
        {"lyrics": "Půlnoční vlak mě veze domů", "artist": "Pokáč", "song": "Půlnoční", "hint": "P____"},
        {"lyrics": "Já vím, že ty víš, že já vím", "artist": "Ewa Farna", "song": "Ty víš", "hint": "Ewa F____"},
        {"lyrics": "Máme se rádi, tak proč to kazit", "artist": "Slza", "song": "Máme se rádi", "hint": "S___"},
        {"lyrics": "Celá léta jsem hledal tu pravou", "artist": "Marek Ztracený", "song": "Léta", "hint": "Marek Z_______"},
        {"lyrics": "Na konci dne to bude dobrý", "artist": "Mirai", "song": "Dobrý", "hint": "M____"},
        {"lyrics": "Nikdy nevíš, co ti život přinese", "artist": "Ewa Farna", "song": "Nevíš", "hint": "Ewa F____"},
        {"lyrics": "Tancuj, tancuj, dokud můžeš", "artist": "Pokáč", "song": "Tancuj", "hint": "P____"},
        {"lyrics": "Slunce svítí, svět je krásnej", "artist": "Mirai", "song": "Slunce", "hint": "M____"},
        {"lyrics": "Věřím na zázraky, věřím na nás", "artist": "Slza", "song": "Zázraky", "hint": "S___"},
        {"lyrics": "Láska je válka, my jsme vojáci", "artist": "Ewa Farna", "song": "Válka", "hint": "Ewa F____"},
        {"lyrics": "Společně až na konec světa", "artist": "Marek Ztracený", "song": "Společně", "hint": "Marek Z_______"},
        {"lyrics": "Každý ráno vstávám s úsměvem", "artist": "Pokáč", "song": "Ráno", "hint": "P____"},
        {"lyrics": "Padám, vstávám, jdu dál", "artist": "Mirai", "song": "Padám", "hint": "M____"},
    ],
    "rock": [
        {"lyrics": "Až mě jednou potkáš, budu jinej člověk", "artist": "Kryštof", "song": "Jinej člověk", "hint": "K______"},
        {"lyrics": "Sním svůj sen a nechci se probudit", "artist": "Kabát", "song": "Sním svůj sen", "hint": "K____"},
        {"lyrics": "Dívám se na hvězdy a přemýšlím", "artist": "Chinaski", "song": "Hvězdy", "hint": "C______"},
        {"lyrics": "Pojď blíž, pojď blíž ke mně", "artist": "Lucie", "song": "Pojď blíž", "hint": "L____"},
        {"lyrics": "Máma mi vždycky říkala, ať si dávám pozor", "artist": "Kabát", "song": "Máma", "hint": "K____"},
        {"lyrics": "Běžím po ulici a nevím kam", "artist": "Kryštof", "song": "Běžím", "hint": "K______"},
        {"lyrics": "Chci žít svůj život naplno", "artist": "Chinaski", "song": "Naplno", "hint": "C______"},
        {"lyrics": "Amerika je daleko, ale sny jsou blízko", "artist": "Lucie", "song": "Amerika", "hint": "L____"},
        {"lyrics": "Malá bílá vrána letí k obloze", "artist": "Kabát", "song": "Bílá vrána", "hint": "K____"},
        {"lyrics": "Zůstaň se mnou ještě chvíli", "artist": "Kryštof", "song": "Zůstaň", "hint": "K______"},
        {"lyrics": "Cestou na jih, kde slunce zapadá", "artist": "Chinaski", "song": "Na jih", "hint": "C______"},
        {"lyrics": "Černý andělé hlídaj můj sen", "artist": "Lucie", "song": "Černý andělé", "hint": "L____"},
        {"lyrics": "Kdo nekrade, ten má", "artist": "Kabát", "song": "Kdo nekrade", "hint": "K____"},
        {"lyrics": "Dnes ještě ne, zítra možná jo", "artist": "Kryštof", "song": "Zítra", "hint": "K______"},
        {"lyrics": "Rock and roll je mrtvej, ale my hrajem dál", "artist": "Chinaski", "song": "Rock and roll", "hint": "C______"},
    ],
    "classic": [
        {"lyrics": "Lady Carneval, tančí dál a dál", "artist": "Karel Gott", "song": "Lady Carneval", "hint": "Karel G___"},
        {"lyrics": "Včelka Mája, ta si létá", "artist": "Karel Gott", "song": "Včelka Mája", "hint": "Karel G___"},
        {"lyrics": "Holubí dům, tam kde jsem doma", "artist": "Waldemar Matuška", "song": "Holubí dům", "hint": "Waldemar M______"},
        {"lyrics": "Jožin z bažin měří přes dva metry", "artist": "Ivan Mládek", "song": "Jožin z bažin", "hint": "Ivan M_____"},
        {"lyrics": "Být stále mlád, to není žádnej věk", "artist": "Marta Kubišová", "song": "Být stále mlád", "hint": "Marta K______"},
        {"lyrics": "Těžkej den, všechno je špatně", "artist": "Olympic", "song": "Těžkej den", "hint": "O______"},
        {"lyrics": "Lásko voníš deštěm", "artist": "Karel Gott", "song": "Lásko", "hint": "Karel G___"},
        {"lyrics": "Když milenky pláčou, pláče celý svět", "artist": "Karel Gott", "song": "Když milenky pláčou", "hint": "Karel G___"},
        {"lyrics": "Rosa na kolejích, vlak co nejede", "artist": "Waldemar Matuška", "song": "Rosa na kolejích", "hint": "Waldemar M______"},
        {"lyrics": "Koukej, támhle finišuje báječnej chlap", "artist": "Ivan Mládek", "song": "Báječnej chlap", "hint": "Ivan M_____"},
        {"lyrics": "Modlitba pro Martu", "artist": "Marta Kubišová", "song": "Modlitba pro Martu", "hint": "Marta K______"},
        {"lyrics": "Dej mi víc své lásky", "artist": "Olympic", "song": "Dej mi víc", "hint": "O______"},
        {"lyrics": "Pane prezidente, kam to jdete", "artist": "Karel Kryl", "song": "Pane prezidente", "hint": "Karel K___"},
        {"lyrics": "Bratříčku zavírej vrátka", "artist": "Karel Kryl", "song": "Bratříčku", "hint": "Karel K___"},
        {"lyrics": "Okno mé lásky, zavři za sebou", "artist": "Karel Gott", "song": "Okno mé lásky", "hint": "Karel G___"},
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
        
        # Wait for answer or timeout
        await asyncio.sleep(quiz_time)
        
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
async def prefix_hudba(ctx, zanr: str = "random"):
    """!hudba [rap/pop/rock/classic/random] - Hudební kvíz"""
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

@bot.command(name="stop", aliases=["stophudba"])
async def stop_quiz(ctx):
    """!stop - Zastav hudební kvíz"""
    channel_id = ctx.channel.id
    if channel_id in active_music_quiz:
        del active_music_quiz[channel_id]
        await ctx.send("🛑 Kvíz zastaven!")
    else:
        await ctx.send("❌ Žádný kvíz neběží.")

# Listen for quiz answers
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    # Check if there's an active quiz
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
                
                embed = discord.Embed(
                    title="🎉 SPRÁVNĚ!",
                    description=f"**{message.author.display_name}** uhodl/a!",
                    color=discord.Color.green()
                )
                embed.add_field(name="🎤 Interpret", value=quiz_data["current_question"]["artist"], inline=True)
                embed.add_field(name="🎵 Píseň", value=quiz_data["current_question"]["song"], inline=True)
                embed.add_field(name="📊 Skóre", value=f"{current_score} bodů", inline=True)
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
    
    print("🚀 Spouštím Countdown Bot...", flush=True)
    bot.run(token)
