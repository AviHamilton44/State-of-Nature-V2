import React, { useState, useRef } from 'react';
import { UploadCloud, FileType } from 'lucide-react';
import './FileUpload.css';

export default function FileUpload({ onUpload }) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files[0]);
    }
  };

  const handleFiles = (file) => {
    // Basic validation, but we proceed anyway as it's a mock
    onUpload(file);
  };

  const onButtonClick = () => {
    inputRef.current.click();
  };

  return (
    <div 
      className={`upload-container ${dragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      onClick={onButtonClick}
    >
      <input 
        ref={inputRef}
        type="file" 
        className="hidden-input" 
        onChange={handleChange} 
        accept=".zip,.shp,.kml" 
      />
      
      <div className="upload-icon-wrapper">
        <UploadCloud size={48} />
      </div>
      
      <h2 className="upload-title">Upload Area Geometry</h2>
      <p className="upload-subtitle">Drag and drop a shapefile (.zip) or KML</p>
      
      <button className="btn-primary" onClick={(e) => { e.stopPropagation(); onButtonClick(); }}>
        <FileType size={20} />
        Select File
      </button>
    </div>
  );
}
