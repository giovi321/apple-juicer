import { useState } from 'react';
import type { BackupSummary } from '../lib/api';
import '../styles/PasswordPrompt.css';

interface PasswordPromptProps {
  backup: BackupSummary;
  onSubmitPassword: (password: string) => void;
  onCancel: () => void;
}

export function PasswordPrompt({ backup, onSubmitPassword, onCancel }: PasswordPromptProps) {
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDecrypt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Password is required');
      return;
    }

    setLoading(true);
    setError(null);
    onSubmitPassword(password);
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
