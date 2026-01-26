import { IModel } from "./base";

export class ImageBufferModel extends IModel<ImageBufferModel> {
  // Offscreen canvas buffer (rendered once)
  buffer: HTMLCanvasElement | null = null;

  // Original dimensions
  width: number = 0;
  height: number = 0;

  reset() {
    this.buffer = null;
    this.width = 0;
    this.height = 0;
  }
}
