import { useState, useCallback } from "react";
import Map, {
  Marker,
  NavigationControl,
  MapLayerMouseEvent,
} from "react-map-gl/maplibre";
import { Corner } from "@/types/db";
import { SATELLITE_STYLE } from "@/map/config";

const DEFAULT_CENTER: Corner = { lng: -85.8316, lat: 33.6598 }; // Anniston, AL

interface MapEditorComponentProps {
  onMapClick?: (lngLat: Corner) => void;
  style?: React.CSSProperties;
}

export const MapEditorComponent = ({
  onMapClick,
  style,
}: MapEditorComponentProps) => {
  const [viewState, setViewState] = useState({
    longitude: DEFAULT_CENTER.lng,
    latitude: DEFAULT_CENTER.lat,
    zoom: 12,
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
      mapStyle={SATELLITE_STYLE}
      cursor={onMapClick ? "crosshair" : "grab"}
    >
      <NavigationControl position="top-right" />
    </Map>
  );
};
