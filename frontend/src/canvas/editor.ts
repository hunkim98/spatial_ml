import { CanvasModel } from "./model";
import { CanvasController } from "./controller";
import { CanvasView } from "./view";
import { CanvasEvent, CanvasEventListeners } from "./events";
import { MapMediaType, HandleType, EditorMode, Point } from "./types";

// Models
import { CanvasElementModel } from "./model/canvasElementModel";
import { MouseControlModel } from "./model/mouseControlModel";
import { EditorStateModel } from "./model/editorStateModel";
import { TransformModel } from "./model/transformModel";
import { ImageBufferModel } from "./model/imageBufferModel";

// Views
import { ImageLayerView } from "./view/imageLayerView";
import { FrameLayerView } from "./view/frameLayerView";

// Controllers
import { HitTestController } from "./controller/hitTestController";
import { ModeController } from "./controller/modeController";
import { ImageCreateController } from "./controller/imageCreateController";
import { ImageMoveController } from "./controller/imageMoveController";
import { ImageResizeController } from "./controller/imageResizeController";
import { ImageRotateController } from "./controller/imageRotateController";

// pdfjs-dist is loaded dynamically to avoid SSR issues
let pdfjs: typeof import("pdfjs-dist") | null = null;

async function getPdfjs() {
  if (!pdfjs) {
    pdfjs = await import("pdfjs-dist");
    pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  }
  return pdfjs;
}

export class Editor {
  private _type: MapMediaType;
  private _resourceUrl: string;
  private _pageNumber: number;

  private models: CanvasModel;
  private views: CanvasView;
  private controllers: CanvasController;
  private listeners: CanvasEventListeners;

  constructor(
    type: MapMediaType,
    resourceUrl: string,
    canvas: HTMLCanvasElement,
    pageNumber: number = 1
  ) {
    this._type = type;
    this._resourceUrl = resourceUrl;
    this._pageNumber = pageNumber;

    this.listeners = {};
    this.models = this._createModels(canvas);
    this.views = this._createViews();
    this.controllers = this._createControllers();
  }

  private _createModels(canvas: HTMLCanvasElement): CanvasModel {
    return {
      canvasElementModel: new CanvasElementModel({
        htmlCanvas: canvas,
        width: canvas.width,
        height: canvas.height,
      }),
      mouseControlModel: new MouseControlModel(),
      editorStateModel: new EditorStateModel(),
      transformModel: new TransformModel(),
      imageBufferModel: new ImageBufferModel(),
    };
  }

  private _createViews(): CanvasView {
    return {
      frameLayerView: new FrameLayerView(this.models),
      imageLayerView: new ImageLayerView(this.models),
    };
  }

  private _createControllers(): CanvasController {
    return {
      hitTestController: new HitTestController(
        this.models,
        this.views,
        this.listeners
      ),
      modeController: new ModeController(
        this.models,
        this.views,
        this.listeners
      ),
      imageCreateController: new ImageCreateController(
        this.models,
        this.views,
        this.listeners
      ),
      imageMoveController: new ImageMoveController(
        this.models,
        this.views,
        this.listeners
      ),
      imageResizeController: new ImageResizeController(
        this.models,
        this.views,
        this.listeners
      ),
      imageRotateController: new ImageRotateController(
        this.models,
        this.views,
        this.listeners
      ),
    };
  }

  async load(): Promise<void> {
    if (this._type === MapMediaType.PDF) {
      await this._loadPdf();
    } else {
      await this._loadImage();
    }
    this.models.editorStateModel.isLoaded = true;
  }

  private async _loadPdf(): Promise<void> {
    const pdfjsLib = await getPdfjs();
    const pdf = await pdfjsLib.getDocument(this._resourceUrl).promise;
    const page = await pdf.getPage(this._pageNumber);
    const viewport = page.getViewport({ scale: 2 });

    const buffer = document.createElement("canvas");

    buffer.width = viewport.width;
    buffer.height = viewport.height;

    const ctx = buffer.getContext("2d");

    if (!ctx) throw new Error("Could not get buffer context");

    await page.render({
      canvasContext: ctx,
      viewport,
      canvas: buffer,
    }).promise;

    this.models.imageBufferModel.buffer = buffer;
    this.models.imageBufferModel.width = viewport.width;
    this.models.imageBufferModel.height = viewport.height;
  }

  private async _loadImage(): Promise<void> {
    return new Promise((resolve, reject) => {
      const img = new Image();

      img.crossOrigin = "anonymous";
      img.onload = () => {
        const buffer = document.createElement("canvas");

        buffer.width = img.naturalWidth;
        buffer.height = img.naturalHeight;

        const ctx = buffer.getContext("2d");

        if (!ctx) return reject(new Error("Could not get buffer context"));

        ctx.drawImage(img, 0, 0);

        this.models.imageBufferModel.buffer = buffer;
        this.models.imageBufferModel.width = img.naturalWidth;
        this.models.imageBufferModel.height = img.naturalHeight;

        resolve();
      };
      img.onerror = reject;
      img.src = this._resourceUrl;
    });
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>): boolean {
    const point = this._getPoint(e);
    const mode = this.models.editorStateModel.mode;

    switch (mode) {
      case EditorMode.CREATE: {
        if (!this.models.editorStateModel.isLoaded) {
          return false;
        }
        this.models.mouseControlModel.isDown = true;
        this.controllers.imageCreateController.execute({ type: "start", point });
        return true;
      }

      case EditorMode.VIEW: {
        const handle = this.controllers.hitTestController.execute(point);
        if (handle === HandleType.NONE) {
          return false;
        }
        this.controllers.modeController.execute(EditorMode.EDIT);
        this.models.mouseControlModel.isDown = true;
        this.models.transformModel.activeHandle = handle;
        this._startTransform(handle, point);
        return true;
      }

      case EditorMode.EDIT: {
        const handle = this.controllers.hitTestController.execute(point);
        if (handle === HandleType.NONE) {
          this.controllers.modeController.execute(EditorMode.VIEW);
          return false;
        }
        this.models.mouseControlModel.isDown = true;
        this.models.transformModel.activeHandle = handle;
        this._startTransform(handle, point);
        return true;
      }

      default:
        return false;
    }
  }

  private _startTransform(handle: HandleType, point: Point): void {
    if (handle === HandleType.BODY) {
      this.controllers.imageMoveController.execute({ type: "start", point });
    } else {
      this.controllers.imageResizeController.execute({ type: "start", point, handle });
    }
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.mouseControlModel.isDown) return;

    const point = this._getPoint(e);
    const mode = this.models.editorStateModel.mode;

    switch (mode) {
      case EditorMode.CREATE: {
        this.controllers.imageCreateController.execute({ type: "move", point });
        this.render();
        break;
      }

      case EditorMode.VIEW:
      case EditorMode.EDIT: {
        const handle = this.models.transformModel.activeHandle;
        if (handle === HandleType.BODY) {
          this.controllers.imageMoveController.execute({ type: "move", point });
        } else if (handle !== HandleType.NONE) {
          this.controllers.imageResizeController.execute({ type: "move", point, handle });
        }
        this.render();
        break;
      }
    }
  }

  onMouseUp(): void {
    if (!this.models.mouseControlModel.isDown) return;

    const mode = this.models.editorStateModel.mode;

    switch (mode) {
      case EditorMode.CREATE: {
        this.controllers.imageCreateController.execute({ type: "end", point: { x: 0, y: 0 } });
        this.models.editorStateModel.isInitialized = true;
        this.controllers.modeController.execute(EditorMode.EDIT);
        break;
      }

      case EditorMode.VIEW:
      case EditorMode.EDIT: {
        const handle = this.models.transformModel.activeHandle;
        if (handle === HandleType.BODY) {
          this.controllers.imageMoveController.execute({ type: "end", point: { x: 0, y: 0 } });
        } else if (handle !== HandleType.NONE) {
          this.controllers.imageResizeController.execute({ type: "end", point: { x: 0, y: 0 }, handle });
        }
        break;
      }
    }

    this.models.mouseControlModel.isDown = false;
  }

  render(): void {
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.render();
  }

  private _getPoint(e: React.MouseEvent<HTMLCanvasElement>): Point {
    const rect = this.models.canvasElementModel.htmlCanvas.getBoundingClientRect();

    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  getCursor(e: React.MouseEvent<HTMLCanvasElement>): string {
    const mode = this.models.editorStateModel.mode;

    // CREATE mode: always crosshair
    if (mode === EditorMode.CREATE) {
      return "crosshair";
    }

    // VIEW mode: default cursor (let map handle it)
    if (mode === EditorMode.VIEW) {
      return "default";
    }

    // EDIT mode: cursor based on what's under the mouse
    if (mode === EditorMode.EDIT) {
      // If dragging, use the cursor for the active handle
      if (this.models.mouseControlModel.isDown) {
        return this._getCursorForHandle(this.models.transformModel.activeHandle);
      }

      // Otherwise, check what's under the cursor
      const point = this._getPoint(e);
      const handle = this.controllers.hitTestController.execute(point);
      return this._getCursorForHandle(handle);
    }

    return "default";
  }

  private _getCursorForHandle(handle: HandleType): string {
    switch (handle) {
      case HandleType.BODY:
        return "move";
      case HandleType.TOP_LEFT:
      case HandleType.BOTTOM_RIGHT:
        return "nwse-resize";
      case HandleType.TOP_RIGHT:
      case HandleType.BOTTOM_LEFT:
        return "nesw-resize";
      default:
        return "default";
    }
  }

  addEventListener(
    type: CanvasEvent,
    listener: (args: Partial<CanvasModel>) => void
  ) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type]!.push(listener);
  }

  removeEventListener(
    type: CanvasEvent,
    listener: (args: Partial<CanvasModel>) => void
  ) {
    if (this.listeners[type]) {
      this.listeners[type] = this.listeners[type]!.filter(
        (l) => l !== listener
      );
      if (this.listeners[type]!.length === 0) {
        delete this.listeners[type];
      }
    }
  }

  clearEventListeners(type: CanvasEvent) {
    delete this.listeners[type];
  }

  // Getters for external access
  get isLoaded(): boolean {
    return this.models.editorStateModel.isLoaded;
  }

  get isInitialized(): boolean {
    return this.models.editorStateModel.isInitialized;
  }

  get mode(): EditorMode {
    return this.models.editorStateModel.mode;
  }

  get corners() {
    return this.models.transformModel.corners;
  }

  get geoCorners() {
    return this.models.transformModel.geoCorners;
  }

  setCorners(corners: typeof this.models.transformModel.corners) {
    this.models.transformModel.corners = corners;
  }

  setGeoCorners(geoCorners: typeof this.models.transformModel.geoCorners) {
    this.models.transformModel.geoCorners = geoCorners;
  }

  /**
   * Initialize the editor with pre-set corners (for embedding with known positions).
   * Sets the editor to EDIT mode and marks as initialized.
   */
  initializeWithCorners(
    screenCorners: typeof this.models.transformModel.corners,
    geoCorners: typeof this.models.transformModel.geoCorners
  ) {
    this.models.transformModel.corners = screenCorners;
    this.models.transformModel.geoCorners = geoCorners;
    this.models.editorStateModel.isInitialized = true;
    this.controllers.modeController.execute(EditorMode.EDIT);
  }

  getImageDataUrl(): string | null {
    const buffer = this.models.imageBufferModel.buffer;
    if (!buffer) return null;

    return buffer.toDataURL("image/png");
  }

  clearCanvas(): void {
    this.views.imageLayerView.clear();
  }

  /**
   * Check if a point (in canvas coordinates) is over the overlay.
   * Used for external hit testing (e.g., document-level mouse tracking).
   */
  hitTest(point: { x: number; y: number }): HandleType {
    return this.controllers.hitTestController.execute(point);
  }
}
