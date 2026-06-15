// Espace d'administration et d'audit affichant les journaux de securite.
// Permet de suivre l'activite des utilisateurs et de reperer les tentatives d'acces bloquees.
import React, { useState, useEffect } from 'react';

function AuditLogs({ user, apiCall }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Appelle l'endpoint admin pour recuperer l'historique des actions.
  const fetchLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/admin/logs');
      if (!response.ok) {
        // Renvoie une erreur specifique si l'utilisateur n'est ni administrateur ni auditeur.
        if (response.status === 403) throw new Error("Accès refusé. Rôle insuffisant.");
        throw new Error("Impossible de charger les journaux");
      }
      const data = await response.json();
      setLogs(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Chargement des logs des le montage de la page.
  useEffect(() => { fetchLogs(); }, []);

  // Filtrage des logs en memoire (recherche par texte libre et statut SUCCESS/DENIED).
  const filteredLogs = logs.filter(log => {
    const matchesStatus = filterStatus === 'ALL' || log.status === filterStatus;
    const matchesSearch =
      log.user_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.trace_id && log.trace_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (log.details && log.details.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesStatus && matchesSearch;
  });

  // Calcul du nombre de tentatives de violation d'isolation ou d'acces (statut DENIED) pour alerter.
  const alertCount = logs.filter(l => l.status === 'DENIED').length;

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Banniere d'alerte visible uniquement en cas d'attaques ou acces illegitimes detectes */}
      {alertCount > 0 && (
        <div className="alert alert-error" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <strong>{alertCount} tentative{alertCount > 1 ? 's' : ''} d'accès bloquée{alertCount > 1 ? 's' : ''}</strong>
            <span style={{ marginLeft: 8 }}>détectée{alertCount > 1 ? 's' : ''} dans les journaux</span>
          </div>
          <span className="status-badge denied">Alerte</span>
        </div>
      )}

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: 12 }}>
          <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            Journaux d'audit
            {loading && <span className="spinner" />}
          </h2>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              className="input"
              placeholder="Rechercher..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: 220 }}
            />
            <select
              className="input"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              style={{ width: 150 }}
            >
              <option value="ALL">Tous</option>
              <option value="SUCCESS">Succès</option>
              <option value="DENIED">Refusés</option>
            </select>
            <button className="btn btn-secondary btn-sm" onClick={fetchLogs}>Actualiser</button>
          </div>
        </div>

        {filteredLogs.length === 0 ? (
          <div className="empty-state">
            <p>Aucun journal correspondant aux critères</p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Utilisateur</th>
                  <th>Action</th>
                  <th>Statut</th>
                  <th>Détails</th>
                  <th>IP</th>
                  <th style={{ textAlign: 'right' }}>Trace ID</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => (
                  // Les lignes avec acces refuse sont surlignees en rouge pour attirer l'attention.
                  <tr key={log.id} style={{ background: log.status === 'DENIED' ? 'var(--red-50)' : undefined }}>
                    <td style={{ whiteSpace: 'nowrap', color: 'var(--gray-500)' }}>
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td style={{ fontWeight: 600 }}>{log.user_email}</td>
                    <td><code>{log.action}</code></td>
                    <td>
                      <span className={`status-badge ${log.status === 'SUCCESS' ? 'success' : 'denied'}`}>
                        {log.status}
                      </span>
                    </td>
                    <td style={{
                      color: 'var(--gray-500)',
                      maxWidth: 260,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {log.details}
                    </td>
                    <td style={{ color: 'var(--gray-500)' }}>{log.ip_address}</td>
                    <td style={{ textAlign: 'right' }}>
                      <span className="trace-id">{log.trace_id}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{ fontSize: 12, color: 'var(--gray-400)', padding: '0 4px' }}>
        Journaux en lecture seule. Toute action est tracée avec un Trace ID unique.
      </div>
    </div>
  );
}

export default AuditLogs;
