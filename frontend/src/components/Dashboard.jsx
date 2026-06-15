// Espace principal (Dashboard) affichant les documents du cabinet courant.
// Permet de telecharger, d'ajouter ou de supprimer des documents, et d'en generer des resumes.
import React, { useState, useEffect } from 'react';

function Dashboard({ user, apiCall, apiBase }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [title, setTitle] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Gestion de la boite de dialogue (modal) de generation de resume de document par IA.
  const [summaryModal, setSummaryModal] = useState({
    isOpen: false,
    docTitle: '',
    loading: false,
    content: '',
    error: ''
  });

  // Recupere la liste des documents du cabinet depuis l'API.
  const fetchDocuments = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await apiCall('/api/documents');
      if (!response.ok) throw new Error("Impossible de charger les documents");
      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Chargement initial au montage du composant.
  useEffect(() => { fetchDocuments(); }, []);

  // Met a jour l'etat lors de la selection d'un fichier et pre-remplit le titre si vide.
  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
      if (!title) {
        // Supprime l'extension du nom de fichier pour le titre par defaut.
        setTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
      }
    }
  };

  // Envoie le fichier selectionne au serveur (upload).
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedFile || !title.trim()) {
      setError("Veuillez saisir un titre et choisir un fichier.");
      return;
    }
    setUploading(true);
    setError('');
    setSuccess('');

    // Utilisation de FormData pour envoyer le fichier binaire et les champs associes.
    const formData = new FormData();
    formData.append("title", title);
    formData.append("file", selectedFile);

    try {
      const response = await apiCall('/api/documents', { method: 'POST', body: formData });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Erreur lors du téléversement");
      }
      setSuccess("Document téléversé avec succès.");
      setTitle('');
      setSelectedFile(null);
      // Reinitialisation de la valeur du champ de fichier HTML.
      const fileInput = document.getElementById("document-file-input");
      if (fileInput) fileInput.value = "";
      fetchDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  // Telecharge un document en recuperant son flux binaire de maniere securisee.
  const handleDownload = async (doc) => {
    setError('');
    try {
      const response = await apiCall(`/api/documents/${doc.id}`);
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Échec du téléchargement");
      }
      // Creation d'un lien temporaire dans le navigateur pour lancer le telechargement.
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err.message);
    }
  };

  // Supprime definitivement un document (action reservee aux administrateurs).
  const handleDelete = async (docId) => {
    if (!window.confirm("Supprimer ce document définitivement ?")) return;
    setError('');
    setSuccess('');
    try {
      const response = await apiCall(`/api/documents/${docId}`, { method: 'DELETE' });
      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Échec de la suppression");
      }
      setSuccess("Document supprimé.");
      fetchDocuments();
    } catch (err) {
      setError(err.message);
    }
  };

  // Interroge le service IA/LLM du backend pour generer un resume du document.
  const handleSummarize = async (doc) => {
    setSummaryModal({
      isOpen: true,
      docTitle: doc.title,
      loading: true,
      content: '',
      error: ''
    });
    try {
      const response = await apiCall(`/api/documents/${doc.id}/summarize`, {
        method: 'POST'
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Erreur lors de la génération du résumé");
      }
      const data = await response.json();
      setSummaryModal(prev => ({
        ...prev,
        loading: false,
        content: data.summary
      }));
    } catch (err) {
      setSummaryModal(prev => ({
        ...prev,
        loading: false,
        error: err.message
      }));
    }
  };

  // Formatage simple pour rendre en gras le texte entoure de double asterisques.
  const formatBoldText = (text) => {
    if (!text) return '';
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, i) => i % 2 === 1 ? <strong key={i} style={{ color: 'var(--gray-900)' }}>{part}</strong> : part);
  };

  // Transforme la reponse textuelle ou markdown legere en elements React structures.
  const renderFormattedContent = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, index) => {
      let trimmed = line.trim();
      if (trimmed.startsWith('###')) {
        return <h4 key={index} style={{ margin: '14px 0 8px 0', color: 'var(--gray-800)', fontWeight: 600 }}>{trimmed.replace(/^###\s*/, '')}</h4>;
      }
      if (trimmed.startsWith('##')) {
        return <h3 key={index} style={{ margin: '18px 0 10px 0', color: 'var(--gray-800)', fontWeight: 700 }}>{trimmed.replace(/^##\s*/, '')}</h3>;
      }
      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        const content = trimmed.replace(/^[-*]\s*/, '');
        return (
          <li key={index} style={{ marginLeft: '16px', marginBottom: '6px', color: 'var(--gray-700)' }}>
            {formatBoldText(content)}
          </li>
        );
      }
      return (
        <p key={index} style={{ marginBottom: '10px', color: 'var(--gray-700)', lineHeight: '1.6' }}>
          {formatBoldText(line)}
        </p>
      );
    });
  };

  // Affiche la taille des fichiers dans une unite adaptee (Octets, Ko, Mo).
  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <div className="two-cols">

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">
              Documents du cabinet
              {loading && <span className="spinner" style={{ marginLeft: 8 }} />}
            </h2>
            <button className="btn btn-ghost btn-sm" onClick={fetchDocuments}>Actualiser</button>
          </div>

          {documents.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📄</div>
              <p>Aucun document pour le moment</p>
              <p className="hint">Téléversez un fichier pour commencer</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Titre</th>
                    <th>Fichier</th>
                    <th>Taille</th>
                    <th>Auteur</th>
                    <th>Date</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc) => (
                    <tr key={doc.id}>
                      <td style={{ fontWeight: 600, color: 'var(--gray-800)' }}>{doc.title}</td>
                      <td><code>{doc.filename}</code></td>
                      <td>{formatSize(doc.size_bytes)}</td>
                      <td style={{ color: 'var(--gray-500)' }}>{doc.uploaded_by}</td>
                      <td style={{ color: 'var(--gray-500)' }}>
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleDownload(doc)}>
                            Ouvrir
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => handleSummarize(doc)}>
                            Résumer
                          </button>
                          <button
                            className={`btn btn-sm ${user.role === 'admin' ? 'btn-danger' : 'btn-secondary'}`}
                            disabled={user.role !== 'admin'}
                            title={user.role !== 'admin' ? 'Réservé aux administrateurs' : ''}
                            onClick={() => user.role === 'admin' && handleDelete(doc.id)}
                          >
                            Supprimer
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-header">
            <h3 className="card-title">Ajouter un document</h3>
          </div>
          <div className="card-body">
            {user.role === 'auditor' ? (
              <div className="alert alert-warning">
                Votre rôle d'auditeur ne permet pas le téléversement de documents.
              </div>
            ) : (
              <form onSubmit={handleUpload} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div>
                  <label className="label">Titre du dossier</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="Ex : Contrat de cession"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>
                <div>
                  <label className="label">Fichier</label>
                  <input
                    type="file"
                    id="document-file-input"
                    className="input"
                    onChange={handleFileChange}
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading}
                  style={{ width: '100%' }}
                >
                  {uploading ? <span className="spinner" /> : "Téléverser"}
                </button>
              </form>
            )}

            <div className="upload-note">
              Les fichiers sont chiffrés via KMS et stockés de façon isolée par cabinet.
            </div>
          </div>
        </div>

      </div>

      {summaryModal.isOpen && (
        <div className="modal-overlay" onClick={() => setSummaryModal(prev => ({ ...prev, isOpen: false }))}>
          <div className="modal-container" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Résumé juridique : {summaryModal.docTitle}</h3>
              <button 
                className="modal-close-btn" 
                onClick={() => setSummaryModal(prev => ({ ...prev, isOpen: false }))}
              >
                &times;
              </button>
            </div>
            
            <div className="modal-body">
              {summaryModal.loading && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 12 }}>
                  <span className="spinner" style={{ width: 32, height: 32, borderWidth: 3 }} />
                  <p style={{ color: 'var(--gray-500)', fontWeight: 500 }}>
                    Génération du résumé en cours...
                  </p>
                </div>
              )}
              
              {summaryModal.error && (
                <div className="alert alert-error" style={{ margin: '10px 0' }}>
                  {summaryModal.error}
                </div>
              )}
              
              {summaryModal.content && (
                <div style={{ color: 'var(--gray-700)' }}>
                  {renderFormattedContent(summaryModal.content)}
                </div>
              )}
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn btn-secondary btn-sm" 
                onClick={() => setSummaryModal(prev => ({ ...prev, isOpen: false }))}
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default Dashboard;
