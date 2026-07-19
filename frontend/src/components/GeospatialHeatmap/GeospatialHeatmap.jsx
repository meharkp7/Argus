import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Polygon, Popup, useMap } from 'react-leaflet';
import { api } from '../../api/client';

const RISK_COLORS = {
  critical: '#DC2626',
  high: '#EA580C',
  medium: '#CA8A04',
  low: '#65A30D',
  normal: '#16A34A',
};

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds([
        [bounds.min_lat, bounds.min_lon],
        [bounds.max_lat, bounds.max_lon],
      ], { padding: [30, 30] });
    }
  }, [bounds, map]);
  return null;
}

export default function GeospatialHeatmap({ onZoneSelect, selectedZone }) {
  const [heatmap, setHeatmap] = useState(null);

  useEffect(() => {
    const fetchHeatmap = async () => {
      try {
        const data = await api.getHeatmap();
        setHeatmap(data);
      } catch (err) {
        console.error('Heatmap fetch failed:', err);
      }
    };
    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!heatmap) {
    return (
      <div className="card" style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-secondary)' }}>Loading plant map...</span>
      </div>
    );
  }

  const center = [
    (heatmap.plant_bounds.min_lat + heatmap.plant_bounds.max_lat) / 2,
    (heatmap.plant_bounds.min_lon + heatmap.plant_bounds.max_lon) / 2,
  ];

  return (
    <div className="card" style={{ height: 480 }}>
      <div className="card-header">
        <span className="card-title">Geospatial Risk Heatmap</span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {Object.entries(RISK_COLORS).map(([level, color]) => (
            <span key={level} style={{ fontSize: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'inline-block' }} />
              {level}
            </span>
          ))}
        </div>
      </div>
      <div style={{ height: 400, borderRadius: '0.5rem', overflow: 'hidden' }}>
        <MapContainer center={center} zoom={16} style={{ height: '100%', width: '100%' }} zoomControl={true}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds bounds={heatmap.plant_bounds} />
          {heatmap.zones.map((zone) => {
            const coords = zone.geometry?.coordinates?.[0]?.map(c => [c[1], c[0]]) || [];
            const color = RISK_COLORS[zone.risk_level] || RISK_COLORS.normal;
            return (
              <Polygon
                key={zone.zone_id}
                positions={coords}
                pathOptions={{
                  color,
                  fillColor: color,
                  fillOpacity: selectedZone === zone.zone_id ? 0.6 : 0.35,
                  weight: selectedZone === zone.zone_id ? 3 : 2,
                }}
                eventHandlers={{
                  click: () => onZoneSelect?.(zone),
                }}
              >
                <Popup>
                  <div style={{ minWidth: 200 }}>
                    <strong>{zone.zone_name}</strong>
                    <p>Risk: <span style={{ color }}>{zone.risk_level.toUpperCase()}</span> ({(zone.risk_score * 100).toFixed(0)}%)</p>
                    <p>Active Permits: {zone.active_permits}</p>
                    <p>Sensor Anomalies: {zone.sensor_anomalies}</p>
                    {zone.explanation && <p style={{ fontSize: '0.85em', marginTop: 4 }}>{zone.explanation}</p>}
                  </div>
                </Popup>
              </Polygon>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
