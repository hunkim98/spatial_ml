import {
  useState,
  useCallback,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import Map, {
  NavigationControl,
  MapLayerMouseEvent,
  MapRef,
} from "react-map-gl/maplibre";
import { Corner } from "@/types/db";
import { SATELLITE_STYLE } from "@/map/config";
import { GeoCorners, ScreenCorners } from "@/canvas/overlay/types";

const DEFAULT_CENTER: Corner = { lng: -85.8316, lat: 33.6598 }; // Anniston, AL
const IMAGE_SOURCE_ID = "overlay-image-source";
const IMAGE_LAYER_ID = "overlay-image-layer";

interface MapEditorComponentProps {
  onMapClick?: (lngLat: Corner) => void;
  cursor?: string;
  style?: React.CSSProperties;
}

export interface MapEditorComponentHandle {
  addImageLayer: (
    imageUrl: string,
    corners: GeoCorners,
    opacity?: number
  ) => void;
  preloadImageLayer: (
    imageUrl: string,
    screenCorners: ScreenCorners,
    opacity?: number
  ) => void;
  removeImageLayer: () => void;
  showImageLayer: (opacity?: number) => void;
  hideImageLayer: () => void;
  updateImageLayerCorners: (corners: GeoCorners) => void;
  unprojectScreenCorners: (corners: ScreenCorners) => GeoCorners | null;
  getMapRef: () => MapRef | null;
}

function toMapLibreCoordinates(
  corners: GeoCorners
): [[number, number], [number, number], [number, number], [number, number]] {
  return [
    [corners.corner1.lng, corners.corner1.lat], // top-left
    [corners.corner2.lng, corners.corner2.lat], // top-right
    [corners.corner4.lng, corners.corner4.lat], // bottom-right
    [corners.corner3.lng, corners.corner3.lat], // bottom-left
  ];
}

export const MapEditorComponent = forwardRef<
  MapEditorComponentHandle,
  MapEditorComponentProps
>(function MapEditorComponent({ onMapClick, cursor, style }, ref) {
  const mapRef = useRef<MapRef>(null);
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

  const addImageLayer = useCallback(
    (imageUrl: string, corners: GeoCorners, opacity: number = 0) => {
      const map = mapRef.current?.getMap();
      if (!map) return;

      const add = () => {
        if (map.getLayer(IMAGE_LAYER_ID)) map.removeLayer(IMAGE_LAYER_ID);
        if (map.getSource(IMAGE_SOURCE_ID)) map.removeSource(IMAGE_SOURCE_ID);

        map.addSource(IMAGE_SOURCE_ID, {
          type: "image",
          url: imageUrl,
          coordinates: toMapLibreCoordinates(corners),
        });

        map.addLayer({
          id: IMAGE_LAYER_ID,
          type: "raster",
          source: IMAGE_SOURCE_ID,
          paint: {
            "raster-opacity": opacity,
            "raster-opacity-transition": { duration: 0, delay: 0 },
          },
        });
      };

      if (map.isStyleLoaded()) {
        add();
      } else {
        map.once("load", add);
      }
    },
    []
  );

  const preloadImageLayer = useCallback(
    (imageUrl: string, screenCorners: ScreenCorners, opacity: number = 0) => {
      const map = mapRef.current?.getMap();
      if (!map) return;
      const preload = () => {
        // Unproject screen corners to geo corners (map is loaded at this point)
        const mapInstance = mapRef.current;
        if (!mapInstance) return;
        const toGeo = (p: { x: number; y: number }) => {
          const lngLat = mapInstance.unproject([p.x, p.y]);
          return { lng: lngLat.lng, lat: lngLat.lat };
        };
        const geoCorners: GeoCorners = {
          corner1: toGeo(screenCorners.corner1),
          corner2: toGeo(screenCorners.corner2),
          corner3: toGeo(screenCorners.corner3),
          corner4: toGeo(screenCorners.corner4),
        };

        if (map.getLayer(IMAGE_LAYER_ID)) map.removeLayer(IMAGE_LAYER_ID);
        if (map.getSource(IMAGE_SOURCE_ID)) map.removeSource(IMAGE_SOURCE_ID);

        map.addSource(IMAGE_SOURCE_ID, {
          type: "image",
          url: imageUrl,
          coordinates: toMapLibreCoordinates(geoCorners),
        });

        map.addLayer({
          id: IMAGE_LAYER_ID,
          type: "raster",
          source: IMAGE_SOURCE_ID,
          paint: {
            "raster-opacity": opacity,
            "raster-opacity-transition": { duration: 0, delay: 0 },
          },
        });
      };

      if (map.isStyleLoaded()) {
        preload();
      } else {
        map.once("load", preload);
      }
    },
    []
  );

  const removeImageLayer = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;

    if (map.getLayer(IMAGE_LAYER_ID)) map.removeLayer(IMAGE_LAYER_ID);
    if (map.getSource(IMAGE_SOURCE_ID)) map.removeSource(IMAGE_SOURCE_ID);
  }, []);

  const showImageLayer = useCallback((opacity: number = 0.7) => {
    const map = mapRef.current?.getMap();
    if (!map || !map.getLayer(IMAGE_LAYER_ID)) return;
    map.setPaintProperty(IMAGE_LAYER_ID, "raster-opacity", opacity);
  }, []);

  const hideImageLayer = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map || !map.getLayer(IMAGE_LAYER_ID)) return;
    map.setPaintProperty(IMAGE_LAYER_ID, "raster-opacity", 0);
  }, []);

  const updateImageLayerCorners = useCallback((corners: GeoCorners) => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    const source = map.getSource(IMAGE_SOURCE_ID);
    if (!source) return;
    (source as any).setCoordinates(toMapLibreCoordinates(corners));
  }, []);

  const unprojectScreenCorners = useCallback(
    (corners: ScreenCorners): GeoCorners | null => {
      const map = mapRef.current;
      if (!map) return null;

      const toGeo = (p: { x: number; y: number }) => {
        const lngLat = map.unproject([p.x, p.y]);
        return { lng: lngLat.lng, lat: lngLat.lat };
      };

      return {
        corner1: toGeo(corners.corner1),
        corner2: toGeo(corners.corner2),
        corner3: toGeo(corners.corner3),
        corner4: toGeo(corners.corner4),
      };
    },
    []
  );

  useImperativeHandle(
    ref,
    () => ({
      addImageLayer,
      preloadImageLayer,
      removeImageLayer,
      showImageLayer,
      hideImageLayer,
      updateImageLayerCorners,
      unprojectScreenCorners,
      getMapRef: () => mapRef.current,
    }),
    [
      addImageLayer,
      preloadImageLayer,
      removeImageLayer,
      showImageLayer,
      hideImageLayer,
      updateImageLayerCorners,
      unprojectScreenCorners,
    ]
  );

  return (
    <Map
      ref={mapRef}
      {...viewState}
      onMove={(evt) => setViewState(evt.viewState)}
      onClick={handleClick}
      cursor={cursor}
      style={{ width: "100%", height: "100%", ...style }}
      mapStyle={SATELLITE_STYLE}
      maxPitch={0}
    >
      <NavigationControl position="top-right" />
    </Map>
  );
});
