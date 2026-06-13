import { useEffect, useState } from 'react';
import { api, type CallRecord } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

function formatDuration(seconds?: number | null): string {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m ? `${m}m ${s}s` : `${s}s`;
}

function callLabel(c: CallRecord): string {
  if (c.is_outgoing) return '↗ Outgoing';
  return c.answered ? '↙ Incoming' : '✗ Missed';
}

export function CallsTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<CallRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listCalls(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load calls');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading calls…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No call history found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-count">{items.length} calls</div>
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Direction</th>
              <th>Contact</th>
              <th>When</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c, i) => (
              <tr key={c.call_identifier ?? i}>
                <td>{callLabel(c)}</td>
                <td>{c.display_name || c.address || '—'}</td>
                <td>{c.occurred_at ? new Date(c.occurred_at).toLocaleString() : '—'}</td>
                <td>{formatDuration(c.duration_seconds) || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
