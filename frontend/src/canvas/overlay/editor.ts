import { CanvasModel } from "./model";
import { CanvasController } from "./controller";
import { CanvasView } from "./view";
import { CanvasEvent, CanvasEventListeners } from "./events";
import { MapMediaType, HandleType, EditorMode, Point } from "./types";

// Models
import { ImageLayerModel } from "./model/layers/imageLayerModel";
import { FrameLayerModel } from "./model/layers/frameLayerModel";
import { MouseControlModel } from "./model/mouseControlModel";
import { MouseInteractionModel } from "./model/mouseInteractionModel";
import { EditorStateModel } from "./model/editorStateModel";
import { ImageBufferModel } from "./model/imageBufferModel";
import { NavigationModel } from "./model/navigationModel";
import { DragInteractionModel } from "./model/dragInteractionModel";
import { ToolManagerModel } from "./model/tools/toolManagerModel";
import { ImageTransformToolModel } from "./model/tools/imageTransformToolModel";

// Views
import { ImageLayerView } from "./view/imageLayerView";
import { FrameLayerView } from "./view/frameLayerView";

// Controllers
import { ModeController } from "./controller/modeController";
import { ImageUploadController } from "./controller/imageUploadController";
import { ToolManagerController } from "./controller/tools/toolManagerController";
import { ImageCreateToolController } from "./controller/tools/imageCreateToolController";
import { ImageMoveToolController } from "./controller/tools/imageMoveToolController";
import { ImageResizeToolController } from "./controller/tools/imageResizeToolController";
import { ImageRotateToolController } from "./controller/tools/imageRotateToolController";

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
  public controllers: CanvasController;
  private listeners: CanvasEventListeners;

  constructor(
    type: MapMediaType,
    resourceUrl: string,
    imageCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number,
    pageNumber: number = 1
  ) {
    this._type = type;
    this._resourceUrl = resourceUrl;
    this._pageNumber = pageNumber;

    this.listeners = {};
    this.models = this._createModels(
      imageCanvas,
      frameCanvas,
      canvasWidth,
      canvasHeight
    );
    this.views = this._createViews();
    this.controllers = this._createControllers();
  }

  private _createModels(
    imageCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ): CanvasModel {
    const dpr = window.devicePixelRatio || 1;

    return {
      imageLayerModel: new ImageLayerModel({
        element: imageCanvas,
        width: canvasWidth,
        height: canvasHeight,
        dpr,
      }),
      frameLayerModel: new FrameLayerModel({
        element: frameCanvas,
        width: canvasWidth,
        height: canvasHeight,
        dpr,
      }),
      mouseControlModel: new MouseControlModel(),
      mouseInteractionModel: new MouseInteractionModel(),
      editorStateModel: new EditorStateModel(),
      imageBufferModel: new ImageBufferModel(),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
        maxScale: 10,
        minScale: 0.1,
      }),
      dragInteractionModel: new DragInteractionModel({}),
      toolManagerModel: new ToolManagerModel({}),
      imageTransformToolModel: new ImageTransformToolModel({}),
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
      modeController: new ModeController(
        this.models,
        this.views,
        this.listeners
      ),
      imageUploadController: new ImageUploadController(
        this.models,
        this.views,
        this.listeners
      ),
      toolManagerController: new ToolManagerController(
        this.models,
        this.views,
        this.listeners
      ),
      imageCreateToolController: new ImageCreateToolController(
        this.models,
        this.views,
        this.listeners
      ),
      imageMoveToolController: new ImageMoveToolController(
        this.models,
        this.views,
        this.listeners
      ),
      imageResizeToolController: new ImageResizeToolController(
        this.models,
        this.views,
        this.listeners
      ),
      imageRotateToolController: new ImageRotateToolController(
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

    // Update mouse interaction model
    this.models.mouseInteractionModel.mouseDownWorldPosition = point;
    this.models.mouseInteractionModel.mouseDownScreenPosition = point;

    switch (mode) {
      case EditorMode.CREATE: {
        if (!this.models.editorStateModel.isLoaded) {
          return false;
        }
        this.models.mouseControlModel.isDown = true;
        this.controllers.imageCreateToolController.execute({ e });
        return true;
      }

      case EditorMode.VIEW: {
        const handle = this.controllers.toolManagerController.detectHandle();
        if (handle === HandleType.NONE) {
          return false;
        }
        this.controllers.modeController.execute(EditorMode.EDIT);
        this.models.mouseControlModel.isDown = true;
        this.models.imageTransformToolModel.activeHandle = handle;
        this._startTransform(handle, e);
        return true;
      }

      case EditorMode.EDIT: {
        const handle = this.controllers.toolManagerController.detectHandle();
        if (handle === HandleType.NONE) {
          this.controllers.modeController.execute(EditorMode.VIEW);
          return false;
        }
        this.models.mouseControlModel.isDown = true;
        this.models.imageTransformToolModel.activeHandle = handle;
        this._startTransform(handle, e);
        return true;
      }

      default:
        return false;
    }
  }

  private _startTransform(
    handle: HandleType,
    e: React.MouseEvent<HTMLCanvasElement>
  ): void {
    if (handle === HandleType.BODY) {
      this.controllers.imageMoveToolController.execute({ e });
    } else {
      this.controllers.imageResizeToolController.execute({ e });
    }
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.mouseControlModel.isDown) return;

    const point = this._getPoint(e);
    const mode = this.models.editorStateModel.mode;

    // Update mouse interaction model
    this.models.mouseInteractionModel.mouseMoveWorldPosition = point;
    this.models.mouseInteractionModel.mouseMoveScreenPosition = point;

    switch (mode) {
      case EditorMode.CREATE: {
        this.controllers.imageCreateToolController.execute({ e });
        this.render();
        break;
      }

      case EditorMode.VIEW:
      case EditorMode.EDIT: {
        const handle = this.models.imageTransformToolModel.activeHandle;
        if (handle === HandleType.BODY) {
          this.controllers.imageMoveToolController.execute({ e });
        } else if (handle !== HandleType.NONE) {
          this.controllers.imageResizeToolController.execute({ e });
        }
        this.render();
        break;
      }
    }
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.mouseControlModel.isDown) return;

    const point = this._getPoint(e);
    const mode = this.models.editorStateModel.mode;

    // Update mouse interaction model
    this.models.mouseInteractionModel.mouseUpWorldPosition = point;
    this.models.mouseInteractionModel.mouseUpScreenPosition = point;

    switch (mode) {
      case EditorMode.CREATE: {
        this.controllers.imageCreateToolController.execute({ e });
        this.models.editorStateModel.isInitialized = true;
        this.controllers.modeController.execute(EditorMode.EDIT);
        break;
      }

      case EditorMode.VIEW:
      case EditorMode.EDIT: {
        const handle = this.models.imageTransformToolModel.activeHandle;
        if (handle === HandleType.BODY) {
          this.controllers.imageMoveToolController.execute({ e });
        } else if (handle !== HandleType.NONE) {
          this.controllers.imageResizeToolController.execute({ e });
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
    const rect = this.models.frameLayerModel.element.getBoundingClientRect();

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
        return this._getCursorForHandle(
          this.models.imageTransformToolModel.activeHandle || HandleType.NONE
        );
      }

      // Otherwise, check what's under the cursor
      const point = this._getPoint(e);
      // Temporarily update mouse position for detection
      const prevPos = this.models.mouseInteractionModel.mouseMoveWorldPosition;
      this.models.mouseInteractionModel.mouseMoveWorldPosition = point;
      const handle = this.controllers.toolManagerController.detectHandle();
      this.models.mouseInteractionModel.mouseMoveWorldPosition = prevPos;
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
    return this.models.imageTransformToolModel.corners;
  }

  get geoCorners() {
    return this.models.imageTransformToolModel.geoCorners;
  }

  setCorners(corners: typeof this.models.imageTransformToolModel.corners) {
    this.models.imageTransformToolModel.corners = corners;
  }

  setGeoCorners(
    geoCorners: typeof this.models.imageTransformToolModel.geoCorners
  ) {
    this.models.imageTransformToolModel.geoCorners = geoCorners;
  }

  /**
   * Initialize the editor with pre-set corners (for embedding with known positions).
   * Sets the editor to EDIT mode and marks as initialized.
   */
  initializeWithCorners(
    screenCorners: typeof this.models.imageTransformToolModel.corners,
    geoCorners: typeof this.models.imageTransformToolModel.geoCorners
  ) {
    this.models.imageTransformToolModel.corners = screenCorners;
    this.models.imageTransformToolModel.geoCorners = geoCorners;
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
}
