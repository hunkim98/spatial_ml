import { ClipperModel } from "./model";
import { ClipperController } from "./controller";
import { ClipperView } from "./view";
import { ClipperEvent, ClipperEventListeners } from "./events";
import { HandleType, Point, ClipRect } from "./types";
import { ActionType } from "./actions/base";

// Models
import { MaskLayerModel } from "./model/layers/frameLayerModel";
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
import { PdfUpdateController } from "./controller/pdfUpdateController";
import { MouseInteractionController } from "./controller/mouseInteractionController";
import { ResizeController } from "./controller/resizeController";
import { UndoController } from "./controller/undoController";
import { RedoController } from "./controller/redoController";
import {
  getCanvasRelativePositionFromWorldPoint,
  getWorldPointFromEvent,
} from "./utils/project";
import { CanvasSizeScaleController } from "./controller/settings/CanvasSizeScaleController";

export class ClipperEditor {
  private _isPanning: boolean = false;

  private models: ClipperModel = {} as ClipperModel;
  private views: ClipperView = {} as ClipperView;
  public controllers: ClipperController = {} as ClipperController;
  private listeners: ClipperEventListeners;

  constructor(
    pdfCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ) {
    this.listeners = {};
    this.models = this._createModels(
      pdfCanvas,
      frameCanvas,
      canvasWidth,
      canvasHeight
    );
    this.views = this._createViews();
    this.controllers = this._createControllers();
  }

  private _createModels(
    pdfCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ): ClipperModel {
    return {
      pdfLayerModel: new PdfLayerModel({
        width: canvasWidth,
        height: canvasHeight,
        dpr: 1,
        element: pdfCanvas,
      }),
      maskLayerModel: new MaskLayerModel({
        width: canvasWidth,
        height: canvasHeight,
        dpr: 1,
        element: frameCanvas,
      }),
      imageModel: new ImageModel({
        image: null,
        blob: null,
        blobUrl: null,
        width: null,
        height: null,
        leftTop: { x: 0, y: 0 }, // Image model will always be at the origin
      }),
      clipRectToolModel: new ClipRectToolModel({}),
      editorStatusModel: new EditorStatusModel({}),
      historyModel: new HistoryModel({ undoStack: [], redoStack: [] }),
      mouseControlModel: new MouseControlModel(),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
        maxScale: 10,
        minScale: 0.1,
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
      canvasSizeScaleController: new CanvasSizeScaleController(
        this.models,
        this.views,
        this.listeners
      ),
      hitTestController: new HitTestController(
        this.models,
        this.views,
        this.listeners
      ),
      pdfUpdateController: new PdfUpdateController(
        this.models,
        this.views,
        this.listeners
      ),

      mouseInteractionController: new MouseInteractionController(
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

  public updatePdf(resourceUrl: string, pageNumber: number): void {
    this.controllers.pdfUpdateController.execute({
      resourceUrl,
      pageNumber,
      canvasWidth: this.models.pdfLayerModel.width,
      canvasHeight: this.models.pdfLayerModel.height,
    });
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const worldPos = getWorldPointFromEvent(
      e,
      this.models.pdfLayerModel.element,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );
    // console.log("worldPos", worldPos);
    const screenPos = getCanvasRelativePositionFromWorldPoint(
      worldPos,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );

    this.models.mouseControlModel.update({
      mouseDownWorldPosition: worldPos,
      mouseDownScreenPosition: screenPos,
      mouseMoveWorldPosition: worldPos,
      mouseMoveScreenPosition: screenPos,
      mouseUpWorldPosition: null,
      mouseUpScreenPosition: null,
    });
    this.controllers.mouseInteractionController.execute({ e });
    // If panning mode (space held), use panZoomController
    // if (this._isPanning) {
    //   this.controllers.panZoomController.execute({ e });
    //   return true;
    // }

    // const point = this._getPoint(e);
    // const tool = this.models.editorStatusModel.tool;

    // if (tool === ActionType.NONE) {
    //   // Start creating a clip rect
    //   this.models.mouseControlModel.mouseDownPosition = point;
    //   return true;
    // }

    // // In edit mode, check for handle hit
    // const handle = this.controllers.hitTestController.execute(point);
    // if (handle === HandleType.NONE) {
    //   return false;
    // }

    // this.models.mouseControlModel.mouseDownPosition = point;
    // this.models.clipRectToolModel.activeHandle = handle;

    // if (handle === HandleType.BODY) {
    //   this.controllers.moveController.execute({ e });
    // } else {
    //   this.controllers.resizeController.execute({ e });
    // }

    // return true;
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    // If panning mode, use panZoomController
    if (!this.models.editorStatusModel.isLoaded) return;
    const worldPos = getWorldPointFromEvent(
      e,
      this.models.pdfLayerModel.element,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );
    // console.log("worldPos", worldPos);
    const screenPos = getCanvasRelativePositionFromWorldPoint(
      worldPos,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );

    this.models.mouseControlModel.update({
      mouseDownWorldPosition: worldPos,
      mouseDownScreenPosition: screenPos,
      mouseMoveWorldPosition: worldPos,
      mouseMoveScreenPosition: screenPos,
      mouseUpWorldPosition: null,
      mouseUpScreenPosition: null,
    });
    this.controllers.mouseInteractionController.execute({ e });
    this.render();
  }

  onMouseUp(_e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    // const worldPos = getWorldPointFromEvent(
    //   e,
    //   this.models.pdfLayerModel.element,
    //   this.models.navigationModel.offset,
    //   this.models.navigationModel.scale
    // );
    // // console.log("worldPos", worldPos);
    // const screenPos = getCanvasRelativePositionFromWorldPoint(
    //   worldPos,
    //   this.models.navigationModel.offset,
    //   this.models.navigationModel.scale
    // );

    // this.models.mouseControlModel.update({
    //   mouseDownWorldPosition: worldPos,
    //   mouseDownScreenPosition: screenPos,
    //   mouseMoveWorldPosition: worldPos,
    //   mouseMoveScreenPosition: screenPos,
    //   mouseUpWorldPosition: null,
    //   mouseUpScreenPosition: null,
    // });
    // this.controllers.interactionController.execute({ e });
    this.models.mouseControlModel.reset();
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.code === "Space" && !this._isPanning) {
      this._isPanning = true;
    }
  }

  onKeyUp(e: KeyboardEvent): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    if (e.code === "Space") {
      this._isPanning = false;
      this.models.mouseControlModel.reset();
    }
  }

  onWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    e.preventDefault();
    this.controllers.mouseInteractionController.execute({ e });
  }

  executeInteraction(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    if (!this.models.editorStatusModel.tool) {
    }
    this.controllers.mouseInteractionController.execute({ e });
  }

  render(): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }

  private _getPoint(e: React.MouseEvent<HTMLCanvasElement>): Point {
    if (!this.models.editorStatusModel.isLoaded) return { x: 0, y: 0 };
    const rect = this.models.pdfLayerModel.element.getBoundingClientRect();

    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    };
  }

  getCursor(e: React.MouseEvent<HTMLCanvasElement>): string {
    // Panning cursor
    if (!this.models.editorStatusModel.isLoaded) return "default";
    if (this._isPanning) {
      return this.models.mouseControlModel.mouseDownWorldPosition
        ? "grabbing"
        : "grab";
    }

    const tool = this.models.editorStatusModel.tool;

    if (tool === ActionType.NONE) {
      return "crosshair";
    }

    if (this.models.mouseControlModel.mouseDownWorldPosition) {
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
      this.models.editorStatusModel.tool = ActionType.MOVE;
    }
    this.render();
  }

  /**
   * Reset the selection.
   */
  resetSelection(): void {
    this.models.clipRectToolModel.reset();
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
