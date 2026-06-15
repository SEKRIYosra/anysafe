// Composant principal de l'application.
// Il gere l'etat global d'authentification (jeton JWT et donnees de l'utilisateur),
// le systeme de navigation par onglets et fournit une fonction d'appel d'API securisee.
import React, { useState, useEffect } from 'react';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import AuditLogs from './components/AuditLogs';
import AttackSimulator from './components/AttackSimulator';

// Adresse de base du serveur backend de demonstration.
const API_BASE = "https://jurydoc-api-438784684569.europe-west9.run.app";

function App() {
  // Chargement des informations d'authentification prealablement enregistrees dans le navigateur.
  const [token, setToken] = useState(localStorage.getItem('jurydoc_token'));
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('jurydoc_user')));
  const [activeTab, setActiveTab] = useState('documents');
  const [latestTraceId, setLatestTraceId] = useState('');

  // Enregistre les identifiants de session et redirige vers l'espace de documents.
  const handleLogin = (newToken, loggedInUser) => {
    localStorage.setItem('jurydoc_token', newToken);
    localStorage.setItem('jurydoc_user', JSON.stringify(loggedInUser));
    setToken(newToken);
    setUser(loggedInUser);
    setActiveTab('documents');
  };

  // Termine la session en nettoyant le stockage local et en informant le serveur pour invalider le jeton.
  const handleLogout = async () => {
    if (token) {
      try {
        // Signalement au backend pour simuler la deconnexion ou inscrire le jeton sur liste noire.
        await fetch(`${API_BASE}/api/attacks/token-replay/simulate-logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (e) {
        console.warn("Logout notification failed:", e);
      }
    }
    localStorage.removeItem('jurydoc_token');
    localStorage.removeItem('jurydoc_user');
    setToken(null);
    setUser(null);
  };

  // Wrapper d'appel API permettant d'ajouter automatiquement l'en-tete d'authentification Bearer
  // ainsi qu'un identifiant de tracabilite unique (X-Trace-ID) pour le suivi des requetes.
  const apiCall = async (endpoint, options = {}) => {
    // Generation d'une chaine de caracteres aleatoire comme identifiant de trace.
    const traceId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);

    const headers = {
      ...(options.headers || {}),
      'X-Trace-ID': traceId
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const mergedOptions = { ...options, headers };

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, mergedOptions);
      // Recuperation de l'identifiant de trace renvoye par le serveur, ou valeur locale par defaut.
      const resTraceId = response.headers.get('X-Trace-ID') || traceId;
      setLatestTraceId(resTraceId);
      return response;
    } catch (err) {
      console.error("API Call error:", err);
      throw err;
    }
  };

  // Convertit l'identifiant technique du cabinet (tenant) en libelle lisible.
  const getTenantName = (tid) => {
    if (tid === 'cabinet-a') return 'Cabinet A — Paris';
    if (tid === 'cabinet-b') return 'Cabinet B — Lyon';
    return tid;
  };

  // Si l'utilisateur n'est pas connecte, redirection automatique vers la page d'authentification.
  if (!token || !user) {
    return <Login onLogin={handleLogin} apiBase={API_BASE} />;
  }

  // Definition des onglets accessibles selon le role de l'utilisateur.
  // Les fonctions de consultation d'audit ne sont accessibles qu'aux administrateurs et auditeurs.
  const tabs = [
    { id: 'documents', label: 'Documents' },
    ...(user.role === 'admin' || user.role === 'auditor'
      ? [{ id: 'logs', label: 'Audit' }]
      : []),
    { id: 'simulator', label: 'Attaques' },
  ];

  return (
    <div className="app-layout fade-in">

      <header className="header">
        <div className="header-left">
          <div className="logo">Jury<span>DOC</span></div>
          <span className="tenant-label">{getTenantName(user.tenant_id)}</span>

          <nav className="nav-tabs">
            {tabs.map(tab => (
              <button
                key={tab.id}
                className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="header-right">
          <div className="user-info">
            <span className="user-email">{user.email}</span>
            <span className={`role-badge ${user.role}`}>{user.role}</span>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
            Déconnexion
          </button>
        </div>
      </header>

      <main className="main-content">
        {activeTab === 'documents' && <Dashboard user={user} apiCall={apiCall} apiBase={API_BASE} />}
        {activeTab === 'logs' && <AuditLogs user={user} apiCall={apiCall} />}
        {activeTab === 'simulator' && <AttackSimulator user={user} token={token} apiCall={apiCall} apiBase={API_BASE} />}
      </main>

      <footer className="footer-bar">
        <span>
          Trace ID: <span className="trace-id">{latestTraceId || '—'}</span>
        </span>
        <span>Mode Cloud GCP · EPISEN · ANYSafe</span>
      </footer>
    </div>
  );
}

export default App;
