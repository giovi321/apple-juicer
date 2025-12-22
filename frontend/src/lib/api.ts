import type {
  BackupStatus,
  CalendarEvent,
  ContactRecord,
  MessageConversation,
  MessageItem,
  NoteRecord,
  PhotoAsset,
  WhatsAppChat,
  WhatsAppMessage,
} from './types.ts';

// Use relative API base URL for nginx reverse proxy
// The nginx server will proxy /api requests to the backend service
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export type DecryptionStatus = 'pending' | 'decrypting' | 'decrypted' | 'failed';

export interface BackupSummary {
  id: string;
  display_name: string;
  device_name?: string | null;
  product_version?: string | null;
  is_encrypted: boolean;
  status: BackupStatus;
  decryption_status: DecryptionStatus;
  last_indexed_at?: string | null;
  decrypted_at?: string | null;
  size_bytes?: number | null;
  last_modified_at?: string | null;
}

export interface ManifestEntry {
  file_id: string;
  domain: string;
  relative_path: string;
  size?: number | null;
  mtime?: number | null;
}

export interface UnlockResponse {
  session_token: string;
  ttl_seconds: number;
}

export interface DecryptStatusResponse {
  backup_id: string;
  decryption_status: DecryptionStatus;
  decrypted_at?: string | null;
  error?: string | null;
}

type HTTPMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

interface RequestOptions extends RequestInit {
  token: string;
  sessionToken?: string;
  query?: Record<string, string | number | undefined | null>;
}

async function request<T>(path: string, method: HTTPMethod, options: RequestOptions): Promise<T> {
  const { token, sessionToken, query, headers, body, ...rest } = options;
  
  // Construct the full URL
  let urlString: string;
  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    // Absolute URL - use URL constructor
    const url = new URL(path, API_BASE_URL);
    if (query) {
      Object.entries(query).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        url.searchParams.set(key, String(value));
      });
    }
    urlString = url.toString();
  } else {
    // Relative path - construct manually
    urlString = API_BASE_URL + path;
    if (query) {
      const queryParams = new URLSearchParams();
      Object.entries(query).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') return;
        queryParams.set(key, String(value));
      });
      const queryString = queryParams.toString();
      if (queryString) {
        urlString += '?' + queryString;
      }
    }
  }
  
  const finalHeaders = new Headers(headers);
  finalHeaders.set('Content-Type', 'application/json');
  finalHeaders.set('X-API-Token', token);
  if (sessionToken) {
    finalHeaders.set('X-Backup-Session', sessionToken);
  }
  const response = await fetch(urlString, {
    method,
    headers: finalHeaders,
    body,
    ...rest,
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed (${response.status})`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export interface DiscoverResponse {
  backups: BackupSummary[];
  base_directory: string;
}

export const api = {
  listBackups: (token: string) => request<DiscoverResponse>('/backups', 'GET', { token }),
  refreshBackups: (token: string) => request<DiscoverResponse>('/backups/refresh', 'POST', { token }),
  decryptBackup: (backupId: string, password: string, token: string) =>
    request<DecryptStatusResponse>(`/backups/${backupId}/decrypt`, 'POST', {
      token,
      body: JSON.stringify({ password }),
    }),
  getDecryptStatus: (backupId: string, token: string) =>
    request<DecryptStatusResponse>(`/backups/${backupId}/decrypt-status`, 'GET', { token }),
  deleteDecryptedData: (backupId: string, token: string) =>
    request<void>(`/backups/${backupId}/decrypted`, 'DELETE', { token }),
  unlockBackup: (backupId: string, password: string, token: string) =>
    request<UnlockResponse>(`/backups/${backupId}/unlock`, 'POST', {
      token,
      body: JSON.stringify({ password }),
    }),
  lockBackup: (backupId: string, token: string, sessionToken: string) =>
    request(`/backups/${backupId}/lock`, 'POST', { token, sessionToken }),
  listFiles: (
    backupId: string,
    token: string,
    params: {
      domain?: string | null;
      path_like?: string | null;
      limit?: number;
      offset?: number;
    },
  ) =>
    request<{ items: ManifestEntry[]; limit: number; offset: number }>(
      `/backups/${backupId}/files`,
      'GET',
      { token, query: params },
    ),
  listDomains: (backupId: string, token: string) =>
    request<{ domains: string[] }>(`/backups/${backupId}/domains`, 'GET', {
      token,
    }),
  listPhotos: (backupId: string, token: string) =>
    request<{ items: PhotoAsset[] }>(`/backups/${backupId}/artifacts/photos`, 'GET', {
      token,
    }),
  listWhatsAppChats: (backupId: string, token: string) =>
    request<{ items: WhatsAppChat[] }>(`/backups/${backupId}/artifacts/whatsapp/chats`, 'GET', {
      token,
    }),
  listWhatsAppMessages: (
    backupId: string,
    chatGuid: string,
    token: string,
  ) =>
    request<{ chat: WhatsAppChat; messages: WhatsAppMessage[] }>(
      `/backups/${backupId}/artifacts/whatsapp/chats/${encodeURIComponent(chatGuid)}`,
      'GET',
      { token },
    ),
  listMessageConversations: (backupId: string, token: string) =>
    request<{ items: MessageConversation[] }>(
      `/backups/${backupId}/artifacts/messages/conversations`,
      'GET',
      { token },
    ),
  listMessages: (backupId: string, conversationGuid: string, token: string) =>
    request<{ conversation: MessageConversation; messages: MessageItem[] }>(
      `/backups/${backupId}/artifacts/messages/conversations/${encodeURIComponent(conversationGuid)}`,
      'GET',
      { token },
    ),
  listNotes: (backupId: string, token: string) =>
    request<{ items: NoteRecord[] }>(`/backups/${backupId}/artifacts/notes`, 'GET', { token }),
  listCalendarEvents: (backupId: string, token: string) =>
    request<{ items: CalendarEvent[] }>(`/backups/${backupId}/artifacts/calendar/events`, 'GET', {
      token,
    }),
  listContacts: (backupId: string, token: string) =>
    request<{ items: ContactRecord[] }>(`/backups/${backupId}/artifacts/contacts`, 'GET', {
      token,
    }),
  downloadFile: async (backupId: string, fileId: string, token: string) => {
    const url = new URL(`/backups/${backupId}/file/${fileId}`, API_BASE_URL);
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'X-API-Token': token,
      },
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Download failed (${response.status})`);
    }
    return response;
  },
};
