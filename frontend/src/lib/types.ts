export type BackupStatus = 'discovered' | 'locked' | 'unlocked' | 'indexing' | 'indexed';

export interface BackupSession {
  backupId: string;
  token: string;
  expiresAt: number;
}

type StatusLabels = { [K in BackupStatus]: string };
type StatusToneMap = { [K in BackupStatus]: { bg: string; text: string } };

export const STATUS_LABELS: StatusLabels = {
  discovered: 'Discovered',
  locked: 'Locked',
  unlocked: 'Unlocked',
  indexing: 'Indexing',
  indexed: 'Indexed',
} as const;

export const STATUS_TONE: StatusToneMap = {
  discovered: { bg: 'rgba(255, 255, 255, 0.08)', text: '#d9dde3' },
  locked: { bg: 'rgba(255, 82, 82, 0.15)', text: '#ff6b6b' },
  unlocked: { bg: 'rgba(76, 217, 123, 0.18)', text: '#74f0a6' },
  indexing: { bg: 'rgba(255, 184, 116, 0.22)', text: '#ffb970' },
  indexed: { bg: 'rgba(106, 217, 180, 0.22)', text: '#7be2c3' },
} as const;

export interface PhotoAsset {
  asset_id: string | null;
  original_filename: string | null;
  relative_path: string | null;
  file_id: string | null;
  taken_at?: string | null;
  timezone_offset_minutes?: number | null;
  width?: number | null;
  height?: number | null;
  media_type?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface WhatsAppChat {
  chat_guid: string;
  title: string | null;
  participant_count: number | null;
  last_message_at: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface WhatsAppAttachment {
  file_id?: string | null;
  relative_path?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface WhatsAppMessage {
  id?: string;
  chat_guid: string;
  message_id: string;
  sender: string | null;
  sender_name: string | null;
  sent_at: string | null;
  message_type: string | null;
  body: string | null;
  is_from_me: boolean;
  has_attachments: boolean;
  attachments: WhatsAppAttachment[];
  metadata?: Record<string, unknown> | null;
}

export interface NoteRecord {
  note_identifier: string;
  title: string | null;
  body: string | null;
  folder: string | null;
  created_at: string | null;
  last_modified_at: string | null;
}

export interface CalendarEvent {
  event_identifier: string;
  calendar_identifier: string;
  calendar_name?: string;
  title: string | null;
  location: string | null;
  notes: string | null;
  starts_at: string | null;
  ends_at: string | null;
  is_all_day: boolean;
}

export interface ContactRecord {
  contact_identifier: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  emails: string[];
  phones: string[];
  avatar_file_id: string | null;
}

export interface MessageConversation {
  conversation_guid: string;
  service: string | null;
  display_name: string | null;
  last_message_at: string | null;
  participant_handles?: string[];
}

export interface MessageItem {
  message_guid: string;
  conversation_guid: string;
  sender: string | null;
  is_from_me: boolean;
  sent_at: string | null;
  text: string | null;
}

export type ArtifactView =
  | 'files'
  | 'photos'
  | 'whatsapp'
  | 'messages'
  | 'notes'
  | 'calendar'
  | 'contacts'
  | 'search';
