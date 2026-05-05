import React, { useState } from 'react';
import axios from 'axios';
import { Compass } from 'lucide-react';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import SectorMatrix from './components/SectorMatrix';
import shp from 'shpjs';
import darukaaLogo from './assets/Darukaa1.png';

import './App.css';

// Mock delays for better UX
const delay = (ms) => new Promise(res => setTimeout(res, ms));

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';

// Minimal KML to GeoJSON parser
const parseKML = (text) => {
  try {
    const parser = new DOMParser();
    const xml = parser.parseFromString(text, 'text/xml');
    const placemarks = xml.getElementsByTagName('Placemark');
    const features = [];

    for (const placemark of placemarks) {
      const name = placemark.getElementsByTagName('name')[0]?.textContent || 'Untitled';

      // Handle Polygons
      const polygons = placemark.getElementsByTagName('Polygon');
      for (const poly of polygons) {
        const coordStrings = poly.getElementsByTagName('coordinates')[0]?.textContent.trim().split(/\s+/);
        const coordinates = coordStrings.map(pair => pair.split(',').map(Number).slice(0, 2));
        features.push({
          type: 'Feature',
          properties: { name },
          geometry: { type: 'Polygon', coordinates: [coordinates] }
        });
      }

      // Handle Points if no Polygons exist for this placemark
      if (polygons.length === 0) {
        const points = placemark.getElementsByTagName('Point');
        for (const point of points) {
          const coordString = point.getElementsByTagName('coordinates')[0]?.textContent.trim();
          const coordinates = coordString.split(',').map(Number).slice(0, 2);
          features.push({
            type: 'Feature',
            properties: { name },
            geometry: { type: 'Point', coordinates }
          });
        }
      }
    }

    if (features.length === 0) return null;
    return features.length === 1 ? features[0] : { type: 'FeatureCollection', features };
  } catch (err) {
    console.error('Error parsing KML:', err);
    return null;
  }
};

function App() {
  const [appState, setAppState] = useState('idle'); // 'idle', 'uploading', 'analyzing', 'calculating', 'results'
  const [activeTab, setActiveTab] = useState('profile'); // 'profile', 'matrix'
  const [data, setData] = useState(null);
  const [geoJson, setGeoJson] = useState(null);
  const [year, setYear] = useState(2025); // Default to latest requested year

  const handleUpload = async (file) => {
    try {
      setAppState('uploading');

      // 1. Call New Pipeline API
      const formData = new FormData();
      formData.append('file', file);
      formData.append('year', year);

      setAppState('analyzing');
      const response = await axios.post(`${API_BASE_URL}/api/run-pipeline`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });

      if (response.data.status === 'success') {
        setData(response.data.scoring);
        
        // Capture GeoJSON from the server and wrap for Leaflet
        if (response.data.geojson) {
          setGeoJson({
            type: "FeatureCollection",
            features: [{
              type: "Feature",
              properties: {},
              geometry: response.data.geojson
            }]
          });
        }
        
        setAppState('results');
      } else {
        throw new Error('Pipeline analysis failed');
      }

    } catch (error) {
      console.error("Error processing file:", error);
      alert("Analysis failed. Ensure the Pipeline API (port 8001) is running with GEE access.");
      setAppState('idle');
    }
  };

  const resetApp = () => {
    setData(null);
    setGeoJson(null);
    setAppState('idle');
  };

  const renderLoadingState = () => {
    let message = "Processing...";
    if (appState === 'uploading') message = "Uploading spatial data...";
    if (appState === 'analyzing') message = "Analyzing environmental matrices...";
    if (appState === 'calculating') message = "Calculating State of Nature score...";

    return (
      <div className="loading-container">
        <div className="loading-spinner-wrapper">
          <div className="loading-ring animate-spin"></div>
          <Compass size={32} color="var(--primary)" />
        </div>
        <p className="loading-text">{message}</p>
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon">
            <img src={darukaaLogo} alt="Darukaa Logo" />
          </div>
          <div>
            <h1 className="app-subtitle" style={{ fontSize: '1rem', fontWeight: '500' }}>State of Nature Dashboard</h1>
          </div>
        </div>

        {appState === 'results' && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Status</div>
            <div style={{ color: 'var(--color-score-high)', fontWeight: '600' }}>Analysis complete</div>
          </div>
        )}
      </header>

      <main className="main-content">
        {appState === 'idle' && (
          <div className="upload-screen">
            <div className="year-selector-wrapper">
              <label htmlFor="year-select">Analysis Year:</label>
              <select
                id="year-select"
                value={year}
                onChange={(e) => setYear(parseInt(e.target.value))}
                className="year-dropdown"
              >
                {[2025, 2024].map(y => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <FileUpload onUpload={handleUpload} />
          </div>
        )}

        {(appState === 'uploading' || appState === 'analyzing' || appState === 'calculating') && renderLoadingState()}

        {appState === 'results' && (
          <div className="tabs-wrapper">
            <nav className="header-tabs">
              <button
                className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
                onClick={() => setActiveTab('profile')}
              >
                Area Profile
              </button>
              <button
                className={`tab-btn ${activeTab === 'matrix' ? 'active' : ''}`}
                onClick={() => setActiveTab('matrix')}
              >
                Sector Matrix
              </button>
            </nav>
          </div>
        )}

        {appState === 'results' && activeTab === 'profile' && (
          <Dashboard data={data} geoJson={geoJson} onReset={resetApp} />
        )}

        {appState === 'results' && activeTab === 'matrix' && (
          <SectorMatrix siteScore={data?.["SoN Score"]} />
        )}
      </main>
    </div>
  );
}

export default App;