// Composant d'authentification (page de connexion).
// Permet de se connecter soit en selectionnant un utilisateur pre-enregistre pour la demonstration,
// soit en saisissant manuellement une adresse email.
import React, { useState } from 'react';

function Login({ onLogin, apiBase }) {
  // Par defaut, on selectionne un compte administrateur du Cabinet A.
  const [selectedEmail, setSelectedEmail] = useState('nour.admin@cabinet-a.fr');
  const [manualEmail, setManualEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Liste des profils de demonstration avec leurs roles respectifs (Admin, Collaborateur, Auditeur).
  const preseededUsers = [
    { label: "Cabinet A — Nour (Admin)", email: "nour.admin@cabinet-a.fr" },
    { label: "Cabinet A — Aya (Collaborateur)", email: "aya.user@cabinet-a.fr" },
    { label: "Cabinet A — Yosra (Auditeur)", email: "yosra.auditor@cabinet-a.fr" },
    { label: "Cabinet B — Avocat Admin", email: "avocat.admin@cabinet-b.fr" },
    { label: "Cabinet B — Avocat User", email: "avocat.user@cabinet-b.fr" },
    { label: "Cabinet B — Avocat Auditor", email: "avocat.auditor@cabinet-b.fr" },
  ];

  // Soumission du formulaire pour recuperer le token JWT correspondant a l'email.
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // On priorise la saisie manuelle si elle est remplie, sinon on utilise le choix de la liste.
    const email = manualEmail.trim() || selectedEmail;

    try {
      const response = await fetch(`${apiBase}/api/auth/token?email=${encodeURIComponent(email)}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Échec de l'authentification");
      }

      const data = await response.json();
      // Transmission du jeton et des infos utilisateur au composant parent (App).
      onLogin(data.access_token, data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card fade-in">

        <h1 className="login-title">
          Jury<span style={{ color: 'var(--blue-600)' }}>DOC</span>
        </h1>
        <p className="login-subtitle">
          Connectez-vous pour accéder à vos dossiers
        </p>

        {error && (
          <div className="alert alert-error" style={{ marginBottom: 16 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">

          <div>
            <label className="label">Profil de démonstration</label>
            <select
              className="input"
              value={selectedEmail}
              onChange={(e) => {
                setSelectedEmail(e.target.value);
                setManualEmail('');
              }}
            >
              {preseededUsers.map((u, i) => (
                <option key={i} value={u.email}>{u.label}</option>
              ))}
            </select>
          </div>

          <div className="divider">ou</div>

          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              placeholder="votre.nom@cabinet.fr"
              value={manualEmail}
              onChange={(e) => setManualEmail(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', padding: '10px 16px', marginTop: 4 }}
          >
            {loading ? <span className="spinner" /> : "Se connecter"}
          </button>

        </form>

        <div className="login-footer">
          Projet M2 EPISEN — Sécurité du Cloud — ANYSafe
        </div>
      </div>
    </div>
  );
}

export default Login;
