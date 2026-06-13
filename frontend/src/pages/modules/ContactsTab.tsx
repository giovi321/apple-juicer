import { useEffect, useState } from 'react';
import { api, type ContactRecord } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

function displayName(c: ContactRecord): string {
  const name = [c.first_name, c.last_name].filter(Boolean).join(' ').trim();
  return name || c.company || 'Unnamed contact';
}

export function ContactsTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<ContactRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listContacts(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load contacts');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading contacts…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No contacts found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-count">{items.length} contacts</div>
      <div className="artifact-cards">
        {items.map((c, i) => (
          <div key={c.contact_identifier ?? i} className="artifact-card">
            <div className="artifact-card-title">{displayName(c)}</div>
            {c.company && <div className="artifact-card-meta"><span>{c.company}</span></div>}
            <div>
              {c.phones.map((p) => (
                <span key={p} className="artifact-chip">📞 {p}</span>
              ))}
              {c.emails.map((e) => (
                <span key={e} className="artifact-chip">✉️ {e}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
