import React, { useState } from 'react';
import { 
  Upload, Play, Download, Cpu, Layers, Settings, 
  Terminal, CheckCircle2, AlertCircle, Eye, RefreshCw, Info 
} from 'lucide-react';
import { uploadImage, processImage, getDownloadUrl } from '../utils/api';
import ImageSlider from './ImageSlider';
import MetadataPanel from './MetadataPanel';

export default function Dashboard() {
  // State variables
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadData, setUploadData] = useState(null);
  const [processData, setProcessData] = useState(null);
  const [threshold, setThreshold] = useState(0.5);
  const [forceClassical, setForceClassical] = useState(false);
  const [activeTab, setActiveTab] = useState('original'); // original, mask, reconstructed, slider
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), text: 'System ready. Awaiting image upload...', type: 'info' }
  ]);

  const addLog = (text, type = 'info') => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), text, type }]);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = async (e) => {
    if (e.target.files && e.target.files[0]) {
      await handleUpload(e.target.files[0]);
    }
  };

  const handleUpload = async (selectedFile) => {
    // Validate format
    const ext = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
    if (!['.tif', '.tiff', '.png', '.jpg', '.jpeg'].includes(ext)) {
      addLog(`Upload error: Format ${ext} not supported.`, 'error');
      alert(`Format ${ext} not supported. Upload a GeoTIFF, TIFF, PNG, or JPEG.`);
      return;
    }

    setFile(selectedFile);
    setIsUploading(true);
    setUploadData(null);
    setProcessData(null);
    addLog(`Uploading file ${selectedFile.name}...`, 'info');

    try {
      const data = await uploadImage(selectedFile);
      setUploadData(data);
      addLog(`File uploaded successfully. Assigned Image ID: ${data.image_id}`, 'success');
      addLog(`Extracted image dimensions: ${data.width}x${data.height}px with ${data.bands} bands.`, 'info');
      if (data.has_geospatial) {
        addLog(`Geospatial projection detected: ${data.metadata?.crs || 'Unknown CRS'}`, 'success');
      } else {
        addLog('No geocoding reference found in metadata. Proceeding with standard pixel space.', 'info');
      }
      setActiveTab('original');
      
      // Auto-trigger cloud removal!
      await triggerProcessing(data);
    } catch (err) {
      addLog(`Upload failed: ${err.message}`, 'error');
      alert(err.message);
      setFile(null);
    } finally {
      setIsUploading(false);
    }
  };

  const triggerProcessing = async (targetUploadData = null) => {
    const activeUploadData = targetUploadData || uploadData;
    if (!activeUploadData) return;
    setIsProcessing(true);
    setProcessData(null);
    addLog(`Initiating cloud removal pipeline on image ${activeUploadData.image_id}...`, 'info');
    addLog(`Parameters - Sensitivity Threshold: ${threshold}, Forced DIP Mode: ${forceClassical}`, 'info');

    try {
      const data = await processImage(activeUploadData.image_id, threshold, forceClassical);
      setProcessData(data);
      addLog('Cloud detection algorithm finished execution.', 'success');
      addLog(`Calculated Cloud Coverage: ${data.cloud_coverage_percentage}%`, 'info');
      addLog(`Surface reconstructed in ${data.processing_time_seconds}s. Confidence Score: ${data.confidence_score}`, 'success');
      setActiveTab('slider');
    } catch (err) {
      addLog(`Processing failed: ${err.message}`, 'error');
      alert(err.message);
    } finally {
      setIsProcessing(false);
    }
  };

  const resetAll = () => {
    setFile(null);
    setUploadData(null);
    setProcessData(null);
    setThreshold(0.5);
    setForceClassical(false);
    setActiveTab('original');
    setLogs([{ time: new Date().toLocaleTimeString(), text: 'System reset. Awaiting image upload...', type: 'info' }]);
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="header glass-panel">
        <div className="logo-container">
          <Layers size={24} style={{ color: 'var(--accent-primary)' }} />
          <h1 className="logo-text">TerraClear</h1>
          <span style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.05)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-secondary)' }}>LISS-IV MVP</span>
        </div>
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>Cloud Reconstruction Pipeline: Active</span>
        </div>
      </header>

      {/* Left Sidebar */}
      <aside className="sidebar">
        {/* Upload Panel */}
        <section className="glass-panel" style={{ padding: '20px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Upload size={18} style={{ color: 'var(--accent-primary)' }} />
            Satellite Data Input
          </h2>

          {!file ? (
            <div 
              className="dropzone"
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              <Upload size={36} className="text-muted" style={{ strokeWidth: 1.5 }} />
              <div>
                <p style={{ fontWeight: 500, margin: '0 0 4px 0' }}>Drag & drop image file</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>GeoTIFF, TIFF, PNG, or JPG up to 50MB</p>
              </div>
              <label className="btn btn-secondary" style={{ display: 'inline-block', width: 'auto', cursor: 'pointer' }}>
                Browse Files
                <input type="file" onChange={handleFileChange} style={{ display: 'none' }} accept=".tif,.tiff,.png,.jpg,.jpeg" />
              </label>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                <CheckCircle2 size={18} style={{ color: 'var(--accent-primary)' }} />
                <div style={{ overflow: 'hidden' }}>
                  <p style={{ fontSize: '0.85rem', fontWeight: 500, margin: 0, textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>{file.name}</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={resetAll}>
                <RefreshCw size={14} /> Clear Selection
              </button>
            </div>
          )}
        </section>

        {/* Processing Controls Panel */}
        <section className="glass-panel" style={{ padding: '20px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Settings size={18} style={{ color: 'var(--accent-secondary)' }} />
            Pipeline Parameters
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label">Detection Sensitivity</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', fontWeight: 600 }}>{threshold}</span>
              </div>
              <input 
                type="range" 
                min="0.1" 
                max="0.9" 
                step="0.05" 
                value={threshold} 
                onChange={(e) => setThreshold(parseFloat(e.target.value))} 
                className="input-slider"
                disabled={!uploadData || isProcessing}
              />
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: 0 }}>
                Adjust threshold sensitivity. Lower values capture more cloud haze.
              </p>
            </div>

            <div className="toggle-container">
              <span className="label" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                Forced Classical (DIP)
                <span title="Bypasses deep learning weights and enforces OpenCV Telea/Navier-Stokes and HSV thresholding.">
                  <Info size={12} className="text-muted" />
                </span>
              </span>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={forceClassical} 
                  onChange={(e) => setForceClassical(e.target.checked)}
                  disabled={!uploadData || isProcessing}
                />
                <span className="slider-round"></span>
              </label>
            </div>

            <button 
              className="btn btn-primary" 
              onClick={triggerProcessing}
              disabled={!uploadData || isProcessing || isUploading}
              style={{ width: '100%', marginTop: '10px' }}
            >
              {isProcessing ? (
                <>
                  <RefreshCw size={16} className="spinner" style={{ animation: 'spin 1s infinite linear' }} />
                  Processing...
                </>
              ) : (
                <>
                  <Play size={16} fill="currentColor" />
                  Process Image
                </>
              )}
            </button>
          </div>
        </section>

        {/* Real-time System Console */}
        <section className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} style={{ color: 'var(--text-muted)' }} />
            Telemetry Console
          </h2>
          <div className="console-box">
            {logs.map((log, index) => (
              <div key={index} className="console-line">
                <span className="console-timestamp">[{log.time}]</span>
                <span className={`console-text ${log.type}`}>{log.text}</span>
              </div>
            ))}
          </div>
        </section>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Visualization Card */}
        <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Top Panel Actions / Navigation tabs */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-glass)', paddingBottom: '12px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                className={`btn ${activeTab === 'original' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('original')}
                disabled={!uploadData}
              >
                Original Image
              </button>
              <button 
                className={`btn ${activeTab === 'mask' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('mask')}
                disabled={!processData}
              >
                Cloud Mask
              </button>
              <button 
                className={`btn ${activeTab === 'reconstructed' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('reconstructed')}
                disabled={!processData}
              >
                Reconstructed Surface
              </button>
              <button 
                className={`btn ${activeTab === 'slider' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                onClick={() => setActiveTab('slider')}
                disabled={!processData}
              >
                Swipe Compare
              </button>
            </div>

            {/* Download Buttons */}
            {processData && (
              <div style={{ display: 'flex', gap: '8px' }}>
                <a 
                  href={getDownloadUrl(uploadData.image_id, 'reconstructed')} 
                  download 
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.85rem', color: 'var(--accent-primary)', borderColor: 'var(--border-glass-active)' }}
                >
                  <Download size={14} /> Download Surface
                </a>
              </div>
            )}
          </div>

          {/* Large Image View */}
          <div style={{ flex: 1, minHeight: '400px' }}>
            {!uploadData ? (
              <div className="empty-state">
                <Eye size={48} className="text-muted" style={{ strokeWidth: 1 }} />
                <p style={{ fontSize: '1.1rem', fontWeight: 500, margin: 0 }}>Satellite Viewer Standby</p>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '300px', margin: 0 }}>
                  Upload a LISS-IV GeoTIFF image to visualize the bands, geospatial bounds, and execute cloud correction algorithms.
                </p>
              </div>
            ) : (
              <div className="viewer-container">
                {isProcessing ? (
                  <div className="empty-state">
                    <RefreshCw size={36} className="spinner" style={{ animation: 'spin 1.5s infinite linear' }} />
                    <p style={{ fontWeight: 500 }}>Processing cloud removal algorithms...</p>
                  </div>
                ) : (
                  <>
                    {activeTab === 'original' && (
                      <div className="image-wrapper">
                        <img 
                          src={getDownloadUrl(uploadData.image_id, 'original')} 
                          alt="Original" 
                          className="viewer-image"
                        />
                      </div>
                    )}
                    {activeTab === 'mask' && (
                      <div className="image-wrapper">
                        <img 
                          src={getDownloadUrl(uploadData.image_id, 'mask')} 
                          alt="Cloud Mask" 
                          className="viewer-image"
                        />
                      </div>
                    )}
                    {activeTab === 'reconstructed' && (
                      <div className="image-wrapper">
                        <img 
                          src={getDownloadUrl(uploadData.image_id, 'reconstructed')} 
                          alt="Reconstructed" 
                          className="viewer-image"
                        />
                      </div>
                    )}
                    {activeTab === 'slider' && (
                      <div className="image-wrapper">
                        <ImageSlider 
                          original={getDownloadUrl(uploadData.image_id, 'original')}
                          reconstructed={getDownloadUrl(uploadData.image_id, 'reconstructed')}
                        />
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Bottom Details Footer (Metadata on Left, Key Performance Metrics on Right) */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '20px' }}>
          {/* Metadata */}
          <div className="glass-panel" style={{ padding: '20px' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} style={{ color: 'var(--accent-primary)' }} />
              LISS-IV Geospatial Metadata Tags
            </h2>
            <MetadataPanel metadata={uploadData} hasGeospatial={uploadData?.has_geospatial} />
          </div>

          {/* Performance Metrics */}
          <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Cpu size={18} style={{ color: 'var(--accent-secondary)' }} />
              Reconstruction Analytics
            </h2>

            {processData ? (
              <div className="metrics-grid">
                <div className="metric-card">
                  <div className="label" style={{ fontSize: '0.75rem' }}>Cloud Cover</div>
                  <div className="metric-value emerald">{processData.cloud_coverage_percentage}%</div>
                </div>
                <div className="metric-card">
                  <div className="label" style={{ fontSize: '0.75rem' }}>Confidence</div>
                  <div className="metric-value cyan">{(processData.confidence_score * 100).toFixed(0)}%</div>
                </div>
                <div className="metric-card" style={{ gridColumn: '1 / -1' }}>
                  <div className="label" style={{ fontSize: '0.75rem' }}>Inference Duration</div>
                  <div className="metric-value">{processData.processing_time_seconds} seconds</div>
                </div>
              </div>
            ) : (
              <div className="empty-state" style={{ padding: '20px', flex: 1 }}>
                <Info size={24} className="text-muted" />
                <p style={{ fontSize: '0.8rem', textAlign: 'center', margin: 0 }}>
                  Awaiting processing to calculate cloud coverage and surface reconstruction confidence.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
