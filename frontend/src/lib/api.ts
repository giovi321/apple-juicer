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

// Re-export types for use in components
export type {
  BackupStatus,
  CalendarEvent,
  ContactRecord,
  MessageAttachment,
  MessageConversation,
  MessageItem,
  NoteRecord,
  PhotoAsset,
  WhatsAppAttachment,
  WhatsAppChat,
  WhatsAppMessage,
} from './types.ts';

// Use relative API base URL for nginx reverse proxy
// The nginx server will proxy /api requests to the backend service
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

function resolveApiBaseUrl(): string {
  if (API_BASE_URL.startsWith('http://') || API_BASE_URL.startsWith('https://')) {
    return API_BASE_URL;
  }
  if (typeof window !== 'undefined' && window.location?.origin) {
    return new URL(API_BASE_URL, window.location.origin).toString();
  }
  return API_BASE_URL;
}

function apiUrl(path: string, query?: Record<string, string | number | undefined | null>): string {
  const base = new URL(resolveApiBaseUrl());
  if (!base.pathname.endsWith('/')) {
    base.pathname += '/';
  }
  const url = new URL(path.replace(/^\//, ''), base);
  if (query) {
    Object.entries(query).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') return;
      url.searchParams.set(key, String(value));
    });
  }
  return url.toString();
}

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
  indexing_progress?: number | null;
  indexing_total?: number | null;
  indexing_artifact?: string | null;
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
    // Absolute URL - preserve any base pathname (e.g. http://host/api)
    const base = new URL(API_BASE_URL);
    if (!base.pathname.endsWith('/')) {
      base.pathname += '/';
    }
    const url = new URL(path.replace(/^\//, ''), base);
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
  downloadFile: async (backupId: string, fileId: string, token: string, sessionToken?: string) => {
    const urlString = apiUrl(`/backups/${backupId}/file/${fileId}`);
    const response = await fetch(urlString, {
      method: 'GET',
      headers: {
        'X-API-Token': token,
        ...(sessionToken ? { 'X-Backup-Session': sessionToken } : {}),
      },
    });
    const contentType = response.headers.get('content-type') || '';
    if (response.ok && contentType.includes('text/html')) {
      const errorText = await response.text();
      throw new Error(
        `Download returned HTML instead of a file (content-type: ${contentType}). URL=${urlString}. BodyStart=${errorText.slice(0, 200)}`,
      );
    }
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Download failed (${response.status})`);
    }
    return response;
  },
  downloadWhatsAppAttachment: async (backupId: string, relativePath: string, token: string, sessionToken?: string) => {
    const urlString = apiUrl(`/backups/${backupId}/artifacts/whatsapp/attachment`, {
      relative_path: relativePath,
    });
    const response = await fetch(urlString, {
      method: 'GET',
      headers: {
        'X-API-Token': token,
        ...(sessionToken ? { 'X-Backup-Session': sessionToken } : {}),
      },
    });
    const contentType = response.headers.get('content-type') || '';
    if (response.ok && contentType.includes('text/html')) {
      const errorText = await response.text();
      throw new Error(
        `Attachment download returned HTML instead of media (content-type: ${contentType}). URL=${urlString}. BodyStart=${errorText.slice(0, 200)}`,
      );
    }
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Download failed (${response.status})`);
    }
    return response;
  },
  getWhatsAppAttachmentUrl: (backupId: string, relativePath: string, token: string) => {
    const urlString = apiUrl(`/backups/${backupId}/artifacts/whatsapp/attachment`, {
      relative_path: relativePath,
    });
    return urlString + `&token=${encodeURIComponent(token)}`;
  },
  extractWhatsAppFiles: (backupId: string, chatGuid: string, token: string, sessionToken: string) => {
    console.log('API: extractWhatsAppFiles called with chatGuid:', chatGuid);
    const url = `/backups/${backupId}/extract/whatsapp/${encodeURIComponent(chatGuid)}`;
    console.log('API: Full URL path:', url);
    return request<{ extracted_files: number; extracted_bytes: number }>(
      url,
      'POST',
      { token, sessionToken }
    );
  },
  downloadMessageAttachment: async (backupId: string, relativePath: string, token: string, sessionToken?: string) => {
    const urlString = apiUrl(`/backups/${backupId}/artifacts/messages/attachment`, {
      relative_path: relativePath,
    });
    const response = await fetch(urlString, {
      method: 'GET',
      headers: {
        'X-API-Token': token,
        ...(sessionToken ? { 'X-Backup-Session': sessionToken } : {}),
      },
    });
    const contentType = response.headers.get('content-type') || '';
    if (response.ok && contentType.includes('text/html')) {
      const errorText = await response.text();
      throw new Error(
        `Attachment download returned HTML instead of media (content-type: ${contentType}). URL=${urlString}. BodyStart=${errorText.slice(0, 200)}`,
      );
    }
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Download failed (${response.status})`);
    }
    return response;
  },
  extractMessageFiles: (backupId: string, conversationGuid: string, token: string, sessionToken: string) => {
    const url = `/backups/${backupId}/extract/messages/${encodeURIComponent(conversationGuid)}`;
    return request<{ extracted_files: number; extracted_bytes: number }>(
      url,
      'POST',
      { token, sessionToken }
    );
  },
};
