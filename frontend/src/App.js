import React, { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Progress } from "./components/ui/progress";
import { Badge } from "./components/ui/badge";
import { Input } from "./components/ui/input";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "./components/ui/select";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { 
  Brain, 
  Calculator, 
  Trophy, 
  Zap, 
  Timer, 
  Star, 
  ArrowRight,
  Copy,
  Check,
  Home as HomeIcon,
  User,
  Sparkles
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Landing Page Component
const LandingPage = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleStart = async (gameType) => {
    if (!username.trim()) {
      toast.error("Zadej své jméno!");
      return;
    }

    setIsLoading(true);
    try {
      const response = await axios.post(`${API}/users`, { username: username.trim() });
      const user = response.data;
      localStorage.setItem("userId", user.id);
      localStorage.setItem("username", user.username);
      navigate(`/game/${gameType}`);
    } catch (error) {
      toast.error("Něco se pokazilo!");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen hero-gradient noise-bg relative overflow-hidden">
      {/* Background Image */}
      <div 
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: "url(https://images.pexels.com/photos/28428584/pexels-photo-28428584.jpeg)",
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
      />
      
      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 py-8 min-h-screen flex flex-col">
        {/* Header */}
        <header className="flex justify-between items-center mb-12">
          <div className="flex items-center gap-2">
            <Sparkles className="w-8 h-8 text-primary" />
            <span className="font-orbitron text-2xl font-bold tracking-wider text-glow-primary">
              QUIZ BOT
            </span>
          </div>
          <Button 
            variant="ghost" 
            onClick={() => navigate("/leaderboard")}
            className="font-rajdhani"
            data-testid="nav-leaderboard-btn"
          >
            <Trophy className="w-5 h-5 mr-2" />
            Žebříček
          </Button>
        </header>

        {/* Hero Section */}
        <main className="flex-1 flex flex-col items-center justify-center text-center">
          <h1 
            className="font-orbitron text-4xl sm:text-5xl lg:text-6xl font-black tracking-wider mb-6 animate-fade-in-up text-glow-primary"
            data-testid="hero-title"
          >
            OTÁZKY & MATEMATIKA
          </h1>
          <p className="font-rajdhani text-lg text-zinc-400 mb-12 max-w-xl animate-fade-in-up stagger-1">
            Testuj své znalosti, získej XP a staň se mistrem kvízů!
          </p>

          {/* Username Input */}
          <div className="w-full max-w-sm mb-8 animate-fade-in-up stagger-2">
            <Input
              placeholder="Zadej své jméno..."
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="h-14 text-lg font-rajdhani bg-black/50 border-white/10 focus:border-primary text-center"
              data-testid="username-input"
            />
          </div>

          {/* Game Selection Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-2xl animate-fade-in-up stagger-3">
            {/* Quiz Card */}
            <Card 
              className="glass-card cursor-pointer group hover:border-primary/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(124,58,237,0.3)]"
              onClick={() => handleStart("quiz")}
              data-testid="quiz-card"
            >
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Brain className="w-8 h-8 text-primary" />
                </div>
                <h3 className="font-orbitron text-xl font-bold mb-2 text-glow-primary">
                  KVÍZ
                </h3>
                <p className="text-zinc-400 font-rajdhani">
                  Otestuj své všeobecné znalosti
                </p>
                <div className="mt-4 flex items-center justify-center gap-2 text-primary">
                  <span className="font-mono text-sm">START</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </CardContent>
            </Card>

            {/* Math Card */}
            <Card 
              className="glass-card cursor-pointer group hover:border-secondary/50 transition-all duration-300 hover:shadow-[0_0_30px_rgba(6,182,212,0.3)]"
              onClick={() => handleStart("math")}
              data-testid="math-card"
            >
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-cyan-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                  <Calculator className="w-8 h-8 text-cyan-400" />
                </div>
                <h3 className="font-orbitron text-xl font-bold mb-2 text-glow-secondary">
                  MATEMATIKA
                </h3>
                <p className="text-zinc-400 font-rajdhani">
                  Výpočty, rovnice a hlavolamy
                </p>
                <div className="mt-4 flex items-center justify-center gap-2 text-cyan-400">
                  <span className="font-mono text-sm">START</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
};

// Game Page Component
const GamePage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const gameType = location.pathname.split("/")[2]; // quiz or math
  
  const [question, setQuestion] = useState(null);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [result, setResult] = useState(null);
  const [score, setScore] = useState(0);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [difficulty, setDifficulty] = useState("medium");
  const [mathType, setMathType] = useState("math_calc");
  const [mee6Command, setMee6Command] = useState("");
  const [copied, setCopied] = useState(false);
  const [useAI, setUseAI] = useState(false);

  const userId = localStorage.getItem("userId");
  const username = localStorage.getItem("username");

  const fetchQuestion = useCallback(async () => {
    setIsLoading(true);
    setResult(null);
    setSelectedAnswer(null);
    setMee6Command("");
    
    try {
      const questionType = gameType === "quiz" ? "quiz" : mathType;
      const endpoint = useAI ? "/questions/generate-ai" : "/questions/generate";
      
      const response = await axios.post(`${API}${endpoint}`, {
        difficulty,
        question_type: questionType
      });
      
      setQuestion(response.data);
      setTimeLeft(response.data.time_limit);
    } catch (error) {
      toast.error("Nepodařilo se načíst otázku");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, [gameType, difficulty, mathType, useAI]);

  useEffect(() => {
    if (!userId) {
      navigate("/");
      return;
    }
    fetchQuestion();
  }, [userId, navigate, fetchQuestion]);

  // Timer
  useEffect(() => {
    if (timeLeft > 0 && !result) {
      const timer = setTimeout(() => setTimeLeft(timeLeft - 1), 1000);
      return () => clearTimeout(timer);
    } else if (timeLeft === 0 && question && !result) {
      handleSubmit(null);
    }
  }, [timeLeft, result, question]);

  const handleSubmit = async (answer) => {
    if (result) return;
    
    setSelectedAnswer(answer);
    
    try {
      const response = await axios.post(`${API}/questions/answer`, {
        question_id: question.id,
        user_id: userId,
        selected_answer: answer || "",
        time_taken: question.time_limit - timeLeft
      });
      
      setResult(response.data);
      setQuestionsAnswered(prev => prev + 1);
      
      if (response.data.correct) {
        setScore(prev => prev + response.data.xp_earned);
        setCorrectAnswers(prev => prev + 1);
        setMee6Command(response.data.mee6_command);
        toast.success(`+${response.data.xp_earned} XP!`, {
          description: "Správná odpověď!"
        });
      } else {
        toast.error("Špatná odpověď!", {
          description: `Správně: ${response.data.correct_answer}`
        });
      }
    } catch (error) {
      toast.error("Chyba při odesílání odpovědi");
      console.error(error);
    }
  };

  const copyMee6Command = () => {
    navigator.clipboard.writeText(mee6Command);
    setCopied(true);
    toast.success("Příkaz zkopírován!");
    setTimeout(() => setCopied(false), 2000);
  };

  const getTimerColor = () => {
    if (timeLeft > 15) return "text-green-400";
    if (timeLeft > 5) return "text-yellow-400";
    return "text-red-400 animate-timer-pulse";
  };

  return (
    <div className="min-h-screen bg-[#050505] noise-bg">
      <div className="container mx-auto px-4 py-6 max-w-3xl">
        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <Button 
            variant="ghost" 
            onClick={() => navigate("/")}
            data-testid="back-home-btn"
          >
            <HomeIcon className="w-5 h-5 mr-2" />
            Domů
          </Button>
          
          <div className="flex items-center gap-4">
            <Badge variant="outline" className="font-mono px-4 py-2">
              <User className="w-4 h-4 mr-2" />
              {username}
            </Badge>
            <Badge className="bg-primary/20 text-primary border-primary/50 font-mono px-4 py-2">
              <Star className="w-4 h-4 mr-2" />
              {score} XP
            </Badge>
          </div>
        </header>

        {/* Game Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <Card className="glass-card">
            <CardContent className="p-4 text-center">
              <p className="text-zinc-400 text-sm font-rajdhani">Otázky</p>
              <p className="font-orbitron text-2xl font-bold">{questionsAnswered}</p>
            </CardContent>
          </Card>
          <Card className="glass-card">
            <CardContent className="p-4 text-center">
              <p className="text-zinc-400 text-sm font-rajdhani">Správné</p>
              <p className="font-orbitron text-2xl font-bold text-green-400">{correctAnswers}</p>
            </CardContent>
          </Card>
          <Card className="glass-card">
            <CardContent className="p-4 text-center">
              <p className="text-zinc-400 text-sm font-rajdhani">Úspěšnost</p>
              <p className="font-orbitron text-2xl font-bold text-cyan-400">
                {questionsAnswered > 0 ? Math.round((correctAnswers / questionsAnswered) * 100) : 0}%
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Settings */}
        <div className="flex flex-wrap gap-4 mb-8">
          <Select value={difficulty} onValueChange={setDifficulty}>
            <SelectTrigger className="w-40 bg-black/50 border-white/10" data-testid="difficulty-select">
              <SelectValue placeholder="Obtížnost" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="easy">Lehká</SelectItem>
              <SelectItem value="medium">Střední</SelectItem>
              <SelectItem value="hard">Těžká</SelectItem>
            </SelectContent>
          </Select>

          {gameType === "math" && (
            <Select value={mathType} onValueChange={setMathType}>
              <SelectTrigger className="w-44 bg-black/50 border-white/10" data-testid="math-type-select">
                <SelectValue placeholder="Typ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="math_calc">Počítání</SelectItem>
                <SelectItem value="math_equation">Rovnice</SelectItem>
                <SelectItem value="math_puzzle">Hlavolamy</SelectItem>
              </SelectContent>
            </Select>
          )}

          <Button
            variant={useAI ? "default" : "outline"}
            onClick={() => setUseAI(!useAI)}
            className={useAI ? "bg-primary" : ""}
            data-testid="ai-toggle-btn"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            AI Otázky
          </Button>
        </div>

        {/* Question Card */}
        {isLoading ? (
          <Card className="glass-card animate-pulse">
            <CardContent className="p-12 text-center">
              <div className="w-12 h-12 mx-auto rounded-full bg-primary/20 animate-spin" />
              <p className="mt-4 text-zinc-400">Načítám otázku...</p>
            </CardContent>
          </Card>
        ) : question ? (
          <Card className="glass-card tracing-beam overflow-hidden" data-testid="question-card">
            {/* Timer */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <Badge variant="outline" className="font-mono">
                {question.difficulty === "easy" ? "Lehká" : 
                 question.difficulty === "medium" ? "Střední" : "Těžká"}
              </Badge>
              <div className={`flex items-center gap-2 font-mono text-xl ${getTimerColor()}`}>
                <Timer className="w-5 h-5" />
                {timeLeft}s
              </div>
              <Badge variant="outline" className="font-mono">
                +{question.xp_reward} XP
              </Badge>
            </div>

            {/* Progress */}
            <Progress 
              value={(timeLeft / question.time_limit) * 100} 
              className="h-1 rounded-none"
            />

            {/* Question */}
            <CardContent className="p-8">
              <h2 
                className="font-rajdhani text-xl sm:text-2xl font-semibold text-center mb-8"
                data-testid="question-text"
              >
                {question.question}
              </h2>

              {/* Options */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {question.options.map((option, index) => {
                  let optionClass = "option-card";
                  if (result) {
                    if (option === result.correct_answer) {
                      optionClass += " correct";
                    } else if (option === selectedAnswer && !result.correct) {
                      optionClass += " wrong";
                    }
                  } else if (option === selectedAnswer) {
                    optionClass += " selected";
                  }

                  return (
                    <button
                      key={index}
                      onClick={() => !result && handleSubmit(option)}
                      disabled={!!result}
                      className={`${optionClass} p-4 rounded-lg bg-black/40 text-left font-rajdhani text-lg transition-all`}
                      data-testid={`option-${index}`}
                    >
                      <span className="font-mono text-primary mr-3">
                        {String.fromCharCode(65 + index)}.
                      </span>
                      {option}
                    </button>
                  );
                })}
              </div>

              {/* Result & Mee6 Command */}
              {result && (
                <div className="mt-8 space-y-4 animate-fade-in-up">
                  <div className={`p-4 rounded-lg text-center ${
                    result.correct ? "bg-green-500/20 border border-green-500/50" : "bg-red-500/20 border border-red-500/50"
                  }`}>
                    <p className="font-orbitron text-lg">
                      {result.correct ? "🎉 SPRÁVNĚ!" : "❌ ŠPATNĚ!"}
                    </p>
                    {!result.correct && (
                      <p className="text-zinc-400 mt-2">
                        Správná odpověď: <span className="text-green-400">{result.correct_answer}</span>
                      </p>
                    )}
                  </div>

                  {mee6Command && (
                    <div className="p-4 rounded-lg bg-primary/10 border border-primary/30">
                      <p className="text-sm text-zinc-400 mb-2">Mee6 příkaz pro XP:</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 p-2 bg-black/50 rounded font-mono text-sm text-primary overflow-x-auto">
                          {mee6Command}
                        </code>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={copyMee6Command}
                          data-testid="copy-mee6-btn"
                        >
                          {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        </Button>
                      </div>
                    </div>
                  )}

                  <Button 
                    onClick={fetchQuestion} 
                    className="w-full h-12 font-orbitron tracking-wider bg-primary hover:bg-primary/80"
                    data-testid="next-question-btn"
                  >
                    DALŠÍ OTÁZKA
                    <ArrowRight className="w-5 h-5 ml-2" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ) : null}

        {/* End Game Button */}
        <div className="mt-8 text-center">
          <Button
            variant="outline"
            onClick={() => navigate("/leaderboard")}
            className="font-rajdhani"
            data-testid="view-leaderboard-btn"
          >
            <Trophy className="w-5 h-5 mr-2" />
            Zobrazit žebříček
          </Button>
        </div>
      </div>
    </div>
  );
};

// Leaderboard Page Component
const LeaderboardPage = () => {
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const response = await axios.get(`${API}/leaderboard?limit=20`);
        setLeaderboard(response.data);
      } catch (error) {
        toast.error("Nepodařilo se načíst žebříček");
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchLeaderboard();
  }, []);

  const getRankStyle = (rank) => {
    if (rank === 1) return "rank-gold";
    if (rank === 2) return "rank-silver";
    if (rank === 3) return "rank-bronze";
    return "bg-zinc-800";
  };

  return (
    <div className="min-h-screen bg-[#050505] noise-bg">
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        {/* Header */}
        <header className="flex items-center justify-between mb-8">
          <Button 
            variant="ghost" 
            onClick={() => navigate("/")}
            data-testid="leaderboard-back-btn"
          >
            <HomeIcon className="w-5 h-5 mr-2" />
            Domů
          </Button>
          <h1 className="font-orbitron text-2xl font-bold tracking-wider text-glow-primary">
            ŽEBŘÍČEK
          </h1>
          <div className="w-24" /> {/* Spacer */}
        </header>

        {/* Leaderboard */}
        <Card className="glass-card overflow-hidden" data-testid="leaderboard-card">
          <CardHeader className="border-b border-white/10">
            <CardTitle className="font-orbitron flex items-center gap-2">
              <Trophy className="w-6 h-6 text-yellow-400" />
              TOP HRÁČI
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {isLoading ? (
              <div className="p-12 text-center">
                <div className="w-12 h-12 mx-auto rounded-full bg-primary/20 animate-spin" />
                <p className="mt-4 text-zinc-400">Načítám žebříček...</p>
              </div>
            ) : leaderboard.length === 0 ? (
              <div className="p-12 text-center">
                <p className="text-zinc-400">Žádní hráči zatím</p>
                <Button 
                  onClick={() => navigate("/")} 
                  className="mt-4"
                  data-testid="start-playing-btn"
                >
                  Buď první!
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {leaderboard.map((entry, index) => (
                  <div 
                    key={index}
                    className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors animate-slide-in"
                    style={{ animationDelay: `${index * 0.05}s` }}
                    data-testid={`leaderboard-entry-${index}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 flex items-center justify-center rounded-full font-orbitron font-bold ${getRankStyle(entry.rank)}`}>
                        {entry.rank}
                      </div>
                      <div>
                        <p className="font-rajdhani font-semibold text-lg">{entry.username}</p>
                        <p className="text-sm text-zinc-400">{entry.games_played} her</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-xl font-bold text-primary">{entry.total_score}</p>
                      <p className="text-sm text-zinc-400">XP</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/game/:type" element={<GamePage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </div>
  );
}

export default App;
