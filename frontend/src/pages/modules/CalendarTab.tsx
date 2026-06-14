import { useEffect, useState } from 'react';
import { api, type CalendarEvent } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import '../../styles/ArtifactTabs.css';

function formatWhen(event: CalendarEvent): string {
  if (!event.starts_at) return '—';
  const start = new Date(event.starts_at);
  if (event.is_all_day) return `${start.toLocaleDateString()} (all day)`;
  const startStr = start.toLocaleString();
  if (!event.ends_at) return startStr;
  const end = new Date(event.ends_at);
  const sameDay = start.toDateString() === end.toDateString();
  return `${startStr} – ${sameDay ? end.toLocaleTimeString() : end.toLocaleString()}`;
}

export function CalendarTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listCalendarEvents(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load calendar events');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading calendar…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No calendar events found in this backup.</div>;

  const exportCsv = () =>
    downloadCsv(
      'calendar.csv',
      ['Title', 'Calendar', 'Starts', 'Ends', 'All day', 'Location', 'Notes'],
      items.map((e) => [e.title, e.calendar_name, e.starts_at, e.ends_at, e.is_all_day, e.location, e.notes]),
    );

  return (
    <div className="artifact-tab">
      <div className="artifact-toolbar">
        <span className="artifact-count">{items.length} events</span>
        <button className="download-btn" onClick={exportCsv}>
          Download CSV
        </button>
      </div>
      <div className="artifact-cards">
        {items.map((e, i) => (
          <div key={e.event_identifier ?? i} className="artifact-card">
            <div className="artifact-card-title">{e.title || 'Untitled event'}</div>
            <div className="artifact-card-meta">
              <span>{formatWhen(e)}</span>
              {e.location && <span>📍 {e.location}</span>}
              {e.calendar_name && <span>🗓 {e.calendar_name}</span>}
            </div>
            {e.notes && <div className="artifact-card-body">{e.notes}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
