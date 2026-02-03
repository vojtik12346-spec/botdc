from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============== Models ==============

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    total_score: int = 0
    quiz_score: int = 0
    math_score: int = 0
    games_played: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str

class QuestionRequest(BaseModel):
    difficulty: str = "medium"  # easy, medium, hard
    question_type: str = "quiz"  # quiz, math_calc, math_equation, math_puzzle

class QuestionResponse(BaseModel):
    id: str
    question: str
    options: List[str]
    correct_answer: str
    difficulty: str
    question_type: str
    time_limit: int
    xp_reward: int

class AnswerSubmit(BaseModel):
    question_id: str
    user_id: str
    selected_answer: str
    time_taken: float

class AnswerResult(BaseModel):
    correct: bool
    correct_answer: str
    xp_earned: int
    mee6_command: str

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_score: int
    games_played: int

class GameSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    game_type: str
    score: int = 0
    questions_answered: int = 0
    correct_answers: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

# ============== Question Generation ==============

# Predefined quiz questions
QUIZ_QUESTIONS = {
    "easy": [
        {"q": "Kolik má rok měsíců?", "options": ["10", "11", "12", "13"], "answer": "12"},
        {"q": "Jaká je hlavní město České republiky?", "options": ["Brno", "Praha", "Ostrava", "Plzeň"], "answer": "Praha"},
        {"q": "Kolik nohou má pavouk?", "options": ["6", "8", "10", "4"], "answer": "8"},
        {"q": "Jaká barva vznikne smícháním modré a žluté?", "options": ["Oranžová", "Zelená", "Fialová", "Hnědá"], "answer": "Zelená"},
        {"q": "Kolik dní má týden?", "options": ["5", "6", "7", "8"], "answer": "7"},
    ],
    "medium": [
        {"q": "Ve kterém roce padla Berlínská zeď?", "options": ["1987", "1989", "1991", "1985"], "answer": "1989"},
        {"q": "Jaká je chemická značka zlata?", "options": ["Ag", "Au", "Fe", "Cu"], "answer": "Au"},
        {"q": "Kdo napsal Hamleta?", "options": ["Dickens", "Shakespeare", "Goethe", "Čapek"], "answer": "Shakespeare"},
        {"q": "Kolik kostí má dospělý člověk?", "options": ["186", "206", "226", "256"], "answer": "206"},
        {"q": "Jaká planeta je nejblíže Slunci?", "options": ["Venuše", "Mars", "Merkur", "Země"], "answer": "Merkur"},
    ],
    "hard": [
        {"q": "V jakém roce byla založena OSN?", "options": ["1942", "1945", "1948", "1950"], "answer": "1945"},
        {"q": "Jaká je nejvyšší hora Afriky?", "options": ["Mount Kenya", "Kilimandžáro", "Mount Stanley", "Atlas"], "answer": "Kilimandžáro"},
        {"q": "Kolik planet ve sluneční soustavě má prstence?", "options": ["1", "2", "3", "4"], "answer": "4"},
        {"q": "Jaký prvek má atomové číslo 79?", "options": ["Stříbro", "Platina", "Zlato", "Měď"], "answer": "Zlato"},
        {"q": "Kdo formuloval teorii relativity?", "options": ["Newton", "Einstein", "Hawking", "Bohr"], "answer": "Einstein"},
    ]
}

def generate_math_calc(difficulty: str) -> dict:
    """Generate calculation problems"""
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
        if a < b:
            a, b = b, a
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
    """Generate equation problems"""
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
    """Generate math puzzles"""
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

# Store active questions
active_questions = {}

def get_time_limit(difficulty: str) -> int:
    return {"easy": 30, "medium": 20, "hard": 15}.get(difficulty, 20)

def get_xp_reward(difficulty: str) -> int:
    return {"easy": 10, "medium": 25, "hard": 50}.get(difficulty, 25)

# ============== Routes ==============

@api_router.get("/")
async def root():
    return {"message": "Quiz Bot API"}

# User routes
@api_router.post("/users", response_model=User)
async def create_user(input: UserCreate):
    existing = await db.users.find_one({"username": input.username}, {"_id": 0})
    if existing:
        return User(**existing)
    
    user = User(username=input.username)
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.users.insert_one(doc)
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    return User(**user)

@api_router.get("/users/by-username/{username}", response_model=User)
async def get_user_by_username(username: str):
    user = await db.users.find_one({"username": username}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    return User(**user)

# Question routes
@api_router.post("/questions/generate", response_model=QuestionResponse)
async def generate_question(request: QuestionRequest):
    difficulty = request.difficulty
    q_type = request.question_type
    
    if q_type == "quiz":
        q_data = random.choice(QUIZ_QUESTIONS.get(difficulty, QUIZ_QUESTIONS["medium"]))
    elif q_type == "math_calc":
        q_data = generate_math_calc(difficulty)
    elif q_type == "math_equation":
        q_data = generate_math_equation(difficulty)
    elif q_type == "math_puzzle":
        q_data = generate_math_puzzle(difficulty)
    else:
        q_data = random.choice(QUIZ_QUESTIONS.get(difficulty, QUIZ_QUESTIONS["medium"]))
    
    question_id = str(uuid.uuid4())
    time_limit = get_time_limit(difficulty)
    xp_reward = get_xp_reward(difficulty)
    
    active_questions[question_id] = {
        "correct_answer": q_data["answer"],
        "difficulty": difficulty,
        "xp_reward": xp_reward
    }
    
    return QuestionResponse(
        id=question_id,
        question=q_data["q"],
        options=q_data["options"],
        correct_answer="",  # Don't send to client
        difficulty=difficulty,
        question_type=q_type,
        time_limit=time_limit,
        xp_reward=xp_reward
    )

@api_router.post("/questions/answer", response_model=AnswerResult)
async def submit_answer(answer: AnswerSubmit):
    q_info = active_questions.get(answer.question_id)
    if not q_info:
        raise HTTPException(status_code=404, detail="Question not found or expired")
    
    correct = answer.selected_answer == q_info["correct_answer"]
    xp_earned = q_info["xp_reward"] if correct else 0
    
    # Update user score
    if correct:
        await db.users.update_one(
            {"id": answer.user_id},
            {"$inc": {"total_score": xp_earned, "games_played": 1}}
        )
    
    # Generate Mee6 command
    mee6_command = f"/give-xp user:{answer.user_id} amount:{xp_earned}" if correct else ""
    
    # Clean up
    del active_questions[answer.question_id]
    
    return AnswerResult(
        correct=correct,
        correct_answer=q_info["correct_answer"],
        xp_earned=xp_earned,
        mee6_command=mee6_command
    )

# Leaderboard routes
@api_router.get("/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(limit: int = 10):
    users = await db.users.find({}, {"_id": 0}).sort("total_score", -1).limit(limit).to_list(limit)
    
    leaderboard = []
    for i, user in enumerate(users, 1):
        leaderboard.append(LeaderboardEntry(
            rank=i,
            username=user["username"],
            total_score=user["total_score"],
            games_played=user["games_played"]
        ))
    
    return leaderboard

# Game session routes
@api_router.post("/sessions/start")
async def start_session(user_id: str, game_type: str):
    session = GameSession(user_id=user_id, game_type=game_type)
    doc = session.model_dump()
    doc['started_at'] = doc['started_at'].isoformat()
    await db.game_sessions.insert_one(doc)
    return {"session_id": session.id}

@api_router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, score: int, correct: int, total: int):
    await db.game_sessions.update_one(
        {"id": session_id},
        {"$set": {
            "score": score,
            "correct_answers": correct,
            "questions_answered": total,
            "ended_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"status": "completed"}

# AI Question Generation (using Emergent LLM)
@api_router.post("/questions/generate-ai", response_model=QuestionResponse)
async def generate_ai_question(request: QuestionRequest):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        # Fallback to regular questions
        return await generate_question(request)
    
    difficulty = request.difficulty
    q_type = request.question_type
    
    prompts = {
        "quiz": f"Vygeneruj jednu {difficulty} obtížnosti kvízovou otázku v češtině. Vrať JSON: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct\": \"správná odpověď\"}}",
        "math_calc": f"Vygeneruj jeden {difficulty} obtížnosti matematický příklad na počítání v češtině. Vrať JSON: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct\": \"správná odpověď\"}}",
        "math_equation": f"Vygeneruj jednu {difficulty} obtížnosti rovnici k vyřešení. Vrať JSON: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct\": \"správná odpověď\"}}",
        "math_puzzle": f"Vygeneruj jeden {difficulty} obtížnosti matematický hlavolam v češtině. Vrať JSON: {{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"correct\": \"správná odpověď\"}}"
    }
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=str(uuid.uuid4()),
            system_message="Jsi pomocník pro generování kvízových otázek. Vždy odpovídej pouze validním JSON bez markdown formátování."
        ).with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=prompts.get(q_type, prompts["quiz"])))
        
        import json
        # Clean response
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean.split("```")[1]
            if response_clean.startswith("json"):
                response_clean = response_clean[4:]
        
        data = json.loads(response_clean)
        
        question_id = str(uuid.uuid4())
        time_limit = get_time_limit(difficulty)
        xp_reward = get_xp_reward(difficulty)
        
        active_questions[question_id] = {
            "correct_answer": data["correct"],
            "difficulty": difficulty,
            "xp_reward": xp_reward
        }
        
        return QuestionResponse(
            id=question_id,
            question=data["question"],
            options=data["options"],
            correct_answer="",
            difficulty=difficulty,
            question_type=q_type,
            time_limit=time_limit,
            xp_reward=xp_reward
        )
    except Exception as e:
        logger.error(f"AI generation error: {e}")
        return await generate_question(request)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
