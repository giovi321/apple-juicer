import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  type BackupSummary,
  type WhatsAppAttachment,
  type WhatsAppChat,
  type WhatsAppMessage,
} from '../../lib/api';
import { Attachment } from './Attachment';

const MESSAGE_BATCH_SIZE = 100;

function formatWhatsAppSender(
  sender: string | null,
  senderName: string | null,
  isFromMe: boolean,
  chatTitle?: string | null,
) {
  if (isFromMe) return 'You';
  const extractPhone = (jid: string | null): string | null => {
    if (!jid) return null;
    const trimmed = String(jid).trim();
    if (!trimmed) return null;
    const optionalPrefix = 'Optional(';
    const unwrapped =
      trimmed.startsWith(optionalPrefix) && trimmed.endsWith(')') ? trimmed.slice(optionalPrefix.length, -1) : trimmed;
    const atSplit = unwrapped.includes('@') ? unwrapped.split('@')[0] : unwrapped;
    const phone = atSplit.replace(/^whatsapp:/i, '').trim();
    return phone || null;
  };
  const looksLikePhone = (str: string | null): boolean => {
    if (!str) return false;
    return /^\+?[\d\s\-().]{7,}$/.test(str.trim());
  };
  const phone = extractPhone(sender);
  const name = senderName?.trim() || null;
  if (name && phone && looksLikePhone(phone)) return `${name} (+${phone.replace(/^\+/, '')})`;
  if (name) return name;
  if (phone && looksLikePhone(phone)) return `+${phone.replace(/^\+/, '')}`;
  if (chatTitle?.trim()) {
    if (phone && looksLikePhone(phone)) return `${chatTitle.trim()} (+${phone.replace(/^\+/, '')})`;
    return chatTitle.trim();
  }
  if (phone) return phone;
  return 'Unknown';
}

interface Props {
  apiToken: string;
  backup: BackupSummary;
  sessionToken?: string;
  onSessionToken?: (token: string) => void;
  initialSelectedGuid?: string;
  onOpenPerson?: (personKey: string) => void;
}

export function WhatsAppModule({
  apiToken,
  backup,
  sessionToken,
  onSessionToken,
  initialSelectedGuid,
  onOpenPerson,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [chats, setChats] = useState<WhatsAppChat[]>([]);
  const [selectedChatGuid, setSelectedChatGuid] = useState<string | null>(initialSelectedGuid ?? null);
  const [messages, setMessages] = useState<WhatsAppMessage[]>([]);
  const [displayedMessages, setDisplayedMessages] = useState<WhatsAppMessage[]>([]);
  const [messageOffset, setMessageOffset] = useState(0);
  const [chatSearchTerm, setChatSearchTerm] = useState('');
  const [messageSearchTerm, setMessageSearchTerm] = useState('');
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [backupData, setBackupData] = useState<BackupSummary>(backup);
  const messagesListRef = useRef<HTMLDivElement | null>(null);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [extractedChats, setExtractedChats] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (initialSelectedGuid) setSelectedChatGuid(initialSelectedGuid);
  }, [initialSelectedGuid]);

  const fetchChats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listWhatsAppChats(backup.id, apiToken);
      const sorted = response.items.sort((a, b) => {
        const da = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const db = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return db - da;
      });
      setChats(sorted);
      setSelectedChatGuid((current) => current ?? (sorted[0]?.chat_guid ?? null));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WhatsApp chats');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken]);

  const fetchMessages = useCallback(async () => {
    if (!selectedChatGuid) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listWhatsAppMessages(backup.id, selectedChatGuid, apiToken);
      const sorted = [...response.messages].sort((a, b) => {
        const da = a.sent_at ? new Date(a.sent_at).getTime() : 0;
        const db = b.sent_at ? new Date(b.sent_at).getTime() : 0;
        return da - db;
      });
      setMessages(sorted);
      const initialOffset = Math.max(0, sorted.length - MESSAGE_BATCH_SIZE);
      setDisplayedMessages(sorted.slice(initialOffset));
      setMessageOffset(initialOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WhatsApp messages');
    } finally {
      setLoading(false);
    }
  }, [backup.id, selectedChatGuid, apiToken]);

  // On mount: refresh indexing status, then load chats if not indexing.
  useEffect(() => {
    setStatusLoaded(false);
    api
      .listBackups(apiToken)
      .then((response) => {
        const updated = response.backups.find((b) => b.id === backup.id);
        if (updated) {
          setBackupData(updated);
          const indexing = updated.indexing_artifact !== null && updated.indexing_artifact !== undefined;
          if (!indexing) void fetchChats();
          else {
            setChats([]);
            setSelectedChatGuid(null);
          }
        }
        setStatusLoaded(true);
      })
      .catch(() => setStatusLoaded(true));
  }, [apiToken, backup.id, fetchChats]);

  useEffect(() => {
    if (selectedChatGuid) void fetchMessages();
  }, [selectedChatGuid, fetchMessages]);

  const isIndexing = backupData.indexing_artifact !== null && backupData.indexing_artifact !== undefined;
  const isIndexingWhatsApp = backupData.indexing_artifact === 'whatsapp';

  useEffect(() => {
    if (!isIndexing) return;
    const interval = setInterval(async () => {
      try {
        const response = await api.listBackups(apiToken);
        const updated = response.backups.find((b) => b.id === backup.id);
        if (updated) {
          setBackupData(updated);
          if (updated.indexing_artifact === null || updated.indexing_artifact === undefined) void fetchChats();
        }
      } catch {
        /* ignore polling errors */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [isIndexing, apiToken, backup.id, fetchChats]);

  const filteredMessages = useMemo(() => {
    const term = messageSearchTerm.trim().toLowerCase();
    if (!term) return messages;
    return messages.filter(
      (m) => (m.body ?? '').toLowerCase().includes(term) || (m.sender ?? '').toLowerCase().includes(term),
    );
  }, [messages, messageSearchTerm]);

  useEffect(() => {
    const initialOffset = Math.max(0, filteredMessages.length - MESSAGE_BATCH_SIZE);
    setDisplayedMessages(filteredMessages.slice(initialOffset));
    setMessageOffset(initialOffset);
  }, [filteredMessages]);

  useEffect(() => {
    if (!messagesListRef.current || loading) return;
    messagesListRef.current.scrollTop = messagesListRef.current.scrollHeight;
  }, [selectedChatGuid, loading]);

  const loadMore = useCallback(() => {
    if (messageOffset <= 0) return;
    const nextOffset = Math.max(0, messageOffset - MESSAGE_BATCH_SIZE);
    setDisplayedMessages(filteredMessages.slice(nextOffset));
    setMessageOffset(nextOffset);
  }, [filteredMessages, messageOffset]);

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      if (e.currentTarget.scrollTop <= 100) loadMore();
    },
    [loadMore],
  );

  const waLoadBlob = useCallback(
    (rp: string) => api.downloadWhatsAppAttachment(backup.id, rp, apiToken, sessionToken).then((r) => r.blob()),
    [backup.id, apiToken, sessionToken],
  );

  const handleDownloadAttachment = useCallback(
    async (relativePath: string, filename: string) => {
      try {
        const response = await api.downloadWhatsAppAttachment(backup.id, relativePath, apiToken, sessionToken);
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Download failed');
      }
    },
    [backup.id, apiToken, sessionToken],
  );

  const handleUnlock = async () => {
    if (!unlockPassword.trim()) {
      setError('Password is required to unlock attachments');
      return;
    }
    setUnlocking(true);
    setError(null);
    try {
      const result = await api.unlockBackup(backup.id, unlockPassword, apiToken);
      onSessionToken?.(result.session_token);
      setUnlockPassword('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unlock failed');
    } finally {
      setUnlocking(false);
    }
  };

  const handleExtract = async () => {
    if (!sessionToken) {
      setError('Please unlock the backup first to extract files');
      return;
    }
    if (!selectedChatGuid) {
      setError('Please select a chat first');
      return;
    }
    setExtracting(true);
    setError(null);
    try {
      const result = await api.extractWhatsAppFiles(backup.id, selectedChatGuid, apiToken, sessionToken);
      setExtractedChats((prev) => new Set(prev).add(selectedChatGuid));
      const sizeMB = (result.extracted_bytes / 1024 / 1024).toFixed(2);
      alert(`Extracted ${result.extracted_files} files (${sizeMB} MB) for this chat. Attachments will now load.`);
      void fetchMessages();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  const filteredChats = chats.filter((chat) => {
    if (!chatSearchTerm) return true;
    const search = chatSearchTerm.toLowerCase();
    return (chat.title?.toLowerCase() || '').includes(search) || (chat.chat_guid?.toLowerCase() || '').includes(search);
  });

  const isChatExtracted = selectedChatGuid ? extractedChats.has(selectedChatGuid) : false;
  const selectedChat = useMemo(
    () => chats.find((c) => c.chat_guid === selectedChatGuid) || null,
    [chats, selectedChatGuid],
  );
  // Only 1:1 chats map to a single person; groups aren't in the People view.
  const chatIsOneToOne = useMemo(() => {
    if (!selectedChat) return false;
    if ((selectedChat.chat_guid || '').includes('g.us')) return false;
    return selectedChat.participant_count == null || selectedChat.participant_count <= 2;
  }, [selectedChat]);

  return (
    <>
      {extracting && (
        <div className="extraction-overlay">
          <div className="extraction-overlay-content">
            <div className="extraction-spinner"></div>
            <div>Extracting attachments...</div>
          </div>
        </div>
      )}
      <div className="whatsapp-module">
        <div className="whatsapp-container">
          <div className="whatsapp-chats-list">
            <div className="whatsapp-header">
              <h3>WhatsApp Chats</h3>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <input
                type="text"
                placeholder="Search chats..."
                value={chatSearchTerm}
                onChange={(e) => setChatSearchTerm(e.target.value)}
                className="search-input"
                disabled={extracting}
              />
            </div>
            {!statusLoaded ? (
              <div className="loading">Loading...</div>
            ) : isIndexingWhatsApp ? (
              <div className="loading">Indexing WhatsApp... please wait.</div>
            ) : loading && !chats.length ? (
              <div className="loading">Loading chats...</div>
            ) : chats.length === 0 ? (
              <div className="no-results">No WhatsApp chats found in this backup.</div>
            ) : (
              <div className="chats-list scrollable">
                {filteredChats.map((chat) => (
                  <button
                    key={chat.chat_guid}
                    className={`chat-item ${selectedChatGuid === chat.chat_guid ? 'active' : ''}`}
                    onClick={() => setSelectedChatGuid(chat.chat_guid)}
                    disabled={extracting}
                  >
                    <div className="chat-title">{chat.title || chat.chat_guid}</div>
                    {chat.last_message_at && (
                      <div className="chat-date">{new Date(chat.last_message_at).toLocaleDateString()}</div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="whatsapp-messages">
            {selectedChatGuid ? (
              <>
                <div className="whatsapp-header">
                  <h3>{selectedChat?.title || 'Chat'}</h3>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="Search messages..."
                      value={messageSearchTerm}
                      onChange={(e) => setMessageSearchTerm(e.target.value)}
                      className="search-input search-box-wide"
                      disabled={extracting}
                    />
                    {isChatExtracted ? (
                      <button className="download-btn extracted" disabled title="Files already extracted for this chat">
                        ✓ Files Extracted
                      </button>
                    ) : (
                      <button
                        className={`download-btn ${extracting ? 'extracting' : ''}`}
                        onClick={handleExtract}
                        disabled={extracting || !sessionToken}
                        title={!sessionToken ? 'Unlock backup first' : 'Extract files for this chat'}
                      >
                        {extracting ? 'Extracting...' : 'Extract Chat Files'}
                      </button>
                    )}
                  </div>
                </div>
                {!sessionToken && (
                  <div className="error-message">
                    <div style={{ marginBottom: '0.75rem' }}>
                      Attachments require an unlocked session. Enter the backup password to unlock downloads.
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <input
                        type="password"
                        placeholder="Backup password"
                        value={unlockPassword}
                        onChange={(e) => setUnlockPassword(e.target.value)}
                        className="search-input"
                        disabled={unlocking || extracting}
                      />
                      <button className="download-btn" onClick={handleUnlock} disabled={unlocking || extracting}>
                        {unlocking ? 'Unlocking...' : 'Unlock Attachments'}
                      </button>
                    </div>
                  </div>
                )}
                {loading && <div className="loading">Loading messages...</div>}
                {error && <div className="error-message">{error}</div>}
                {!loading && !error && (
                  <div ref={messagesListRef} className="messages-list scrollable" onScroll={handleScroll}>
                    {displayedMessages.map((message, index) => (
                      <div
                        key={message.message_id || index}
                        className={`message ${message.is_from_me ? 'from-me' : 'from-other'}`}
                      >
                        {!message.is_from_me && (
                          <div className="message-sender">
                            {onOpenPerson && message.person_key && chatIsOneToOne ? (
                              <button
                                type="button"
                                className="sender-link"
                                onClick={() => onOpenPerson(message.person_key!)}
                                title="View this person"
                              >
                                {formatWhatsAppSender(message.sender, message.sender_name, message.is_from_me, selectedChat?.title)}
                              </button>
                            ) : (
                              formatWhatsAppSender(message.sender, message.sender_name, message.is_from_me, selectedChat?.title)
                            )}
                          </div>
                        )}
                        {message.body && <div className="message-body">{message.body}</div>}
                        {message.attachments && message.attachments.length > 0 && (
                          <div className="message-attachments">
                            {message.attachments.map((attachment: WhatsAppAttachment, attIndex: number) => (
                              <div
                                key={attachment.relative_path ?? attachment.file_id ?? String(attIndex)}
                                className="attachment-inline"
                              >
                                <Attachment
                                  attachment={attachment}
                                  extracted={isChatExtracted}
                                  loadBlob={waLoadBlob}
                                  onPreview={setPreviewImage}
                                  onDownload={handleDownloadAttachment}
                                />
                              </div>
                            ))}
                          </div>
                        )}
                        <div className="message-time">
                          {message.sent_at && new Date(message.sent_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="no-results">Select a chat to view messages</div>
            )}
          </div>
        </div>
      </div>

      {previewImage && (
        <div className="image-preview-modal" onClick={() => setPreviewImage(null)}>
          <div className="image-preview-content" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
            <button className="image-preview-close" onClick={() => setPreviewImage(null)}>
              ✕
            </button>
            <img src={previewImage || ''} alt="Preview" />
          </div>
        </div>
      )}
    </>
  );
}
