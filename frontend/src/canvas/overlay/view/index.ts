import { FrameLayerView } from "./frameLayerView";
import { ImageLayerView } from "./imageLayerView";
import { PolygonLayerView } from "./polygonLayerView";

export type CanvasView = {
  frameLayerView: FrameLayerView;
  imageLayerView: ImageLayerView;
  polygonLayerView: PolygonLayerView;
};
