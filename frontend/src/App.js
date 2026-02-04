import React, { useState, useEffect } from "react";
import { Toaster } from "./components/ui/sonner";
import { toast } from "sonner";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Switch } from "./components/ui/switch";
import { Badge } from "./components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import "./App.css";

const API_URL = process.env.REACT_APP_BACKEND_URL;

// Discord OAuth URLs
const DISCORD_CLIENT_ID = "1466110673875374201";
const REDIRECT_URI = "https://discord-gamify.preview.emergentagent.com";
const DISCORD_INVITE_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands`;
const DISCORD_LOGIN_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=identify%20guilds`;

// ============== Landing Page ==============

function LandingPage({ onLogin, onViewLeaderboard, stats }) {
  return (
    <div className="landing-page">
      <div className="hero-section">
        <div className="hero-content">
          <span className="hero-icon">⚔️</span>
          <h1 className="hero-title">Valhalla Bot</h1>
          <p className="hero-subtitle">
            Discord bot pro kvízy, XP systém a sledování herní aktivity
          </p>
          
          <div className="hero-features">
            <div className="feature-item">
              <span>🎵</span>
              <span>Hudební kvíz</span>
            </div>
            <div className="feature-item">
              <span>🎬</span>
              <span>Filmový kvíz</span>
            </div>
            <div className="feature-item">
              <span>⚡</span>
              <span>XP systém</span>
            </div>
            <div className="feature-item">
              <span>🎮</span>
              <span>Sledování her</span>
            </div>
          </div>

          <div className="hero-buttons">
            <a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer" className="add-bot-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19.27 5.33C17.94 4.71 16.5 4.26 15 4a.09.09 0 0 0-.07.03c-.18.33-.39.76-.53 1.09a16.09 16.09 0 0 0-4.8 0c-.14-.34-.35-.76-.54-1.09c-.01-.02-.04-.03-.07-.03c-1.5.26-2.93.71-4.27 1.33c-.01 0-.02.01-.03.02c-2.72 4.07-3.47 8.03-3.1 11.95c0 .02.01.04.03.05c1.8 1.32 3.53 2.12 5.24 2.65c.03.01.06 0 .07-.02c.4-.55.76-1.13 1.07-1.74c.02-.04 0-.08-.04-.09c-.57-.22-1.11-.48-1.64-.78c-.04-.02-.04-.08-.01-.11c.11-.08.22-.17.33-.25c.02-.02.05-.02.07-.01c3.44 1.57 7.15 1.57 10.55 0c.02-.01.05-.01.07.01c.11.09.22.17.33.26c.04.03.04.09-.01.11c-.52.31-1.07.56-1.64.78c-.04.01-.05.06-.04.09c.32.61.68 1.19 1.07 1.74c.03.01.06.02.09.01c1.72-.53 3.45-1.33 5.25-2.65c.02-.01.03-.03.03-.05c.44-4.53-.73-8.46-3.1-11.95c-.01-.01-.02-.02-.04-.02zM8.52 14.91c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12c0 1.17-.84 2.12-1.89 2.12zm6.97 0c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12c0 1.17-.83 2.12-1.89 2.12z"/>
              </svg>
              Přidat na server
            </a>
            
            <button onClick={onLogin} className="login-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
              Přihlásit se
            </button>
          </div>
        </div>
      </div>

      <div className="public-section">
        <div className="section-buttons">
          <button onClick={onViewLeaderboard} className="section-btn">
            🏆 Žebříček hráčů
          </button>
        </div>
      </div>

      <div className="info-section">
        <h2>🛡️ Jak to funguje?</h2>
        <div className="steps-grid">
          <div className="step-card">
            <span className="step-number">1</span>
            <h3>Přidej bota</h3>
            <p>Klikni na "Přidat na server" a vyber svůj Discord server</p>
          </div>
          <div className="step-card">
            <span className="step-number">2</span>
            <h3>Hraj kvízy</h3>
            <p>Použij /hudba, /film nebo /pravda a sbírej XP</p>
          </div>
          <div className="step-card">
            <span className="step-number">3</span>
            <h3>Stoupej v žebříčku</h3>
            <p>Získej nejvíc XP a staň se legendou!</p>
          </div>
        </div>
      </div>

      <div className="stats-preview">
        <div className="stats-row">
          <div className="stat-box">
            <span className="stat-number">{stats.guildCount || 0}</span>
            <span className="stat-text">Serverů</span>
          </div>
          <div className="stat-box">
            <span className="stat-number">{stats.totalUsers || 0}</span>
            <span className="stat-text">Hráčů</span>
          </div>
          <div className="stat-box">
            <span className="stat-number">{stats.totalXp?.toLocaleString() || 0}</span>
            <span className="stat-text">XP rozdáno</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============== Leaderboard Page ==============

function LeaderboardPage({ onBack, onViewProfile }) {
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const response = await fetch(`${API_URL}/api/leaderboard`);
      if (response.ok) {
        const data = await response.json();
        setPlayers(data);
      }
    } catch (error) {
      console.error("Failed to fetch leaderboard");
    }
    setLoading(false);
  };

  const getRankEmoji = (rank) => {
    if (rank === 1) return "🥇";
    if (rank === 2) return "🥈";
    if (rank === 3) return "🥉";
    return `#${rank}`;
  };

  const getLevelBadge = (level) => {
    if (level >= 30) return "🏆";
    if (level >= 25) return "👑";
    if (level >= 20) return "💎";
    if (level >= 15) return "🔥";
    if (level >= 10) return "💫";
    if (level >= 5) return "🌟";
    return "🌱";
  };

  return (
    <div className="leaderboard-page">
      <div className="page-header">
        <button className="back-btn" onClick={onBack}>← Zpět</button>
        <h1>🏆 Žebříček hráčů</h1>
      </div>

      {loading ? (
        <div className="loading">Načítám...</div>
      ) : (
        <div className="leaderboard-list">
          {players.map((player, index) => (
            <div 
              key={player.user_id} 
              className={`leaderboard-item ${index < 3 ? 'top-three' : ''}`}
              onClick={() => onViewProfile(player)}
            >
              <span className="rank">{getRankEmoji(index + 1)}</span>
              <div className="player-info">
                <span className="player-name">{player.name || "Neznámý"}</span>
                <span className="player-level">{getLevelBadge(player.level)} Level {player.level}</span>
              </div>
              <div className="player-stats">
                <span className="player-xp">⚡ {player.xp?.toLocaleString()} XP</span>
                <span className="player-games">🎮 {player.total_games || 0} her</span>
              </div>
              <span className="view-arrow">→</span>
            </div>
          ))}
          {players.length === 0 && (
            <div className="no-data">Zatím žádní hráči</div>
          )}
        </div>
      )}
    </div>
  );
}

// ============== Player Profile Page ==============

function PlayerProfilePage({ player, onBack }) {
  const [profile, setProfile] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
    fetchHistory();
  }, [player]);

  const fetchProfile = async () => {
    try {
      const response = await fetch(`${API_URL}/api/player/${player.user_id}`);
      if (response.ok) {
        const data = await response.json();
        setProfile(data);
      }
    } catch (error) {
      console.error("Failed to fetch profile");
    }
    setLoading(false);
  };

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_URL}/api/player/${player.user_id}/history`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      }
    } catch (error) {
      console.error("Failed to fetch history");
    }
  };

  const getLevelBadge = (level) => {
    if (level >= 30) return "🏆";
    if (level >= 25) return "👑";
    if (level >= 20) return "💎";
    if (level >= 15) return "🔥";
    if (level >= 10) return "💫";
    if (level >= 5) return "🌟";
    return "🌱";
  };

  const data = profile || player;

  return (
    <div className="profile-page">
      <div className="page-header">
        <button className="back-btn" onClick={onBack}>← Zpět</button>
        <h1>Profil hráče</h1>
      </div>

      <div className="profile-content">
        <Card className="profile-card">
          <CardContent className="profile-main">
            <div className="profile-header">
              <div className="profile-avatar">
                {getLevelBadge(data.level || 1)}
              </div>
              <div className="profile-info">
                <h2>{data.name || "Neznámý hráč"}</h2>
                <span className="profile-level">Level {data.level || 1}</span>
              </div>
            </div>

            <div className="profile-stats-grid">
              <div className="profile-stat">
                <span className="stat-value">⚡ {data.xp?.toLocaleString() || 0}</span>
                <span className="stat-label">Celkem XP</span>
              </div>
              <div className="profile-stat">
                <span className="stat-value">🎮 {data.total_games || 0}</span>
                <span className="stat-label">Odehraných her</span>
              </div>
              <div className="profile-stat">
                <span className="stat-value">✅ {data.total_correct || 0}</span>
                <span className="stat-label">Správných odpovědí</span>
              </div>
              <div className="profile-stat">
                <span className="stat-value">🔥 {data.streak || 0}</span>
                <span className="stat-label">Dnů streak</span>
              </div>
              <div className="profile-stat">
                <span className="stat-value">🎯 {data.total_games > 0 ? Math.round((data.total_correct / data.total_games) * 100) : 0}%</span>
                <span className="stat-label">Přesnost</span>
              </div>
              <div className="profile-stat">
                <span className="stat-value">🕹️ {data.unlocked_games?.length || 0}</span>
                <span className="stat-label">Odemčených her</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="history-card">
          <CardHeader>
            <CardTitle>📜 Historie kvízů</CardTitle>
          </CardHeader>
          <CardContent>
            {history.length > 0 ? (
              <div className="history-list">
                {history.map((item, index) => (
                  <div key={index} className="history-item">
                    <span className="history-type">
                      {item.type === 'music' ? '🎵' : item.type === 'film' ? '🎬' : '🤔'}
                    </span>
                    <div className="history-info">
                      <span className="history-result">
                        {item.won ? '🏆 Výhra' : item.correct ? '✅ Správně' : '❌ Špatně'}
                      </span>
                      <span className="history-date">{new Date(item.date).toLocaleDateString('cs-CZ')}</span>
                    </div>
                    <span className="history-xp">+{item.xp_earned} XP</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-data">Zatím žádná historie</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ============== Dashboard (after login) ==============

function Dashboard({ user, servers, onSelectServer, onLogout, onViewLeaderboard }) {
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="user-info">
          <img src={user.avatar} alt={user.username} className="user-avatar" />
          <div>
            <span className="user-name">{user.username}</span>
            <span className="user-tag">Přihlášen přes Discord</span>
          </div>
        </div>
        <div className="header-actions">
          <button onClick={onViewLeaderboard} className="leaderboard-btn">
            🏆 Žebříček
          </button>
          <button onClick={onLogout} className="logout-btn">
            Odhlásit se
          </button>
        </div>
      </div>

      <div className="servers-section">
        <h2>🖥️ Tvoje servery</h2>
        <p className="servers-hint">Vyber server pro nastavení (zobrazují se jen servery kde jsi admin)</p>
        
        {servers.length > 0 ? (
          <div className="servers-grid">
            {servers.map((server) => (
              <div 
                key={server.id} 
                className={`server-card ${!server.botInstalled ? 'server-card-disabled' : ''}`}
                onClick={() => server.botInstalled && onSelectServer(server)}
              >
                <div className="server-icon">
                  {server.icon ? (
                    <img src={`https://cdn.discordapp.com/icons/${server.id}/${server.icon}.png`} alt={server.name} />
                  ) : (
                    <span>{server.name.charAt(0)}</span>
                  )}
                </div>
                <div className="server-info">
                  <span className="server-name">{server.name}</span>
                  {server.botInstalled ? (
                    <Badge variant="default" className="bot-badge">Bot nainstalován</Badge>
                  ) : (
                    <Badge variant="secondary" className="bot-badge">Bot není na serveru</Badge>
                  )}
                </div>
                {server.botInstalled ? (
                  <span className="server-arrow">→</span>
                ) : (
                  <a 
                    href={`https://discord.com/oauth2/authorize?client_id=1466110673875374201&permissions=8&scope=bot%20applications.commands&guild_id=${server.id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="add-to-server-btn"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Přidat
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="no-servers">
            <p>Nemáš žádné servery kde bys byl admin.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ============== Server Settings Page ==============

function ServerSettings({ server, onBack }) {
  const [settings, setSettings] = useState({
    notificationChannelId: "",
    pingRoleId: "",
    xpPerQuiz: 25,
    xpPerTruth: 15,
    xpPer10Min: 5,
    xpDailyLimit: 200,
    xpUnlockBonus: 25,
    dailyBonus: 100,
    streakBonus: 10,
    autoDeleteSeconds: 60,
    cmdHudba: true,
    cmdFilm: true,
    cmdPravda: true,
    cmdGamelevel: false,
    cmdTop: false,
    cmdDaily: false,
    cmdHry: false,
    cmdUkoly: false,
    cmdHerniinfo: true,
  });

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load settings from server on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${API_URL}/api/bot/settings/${server.id}`);
        if (response.ok) {
          const data = await response.json();
          // Merge loaded settings with defaults
          setSettings(prev => ({ ...prev, ...data }));
        }
      } catch (error) {
        console.error("Failed to load settings:", error);
      }
      setLoading(false);
    };
    loadSettings();
  }, [server.id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/bot/settings/${server.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      if (response.ok) {
        toast.success("Nastavení uloženo!");
      } else {
        toast.error("Chyba při ukládání");
      }
    } catch (error) {
      toast.error("Nelze se připojit k serveru");
    }
    setSaving(false);
  };

  return (
    <div className="settings-page">
      <div className="settings-header">
        <button className="back-btn" onClick={onBack}>
          ← Zpět
        </button>
        <div className="current-server">
          <div className="server-icon-small">
            {server.icon ? (
              <img src={`https://cdn.discordapp.com/icons/${server.id}/${server.icon}.png`} alt={server.name} />
            ) : (
              <span>{server.name.charAt(0)}</span>
            )}
          </div>
          <span className="server-name-header">{server.name}</span>
        </div>
      </div>

      <Tabs defaultValue="channels" className="settings-tabs">
        <TabsList className="tabs-list">
          <TabsTrigger value="channels">📢 Kanály</TabsTrigger>
          <TabsTrigger value="xp">⚡ XP Systém</TabsTrigger>
          <TabsTrigger value="commands">🎮 Příkazy</TabsTrigger>
        </TabsList>

        {/* Channels Tab */}
        <TabsContent value="channels">
          <Card className="settings-card">
            <CardHeader>
              <CardTitle>📢 Nastavení kanálů</CardTitle>
              <CardDescription>Nastav kam bot posílá notifikace pro tento server</CardDescription>
            </CardHeader>
            <CardContent className="card-content">
              <div className="form-group">
                <Label htmlFor="notificationChannel">Kanál pro herní notifikace</Label>
                <Input
                  id="notificationChannel"
                  value={settings.notificationChannelId}
                  onChange={(e) => setSettings({ ...settings, notificationChannelId: e.target.value })}
                  placeholder="ID kanálu (např. 1468355022159872073)"
                />
                <p className="form-hint">Sem chodí notifikace o XP, level up, splněné úkoly</p>
              </div>

              <div className="form-group">
                <Label htmlFor="pingRole">Role pro ping při úspěchu</Label>
                <Input
                  id="pingRole"
                  value={settings.pingRoleId}
                  onChange={(e) => setSettings({ ...settings, pingRoleId: e.target.value })}
                  placeholder="ID role (např. 485172457544744972)"
                />
                <p className="form-hint">Tato role bude pingnutá při odemčení hry nebo splnění úkolu</p>
              </div>

              <div className="form-group">
                <Label htmlFor="autoDelete">Automatické mazání odpovědí (sekundy)</Label>
                <Input
                  id="autoDelete"
                  type="number"
                  value={settings.autoDeleteSeconds}
                  onChange={(e) => setSettings({ ...settings, autoDeleteSeconds: parseInt(e.target.value) })}
                  placeholder="60"
                />
                <p className="form-hint">Po kolika sekundách se smažou odpovědi na příkazy</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* XP System Tab */}
        <TabsContent value="xp">
          <Card className="settings-card">
            <CardHeader>
              <CardTitle>⚡ XP Systém</CardTitle>
              <CardDescription>Nastav odměny a limity pro tento server</CardDescription>
            </CardHeader>
            <CardContent className="card-content">
              <div className="xp-grid">
                <div className="form-group">
                  <Label>XP za kvíz (hudba/film)</Label>
                  <Input
                    type="number"
                    value={settings.xpPerQuiz}
                    onChange={(e) => setSettings({ ...settings, xpPerQuiz: parseInt(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <Label>XP za Pravda/Lež</Label>
                  <Input
                    type="number"
                    value={settings.xpPerTruth}
                    onChange={(e) => setSettings({ ...settings, xpPerTruth: parseInt(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <Label>XP za 10 min hraní</Label>
                  <Input
                    type="number"
                    value={settings.xpPer10Min}
                    onChange={(e) => setSettings({ ...settings, xpPer10Min: parseInt(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <Label>Denní limit XP (hraní)</Label>
                  <Input
                    type="number"
                    value={settings.xpDailyLimit}
                    onChange={(e) => setSettings({ ...settings, xpDailyLimit: parseInt(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <Label>Bonus za odemčení hry</Label>
                  <Input
                    type="number"
                    value={settings.xpUnlockBonus}
                    onChange={(e) => setSettings({ ...settings, xpUnlockBonus: parseInt(e.target.value) })}
                  />
                </div>

                <div className="form-group">
                  <Label>Denní bonus (/daily)</Label>
                  <Input
                    type="number"
                    value={settings.dailyBonus}
                    onChange={(e) => setSettings({ ...settings, dailyBonus: parseInt(e.target.value) })}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Commands Tab */}
        <TabsContent value="commands">
          <Card className="settings-card">
            <CardHeader>
              <CardTitle>🎮 Nastavení příkazů</CardTitle>
              <CardDescription>Klikni na přepínač pro změnu oprávnění (Admin / Všichni)</CardDescription>
            </CardHeader>
            <CardContent className="card-content">
              <div className="commands-list">
                <h3>🎵 Kvízy</h3>
                <div className="command-grid">
                  <div className="command-item">
                    <span className="command-name">/hudba</span>
                    <span className="command-desc">Hudební kvíz</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdHudba ? "default" : "secondary"}>
                        {settings.cmdHudba ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdHudba}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdHudba: checked })}
                      />
                    </div>
                  </div>
                  <div className="command-item">
                    <span className="command-name">/film</span>
                    <span className="command-desc">Filmový kvíz</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdFilm ? "default" : "secondary"}>
                        {settings.cmdFilm ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdFilm}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdFilm: checked })}
                      />
                    </div>
                  </div>
                  <div className="command-item">
                    <span className="command-name">/pravda</span>
                    <span className="command-desc">Pravda/Lež</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdPravda ? "default" : "secondary"}>
                        {settings.cmdPravda ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdPravda}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdPravda: checked })}
                      />
                    </div>
                  </div>
                </div>

                <h3>📊 Level systém</h3>
                <div className="command-grid">
                  <div className="command-item">
                    <span className="command-name">/gamelevel</span>
                    <span className="command-desc">Tvůj level a XP</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdGamelevel ? "default" : "secondary"}>
                        {settings.cmdGamelevel ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdGamelevel}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdGamelevel: checked })}
                      />
                    </div>
                  </div>
                  <div className="command-item">
                    <span className="command-name">/top</span>
                    <span className="command-desc">Žebříček</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdTop ? "default" : "secondary"}>
                        {settings.cmdTop ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdTop}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdTop: checked })}
                      />
                    </div>
                  </div>
                  <div className="command-item">
                    <span className="command-name">/daily</span>
                    <span className="command-desc">Denní bonus</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdDaily ? "default" : "secondary"}>
                        {settings.cmdDaily ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdDaily}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdDaily: checked })}
                      />
                    </div>
                  </div>
                </div>

                <h3>🎮 Herní příkazy</h3>
                <div className="command-grid">
                  <div className="command-item">
                    <span className="command-name">/hry</span>
                    <span className="command-desc">Odemčené hry</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdHry ? "default" : "secondary"}>
                        {settings.cmdHry ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdHry}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdHry: checked })}
                      />
                    </div>
                  </div>
                  <div className="command-item">
                    <span className="command-name">/ukoly</span>
                    <span className="command-desc">Herní úkoly</span>
                    <div className="command-toggle">
                      <Badge variant={settings.cmdUkoly ? "default" : "secondary"}>
                        {settings.cmdUkoly ? "Admin" : "Všichni"}
                      </Badge>
                      <Switch
                        checked={settings.cmdUkoly}
                        onCheckedChange={(checked) => setSettings({ ...settings, cmdUkoly: checked })}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="save-section">
        <Button onClick={handleSave} disabled={saving} className="save-btn">
          {saving ? "Ukládám..." : "💾 Uložit nastavení"}
        </Button>
      </div>
    </div>
  );
}

// ============== Main App ==============

function App() {
  const [user, setUser] = useState(null);
  const [selectedServer, setSelectedServer] = useState(null);
  const [servers, setServers] = useState([]);
  const [botGuilds, setBotGuilds] = useState([]);
  const [stats, setStats] = useState({ guildCount: 0, totalUsers: 0, totalXp: 0 });
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState('landing'); // landing, leaderboard, profile
  const [selectedPlayer, setSelectedPlayer] = useState(null);

  useEffect(() => {
    // Check for OAuth callback
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    
    if (code) {
      handleOAuthCallback(code);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      // Check for stored session
      const storedUser = localStorage.getItem('discord_user');
      const storedServers = localStorage.getItem('discord_servers');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
        if (storedServers) {
          setServers(JSON.parse(storedServers));
        }
      }
      setLoading(false);
    }
    
    fetchStats();
    fetchBotGuilds();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/stats`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.log("Stats not available");
    }
  };

  const fetchBotGuilds = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/guilds`);
      if (response.ok) {
        const data = await response.json();
        setBotGuilds(data.map(g => g.id));
      }
    } catch (error) {
      console.log("Bot guilds not available");
    }
  };

  const handleOAuthCallback = async (code) => {
    try {
      const response = await fetch(`${API_URL}/api/discord/callback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, redirect_uri: REDIRECT_URI })
      });
      
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
        
        // Filter servers where user is admin
        const adminServers = data.guilds.filter(g => 
          (g.permissions & 0x8) === 0x8 || g.owner
        ).map(g => ({
          ...g,
          botInstalled: botGuilds.includes(g.id)
        }));
        
        setServers(adminServers);
        
        localStorage.setItem('discord_user', JSON.stringify(data.user));
        localStorage.setItem('discord_servers', JSON.stringify(adminServers));
        
        toast.success(`Vítej, ${data.user.username}!`);
      } else {
        toast.error('Přihlášení selhalo');
      }
    } catch (error) {
      console.error('OAuth error:', error);
      toast.error('Chyba při přihlašování');
    }
    setLoading(false);
  };

  const handleLogin = () => {
    window.location.href = DISCORD_LOGIN_URL;
  };

  const handleLogout = () => {
    setUser(null);
    setServers([]);
    setSelectedServer(null);
    localStorage.removeItem('discord_user');
    localStorage.removeItem('discord_servers');
    toast.success('Odhlášen');
  };

  const handleViewLeaderboard = () => {
    setCurrentPage('leaderboard');
  };

  const handleViewProfile = (player) => {
    setSelectedPlayer(player);
    setCurrentPage('profile');
  };

  const handleBackToMain = () => {
    setCurrentPage('landing');
    setSelectedPlayer(null);
  };

  // Update servers with bot installation status
  useEffect(() => {
    if (servers.length > 0 && botGuilds.length > 0) {
      const updatedServers = servers.map(s => ({
        ...s,
        botInstalled: botGuilds.includes(s.id)
      }));
      setServers(updatedServers);
    }
  }, [botGuilds]);

  if (loading) {
    return (
      <div className="loading-screen">
        <span className="loading-icon">⚔️</span>
        <p>Načítám...</p>
      </div>
    );
  }

  // Page routing
  if (currentPage === 'leaderboard') {
    return (
      <div className="app-container">
        <Toaster position="top-right" richColors />
        <LeaderboardPage onBack={handleBackToMain} onViewProfile={handleViewProfile} />
        <footer className="footer">
          <p>⚔️ Valhalla Bot</p>
        </footer>
      </div>
    );
  }

  if (currentPage === 'profile' && selectedPlayer) {
    return (
      <div className="app-container">
        <Toaster position="top-right" richColors />
        <PlayerProfilePage player={selectedPlayer} onBack={() => setCurrentPage('leaderboard')} />
        <footer className="footer">
          <p>⚔️ Valhalla Bot</p>
        </footer>
      </div>
    );
  }

  return (
    <div className="app-container">
      <Toaster position="top-right" richColors />
      
      {!user ? (
        <LandingPage onLogin={handleLogin} onViewLeaderboard={handleViewLeaderboard} stats={stats} />
      ) : selectedServer ? (
        <ServerSettings 
          server={selectedServer} 
          onBack={() => setSelectedServer(null)}
        />
      ) : (
        <Dashboard 
          user={user}
          servers={servers}
          onSelectServer={setSelectedServer}
          onLogout={handleLogout}
          onViewLeaderboard={handleViewLeaderboard}
        />
      )}

      <footer className="footer">
        <p>⚔️ Valhalla Bot • {stats.guildCount} serverů • {stats.totalUsers} hráčů</p>
      </footer>
    </div>
  );
}

export default App;
