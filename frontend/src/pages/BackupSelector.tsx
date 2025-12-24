import { useCallback, useEffect, useState } from 'react';
import { api, type BackupSummary } from '../lib/api';
import '../styles/BackupSelector.css';

interface BackupSelectorProps {
  apiToken: string;
  onBackupSelected: (backup: BackupSummary) => void;
  refreshTrigger?: number;
  externalMessage?: string | null;
  decryptingBackupId?: string | null;
}

interface DeleteConfirmModalProps {
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirmModal({ onConfirm, onCancel }: DeleteConfirmModalProps) {
  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h3>⚠️ Delete Decrypted Data</h3>
        <p>This will permanently delete all decrypted data for this backup.</p>
        <p><strong>Warning:</strong> This action cannot be undone. The encrypted backup will remain intact.</p>
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onCancel}>Cancel</button>
          <button className="btn-delete" onClick={onConfirm}>Delete</button>
        </div>
      </div>
    </div>
  );
}

export function BackupSelector({
  apiToken,
  onBackupSelected,
  refreshTrigger,
  externalMessage,
  decryptingBackupId,
}: BackupSelectorProps) {
  const [backups, setBackups] = useState<BackupSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [backupToDelete, setBackupToDelete] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  // Determine if any blocking action is in progress (decrypting or deleting)
  const isBlockingAction = !!decryptingBackupId || !!actionInProgress;

  const fetchBackups = useCallback(async () => {
    if (!apiToken) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listBackups(apiToken);
      setBackups(response.backups);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load backups');
    } finally {
      setLoading(false);
    }
  }, [apiToken]);

  const handleRefresh = useCallback(async () => {
    if (!apiToken) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.refreshBackups(apiToken);
      setBackups(response.backups);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh backups');
    } finally {
      setLoading(false);
    }
  }, [apiToken]);

  useEffect(() => {
    void fetchBackups();
  }, [fetchBackups, refreshTrigger]);

  const formatBytes = (bytes: number | null | undefined): string => {
    if (!bytes) return 'Unknown';
    const gb = bytes / (1024 * 1024 * 1024);
    return gb.toFixed(2) + ' GB';
  };

  const formatDate = (date: string | null | undefined): string => {
    if (!date) return 'Never';
    const d = new Date(date);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}/${month}/${year}`;
  };

  const handleDeleteDecryptedData = async (backupId: string) => {
    setShowDeleteModal(false);
    setBackupToDelete(null);
    setActionInProgress(backupId);
    try {
      await api.deleteDecryptedData(backupId, apiToken);
      await fetchBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete decrypted data');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleCardClick = (backup: BackupSummary, e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) {
      return;
    }
    // Disable card clicks during decryption or deletion
    if (isBlockingAction) {
      return;
    }
    onBackupSelected(backup);
  };

  return (
    <div className="backup-selector">
      <div className="backup-selector-header">
        <button onClick={handleRefresh} disabled={loading || isBlockingAction} className="refresh-btn">
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {externalMessage && /fail|error/i.test(externalMessage) && (
        <div className="action-message error">
          {externalMessage}
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {loading && backups.length === 0 ? (
        <div className="loading">Loading backups...</div>
      ) : backups.length === 0 ? (
        <div className="no-backups">No backups found. Please check your configuration.</div>
      ) : (
        <div className="backups-grid">
          {backups.map((backup) => (
            <div
              key={backup.id}
              className={`backup-card ${isBlockingAction ? 'disabled' : ''}`}
              onClick={(e) => handleCardClick(backup, e)}
            >
              <div className="backup-card-header">
                <div className="backup-title-section">
                  <h3>{backup.display_name}</h3>
                  <span className="backup-folder-name">{backup.id}</span>
                </div>
                {(() => {
                  const isDecrypting =
                    decryptingBackupId === backup.id || backup.decryption_status === 'decrypting';
                  const isDeleting = actionInProgress === backup.id;
                  
                  let statusKey: string;
                  let statusLabel: string;
                  
                  if (isDeleting) {
                    statusKey = 'deleting';
                    statusLabel = 'deleting...';
                  } else if (isDecrypting) {
                    statusKey = 'decrypting';
                    statusLabel = 'decrypting...';
                  } else if (backup.decryption_status === 'pending') {
                    statusKey = 'encrypted';
                    statusLabel = 'encrypted';
                  } else {
                    statusKey = backup.decryption_status;
                    statusLabel = backup.decryption_status;
                  }

                  return (
                    <span className={`status-badge status-${statusKey}${isDecrypting || isDeleting ? ' pulsate' : ''}`}>
                      {statusLabel}
                    </span>
                  );
                })()}
              </div>
              <div className="backup-card-details">
                {backup.device_name && (
                  <div className="detail">
                    <span className="label">Device:</span>
                    <span className="value">{backup.device_name}</span>
                  </div>
                )}
                {backup.product_version && (
                  <div className="detail">
                    <span className="label">Version:</span>
                    <span className="value">{backup.product_version}</span>
                  </div>
                )}
                <div className="detail">
                  <span className="label">Size:</span>
                  <span className="value">{formatBytes(backup.size_bytes)}</span>
                </div>
                <div className="detail">
                  <span className="label">Last Modified:</span>
                  <span className="value">{formatDate(backup.last_modified_at)}</span>
                </div>
                {backup.decrypted_at && (
                  <div className="detail">
                    <span className="label">Decrypted:</span>
                    <span className="value">{formatDate(backup.decrypted_at)}</span>
                  </div>
                )}
              </div>
              <div className="backup-card-footer">
                <span className="encryption-status">
                  {backup.is_encrypted ? '🔒 Encrypted' : '🔓 Unencrypted'}
                </span>
                {backup.decryption_status === 'decrypted' && (
                  <div className="backup-actions">
                    <button
                      className="btn-redecrypt"
                      onClick={(e) => {
                        e.stopPropagation();
                        onBackupSelected(backup);
                      }}
                      disabled={actionInProgress === backup.id}
                    >
                      Re-decrypt
                    </button>
                    <button
                      className="btn-delete-data"
                      onClick={(e) => {
                        e.stopPropagation();
                        setBackupToDelete(backup.id);
                        setShowDeleteModal(true);
                      }}
                      disabled={actionInProgress === backup.id}
                    >
                      {actionInProgress === backup.id ? 'Deleting...' : 'Delete Data'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {showDeleteModal && backupToDelete && (
        <DeleteConfirmModal
          onConfirm={() => handleDeleteDecryptedData(backupToDelete)}
          onCancel={() => {
            setShowDeleteModal(false);
            setBackupToDelete(null);
          }}
        />
      )}
    </div>
  );
}
