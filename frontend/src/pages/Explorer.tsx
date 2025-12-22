import { useCallback, useEffect, useState } from 'react';
import { api, type BackupSummary, type ManifestEntry } from '../lib/api';
import '../styles/Explorer.css';

interface ExplorerProps {
  apiToken: string;
  backup: BackupSummary;
}

type ModuleView = 'files' | 'whatsapp' | 'messages' | 'photos' | 'notes' | 'calendar' | 'contacts';

const MODULES: { id: ModuleView; label: string; description: string }[] = [
  { id: 'files', label: 'Manifest', description: 'Browse manifest entries' },
  { id: 'whatsapp', label: 'WhatsApp', description: 'Explore chats and messages' },
  { id: 'messages', label: 'Messages', description: 'iMessage/SMS conversations' },
  { id: 'photos', label: 'Photos', description: 'Photos timeline' },
  { id: 'notes', label: 'Notes', description: 'Notes database' },
  { id: 'calendar', label: 'Calendar', description: 'Calendar events' },
  { id: 'contacts', label: 'Contacts', description: 'Address book entries' },
];

export function Explorer({ apiToken, backup }: ExplorerProps) {
  const [activeModule, setActiveModule] = useState<ModuleView>('files');
  const [domains, setDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [files, setFiles] = useState<ManifestEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [chatSearchTerm, setChatSearchTerm] = useState('');
  const [messageSearchTerm, setMessageSearchTerm] = useState('');
  const [whatsappChats, setWhatsappChats] = useState<any[]>([]);
  const [selectedChatGuid, setSelectedChatGuid] = useState<string | null>(null);
  const [whatsappMessages, setWhatsappMessages] = useState<any[]>([]);
  const [displayedMessages, setDisplayedMessages] = useState<any[]>([]);
  const [messageOffset, setMessageOffset] = useState(0);
  const MESSAGE_BATCH_SIZE = 100;

  const fetchDomains = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listDomains(backup.id, apiToken);
      setDomains(response.domains);
      if (response.domains.length > 0 && !selectedDomain) {
        setSelectedDomain(response.domains[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load domains');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken, selectedDomain]);

  const fetchFiles = useCallback(async () => {
    if (!selectedDomain) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listFiles(backup.id, apiToken, {
        domain: selectedDomain,
        path_like: searchTerm ? `%${searchTerm}%` : null,
        limit: 200,
      });
      setFiles(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken, selectedDomain, searchTerm]);

  const fetchWhatsAppChats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listWhatsAppChats(backup.id, apiToken);
      const sortedChats = response.items.sort((a, b) => {
        const dateA = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const dateB = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return dateB - dateA;
      });
      setWhatsappChats(sortedChats);
      if (sortedChats.length > 0 && !selectedChatGuid) {
        setSelectedChatGuid(sortedChats[0].chat_guid);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WhatsApp chats');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken, selectedChatGuid]);

  const fetchWhatsAppMessages = useCallback(async () => {
    if (!selectedChatGuid) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listWhatsAppMessages(backup.id, selectedChatGuid, apiToken);
      const sortedMessages = response.messages.sort((a, b) => {
        const dateA = a.sent_at ? new Date(a.sent_at).getTime() : 0;
        const dateB = b.sent_at ? new Date(b.sent_at).getTime() : 0;
        return dateB - dateA;
      });
      setWhatsappMessages(sortedMessages);
      setDisplayedMessages(sortedMessages.slice(0, MESSAGE_BATCH_SIZE));
      setMessageOffset(MESSAGE_BATCH_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WhatsApp messages');
    } finally {
      setLoading(false);
    }
  }, [backup.id, selectedChatGuid, apiToken, MESSAGE_BATCH_SIZE]);

  useEffect(() => {
    if (activeModule === 'files') {
      void fetchDomains();
    }
  }, [activeModule, fetchDomains]);

  useEffect(() => {
    if (activeModule === 'files') {
      void fetchFiles();
    }
  }, [selectedDomain, searchTerm, activeModule, fetchFiles]);

  useEffect(() => {
    if (activeModule === 'whatsapp') {
      void fetchWhatsAppChats();
    }
  }, [activeModule, fetchWhatsAppChats]);

  useEffect(() => {
    if (activeModule === 'whatsapp' && selectedChatGuid) {
      void fetchWhatsAppMessages();
    }
  }, [selectedChatGuid, activeModule, fetchWhatsAppMessages]);

  const loadMoreMessages = useCallback(() => {
    if (messageOffset < whatsappMessages.length) {
      const nextBatch = whatsappMessages.slice(0, messageOffset + MESSAGE_BATCH_SIZE);
      setDisplayedMessages(nextBatch);
      setMessageOffset(messageOffset + MESSAGE_BATCH_SIZE);
    }
  }, [whatsappMessages, messageOffset, MESSAGE_BATCH_SIZE]);

  const handleMessagesScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const element = e.currentTarget;
    if (element.scrollHeight - element.scrollTop <= element.clientHeight + 100) {
      loadMoreMessages();
    }
  }, [loadMoreMessages]);

  const filteredChats = whatsappChats.filter(chat => {
    if (!chatSearchTerm) return true;
    const title = chat.title?.toLowerCase() || '';
    const guid = chat.chat_guid?.toLowerCase() || '';
    const search = chatSearchTerm.toLowerCase();
    return title.includes(search) || guid.includes(search);
  });

  const filteredMessages = displayedMessages.filter(msg => {
    if (!messageSearchTerm) return true;
    const body = msg.body?.toLowerCase() || '';
    const sender = msg.sender?.toLowerCase() || '';
    const search = messageSearchTerm.toLowerCase();
    return body.includes(search) || sender.includes(search);
  });

  const handleDownloadFile = async (fileId: string) => {
    try {
      const response = await api.downloadFile(backup.id, fileId, apiToken);
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
    <div className="explorer">
      <div className="explorer-header">
        <div className="backup-info-card">
          <div className="backup-title-line">
            <h2>{backup.display_name}</h2>
            {backup.device_name && <span className="device-name">{backup.device_name}</span>}
            {backup.product_version && <span className="product-version">{backup.product_version}</span>}
          </div>
          <div className="backup-metadata">
            <div className="metadata-item">
              <span className="metadata-label">Backup ID:</span>
              <span className="metadata-value">{backup.id}</span>
            </div>
            {backup.size_bytes && (
              <div className="metadata-item">
                <span className="metadata-label">Size:</span>
                <span className="metadata-value">{(backup.size_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB</span>
              </div>
            )}
            {backup.last_modified_at && (
              <div className="metadata-item">
                <span className="metadata-label">Created:</span>
                <span className="metadata-value">{new Date(backup.last_modified_at).toLocaleString()}</span>
              </div>
            )}
            {backup.decrypted_at && (
              <div className="metadata-item">
                <span className="metadata-label">Decrypted:</span>
                <span className="metadata-value">{new Date(backup.decrypted_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="explorer-content">
        <div className="module-selector">
          <div className="module-tabs">
            {MODULES.map((module) => (
              <button
                key={module.id}
                className={`module-tab ${activeModule === module.id ? 'active' : ''}`}
                onClick={() => setActiveModule(module.id)}
              >
                <span className="module-label">{module.label}</span>
                <span className="module-description">{module.description}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="module-content">
          {activeModule === 'files' && (
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
                            <button
                              onClick={() => handleDownloadFile(file.file_id)}
                              className="download-btn"
                            >
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
          )}

          {activeModule === 'whatsapp' && (
            <div className="whatsapp-module">
              <div className="whatsapp-container">
                <div className="whatsapp-chats-list">
                  <div className="whatsapp-header">
                    <h3>Chats ({whatsappChats.length})</h3>
                    <input
                      type="text"
                      placeholder="Search chats..."
                      value={chatSearchTerm}
                      onChange={(e) => setChatSearchTerm(e.target.value)}
                      className="search-input"
                    />
                  </div>
                  {loading && !whatsappChats.length ? (
                    <div className="loading">Loading chats...</div>
                  ) : whatsappChats.length === 0 ? (
                    <div className="no-results">No WhatsApp chats found</div>
                  ) : (
                    <div className="chats-list scrollable">
                      {filteredChats.map((chat) => (
                        <button
                          key={chat.chat_guid}
                          className={`chat-item ${selectedChatGuid === chat.chat_guid ? 'active' : ''}`}
                          onClick={() => setSelectedChatGuid(chat.chat_guid)}
                        >
                          <div className="chat-title">{chat.title || chat.chat_guid}</div>
                          {chat.last_message_at && (
                            <div className="chat-date">
                              {new Date(chat.last_message_at).toLocaleDateString()}
                            </div>
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
                        <h3>Messages ({whatsappMessages.length})</h3>
                        <input
                          type="text"
                          placeholder="Search messages..."
                          value={messageSearchTerm}
                          onChange={(e) => setMessageSearchTerm(e.target.value)}
                          className="search-input"
                        />
                      </div>
                      {loading && !whatsappMessages.length ? (
                        <div className="loading">Loading messages...</div>
                      ) : whatsappMessages.length === 0 ? (
                        <div className="no-results">No messages in this chat</div>
                      ) : (
                        <div className="messages-list scrollable" onScroll={handleMessagesScroll}>
                          {filteredMessages.map((msg) => (
                            <div key={msg.message_id} className={`message ${msg.is_from_me ? 'from-me' : 'from-other'}`}>
                              <div className="message-sender">{msg.sender || 'Me'}</div>
                              <div className="message-body">{msg.body}</div>
                              {msg.sent_at && (
                                <div className="message-time">
                                  {new Date(msg.sent_at).toLocaleString()}
                                </div>
                              )}
                            </div>
                          ))}
                          {messageOffset < whatsappMessages.length && (
                            <div className="load-more-indicator">Loading more messages...</div>
                          )}
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="no-results">Select a chat to view messages</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeModule !== 'files' && activeModule !== 'whatsapp' && (
            <div className="coming-soon">
              <h3>{MODULES.find((m) => m.id === activeModule)?.label} Module</h3>
              <p>Coming soon...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
