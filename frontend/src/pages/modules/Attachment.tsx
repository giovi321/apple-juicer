import { useEffect, useRef, useState } from 'react';

export interface AttachmentLike {
  relative_path?: string | null;
  file_id?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
}

export interface AttachmentProps {
  attachment: AttachmentLike;
  extracted: boolean;
  /** Fetch the attachment's bytes. Memoize in the parent (useCallback) so the
   *  loaders only re-run when the backup/token/session actually change. */
  loadBlob: (relativePath: string) => Promise<Blob>;
  onPreview: (objectUrl: string) => void;
  onDownload: (relativePath: string, filename: string) => void;
}

function guessFilename(a: AttachmentLike): string {
  const rp = a.relative_path ?? '';
  const last = rp.split('/').filter(Boolean).pop();
  return last || a.file_id || 'attachment';
}

function sizeLabel(bytes?: number | null): string {
  return bytes ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : '';
}

function iconFor(mime?: string | null): string {
  if (mime?.startsWith('image/')) return '🖼️';
  if (mime?.startsWith('video/')) return '🎬';
  if (mime?.startsWith('audio/')) return '🎵';
  return '📄';
}

function AttachmentImage({
  relativePath,
  filename,
  loadBlob,
  onPreview,
  onDownload,
}: {
  relativePath: string;
  filename: string;
  loadBlob: (relativePath: string) => Promise<Blob>;
  onPreview: (objectUrl: string) => void;
  onDownload: (relativePath: string, filename: string) => void;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    let objectUrl: string | null = null;
    loadBlob(relativePath)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (mounted) {
          setImageUrl(objectUrl);
          setLoading(false);
          setError(null);
        } else {
          URL.revokeObjectURL(objectUrl);
        }
      })
      .catch((err) => {
        if (mounted) {
          setLoading(false);
          setError(err instanceof Error ? err.message : 'Failed to load');
        }
      });
    return () => {
      mounted = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [relativePath, loadBlob]);

  if (loading) return <div className="attachment-loading">Loading image...</div>;
  if (error || !imageUrl) return <div className="attachment-error">Failed to load image: {error}</div>;

  return (
    <div className="attachment-image-wrapper">
      <img src={imageUrl} alt={filename} className="attachment-image" onClick={() => onPreview(imageUrl)} />
      <button
        className="attachment-download-overlay"
        onClick={(e) => {
          e.stopPropagation();
          onDownload(relativePath, filename);
        }}
        title="Download"
      >
        ⬇️
      </button>
    </div>
  );
}

function AttachmentMedia({
  relativePath,
  mimeType,
  kind,
  filename,
  loadBlob,
  onDownload,
}: {
  relativePath: string;
  mimeType: string | null;
  kind: 'video' | 'audio';
  filename: string;
  loadBlob: (relativePath: string) => Promise<Blob>;
  onDownload: (relativePath: string, filename: string) => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    let mounted = true;
    let objectUrl: string | null = null;
    loadBlob(relativePath)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (mounted) {
          setUrl(objectUrl);
          setLoading(false);
        } else {
          URL.revokeObjectURL(objectUrl);
        }
      })
      .catch((e) => {
        if (mounted) {
          setLoading(false);
          setError(e instanceof Error ? e.message : 'Failed to load media');
        }
      });
    return () => {
      mounted = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [relativePath, loadBlob]);

  useEffect(() => {
    if (kind !== 'audio') return;
    const el = audioRef.current;
    if (!el) return;
    const onLoaded = () => setDuration(Number.isFinite(el.duration) ? el.duration : 0);
    const onTime = () => setCurrentTime(el.currentTime || 0);
    const onEnded = () => setIsPlaying(false);
    el.addEventListener('loadedmetadata', onLoaded);
    el.addEventListener('timeupdate', onTime);
    el.addEventListener('ended', onEnded);
    return () => {
      el.removeEventListener('loadedmetadata', onLoaded);
      el.removeEventListener('timeupdate', onTime);
      el.removeEventListener('ended', onEnded);
    };
  }, [kind, url]);

  const toggleAudio = async () => {
    const el = audioRef.current;
    if (!el) return;
    if (el.paused) {
      await el.play();
      setIsPlaying(true);
    } else {
      el.pause();
      setIsPlaying(false);
    }
  };

  const seekAudio = (value: number) => {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = value;
    setCurrentTime(value);
  };

  if (loading) return <div className="attachment-loading">Loading media...</div>;
  if (error || !url) return <div className="attachment-error">Failed to load media: {error}</div>;

  if (kind === 'video') {
    return (
      <div className="attachment-video-wrapper">
        <video controls className="attachment-video">
          <source src={url} type={mimeType ?? undefined} />
        </video>
        <button className="attachment-download-overlay" onClick={() => onDownload(relativePath, filename)}>
          ⬇️
        </button>
      </div>
    );
  }

  return (
    <div className="attachment-audio-wrapper">
      <button className="audio-mini-btn" onClick={toggleAudio}>
        {isPlaying ? 'Pause' : 'Play'}
      </button>
      <input
        className="audio-mini-range"
        type="range"
        min={0}
        max={duration || 0}
        step={0.01}
        value={Math.min(currentTime, duration || 0)}
        onChange={(e) => seekAudio(Number(e.target.value))}
      />
      <audio ref={audioRef} preload="metadata" src={url} />
      <button className="attachment-download-btn-small" onClick={() => onDownload(relativePath, filename)}>
        ⬇️
      </button>
    </div>
  );
}

/** Shared renderer for WhatsApp and Messages attachments. */
export function Attachment({ attachment, extracted, loadBlob, onPreview, onDownload }: AttachmentProps) {
  if (!attachment.relative_path) return null;
  const relativePath = attachment.relative_path;
  const filename = guessFilename(attachment);
  const mime = attachment.mime_type;

  if (!extracted) {
    return (
      <div className="attachment-placeholder">
        <span className="attachment-icon">{iconFor(mime)}</span>
        <span className="attachment-name">{filename}</span>
        <span className="attachment-size">{sizeLabel(attachment.size_bytes)}</span>
        <span className="attachment-hint">Extract files to view</span>
      </div>
    );
  }

  if (mime?.startsWith('image/')) {
    return (
      <div className="attachment-image-wrapper">
        <AttachmentImage
          relativePath={relativePath}
          filename={filename}
          loadBlob={loadBlob}
          onPreview={onPreview}
          onDownload={onDownload}
        />
      </div>
    );
  }

  if (mime?.startsWith('video/')) {
    return (
      <AttachmentMedia
        relativePath={relativePath}
        mimeType={mime}
        kind="video"
        filename={filename}
        loadBlob={loadBlob}
        onDownload={onDownload}
      />
    );
  }

  if (mime?.startsWith('audio/')) {
    return (
      <AttachmentMedia
        relativePath={relativePath}
        mimeType={mime}
        kind="audio"
        filename={filename}
        loadBlob={loadBlob}
        onDownload={onDownload}
      />
    );
  }

  return (
    <div className="attachment-file">
      <span className="attachment-icon">📄</span>
      <span className="attachment-name">{filename}</span>
      <span className="attachment-size">{sizeLabel(attachment.size_bytes)}</span>
      <button className="attachment-download-btn-small" onClick={() => onDownload(relativePath, filename)}>
        ⬇️
      </button>
    </div>
  );
}
