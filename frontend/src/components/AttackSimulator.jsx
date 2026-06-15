import React, { useState } from 'react';

function AttackSimulator({ user, token, apiCall, apiBase }) {
  const [consoleLogs, setConsoleLogs] = useState([]);
  const [activeAttack, setActiveAttack] = useState('idor');
  const [docId, setDocId] = useState(4);

  const logToConsole = (attackName, mode, url, status, data) => {
    const time = new Date().toLocaleTimeString();
    setConsoleLogs(prev => [{
      time, attackName, mode, url, status,
      body: typeof data === 'object' ? JSON.stringify(data, null, 2) : data
    }, ...prev]);
  };

  const clearConsole = () => setConsoleLogs([]);

  const runIdor = async (mode) => {
    const endpoint = mode === 'vulnerable'
      ? `/api/attacks/idor/vulnerable/${docId}`
      : `/api/attacks/idor/secured/${docId}`;
    try {
      const response = await apiCall(endpoint);
      const data = await response.json();
      logToConsole("IDOR / Accès Inter-Tenant", mode, `${apiBase}${endpoint}`, response.status, data);
    } catch (e) {
      logToConsole("IDOR", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
    }
  };

  const runPrivilegeEscalation = async (mode) => {
    if (mode === 'vulnerable') {
      const endpoint = `/api/attacks/privilege-escalation/vulnerable/${docId}?role=user`;
      try {
        const response = await apiCall(endpoint, { method: 'POST' });
        const data = await response.json();
        logToConsole("Privilege Escalation", mode, `${apiBase}${endpoint}`, response.status, data);
      } catch (e) {
        logToConsole("Privilege Escalation", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
      }
    } else {
      const endpoint = `/api/documents/${docId}`;
      try {
        const response = await apiCall(endpoint, { method: 'DELETE' });
        let data;
        try { data = await response.json(); } catch { data = "Suppression effectuée"; }
        logToConsole("Privilege Escalation (RBAC)", mode, `${apiBase}${endpoint}`, response.status, data);
      } catch (e) {
        logToConsole("Privilege Escalation", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
      }
    }
  };

  const runTokenReplay = async (mode) => {
    const endpoint = mode === 'vulnerable'
      ? '/api/attacks/token-replay/vulnerable'
      : '/api/attacks/token-replay/secured';
    try {
      await apiCall('/api/attacks/token-replay/simulate-logout', { method: 'POST' });
      const response = await apiCall(endpoint);
      const data = await response.json();
      logToConsole("Token Replay", mode, `${apiBase}${endpoint}`, response.status, data);
    } catch (e) {
      logToConsole("Token Replay", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
    }
  };

  const runPublicExfiltration = async (mode) => {
    const filename = "dupont_vs_state.pdf";
    const endpoint = mode === 'vulnerable'
      ? `/api/attacks/public-leak/vulnerable/${filename}`
      : `/api/attacks/public-leak/secured/${filename}`;
    try {
      const response = await fetch(`${apiBase}${endpoint}`);
      const data = await response.json();
      logToConsole("Exfiltration Stockage", mode, `${apiBase}${endpoint}`, response.status, data);
    } catch (e) {
      logToConsole("Exfiltration Stockage", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
    }
  };

  const runDos = async (mode) => {
    const clientId = "demo-attacker-99";
    const endpoint = `/api/attacks/dos/simulate?client_id=${clientId}&mode=${mode}`;
    logToConsole("DoS", mode, `${apiBase}${endpoint}`, "INFO", "Envoi de 8 requêtes consécutives...");
    for (let i = 1; i <= 8; i++) {
      try {
        const response = await apiCall(endpoint);
        const data = await response.json();
        logToConsole(`Requête #${i}`, mode, `${apiBase}${endpoint}`, response.status, data);
      } catch (e) {
        logToConsole(`Requête #${i}`, mode, `${apiBase}${endpoint}`, "Bloqué", e.message);
      }
    }
  };

  const runSecretLeak = async (mode) => {
    const endpoint = `/api/attacks/secret-leak/simulate?mode=${mode}`;
    try {
      const response = await apiCall(endpoint);
      const data = await response.json();
      logToConsole("Fuite de Secrets", mode, `${apiBase}${endpoint}`, response.status, data);
    } catch (e) {
      logToConsole("Fuite de Secrets", mode, `${apiBase}${endpoint}`, "Erreur", e.message);
    }
  };

  const runAttack = (mode) => {
    const runners = { idor: runIdor, privilege: runPrivilegeEscalation, replay: runTokenReplay, public_leak: runPublicExfiltration, dos: runDos, secrets: runSecretLeak };
    runners[activeAttack]?.(mode);
  };

  const attacks = {
    idor: {
      title: "1. IDOR — Accès inter-tenant",
      stride: "Information Disclosure",
      risk: "critical",
      riskLabel: "Critique",
      showDocId: true,
      desc: "L'attaquant manipule l'identifiant du document pour accéder à un fichier appartenant à un autre cabinet. Sans vérification du tenant_id, les données fuient entre locataires.",
      code: `if doc.tenant_id != current_user.tenant_id:
    write_audit_log(status="DENIED", details="IDOR Blocked")
    raise HTTPException(403, "Cross-Tenant Block")`
    },
    privilege: {
      title: "2. Privilege Escalation",
      stride: "Elevation of Privilege",
      risk: "high",
      riskLabel: "Élevé",
      showDocId: true,
      desc: "Un auditeur ou collaborateur tente une suppression réservée aux administrateurs. Sans RBAC, l'API accepte la requête.",
      code: `class RequireRole:
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles
    def __call__(self, current_user):
        if current_user.role not in self.allowed_roles:
            raise HTTPException(403, "Forbidden")`
    },
    replay: {
      title: "3. Rejeu de jeton",
      stride: "Spoofing",
      risk: "high",
      riskLabel: "Élevé",
      showDocId: false,
      desc: "Un token expiré ou révoqué est rejoué. Sans blacklist ou TTL court, le serveur accepte indéfiniment le jeton usurpé.",
      code: `if token in token_blacklist:
    raise HTTPException(401, "Token Replay Blocked")`
    },
    public_leak: {
      title: "4. Exfiltration GCS publique",
      stride: "Information Disclosure",
      risk: "critical",
      riskLabel: "Critique",
      showDocId: false,
      desc: "Accès direct au bucket de stockage sans passer par l'API. Si la Public Access Prevention n'est pas activée, les fichiers sont téléchargeables par n'importe qui.",
      code: `# Terraform — storage.tf
resource "google_storage_bucket" "documents" {
  public_access_prevention = "enforced"
}`
    },
    dos: {
      title: "5. DoS / Rate limiting",
      stride: "Denial of Service",
      risk: "medium",
      riskLabel: "Moyen",
      showDocId: false,
      desc: "Envoi massif de requêtes pour saturer l'API. Le rate limiter bloque au-delà de 5 requêtes en 10 secondes.",
      code: `if len(hits) > 5:
    raise HTTPException(429, "Too Many Requests")`
    },
    secrets: {
      title: "6. Fuite de secrets",
      stride: "Information Disclosure",
      risk: "high",
      riskLabel: "Élevé",
      showDocId: false,
      desc: "Les mots de passe ou clés de connexion apparaissent en clair dans les logs applicatifs ou les scripts CI/CD.",
      code: `# Utiliser GCP Secret Manager
DATABASE_URL = secret_manager.access_secret_version(...)`
    }
  };

  const current = attacks[activeAttack];

  return (
    <div className="fade-in" style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20, minHeight: 500 }}>

      <div className="card" style={{ height: 'fit-content' }}>
        <div className="card-header">
          <h3 className="card-title">Scénarios</h3>
        </div>
        <div style={{ padding: 8 }}>
          <div className="sidebar-list">
            {Object.keys(attacks).map(key => (
              <button
                key={key}
                className={`attack-item ${activeAttack === key ? 'active' : ''}`}
                onClick={() => setActiveAttack(key)}
              >
                {attacks[key].title}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">{current.title}</h2>
            <div style={{ display: 'flex', gap: 8 }}>
              <span className="status-badge warning" style={{ fontSize: 11 }}>
                STRIDE: {current.stride}
              </span>
              <span className={`risk-badge ${current.risk}`}>
                {current.riskLabel}
              </span>
            </div>
          </div>
          <div className="card-body">
            <p style={{ color: 'var(--gray-600)', marginBottom: 20, lineHeight: 1.7 }}>
              {current.desc}
            </p>

            {current.showDocId && (
              <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-600)' }}>
                  ID du document cible :
                </label>
                <input
                  type="number"
                  value={docId}
                  onChange={(e) => setDocId(parseInt(e.target.value))}
                  style={{
                    width: 80,
                    padding: '4px 8px',
                    border: '1px solid var(--gray-300)',
                    borderRadius: 6,
                    fontSize: 14,
                    fontFamily: 'monospace'
                  }}
                />
              </div>
            )}

            <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
              <button className="btn btn-danger" onClick={() => runAttack('vulnerable')}>
                Lancer (vulnérable)
              </button>
              <button className="btn btn-success" onClick={() => runAttack('secured')}>
                Lancer (sécurisé)
              </button>
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--gray-500)', marginBottom: 6 }}>
                Code de remédiation
              </div>
              <pre className="code-block">{current.code}</pre>
            </div>
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div className="card-header">
            <h3 className="card-title">Console réseau</h3>
            <button className="btn btn-ghost btn-sm" onClick={clearConsole}>Vider</button>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="console" style={{ borderRadius: 0, border: 'none' }}>
              {consoleLogs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>
                  Lancez une attaque pour voir le trafic réseau
                </div>
              ) : (
                consoleLogs.map((log, i) => (
                  <div key={i} className="console-entry">
                    <div className="console-meta">
                      <span className="time">[{log.time}] {log.attackName}</span>
                      <span className={`console-tag ${log.mode === 'vulnerable' ? 'vuln' : 'secure'}`}>
                        {log.mode === 'vulnerable' ? 'VULN' : 'SÉCURISÉ'}
                      </span>
                    </div>
                    <div>
                      <span style={{ color: '#9ca3af' }}>URL: </span>
                      <span className="console-url">{log.url}</span>
                    </div>
                    <div>
                      <span style={{ color: '#9ca3af' }}>Status: </span>
                      <span className={`console-status ${log.status === 200 ? 'ok' : 'error'}`}>
                        {log.status}
                      </span>
                    </div>
                    <pre>{log.body}</pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default AttackSimulator;