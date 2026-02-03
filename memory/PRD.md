# Discord Bot PRD - Kvízy a Herní Systém

## Původní požadavek
Vytvořit Discord bota s kvízy a herními funkcemi pro komunitu.

## Implementované funkce

### 🎮 Herní příkazy (HOTOVO)
- `/hudba [žánr]` - Hudební kvíz (25 XP za správnou odpověď)
- `/film [žánr]` - Filmový kvíz s 237 filmy (25 XP)
- `/pravda [kategorie]` - Pravda/Lež hra se 100 fakty (15 XP)

### 📊 XP a Level Systém (HOTOVO)
- `/gamelevel` - Zobrazí herní profil, level, XP, statistiky
- `/top` - Žebříček TOP 10 hráčů
- `/daily` - Denní bonus +100 XP + streak bonus
- Automatické XP za správné odpovědi v kvízech
- Level up notifikace

### 🕹️ Sledování herní aktivity (HOTOVO)
- Automatické XP za hraní her na PC (5 XP/10 min, max 200 XP/den)
- Bonus 25 XP za odemčení nové hry
- `/hry` - Seznam odemčených her a čas hraní
- `/ukoly [hra]` - Úkoly pro konkrétní hru s XP odměnami

### 🔧 Administrace (HOTOVO)
- Kvízy omezeny pouze pro administrátory
- `!herniinfo` - Trvalá zpráva s přehledem příkazů do kanálu
- `!prikazy` - Kompletní přehled všech příkazů
- Automatické mazání odpovědí po 1 minutě
- Všechny herní notifikace do kanálu `1468355022159872073`
- Ping role `485172457544744972` při herních úspěších

## Architektura

```
/app/backend/
├── discord_bot.py    # Hlavní bot (monolit)
├── server.py         # FastAPI server
└── .env             # Konfigurace
```

## Databáze (MongoDB)
- Collection: `game_users`
- Struktura: user_id, guild_id, xp, level, streak, game_times, unlocked_games, completed_quests

## Budoucí úkoly (Backlog)
- [ ] Emoji kvíz (`/emoji`)
- [ ] Matematický kvíz (`/matika`)
- [ ] Hádání hlavních měst (`/zeme`)
- [ ] Refaktoring do Cogs modulů

## Changelog
- 2025-01: Přidán příkaz `!herniinfo` pro trvalou zprávu s herními příkazy
- 2025-01: Změna mazání odpovědí z 5 min na 1 minutu
- 2025-01: Oprava směrování notifikací do správného kanálu
- 2025-01: Filmový kvíz rozšířen na 237 filmů
- 2025-01: Implementován systém úkolů pro hry
