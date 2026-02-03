# Quiz Bot - PRD (Product Requirements Document)

## Original Problem Statement
"Udelame bot Otazkama a matematika minihra" - Build a Discord quiz bot with questions and math mini-game

## User Requirements
1. Discord bot (NOT web app)
2. Combination of quiz questions + math problems
3. All types of math (calculations, equations, puzzles) with time limit
4. Own XP system with leaderboard (Mee6 API is not public)
5. Both slash commands AND prefix commands
6. Direct XP giving via /givexp command

## Architecture
- **Discord Bot**: discord.py with slash commands
- **Database**: MongoDB for XP/user tracking
- **Service**: Runs via supervisor

## What's Been Implemented (Feb 2026)
- [x] Discord bot online (`Vlastni bot#6953`)
- [x] `/quiz` - Kvízové otázky (easy/medium/hard)
- [x] `/math` - Matematika (calc/equation/puzzle)
- [x] `/leaderboard` - Žebříček serveru
- [x] `/profile` - Profil hráče
- [x] `/givexp` - Admin příkaz pro dávání XP
- [x] `/help` - Nápověda
- [x] Prefix příkazy: `!quiz`, `!math`, `!lb`, `!profile`, `!givexp`
- [x] XP systém s levely (100 XP = 1 level)
- [x] Interaktivní tlačítka pro odpovědi
- [x] Časovač pro každou otázku

## Bot Commands
| Slash | Prefix | Popis |
|-------|--------|-------|
| `/quiz [obtížnost]` | `!quiz [easy/medium/hard]` | Kvízová otázka |
| `/math [typ] [obtížnost]` | `!math [calc/equation/puzzle]` | Matematika |
| `/leaderboard` | `!lb`, `!top` | Žebříček |
| `/profile [@user]` | `!profile`, `!p` | Profil |
| `/givexp @user amount` | `!givexp` | Dej XP (admin) |
| `/help` | `!pomoc` | Nápověda |

## XP Rewards
- Easy: +10 XP
- Medium: +25 XP  
- Hard: +50 XP
- Level up: každých 100 XP

## Next Tasks
1. Přidat AI generované otázky (OpenAI)
2. Denní výzvy
3. Více kategorií kvízu
4. Streak bonusy
