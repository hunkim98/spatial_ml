import * as pdfjs from "pdfjs-dist";

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export enum MapMediaType {
  IMAGE = "IMAGE",
  PDF = "PDF",
}

export enum DrawMode {
  NONE = "NONE",
  CREATE = "CREATE",
  MOVE = "MOVE",
  RESIZE = "RESIZE",
  ROTATE = "ROTATE",
}

export class MapMediaCanvas {
  _type: MapMediaType;
  _resourceUrl: string;
  _canvas: HTMLCanvasElement;
  _pageNumber: number;
  _drawMode: DrawMode;

  // Offscreen buffer - loaded once, drawn many times
  private _buffer: HTMLCanvasElement | null = null;
  private _loaded: boolean = false;

  constructor(
    type: MapMediaType,
    resourceUrl: string,
    canvas: HTMLCanvasElement,
    pageNumber: number = 1
  ) {
    this._type = type;
    this._resourceUrl = resourceUrl;
    this._canvas = canvas;
    this._pageNumber = pageNumber;
    this._drawMode = DrawMode.NONE;
  }

  get loaded(): boolean {
    return this._loaded;
  }

  get bufferWidth(): number {
    return this._buffer?.width ?? 0;
  }

  get bufferHeight(): number {
    return this._buffer?.height ?? 0;
  }

  async load(): Promise<void> {
    if (this._type === MapMediaType.IMAGE) {
      await this._loadImage();
    } else if (this._type === MapMediaType.PDF) {
      await this._loadPdf();
    }
    this._loaded = true;
  }

  // Draw the loaded resource at specified position/transform
  draw(x: number, y: number, scale: number = 1, rotation: number = 0): void {
    if (!this._buffer || !this._loaded) return;

    const ctx = this._canvas.getContext("2d");
    if (!ctx) return;

    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((rotation * Math.PI) / 180);
    ctx.scale(scale, scale);
    ctx.drawImage(
      this._buffer,
      -this._buffer.width / 2,
      -this._buffer.height / 2
    );
    ctx.restore();
  }

  // Clear the canvas
  clear(): void {
    const ctx = this._canvas.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, this._canvas.width, this._canvas.height);
    }
  }

  private async _loadImage(): Promise<void> {
    const img = new Image();
    img.crossOrigin = "anonymous";

    return new Promise((resolve, reject) => {
      img.onload = () => {
        // Create offscreen buffer
        this._buffer = document.createElement("canvas");
        this._buffer.width = img.naturalWidth;
        this._buffer.height = img.naturalHeight;

        const ctx = this._buffer.getContext("2d");
        if (!ctx) return reject(new Error("Could not get buffer context"));

        ctx.drawImage(img, 0, 0);
        resolve();
      };
      img.onerror = reject;
      img.src = this._resourceUrl;
    });
  }

  private async _loadPdf(): Promise<void> {
    const pdf = await pdfjs.getDocument(this._resourceUrl).promise;
    const page = await pdf.getPage(this._pageNumber);

    // Render at 2x for crisp display
    const viewport = page.getViewport({ scale: 2 });

    // Create offscreen buffer
    this._buffer = document.createElement("canvas");
    this._buffer.width = viewport.width;
    this._buffer.height = viewport.height;

    const ctx = this._buffer.getContext("2d");
    if (!ctx) throw new Error("Could not get buffer context");

    await page.render({
      canvasContext: ctx,
      viewport,
      canvas: this._buffer,
    }).promise;
  }

  private drawBoundingBox(): void {}

  private onMouseDown(event: MouseEvent): void {}

  private onMouseMove(event: MouseEvent): void {}

  private onMouseUp(event: MouseEvent): void {}
}
