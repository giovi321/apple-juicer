import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchTab } from './SearchTab';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({ api: { search: vi.fn() } }));

describe('SearchTab', () => {
  beforeEach(() => vi.clearAllMocks());

  it('runs a search and deep-links a clicked result to its tab', async () => {
    vi.mocked(api.search).mockResolvedValue({
      query: 'ada',
      items: [{ artifact_type: 'contact', artifact_ref: 'contact-1', display_text: 'Ada Lovelace', payload: null }],
    });
    const onNavigate = vi.fn();

    render(<SearchTab apiToken="t" backupId="b" onNavigate={onNavigate} />);

    await userEvent.type(screen.getByPlaceholderText(/Search messages/), 'ada');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));

    const result = await screen.findByText('Ada Lovelace');
    await userEvent.click(result);

    expect(api.search).toHaveBeenCalledWith('b', 'ada', 't');
    expect(onNavigate).toHaveBeenCalledWith({ module: 'contacts' });
  });

  it('passes the chat guid for a WhatsApp result', async () => {
    vi.mocked(api.search).mockResolvedValue({
      query: 'hi',
      items: [
        {
          artifact_type: 'whatsapp_message',
          artifact_ref: 'm1',
          display_text: 'Hi there',
          payload: { chat_guid: 'chat-123' },
        },
      ],
    });
    const onNavigate = vi.fn();

    render(<SearchTab apiToken="t" backupId="b" onNavigate={onNavigate} />);
    await userEvent.type(screen.getByPlaceholderText(/Search messages/), 'hi');
    await userEvent.click(screen.getByRole('button', { name: 'Search' }));
    await userEvent.click(await screen.findByText('Hi there'));

    expect(onNavigate).toHaveBeenCalledWith({ module: 'whatsapp', chatGuid: 'chat-123' });
  });
});
