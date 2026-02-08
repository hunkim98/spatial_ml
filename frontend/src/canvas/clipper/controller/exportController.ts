import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEventListeners } from "../events";

type Models = Pick<ClipperModel, "clipRectToolModel" | "imageModel">;
type Views = never;

export interface ExportResult {
  blob: Blob;
  blobUrl: string;
  width: number;
  height: number;
  clipRect: { x: number; y: number; width: number; height: number };
}

export interface ExportParams {
  format?: "png" | "jpeg";
  quality?: number; // 0-1, for jpeg only
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
   * Export the clipped region as a high-quality image
   * @param params - Export parameters (format, quality)
   * @returns Export result with blob and metadata, or null if nothing to export
   */
  async execute(params: ExportParams = {}): Promise<ExportResult | null> {
    const { format = "png", quality = 0.95 } = params;

    const { rect } = this.models.clipRectToolModel;
    const { image } = this.models.imageModel;

    if (!image || !rect) {
      console.warn("No image or clip rect to export");
      return null;
    }

    // Create temporary canvas for clipped region
    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = rect.width;
    tempCanvas.height = rect.height;
    const ctx = tempCanvas.getContext("2d");

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

    // Convert to blob
    const mimeType = format === "png" ? "image/png" : "image/jpeg";
    const blob = await new Promise<Blob>((resolve, reject) => {
      tempCanvas.toBlob(
        (b) => {
          if (b) resolve(b);
          else reject(new Error("Failed to create blob"));
        },
        mimeType,
        quality
      );
    });

    const blobUrl = URL.createObjectURL(blob);

    return {
      blob,
      blobUrl,
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
