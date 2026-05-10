import { PatternSelectorModel } from "./model";
import { PatternSelectorController } from "./controller";
import { PatternSelectorView } from "./view";
import {
  PatternSelectorEvent,
  PatternSelectorEventListeners,
} from "./events";
import { PatternToolType } from "./model/toolManagerModel";

// Models
import { ImageLayerModel } from "./model/layers/imageLayerModel";
import { OverlayLayerModel } from "./model/layers/overlayLayerModel";
import { ImageModel } from "./model/imageModel";
import { NavigationModel } from "./model/navigationModel";
import { MouseInteractionModel } from "./model/mouseInteractionModel";
import { DragInteractionModel } from "./model/dragInteractionModel";
import { EditorStatusModel } from "./model/editorStatusModel";
import { PatternCirclesModel } from "./model/patternCirclesModel";
import { ToolManagerModel } from "./model/toolManagerModel";

// Views
import { ImageLayerView } from "./view/imageLayerView";
import { OverlayLayerView } from "./view/overlayLayerView";

// Controllers
import { CanvasSizeController } from "./controller/canvasSizeController";
import { ImageBufferUpdateController } from "./controller/imageBufferUpdateController";
import { MouseInteractionController } from "./controller/mouseInteractionController";
import { DragInteractionController } from "./controller/dragInteractionController";
import { ToolManagerController } from "./controller/toolManagerController";
import { PatternCircleCreateController } from "./controller/patternCircleCreateController";
import { PatternCircleEditController } from "./controller/patternCircleEditController";

import {
  getCanvasRelativePositionFromWorldPoint,
  getWorldPointFromEvent,
} from "./utils/project";

export class PatternSelectorEditor {
  private models: PatternSelectorModel;
  private views: PatternSelectorView;
  public controllers: PatternSelectorController;
  private listeners: PatternSelectorEventListeners;
  private _isSpaceHeld: boolean = false;

  constructor(
    imageCanvas: HTMLCanvasElement,
    overlayCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ) {
    this.listeners = {};
    this.models = this._createModels(
      imageCanvas,
      overlayCanvas,
      canvasWidth,
      canvasHeight
    );
    this.views = this._createViews();
    this.controllers = this._createControllers();
  }

  private _createModels(
    imageCanvas: HTMLCanvasElement,
    overlayCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ): PatternSelectorModel {
    return {
      imageLayerModel: new ImageLayerModel({
        width: canvasWidth,
        height: canvasHeight,
        dpr: 1,
        element: imageCanvas,
      }),
      overlayLayerModel: new OverlayLayerModel({
        width: canvasWidth,
        height: canvasHeight,
        dpr: 1,
        element: overlayCanvas,
      }),
      imageModel: new ImageModel({
        image: null,
        width: null,
        height: null,
        leftTop: { x: 0, y: 0 },
      }),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
        maxScale: 10,
        minScale: 0.1,
      }),
      mouseInteractionModel: new MouseInteractionModel(),
      dragInteractionModel: new DragInteractionModel(),
      editorStatusModel: new EditorStatusModel(),
      patternCirclesModel: new PatternCirclesModel(),
      toolManagerModel: new ToolManagerModel(),
    };
  }

  private _createViews(): PatternSelectorView {
    return {
      imageLayerView: new ImageLayerView(this.models),
      overlayLayerView: new OverlayLayerView(this.models),
    };
  }

  private _createControllers(): PatternSelectorController {
    return {
      canvasSizeController: new CanvasSizeController(
        this.models,
        this.views,
        this.listeners
      ),
      imageBufferUpdateController: new ImageBufferUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      mouseInteractionController: new MouseInteractionController(
        this.models,
        this.views,
        this.listeners
      ),
      dragInteractionController: new DragInteractionController(
        this.models,
        this.views,
        this.listeners
      ),
      toolManagerController: new ToolManagerController(
        this.models,
        this.views,
        this.listeners
      ),
      patternCircleCreateController: new PatternCircleCreateController(
        this.models,
        this.views,
        this.listeners
      ),
      patternCircleEditController: new PatternCircleEditController(
        this.models,
        this.views,
        this.listeners
      ),
    };
  }

  // ========== Public API ==========

  public loadImageUrl(imageUrl: string): void {
    this.controllers.imageBufferUpdateController.execute({ imageUrl });
  }

  public get isLoaded(): boolean {
    return this.models.editorStatusModel.isLoaded;
  }

  public get isSpaceHeld(): boolean {
    return this._isSpaceHeld;
  }

  public get patternCircles() {
    return this.models.patternCirclesModel.circles;
  }

  public removePattern(id: string): void {
    this.models.patternCirclesModel.removeCircle(id);
    this.render();
    this.dispatchEvent(PatternSelectorEvent.PATTERN_REMOVED);
  }

  public renamePattern(id: string, name: string): void {
    this.models.patternCirclesModel.renameCircle(id, name);
    this.render();
  }

  /**
   * Export a pattern as the inscribed square of the circle.
   * The inscribed square has side = radius * sqrt(2), centered on the circle.
   */
  public exportPatternCrop(
    patternId: string
  ): { buffer: HTMLCanvasElement; size: number } | null {
    const circle = this.models.patternCirclesModel.circles.find(
      (c) => c.id === patternId
    );
    if (!circle) return null;

    const { image, width, height } = this.models.imageModel;
    if (!image || !width || !height) return null;

    // Inscribed square: side = radius * sqrt(2), half-side = radius / sqrt(2)
    const halfSide = circle.radius * Math.SQRT1_2;
    const size = Math.round(halfSide * 2);

    const sx = Math.max(0, Math.round(circle.center.x - halfSide));
    const sy = Math.max(0, Math.round(circle.center.y - halfSide));
    const sw = Math.min(size, width - sx);
    const sh = Math.min(size, height - sy);

    if (sw <= 0 || sh <= 0) return null;

    const buffer = document.createElement("canvas");
    buffer.width = sw;
    buffer.height = sh;
    const ctx = buffer.getContext("2d");
    if (!ctx) return null;

    ctx.drawImage(image, sx, sy, sw, sh, 0, 0, sw, sh);

    return { buffer, size: Math.max(sw, sh) };
  }

  // ========== Event handling ==========

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;

    const worldPos = getWorldPointFromEvent(
      e,
      this.models.imageLayerModel.element,
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

    if (this._isSpaceHeld) {
      // Space held → pan mode
      this.controllers.dragInteractionController.execute({ e });
    } else {
      // Detect tool from hit detection
      this.controllers.toolManagerController.execute({ e });
      this.executeActiveTool(e);
    }

    this.render();
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;

    const worldPos = getWorldPointFromEvent(
      e,
      this.models.imageLayerModel.element,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );
    const screenPos = getCanvasRelativePositionFromWorldPoint(
      worldPos,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );

    this.models.mouseInteractionModel.update({
      mouseMoveWorldPosition: worldPos,
      mouseMoveScreenPosition: screenPos,
    });

    if (this._isSpaceHeld) {
      this.controllers.dragInteractionController.execute({ e });
    } else {
      // Update candidate tool for cursor
      this.controllers.toolManagerController.execute({ e });
      this.executeActiveTool(e);
    }

    this.render();
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStatusModel.isLoaded) return;

    const worldPos = getWorldPointFromEvent(
      e,
      this.models.imageLayerModel.element,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );
    const screenPos = getCanvasRelativePositionFromWorldPoint(
      worldPos,
      this.models.navigationModel.offset,
      this.models.navigationModel.scale
    );

    this.models.mouseInteractionModel.update({
      mouseUpWorldPosition: worldPos,
      mouseUpScreenPosition: screenPos,
    });

    if (this._isSpaceHeld) {
      this.controllers.dragInteractionController.execute({ e });
    } else {
      this.executeActiveTool(e);
      // Clear active tool on mouseup
      this.models.toolManagerModel.activeTool = null;
      this.models.toolManagerModel.activeCircleId = null;
    }

    this.controllers.mouseInteractionController.execute({ e });
    this.render();
  }

  private executeActiveTool(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { activeTool } = this.models.toolManagerModel;
    if (!activeTool) return;

    switch (activeTool) {
      case PatternToolType.CREATE:
        if (e.type === "mousedown") {
          const worldPos =
            this.models.mouseInteractionModel.mouseDownWorldPosition;
          if (worldPos) {
            this.controllers.patternCircleCreateController.execute({
              point: worldPos,
            });
          }
          // Clear active tool immediately — create is a single click
          this.models.toolManagerModel.activeTool = null;
          this.models.toolManagerModel.activeCircleId = null;
        }
        break;
      case PatternToolType.RESIZE:
      case PatternToolType.MOVE:
        this.controllers.patternCircleEditController.execute({ e });
        break;
    }
  }

  onWheel(e: WheelEvent): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    this.controllers.mouseInteractionController.execute({
      e: e as unknown as React.WheelEvent<HTMLCanvasElement>,
    });
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.code === "Space") {
      e.preventDefault();
      this._isSpaceHeld = true;
    }
  }

  onKeyUp(e: KeyboardEvent): void {
    if (e.code === "Space") {
      this._isSpaceHeld = false;
      this.models.mouseInteractionModel.reset();
      this.models.dragInteractionModel.reset();
    }
  }

  getCursor(): string {
    if (!this.models.editorStatusModel.isLoaded) return "default";

    if (this._isSpaceHeld) {
      return this.models.dragInteractionModel.dragStartWorldPosition
        ? "grabbing"
        : "grab";
    }

    const { candidateTool, activeTool } = this.models.toolManagerModel;
    const tool = activeTool ?? candidateTool;

    switch (tool) {
      case PatternToolType.RESIZE:
        return "nwse-resize";
      case PatternToolType.MOVE:
        return "move";
      case PatternToolType.CREATE:
      default:
        return "crosshair";
    }
  }

  // ========== Rendering ==========

  render(): void {
    if (!this.models.editorStatusModel.isLoaded) return;
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.overlayLayerView.render();
  }

  // ========== Event listeners ==========

  addEventListener(
    type: PatternSelectorEvent,
    listener: (args: Partial<PatternSelectorModel>) => void
  ) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type]!.push(listener);
  }

  removeEventListener(
    type: PatternSelectorEvent,
    listener: (args: Partial<PatternSelectorModel>) => void
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

  private dispatchEvent(eventName: PatternSelectorEvent) {
    const listeners = this.listeners[eventName];
    if (listeners) {
      listeners.forEach((listener) => listener(this.models));
    }
  }
}
