import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MapModule } from './MapModule';
import { api } from '../../lib/api';

// Leaflet needs real layout, which jsdom doesn't provide — stub the map layer.
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children?: unknown }) => <div data-testid="map">{children as never}</div>,
  TileLayer: () => <div data-testid="tile" />,
  Marker: ({ children }: { children?: unknown }) => <div data-testid="marker">{children as never}</div>,
  Popup: ({ children }: { children?: unknown }) => <div data-testid="popup">{children as never}</div>,
  useMap: () => ({ fitBounds: vi.fn() }),
}));
vi.mock('leaflet', () => ({
  default: {
    Icon: { Default: { mergeOptions: vi.fn() } },
    latLngBounds: vi.fn(() => ({})),
  },
}));
vi.mock('leaflet/dist/leaflet.css', () => ({}));
vi.mock('leaflet/dist/images/marker-icon-2x.png', () => ({ default: 'marker2x' }));
vi.mock('leaflet/dist/images/marker-icon.png', () => ({ default: 'marker' }));
vi.mock('leaflet/dist/images/marker-shadow.png', () => ({ default: 'shadow' }));
vi.mock('../../lib/api', () => ({ api: { getMap: vi.fn() } }));

const PHOTO = { kind: 'photo', latitude: 47.1, longitude: 8.5, label: 'IMG_0001.JPG', timestamp: null };
const LOCATION = { kind: 'location', latitude: 37.3, longitude: -122.0, label: 'Significant location', timestamp: null };

describe('MapModule', () => {
  beforeEach(() => vi.clearAllMocks());

  it('plots one marker per point and labels them', async () => {
    vi.mocked(api.getMap).mockResolvedValue({ items: [PHOTO, LOCATION], total: 2, capped: false } as never);
    render(<MapModule apiToken="t" backupId="b1" />);

    await screen.findByTestId('map');
    expect(screen.getAllByTestId('marker')).toHaveLength(2);
    expect(screen.getByText('IMG_0001.JPG')).toBeInTheDocument();
    expect(api.getMap).toHaveBeenCalledWith('b1', 't');
  });

  it('filters out points with null coordinates', async () => {
    const noCoords = { kind: 'photo', latitude: null, longitude: null, label: 'no gps', timestamp: null };
    vi.mocked(api.getMap).mockResolvedValue({ items: [PHOTO, noCoords], total: 2, capped: false } as never);
    render(<MapModule apiToken="t" backupId="b1" />);

    await screen.findByTestId('map');
    expect(screen.getAllByTestId('marker')).toHaveLength(1);
  });

  it('shows an empty state when there are no mappable points', async () => {
    vi.mocked(api.getMap).mockResolvedValue({ items: [], total: 0, capped: false } as never);
    render(<MapModule apiToken="t" backupId="b1" />);

    expect(await screen.findByText(/No mappable points found/)).toBeInTheDocument();
    expect(screen.queryByTestId('map')).not.toBeInTheDocument();
  });
});
