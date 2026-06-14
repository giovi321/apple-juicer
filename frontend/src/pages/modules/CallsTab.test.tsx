import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CallsTab } from './CallsTab';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({ api: { listCalls: vi.fn() } }));

describe('CallsTab', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders call rows from the API', async () => {
    vi.mocked(api.listCalls).mockResolvedValue({
      items: [
        {
          call_identifier: 'c1',
          address: '+15550001111',
          display_name: 'Ada',
          occurred_at: '2020-01-01T00:00:00Z',
          duration_seconds: 65,
          is_outgoing: true,
          answered: true,
          service: null,
        },
      ],
    });

    render(<CallsTab apiToken="t" backupId="b" />);

    expect(await screen.findByText('Ada')).toBeInTheDocument();
    expect(screen.getByText('1 calls')).toBeInTheDocument();
    expect(api.listCalls).toHaveBeenCalledWith('b', 't');
  });

  it('shows an empty state when there are no calls', async () => {
    vi.mocked(api.listCalls).mockResolvedValue({ items: [] });
    render(<CallsTab apiToken="t" backupId="b" />);
    expect(await screen.findByText(/No call history/)).toBeInTheDocument();
  });
});
