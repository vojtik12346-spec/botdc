# Discord Bot - PRD (Product Requirements Document)

## Original Problem Statement
"Bot s otázkami a matematickou minihrou" - Build a Discord quiz bot with questions and games

## User Requirements
1. Discord bot (NOT web app)
2. Quiz games with multiple categories
3. All texts in Czech
4. Both slash commands AND prefix commands
5. Web dashboard for bot management

## Architecture
- **Discord Bot**: discord.py with slash commands
- **Backend API**: FastAPI for web dashboard
- **Database**: MongoDB for sessions
- **Service**: Runs via supervisor

## What's Been Implemented (Feb 2026)

### Discord Bot Commands
| Slash | Prefix | Popis |
|-------|--------|-------|
| `/odpocet [čas] [důvod]` | `!odpocet` | Spustí odpočet |
| `/poll [otázka] [možnosti] [čas]` | `!poll` | Vytvoří anketu |
| `/hudba [žánr]` | `!hudba` | Hudební kvíz (rap, pop, rock, classic) |
| `/film [žánr]` | `!film` | Filmový kvíz (české, hollywood, komedie, akční, horor, scifi) |
| `/hudba-nastaveni` | - | Admin nastavení kvízu (čas, počet kol) |
| `/stop` | `!stop` | Zastaví běžící kvíz |
| `/help` | `!pomoc` | Nápověda |

### Implemented Features
- [x] Odpočet s ping notifikací a možností zrušení
- [x] Ankety s tlačítky, živými výsledky a jmény hlasujících
- [x] Hudební kvíz - hádej interpreta podle textu (169+ českých písní)
- [x] **Filmový kvíz** - hádej film podle hlášky (100+ filmů v 6 žánrech)
- [x] Web dashboard s Discord OAuth přihlášením
- [x] Slash i prefix příkazy

### Film Quiz Categories
- České filmy (Pelíšky, Samotáři, Kolja...)
- Hollywood (Titanic, Star Wars, Forrest Gump...)
- Komedie (Shrek, Austin Powers, Ace Ventura...)
- Akční (Terminátor, Smrtonosná past, Avengers...)
- Horor (Vřískot, To, Poltergeist...)
- Sci-Fi (Matrix, Interstellar, Blade Runner...)

## Technical Details
- **Bot Name**: Vlastni bot#6953
- **Connected Servers**: 2
- **Slash Commands**: 7 synchronized

## Key Files
- `/app/backend/discord_bot.py` - Discord bot logic
- `/app/backend/server.py` - FastAPI web dashboard API
- `/app/frontend/src/App.js` - Web dashboard UI

## Next Tasks
1. Rozšířit databázi filmů
2. Přidat nastavení filmového kvízu do dashboardu
3. Denní výzvy a streak bonusy
4. Více herních módů (např. rychlé kolo)
5. Statistiky hráčů a serveru

## Known Limitations
- Quiz state is stored in memory (resets on bot restart)
- Quiz settings are per-guild but also in memory
