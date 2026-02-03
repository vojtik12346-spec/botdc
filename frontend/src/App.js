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

// ============== Valhalla Bot Admin Panel ==============

function App() {
  const [settings, setSettings] = useState({
    notificationChannelId: "1468355022159872073",
    pingRoleId: "485172457544744972",
    xpPerQuiz: 25,
    xpPerTruth: 15,
    xpPer10Min: 5,
    xpDailyLimit: 200,
    xpUnlockBonus: 25,
    dailyBonus: 100,
    streakBonus: 10,
    autoDeleteSeconds: 60,
    adminOnlyQuiz: true,
  });

  const [stats, setStats] = useState({
    totalUsers: 0,
    totalXp: 0,
    totalGames: 0,
    activeToday: 0,
    guildCount: 0,
  });

  const [botStatus, setBotStatus] = useState("online");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchStats();
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

  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_URL}/api/bot/settings`, {
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
    <div className="app-container">
      <Toaster position="top-right" richColors />
      
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">⚔️</span>
            <h1>Valhalla Bot</h1>
            <Badge variant={botStatus === "online" ? "default" : "destructive"} className="status-badge">
              {botStatus === "online" ? "🟢 Online" : "🔴 Offline"}
            </Badge>
          </div>
          <p className="header-subtitle">Admin Panel</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <Tabs defaultValue="channels" className="settings-tabs">
          <TabsList className="tabs-list">
            <TabsTrigger value="channels">📢 Kanály</TabsTrigger>
            <TabsTrigger value="xp">⚡ XP Systém</TabsTrigger>
            <TabsTrigger value="commands">🎮 Příkazy</TabsTrigger>
            <TabsTrigger value="stats">📊 Statistiky</TabsTrigger>
          </TabsList>

          {/* Channels Tab */}
          <TabsContent value="channels">
            <Card className="settings-card">
              <CardHeader>
                <CardTitle>📢 Nastavení kanálů</CardTitle>
                <CardDescription>Nastav kam bot posílá notifikace</CardDescription>
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
                <CardDescription>Nastav odměny a limity</CardDescription>
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

                  <div className="form-group">
                    <Label>Streak bonus (za den)</Label>
                    <Input
                      type="number"
                      value={settings.streakBonus}
                      onChange={(e) => setSettings({ ...settings, streakBonus: parseInt(e.target.value) })}
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
                <CardDescription>Oprávnění a dostupnost příkazů</CardDescription>
              </CardHeader>
              <CardContent className="card-content">
                <div className="switch-group">
                  <div className="switch-item">
                    <div className="switch-info">
                      <Label>Kvízy pouze pro adminy</Label>
                      <p className="form-hint">/hudba, /film, /pravda může spustit jen admin</p>
                    </div>
                    <Switch
                      checked={settings.adminOnlyQuiz}
                      onCheckedChange={(checked) => setSettings({ ...settings, adminOnlyQuiz: checked })}
                    />
                  </div>
                </div>

                <div className="commands-list">
                  <h3>📋 Seznam příkazů</h3>
                  <div className="command-grid">
                    <div className="command-item">
                      <span className="command-name">/hudba</span>
                      <span className="command-desc">Hudební kvíz</span>
                      <Badge>Admin</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/film</span>
                      <span className="command-desc">Filmový kvíz</span>
                      <Badge>Admin</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/pravda</span>
                      <span className="command-desc">Pravda/Lež</span>
                      <Badge>Admin</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/gamelevel</span>
                      <span className="command-desc">Tvůj level a XP</span>
                      <Badge variant="secondary">Všichni</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/top</span>
                      <span className="command-desc">Žebříček</span>
                      <Badge variant="secondary">Všichni</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/daily</span>
                      <span className="command-desc">Denní bonus</span>
                      <Badge variant="secondary">Všichni</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/hry</span>
                      <span className="command-desc">Odemčené hry</span>
                      <Badge variant="secondary">Všichni</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">/ukoly</span>
                      <span className="command-desc">Herní úkoly</span>
                      <Badge variant="secondary">Všichni</Badge>
                    </div>
                    <div className="command-item">
                      <span className="command-name">!herniinfo</span>
                      <span className="command-desc">Info zpráva</span>
                      <Badge>Admin</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Stats Tab */}
          <TabsContent value="stats">
            <Card className="settings-card">
              <CardHeader>
                <CardTitle>📊 Statistiky</CardTitle>
                <CardDescription>Přehled aktivity na serveru</CardDescription>
              </CardHeader>
              <CardContent className="card-content">
                <div className="stats-grid">
                  <div className="stat-card">
                    <span className="stat-icon">👥</span>
                    <span className="stat-value">{stats.totalUsers}</span>
                    <span className="stat-label">Hráčů celkem</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-icon">⚡</span>
                    <span className="stat-value">{stats.totalXp.toLocaleString()}</span>
                    <span className="stat-label">XP rozdáno</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-icon">🎮</span>
                    <span className="stat-value">{stats.totalGames}</span>
                    <span className="stat-label">Kvízů odehráno</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-icon">🔥</span>
                    <span className="stat-value">{stats.activeToday}</span>
                    <span className="stat-label">Aktivních dnes</span>
                  </div>
                </div>

                <Button onClick={fetchStats} variant="outline" className="refresh-btn">
                  🔄 Obnovit statistiky
                </Button>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Save Button */}
        <div className="save-section">
          <Button onClick={handleSave} disabled={saving} className="save-btn">
            {saving ? "Ukládám..." : "💾 Uložit nastavení"}
          </Button>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>⚔️ Valhalla Bot Admin Panel • Vytvořeno pro Discord komunitu</p>
      </footer>
    </div>
  );
}

export default App;
