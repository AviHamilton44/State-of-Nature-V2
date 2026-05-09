import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Filter, BarChart3 } from 'lucide-react';
import './SectorMatrix.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:8001';

const BIOMES_DATA = [
  { name: "Tropical-subtropical forests", code: "T1" },
  { name: "Temperate-boreal forests and woodlands", code: "T2" },
  { name: "Shrublands and shrubby woodlands", code: "T3" },
  { name: "Savannas and grasslands", code: "T4" },
  { name: "Deserts and semi-deserts", code: "T5" },
  { name: "Polar/alpine (cryogenic)", code: "T6" },
  { name: "Intensive land-use", code: "T7" },
  { name: "Marine shelf", code: "M1" },
  { name: "Pelagic ocean waters", code: "M2" },
  { name: "Deep sea floors", code: "M3" },
  { name: "Anthropogenic marine", code: "M4" },
  { name: "Rivers and streams", code: "F1" },
  { name: "Lakes", code: "F2" },
  { name: "Artificial wetlands", code: "F3" },
  { name: "Subterranean lithic", code: "S1" },
  { name: "Anthropogenic subterranean voids", code: "S2" },
  { name: "Shorelines", code: "MT1" },
  { name: "Supralittoral coastal", code: "MT2" },
  { name: "Anthropogenic shorelines", code: "MT3" },
  { name: "Subterranean freshwaters", code: "SF1" },
  { name: "Anthropogenic subterranean freshwaters", code: "SF2" },
  { name: "Semi-confined transitional waters", code: "FM1" },
  { name: "Brackish tidal", code: "MFT1" },
  { name: "Subterranean tidal", code: "SM1" },
  { name: "Palustrine wetlands", code: "TF1" }
];

const getScoreColor = (score) => {
  if (score <= 4) return '#73D2D5'; // Very Low
  if (score <= 5) return '#78DD8E'; // Low
  if (score <= 7) return '#F6E975'; // Moderate
  if (score <= 8) return '#E18259'; // High
  return '#D86464'; // Very High
};

const SectorMatrix = ({ siteScore }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedGroup, setSelectedGroup] = useState('All');
  const [hoveredCell, setHoveredCell] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_BASE_URL}/api/sector-son-matrix`);
        setData(res.data);
      } catch (err) {
        console.error("Failed to fetch sector matrix", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const groups = ['All', ...new Set(data.map(item => item.group))];
  const uniqueSectors = [...new Set(data.map(item => item.sector))];

  const filteredSectors = uniqueSectors.filter(sector => {
    const firstMatch = data.find(item => item.sector === sector);
    const matchesSearch = sector.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesGroup = selectedGroup === 'All' || (firstMatch && firstMatch.group === selectedGroup);
    return matchesSearch && matchesGroup;
  });

  const getCellData = (sector, biomeName) => {
    return data.find(item => item.sector === sector && item.biome === biomeName);
  };

  if (loading) return <div className="loading-state">Loading Sector Matrix...</div>;

  return (
    <div className="sector-matrix-wrapper">
      <div className="matrix-header">
        <div className="header-info">
          <h2 className="title">Sector SoN Matrix (ENCORE × TNFD)</h2>
          <p className="subtitle">Benchmark comparison across industry activities and 25 Biomes.</p>
        </div>
        
        <div className="matrix-controls">
          <div className="search-box">
            <Search size={18} />
            <input 
              type="text" 
              placeholder="Search sectors..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="filter-box">
            <Filter size={18} />
            <select value={selectedGroup} onChange={(e) => setSelectedGroup(e.target.value)}>
              {groups.map(group => <option key={group} value={group}>{group}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="matrix-legend" style={{ gap: '1rem', flexWrap: 'wrap' }}>
        <div className="legend-item"><span className="dot" style={{backgroundColor: '#73D2D5'}}></span> Very Low (0-4)</div>
        <div className="legend-item"><span className="dot" style={{backgroundColor: '#78DD8E'}}></span> Low (4-5)</div>
        <div className="legend-item"><span className="dot" style={{backgroundColor: '#F6E975'}}></span> Moderate (5-7)</div>
        <div className="legend-item"><span className="dot" style={{backgroundColor: '#E18259'}}></span> High (7-8)</div>
        <div className="legend-item"><span className="dot" style={{backgroundColor: '#D86464'}}></span> Very High (8-10)</div>
      </div>

      <div className="matrix-scroll-area">
        <table className="matrix-table">
          <thead>
            <tr>
              <th className="sticky-col">Sector Activity</th>
              {BIOMES_DATA.map(b => (
                <th key={b.code} title={b.name} className="biome-th">
                  {b.code}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredSectors.map(sector => (
              <tr key={sector}>
                <td className="sticky-col sector-name">
                  <div>{sector}</div>
                  <div className="group-tag">{data.find(d => d.sector === sector)?.group}</div>
                </td>
                {BIOMES_DATA.map(b => {
                  const cell = getCellData(sector, b.name);
                  if (!cell) return <td key={b.code} className="empty-cell">-</td>;
                  
                  return (
                    <td 
                      key={b.code} 
                      className="matrix-cell"
                      style={{ backgroundColor: getScoreColor(cell.son_score) + '20' }}
                      onMouseEnter={() => setHoveredCell(cell)}
                      onMouseLeave={() => setHoveredCell(null)}
                    >
                      <div className="score-val" style={{ color: getScoreColor(cell.son_score) }}>
                        {cell.son_score.toFixed(1)}
                      </div>
                      
                      {hoveredCell === cell && (
                        <div className="cell-tooltip">
                          <div className="tooltip-header">{sector}</div>
                          <div className="tooltip-biome">{b.name} ({b.code})</div>
                          <div className="tooltip-son">Overall SoN: {cell.son_score}</div>
                          <div className="tooltip-dims">
                            <div>Extent: {cell.dimensions.extent}</div>
                            <div>Condition: {cell.dimensions.condition}</div>
                            <div>Population: {cell.dimensions.population}</div>
                            <div>Extinction: {cell.dimensions.extinction}</div>
                          </div>
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {siteScore && (
        <div className="benchmark-bar glass-panel">
          <div className="comparison-icon">
            <BarChart3 size={24} color="var(--primary)" />
          </div>
          <div className="comparison-text">
            <h3>Industry Benchmarking</h3>
            <p>Your site SoN score (<strong>{siteScore}</strong>) can be benchmarked against the sector-biome averages above.</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SectorMatrix;
