import { ClipperModel } from "./model";
import { ClipperController } from "./controller";
import { ClipperView } from "./view";
import { ClipperEvent, ClipperEventListeners } from "./events";
import { HandleType, Point, ClipRect } from "./types";
import { ActionType } from "./actions/base";
import { getPdfPageAsBlob } from "@/lib/pdf";

// Models
import { BackgroundLayerModel } from "./model/layers/backgroundLayerModel";
import { FrameLayerModel } from "./model/layers/frameLayerModel";
import { PdfLayerModel } from "./model/layers/pdfLayerModel";
import { ClipRectToolModel } from "./model/tools/clipRectToolModel";
import { EditorStatusModel } from "./model/editorStatusModel";
import { HistoryModel } from "./model/historyModel";
import { ImageModel } from "./model/imageModel";
import { MouseControlModel } from "./model/mouseControlModel";
import { NavigationModel } from "./model/navigationModel";

// Views
import { PdfLayerView } from "./view/pdfLayerView";
import { MaskLayerView } from "./view/maskLayerView";

// Controllers
import { HitTestController } from "./controller/hitTestController";
import { ImageUpdateController } from "./controller/imageUpdateController";
import { MoveController } from "./controller/moveController";
import { PanZoomController } from "./controller/panZoomController";
import { ResizeController } from "./controller/resizeController";
import { UndoController } from "./controller/undoController";
import { RedoController } from "./controller/redoController";

export class ClipperEditor {
  private _resourceUrl: string;
  private _pageNumber: number;
  private _isPanning: boolean = false;

  private models: ClipperModel;
  private views: ClipperView;
  private controllers: ClipperController;
  private listeners: ClipperEventListeners;

  constructor(
    resourceUrl: string,
    pdfCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    pageNumber: number = 1
  ) {
    this._resourceUrl = resourceUrl;
    this._pageNumber = pageNumber;

    this.listeners = {};
    this.models = this._createModels(pdfCanvas, frameCanvas);
    this.views = this._createViews();
    this.controllers = this._createControllers();
  }

  private _createModels(
    pdfCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement
  ): ClipperModel {
    const dpr = window.devicePixelRatio || 1;

    return {
      backgroundLayerModel: new BackgroundLayerModel({
        width: pdfCanvas.width,
        height: pdfCanvas.height,
        dpr,
        element: pdfCanvas,
      }),
      pdfLayerModel: new PdfLayerModel({
        width: pdfCanvas.width,
        height: pdfCanvas.height,
        dpr,
        element: pdfCanvas,
      }),
      frameLayerModel: new FrameLayerModel({
        width: frameCanvas.width,
        height: frameCanvas.height,
        dpr,
        element: frameCanvas,
      }),
      imageModel: new ImageModel(),
      clipRectToolModel: new ClipRectToolModel({}),
      editorStatusModel: new EditorStatusModel({}),
      historyModel: new HistoryModel({ undoStack: [], redoStack: [] }),
      mouseControlModel: new MouseControlModel(),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
        maxScale: 10,
        minScale: 0.1,
        zoomSensitivity: 20,
      }),
    };
  }

  private _createViews(): ClipperView {
    return {
      pdfLayerView: new PdfLayerView(this.models),
      maskLayerView: new MaskLayerView(this.models),
    };
  }

  private _createControllers(): ClipperController {
    return {
      hitTestController: new HitTestController(
        this.models,
        this.views,
        this.listeners
      ),
      imageUpdateController: new ImageUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      moveController: new MoveController(
        this.models,
        this.views,
        this.listeners
      ),
      panZoomController: new PanZoomController(
        this.models,
        this.views,
        this.listeners
      ),
      resizeController: new ResizeController(
        this.models,
        this.views,
        this.listeners
      ),
      undoController: new UndoController(
        this.models,
        this.views,
        this.listeners
      ),
      redoController: new RedoController(
        this.models,
        this.views,
        this.listeners
      ),
    };
  }

  async load(): Promise<void> {
    this.models.editorStatusModel.isLoading = true;

    await this._loadPdf();

    this.models.editorStatusModel.isLoading = false;
    this.models.editorStatusModel.isLoaded = true;

    // Center and fit image to canvas
    this.controllers.imageUpdateController.execute({});
  }

  private async _loadPdf(): Promise<void> {
    const { blob, url } = await getPdfPageAsBlob(
      this._resourceUrl,
      this._pageNumber
    );

    this.models.imageModel.blob = blob;
    this.models.imageModel.blobUrl = url;

    // Load the image from blobUrl
    const image = await this._loadImage(url);
    this.models.imageModel.image = image;

    // Set image dimensions in world coordinates
    this.models.imageModel.width = image.width;
    this.models.imageModel.height = image.height;
    this.models.imageModel.leftTop = { x: 0, y: 0 };
  }

  private _loadImage(url: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Failed to load image"));
      img.src = url;
    });
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>): boolean {
    if (!this.models.editorStatusModel.isLoaded) {
      return false;
    }

    // If panning mode (space held), use panZoomController
    if (this._isPanning) {
      this.controllers.panZoomController.execute({ e });
      return true;
    }

    const point = this._getPoint(e);
    const tool = this.models.editorStatusModel.tool;

    if (tool === ActionType.NONE) {
      // Start creating a clip rect
      this.models.mouseControlModel.mouseDownPosition = point;
      return true;
    }

    // In edit mode, check for handle hit
    const handle = this.controllers.hitTestController.execute(point);
    if (handle === HandleType.NONE) {
      return false;
    }

    this.models.mouseControlModel.mouseDownPosition = point;
    this.models.clipRectToolModel.activeHandle = handle;

    if (handle === HandleType.BODY) {
      this.controllers.moveController.execute({ e });
    } else {
      this.controllers.resizeController.execute({ e });
    }

    return true;
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    // If panning mode, use panZoomController
    if (this._isPanning && this.models.mouseControlModel.mouseDownPosition) {
      this.controllers.panZoomController.execute({ e });
      return;
    }

    if (!this.models.mouseControlModel.mouseDownPosition) return;

    const point = this._getPoint(e);
    this.models.mouseControlModel.mouseMovePosition = point;

    const handle = this.models.clipRectToolModel.activeHandle;
    if (handle === HandleType.BODY) {
      this.controllers.moveController.execute({ e });
    } else if (handle !== HandleType.NONE) {
      this.controllers.resizeController.execute({ e });
    }

    this.render();
  }

  onMouseUp(): void {
    if (!this.models.mouseControlModel.mouseDownPosition) return;

    this.models.mouseControlModel.reset();
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.code === "Space" && !this._isPanning) {
      this._isPanning = true;
    }
  }

  onKeyUp(e: KeyboardEvent): void {
    if (e.code === "Space") {
      this._isPanning = false;
      this.models.mouseControlModel.reset();
    }
  }

  onWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    e.preventDefault();
    this.controllers.panZoomController.execute({ e });
  }

  render(): void {
    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }

  private _getPoint(e: React.MouseEvent<HTMLCanvasElement>): Point {
    const rect = this.models.pdfLayerModel.element.getBoundingClientRect();

    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  getCursor(e: React.MouseEvent<HTMLCanvasElement>): string {
    // Panning cursor
    if (this._isPanning) {
      return this.models.mouseControlModel.mouseDownPosition ? "grabbing" : "grab";
    }

    const tool = this.models.editorStatusModel.tool;

    if (tool === ActionType.NONE) {
      return "crosshair";
    }

    if (this.models.mouseControlModel.mouseDownPosition) {
      return this._getCursorForHandle(
        this.models.clipRectToolModel.activeHandle
      );
    }

    const point = this._getPoint(e);
    const handle = this.controllers.hitTestController.execute(point);
    return this._getCursorForHandle(handle);
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
    type: ClipperEvent,
    listener: (args: Partial<ClipperModel>) => void
  ) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type]!.push(listener);
  }

  removeEventListener(
    type: ClipperEvent,
    listener: (args: Partial<ClipperModel>) => void
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

  clearEventListeners(type: ClipperEvent) {
    delete this.listeners[type];
  }

  private _dispatchEvent(eventName: ClipperEvent) {
    const listeners = this.listeners[eventName];

    if (listeners) {
      listeners.forEach((listener) => listener(this.models));
    }
  }

  // Public getters
  get isLoaded(): boolean {
    return this.models.editorStatusModel.isLoaded;
  }

  get isInitialized(): boolean {
    return this.models.editorStatusModel.isInitialized;
  }

  get tool(): ActionType {
    return this.models.editorStatusModel.tool;
  }

  get clipRect(): ClipRect | null {
    return this.models.clipRectToolModel.rect;
  }

  /**
   * Get the clip rect (in canvas coordinates).
   */
  getClipRect(): ClipRect | null {
    return this.models.clipRectToolModel.rect;
  }

  /**
   * Set the clip rect programmatically (in canvas coordinates).
   */
  setClipRect(rect: ClipRect): void {
    this.models.clipRectToolModel.rect = rect;
    if (rect.width > 0 && rect.height > 0) {
      this.models.editorStatusModel.isInitialized = true;
      this.models.editorStatusModel.tool = ActionType.MOVE;
    }
    this.render();
  }

  /**
   * Reset the selection.
   */
  resetSelection(): void {
    this.models.clipRectToolModel.reset();
    this.models.editorStatusModel.isInitialized = false;
    this.models.editorStatusModel.tool = ActionType.NONE;
    this.render();
    this._dispatchEvent(ClipperEvent.MODE_CHANGED);
  }

  /**
   * Clear the canvas.
   */
  clearCanvas(): void {
    this.views.pdfLayerView.clear();
  }

  /**
   * Hit test a point against the selection.
   */
  hitTest(point: Point): HandleType {
    return this.controllers.hitTestController.execute(point);
  }
}
