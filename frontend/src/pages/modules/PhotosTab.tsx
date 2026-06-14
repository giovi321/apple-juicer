import { useEffect, useState } from 'react';
import { api, type PhotoAsset } from '../../lib/api';
import { downloadCsv } from '../../lib/csv';
import '../../styles/ArtifactTabs.css';

function fileName(p: PhotoAsset): string {
  return p.original_filename || p.relative_path?.split('/').pop() || 'photo';
}

export function PhotosTab({
  apiToken,
  backupId,
  sessionToken,
}: {
  apiToken: string;
  backupId: string;
  sessionToken?: string;
}) {
  const [items, setItems] = useState<PhotoAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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

  const exportCsv = () =>
    downloadCsv(
      'photos.csv',
      ['Filename', 'Taken', 'Type', 'Width', 'Height', 'Relative path'],
      items.map((p) => [p.original_filename, p.taken_at, p.media_type, p.width, p.height, p.relative_path]),
    );

  const viewPhoto = async (relativePath: string) => {
    setBusy(true);
    setError(null);
    try {
      const response = await api.downloadPhotoFile(backupId, relativePath, apiToken, sessionToken);
      const blob = await response.blob();
      setPreview(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load photo');
    } finally {
      setBusy(false);
    }
  };

  const savePhoto = async (relativePath: string, name: string) => {
    setBusy(true);
    setError(null);
    try {
      const response = await api.downloadPhotoFile(backupId, relativePath, apiToken, sessionToken);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Download failed');
    } finally {
      setBusy(false);
    }
  };

  const closePreview = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null);
  };

  if (loading) return <div className="loading">Loading photos…</div>;
  if (error && !items.length) return <div className="error-message">{error}</div>;
  if (!items.length) return <div className="no-results">No photos found in this backup.</div>;

  return (
    <div className="artifact-tab">
      <div className="artifact-toolbar">
        <span className="artifact-count">{items.length} photos</span>
        <button className="download-btn" onClick={exportCsv}>
          Download CSV
        </button>
        {busy && <span className="artifact-count">Loading image…</span>}
      </div>
      {error && <div className="error-message">{error}</div>}
      {!sessionToken && (
        <div className="error-message">Unlock the backup (Attachments) to view or download the actual images.</div>
      )}
      <div className="artifact-scroll">
        <table className="artifact-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Taken</th>
              <th>Type</th>
              <th>Dimensions</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((p, i) => {
              const rp = p.relative_path;
              return (
                <tr key={p.asset_id ?? p.file_id ?? `${p.original_filename}-${i}`}>
                  <td>{fileName(p)}</td>
                  <td>{p.taken_at ? new Date(p.taken_at).toLocaleString() : '—'}</td>
                  <td>{p.media_type || '—'}</td>
                  <td>{p.width && p.height ? `${p.width}×${p.height}` : '—'}</td>
                  <td>
                    {rp && sessionToken ? (
                      <>
                        <button className="download-btn" disabled={busy} onClick={() => viewPhoto(rp)}>
                          View
                        </button>{' '}
                        <button className="download-btn" disabled={busy} onClick={() => savePhoto(rp, fileName(p))}>
                          ⬇
                        </button>
                      </>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {preview && (
        <div className="image-preview-modal" onClick={closePreview}>
          <div className="image-preview-content" onClick={(e) => e.stopPropagation()}>
            <button className="image-preview-close" onClick={closePreview}>
              ✕
            </button>
            <img src={preview} alt="Preview" />
          </div>
        </div>
      )}
    </div>
  );
}
