import { CanvasModel } from "../model";
import { IView } from "./base";
import { ProjectedFeature } from "../model/tools/geojsonEditModel";

// Same palette as MapEditorComponent for consistency
const ZONE_COLORS = [
  "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
  "#911eb4", "#42d4f4", "#f032e6", "#bfef45", "#fabed4",
  "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3",
  "#808000", "#ffd8b1", "#000075", "#a9a9a9",
];

const VERTEX_RADIUS = 5;
const VERTEX_RADIUS_ACTIVE = 7;
const VERTEX_RADIUS_CANDIDATE = 6;
const SELECTION_STROKE_WIDTH = 3;
const SELECTION_DASH = [6, 3];

type Models = Pick<CanvasModel, "frameLayerModel" | "geojsonEditModel">;

/**
 * PolygonLayerView — renders selection highlight + vertex handles on the frame canvas.
 * MapLibre renders the actual polygon fills/strokes; this view only draws the
 * interactive editing overlay on top.
 */
export class PolygonLayerView extends IView<Models> {
  private zoneColorMap: Record<string, string> = {};

  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const {
      featureCollection,
      projectedFeatures,
      selectedFeatureIndex,
    } = this.models.geojsonEditModel;
    if (!featureCollection || projectedFeatures.length === 0) return;

    const ctx = this.models.frameLayerModel.ctx;
    ctx.save();

    this.buildColorMap(featureCollection);

    // Only draw overlay for the selected polygon
    if (selectedFeatureIndex !== null) {
      const projected = projectedFeatures[selectedFeatureIndex];
      if (projected && projected.rings.length > 0) {
        const feature = featureCollection.features[selectedFeatureIndex];
        const zoneName = (feature?.properties?.zone as string) ?? "";
        const color = this.zoneColorMap[zoneName] ?? "#888";

        this.drawSelectionBorder(ctx, projected, color);
        this.drawVertexHandles(ctx, projected, selectedFeatureIndex);
      }
    }

    ctx.restore();
  }

  private buildColorMap(fc: GeoJSON.FeatureCollection): void {
    const names = new Set<string>();
    for (const f of fc.features) {
      names.add((f.properties?.zone as string) ?? "");
    }
    const sorted = [...names];
    this.zoneColorMap = {};
    sorted.forEach((name, i) => {
      this.zoneColorMap[name] = ZONE_COLORS[i % ZONE_COLORS.length];
    });
  }

  private drawSelectionBorder(
    ctx: CanvasRenderingContext2D,
    projected: ProjectedFeature,
    color: string
  ): void {
    ctx.beginPath();

    for (const ring of projected.rings) {
      const pts = ring.points;
      if (pts.length === 0) continue;

      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) {
        ctx.lineTo(pts[i].x, pts[i].y);
      }
      ctx.closePath();
    }

    ctx.globalAlpha = 1;
    ctx.strokeStyle = color;
    ctx.lineWidth = SELECTION_STROKE_WIDTH;
    ctx.setLineDash(SELECTION_DASH);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  private drawVertexHandles(
    ctx: CanvasRenderingContext2D,
    projected: ProjectedFeature,
    featureIndex: number
  ): void {
    const { activeVertex, candidateVertex } = this.models.geojsonEditModel;

    for (let ri = 0; ri < projected.rings.length; ri++) {
      const pts = projected.rings[ri].points;
      for (let vi = 0; vi < pts.length; vi++) {
        const pt = pts[vi];

        const isActive =
          activeVertex !== null &&
          activeVertex.featureIndex === featureIndex &&
          activeVertex.ringIndex === ri &&
          activeVertex.vertexIndex === vi;

        const isCandidate =
          !isActive &&
          candidateVertex !== null &&
          candidateVertex.featureIndex === featureIndex &&
          candidateVertex.ringIndex === ri &&
          candidateVertex.vertexIndex === vi;

        let radius = VERTEX_RADIUS;
        let fillColor = "#FFFFFF";
        let strokeColor = "#6D96FF";

        if (isActive) {
          radius = VERTEX_RADIUS_ACTIVE;
          fillColor = "#FF6D6D";
          strokeColor = "#CC0000";
        } else if (isCandidate) {
          radius = VERTEX_RADIUS_CANDIDATE;
          fillColor = "#E0E8FF";
          strokeColor = "#4363d8";
        }

        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }

  scale(dpr: number): void {
    this.models.frameLayerModel.ctx.scale(dpr, dpr);
  }

  clear(): void {
    // Polygon view shares the frame canvas — clearing is done centrally
    // in the editor's render() cycle. No-op here to avoid double-clear.
  }
}
