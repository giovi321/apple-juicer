import { useEffect, useState } from 'react';
import { api, type Voicemail } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import '../../styles/ArtifactTabs.css';

function formatDuration(seconds?: number | null): string {
  if (!seconds) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m ? `${m}m ${s}s` : `${s}s`;
}

export function VoicemailTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<Voicemail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listVoicemail(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load voicemail');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  const exportCsv = () =>
    downloadCsv(
      'voicemail.csv',
      ['Sender', 'Received', 'Duration (s)', 'Trashed'],
      items.map((v) => [v.sender, v.received_at, v.duration_seconds, v.trashed]),
    );

  if (loading) return <div className="loading">Loading voicemail…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No voicemail found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-toolbar">
        <span className="artifact-count">{items.length} voicemails</span>
        <button className="download-btn" onClick={exportCsv}>
          Download CSV
        </button>
      </div>
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Sender</th>
              <th>Received</th>
              <th>Duration</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((v, i) => (
              <tr key={v.voicemail_identifier ?? i}>
                <td>{v.sender || '—'}</td>
                <td>{v.received_at ? new Date(v.received_at).toLocaleString() : '—'}</td>
                <td>{formatDuration(v.duration_seconds)}</td>
                <td>{v.trashed ? '🗑 Deleted' : 'Inbox'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
