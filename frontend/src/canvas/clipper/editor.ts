import { ClipperModel } from "./model";
import { ClipperController } from "./controller";
import { ClipperView } from "./view";
import { ClipperEvent, ClipperEventListeners } from "./events";
import { HandleType, Point } from "./types";
import { ActionType } from "./actions/base";

// Models
import { MaskLayerModel } from "./model/layers/frameLayerModel";
import { PdfLayerModel } from "./model/layers/pdfLayerModel";
import { ClipRectToolModel } from "./model/tools/clipRectToolModel";
import { EditorStatusModel } from "./model/editorStatusModel";
import { HistoryModel } from "./model/historyModel";
import { ImageModel } from "./model/imageModel";
import { MouseInteractionModel } from "./model/mouseInteractionModel";
import { NavigationModel } from "./model/navigationModel";

// Views
import { PdfLayerView } from "./view/pdfLayerView";
import { MaskLayerView } from "./view/maskLayerView";

// Controllers
import { PdfUpdateController } from "./controller/pdfUpdateController";
import { MouseInteractionController } from "./controller/mouseInteractionController";
import { UndoController } from "./controller/undoController";
import { RedoController } from "./controller/redoController";
import {
  getCanvasRelativePositionFromWorldPoint,
  getWorldPointFromEvent,
} from "./utils/project";
import { CanvasSizeScaleController } from "./controller/settings/CanvasSizeScaleController";
import { ToolManagerModel } from "./model/tools/toolManagerModel";
import { ToolManagerController } from "./controller/tools/toolManagerController";
import { ClipRectCreateToolController } from "./controller/tools/clipRectCreateToolController";
import { ClipRectEditToolController } from "./controller/tools/clipRectEditToolController";
import { ToolType } from "./types/tool";
import { DragInteractionModel } from "./model/dragInteractionModel";
import { DragInteractionController } from "./controller/dragInteractionController";
import { ExportController } from "./controller/exportController";

export class ClipperEditor {
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
      mouseInteractionModel: new MouseInteractionModel(),
      toolManagerModel: new ToolManagerModel({}),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
        maxScale: 10,
        minScale: 0.1,
      }),
      dragInteractionModel: new DragInteractionModel({}),
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
      pdfUpdateController: new PdfUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      toolManagerController: new ToolManagerController(
        this.models,
        this.views,
        this.listeners
      ),
      mouseInteractionController: new MouseInteractionController(
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
      dragInteractionController: new DragInteractionController(
        this.models,
        this.views,
        this.listeners
      ),
      clipRectCreateToolController: new ClipRectCreateToolController(
        this.models,
        this.views,
        this.listeners
      ),
      clipRectEditToolController: new ClipRectEditToolController(
        this.models,
        this.views,
        this.listeners
      ),
      exportController: new ExportController(
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

    this.models.mouseInteractionModel.update({
      mouseDownWorldPosition: worldPos,
      mouseDownScreenPosition: screenPos,
      mouseMoveWorldPosition: worldPos,
      mouseMoveScreenPosition: screenPos,
      mouseUpWorldPosition: null,
      mouseUpScreenPosition: null,
    });
    this.controllers.mouseInteractionController.execute({ e });
    this.controllers.dragInteractionController.execute({ e });
    this.controllers.toolManagerController.execute({ e }); // Detect tool/handle at mousedown
    this.executeInteraction(e);
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    const worldPos = getWorldPointFromEvent(
      e,
      this.models.pdfLayerModel.element,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );
    const screenPos = getCanvasRelativePositionFromWorldPoint(
      worldPos,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );

    this.models.mouseInteractionModel.update({
      mouseDownWorldPosition: worldPos,
      mouseDownScreenPosition: screenPos,
      mouseMoveWorldPosition: worldPos,
      mouseMoveScreenPosition: screenPos,
      mouseUpWorldPosition: null,
      mouseUpScreenPosition: null,
    });
    this.controllers.mouseInteractionController.execute({ e });
    this.controllers.dragInteractionController.execute({ e });
    // Always update candidate (for cursor), locks active during editing
    this.controllers.toolManagerController.execute({ e });
    this.executeInteraction(e);
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>): void {
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
    this.controllers.mouseInteractionController.execute({ e });
    this.controllers.dragInteractionController.execute({ e });
    this.controllers.toolManagerController.execute({ e });
    this.executeInteraction(e);
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.code === "Space") {
      // null means the grab tool is active
      this.models.toolManagerModel.activeTool = null;
    }
  }

  onKeyUp(e: KeyboardEvent): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    if (e.code === "Space") {
      this.models.mouseInteractionModel.reset();
    }
  }

  onWheel(e: WheelEvent): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    this.controllers.mouseInteractionController.execute({
      e: e as unknown as React.WheelEvent<HTMLCanvasElement>,
    });
  }

  executeInteraction(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    const { activeTool } = this.models.toolManagerModel;
    if (!activeTool) {
      return;
    }
    switch (activeTool) {
      case ToolType.CLIP_RECT_CREATE:
        this.controllers.clipRectCreateToolController.execute({ e });
        break;
      case ToolType.CLIP_RECT_RESIZE:
        this.controllers.clipRectEditToolController.execute({ e });
        break;
      default:
        this.controllers.mouseInteractionController.execute({ e });
    }
    this.render();
  }

  render(): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }

  getCursor(e: React.MouseEvent<HTMLCanvasElement>): string {
    if (!this.models.editorStatusModel.isLoaded) return "default";

    // Use candidate tool/handle for cursor (always reflects current mouse position)
    const tool = this.models.toolManagerModel.candidateTool;
    const handle = this.models.clipRectToolModel.candidateHandle;
    const dragStart = this.models.dragInteractionModel.dragStartWorldPosition;

    if (!tool) {
      if (dragStart) {
        return "grabbing";
      }
      return "grab";
    }
    if (tool === ToolType.CLIP_RECT_CREATE) {
      return "crosshair";
    }
    if (tool === ToolType.CLIP_RECT_RESIZE) {
      if (!handle) return "grab";
      return this._getCursorForHandle(handle);
    }
    return "grab";
  }

  private _getCursorForHandle(handle: HandleType | null): string {
    if (!handle) return "grab";
    switch (handle) {
      case HandleType.BODY:
        return "move";
      case HandleType.TOP_LEFT:
      case HandleType.BOTTOM_RIGHT:
        return "nwse-resize";
      case HandleType.TOP_RIGHT:
      case HandleType.BOTTOM_LEFT:
        return "nesw-resize";
      case HandleType.LEFT:
      case HandleType.RIGHT:
        return "ew-resize";
      case HandleType.TOP:
      case HandleType.BOTTOM:
        return "ns-resize";
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

  // Public methods
  /**
   * Export the clipped region as a high-quality image
   * Delegates to ExportController
   */
  async exportClippedImage(format?: "png" | "jpeg", quality?: number) {
    return this.controllers.exportController.execute({ format, quality });
  }
}
