import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  type BackupSummary,
  type MessageAttachment,
  type MessageConversation,
  type MessageItem,
} from '../../lib/api';
import { Attachment } from './Attachment';

const MESSAGE_BATCH_SIZE = 100;

function formatMessageSender(sender: string | null, isFromMe: boolean, conversationName?: string | null) {
  if (isFromMe) return 'You';
  if (sender) return sender;
  if (conversationName) return conversationName;
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

export function MessagesModule({
  apiToken,
  backup,
  sessionToken,
  onSessionToken,
  initialSelectedGuid,
  onOpenPerson,
}: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<MessageConversation[]>([]);
  const [selectedGuid, setSelectedGuid] = useState<string | null>(initialSelectedGuid ?? null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [displayedMessages, setDisplayedMessages] = useState<MessageItem[]>([]);
  const [messageOffset, setMessageOffset] = useState(0);
  const [conversationSearchTerm, setConversationSearchTerm] = useState('');
  const [messageSearchTerm, setMessageSearchTerm] = useState('');
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [backupData, setBackupData] = useState<BackupSummary>(backup);
  const messagesListRef = useRef<HTMLDivElement | null>(null);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [extractedConversations, setExtractedConversations] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (initialSelectedGuid) setSelectedGuid(initialSelectedGuid);
  }, [initialSelectedGuid]);

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMessageConversations(backup.id, apiToken);
      const sorted = response.items.sort((a, b) => {
        const da = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const db = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return db - da;
      });
      setConversations(sorted);
      setSelectedGuid((current) => current ?? (sorted[0]?.conversation_guid ?? null));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken]);

  const fetchMessages = useCallback(async () => {
    if (!selectedGuid) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMessages(backup.id, selectedGuid, apiToken);
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
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [backup.id, selectedGuid, apiToken]);

  useEffect(() => {
    setStatusLoaded(false);
    api
      .listBackups(apiToken)
      .then((response) => {
        const updated = response.backups.find((b) => b.id === backup.id);
        if (updated) {
          setBackupData(updated);
          const indexing = updated.indexing_artifact !== null && updated.indexing_artifact !== undefined;
          if (!indexing) void fetchConversations();
          else {
            setConversations([]);
            setSelectedGuid(null);
          }
        }
        setStatusLoaded(true);
      })
      .catch(() => setStatusLoaded(true));
  }, [apiToken, backup.id, fetchConversations]);

  useEffect(() => {
    if (selectedGuid) void fetchMessages();
  }, [selectedGuid, fetchMessages]);

  const isIndexing = backupData.indexing_artifact !== null && backupData.indexing_artifact !== undefined;
  const isIndexingMessages = backupData.indexing_artifact === 'messages';

  useEffect(() => {
    if (!isIndexing) return;
    const interval = setInterval(async () => {
      try {
        const response = await api.listBackups(apiToken);
        const updated = response.backups.find((b) => b.id === backup.id);
        if (updated) {
          setBackupData(updated);
          if (updated.indexing_artifact === null || updated.indexing_artifact === undefined) void fetchConversations();
        }
      } catch {
        /* ignore polling errors */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [isIndexing, apiToken, backup.id, fetchConversations]);

  const filteredMessages = useMemo(() => {
    const term = messageSearchTerm.trim().toLowerCase();
    if (!term) return messages;
    return messages.filter(
      (m) => (m.text ?? '').toLowerCase().includes(term) || (m.sender ?? '').toLowerCase().includes(term),
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
  }, [selectedGuid, loading]);

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

  const msgLoadBlob = useCallback(
    (rp: string) => api.downloadMessageAttachment(backup.id, rp, apiToken, sessionToken).then((r) => r.blob()),
    [backup.id, apiToken, sessionToken],
  );

  const handleDownloadAttachment = useCallback(
    async (relativePath: string, filename: string) => {
      try {
        const response = await api.downloadMessageAttachment(backup.id, relativePath, apiToken, sessionToken);
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
    if (!selectedGuid) {
      setError('Please select a conversation first');
      return;
    }
    setExtracting(true);
    setError(null);
    try {
      const result = await api.extractMessageFiles(backup.id, selectedGuid, apiToken, sessionToken);
      setExtractedConversations((prev) => new Set(prev).add(selectedGuid));
      const sizeMB = (result.extracted_bytes / 1024 / 1024).toFixed(2);
      alert(`Extracted ${result.extracted_files} files (${sizeMB} MB) for this conversation. Attachments will now load.`);
      void fetchMessages();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  const filteredConversations = conversations.filter((conv) => {
    if (!conversationSearchTerm) return true;
    const search = conversationSearchTerm.toLowerCase();
    const handles = (conv.participant_handles || []).join(' ').toLowerCase();
    return (
      (conv.display_name?.toLowerCase() || '').includes(search) ||
      (conv.conversation_guid?.toLowerCase() || '').includes(search) ||
      handles.includes(search)
    );
  });

  const isConversationExtracted = selectedGuid ? extractedConversations.has(selectedGuid) : false;
  const selectedConversation = useMemo(
    () => conversations.find((c) => c.conversation_guid === selectedGuid) || null,
    [conversations, selectedGuid],
  );
  // Only 1:1 conversations map to a single person in the People view.
  const conversationIsOneToOne = (selectedConversation?.participant_handles?.length ?? 1) === 1;

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
              <h3>Conversations</h3>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <input
                type="text"
                placeholder="Search conversations..."
                value={conversationSearchTerm}
                onChange={(e) => setConversationSearchTerm(e.target.value)}
                className="search-input"
                disabled={extracting}
              />
            </div>
            {!statusLoaded ? (
              <div className="loading">Loading...</div>
            ) : isIndexingMessages ? (
              <div className="loading">Indexing messages... please wait.</div>
            ) : loading && !conversations.length ? (
              <div className="loading">Loading conversations...</div>
            ) : conversations.length === 0 ? (
              <div className="no-results">No conversations found in this backup.</div>
            ) : (
              <div className="chats-list scrollable">
                {filteredConversations.map((conv) => (
                  <button
                    key={conv.conversation_guid}
                    className={`chat-item ${selectedGuid === conv.conversation_guid ? 'active' : ''}`}
                    onClick={() => setSelectedGuid(conv.conversation_guid)}
                    disabled={extracting}
                  >
                    <div className="chat-title">
                      {conv.display_name || conv.participant_handles?.join(', ') || conv.conversation_guid}
                    </div>
                    <div className="chat-subtitle">
                      {conv.service === 'iMessage' ? '💬' : '📱'} {conv.service || 'SMS'}
                    </div>
                    {conv.last_message_at && (
                      <div className="chat-date">{new Date(conv.last_message_at).toLocaleDateString()}</div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="whatsapp-messages">
            {selectedGuid ? (
              <>
                <div className="whatsapp-header">
                  <h3>
                    {selectedConversation?.display_name ||
                      selectedConversation?.participant_handles?.join(', ') ||
                      'Conversation'}
                  </h3>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="Search messages..."
                      value={messageSearchTerm}
                      onChange={(e) => setMessageSearchTerm(e.target.value)}
                      className="search-input search-box-wide"
                      disabled={extracting}
                    />
                    {isConversationExtracted ? (
                      <button
                        className="download-btn extracted"
                        disabled
                        title="Files already extracted for this conversation"
                      >
                        ✓ Files Extracted
                      </button>
                    ) : (
                      <button
                        className={`download-btn ${extracting ? 'extracting' : ''}`}
                        onClick={handleExtract}
                        disabled={extracting || !sessionToken}
                        title={!sessionToken ? 'Unlock backup first' : 'Extract files for this conversation'}
                      >
                        {extracting ? 'Extracting...' : 'Extract Files'}
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
                        key={message.message_guid || index}
                        className={`message ${message.is_from_me ? 'from-me' : 'from-other'}`}
                      >
                        {!message.is_from_me && (
                          <div className="message-sender">
                            {onOpenPerson && message.person_key && conversationIsOneToOne ? (
                              <button
                                type="button"
                                className="sender-link"
                                onClick={() => onOpenPerson(message.person_key!)}
                                title="View this person"
                              >
                                {formatMessageSender(message.sender, message.is_from_me, selectedConversation?.display_name)}
                              </button>
                            ) : (
                              formatMessageSender(message.sender, message.is_from_me, selectedConversation?.display_name)
                            )}
                          </div>
                        )}
                        {message.text && <div className="message-body">{message.text}</div>}
                        {message.attachments && message.attachments.length > 0 && (
                          <div className="message-attachments">
                            {message.attachments.map((attachment: MessageAttachment, attIndex: number) => (
                              <div
                                key={attachment.relative_path ?? attachment.file_id ?? String(attIndex)}
                                className="attachment-inline"
                              >
                                <Attachment
                                  attachment={attachment}
                                  extracted={isConversationExtracted}
                                  loadBlob={msgLoadBlob}
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
              <div className="no-results">Select a conversation to view messages</div>
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
