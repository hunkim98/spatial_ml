import { IModel } from "./base";

export class CanvasElementModel extends IModel<CanvasElementModel> {
  htmlCanvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;
  width: number;
  height: number;
  dpr: number;

  constructor({
    htmlCanvas,
    width,
    height,
    dpr = 1,
  }: {
    htmlCanvas: HTMLCanvasElement;
    width: number;
    height: number;
    dpr?: number;
  }) {
    super();
    this.htmlCanvas = htmlCanvas;
    this.ctx = htmlCanvas.getContext("2d")!;
    this.width = width;
    this.height = height;
    this.dpr = dpr;
  }

  reset() {
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.clearRect(0, 0, this.htmlCanvas.width, this.htmlCanvas.height);
  }
}
