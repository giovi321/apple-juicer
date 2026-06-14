import { useEffect, useState } from 'react';
import { api, type SafariVisit } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

export function SafariTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<SafariVisit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listSafari(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load history');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading history…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No Safari history found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-count">{items.length} visits</div>
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>URL</th>
              <th>Visited</th>
            </tr>
          </thead>
          <tbody>
            {items.map((v, i) => (
              <tr key={v.visit_identifier ?? i}>
                <td>{v.title || '—'}</td>
                <td>
                  {v.url ? (
                    <a href={v.url} target="_blank" rel="noreferrer">
                      {v.url}
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td>{v.visited_at ? new Date(v.visited_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
