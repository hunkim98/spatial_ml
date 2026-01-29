/**
 * Configuration and data for Anniston, AL zoning map.
 * Uses real GeoJSON data from data/maps.
 */

export interface ZoneInfo {
  code: string;
  name: string;
  color: string;
  description: string;
}

export const ANNISTON_CENTER = {
  lng: -85.8316,
  lat: 33.6598,
};

export const ANNISTON_BOUNDS: [number, number, number, number] = [
  -85.88, 33.60, -85.75, 33.75
];

// PDF info for the zoning map
export const ANNISTON_PDF = {
  path: "AL/anniston/pdf/2024-Zoning-Map.pdf",
  url: "/api/pdf/AL/anniston/pdf/2024-Zoning-Map.pdf",
};

// GeoJSON API endpoint
export const ANNISTON_GEOJSON_URL = "/api/geojson/AL/anniston/geojson/Anniston_Zoning.json";

// Zone types matching the real GeoJSON Zone_2024 field format
export const ZONE_TYPES: Record<string, ZoneInfo> = {
  "C: Urban Core": {
    code: "C",
    name: "Urban Core",
    color: "#E53935",
    description: "Historic downtown commercial area promoting walkability and mixed uses",
  },
  "UC1: Urban Center 1": {
    code: "UC1",
    name: "Urban Center 1",
    color: "#F4511E",
    description: "Walkable mix of uses adjacent to Urban Core",
  },
  "UC2: Urban Center 2": {
    code: "UC2",
    name: "Urban Center 2",
    color: "#FF7043",
    description: "Small mixed-use centers serving urban neighborhoods",
  },
  "UN1: Urban Neighborhood 1": {
    code: "UN1",
    name: "Urban Neighborhood 1",
    color: "#FFCA28",
    description: "Mixed residential with small-lot single-family and some multifamily",
  },
  "UN2: Urban Neighborhood 2": {
    code: "UN2",
    name: "Urban Neighborhood 2",
    color: "#FFE082",
    description: "Transitional neighborhood with larger lots than UN1",
  },
  "SN1: Suburban Neighborhood 1": {
    code: "SN1",
    name: "Suburban Neighborhood 1",
    color: "#81C784",
    description: "Single-family homes on varying lot sizes with some multifamily",
  },
  "SN2: Suburban Neighborhood 2": {
    code: "SN2",
    name: "Suburban Neighborhood 2",
    color: "#A5D6A7",
    description: "Primarily single-family homes with little multifamily",
  },
  "SNC: Suburban Neighborhood Center": {
    code: "SNC",
    name: "Suburban Neighborhood Center",
    color: "#4DB6AC",
    description: "Small mixed-use centers serving surrounding neighborhoods",
  },
  "SC: Suburban Corridor": {
    code: "SC",
    name: "Suburban Corridor",
    color: "#7986CB",
    description: "Single-use commercial development along corridors",
  },
  "SE: Suburban Edge": {
    code: "SE",
    name: "Suburban Edge",
    color: "#C5E1A5",
    description: "Large lots (1+ acre) with scattered residential",
  },
  "MI: Major Institution/Civic Campus": {
    code: "MI",
    name: "Major Institution",
    color: "#9575CD",
    description: "Educational campuses, hospitals, parks, cemeteries",
  },
  "MI: Major UC2: Urban Center 2": {
    code: "MI/UC2",
    name: "Major Institution / Urban Center 2",
    color: "#B39DDB",
    description: "Mixed institutional and urban center",
  },
  "IL: Industrial Limited": {
    code: "IL",
    name: "Industrial Limited",
    color: "#90A4AE",
    description: "Light industrial, clean manufacturing, warehousing",
  },
  "IG: Industrial General": {
    code: "IG",
    name: "Industrial General",
    color: "#78909C",
    description: "Large footprint buildings for industrial development",
  },
  "NO: Natural/Open Space": {
    code: "NO",
    name: "Natural & Open Space",
    color: "#2E7D32",
    description: "Areas intended to remain in natural state",
  },
};

// Helper to get zone info by Zone_2024 value
export function getZoneInfo(zone2024: string): ZoneInfo | null {
  return ZONE_TYPES[zone2024] || null;
}

// Helper to extract zone code from Zone_2024 format
export function getZoneCode(zone2024: string): string {
  if (!zone2024) return "";
  const match = zone2024.match(/^([A-Z0-9]+):/);
  return match ? match[1] : zone2024;
}

// Workflow steps
export const WORKFLOW_STEPS = [
  {
    step: 1,
    title: "Upload Document",
    description: "Zoning map PDF uploaded",
    status: "completed" as const,
  },
  {
    step: 2,
    title: "Georeference",
    description: "Aligned with satellite imagery",
    status: "completed" as const,
  },
  {
    step: 3,
    title: "Extract Polygons",
    description: "Zoning boundaries extracted",
    status: "completed" as const,
  },
  {
    step: 4,
    title: "Review & Edit",
    description: "Quality review in progress",
    status: "current" as const,
  },
  {
    step: 5,
    title: "Export",
    description: "Export as GeoJSON or Shapefile",
    status: "pending" as const,
  },
];
