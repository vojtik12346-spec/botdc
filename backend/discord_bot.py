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
        title="⏰ Countdown Bot",
        description="Příkazy pro odpočet:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Použití",
        value="""
`/odpocet [čas] [důvod]` - Spusť odpočet
`!odpocet [čas] [důvod]` - Prefix verze
        """,
        inline=False
    )
    embed.add_field(
        name="Formáty času",
        value="""
`30s` - 30 sekund
`2m` - 2 minuty
`1h` - 1 hodina
`1d` - 1 den
        """,
        inline=False
    )
    embed.add_field(
        name="Příklady",
        value="""
`/odpocet 5m`
`/odpocet 1h Soutěž začíná!`
`!odpocet 30s Rychlý odpočet`
        """,
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name="pomoc")
async def prefix_help(ctx):
    """!pomoc - Zobraz nápovědu"""
    embed = discord.Embed(
        title="⏰ Countdown Bot",
        description="Příkazy pro odpočet:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Použití",
        value="`!odpocet [čas] [důvod]`",
        inline=False
    )
    embed.add_field(
        name="Formáty",
        value="`30s`, `2m`, `1h`, `1d`",
        inline=False
    )
    await ctx.send(embed=embed)

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
