/**
 * Characterization tests for the WhatsApp and Messages conversation flows that
 * are still inline in Explorer. They pin the current behaviour so the modules
 * can later be extracted into their own components without regressing:
 *   - selecting the conversations tab loads and lists conversations
 *   - the first conversation auto-selects and its messages render
 *   - when there is no unlock session, the "unlock to view attachments" prompt
 *     is shown
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Explorer } from './Explorer';
import { api } from '../lib/api';
import type { BackupSummary } from '../lib/api';

vi.mock('../lib/api', () => ({
  api: {
    // FilesModule (the default tab) + status polling
    listDomains: vi.fn(),
    listFiles: vi.fn(),
    listBackups: vi.fn(),
    // WhatsApp
    listWhatsAppChats: vi.fn(),
    listWhatsAppMessages: vi.fn(),
    // Messages
    listMessageConversations: vi.fn(),
    listMessages: vi.fn(),
    // People
    listPeople: vi.fn(),
    getPerson: vi.fn(),
  },
}));

const BACKUP: BackupSummary = {
  id: 'b1',
  display_name: 'Test Backup',
  device_name: null,
  product_version: null,
  is_encrypted: true,
  status: 'indexed',
  decryption_status: 'decrypted',
  indexing_artifact: null,
};

function baseMocks() {
  vi.mocked(api.listDomains).mockResolvedValue({ domains: [] });
  vi.mocked(api.listFiles).mockResolvedValue({ items: [], limit: 200, offset: 0 });
  vi.mocked(api.listBackups).mockResolvedValue({ backups: [BACKUP], base_directory: '/' });
  vi.mocked(api.listPeople).mockResolvedValue({ items: [] });
}

describe('Explorer · WhatsApp flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseMocks();
  });

  it('lists chats, auto-selects the first, and renders its messages', async () => {
    vi.mocked(api.listWhatsAppChats).mockResolvedValue({
      items: [{ chat_guid: 'g1', title: 'Ada', participant_count: 2, last_message_at: null, metadata: null }],
    });
    vi.mocked(api.listWhatsAppMessages).mockResolvedValue({
      chat: { chat_guid: 'g1', title: 'Ada', participant_count: 2, last_message_at: null, metadata: null },
      messages: [
        {
          chat_guid: 'g1',
          message_id: 'm1',
          sender: '15550001111',
          sender_name: 'Ada',
          sent_at: '2020-01-01T00:00:00Z',
          message_type: '0',
          body: 'Hi there',
          is_from_me: false,
          has_attachments: false,
          attachments: [],
          metadata: null,
        },
      ],
    });

    render(<Explorer apiToken="t" backup={BACKUP} />);
    await userEvent.click(screen.getByRole('button', { name: /WhatsApp/ }));

    expect(await screen.findByText('Hi there')).toBeInTheDocument();
    expect(api.listWhatsAppChats).toHaveBeenCalledWith('b1', 't');
    expect(api.listWhatsAppMessages).toHaveBeenCalledWith('b1', 'g1', 't');
  });

  it('prompts to unlock attachments when there is no session', async () => {
    vi.mocked(api.listWhatsAppChats).mockResolvedValue({
      items: [{ chat_guid: 'g1', title: 'Ada', participant_count: 2, last_message_at: null, metadata: null }],
    });
    vi.mocked(api.listWhatsAppMessages).mockResolvedValue({
      chat: { chat_guid: 'g1', title: 'Ada', participant_count: 2, last_message_at: null, metadata: null },
      messages: [],
    });

    render(<Explorer apiToken="t" backup={BACKUP} />);
    await userEvent.click(screen.getByRole('button', { name: /WhatsApp/ }));

    expect(await screen.findByText(/Unlock Attachments/)).toBeInTheDocument();
  });
});

describe('Explorer · Messages flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseMocks();
  });

  it('lists conversations, auto-selects the first, and renders its messages', async () => {
    vi.mocked(api.listMessageConversations).mockResolvedValue({
      items: [
        {
          conversation_guid: 'c1',
          service: 'iMessage',
          display_name: 'Grace',
          last_message_at: null,
          participant_handles: ['+15550002222'],
        },
      ],
    });
    vi.mocked(api.listMessages).mockResolvedValue({
      conversation: {
        conversation_guid: 'c1',
        service: 'iMessage',
        display_name: 'Grace',
        last_message_at: null,
        participant_handles: ['+15550002222'],
      },
      messages: [
        {
          message_guid: 'im1',
          conversation_guid: 'c1',
          sender: '+15550002222',
          is_from_me: false,
          sent_at: '2020-01-01T00:00:00Z',
          text: 'Hello from Grace',
          has_attachments: false,
          attachments: [],
          metadata: null,
        },
      ],
    });

    render(<Explorer apiToken="t" backup={BACKUP} />);
    await userEvent.click(screen.getByRole('button', { name: /Messages/ }));

    expect(await screen.findByText('Hello from Grace')).toBeInTheDocument();
    expect(api.listMessageConversations).toHaveBeenCalledWith('b1', 't');
    expect(api.listMessages).toHaveBeenCalledWith('b1', 'c1', 't');
  });
});

describe('Explorer · People deep-link', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    baseMocks();
  });

  it('jumps from a conversation sender to that person in the People view', async () => {
    const conv = {
      conversation_guid: 'c1',
      service: 'iMessage',
      display_name: 'Grace',
      last_message_at: null,
      participant_handles: ['+15550002222'],
    };
    vi.mocked(api.listMessageConversations).mockResolvedValue({ items: [conv] });
    vi.mocked(api.listMessages).mockResolvedValue({
      conversation: conv,
      messages: [
        {
          message_guid: 'im1',
          conversation_guid: 'c1',
          sender: '+15550002222',
          person_key: 'phone:5550002222',
          is_from_me: false,
          sent_at: '2020-01-01T00:00:00Z',
          text: 'Hello from Grace',
          has_attachments: false,
          attachments: [],
          metadata: null,
        },
      ],
    });
    const grace = {
      key: 'phone:5550002222',
      kind: 'phone',
      display_name: 'Grace',
      is_contact: false,
      identifiers: ['+15550002222'],
      whatsapp_count: 0,
      message_count: 2,
      call_count: 0,
      voicemail_count: 0,
      total_events: 2,
      last_activity_at: null,
    };
    vi.mocked(api.listPeople).mockResolvedValue({ items: [grace] });
    vi.mocked(api.getPerson).mockResolvedValue({
      person: grace,
      contact: null,
      events: [],
      whatsapp_chat_guid: null,
      conversation_guid: 'c1',
    });

    render(<Explorer apiToken="t" backup={BACKUP} />);
    await userEvent.click(screen.getByRole('button', { name: /Messages/ }));

    // the incoming sender name is clickable
    const senderLink = await screen.findByRole('button', { name: /\+15550002222/ });
    await userEvent.click(senderLink);

    // the People view opens, scoped to that person
    expect(await screen.findByPlaceholderText('Search people…')).toBeInTheDocument();
    expect(api.getPerson).toHaveBeenCalledWith('b1', 'phone:5550002222', 't');
  });

  it('jumps from a WhatsApp sender (1:1 chat) to that person', async () => {
    const chat = { chat_guid: 'g1', title: 'Ada', participant_count: 2, last_message_at: null, metadata: null };
    vi.mocked(api.listWhatsAppChats).mockResolvedValue({ items: [chat] });
    vi.mocked(api.listWhatsAppMessages).mockResolvedValue({
      chat,
      messages: [
        {
          chat_guid: 'g1',
          message_id: 'm1',
          sender: '15550001111',
          sender_name: 'Ada',
          person_key: 'phone:5550001111',
          sent_at: '2020-01-01T00:00:00Z',
          message_type: '0',
          body: 'Hi there',
          is_from_me: false,
          has_attachments: false,
          attachments: [],
          metadata: null,
        },
      ],
    });
    const ada = {
      key: 'phone:5550001111',
      kind: 'phone',
      display_name: 'Ada Lovelace',
      is_contact: true,
      identifiers: ['15550001111@s.whatsapp.net'],
      whatsapp_count: 2,
      message_count: 0,
      call_count: 0,
      voicemail_count: 0,
      total_events: 2,
      last_activity_at: null,
    };
    vi.mocked(api.listPeople).mockResolvedValue({ items: [ada] });
    vi.mocked(api.getPerson).mockResolvedValue({
      person: ada,
      contact: null,
      events: [],
      whatsapp_chat_guid: 'g1',
      conversation_guid: null,
    });

    render(<Explorer apiToken="t" backup={BACKUP} />);
    await userEvent.click(screen.getByRole('button', { name: /WhatsApp/ }));

    // the formatted sender name is clickable (only in 1:1 chats)
    const senderLink = await screen.findByRole('button', { name: /Ada \(\+15550001111\)/ });
    await userEvent.click(senderLink);

    expect(await screen.findByPlaceholderText('Search people…')).toBeInTheDocument();
    expect(api.getPerson).toHaveBeenCalledWith('b1', 'phone:5550001111', 't');
  });
});
