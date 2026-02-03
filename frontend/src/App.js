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

// Discord OAuth URL - nahraď CLIENT_ID svým bot client ID
const DISCORD_CLIENT_ID = "1336454706620063826";
const DISCORD_INVITE_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands`;

// ============== Landing Page ==============

function LandingPage({ onSelectServer, servers }) {
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

          <a href={DISCORD_INVITE_URL} target="_blank" rel="noopener noreferrer" className="add-bot-btn">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.27 5.33C17.94 4.71 16.5 4.26 15 4a.09.09 0 0 0-.07.03c-.18.33-.39.76-.53 1.09a16.09 16.09 0 0 0-4.8 0c-.14-.34-.35-.76-.54-1.09c-.01-.02-.04-.03-.07-.03c-1.5.26-2.93.71-4.27 1.33c-.01 0-.02.01-.03.02c-2.72 4.07-3.47 8.03-3.1 11.95c0 .02.01.04.03.05c1.8 1.32 3.53 2.12 5.24 2.65c.03.01.06 0 .07-.02c.4-.55.76-1.13 1.07-1.74c.02-.04 0-.08-.04-.09c-.57-.22-1.11-.48-1.64-.78c-.04-.02-.04-.08-.01-.11c.11-.08.22-.17.33-.25c.02-.02.05-.02.07-.01c3.44 1.57 7.15 1.57 10.55 0c.02-.01.05-.01.07.01c.11.09.22.17.33.26c.04.03.04.09-.01.11c-.52.31-1.07.56-1.64.78c-.04.01-.05.06-.04.09c.32.61.68 1.19 1.07 1.74c.03.01.06.02.09.01c1.72-.53 3.45-1.33 5.25-2.65c.02-.01.03-.03.03-.05c.44-4.53-.73-8.46-3.1-11.95c-.01-.01-.02-.02-.04-.02zM8.52 14.91c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12c0 1.17-.84 2.12-1.89 2.12zm6.97 0c-1.03 0-1.89-.95-1.89-2.12s.84-2.12 1.89-2.12c1.06 0 1.9.96 1.89 2.12c0 1.17-.83 2.12-1.89 2.12z"/>
            </svg>
            Přidat na Discord
          </a>
        </div>
      </div>

      {servers.length > 0 && (
        <div className="servers-section">
          <h2>🖥️ Tvoje servery</h2>
          <p className="servers-hint">Vyber server pro nastavení</p>
          <div className="servers-grid">
            {servers.map((server) => (
              <div 
                key={server.id} 
                className="server-card"
                onClick={() => onSelectServer(server)}
              >
                <div className="server-icon">
                  {server.icon ? (
                    <img src={server.icon} alt={server.name} />
                  ) : (
                    <span>{server.name.charAt(0)}</span>
                  )}
                </div>
                <div className="server-info">
                  <span className="server-name">{server.name}</span>
                  <span className="server-members">{server.memberCount} členů</span>
                </div>
                <span className="server-arrow">→</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="stats-preview">
        <h2>📊 Statistiky bota</h2>
        <div className="stats-row">
          <div className="stat-box">
            <span className="stat-number">2</span>
            <span className="stat-text">Serverů</span>
          </div>
          <div className="stat-box">
            <span className="stat-number">5</span>
            <span className="stat-text">Hráčů</span>
          </div>
          <div className="stat-box">
            <span className="stat-number">250</span>
            <span className="stat-text">XP rozdáno</span>
          </div>
        </div>
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
              <img src={server.icon} alt={server.name} />
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
  const [selectedServer, setSelectedServer] = useState(null);
  const [servers, setServers] = useState([]);
  const [stats, setStats] = useState({ guildCount: 0, totalUsers: 0, totalXp: 0 });

  useEffect(() => {
    fetchServers();
    fetchStats();
  }, []);

  const fetchServers = async () => {
    try {
      const response = await fetch(`${API_URL}/api/bot/guilds`);
      if (response.ok) {
        const data = await response.json();
        setServers(data);
      }
    } catch (error) {
      console.log("Servers not available");
    }
  };

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

  return (
    <div className="app-container">
      <Toaster position="top-right" richColors />
      
      {!selectedServer ? (
        <LandingPage 
          onSelectServer={setSelectedServer} 
          servers={servers}
        />
      ) : (
        <ServerSettings 
          server={selectedServer} 
          onBack={() => setSelectedServer(null)}
        />
      )}

      <footer className="footer">
        <p>⚔️ Valhalla Bot • {stats.guildCount} serverů • {stats.totalUsers} hráčů</p>
      </footer>
    </div>
  );
}

export default App;
