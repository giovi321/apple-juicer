import { useState } from 'react';
import { api, type BackupSummary } from '../lib/api';
import '../styles/PasswordPrompt.css';

interface PasswordPromptProps {
  apiToken: string;
  backup: BackupSummary;
  onDecryptComplete: () => void;
  onCancel: () => void;
}

export function PasswordPrompt({ apiToken, backup, onDecryptComplete, onCancel }: PasswordPromptProps) {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decryptionStatus, setDecryptionStatus] = useState<string | null>(null);

  const handleDecrypt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError(null);
    setDecryptionStatus('Starting decryption...');

    try {
      const response = await api.decryptBackup(backup.id, password, apiToken);
      
      if (response.decryption_status === 'decrypted') {
        setDecryptionStatus('Decryption complete!');
        setTimeout(() => onDecryptComplete(), 1000);
      } else if (response.decryption_status === 'failed') {
        setError(response.error || 'Decryption failed');
        setDecryptionStatus(null);
      } else {
        setDecryptionStatus(`Status: ${response.decryption_status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decryption failed');
      setDecryptionStatus(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="password-prompt-overlay">
      <div className="password-prompt-modal">
        <div className="modal-header">
          <h2>Decrypt Backup</h2>
          <button className="close-btn" onClick={onCancel} disabled={loading}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="backup-info">
            <h3>{backup.display_name}</h3>
            {backup.device_name && <p className="device-name">{backup.device_name}</p>}
          </div>

          <form onSubmit={handleDecrypt}>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter backup password"
                disabled={loading}
                autoFocus
              />
            </div>

            {error && <div className="error-message">{error}</div>}
            {decryptionStatus && <div className="status-message">{decryptionStatus}</div>}

            <div className="form-actions">
              <button type="button" onClick={onCancel} disabled={loading} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={loading} className="btn-primary">
                {loading ? 'Decrypting...' : 'Decrypt'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
