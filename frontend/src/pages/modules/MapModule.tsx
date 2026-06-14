import { useEffect, useMemo, useState } from 'react';
import { MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { api, type MapPoint } from '../../lib/api';
import '../../styles/ArtifactTabs.css';

// Leaflet's default marker icons resolve to broken paths under a bundler; point
// them at the imported asset URLs instead.
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map((p) => [p.latitude, p.longitude] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
  }, [points, map]);
  return null;
}

export function MapModule({ apiToken, backupId }: { apiToken: string; backupId: string }) {
  const [items, setItems] = useState<MapPoint[]>([]);
  const [total, setTotal] = useState(0);
  const [capped, setCapped] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    api
      .getMap(backupId, apiToken)
      .then((res) => {
        if (!mounted) return;
        setItems(res.items.filter((p) => p.latitude != null && p.longitude != null));
        setTotal(res.total);
        setCapped(res.capped);
        setLoading(false);
      })
      .catch((e) => {
        if (!mounted) return;
        setError(e instanceof Error ? e.message : 'Failed to load map');
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [backupId, apiToken]);

  const center = useMemo<[number, number]>(
    () => (items.length ? [items[0].latitude, items[0].longitude] : [20, 0]),
    [items],
  );

  if (loading) return <div className="loading">Loading map…</div>;
  if (error) return <div className="error-message">{error}</div>;
  if (!items.length) {
    return (
      <div className="no-results">
        No mappable points found. Significant-location caches are often excluded from iOS backups, and none of the
        indexed photos carry GPS geotags.
      </div>
    );
  }

  return (
    <div className="artifact-tab">
      <div className="artifact-count">
        {items.length} mappable point{items.length === 1 ? '' : 's'}
        {capped ? ` (showing the first ${items.length} of ${total})` : ''}
      </div>
      <div style={{ height: '70vh', width: '100%' }}>
        <MapContainer center={center} zoom={3} scrollWheelZoom style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {items.map((p, i) => (
            <Marker key={`${p.kind}-${i}`} position={[p.latitude, p.longitude]}>
              <Popup>
                <strong>{p.kind === 'photo' ? 'Photo' : 'Location'}</strong>
                {p.label ? <div>{p.label}</div> : null}
                {p.timestamp ? <div>{new Date(p.timestamp).toLocaleString()}</div> : null}
              </Popup>
            </Marker>
          ))}
          <FitBounds points={items} />
        </MapContainer>
      </div>
    </div>
  );
}
