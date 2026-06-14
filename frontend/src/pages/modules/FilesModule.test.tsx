import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { FilesModule } from './FilesModule';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({
  api: { listDomains: vi.fn(), listFiles: vi.fn(), downloadFile: vi.fn() },
}));

describe('FilesModule', () => {
  beforeEach(() => vi.clearAllMocks());

  it('selects the first domain and lists its files', async () => {
    vi.mocked(api.listDomains).mockResolvedValue({ domains: ['HomeDomain', 'MediaDomain'] });
    vi.mocked(api.listFiles).mockResolvedValue({
      items: [{ file_id: 'f1', domain: 'HomeDomain', relative_path: 'Library/x.db', size: 2048, mtime: null }],
      limit: 200,
      offset: 0,
    });

    render(<FilesModule apiToken="t" backupId="b" />);

    expect(await screen.findByText('Library/x.db')).toBeInTheDocument();
    expect(api.listFiles).toHaveBeenCalledWith('b', 't', expect.objectContaining({ domain: 'HomeDomain' }));
  });
});
