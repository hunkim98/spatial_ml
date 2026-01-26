import { useState, useCallback } from "react";
import Map, { Marker, NavigationControl, MapLayerMouseEvent } from "react-map-gl/maplibre";
import { Corner } from "@/types/db";

interface MarkerData {
  id: string;
  position: Corner;
  color: string;
}

interface GeoMapProps {
  markers?: MarkerData[];
  onMapClick?: (lngLat: Corner) => void;
  initialCenter?: Corner;
  initialZoom?: number;
  style?: React.CSSProperties;
}

const DEFAULT_CENTER: Corner = { lng: -71.0589, lat: 42.3601 }; // Boston

export function GeoMap({
  markers = [],
  onMapClick,
  initialCenter = DEFAULT_CENTER,
  initialZoom = 12,
  style,
}: GeoMapProps) {
  const [viewState, setViewState] = useState({
    longitude: initialCenter.lng,
    latitude: initialCenter.lat,
    zoom: initialZoom,
  });

  const handleClick = useCallback(
    (event: MapLayerMouseEvent) => {
      if (onMapClick) {
        onMapClick({ lng: event.lngLat.lng, lat: event.lngLat.lat });
      }
    },
    [onMapClick]
  );

  return (
    <Map
      {...viewState}
      onMove={(evt) => setViewState(evt.viewState)}
      onClick={handleClick}
      style={{ width: "100%", height: "100%", ...style }}
      mapStyle="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
      cursor={onMapClick ? "crosshair" : "grab"}
    >
      <NavigationControl position="top-right" />

      {markers.map((marker) => (
        <Marker
          key={marker.id}
          longitude={marker.position.lng}
          latitude={marker.position.lat}
          anchor="center"
        >
          <div
            style={{
              width: 16,
              height: 16,
              borderRadius: "50%",
              backgroundColor: marker.color,
              border: "2px solid white",
              boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
            }}
          />
        </Marker>
      ))}
    </Map>
  );
}
