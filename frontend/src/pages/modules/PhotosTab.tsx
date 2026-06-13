import { useEffect, useState } from 'react';
import { api, type PhotoAsset } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

export function PhotosTab({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<PhotoAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listPhotos(backupId, apiToken)
      .then((res) => {
        if (mounted) {
          setItems(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load photos');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  if (loading) return <div className="loading">Loading photos…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No photos found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-count">{items.length} photos</div>
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Taken</th>
              <th>Type</th>
              <th>Dimensions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p, i) => (
              <tr key={p.asset_id ?? p.file_id ?? `${p.original_filename}-${i}`}>
                <td>{p.original_filename || p.relative_path || '—'}</td>
                <td>{p.taken_at ? new Date(p.taken_at).toLocaleString() : '—'}</td>
                <td>{p.media_type || '—'}</td>
                <td>{p.width && p.height ? `${p.width}×${p.height}` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
