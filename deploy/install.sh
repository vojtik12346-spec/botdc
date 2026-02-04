#!/bin/bash
# Valhalla Bot - Instalační skript
# Spusť jako: sudo bash install.sh

echo "⚔️ Valhalla Bot - Instalace"
echo "================================"

# Update systému
echo "📦 Aktualizuji systém..."
apt-get update
apt-get upgrade -y

# Instalace závislostí
echo "📦 Instaluji závislosti..."
apt-get install -y python3 python3-pip python3-venv ffmpeg git curl

# Instalace MongoDB
echo "📦 Instaluji MongoDB..."
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list
apt-get update
apt-get install -y mongodb-org
systemctl start mongod
systemctl enable mongod

# Vytvoření složky pro bota
echo "📁 Vytvářím složky..."
mkdir -p /opt/valhalla-bot
cd /opt/valhalla-bot

# Vytvoření virtuálního prostředí
echo "🐍 Vytvářím Python prostředí..."
python3 -m venv venv
source venv/bin/activate

# Instalace Python balíčků
echo "📦 Instaluji Python balíčky..."
pip install --upgrade pip
pip install discord.py[voice] pymongo python-dotenv aiohttp PyNaCl yt-dlp

echo ""
echo "✅ Základní instalace dokončena!"
echo ""
echo "📋 Další kroky:"
echo "1. Nahraj soubory bota do /opt/valhalla-bot/"
echo "2. Uprav soubor .env s tvými tokeny"
echo "3. Spusť: sudo systemctl start valhalla-bot"
echo ""
