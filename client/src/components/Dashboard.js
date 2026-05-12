import { useState, useEffect } from 'react';
import * as Recharts from 'recharts';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import {
  Leaf, Activity, BarChart2, Map as MapIcon, Droplet, Wind, Sun,
  ShieldAlert, Zap, Box, ChevronDown, ChevronUp, Info, PieChart as PieChartIcon
} from 'lucide-react';
import './Dashboard.css';

const {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
  Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell, PieChart, Pie,
  LineChart, Line
} = Recharts;

const RADIAN = Math.PI / 180;


const getMetricIcon = (name) => {
  const n = name.toLowerCase();
  if (n.includes('water') || n.includes('rain') || n.includes('aquatic') || n.includes('aridity') || n.includes('scarcity')) return <Droplet size={16} color="var(--primary)" />;
  if (n.includes('air') || n.includes('wind') || n.includes('pollution') || n.includes('light')) return <Wind size={16} color="var(--dim-extent)" />;
  if (n.includes('sun') || n.includes('temp') || n.includes('climate') || n.includes('lst')) return <Sun size={16} color="var(--color-score-mid)" />;
  if (n.includes('risk') || n.includes('threat') || n.includes('loss') || n.includes('extinction') || n.includes('disturbance')) return <ShieldAlert size={16} color="var(--dim-threat)" />;
  if (n.includes('energy') || n.includes('power') || n.includes('npp') || n.includes('functional')) return <Zap size={16} color="var(--color-score-high)" />;
  if (n.includes('species') || n.includes('biodiversity') || n.includes('bii') || n.includes('habitat') || n.includes('integrity') || n.includes('ndvi')) return <Leaf size={16} color="var(--color-score-high)" />;
  return <Box size={16} color="var(--text-secondary)" />;
};

const getMetricGrade = (metricValue, groupName, metricName, data) => {
  if (metricValue === "Coming soon" || metricValue === null || metricValue === undefined) {
    return { label: "N/A", class: "badge-neutral" };
  }

  // Use the 1-5 integrity score from the backend's pillar_concerns object
  const pillarConcerns = data?.pillar_concerns || {};
  const integrityScore = pillarConcerns[groupName]?.[metricName];

  if (integrityScore === null || integrityScore === undefined) {
    // Fallback logic if integrity score isn't pre-calculated
    const num = parseFloat(metricValue);
    if (isNaN(num)) return { label: "N/A", class: "badge-neutral" };

    // Convert 0-1 normalized to 1-5 scale for grading
    const isNegative = groupName === 'Pillar-4: Extinction Risk' || groupName === 'Pillar-5: Pressure';
    const score1to5 = isNegative ? 1 + (num * 4) : 1 + ((1 - num) * 4);

    if (score1to5 >= 4.5) return { label: "Very High", class: "badge-very-high" };
    if (score1to5 >= 3.5) return { label: "High", class: "badge-high" };
    if (score1to5 >= 2.5) return { label: "Moderate", class: "badge-moderate" };
    if (score1to5 >= 1.5) return { label: "Low", class: "badge-low" };
    return { label: "Very Low", class: "badge-very-low" };
  }

  // Use the 1-5 concern score (1 is VL concern, 5 is VH concern)
  if (integrityScore <= 1.5) return { label: "Very Low", class: "badge-very-low" };
  if (integrityScore <= 2.5) return { label: "Low", class: "badge-low" };
  if (integrityScore <= 3.5) return { label: "Moderate", class: "badge-moderate" };
  if (integrityScore <= 4.5) return { label: "High", class: "badge-high" };
  return { label: "Very High", class: "badge-very-high" };
};

const getPillarName = (groupName) => {
  return groupName;
};

const getMetricConcernLevel = (val, groupName, name) => {
  if (val === "Coming soon") return null;
  const num = parseFloat(val);
  if (isNaN(num)) return null;

  const isNegativeIndicator = groupName === 'Pillar-4: Extinction Risk' || groupName === 'Pillar-5: Pressure';

  // Backend concern_score logic implies:
  // concern_numeric = 1 + (val * 4)
  // Our logic: concern = 5 - val*4
  // 5 means Very High concern

  let mappedScore;
  if (isNegativeIndicator) {
    mappedScore = 1 + (num * 4); // higher val -> higher score
  } else {
    mappedScore = 1 + ((1 - num) * 4); // lower val -> higher score
  }

  if (mappedScore <= 1.5) return 'VL';
  if (mappedScore <= 2.5) return 'L';
  if (mappedScore <= 3.5) return 'M';
  if (mappedScore <= 4.5) return 'H';
  return 'VH';
};

const calculateDistribution = (metrics, pillarConcerns) => {
  const dist = [
    { name: 'Extent', VL: 0, L: 0, M: 0, H: 0, VH: 0 },
    { name: 'Condition', VL: 0, L: 0, M: 0, H: 0, VH: 0 },
    { name: 'Population', VL: 0, L: 0, M: 0, H: 0, VH: 0 },
    { name: 'Extinction', VL: 0, L: 0, M: 0, H: 0, VH: 0 }
  ];

  const pillarMap = {
    "Pillar-1: Ecosystem Extent": 0,
    "Pillar-2: Ecosystem Condition": 1,
    "Pillar-3: Population": 2,
    "Pillar-4: Extinction Risk": 3
  };

  const getLevel = (numeric) => {
    if (numeric === null || numeric === undefined) return null;
    if (numeric <= 1.5) return 'VL';
    if (numeric <= 2.5) return 'L';
    if (numeric <= 3.5) return 'M';
    if (numeric <= 4.5) return 'H';
    return 'VH';
  };

  if (metrics && typeof metrics === 'object') {
    Object.entries(metrics).forEach(([groupName, groupData]) => {
      const idx = pillarMap[groupName];
      if (idx !== undefined && groupData && typeof groupData === 'object') {
        Object.entries(groupData).forEach(([name, val]) => {
          const concernNumeric = pillarConcerns?.[groupName]?.[name];
          const level = concernNumeric !== undefined ? getLevel(concernNumeric) : getMetricConcernLevel(val, groupName, name);
          if (level) dist[idx][level] += 1;
        });
      }
    });
  }
  return dist;
};

const getConcernColor = (val) => {
  if (val > 4.5) return '#D86464'; // Very High
  if (val > 3.5) return '#E18259'; // High
  if (val > 2.5) return '#F6E975'; // Moderate
  if (val > 1.5) return '#78DD8E'; // Low
  return '#73D2D5'; // Very Low
};

const formatConcernLabel = (val) => {
  if (val > 4.5) return 'Very High';
  if (val > 3.5) return 'High';
  if (val > 2.5) return 'Moderate';
  if (val > 1.5) return 'Low';
  return 'Very Low';
};

// Calculate geodesic area in km2 for WGS84 GeoJSON
const getRingArea = (coords) => {
  let area = 0;
  if (coords && coords.length > 2) {
    for (let i = 0; i < coords.length - 1; i++) {
      const p1 = coords[i];
      const p2 = coords[i + 1];
      const dLon = (p2[0] - p1[0]) * Math.PI / 180;
      area += dLon * (2 + Math.sin(p1[1] * Math.PI / 180) + Math.sin(p2[1] * Math.PI / 180));
    }
    area = Math.abs(area * 6378.137 * 6378.137 / 2.0);
  }
  return area;
};

const getFeatureAreaKm2 = (feature) => {
  let area = 0;
  if (!feature.geometry || !feature.geometry.coordinates) return null;

  if (feature.geometry.type === 'Polygon') {
    area = getRingArea(feature.geometry.coordinates[0]);
    for (let i = 1; i < feature.geometry.coordinates.length; i++) {
      area -= getRingArea(feature.geometry.coordinates[i]);
    }
  } else if (feature.geometry.type === 'MultiPolygon') {
    feature.geometry.coordinates.forEach(polygon => {
      let polyArea = getRingArea(polygon[0]);
      for (let i = 1; i < polygon.length; i++) {
        polyArea -= getRingArea(polygon[i]);
      }
      area += polyArea;
    });
  }
  return Math.abs(area);
};

export default function Dashboard({ data, geoJson, onReset }) {
  const [mapType, setMapType] = useState('base');
  const [expandedGroup, setExpandedGroup] = useState(null);
  const [bounds, setBounds] = useState(null);
  const [activePressure, setActivePressure] = useState('GHM');

  useEffect(() => {
    if (geoJson) {
      console.log("🗺️ Dashboard received GeoJSON:", geoJson);
      try {
        const layer = L.geoJSON(geoJson);
        const b = layer.getBounds();
        if (b.isValid()) {
          console.log("✅ Map bounds calculated:", b);
          setBounds(b);
        } else {
          console.warn("⚠️ Map data received but bounds are invalid. Possible empty geometry?");
        }
      } catch (e) {
        console.error("❌ Failed to process map data:", e);
      }
    }
  }, [geoJson]);


  if (!data) return null;

  const tileUrls = {
    base: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    street: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
  };

  const { metrics } = data;
  const sonValue = data["SoN Score"] || 0;

  // Map dimensions for Radar chart
  const radarData = [
    { subject: 'Extent', A: data["Extent"] || 1, fullMark: 5 },
    { subject: 'Condition', A: data["Condition"] || 1, fullMark: 5 },
    { subject: 'Population', A: data["Population"] || 1, fullMark: 5 },
    { subject: 'Extinction', A: data["Extinction"] || 1, fullMark: 5 },
  ];


  const stackedData = calculateDistribution(metrics || {}, data?.pillar_concerns);

  const pillarMetricCounts = [
    { name: 'Extent', count: (metrics && typeof metrics === 'object' && metrics["Pillar-1: Ecosystem Extent"]) ? Object.keys(metrics["Pillar-1: Ecosystem Extent"]).length : 0, fill: '#10B981' },
    { name: 'Condition', count: (metrics && typeof metrics === 'object' && metrics["Pillar-2: Ecosystem Condition"]) ? Object.keys(metrics["Pillar-2: Ecosystem Condition"]).length : 0, fill: '#3B82F6' },
    { name: 'Population', count: (metrics && typeof metrics === 'object' && metrics["Pillar-3: Population"]) ? Object.keys(metrics["Pillar-3: Population"]).length : 0, fill: '#8B5CF6' },
    { name: 'Extinction', count: (metrics && typeof metrics === 'object' && metrics["Pillar-4: Extinction Risk"]) ? Object.keys(metrics["Pillar-4: Extinction Risk"]).length : 0, fill: '#F59E0B' },
  ];

  const pressureData = [
    {
      name: 'GHM',
      val: (metrics?.["Pillar-5: Pressure"]?.["GHM"] || 0),
      fill: '#ef4444',
      icon: <Box size={16} color="#ef4444" />,
      label: 'Global Human Mod.'
    },
    {
      name: 'HDI',
      val: (metrics?.["Pillar-5: Pressure"]?.["HDI"] || 0),
      fill: '#3b82f6',
      icon: <Activity size={16} color="#3b82f6" />,
      label: 'Human Dev. Index'
    },
    {
      name: 'Light',
      val: (metrics?.["Pillar-5: Pressure"]?.["Light Pollution"] || 0),
      fill: '#f59e0b',
      icon: <Zap size={16} color="#f59e0b" />,
      label: 'Light Pollution'
    },
  ];



  const p5 = metrics?.["Pillar-5: Pressure"] || {};
  const pc5 = data?.pillar_concerns?.["Pillar-5: Pressure"] || {};

  // Map for Packed Circles
  const pressureConfig = {
    GHM: { label: 'GHM', max: 1.0, description: 'Global Human Modification' },
    HDI: { label: 'HDI', max: 1.0, description: 'Human Disturbance Index' },
    Light: { label: 'Light', max: 100.0, description: 'Light Pollution' }
  };

  const activePData = pressureData.find(d => d.name === activePressure) || pressureData[0];
  const config = pressureConfig[activePressure];
  
  // Map internal name to concern key
  const concernKeyMap = { 'GHM': 'GHM', 'HDI': 'HDI', 'Light': 'Light Pollution' };
  const activeConcernVal = pc5[concernKeyMap[activePressure]];
  const activeColor = getConcernColor(activeConcernVal);
  const activeLabel = formatConcernLabel(activeConcernVal);

  const percentage = Math.min(100, (activePData.val / config.max) * 100);
  const ringData = [
    { name: 'Value', value: percentage, fill: activeColor },
    { name: 'Remaining', value: 100 - percentage, fill: 'rgba(0,0,0,0.05)' }
  ];
  const temperatureData = [
    { 
      name: 'Day LST', 
      value: typeof p5["Day LST"] === 'number' ? p5["Day LST"] : 0,
      concern: formatConcernLabel(pc5["Day LST"]),
      concernValue: pc5["Day LST"]
    },
    { 
      name: 'Night LST', 
      value: typeof p5["Night LST"] === 'number' ? p5["Night LST"] : 0,
      concern: formatConcernLabel(pc5["Night LST"]),
      concernValue: pc5["Night LST"]
    }
  ];
  if (typeof p5["Urban Heat Island"] === 'number') {
    temperatureData.push({ 
      name: 'UHI', 
      value: p5["Urban Heat Island"],
      concern: formatConcernLabel(pc5["Urban Heat Island"]),
      concernValue: pc5["Urban Heat Island"]
    });
  }

  const onEachFeature = (feature, layer) => {
    if (feature.properties) {
      let tooltipContent = '';

      const tryKeys = (keys, label) => {
        for (let k of keys) {
          if (feature.properties[k] !== undefined && feature.properties[k] !== null) {
            tooltipContent += `<strong>${label}:</strong> ${feature.properties[k]}<br/>`;
            return;
          }
        }
      };

      tryKeys(['Name', 'NAME', 'name'], 'Name');

      const realArea = getFeatureAreaKm2(feature);
      if (realArea !== null && realArea > 0) {
        let displayArea = Math.round(realArea).toLocaleString();
        if (Math.round(realArea) === 0 && realArea > 0) displayArea = "< 1";
        tooltipContent += `<strong>Area:</strong> ${displayArea} km²<br/>`;
      } else {
        tryKeys(['Area', 'AREA', 'area', 'Shape_Area'], 'Area');
      }

      if (!tooltipContent && Object.keys(feature.properties).length > 0) {
        const keys = Object.keys(feature.properties).slice(0, 3);
        keys.forEach(k => {
          tooltipContent += `<strong>${k}:</strong> ${feature.properties[k]}<br/>`;
        });
      }

      if (tooltipContent) {
        layer.bindTooltip(`<div class="map-tooltip" style="font-family: inherit; color: var(--text-primary);">${tooltipContent}</div>`, { permanent: false, direction: 'auto', sticky: true });
      }
    }
  };

  const gaugeData = [
    { value: 1, fill: '#73D2D5', label: 'Very Low', range: '0', textColor: '#73D2D5' },
    { value: 1, fill: '#78DD8E', label: 'Low', range: '4', textColor: '#78DD8E' },
    { value: 1, fill: '#F6E975', label: 'Moderate', range: '5', textColor: '#F6E975' },
    { value: 1, fill: '#E18259', label: 'High', range: '7', textColor: '#E18259' },
    { value: 1, fill: '#D86464', label: 'Very High', range: '10', textColor: 'black' }
  ];

  const getGaugeStatus = (val) => {
    if (val <= 4) return gaugeData[0];
    if (val <= 5) return gaugeData[1];
    if (val <= 7) return gaugeData[2];
    if (val <= 8) return gaugeData[3];
    return gaugeData[4];
  };

  const getVisualPercentage = (val) => {
    if (val <= 4) return (val / 4) * 20;
    if (val <= 5) return 20 + ((val - 4) / 1) * 20;
    if (val <= 7) return 40 + ((val - 5) / 2) * 20;
    if (val <= 8) return 60 + ((val - 7) / 1) * 20;
    return 80 + ((val - 8) / 2) * 20;
  };

  const currentStatus = getGaugeStatus(sonValue);


  // Helper component to handle map zooming
  function MapBoundsUpdater({ bounds }) {
    const map = useMap();
    useEffect(() => {
      if (bounds && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    }, [bounds, map]);
    return null;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title text-gradient">Area Profile</h1>
          <p>Analysis complete. Viewing calculated metrics.</p>
        </div>
        <button className="btn-primary" onClick={onReset}>
          Analyze New Area
        </button>
      </div>

      <div className="dashboard-grid">

        {/* Map Card */}
        <div className="glass-panel card-map" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <MapIcon size={20} color="var(--primary)" />
              <h3 className="card-title">Map Visualization</h3>
            </div>
            <select
              value={mapType}
              onChange={(e) => setMapType(e.target.value)}
              className="map-type-selector"
              style={{
                padding: '0.5rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid rgba(0,0,0,0.1)',
                background: 'var(--bg-surface-elevated)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontFamily: 'inherit',
                outline: 'none'
              }}
            >
              <option value="base">Base Map</option>
              <option value="satellite">Satellite Imagery</option>
              <option value="street">Street Map</option>
            </select>
          </div>
          <div className="map-container-wrapper" style={{ height: '400px', width: '100%', position: 'relative' }}>
            <MapContainer
              center={[20, 78]}
              zoom={4}
              style={{ height: '100%', width: '100%', backgroundColor: '#0B0E14' }}
              zoomControl={true}
            >
              <TileLayer
                url={tileUrls[mapType]}
                attribution='Map data providers'
              />
              {geoJson && (
                <GeoJSON
                  data={geoJson}
                  style={{ color: '#10B981', weight: 2, fillOpacity: 0.2 }}
                  onEachFeature={onEachFeature}
                />
              )}
              <MapBoundsUpdater bounds={bounds} />
            </MapContainer>
          </div>
        </div>

        {/* 1. State of Nature Score Gauge Upgrade */}
        <div className="glass-panel card-contribution-donut chart-hover-effect" style={{ padding: '1.5rem', position: 'relative' }}>
          <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.1rem', marginBottom: '0.5rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: '600' }}>Overall Assessment</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
              <PieChartIcon size={20} color="var(--primary)" />
              <div style={{ 
                fontSize: '2.2rem',
                fontWeight: '900',
                color: currentStatus.fill,
                textShadow: `0 0 10px ${currentStatus.fill}40`,
                transition: 'all 0.5s ease',
                lineHeight: '1.1'
              }}>
                {sonValue.toFixed(1)} <span style={{ fontSize: '1.1rem', opacity: 0.5 }}>/ 10</span>
              </div>
            </div>
            <h3 className="card-title" style={{ fontSize: '0.9rem', opacity: 0.7, letterSpacing: '0.5px', border: 'none', padding: 0 }}>State of Nature Score</h3>
          </div>
          <div className="chart-container" style={{ position: 'relative', height: '250px', marginTop: '0' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <Pie
                  dataKey="value"
                  startAngle={180}
                  endAngle={0}
                  data={gaugeData}
                  cx="50%"
                  cy="80%"
                  innerRadius="65%"
                  outerRadius="95%"
                  stroke="#fff"
                  strokeWidth={2}
                  isAnimationActive={true}
                >
                  {gaugeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                {/* Needle and Outer Labels using a dummy Pie activeShape */}
                <Pie
                  data={[{ value: 10, sonValue }]}
                  dataKey="value"
                  startAngle={180}
                  endAngle={0}
                  cx="50%"
                  cy="80%"
                  innerRadius="65%"
                  outerRadius="95%"
                  stroke="none"
                  fill="transparent"
                  activeIndex={0}
                  activeShape={(props) => {
                    const { cx, cy, outerRadius, payload } = props;
                    const value = payload.sonValue;
                    
                    // Needle Math mapped to equal visual segments
                    const visualPercent = getVisualPercentage(value);
                    const ang = 180.0 * (1 - visualPercent / 100);
                    const length = outerRadius + 5;
                    const sin = Math.sin(-RADIAN * ang);
                    const cos = Math.cos(-RADIAN * ang);
                    const r = 7;
                    const xba = cx + r * sin;
                    const yba = cy - r * cos;
                    const xbb = cx - r * sin;
                    const ybb = cy + r * cos;
                    const xp = cx + length * cos;
                    const yp = cy + length * sin;

                    // Range Labels Math
                    const rangeMarkers = [
                      { val: "0", percent: 0 },
                      { val: "4", percent: 20 },
                      { val: "5", percent: 40 },
                      { val: "7", percent: 60 },
                      { val: "8", percent: 80 },
                      { val: "10", percent: 100 }
                    ];
                    const labels = rangeMarkers.map((marker, i) => {
                      const lAng = 180 - (marker.percent / 100) * 180;
                      const lRadius = outerRadius + 15;
                      const lx = cx + lRadius * Math.cos(-RADIAN * lAng);
                      const ly = cy + lRadius * Math.sin(-RADIAN * lAng);
                      return (
                        <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="central" fill="var(--text-muted)" fontSize="10px" fontWeight="700">
                          {marker.val}
                        </text>
                      );
                    });

                    return (
                      <g>
                        {labels}
                        <circle cx={cx} cy={cy} r={r} fill="var(--text-primary)" stroke="none" />
                        <path d={`M${xba} ${yba}L${xbb} ${ybb}L${xp} ${yp}Z`} fill="var(--text-primary)" />
                        <circle cx={cx} cy={cy} r={r - 3} fill="var(--bg-surface)" stroke="none" />
                      </g>
                    );
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ textAlign: 'center', marginTop: '-1rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{
              fontSize: '1.1rem',
              fontWeight: '900',
              color: currentStatus.fill,
              textTransform: 'uppercase',
              letterSpacing: '1px',
              transition: 'all 0.5s ease'
            }}>
              {currentStatus.label}
            </div>

            {/* Legend */}
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '0.5rem',
              marginTop: '0.5rem',
              flexWrap: 'wrap',
              padding: '0.4rem',
              background: 'var(--bg-surface-elevated)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(0,0,0,0.05)',
              width: '100%'
            }}>
              {gaugeData.map(d => (
                <div key={d.label} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '2px', backgroundColor: d.fill }}></div>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', fontWeight: '600', whiteSpace: 'nowrap' }}>
                    {d.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 2. SoN Pillar Score Radar Chart */}
        <div className="glass-panel card-radar-chart" style={{ padding: '1.5rem' }}>
          <div className="card-header">
            <Activity size={20} color="var(--primary)" />
            <h3 className="card-title">SoN Pillar Score</h3>
          </div>
          <div className="chart-container" style={{ height: '250px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                <PolarGrid stroke="rgba(0,0,0,0.1)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 5]} tick={false} axisLine={false} />
                <Radar name="Area" dataKey="A" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.8} />
                <Tooltip
                  wrapperStyle={{ backgroundColor: '#ffffff', opacity: 1, zIndex: 1000, borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.15)' }}
                  contentStyle={{ backgroundColor: '#ffffff', opacity: 1 }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      const score = d.A;
                      return (
                        <div className="tooltip-solid" style={{ backgroundColor: '#ffffff', opacity: 1, padding: '12px', borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.2)' }}>
                          <p style={{ margin: 0, fontWeight: 600 }}>{d.subject}</p>
                          <p style={{ margin: '4px 0 0', fontSize: '0.875rem' }}>
                            Concern: <span style={{ color: getConcernColor(score), fontWeight: 600 }}>{formatConcernLabel(score)} ({score.toFixed(2)})</span>
                          </p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Pressure Index (Refined Ring Graph) */}
        <div className="glass-panel card-pressure-index chart-hover-effect" style={{ padding: '1.5rem' }}>
          <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.25rem', marginBottom: '1.5rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: '600' }}>Threats and Pressure</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <Activity size={20} color={activeColor} />
                <h3 className="card-title">Pressure Index</h3>
              </div>
              <div className="toggle-group">
                {Object.keys(pressureConfig).map(k => {
                  const kVal = pc5[concernKeyMap[k]];
                  const kColor = getConcernColor(kVal);
                  return (
                    <button
                      key={k}
                      className={`toggle-btn ${activePressure === k ? 'active' : ''}`}
                      onClick={() => setActivePressure(k)}
                      style={{
                        padding: '4px 12px',
                        fontSize: '0.75rem',
                        fontWeight: '700',
                        borderRadius: '20px',
                        border: `1.5px solid ${activePressure === k ? kColor : 'var(--border-color)'}`,
                        background: activePressure === k ? kColor : 'transparent',
                        color: activePressure === k ? (kVal > 2.5 && kVal <= 3.5 ? 'black' : 'white') : 'var(--text-secondary)',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        marginLeft: '5px'
                      }}
                    >
                      {k}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', height: '100%' }}>
            <div className="chart-container" style={{ height: '240px', position: 'relative', width: '100%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={ringData}
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={90}
                    startAngle={90}
                    endAngle={-270}
                    dataKey="value"
                    stroke="none"
                  >
                    {ringData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                width: '100%'
              }}>
                <div style={{ fontSize: '1.75rem', fontWeight: '900', color: activeColor, lineHeight: 1.1 }}>
                  {activePData.val.toFixed(2)} <span style={{ fontSize: '1rem', fontWeight: '700' }}>{config.label}</span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '8px', fontWeight: '700', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  <span style={{ color: activeColor }}>{activeLabel}</span>
                </div>
              </div>
            </div>

            {/* Legend / Metrics Info */}
            <div style={{ display: 'flex', gap: '1.5rem', marginTop: '10px', width: '100%', justifyContent: 'center' }}>
              {pressureData.map(d => {
                const dVal = pc5[concernKeyMap[d.name]];
                const dColor = getConcernColor(dVal);
                return (
                  <div 
                    key={d.name} 
                    style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      gap: '0.5rem', 
                      cursor: 'pointer',
                      opacity: activePressure === d.name ? 1 : 0.6,
                      transition: 'all 0.2s',
                      transform: activePressure === d.name ? 'scale(1.05)' : 'scale(1)'
                    }}
                    onClick={() => setActivePressure(d.name)}
                  >
                    <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: dColor, boxShadow: activePressure === d.name ? `0 0 8px ${dColor}` : 'none' }}></div>
                    <span style={{ fontSize: '0.75rem', fontWeight: '800', color: activePressure === d.name ? 'var(--text-primary)' : 'var(--text-muted)' }}>{d.name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 4. Concern Distribution Stacked Chart */}
        <div className="glass-panel card-concern-stacked dashboard-widget chart-hover-effect" style={{ padding: '1.5rem' }}>
          <div className="card-header">
            <BarChart2 size={20} color="var(--primary)" />
            <h3 className="card-title">Concern Distribution</h3>
          </div>
          <div className="chart-container" style={{ height: '250px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stackedData} layout="vertical" margin={{ top: 0, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} width={65} />
                <Tooltip
                  wrapperStyle={{ backgroundColor: '#ffffff', opacity: 1, zIndex: 1000, borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.15)' }}
                  cursor={{ fill: 'rgba(0,0,0,0.05)' }}
                  contentStyle={{ backgroundColor: '#ffffff', opacity: 1, border: '1px solid rgba(0,0,0,0.1)', borderRadius: '8px', color: 'var(--text-primary)' }}
                />
                <Bar dataKey="VH" stackId="a" fill="#D86464" name="Very High" />
                <Bar dataKey="H" stackId="a" fill="#E18259" name="High" />
                <Bar dataKey="M" stackId="a" fill="#F6E975" name="Moderate" />
                <Bar dataKey="L" stackId="a" fill="#78DD8E" name="Low" />
                <Bar dataKey="VL" stackId="a" fill="#73D2D5" name="Very Low" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {/* Custom Legend at the bottom to match Pressure Index style */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            gap: '1rem', 
            marginTop: '1.5rem',
            flexWrap: 'wrap'
          }}>
            {[
              { label: 'Very High', color: '#D86464' },
              { label: 'High', color: '#E18259' },
              { label: 'Moderate', color: '#F6E975' },
              { label: 'Low', color: '#78DD8E' },
              { label: 'Very Low', color: '#73D2D5' }
            ].map((item) => (
              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.color }}></div>
                <span style={{ fontSize: '0.7rem', fontWeight: '800', color: 'var(--text-muted)' }}>{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 5. Temperature Stress Index */}
        <div className="glass-panel card-temperature-index chart-hover-effect" style={{ padding: '1.5rem' }}>
          <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.25rem' }}>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: '600' }}>Threats and Pressure</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Sun size={20} color="var(--color-score-mid)" />
              <h3 className="card-title">Temperature Stress Index</h3>
            </div>
          </div>
          <div className="chart-container" style={{ height: '250px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={temperatureData} margin={{ top: 20, right: 20, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 50]} tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip
                  wrapperStyle={{ backgroundColor: '#ffffff', opacity: 1, zIndex: 1000, borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.15)' }}
                  contentStyle={{ backgroundColor: '#ffffff', opacity: 1 }}
                  cursor={{ fill: 'rgba(0,0,0,0.05)' }}
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const d = payload[0].payload;
                      return (
                        <div className="tooltip-solid" style={{ backgroundColor: '#ffffff', opacity: 1, padding: '12px', borderRadius: '8px', boxShadow: '0 4px 15px rgba(0,0,0,0.2)' }}>
                          <p style={{ margin: 0, fontWeight: 600 }}>{d.name}</p>
                          <p style={{ margin: '4px 0 0', color: getConcernColor(d.concernValue), fontSize: '0.875rem', fontWeight: 600 }}>
                            {d.value.toFixed(2)} {d.name === 'UHI' ? '' : '°C'}
                          </p>
                          {d.concern && (
                            <p style={{ 
                              margin: '8px 0 0', 
                              fontSize: '0.75rem', 
                              textTransform: 'uppercase',
                              letterSpacing: '0.05em'
                            }}>
                              <span style={{ color: 'black', fontWeight: 'normal' }}>Concern: </span>
                              <span style={{ color: getConcernColor(d.concernValue), fontWeight: '800' }}>{d.concern}</span>
                            </p>
                          )}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="none" 
                  strokeWidth={0} 
                  dot={(props) => {
                    const { cx, cy, payload } = props;
                    return (
                      <circle 
                        key={payload.name}
                        cx={cx} 
                        cy={cy} 
                        r={8} 
                        fill={getConcernColor(payload.concernValue)} 
                        stroke="none" 
                      />
                    );
                  }}
                  activeDot={(props) => {
                    const { cx, cy, payload } = props;
                    return (
                      <circle 
                        cx={cx} 
                        cy={cy} 
                        r={10} 
                        fill={getConcernColor(payload.concernValue)} 
                        stroke="#fff" 
                        strokeWidth={2}
                      />
                    );
                  }} 
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 6. Metric Density by Pillar Chart */}
        <div className="glass-panel card-pillar-bar chart-hover-effect" style={{ padding: '1.5rem' }}>
          <div className="card-header" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: '600' }}>Baseline Diagnostic</div>
              <div style={{ fontSize: '0.7rem', fontWeight: '800', color: 'var(--primary)', textTransform: 'uppercase' }}>
                {pillarMetricCounts.reduce((acc, curr) => acc + curr.count, 0)} Metrics Total
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <BarChart2 size={20} color="var(--primary)" />
              <h3 className="card-title">Metric Density by Pillar</h3>
            </div>
          </div>
          <div className="chart-container" style={{ height: '250px', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pillarMetricCounts} margin={{ top: 25, right: 30, left: -20, bottom: 5 }}>
                <defs>
                  {pillarMetricCounts.map((entry, index) => (
                    <linearGradient key={`grad-${index}`} id={`colorPillar-${index}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={entry.fill} stopOpacity={0.9} />
                      <stop offset="95%" stopColor={entry.fill} stopOpacity={0.4} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis 
                  dataKey="name" 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{ fontSize: 10, fontWeight: 700, fill: 'var(--text-secondary)' }} 
                />
                <YAxis hide domain={[0, 'dataMax + 2']} />
                <Tooltip 
                  cursor={{ fill: 'rgba(0,0,0,0.03)', radius: 10 }}
                  contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', padding: '10px' }}
                />
                <Bar dataKey="count" radius={[12, 12, 4, 4]} barSize={45}>
                  {pillarMetricCounts.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={`url(#colorPillar-${index})`} />
                  ))}
                  <Recharts.LabelList 
                    dataKey="count" 
                    position="top" 
                    offset={10}
                    style={{ fill: 'var(--text-primary)', fontWeight: 900, fontSize: '15px', fontFamily: 'inherit' }} 
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          {/* Custom Legend at the bottom */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            gap: '1rem', 
            marginTop: '1rem',
            flexWrap: 'wrap'
          }}>
            {pillarMetricCounts.map((item) => (
              <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: item.fill }}></div>
                <span style={{ fontSize: '0.7rem', fontWeight: '800', color: 'var(--text-muted)' }}>{item.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Detailed Metrics Grid */}
        <div className="glass-panel card-metrics" style={{ padding: '2rem' }}>
          <div className="card-header">
            <BarChart2 size={24} color="var(--text-primary)" />
            <h3 className="card-title" style={{ fontSize: '1.25rem' }}>Detailed Metrics</h3>
          </div>

          {(metrics && typeof metrics === 'object') ? Object.entries(metrics).map(([groupName, groupData]) => {
            const isExpanded = expandedGroup === groupName;
            return (
              <div key={groupName} className="metrics-section" style={{ marginBottom: '0.25rem' }}>
                <div
                  className="accordion-header"
                  onClick={() => setExpandedGroup(isExpanded ? null : groupName)}
                >
                  <div className="accordion-title">
                    {getPillarName(groupName)}
                  </div>
                  {isExpanded ? <ChevronUp size={20} color="var(--text-secondary)" /> : <ChevronDown size={20} color="var(--text-secondary)" />}
                </div>

                <div className={`accordion-content ${isExpanded ? 'expanded' : ''}`}>
                  <div className="metrics-list">
                    {groupData && typeof groupData === 'object' && Object.entries(groupData).map(([metricName, metricValue]) => {
                      const rawValue = data.raw_metrics?.[groupName]?.[metricName] ?? 0;
                      const grade = getMetricGrade(metricValue, groupName, metricName, data);
                      return (
                        <div key={metricName} className="metric-item">
                          <span className="metric-name" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            {getMetricIcon(metricName)}
                            <span>{metricName.replace(/_/g, ' ')}</span>
                            <Info
                              size={14}
                              color="var(--text-muted)"
                              style={{ cursor: 'help' }}
                              title={`Calculated parameter indexing algorithm value for ${metricName.replace(/_/g, ' ')}. Indicates current health standard.`}
                            />
                          </span>
                          <span style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span className={`metric-badge ${grade.class}`}>{grade.label}</span>
                            <span className="metric-val" style={{ width: metricValue === "Coming soon" ? 'auto' : 'auto', minWidth: '40px', textAlign: 'right', fontSize: metricValue === "Coming soon" ? '0.875rem' : 'inherit', color: metricValue === "Coming soon" ? 'var(--text-muted)' : 'inherit' }}>
                              {metricValue === "Coming soon" ? metricValue :
                                (metricName.toLowerCase().includes('species') || metricName.toLowerCase().includes('richness') || metricName.toLowerCase().includes('range') || metricName.toLowerCase().includes('count')) ?
                                  Math.round(parseFloat(rawValue)) :
                                  `${parseFloat(rawValue).toFixed(2)}${metricName.toUpperCase().includes('LST') ? '°C' : ''}`}
                            </span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          }) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No detailed metrics available for this site.
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
