import { useEffect, useState } from 'react';
import { api, type TimelineEvent } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

const ICONS: Record<string, string> = {
  whatsapp_message: '💬',
  message: '📱',
  call: '📞',
  calendar_event: '🗓',
  photo: '🖼️',
  safari: '🌐',
  location: '📍',
  voicemail: '📭',
  note: '📝',
};

export function TimelineTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .getTimeline(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load timeline');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading timeline…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No timestamped activity found in this backup.</div>;

  let lastDay = '';

  return (
    <div className="artifact-tab">
      <div className="artifact-count">{items.length} most recent events</div>
      <div className="artifact-cards">
        {items.map((e, i) => {
          const date = new Date(e.timestamp);
          const day = date.toLocaleDateString();
          const showDay = day !== lastDay;
          lastDay = day;
          return (
            <div key={`${e.artifact_type}-${e.timestamp}-${i}`}>
              {showDay && (
                <div className="artifact-card-meta" style={{ marginTop: i ? '0.5rem' : 0, fontWeight: 600 }}>
                  {day}
                </div>
              )}
              <div className="artifact-card">
                <div className="artifact-card-meta">
                  <span className="artifact-chip">{ICONS[e.artifact_type] ?? '•'}</span>
                  <span>{date.toLocaleTimeString()}</span>
                  {e.subtitle && <span>{e.subtitle}</span>}
                </div>
                <div className="artifact-card-body">{e.title || ''}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
