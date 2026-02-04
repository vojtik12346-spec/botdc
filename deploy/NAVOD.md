# ⚔️ Valhalla Bot - Návod na instalaci

## 📋 Přehled
Tento návod tě provede instalací Valhalla Bota na tvůj VPS.

**Tvůj VPS:**
- IP: 185.102.22.166
- User: administrator
- OS: Ubuntu 24.04

---

## 🚀 Krok 1: Připojení k VPS

Otevři terminál (CMD nebo PowerShell na Windows) a zadej:

```bash
ssh administrator@185.102.22.166
```

Zadej heslo: `BRpcOwwR`

---

## 🚀 Krok 2: Stažení a instalace

Po přihlášení zadej tyto příkazy (jeden po druhém):

```bash
# Přepni na root
sudo su

# Aktualizuj systém
apt-get update && apt-get upgrade -y

# Nainstaluj závislosti
apt-get install -y python3 python3-pip python3-venv ffmpeg git curl unzip

# Vytvoř složku pro bota
mkdir -p /opt/valhalla-bot
cd /opt/valhalla-bot

# Vytvoř Python prostředí
python3 -m venv venv
source venv/bin/activate

# Nainstaluj Python balíčky
pip install discord.py[voice] pymongo python-dotenv aiohttp PyNaCl yt-dlp
```

---

## 🚀 Krok 3: Instalace MongoDB

```bash
# Přidej MongoDB repozitář
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/ubuntu noble/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list

apt-get update
apt-get install -y mongodb-org

# Spusť MongoDB
systemctl start mongod
systemctl enable mongod
```

---

## 🚀 Krok 4: Nahrání souborů bota

Na svém počítači stáhni soubory bota a nahraj je na VPS.

**Možnost A - pomocí SCP (z tvého PC):**
```bash
scp discord_bot.py .env administrator@185.102.22.166:/opt/valhalla-bot/
```

**Možnost B - pomocí nano (přímo na VPS):**
```bash
cd /opt/valhalla-bot
nano discord_bot.py
# Vlož obsah souboru a ulož (Ctrl+X, Y, Enter)

nano .env
# Vlož obsah .env a ulož
```

---

## 🚀 Krok 5: Vytvoření systemd služby

```bash
# Vytvoř service soubor
nano /etc/systemd/system/valhalla-bot.service
```

Vlož tento obsah:
```ini
[Unit]
Description=Valhalla Discord Bot
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/valhalla-bot
Environment=PATH=/opt/valhalla-bot/venv/bin
ExecStart=/opt/valhalla-bot/venv/bin/python3 discord_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ulož (Ctrl+X, Y, Enter).

---

## 🚀 Krok 6: Spuštění bota

```bash
# Načti službu
systemctl daemon-reload

# Spusť bota
systemctl start valhalla-bot

# Povol automatický start
systemctl enable valhalla-bot

# Zkontroluj status
systemctl status valhalla-bot
```

---

## ✅ Hotovo!

Bot by měl nyní běžet 24/7. 

**Užitečné příkazy:**
```bash
# Zobraz status
systemctl status valhalla-bot

# Zobraz logy
journalctl -u valhalla-bot -f

# Restartuj bota
systemctl restart valhalla-bot

# Zastav bota
systemctl stop valhalla-bot
```

---

## ❓ Problémy?

1. **Bot se nespustí** - zkontroluj logy: `journalctl -u valhalla-bot -n 50`
2. **MongoDB nefunguje** - zkontroluj: `systemctl status mongod`
3. **FFmpeg chybí** - nainstaluj: `apt-get install ffmpeg`
