import { useEffect, useState } from 'react';
import { api, type ManifestEntry } from '../../lib/api';

export function FilesModule({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [domains, setDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [files, setFiles] = useState<ManifestEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listDomains(backupId, apiToken)
      .then((res) => {
        if (!mounted) return;
        setDomains(res.domains);
        setSelectedDomain((current) => current ?? res.domains[0] ?? null);
        setLoading(false);
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load domains');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  useEffect(() => {
    if (!selectedDomain) return;
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .listFiles(backupId, apiToken, {
        domain: selectedDomain,
        path_like: searchTerm ? `%${searchTerm}%` : null,
        limit: 200,
      })
      .then((res) => {
        if (mounted) {
          setFiles(res.items);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mounted) {
          setError(e instanceof Error ? e.message : 'Failed to load files');
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken, selectedDomain, searchTerm]);

  const handleDownloadFile = async (fileId: string) => {
    try {
      const response = await api.downloadFile(backupId, fileId, apiToken);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileId;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  };

  return (
    <div className="files-module">
      <div className="files-controls">
        <div className="domain-selector">
          <select
            id="domain-select"
            value={selectedDomain || ''}
            onChange={(e) => setSelectedDomain(e.target.value)}
            disabled={loading}
          >
            {domains.map((domain) => (
              <option key={domain} value={domain}>
                {domain}
              </option>
            ))}
          </select>
        </div>
        <div className="search-box search-box-wide">
          <input
            type="text"
            placeholder="Search files..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            disabled={loading}
            autoComplete="off"
          />
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">Loading files...</div>
      ) : files.length === 0 ? (
        <div className="no-results">No files found in this domain.</div>
      ) : (
        <div className="files-list">
          <table>
            <thead>
              <tr>
                <th>File ID</th>
                <th>Path</th>
                <th>Size</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {files.map((file) => (
                <tr key={file.file_id}>
                  <td className="file-id">{file.file_id}</td>
                  <td className="file-path">{file.relative_path}</td>
                  <td className="file-size">{file.size ? `${(file.size / 1024).toFixed(2)} KB` : 'N/A'}</td>
                  <td className="file-action">
                    <button onClick={() => handleDownloadFile(file.file_id)} className="download-btn">
                      Download
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
