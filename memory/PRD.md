# Quiz Bot - PRD (Product Requirements Document)

## Original Problem Statement
"Udelame bot Otazkama a matematika minihra" - Build a quiz bot with questions and math mini-game

## User Requirements
1. Combination of quiz questions + math problems
2. All types of math (calculations, equations, puzzles) with time limit
3. Scoring system, leaderboard, /give-xp command for Mee6 integration
4. Dark cyber-arcade theme ("hodne vypadaci vzhled")
5. AI-generated questions using OpenAI GPT

## User Personas
- **Discord gamers**: Want fun quizzes with XP rewards
- **Students**: Practice math and general knowledge
- **Community moderators**: Use Mee6 /give-xp commands to reward players

## Architecture
- **Backend**: FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + shadcn/ui
- **AI**: OpenAI GPT-5.2 via Emergent LLM Key

## What's Been Implemented (Feb 2026)
- [x] Landing page with Quiz/Math game selection
- [x] User registration and session management
- [x] Quiz game with 15 questions (easy/medium/hard)
- [x] Math mini-game (calculations, equations, puzzles)
- [x] Timer for each question (15-30s based on difficulty)
- [x] XP reward system (10/25/50 XP)
- [x] /give-xp Mee6 command generation
- [x] Leaderboard with top players
- [x] AI question generation toggle
- [x] Cyber-arcade dark theme with neon glows

## API Endpoints
- POST `/api/users` - Create user
- GET `/api/users/{id}` - Get user
- POST `/api/questions/generate` - Generate question
- POST `/api/questions/generate-ai` - AI-generated question
- POST `/api/questions/answer` - Submit answer
- GET `/api/leaderboard` - Get leaderboard

## Prioritized Backlog
### P0 (Critical)
- All core features implemented ✅

### P1 (High)
- Discord bot integration (actual bot instead of web app)
- Multiplayer real-time mode

### P2 (Medium)
- More question categories
- Custom question sets
- User achievements/badges
- Sound effects and music

## Next Tasks
1. Integrate as actual Discord bot using discord.py
2. Add more quiz categories (sports, movies, music)
3. Implement daily challenges
4. Add streak bonuses
