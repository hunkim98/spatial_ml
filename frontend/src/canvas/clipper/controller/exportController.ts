import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEventListeners } from "../events";

type Models = Pick<ClipperModel, "clipRectToolModel" | "imageModel">;
type Views = never;

export interface ExportResult {
  buffer: HTMLCanvasElement;
  width: number;
  height: number;
  clipRect: { x: number; y: number; width: number; height: number };
}

export interface ExportParams {
  // No format/quality needed - we return raw canvas buffer
}

/**
 * ExportController - Handles exporting the clipped region as an image
 * Following MVC pattern: reads from models, performs export logic
 */
export class ExportController extends BaseController<
  Models,
  Views,
  ExportParams
> {
  constructor(
    models: ClipperModel,
    views: ClipperView,
    listeners: ClipperEventListeners
  ) {
    super(models, views, listeners);
  }

  /**
   * Export the clipped region as a canvas buffer
   * Returns raw canvas buffer for direct use in overlay editor
   * @param params - Export parameters (currently unused)
   * @returns Export result with canvas buffer and metadata, or null if nothing to export
   */
  execute(params: ExportParams = {}): ExportResult | null {
    const { rect } = this.models.clipRectToolModel;
    const { image } = this.models.imageModel;

    if (!image || !rect) {
      console.warn("No image or clip rect to export");
      return null;
    }

    // Create canvas buffer for clipped region
    const buffer = document.createElement("canvas");
    buffer.width = rect.width;
    buffer.height = rect.height;
    const ctx = buffer.getContext("2d");

    if (!ctx) {
      console.error("Could not get canvas context");
      return null;
    }

    // Draw the clipped portion
    ctx.drawImage(
      image,
      rect.offset.x, // source x
      rect.offset.y, // source y
      rect.width, // source width
      rect.height, // source height
      0, // dest x
      0, // dest y
      rect.width, // dest width
      rect.height // dest height
    );

    return {
      buffer,
      width: rect.width,
      height: rect.height,
      clipRect: {
        x: rect.offset.x,
        y: rect.offset.y,
        width: rect.width,
        height: rect.height,
      },
    };
  }
}
