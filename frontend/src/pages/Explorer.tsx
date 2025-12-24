import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  api,
  type BackupSummary,
  type ManifestEntry,
  type MessageAttachment,
  type MessageConversation,
  type MessageItem,
  type WhatsAppAttachment,
  type WhatsAppChat,
  type WhatsAppMessage,
} from '../lib/api';
import '../styles/Explorer.css';

interface ExplorerProps {
  apiToken: string;
  backup: BackupSummary;
  sessionToken?: string;
  onSessionToken?: (token: string) => void;
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

export function Explorer({ apiToken, backup, sessionToken, onSessionToken }: ExplorerProps) {
  const [activeModule, setActiveModule] = useState<ModuleView>('files');
  const [domains, setDomains] = useState<string[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [files, setFiles] = useState<ManifestEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [chatSearchTerm, setChatSearchTerm] = useState('');
  const [messageSearchTerm, setMessageSearchTerm] = useState('');
  const [whatsappChats, setWhatsappChats] = useState<WhatsAppChat[]>([]);
  const [selectedChatGuid, setSelectedChatGuid] = useState<string | null>(null);
  const [whatsappMessages, setWhatsappMessages] = useState<WhatsAppMessage[]>([]);
  const [displayedMessages, setDisplayedMessages] = useState<WhatsAppMessage[]>([]);
  const [messageOffset, setMessageOffset] = useState(0);
  const MESSAGE_BATCH_SIZE = 100;
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [backupData, setBackupData] = useState<BackupSummary>(backup);
  const messagesListRef = useRef<HTMLDivElement | null>(null);
  const [unlockPassword, setUnlockPassword] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [extractedChats, setExtractedChats] = useState<Set<string>>(new Set());

  // Messages (iMessage/SMS) state
  const [messageConversations, setMessageConversations] = useState<MessageConversation[]>([]);
  const [selectedConversationGuid, setSelectedConversationGuid] = useState<string | null>(null);
  const [imessageMessages, setImessageMessages] = useState<MessageItem[]>([]);
  const [displayedImessages, setDisplayedImessages] = useState<MessageItem[]>([]);
  const [imessageOffset, setImessageOffset] = useState(0);
  const [conversationSearchTerm, setConversationSearchTerm] = useState('');
  const [imessageSearchTerm, setImessageSearchTerm] = useState('');
  const [extractedConversations, setExtractedConversations] = useState<Set<string>>(new Set());
  const imessagesListRef = useRef<HTMLDivElement | null>(null);

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
    console.log('DEBUG: fetchWhatsAppChats called');
    setLoading(true);
    setError(null);
    try {
      const response = await api.listWhatsAppChats(backup.id, apiToken);
      console.log('DEBUG: WhatsApp chats response:', response);
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
      console.error('DEBUG: Error fetching WhatsApp chats:', err);
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
      const sortedMessages = [...response.messages].sort((a, b) => {
        const dateA = a.sent_at ? new Date(a.sent_at).getTime() : 0;
        const dateB = b.sent_at ? new Date(b.sent_at).getTime() : 0;
        return dateA - dateB;
      });
      setWhatsappMessages(sortedMessages);
      const initialOffset = Math.max(0, sortedMessages.length - MESSAGE_BATCH_SIZE);
      setDisplayedMessages(sortedMessages.slice(initialOffset));
      setMessageOffset(initialOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load WhatsApp messages');
    } finally {
      setLoading(false);
    }
  }, [backup.id, selectedChatGuid, apiToken, MESSAGE_BATCH_SIZE]);

  const fetchMessageConversations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMessageConversations(backup.id, apiToken);
      const sortedConversations = response.items.sort((a, b) => {
        const dateA = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const dateB = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return dateB - dateA;
      });
      setMessageConversations(sortedConversations);
      if (sortedConversations.length > 0 && !selectedConversationGuid) {
        setSelectedConversationGuid(sortedConversations[0].conversation_guid);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  }, [backup.id, apiToken, selectedConversationGuid]);

  const fetchImessageMessages = useCallback(async () => {
    if (!selectedConversationGuid) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.listMessages(backup.id, selectedConversationGuid, apiToken);
      const sortedMessages = [...response.messages].sort((a, b) => {
        const dateA = a.sent_at ? new Date(a.sent_at).getTime() : 0;
        const dateB = b.sent_at ? new Date(b.sent_at).getTime() : 0;
        return dateA - dateB;
      });
      setImessageMessages(sortedMessages);
      const initialOffset = Math.max(0, sortedMessages.length - MESSAGE_BATCH_SIZE);
      setDisplayedImessages(sortedMessages.slice(initialOffset));
      setImessageOffset(initialOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }, [backup.id, selectedConversationGuid, apiToken, MESSAGE_BATCH_SIZE]);

  const filteredMessages = useMemo(() => {
    const term = messageSearchTerm.trim().toLowerCase();
    if (!term) return whatsappMessages;
    return whatsappMessages.filter((m) => {
      const body = (m.body ?? '').toLowerCase();
      const sender = (m.sender ?? '').toLowerCase();
      return body.includes(term) || sender.includes(term);
    });
  }, [whatsappMessages, messageSearchTerm]);

  const filteredImessages = useMemo(() => {
    const term = imessageSearchTerm.trim().toLowerCase();
    if (!term) return imessageMessages;
    return imessageMessages.filter((m) => {
      const text = (m.text ?? '').toLowerCase();
      const sender = (m.sender ?? '').toLowerCase();
      return text.includes(term) || sender.includes(term);
    });
  }, [imessageMessages, imessageSearchTerm]);

  useEffect(() => {
    const initialOffset = Math.max(0, filteredMessages.length - MESSAGE_BATCH_SIZE);
    setDisplayedMessages(filteredMessages.slice(initialOffset));
    setMessageOffset(initialOffset);
  }, [filteredMessages, MESSAGE_BATCH_SIZE]);

  useEffect(() => {
    const initialOffset = Math.max(0, filteredImessages.length - MESSAGE_BATCH_SIZE);
    setDisplayedImessages(filteredImessages.slice(initialOffset));
    setImessageOffset(initialOffset);
  }, [filteredImessages, MESSAGE_BATCH_SIZE]);

  useEffect(() => {
    if (!messagesListRef.current) return;
    if (loading) return;
    messagesListRef.current.scrollTop = messagesListRef.current.scrollHeight;
  }, [selectedChatGuid, loading]);

  useEffect(() => {
    if (!imessagesListRef.current) return;
    if (loading) return;
    imessagesListRef.current.scrollTop = imessagesListRef.current.scrollHeight;
  }, [selectedConversationGuid, loading]);

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
      // Refresh backup data to get latest indexing status
      setStatusLoaded(false);
      api.listBackups(apiToken).then(response => {
        const updatedBackup = response.backups.find(b => b.id === backup.id);
        if (updatedBackup) {
          setBackupData(updatedBackup);
          // Only fetch chats if indexing is complete (no indexing_artifact means indexing is done)
          const isIndexing = updatedBackup.indexing_artifact !== null && updatedBackup.indexing_artifact !== undefined;
          if (!isIndexing) {
            void fetchWhatsAppChats();
          } else {
            // Clear any existing chats during indexing
            setWhatsappChats([]);
            setSelectedChatGuid(null);
          }
        }
        setStatusLoaded(true);
      }).catch(err => {
        console.error('Failed to refresh backup status:', err);
        setStatusLoaded(true);
      });
    }
  }, [activeModule, fetchWhatsAppChats, backup.id, apiToken]);

  useEffect(() => {
    if (activeModule === 'whatsapp' && selectedChatGuid) {
      void fetchWhatsAppMessages();
    }
  }, [selectedChatGuid, activeModule, fetchWhatsAppMessages]);

  useEffect(() => {
    if (activeModule === 'messages') {
      setStatusLoaded(false);
      api.listBackups(apiToken).then(response => {
        const updatedBackup = response.backups.find(b => b.id === backup.id);
        if (updatedBackup) {
          setBackupData(updatedBackup);
          const isIndexing = updatedBackup.indexing_artifact !== null && updatedBackup.indexing_artifact !== undefined;
          if (!isIndexing) {
            void fetchMessageConversations();
          } else {
            setMessageConversations([]);
            setSelectedConversationGuid(null);
          }
        }
        setStatusLoaded(true);
      }).catch(err => {
        console.error('Failed to refresh backup status:', err);
        setStatusLoaded(true);
      });
    }
  }, [activeModule, fetchMessageConversations, backup.id, apiToken]);

  useEffect(() => {
    if (activeModule === 'messages' && selectedConversationGuid) {
      void fetchImessageMessages();
    }
  }, [selectedConversationGuid, activeModule, fetchImessageMessages]);

  // Poll for backup status updates when indexing is in progress
  const isIndexing = backupData.indexing_artifact !== null && backupData.indexing_artifact !== undefined;
  const isIndexingWhatsApp = backupData.indexing_artifact === 'whatsapp';
  const isIndexingMessages = backupData.indexing_artifact === 'messages';
  useEffect(() => {
    console.log('DEBUG: Polling effect triggered, indexing_artifact:', backupData.indexing_artifact);
    if (isIndexing) {
      const interval = setInterval(async () => {
        try {
          console.log('DEBUG: Polling for backup status...');
          const response = await api.listBackups(apiToken);
          const updatedBackup = response.backups.find(b => b.id === backup.id);
          if (updatedBackup) {
            console.log('DEBUG: Updated backup data:', updatedBackup);
            setBackupData(updatedBackup);
            // If indexing completed, refresh the appropriate module
            const isIndexing = updatedBackup.indexing_artifact !== null && updatedBackup.indexing_artifact !== undefined;
            if (!isIndexing) {
              if (activeModule === 'whatsapp') {
                void fetchWhatsAppChats();
              } else if (activeModule === 'messages') {
                void fetchMessageConversations();
              }
            }
          }
        } catch (err) {
          console.error('Failed to refresh backup status:', err);
        }
      }, 2000); // Poll every 2 seconds

      return () => clearInterval(interval);
    }
  }, [isIndexing, backup.id, apiToken, activeModule, fetchWhatsAppChats, fetchMessageConversations]);

  const loadMoreMessages = useCallback(() => {
    if (messageOffset <= 0) return;
    const nextOffset = Math.max(0, messageOffset - MESSAGE_BATCH_SIZE);
    setDisplayedMessages(filteredMessages.slice(nextOffset));
    setMessageOffset(nextOffset);
  }, [filteredMessages, messageOffset, MESSAGE_BATCH_SIZE]);

  const handleMessagesScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const element = e.currentTarget;
      if (element.scrollTop <= 100) {
        loadMoreMessages();
      }
    },
    [loadMoreMessages],
  );

  const loadMoreImessages = useCallback(() => {
    if (imessageOffset <= 0) return;
    const nextOffset = Math.max(0, imessageOffset - MESSAGE_BATCH_SIZE);
    setDisplayedImessages(filteredImessages.slice(nextOffset));
    setImessageOffset(nextOffset);
  }, [filteredImessages, imessageOffset, MESSAGE_BATCH_SIZE]);

  const handleImessagesScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const element = e.currentTarget;
      if (element.scrollTop <= 100) {
        loadMoreImessages();
      }
    },
    [loadMoreImessages],
  );

  const filteredChats = whatsappChats.filter(chat => {
    if (!chatSearchTerm) return true;
    const title = chat.title?.toLowerCase() || '';
    const guid = chat.chat_guid?.toLowerCase() || '';
    const search = chatSearchTerm.toLowerCase();
    return title.includes(search) || guid.includes(search);
  });

  const filteredConversations = messageConversations.filter(conv => {
    if (!conversationSearchTerm) return true;
    const name = conv.display_name?.toLowerCase() || '';
    const guid = conv.conversation_guid?.toLowerCase() || '';
    const handles = (conv.participant_handles || []).join(' ').toLowerCase();
    const search = conversationSearchTerm.toLowerCase();
    return name.includes(search) || guid.includes(search) || handles.includes(search);
  });

  const selectedConversation = useMemo(() => {
    return messageConversations.find(c => c.conversation_guid === selectedConversationGuid) || null;
  }, [messageConversations, selectedConversationGuid]);

  const isConversationExtracted = selectedConversationGuid ? extractedConversations.has(selectedConversationGuid) : false;

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

  const handleDownloadAttachment = async (relativePath: string, filename: string) => {
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
  };

  const handlePreviewImage = async (relativePath: string, mimeType: string | null) => {
    if (!mimeType?.startsWith('image/')) return;
    try {
      const response = await api.downloadWhatsAppAttachment(backup.id, relativePath, apiToken, sessionToken);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      setPreviewImage(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    }
  };

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

  const handleExtractWhatsAppFiles = async () => {
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
    console.log('DEBUG: Extracting files for chat:', selectedChatGuid);
    try {
      const result = await api.extractWhatsAppFiles(backup.id, selectedChatGuid, apiToken, sessionToken);
      console.log('DEBUG: Extraction result:', result);
      // Mark this chat as extracted
      setExtractedChats(prev => new Set(prev).add(selectedChatGuid));
      const sizeMB = (result.extracted_bytes / 1024 / 1024).toFixed(2);
      alert(`Extracted ${result.extracted_files} files (${sizeMB} MB) for this chat. Attachments will now load.`);
      // Refresh messages to trigger re-render of attachments
      void fetchWhatsAppMessages();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  const handleDownloadMessageAttachment = async (relativePath: string, filename: string) => {
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
  };

  const handleExtractMessageFiles = async () => {
    if (!sessionToken) {
      setError('Please unlock the backup first to extract files');
      return;
    }
    if (!selectedConversationGuid) {
      setError('Please select a conversation first');
      return;
    }
    setExtracting(true);
    setError(null);
    try {
      const result = await api.extractMessageFiles(backup.id, selectedConversationGuid, apiToken, sessionToken);
      setExtractedConversations(prev => new Set(prev).add(selectedConversationGuid));
      const sizeMB = (result.extracted_bytes / 1024 / 1024).toFixed(2);
      alert(`Extracted ${result.extracted_files} files (${sizeMB} MB) for this conversation. Attachments will now load.`);
      void fetchImessageMessages();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed');
    } finally {
      setExtracting(false);
    }
  };

  // Check if current chat has been extracted
  const isChatExtracted = selectedChatGuid ? extractedChats.has(selectedChatGuid) : false;

  const selectedChat = useMemo(() => {
    return whatsappChats.find(c => c.chat_guid === selectedChatGuid) || null;
  }, [whatsappChats, selectedChatGuid]);

  const formatWhatsAppSender = (sender: string | null, senderName: string | null, isFromMe: boolean, chatTitle?: string | null) => {
    if (isFromMe) return 'You';
    
    // Extract phone number from JID (e.g., "1234567890@s.whatsapp.net" -> "1234567890")
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
    
    // Check if a string looks like a phone number (digits, possibly with + prefix)
    const looksLikePhone = (str: string | null): boolean => {
      if (!str) return false;
      // Phone numbers: optional +, then mostly digits (allow some formatting chars)
      return /^\+?[\d\s\-().]{7,}$/.test(str.trim());
    };
    
    const phone = extractPhone(sender);
    const name = senderName?.trim() || null;
    
    // Prefer showing name with phone, or just one if the other is missing
    if (name && phone && looksLikePhone(phone)) {
      return `${name} (+${phone.replace(/^\+/, '')})`;
    }
    if (name) {
      return name;
    }
    if (phone && looksLikePhone(phone)) {
      return `+${phone.replace(/^\+/, '')}`;
    }
    // For 1:1 chats, use the chat title (partner name) as fallback
    if (chatTitle?.trim()) {
      if (phone && looksLikePhone(phone)) {
        return `${chatTitle.trim()} (+${phone.replace(/^\+/, '')})`;
      }
      return chatTitle.trim();
    }
    // If we have a sender value but it doesn't look like a phone, still show it
    // but only if we have nothing else
    if (phone) {
      return phone;
    }
    return 'Unknown';
  };

  const guessAttachmentFilename = (attachment: WhatsAppAttachment) => {
    const rp = attachment.relative_path ?? '';
    const last = rp.split('/').filter(Boolean).pop();
    return last || attachment.file_id || 'attachment';
  };

  const guessMessageAttachmentFilename = (attachment: MessageAttachment) => {
    const rp = attachment.relative_path ?? '';
    const last = rp.split('/').filter(Boolean).pop();
    return last || attachment.file_id || 'attachment';
  };

  const formatMessageSender = (sender: string | null, isFromMe: boolean, conversationName?: string | null) => {
    if (isFromMe) return 'You';
    if (sender) return sender;
    if (conversationName) return conversationName;
    return 'Unknown';
  };

  const AttachmentImage = ({
    relativePath,
    filename,
    mimeType,
  }: {
    relativePath: string;
    filename: string;
    mimeType: string | null;
  }) => {
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      let isMounted = true;
      const loadImage = async () => {
        console.log('Loading attachment:', relativePath);
        try {
          const response = await api.downloadWhatsAppAttachment(backup.id, relativePath, apiToken, sessionToken);
          console.log('Got response:', response.status);
          const blob = await response.blob();
          console.log('Got blob, size:', blob.size, 'type:', blob.type);
          const url = window.URL.createObjectURL(blob);
          if (isMounted) {
            setImageUrl(url);
            setLoading(false);
            setError(null);
          }
        } catch (err) {
          console.error('Failed to load image:', err);
          if (isMounted) {
            setLoading(false);
            setError(err instanceof Error ? err.message : 'Failed to load');
          }
        }
      };
      loadImage();
      return () => {
        isMounted = false;
        if (imageUrl) window.URL.revokeObjectURL(imageUrl);
      };
    }, [relativePath, backup.id, apiToken, sessionToken]);

    if (loading) {
      return <div className="attachment-loading">Loading image...</div>;
    }

    if (error || !imageUrl) {
      return <div className="attachment-error">Failed to load image: {error}</div>;
    }

    return (
      <div className="attachment-image-wrapper">
        <img 
          src={imageUrl} 
          alt={filename}
          className="attachment-image"
          onClick={() => handlePreviewImage(relativePath, mimeType)}
        />
        <button
          className="attachment-download-overlay"
          onClick={(e) => {
            e.stopPropagation();
            handleDownloadAttachment(relativePath, filename);
          }}
          title="Download"
        >
          ⬇️
        </button>
      </div>
    );
  };

  const AttachmentMedia = ({
    relativePath,
    mimeType,
    kind,
    filename,
  }: {
    relativePath: string;
    mimeType: string | null;
    kind: 'video' | 'audio';
    filename: string;
  }) => {
    const [url, setUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);

    useEffect(() => {
      let isMounted = true;
      let objectUrl: string | null = null;
      const load = async () => {
        try {
          const response = await api.downloadWhatsAppAttachment(backup.id, relativePath, apiToken, sessionToken);
          const blob = await response.blob();
          objectUrl = window.URL.createObjectURL(blob);
          if (isMounted) {
            setUrl(objectUrl);
            setLoading(false);
          } else {
            window.URL.revokeObjectURL(objectUrl);
          }
        } catch (e) {
          if (isMounted) {
            setLoading(false);
            setError(e instanceof Error ? e.message : 'Failed to load media');
          }
        }
      };
      load();
      return () => {
        isMounted = false;
        if (objectUrl) window.URL.revokeObjectURL(objectUrl);
      };
    }, [relativePath, backup.id, apiToken, sessionToken]);

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
          <button className="attachment-download-overlay" onClick={() => handleDownloadAttachment(relativePath, filename)}>
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
        <button className="attachment-download-btn-small" onClick={() => handleDownloadAttachment(relativePath, filename)}>
          ⬇️
        </button>
      </div>
    );
  };

  const MessageAttachmentImage = ({
    relativePath,
    filename,
  }: {
    relativePath: string;
    filename: string;
    mimeType?: string | null;
  }) => {
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
      let isMounted = true;
      const loadImage = async () => {
        try {
          const response = await api.downloadMessageAttachment(backup.id, relativePath, apiToken, sessionToken);
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          if (isMounted) {
            setImageUrl(url);
            setLoading(false);
            setError(null);
          }
        } catch (err) {
          if (isMounted) {
            setLoading(false);
            setError(err instanceof Error ? err.message : 'Failed to load');
          }
        }
      };
      loadImage();
      return () => {
        isMounted = false;
        if (imageUrl) window.URL.revokeObjectURL(imageUrl);
      };
    }, [relativePath, backup.id, apiToken, sessionToken]);

    if (loading) {
      return <div className="attachment-loading">Loading image...</div>;
    }

    if (error || !imageUrl) {
      return <div className="attachment-error">Failed to load image: {error}</div>;
    }

    return (
      <div className="attachment-image-wrapper">
        <img 
          src={imageUrl} 
          alt={filename}
          className="attachment-image"
          onClick={() => {
            const url = imageUrl;
            setPreviewImage(url);
          }}
        />
        <button
          className="attachment-download-overlay"
          onClick={(e) => {
            e.stopPropagation();
            handleDownloadMessageAttachment(relativePath, filename);
          }}
          title="Download"
        >
          ⬇️
        </button>
      </div>
    );
  };

  const MessageAttachmentMedia = ({
    relativePath,
    mimeType,
    kind,
    filename,
  }: {
    relativePath: string;
    mimeType: string | null;
    kind: 'video' | 'audio';
    filename: string;
  }) => {
    const [url, setUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);

    useEffect(() => {
      let isMounted = true;
      let objectUrl: string | null = null;
      const load = async () => {
        try {
          const response = await api.downloadMessageAttachment(backup.id, relativePath, apiToken, sessionToken);
          const blob = await response.blob();
          objectUrl = window.URL.createObjectURL(blob);
          if (isMounted) {
            setUrl(objectUrl);
            setLoading(false);
          } else {
            window.URL.revokeObjectURL(objectUrl);
          }
        } catch (e) {
          if (isMounted) {
            setLoading(false);
            setError(e instanceof Error ? e.message : 'Failed to load media');
          }
        }
      };
      load();
      return () => {
        isMounted = false;
        if (objectUrl) window.URL.revokeObjectURL(objectUrl);
      };
    }, [relativePath, backup.id, apiToken, sessionToken]);

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
          <button className="attachment-download-overlay" onClick={() => handleDownloadMessageAttachment(relativePath, filename)}>
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
        <button className="attachment-download-btn-small" onClick={() => handleDownloadMessageAttachment(relativePath, filename)}>
          ⬇️
        </button>
      </div>
    );
  };

  const renderMessageAttachment = (attachment: MessageAttachment) => {
    if (!attachment.relative_path) {
      return null;
    }
    const filename = guessMessageAttachmentFilename(attachment);

    if (!isConversationExtracted) {
      const icon = attachment.mime_type?.startsWith('image/') ? '🖼️' :
                   attachment.mime_type?.startsWith('video/') ? '🎬' :
                   attachment.mime_type?.startsWith('audio/') ? '🎵' : '📄';
      return (
        <div className="attachment-placeholder">
          <span className="attachment-icon">{icon}</span>
          <span className="attachment-name">{filename}</span>
          <span className="attachment-size">
            {attachment.size_bytes ? `${(attachment.size_bytes / 1024 / 1024).toFixed(1)} MB` : ''}
          </span>
          <span className="attachment-hint">Extract files to view</span>
        </div>
      );
    }

    if (attachment.mime_type?.startsWith('image/')) {
      return (
        <div className="attachment-image-wrapper">
          <MessageAttachmentImage
            relativePath={attachment.relative_path}
            filename={filename}
            mimeType={attachment.mime_type}
          />
        </div>
      );
    }

    if (attachment.mime_type?.startsWith('video/')) {
      return (
        <MessageAttachmentMedia
          relativePath={attachment.relative_path}
          mimeType={attachment.mime_type}
          kind="video"
          filename={filename}
        />
      );
    }

    if (attachment.mime_type?.startsWith('audio/')) {
      return (
        <MessageAttachmentMedia
          relativePath={attachment.relative_path}
          mimeType={attachment.mime_type}
          kind="audio"
          filename={filename}
        />
      );
    }

    return (
      <div className="attachment-file">
        <span className="attachment-icon">📄</span>
        <span className="attachment-name">{filename}</span>
        <span className="attachment-size">
          {attachment.size_bytes ? `${(attachment.size_bytes / 1024 / 1024).toFixed(1)} MB` : ''}
        </span>
        <button
          className="attachment-download-btn-small"
          onClick={() => handleDownloadMessageAttachment(attachment.relative_path ?? '', filename)}
        >
          ⬇️
        </button>
      </div>
    );
  };

  const renderAttachment = (attachment: WhatsAppAttachment) => {
    if (!attachment.relative_path) {
      return null;
    }
    const filename = guessAttachmentFilename(attachment);

    // If chat is not extracted, show placeholder instead of trying to load
    if (!isChatExtracted) {
      const icon = attachment.mime_type?.startsWith('image/') ? '🖼️' :
                   attachment.mime_type?.startsWith('video/') ? '🎬' :
                   attachment.mime_type?.startsWith('audio/') ? '🎵' : '📄';
      return (
        <div className="attachment-placeholder">
          <span className="attachment-icon">{icon}</span>
          <span className="attachment-name">{filename}</span>
          <span className="attachment-size">
            {attachment.size_bytes ? `${(attachment.size_bytes / 1024 / 1024).toFixed(1)} MB` : ''}
          </span>
          <span className="attachment-hint">Extract files to view</span>
        </div>
      );
    }

    if (attachment.mime_type?.startsWith('image/')) {
      return (
        <div className="attachment-image-wrapper">
          <AttachmentImage
            relativePath={attachment.relative_path}
            filename={filename}
            mimeType={attachment.mime_type}
          />
        </div>
      );
    }

    if (attachment.mime_type?.startsWith('video/')) {
      return (
        <AttachmentMedia
          relativePath={attachment.relative_path}
          mimeType={attachment.mime_type}
          kind="video"
          filename={filename}
        />
      );
    }

    if (attachment.mime_type?.startsWith('audio/')) {
      return (
        <AttachmentMedia
          relativePath={attachment.relative_path}
          mimeType={attachment.mime_type}
          kind="audio"
          filename={filename}
        />
      );
    }

    return (
      <div className="attachment-file">
        <span className="attachment-icon">📄</span>
        <span className="attachment-name">{filename}</span>
        <span className="attachment-size">
          {attachment.size_bytes ? `${(attachment.size_bytes / 1024 / 1024).toFixed(1)} MB` : ''}
        </span>
        <button
          className="attachment-download-btn-small"
          onClick={() => handleDownloadAttachment(attachment.relative_path ?? '', filename)}
        >
          ⬇️
        </button>
      </div>
    );
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
        {extracting && (
          <div className="extraction-overlay">
            <div className="extraction-overlay-content">
              <div className="extraction-spinner"></div>
              <div>Extracting attachments...</div>
              <div style={{ fontSize: '0.85rem', opacity: 0.7, marginTop: '0.5rem' }}>
                Please wait, do not navigate away
              </div>
            </div>
          </div>
        )}
        <div className="module-selector">
          <div className="module-tabs">
            {MODULES.map((module) => (
              <button
                key={module.id}
                className={`module-tab ${activeModule === module.id ? 'active' : ''}`}
                onClick={() => setActiveModule(module.id)}
                disabled={extracting}
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
                    disabled={loading || extracting}
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
                    disabled={loading || extracting}
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
                            <button
                              onClick={() => handleDownloadFile(file.file_id)}
                              className="download-btn"
                              disabled={extracting}
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
                  <div className="loading">
                    <div>
                      <div>Indexing WhatsApp...</div>
                      {backupData.indexing_progress !== undefined && backupData.indexing_progress !== null && backupData.indexing_total ? (
                        <>
                          <div className="progress-bar">
                            <div 
                              className="progress-fill" 
                              style={{ width: `${(backupData.indexing_progress / backupData.indexing_total) * 100}%` }}
                            />
                            <div className="progress-text">
                              {Math.round((backupData.indexing_progress / backupData.indexing_total) * 100)}%
                            </div>
                          </div>
                          <div className="progress-subtext">
                            {backupData.indexing_progress}/{backupData.indexing_total}
                          </div>
                        </>
                      ) : null}
                      <div style={{ fontSize: '0.85rem', marginTop: '0.5rem', opacity: 0.7 }}>
                        Please wait while WhatsApp chats are being indexed...
                      </div>
                    </div>
                  </div>
                ) : loading && !whatsappChats.length ? (
                  <div className="loading">Loading chats...</div>
                ) : whatsappChats.length === 0 ? (
                  <div className="no-results">
                    <div>
                      <div>No WhatsApp chats found</div>
                      <div style={{ fontSize: '0.85rem', marginTop: '0.5rem', opacity: 0.7 }}>
                        Indexing completed but no WhatsApp data was found in this backup.
                      </div>
                    </div>
                  </div>
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
                      <h3>
                        {selectedChat?.title || 'Chat'}
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
                        {isChatExtracted ? (
                          <button
                            className="download-btn extracted"
                            disabled
                            title="Files already extracted for this chat"
                          >
                            ✓ Files Extracted
                          </button>
                        ) : (
                          <button
                            className={`download-btn ${extracting ? 'extracting' : ''}`}
                            onClick={handleExtractWhatsAppFiles}
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
                      <div
                        ref={messagesListRef}
                        className="messages-list scrollable"
                        onScroll={handleMessagesScroll}
                      >
                        {displayedMessages.map((message, index) => (
                          <div
                            key={message.message_id || index}
                            className={`message ${message.is_from_me ? 'from-me' : 'from-other'}`}
                          >
                            {!message.is_from_me && (
                              <div className="message-sender">
                                {formatWhatsAppSender(message.sender, message.sender_name, message.is_from_me, selectedChat?.title)}
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
                                    {renderAttachment(attachment)}
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
                  <div className="no-results">
                    Select a chat to view messages
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeModule === 'messages' && (
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
                  <div className="loading">
                    <div>
                      <div>Indexing messages...</div>
                      {backupData.indexing_progress !== undefined && backupData.indexing_progress !== null && backupData.indexing_total ? (
                        <>
                          <div className="progress-bar">
                            <div 
                              className="progress-fill" 
                              style={{ width: `${(backupData.indexing_progress / backupData.indexing_total) * 100}%` }}
                            />
                            <div className="progress-text">
                              {Math.round((backupData.indexing_progress / backupData.indexing_total) * 100)}%
                            </div>
                          </div>
                          <div className="progress-subtext">
                            {backupData.indexing_progress}/{backupData.indexing_total}
                          </div>
                        </>
                      ) : null}
                      <div style={{ fontSize: '0.85rem', marginTop: '0.5rem', opacity: 0.7 }}>
                        Please wait while messages are being indexed...
                      </div>
                    </div>
                  </div>
                ) : loading && !messageConversations.length ? (
                  <div className="loading">Loading conversations...</div>
                ) : messageConversations.length === 0 ? (
                  <div className="no-results">
                    <div>
                      <div>No conversations found</div>
                      <div style={{ fontSize: '0.85rem', marginTop: '0.5rem', opacity: 0.7 }}>
                        Indexing completed but no iMessage/SMS data was found in this backup.
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="chats-list scrollable">
                    {filteredConversations.map((conv) => (
                      <button
                        key={conv.conversation_guid}
                        className={`chat-item ${selectedConversationGuid === conv.conversation_guid ? 'active' : ''}`}
                        onClick={() => setSelectedConversationGuid(conv.conversation_guid)}
                        disabled={extracting}
                      >
                        <div className="chat-title">
                          {conv.display_name || conv.participant_handles?.join(', ') || conv.conversation_guid}
                        </div>
                        <div className="chat-subtitle">
                          {conv.service === 'iMessage' ? '💬' : '📱'} {conv.service || 'SMS'}
                        </div>
                        {conv.last_message_at && (
                          <div className="chat-date">
                            {new Date(conv.last_message_at).toLocaleDateString()}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="whatsapp-messages">
                {selectedConversationGuid ? (
                  <>
                    <div className="whatsapp-header">
                      <h3>
                        {selectedConversation?.display_name || selectedConversation?.participant_handles?.join(', ') || 'Conversation'}
                      </h3>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input
                          type="text"
                          placeholder="Search messages..."
                          value={imessageSearchTerm}
                          onChange={(e) => setImessageSearchTerm(e.target.value)}
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
                            onClick={handleExtractMessageFiles}
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
                      <div
                        ref={imessagesListRef}
                        className="messages-list scrollable"
                        onScroll={handleImessagesScroll}
                      >
                        {displayedImessages.map((message, index) => (
                          <div
                            key={message.message_guid || index}
                            className={`message ${message.is_from_me ? 'from-me' : 'from-other'}`}
                          >
                            {!message.is_from_me && (
                              <div className="message-sender">
                                {formatMessageSender(message.sender, message.is_from_me, selectedConversation?.display_name)}
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
                                    {renderMessageAttachment(attachment)}
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
                  <div className="no-results">
                    Select a conversation to view messages
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeModule === 'photos' && (
          <div className="coming-soon">
            <h3>Photos</h3>
            <p>Photos timeline coming soon...</p>
          </div>
        )}

        {activeModule === 'notes' && (
          <div className="coming-soon">
            <h3>Notes</h3>
            <p>Notes functionality coming soon...</p>
          </div>
        )}

        {activeModule === 'calendar' && (
          <div className="coming-soon">
            <h3>Calendar</h3>
            <p>Calendar events coming soon...</p>
          </div>
        )}

        {activeModule === 'contacts' && (
          <div className="coming-soon">
            <h3>Contacts</h3>
            <p>Address book coming soon...</p>
          </div>
        )}
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
    </div>
  );
}
