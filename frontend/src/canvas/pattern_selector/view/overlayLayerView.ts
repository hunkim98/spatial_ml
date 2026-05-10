import { PatternSelectorModel } from "../model";
import { getCanvasRelativePositionFromWorldPoint } from "../utils/project";
import { IView } from "./base";

const PATTERN_COLORS = [
  "#FF6B6B",
  "#4ECDC4",
  "#45B7D1",
  "#96CEB4",
  "#FFEAA7",
  "#DDA0DD",
  "#98D8C8",
  "#F7DC6F",
  "#BB8FCE",
  "#85C1E9",
];

const STROKE_WIDTH = 2;
const STROKE_WIDTH_HOVER = 3;

type Models = Pick<
  PatternSelectorModel,
  | "overlayLayerModel"
  | "patternCirclesModel"
  | "navigationModel"
  | "toolManagerModel"
>;

export class OverlayLayerView extends IView<Models> {
  constructor(models: PatternSelectorModel) {
    super(models);
  }

  scale(dpr: number) {
    this.models.overlayLayerModel.ctx.scale(dpr, dpr);
  }

  render(): void {
    this.clear();

    const { ctx } = this.models.overlayLayerModel;
    const { offset, scale } = this.models.navigationModel;
    const { circles, isCreating, creatingCenter, creatingRadius } =
      this.models.patternCirclesModel;
    const { candidateCircleId, activeCircleId } = this.models.toolManagerModel;
    const highlightedId = activeCircleId ?? candidateCircleId;

    ctx.save();

    // Draw existing pattern circles
    circles.forEach((circle, i) => {
      const color = PATTERN_COLORS[i % PATTERN_COLORS.length];
      const isHighlighted = circle.id === highlightedId;
      const screenCenter = getCanvasRelativePositionFromWorldPoint(
        circle.center,
        offset,
        scale
      );
      const screenRadius = circle.radius * scale;

      // Fill
      ctx.beginPath();
      ctx.arc(screenCenter.x, screenCenter.y, screenRadius, 0, Math.PI * 2);
      ctx.fillStyle = color + (isHighlighted ? "44" : "22");
      ctx.fill();

      // Stroke
      ctx.strokeStyle = color;
      ctx.lineWidth = isHighlighted ? STROKE_WIDTH_HOVER : STROKE_WIDTH;
      ctx.stroke();

      // Inscribed square preview (dashed)
      const halfSide = (circle.radius * Math.SQRT1_2) * scale;
      ctx.strokeStyle = color + "66";
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.strokeRect(
        screenCenter.x - halfSide,
        screenCenter.y - halfSide,
        halfSide * 2,
        halfSide * 2
      );
      ctx.setLineDash([]);

      // Label
      ctx.fillStyle = color;
      ctx.font = "bold 12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(
        circle.name,
        screenCenter.x,
        screenCenter.y - screenRadius - 6
      );
    });

    // Draw creating circle (in-progress)
    if (isCreating && creatingCenter) {
      const screenCenter = getCanvasRelativePositionFromWorldPoint(
        creatingCenter,
        offset,
        scale
      );
      const screenRadius = creatingRadius * scale;

      ctx.beginPath();
      ctx.arc(screenCenter.x, screenCenter.y, screenRadius, 0, Math.PI * 2);
      ctx.strokeStyle = "#6D96FF";
      ctx.lineWidth = STROKE_WIDTH;
      ctx.setLineDash([5, 5]);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = "#6D96FF33";
      ctx.fill();
    }

    ctx.restore();
  }

  clear(): void {
    const { element, ctx } = this.models.overlayLayerModel;
    if (!element || !ctx) return;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
