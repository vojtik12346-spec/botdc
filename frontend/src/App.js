import React, { useState, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Switch } from "./components/ui/switch";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import {
  Settings,
  BarChart3,
  Music,
  Users,
  LogOut,
  Bot,
  Clock,
  Hash,
  Activity,
  Trophy,
  FileText,
  Zap,
  Timer,
  Vote
} from "lucide-react";
import "./App.css";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ============== Auth Context ==============

const AuthContext = React.createContext(null);

function useAuth() {
  return React.useContext(AuthContext);
}

// ============== Login Page ==============

function LoginPage() {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (user && !loading) {
      navigate("/dashboard");
    }
  }, [user, loading, navigate]);

  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-cyan-900/20" />
      
      <Card className="w-full max-w-md bg-[#12121a] border-purple-500/20 relative z-10">
        <CardHeader className="text-center">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
            <Bot className="w-10 h-10 text-white" />
          </div>
          <CardTitle className="text-2xl font-bold text-white">Quiz Bot Dashboard</CardTitle>
          <CardDescription className="text-zinc-400">
            Spravuj nastavení svého Discord bota
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleLogin}
            className="w-full h-12 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Přihlásit se přes Google
          </Button>
          
          <p className="text-center text-zinc-500 text-sm mt-4">
            Bezpečné přihlášení pomocí Google účtu
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ============== Auth Callback ==============

function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      const hash = location.hash;
      const sessionIdMatch = hash.match(/session_id=([^&]+)/);
      
      if (!sessionIdMatch) {
        navigate("/login");
        return;
      }

      const sessionId = sessionIdMatch[1];

      try {
        const response = await fetch(`${API_URL}/api/auth/session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ session_id: sessionId })
        });

        if (!response.ok) {
          throw new Error("Auth failed");
        }

        const user = await response.json();
        // Clear hash and navigate to dashboard with user data
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/dashboard", { state: { user } });
      } catch (error) {
        console.error("Auth error:", error);
        toast.error("Přihlášení selhalo");
        navigate("/login");
      }
    };

    processAuth();
  }, [location, navigate]);

  return (
    <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin w-12 h-12 border-3 border-purple-500 border-t-transparent rounded-full mx-auto mb-4" />
        <p className="text-zinc-400">Přihlašování...</p>
      </div>
    </div>
  );
}

// ============== Protected Route ==============

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

// ============== Dashboard ==============

function Dashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [settings, setSettings] = useState({
    quiz_time: 60,
    quiz_rounds: 5,
    poll_enabled: true,
    countdown_enabled: true
  });
  const [stats, setStats] = useState({
    total_users: 0,
    total_quizzes: 0,
    total_polls: 0,
    leaderboard: []
  });
  const [songs, setSongs] = useState({});
  const [logs, setLogs] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      // Fetch stats
      const statsRes = await fetch(`${API_URL}/api/stats`, { credentials: "include" });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }

      // Fetch songs
      const songsRes = await fetch(`${API_URL}/api/songs`, { credentials: "include" });
      if (songsRes.ok) {
        setSongs(await songsRes.json());
      }

      // Fetch logs
      const logsRes = await fetch(`${API_URL}/api/logs`, { credentials: "include" });
      if (logsRes.ok) {
        setLogs(await logsRes.json());
      }

      // Fetch settings (use default guild for now)
      const settingsRes = await fetch(`${API_URL}/api/settings/default`, { credentials: "include" });
      if (settingsRes.ok) {
        const data = await settingsRes.json();
        setSettings(prev => ({ ...prev, ...data }));
      }
    } catch (error) {
      console.error("Fetch error:", error);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/settings/default`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(settings)
      });

      if (response.ok) {
        toast.success("Nastavení uloženo!");
      } else {
        toast.error("Chyba při ukládání");
      }
    } catch (error) {
      toast.error("Chyba při ukládání");
    }
    setSaving(false);
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="bg-[#12121a] border-b border-purple-500/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-white">Quiz Bot</h1>
              <p className="text-xs text-zinc-500">Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Badge variant="outline" className="border-green-500/50 text-green-400">
              <Activity className="w-3 h-3 mr-1" />
              Online
            </Badge>
            
            <div className="flex items-center gap-2">
              {user?.picture && (
                <img src={user.picture} alt="" className="w-8 h-8 rounded-full" />
              )}
              <span className="text-zinc-300 text-sm hidden sm:block">{user?.name}</span>
            </div>

            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-zinc-400 hover:text-white">
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-8">
          <TabsList className="bg-[#12121a] border border-purple-500/20 p-1">
            <TabsTrigger value="overview" className="data-[state=active]:bg-purple-600">
              <BarChart3 className="w-4 h-4 mr-2" />
              Přehled
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-purple-600">
              <Settings className="w-4 h-4 mr-2" />
              Nastavení
            </TabsTrigger>
            <TabsTrigger value="songs" className="data-[state=active]:bg-purple-600">
              <Music className="w-4 h-4 mr-2" />
              Písně
            </TabsTrigger>
            <TabsTrigger value="leaderboard" className="data-[state=active]:bg-purple-600">
              <Trophy className="w-4 h-4 mr-2" />
              Žebříček
            </TabsTrigger>
            <TabsTrigger value="logs" className="data-[state=active]:bg-purple-600">
              <FileText className="w-4 h-4 mr-2" />
              Logy
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card className="bg-[#12121a] border-purple-500/20">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-zinc-400 text-sm">Celkem hráčů</p>
                      <p className="text-3xl font-bold text-white">{stats.total_users}</p>
                    </div>
                    <Users className="w-10 h-10 text-purple-500" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-[#12121a] border-cyan-500/20">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-zinc-400 text-sm">Kvízů odehráno</p>
                      <p className="text-3xl font-bold text-white">{stats.total_quizzes}</p>
                    </div>
                    <Music className="w-10 h-10 text-cyan-500" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-[#12121a] border-green-500/20">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-zinc-400 text-sm">Anket vytvořeno</p>
                      <p className="text-3xl font-bold text-white">{stats.total_polls}</p>
                    </div>
                    <Vote className="w-10 h-10 text-green-500" />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-[#12121a] border-yellow-500/20">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-zinc-400 text-sm">Status</p>
                      <p className="text-xl font-bold text-green-400">Online</p>
                    </div>
                    <Zap className="w-10 h-10 text-yellow-500" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Quick Commands */}
            <Card className="bg-[#12121a] border-purple-500/20">
              <CardHeader>
                <CardTitle className="text-white">Dostupné příkazy</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/20">
                    <code className="text-purple-400">/hudba</code>
                    <p className="text-zinc-400 text-sm mt-1">Hudební kvíz</p>
                  </div>
                  <div className="p-4 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
                    <code className="text-cyan-400">/poll</code>
                    <p className="text-zinc-400 text-sm mt-1">Vytvoř anketu</p>
                  </div>
                  <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20">
                    <code className="text-green-400">/odpocet</code>
                    <p className="text-zinc-400 text-sm mt-1">Spusť odpočet</p>
                  </div>
                  <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                    <code className="text-yellow-400">/hudba-nastaveni</code>
                    <p className="text-zinc-400 text-sm mt-1">Nastav kvíz</p>
                  </div>
                  <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                    <code className="text-red-400">!stop</code>
                    <p className="text-zinc-400 text-sm mt-1">Zastav kvíz</p>
                  </div>
                  <div className="p-4 rounded-lg bg-zinc-500/10 border border-zinc-500/20">
                    <code className="text-zinc-400">/help</code>
                    <p className="text-zinc-400 text-sm mt-1">Nápověda</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-6">
            <Card className="bg-[#12121a] border-purple-500/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Music className="w-5 h-5" />
                  Hudební kvíz
                </CardTitle>
                <CardDescription>Nastavení hudebního kvízu</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="quiz_time" className="text-zinc-300 flex items-center gap-2">
                      <Clock className="w-4 h-4" />
                      Čas na odpověď (sekundy)
                    </Label>
                    <Input
                      id="quiz_time"
                      type="number"
                      min={30}
                      max={300}
                      value={settings.quiz_time}
                      onChange={(e) => setSettings({ ...settings, quiz_time: parseInt(e.target.value) || 60 })}
                      className="bg-[#1a1a24] border-purple-500/20 text-white"
                    />
                    <p className="text-xs text-zinc-500">30 - 300 sekund</p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="quiz_rounds" className="text-zinc-300 flex items-center gap-2">
                      <Hash className="w-4 h-4" />
                      Počet otázek
                    </Label>
                    <Input
                      id="quiz_rounds"
                      type="number"
                      min={1}
                      max={20}
                      value={settings.quiz_rounds}
                      onChange={(e) => setSettings({ ...settings, quiz_rounds: parseInt(e.target.value) || 5 })}
                      className="bg-[#1a1a24] border-purple-500/20 text-white"
                    />
                    <p className="text-xs text-zinc-500">1 - 20 otázek</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#12121a] border-cyan-500/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Vote className="w-5 h-5" />
                  Ankety
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-zinc-300">Povolit ankety</p>
                    <p className="text-xs text-zinc-500">Příkaz /poll bude dostupný</p>
                  </div>
                  <Switch
                    checked={settings.poll_enabled}
                    onCheckedChange={(checked) => setSettings({ ...settings, poll_enabled: checked })}
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-[#12121a] border-green-500/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Timer className="w-5 h-5" />
                  Odpočet
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-zinc-300">Povolit odpočet</p>
                    <p className="text-xs text-zinc-500">Příkaz /odpocet bude dostupný</p>
                  </div>
                  <Switch
                    checked={settings.countdown_enabled}
                    onCheckedChange={(checked) => setSettings({ ...settings, countdown_enabled: checked })}
                  />
                </div>
              </CardContent>
            </Card>

            <Button
              onClick={saveSettings}
              disabled={saving}
              className="w-full md:w-auto bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-700 hover:to-cyan-700"
            >
              {saving ? "Ukládám..." : "Uložit nastavení"}
            </Button>
          </TabsContent>

          {/* Songs Tab */}
          <TabsContent value="songs" className="space-y-6">
            {Object.entries(songs).map(([genre, songList]) => (
              <Card key={genre} className="bg-[#12121a] border-purple-500/20">
                <CardHeader>
                  <CardTitle className="text-white capitalize flex items-center gap-2">
                    {genre === "rap" && "🎤"}
                    {genre === "pop" && "🎵"}
                    {genre === "rock" && "🎸"}
                    {genre === "classic" && "🎺"}
                    {genre}
                  </CardTitle>
                  <CardDescription>{songList.length} písní</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {songList.map((song, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-[#1a1a24] border border-zinc-800">
                        <p className="text-white font-medium">{song.artist}</p>
                        <p className="text-zinc-400 text-sm">{song.song}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </TabsContent>

          {/* Leaderboard Tab */}
          <TabsContent value="leaderboard">
            <Card className="bg-[#12121a] border-yellow-500/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Trophy className="w-5 h-5 text-yellow-500" />
                  Top hráči
                </CardTitle>
              </CardHeader>
              <CardContent>
                {stats.leaderboard.length === 0 ? (
                  <p className="text-zinc-400 text-center py-8">Zatím žádní hráči</p>
                ) : (
                  <div className="space-y-2">
                    {stats.leaderboard.map((player, idx) => (
                      <div key={idx} className="flex items-center justify-between p-4 rounded-lg bg-[#1a1a24] border border-zinc-800">
                        <div className="flex items-center gap-4">
                          <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                            idx === 0 ? "bg-yellow-500 text-black" :
                            idx === 1 ? "bg-zinc-400 text-black" :
                            idx === 2 ? "bg-orange-600 text-white" :
                            "bg-zinc-700 text-white"
                          }`}>
                            {idx + 1}
                          </span>
                          <span className="text-white">{player.name || player.username}</span>
                        </div>
                        <span className="text-purple-400 font-bold">{player.score || 0} bodů</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs">
            <Card className="bg-[#12121a] border-zinc-500/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Poslední příkazy
                </CardTitle>
              </CardHeader>
              <CardContent>
                {logs.length === 0 ? (
                  <p className="text-zinc-400 text-center py-8">Zatím žádné logy</p>
                ) : (
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {logs.map((log, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-[#1a1a24] border border-zinc-800 text-sm">
                        <div>
                          <code className="text-purple-400">{log.command}</code>
                          <span className="text-zinc-400 ml-2">od {log.user}</span>
                        </div>
                        <span className="text-zinc-500">{log.timestamp}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

// ============== Auth Provider ==============

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    // Skip auth check if we have user from location state (just logged in)
    if (location.state?.user) {
      setUser(location.state.user);
      setLoading(false);
      return;
    }

    const checkAuth = async () => {
      try {
        const response = await fetch(`${API_URL}/api/auth/me`, {
          credentials: "include"
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        }
      } catch (error) {
        console.error("Auth check error:", error);
      }
      setLoading(false);
    };

    checkAuth();
  }, [location.state]);

  const logout = async () => {
    try {
      await fetch(`${API_URL}/api/auth/logout`, {
        method: "POST",
        credentials: "include"
      });
    } catch (error) {
      console.error("Logout error:", error);
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// ============== App Router ==============

function AppRouter() {
  const location = useLocation();

  // Check for session_id in URL hash BEFORE routing
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  );
}

// ============== Main App ==============

function App() {
  return (
    <BrowserRouter>
      <AppRouter />
      <Toaster position="top-center" richColors />
    </BrowserRouter>
  );
}

export default App;
