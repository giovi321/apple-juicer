import { useState } from 'react';
import { api, type SearchResult } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

const TYPE_META: Record<string, { label: string; icon: string }> = {
  photo: { label: 'Photo', icon: '🖼️' },
  whatsapp_message: { label: 'WhatsApp', icon: '💬' },
  message: { label: 'Message', icon: '📱' },
  note: { label: 'Note', icon: '📝' },
  calendar_event: { label: 'Event', icon: '🗓' },
  contact: { label: 'Contact', icon: '👤' },
};

export function SearchTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [query, setQuery] = useState('');
  const [items, setItems] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const term = query.trim();
    if (!term) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.search(backupId, term, apiToken);
      setItems(res.items);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="artifact-tab">
      <form className="artifact-toolbar" onSubmit={runSearch}>
        <input
          type="text"
          className="search-input search-box-wide"
          placeholder="Search messages, notes, contacts, events…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus
        />
        <button type="submit" className="download-btn" disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </form>

      {error && <div className="error-message">{error}</div>}
      {searched && !loading && !error && (
        <div className="artifact-count">
          {items.length} result{items.length === 1 ? '' : 's'}
        </div>
      )}

      {searched && !loading && !error && !items.length ? (
        <div className="no-results">No matches.</div>
      ) : (
        <div className="artifact-cards">
          {items.map((r, i) => {
            const meta = TYPE_META[r.artifact_type] ?? { label: r.artifact_type, icon: '🔎' };
            const context =
              (r.payload?.chat_guid as string | undefined) ??
              (r.payload?.conversation_guid as string | undefined) ??
              (r.payload?.calendar_name as string | undefined);
            return (
              <div key={`${r.artifact_type}-${r.artifact_ref}-${i}`} className="artifact-card">
                <div className="artifact-card-meta">
                  <span className="artifact-chip">
                    {meta.icon} {meta.label}
                  </span>
                  {context && <span>{context}</span>}
                </div>
                <div className="artifact-card-body">{r.display_text || r.artifact_ref}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
