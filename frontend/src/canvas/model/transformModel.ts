import { IModel } from "./base";
import { Point, GeoCorners, ScreenCorners, HandleType } from "../types";

export class TransformModel extends IModel<TransformModel> {
  // Screen-space corners (during editing)
  corners: ScreenCorners | null = null;

  // Geo corners (synced with MapLibre)
  geoCorners: GeoCorners | null = null;

  // Interaction state
  activeHandle: HandleType = HandleType.NONE;
  dragStart: Point | null = null;
  cornersAtDragStart: ScreenCorners | null = null;

  reset() {
    this.corners = null;
    this.geoCorners = null;
    this.activeHandle = HandleType.NONE;
    this.dragStart = null;
    this.cornersAtDragStart = null;
  }
}
