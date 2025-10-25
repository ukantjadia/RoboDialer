"use client"

import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapLocation {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  phone?: string;
  website?: string;
  rating?: number;
  businessType?: string;
  mapsUrl?: string;
}

interface MapComponentProps {
  locations: MapLocation[];
}

// Fix for Leaflet marker icons in Next.js
const icon = L.icon({
  iconUrl: '/images/marker-icon.png',
  iconRetinaUrl: '/images/marker-icon-2x.png',
  shadowUrl: '/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

// Fallback icon if marker images don't exist
const createCustomIcon = (color: string = '#3B82F6') => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background-color: ${color};
        width: 20px;
        height: 20px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 12px;
      ">
        📍
      </div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  });
};

export default function MapComponent({ locations }: MapComponentProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || locations.length === 0) return;

    // Initialize map
    const map = L.map(mapRef.current).setView([37.7749, -122.4194], 10);
    mapInstanceRef.current = map;

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Add markers for each location
    locations.forEach((location, index) => {
      const marker = L.marker([location.latitude, location.longitude], {
        icon: createCustomIcon(index === 0 ? '#EF4444' : '#3B82F6') // First location is red, others are blue
      }).addTo(map);

      // Create popup content
      const popupContent = `
        <div style="min-width: 200px;">
          <h3 style="margin: 0 0 8px 0; font-weight: bold; color: #1F2937;">${location.name}</h3>
          <p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">${location.address}</p>
          ${location.phone ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">📞 ${location.phone}</p>` : ''}
          ${location.website ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">🌐 <a href="${location.website}" target="_blank" style="color: #3B82F6;">Visit Website</a></p>` : ''}
          ${location.rating ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">⭐ ${location.rating}/5</p>` : ''}
          ${location.businessType ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">🏢 ${location.businessType}</p>` : ''}
          ${location.mapsUrl ? `<p style="margin: 0 0 0 0; color: #6B7280; font-size: 14px;">🗺️ <a href="${location.mapsUrl}" target="_blank" style="color: #3B82F6;">View on Google Maps</a></p>` : ''}
        </div>
      `;

      marker.bindPopup(popupContent);
    });

    // Fit map to show all markers
    if (locations.length > 1) {
      const group = new L.featureGroup(locations.map(loc => 
        L.marker([loc.latitude, loc.longitude])
      ));
      map.fitBounds(group.getBounds().pad(0.1));
    } else if (locations.length === 1) {
      map.setView([locations[0].latitude, locations[0].longitude], 15);
    }

    // Cleanup function
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [locations]);

  // Update map when locations change
  useEffect(() => {
    if (mapInstanceRef.current && locations.length > 0) {
      // Clear existing markers
      mapInstanceRef.current.eachLayer((layer) => {
        if (layer instanceof L.Marker) {
          mapInstanceRef.current?.removeLayer(layer);
        }
      });

      // Add new markers
      locations.forEach((location, index) => {
        const marker = L.marker([location.latitude, location.longitude], {
          icon: createCustomIcon(index === 0 ? '#EF4444' : '#3B82F6')
        }).addTo(mapInstanceRef.current!);

        const popupContent = `
          <div style="min-width: 200px;">
            <h3 style="margin: 0 0 8px 0; font-weight: bold; color: #1F2937;">${location.name}</h3>
            <p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">${location.address}</p>
            ${location.phone ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">📞 ${location.phone}</p>` : ''}
            ${location.website ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">🌐 <a href="${location.website}" target="_blank" style="color: #3B82F6;">Visit Website</a></p>` : ''}
            ${location.rating ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">⭐ ${location.rating}/5</p>` : ''}
            ${location.businessType ? `<p style="margin: 0 0 6px 0; color: #6B7280; font-size: 14px;">🏢 ${location.businessType}</p>` : ''}
            ${location.mapsUrl ? `<p style="margin: 0 0 0 0; color: #6B7280; font-size: 14px;">🗺️ <a href="${location.mapsUrl}" target="_blank" style="color: #3B82F6;">View on Google Maps</a></p>` : ''}
          </div>
        `;

        marker.bindPopup(popupContent);
      });

      // Fit map to show all markers
      if (locations.length > 1) {
        const group = new L.featureGroup(locations.map(loc => 
          L.marker([loc.latitude, loc.longitude])
        ));
        mapInstanceRef.current.fitBounds(group.getBounds().pad(0.1));
      } else if (locations.length === 1) {
        mapInstanceRef.current.setView([locations[0].latitude, locations[0].longitude], 15);
      }
    }
  }, [locations]);

  return (
    <div 
      ref={mapRef} 
      className="w-full h-full"
      style={{ minHeight: '400px' }}
    />
  );
}
