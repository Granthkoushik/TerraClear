import React from 'react';
import { Globe, MapPin, Grid, Layers } from 'lucide-react';

export default function MetadataPanel({ metadata, hasGeospatial }) {
  if (!metadata) {
    return (
      <div className="empty-state">
        <Globe size={32} className="text-muted" />
        <p>Upload a satellite image to view metadata</p>
      </div>
    );
  }

  const formatSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <div>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={18} className="text-primary" style={{ color: 'var(--accent-primary)' }} />
          Image Specifications
        </h3>
        <table className="meta-table">
          <tbody>
            <tr>
              <td className="meta-key">Dimensions</td>
              <td className="meta-value">{metadata.width} × {metadata.height} px</td>
            </tr>
            <tr>
              <td className="meta-key">Bands</td>
              <td className="meta-value">{metadata.bands}</td>
            </tr>
            <tr>
              <td className="meta-key">File Size</td>
              <td className="meta-value">{formatSize(metadata.size_bytes)}</td>
            </tr>
            <tr>
              <td className="meta-key">Geo-Referenced</td>
              <td className="meta-value">
                <span style={{ 
                  color: hasGeospatial ? 'var(--accent-primary)' : 'var(--text-muted)',
                  fontWeight: 600
                }}>
                  {hasGeospatial ? 'Yes (ISRO/GeoTIFF Standard)' : 'No (Standard Image)'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {hasGeospatial && metadata.metadata && (
        <>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '12px 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Globe size={18} style={{ color: 'var(--accent-secondary)' }} />
              Spatial Reference
            </h3>
            <table className="meta-table">
              <tbody>
                <tr>
                  <td className="meta-key">CRS</td>
                  <td className="meta-value" title={metadata.metadata.crs}>{metadata.metadata.crs || 'N/A'}</td>
                </tr>
                {metadata.metadata.resolution && (
                  <tr>
                    <td className="meta-key">Resolution</td>
                    <td className="meta-value">
                      X: {metadata.metadata.resolution.x.toFixed(2)}m, Y: {metadata.metadata.resolution.y.toFixed(2)}m
                    </td>
                  </tr>
                )}
                {metadata.metadata.center && (
                  <tr>
                    <td className="meta-key">Center Lat/Lng</td>
                    <td className="meta-value">
                      X: {metadata.metadata.center.x.toFixed(4)}, Y: {metadata.metadata.center.y.toFixed(4)}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {metadata.metadata.bounds && (
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '12px 0 12px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <MapPin size={18} style={{ color: 'var(--accent-secondary)' }} />
                Bounding Coordinates
              </h3>
              <table className="meta-table">
                <tbody>
                  <tr>
                    <td className="meta-key">Left (Min X)</td>
                    <td className="meta-value">{metadata.metadata.bounds.left.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="meta-key">Right (Max X)</td>
                    <td className="meta-value">{metadata.metadata.bounds.right.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="meta-key">Bottom (Min Y)</td>
                    <td className="meta-value">{metadata.metadata.bounds.bottom.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td className="meta-key">Top (Max Y)</td>
                    <td className="meta-value">{metadata.metadata.bounds.top.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
