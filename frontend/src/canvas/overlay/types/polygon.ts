/**
 * Reference to a specific vertex within a GeoJSON FeatureCollection.
 *
 * Maps to: featureCollection.features[featureIndex].geometry.coordinates[ringIndex][vertexIndex]
 */
export interface VertexRef {
  featureIndex: number;
  ringIndex: number; // 0 = exterior ring, 1+ = holes
  vertexIndex: number;
}

/**
 * Reference to a specific edge (line segment between two adjacent vertices).
 *
 * The edge runs from vertex[segmentIndex] to vertex[segmentIndex + 1].
 */
export interface EdgeRef {
  featureIndex: number;
  ringIndex: number;
  segmentIndex: number;
}
