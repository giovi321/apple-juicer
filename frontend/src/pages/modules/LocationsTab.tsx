import { useEffect, useState } from 'react';
import { api, type LocationPoint } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import '../../styles/ArtifactTabs.css';

export function LocationsTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<LocationPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listLocations(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load locations');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  const exportCsv = () =>
    downloadCsv(
      'locations.csv',
      ['Recorded', 'Latitude', 'Longitude', 'Altitude (m)', 'Speed', 'Accuracy (m)'],
      items.map((l) => [l.recorded_at, l.latitude, l.longitude, l.altitude, l.speed, l.horizontal_accuracy]),
    );

  if (loading) return <div className="loading">Loading locations…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) {
    return (
      <div className="no-results">
        No location data found in this backup. (Location caches are often excluded from iOS backups.)
      </div>
    );
  }

  return (
    <div className="artifact-tab">
      <div className="artifact-toolbar">
        <span className="artifact-count">{items.length} points</span>
        <button className="download-btn" onClick={exportCsv}>
          Download CSV
        </button>
      </div>
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Recorded</th>
              <th>Latitude</th>
              <th>Longitude</th>
              <th>Accuracy</th>
              <th>Map</th>
            </tr>
          </thead>
          <tbody>
            {items.map((l, i) => (
              <tr key={l.location_identifier ?? i}>
                <td>{l.recorded_at ? new Date(l.recorded_at).toLocaleString() : '—'}</td>
                <td>{l.latitude ?? '—'}</td>
                <td>{l.longitude ?? '—'}</td>
                <td>{l.horizontal_accuracy != null ? `${l.horizontal_accuracy} m` : '—'}</td>
                <td>
                  {l.latitude != null && l.longitude != null ? (
                    <a
                      href={`https://www.openstreetmap.org/?mlat=${l.latitude}&mlon=${l.longitude}#map=15/${l.latitude}/${l.longitude}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Open
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
