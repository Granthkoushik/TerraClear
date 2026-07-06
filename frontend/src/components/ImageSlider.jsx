import React, { useState, useRef, useEffect } from 'react';

export default function ImageSlider({ original, reconstructed }) {
  const [sliderPosition, setSliderPosition] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);

  const handleMove = (clientX) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const position = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(position);
  };

  const handleTouchMove = (e) => {
    if (!isDragging) return;
    if (e.touches && e.touches[0]) {
      handleMove(e.touches[0].clientX);
    }
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    handleMove(e.clientX);
  };

  useEffect(() => {
    const handleMouseUp = () => setIsDragging(false);
    window.addEventListener('mouseup', handleMouseUp);
    window.addEventListener('touchend', handleMouseUp);
    
    return () => {
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('touchend', handleMouseUp);
    };
  }, []);

  return (
    <div 
      className="slider-wrapper" 
      ref={containerRef}
      onMouseDown={() => setIsDragging(true)}
      onTouchStart={() => setIsDragging(true)}
      onMouseMove={handleMouseMove}
      onTouchMove={handleTouchMove}
      style={{ cursor: isDragging ? 'ew-resize' : 'default' }}
    >
      {/* Before Image (Original) */}
      <div className="slider-before">
        <img src={original} alt="Original Cloudy Satellite" />
        <div style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          background: 'rgba(0,0,0,0.6)',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: '500',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          Original LISS-IV
        </div>
      </div>

      {/* After Image (Reconstructed) */}
      <div 
        className="slider-after" 
        style={{ clipPath: `polygon(0 0, ${sliderPosition}% 0, ${sliderPosition}% 100%, 0 100%)` }}
      >
        <img src={reconstructed} alt="Reconstructed Surface" />
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          background: 'rgba(16, 185, 129, 0.75)',
          padding: '4px 8px',
          borderRadius: '4px',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: '#040810',
          border: '1px solid rgba(16, 185, 129, 0.3)'
        }}>
          Reconstructed Clear-Surface
        </div>
      </div>

      {/* Slider Bar & Drag Handle */}
      <div 
        className="slider-bar" 
        style={{ left: `${sliderPosition}%` }}
      >
        <div className="slider-handle">
          ↔
        </div>
      </div>
    </div>
  );
}
