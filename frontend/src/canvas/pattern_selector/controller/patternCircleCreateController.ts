import {
  PatternSelectorEvent,
  PatternSelectorEventListeners,
} from "../events";
import { PatternSelectorModel } from "../model";
import { PatternSelectorView } from "../view";
import { Point } from "../types";
import { BaseController } from "./base";

type Models = Pick<
  PatternSelectorModel,
  "patternCirclesModel" | "imageModel"
>;
type Views = never;

type ExecuteParams = {
  /** The clicked point in image (world) space */
  point: Point;
  /** Maximum radius in image pixels */
  maxRadius?: number;
};

const DEFAULT_MAX_RADIUS = 64;

/**
 * PatternCircleCreateController
 *
 * When the user clicks a point on the image, this controller:
 * 1. Reads the pixel color at the clicked point
 * 2. Expands outward in a circle, checking color similarity
 * 3. Determines the radius where the color stops being similar
 * 4. Creates a PatternCircle with the computed radius
 */
export class PatternCircleCreateController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    const { point, maxRadius = DEFAULT_MAX_RADIUS } = params;
    const { image, width, height } = this.models.imageModel;
    if (!image || !width || !height) return;

    // Clamp point to image bounds
    const cx = Math.round(Math.max(0, Math.min(width - 1, point.x)));
    const cy = Math.round(Math.max(0, Math.min(height - 1, point.y)));

    // Get pixel data from the image
    const offscreen = document.createElement("canvas");
    offscreen.width = width;
    offscreen.height = height;
    const ctx = offscreen.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(image, 0, 0);

    const centerPixel = ctx.getImageData(cx, cy, 1, 1).data;
    const color: [number, number, number] = [
      centerPixel[0],
      centerPixel[1],
      centerPixel[2],
    ];

    const radius = this.computeColorRadius(
      ctx, cx, cy, width, height, maxRadius, color
    );

    const id = `pattern_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const hexName = this.rgbToHex(color);

    this.models.patternCirclesModel.addCircle({
      id,
      name: hexName,
      color,
      center: { x: cx, y: cy },
      radius: Math.max(radius, 8), // minimum 8px radius
    });

    this.dispatchEvent(PatternSelectorEvent.PATTERN_ADDED);
  }

  /**
   * Compute the radius by expanding outward from the center pixel,
   * checking how far the center color extends.
   *
   * Algorithm: Sample pixels along radial lines at increasing radii.
   * At each radius, check a ring of sample points. If more than half
   * of the samples differ significantly from the center color, stop.
   */
  private rgbToHex(color: [number, number, number]): string {
    return (
      "#" +
      color.map((c) => c.toString(16).padStart(2, "0")).join("").toUpperCase()
    );
  }

  private computeColorRadius(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    imgWidth: number,
    imgHeight: number,
    maxRadius: number,
    centerColor: [number, number, number]
  ): number {
    const [centerR, centerG, centerB] = centerColor;

    const COLOR_THRESHOLD = 25; // max RGB distance to be considered "similar"
    const LINE_DARKNESS_THRESHOLD = 80; // pixels darker than this (luminance) are likely boundary lines
    const SAMPLE_POINTS = 24; // more samples per ring for better line detection
    const DISSIMILAR_RATIO = 0.25; // stop when even 25% of ring is dissimilar (stricter)
    const LINE_HIT_RATIO = 0.1; // stop if any ~10% of ring hits a dark line

    for (let r = 4; r <= maxRadius; r += 2) {
      let dissimilarCount = 0;
      let lineHitCount = 0;
      let validSamples = 0;

      for (let i = 0; i < SAMPLE_POINTS; i++) {
        const angle = (2 * Math.PI * i) / SAMPLE_POINTS;
        const sx = Math.round(cx + r * Math.cos(angle));
        const sy = Math.round(cy + r * Math.sin(angle));

        // Skip out-of-bounds samples
        if (sx < 0 || sx >= imgWidth || sy < 0 || sy >= imgHeight) {
          dissimilarCount++;
          validSamples++;
          continue;
        }

        const pixel = ctx.getImageData(sx, sy, 1, 1).data;
        const pr = pixel[0], pg = pixel[1], pb = pixel[2];

        // Check for dark boundary lines (low luminance)
        const luminance = 0.299 * pr + 0.587 * pg + 0.114 * pb;
        if (luminance < LINE_DARKNESS_THRESHOLD) {
          lineHitCount++;
        }

        const dr = Math.abs(pr - centerR);
        const dg = Math.abs(pg - centerG);
        const db = Math.abs(pb - centerB);
        const dist = Math.max(dr, dg, db); // Chebyshev distance

        validSamples++;
        if (dist > COLOR_THRESHOLD) {
          dissimilarCount++;
        }
      }

      if (validSamples === 0) continue;

      // Stop if enough samples are dissimilar
      if (dissimilarCount / validSamples >= DISSIMILAR_RATIO) {
        return r;
      }

      // Stop if we hit dark boundary lines
      if (lineHitCount / validSamples >= LINE_HIT_RATIO) {
        return r;
      }
    }

    return maxRadius;
  }
}
