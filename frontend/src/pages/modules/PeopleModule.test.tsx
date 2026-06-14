import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PeopleModule } from './PeopleModule';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({
  api: {
    listPeople: vi.fn(),
    getPerson: vi.fn(),
  },
}));

const ADA = {
  key: 'phone:5550001111',
  kind: 'phone',
  display_name: 'Ada Lovelace',
  is_contact: true,
  identifiers: ['15550001111@s.whatsapp.net', '+15550001111'],
  whatsapp_count: 1,
  message_count: 0,
  call_count: 1,
  voicemail_count: 1,
  total_events: 3,
  last_activity_at: '2020-01-01T00:00:00Z',
};

describe('PeopleModule', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listPeople).mockResolvedValue({ items: [ADA] });
    vi.mocked(api.getPerson).mockResolvedValue({
      person: ADA,
      contact: {
        contact_identifier: 'c1',
        first_name: 'Ada',
        last_name: 'Lovelace',
        company: 'Analytical Engines',
        emails: ['ada@example.com'],
        phones: ['+15550001111'],
        avatar_file_id: null,
      },
      events: [
        { timestamp: '2020-01-01T00:00:00Z', artifact_type: 'call', title: 'Ada', subtitle: 'Call · outgoing · 65s' },
        { timestamp: '2019-12-31T00:00:00Z', artifact_type: 'whatsapp_message', title: 'Hi there', subtitle: 'WhatsApp' },
      ],
    });
  });

  it('lists people, auto-selects the first, and renders their correlated activity', async () => {
    render(<PeopleModule apiToken="t" backupId="b1" />);

    // the person appears in the master list with their name
    expect(await screen.findByRole('button', { name: /Ada Lovelace/ })).toBeInTheDocument();
    expect(api.listPeople).toHaveBeenCalledWith('b1', 't');

    // auto-selected -> detail loads with the contact card and a cross-artifact event
    expect(await screen.findByText(/Contact card/)).toBeInTheDocument();
    expect(await screen.findByText('Hi there')).toBeInTheDocument();
    expect(api.getPerson).toHaveBeenCalledWith('b1', 'phone:5550001111', 't');
  });

  it('filters the people list by search term', async () => {
    render(<PeopleModule apiToken="t" backupId="b1" />);
    await screen.findByRole('button', { name: /Ada Lovelace/ });

    const input = screen.getByPlaceholderText('Search people…');
    await userEvent.type(input, 'zzz');
    expect(screen.queryByRole('button', { name: /Ada Lovelace/ })).not.toBeInTheDocument();
  });
});
