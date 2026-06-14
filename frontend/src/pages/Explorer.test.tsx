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
