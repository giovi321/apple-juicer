import { useEffect, useState } from 'react';
import { api, type NoteRecord } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import '../../styles/ArtifactTabs.css';

export function NotesTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<NoteRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listNotes(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load notes');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading notes…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No notes found in this backup.</div>;

  const exportCsv = () =>
    downloadCsv(
      'notes.csv',
      ['Title', 'Folder', 'Modified', 'Created', 'Body'],
      items.map((n) => [n.title, n.folder, n.last_modified_at, n.created_at, n.body]),
    );

  return (
    <div className="artifact-tab">
      <div className="artifact-toolbar">
        <span className="artifact-count">{items.length} notes</span>
        <button className="download-btn" onClick={exportCsv}>
          Download CSV
        </button>
      </div>
      <div className="artifact-cards">
        {items.map((n, i) => (
          <div key={n.note_identifier ?? i} className="artifact-card">
            <div className="artifact-card-title">{n.title || 'Untitled note'}</div>
            <div className="artifact-card-meta">
              {n.folder && <span>{n.folder}</span>}
              {n.last_modified_at && <span>{new Date(n.last_modified_at).toLocaleString()}</span>}
            </div>
            {n.body && <div className="artifact-card-body">{n.body}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
