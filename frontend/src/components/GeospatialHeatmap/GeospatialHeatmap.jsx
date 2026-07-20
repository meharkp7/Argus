import { useEffect, useMemo, useState } from 'react';
import { MapContainer, Polygon, Popup, TileLayer, useMap } from 'react-leaflet';
import { api } from '../../api/client';

const RISK_COLORS = {
  critical: { bg: '#DC2626', border: '#991B1B', opacity: 0.7, weight: 3 },
  high: { bg: '#F97316', border: '#9A3412', opacity: 0.65, weight: 2.5 },
  medium: { bg: '#EAB308', border: '#854D0E', opacity: 0.6, weight: 2 },
  low: { bg: '#22C55E', border: '#166534', opacity: 0.55, weight: 2 },
  normal: { bg: '#10B981', border: '#064E3B', opacity: 0.5, weight: 1.5 },
};

function FitBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds([
        [bounds.min_lat, bounds.min_lon],
        [bounds.max_lat, bounds.max_lon],
      ], { padding: [50, 50] });
    }
  }, [bounds, map]);
  return null;
}

export default function GeospatialHeatmap({ onZoneSelect, selectedZone }) {
  const [heatmap, setHeatmap] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const fetchHeatmap = async () => {
      try {
        setRefreshing(true);
        const data = await api.getHeatmap();
        setHeatmap(data);
        console.log('Heatmap loaded with zones:', data?.zones?.length || 0);
      } catch (err) {
        console.error('Heatmap fetch failed:', err);
      } finally {
        setRefreshing(false);
      }
    };
    fetchHeatmap();
    const interval = setInterval(fetchHeatmap, 2500);
    return () => clearInterval(interval);
  }, []);

  const rankedZones = useMemo(() => 
    heatmap ? [...heatmap.zones].sort((a, b) => b.risk_score - a.risk_score) : [],
    [heatmap?.zones]
  );

  if (!heatmap) {
    return (
      <div className="card card--glass map-panel">
        <div className="skeleton-block">Loading geospatial risk surface…</div>
      </div>
    );
  }

  const center = [
    (heatmap.plant_bounds.min_lat + heatmap.plant_bounds.max_lat) / 2,
    (heatmap.plant_bounds.min_lon + heatmap.plant_bounds.max_lon) / 2,
  ];

  return (
    <div className="card card--glass map-panel">
      <div className="card-header">
        <div>
          <span className="card-title">Geospatial Risk Heatmap</span>
          <div className="map-subtitle">
            <span className={`status-pill ${refreshing ? 'status-pill--updating' : 'status-pill--live'}`}>
              {refreshing ? 'Refreshing' : 'Live'}
            </span>
            <span>{heatmap.plant_name ?? 'Industrial Risk Surface'}</span>
            <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#64748b' }}>
              {heatmap.zones.length} zones monitored
            </span>
          </div>
        </div>
        <div className="legend-row">
          {Object.entries(RISK_COLORS).map(([level, config]) => (
            <span key={level} className="legend-chip">
              <span className="legend-chip__swatch" style={{ background: config.bg }} />
              {level}
            </span>
          ))}
        </div>
      </div>
      <div className="map-panel__layout">
        <div className="map-panel__canvas">
          <MapContainer center={center} zoom={16} style={{ height: '100%', width: '100%' }} zoomControl={true}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <FitBounds bounds={heatmap.plant_bounds} />
            {heatmap.zones.map((zone) => {
              const coords = zone.geometry?.coordinates?.[0]?.map(c => [c[1], c[0]]) || [];
              if (coords.length === 0) return null;
              
              const color = RISK_COLORS[zone.risk_level] || RISK_COLORS.normal;
              const isSelected = selectedZone === zone.zone_id;
              
              return (
                <Polygon
                  key={zone.zone_id}
                  positions={coords}
                  pathOptions={{
                    color: color.border,
                    fillColor: color.bg,
                    fillOpacity: isSelected ? color.opacity + 0.25 : color.opacity,
                    weight: isSelected ? color.weight + 1.5 : color.weight,
                    opacity: 1,
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                  eventHandlers={{
                    click: () => onZoneSelect?.(zone),
                    mouseover: (e) => {
                      e.target.setStyle({ 
                        weight: color.weight + 1.5, 
                        fillOpacity: color.opacity + 0.15,
                      });
                    },
                    mouseout: (e) => {
                      if (!isSelected) {
                        e.target.setStyle({ 
                          weight: color.weight, 
                          fillOpacity: color.opacity 
                        });
                      }
                    },
                  }}
                >
                  <Popup>
                    <div style={{ minWidth: 260, fontFamily: 'system-ui, -apple-system, sans-serif' }}>
                      <div style={{ marginBottom: 12 }}>
                        <strong style={{ fontSize: '1rem', display: 'block', marginBottom: 6, color: '#0f172a' }}>
                          {zone.zone_name}
                        </strong>
                        <div style={{ fontSize: '0.9rem', color: color.bg, fontWeight: 700 }}>
                          {zone.risk_level.toUpperCase()} RISK
                        </div>
                        <div style={{ fontSize: '1.3rem', fontWeight: 700, color: color.bg, marginTop: 4 }}>
                          {(zone.risk_score * 100).toFixed(0)}%
                        </div>
                      </div>
                      <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '8px 0' }} />
                      <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <strong>Active Permits:</strong>
                          <span style={{ fontWeight: 600 }}>{zone.active_permits}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <strong>Sensor Anomalies:</strong>
                          <span style={{ fontWeight: 600 }}>{zone.sensor_anomalies}</span>
                        </div>
                        {zone.maintenance_status && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <strong>Maintenance:</strong>
                            <span>{zone.maintenance_status}</span>
                          </div>
                        )}
                        {zone.active_shift && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <strong>Active Shift:</strong>
                            <span>{zone.active_shift}</span>
                          </div>
                        )}
                        {zone.hazard_class && (
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                            <strong>Hazard Class:</strong>
                            <span>{zone.hazard_class}</span>
                          </div>
                        )}
                        {zone.area_sqm && (
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <strong>Area:</strong>
                            <span>{(zone.area_sqm / 1000).toFixed(1)}k m²</span>
                          </div>
                        )}
                      </div>
                      {zone.explanation && (
                        <div style={{ 
                          fontSize: '0.75rem', 
                          marginTop: 10, 
                          padding: '10px', 
                          background: '#f0f9ff', 
                          borderLeft: `3px solid ${color.bg}`,
                          borderRadius: 4, 
                          color: '#334155',
                          lineHeight: 1.6 
                        }}>
                          <strong style={{ display: 'block', marginBottom: 4 }}>Causal Analysis:</strong>
                          {zone.explanation}
                        </div>
                      )}
                    </div>
                  </Popup>
                </Polygon>
              );
            })}
          </MapContainer>
        </div>
        <aside className="map-panel__zones">
          <span className="card-title">Zone Ranking by Risk</span>
          {rankedZones.length === 0 ? (
            <div style={{ padding: '1rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>
              No zones detected
            </div>
          ) : (
            rankedZones.map((zone) => (
              <button
                key={zone.zone_id}
                type="button"
                className={`zone-rank ${selectedZone === zone.zone_id ? 'zone-rank--active' : ''}`}
                onClick={() => onZoneSelect?.(zone)}
              >
                <div>
                  <strong>{zone.zone_name}</strong>
                  <span>{zone.active_permits} permits · {zone.sensor_anomalies} anomalies</span>
                </div>
                <span className={`zone-rank__score zone-rank__score--${zone.risk_level}`}>
                  {(zone.risk_score * 100).toFixed(0)}%
                </span>
              </button>
            ))
          )}
        </aside>
      </div>
    </div>
  );
}
