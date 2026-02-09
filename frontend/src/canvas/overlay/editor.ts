import { CanvasModel } from "./model";
import { CanvasController } from "./controller";
import { CanvasView } from "./view";
import { CanvasEvent, CanvasEventListeners } from "./events";
import { HandleType, EditorMode, Point } from "./types";

// Models
import { ImageLayerModel } from "./model/layers/imageLayerModel";
import { FrameLayerModel } from "./model/layers/frameLayerModel";
import { MouseControlModel } from "./model/mouseControlModel";
import { MouseInteractionModel } from "./model/mouseInteractionModel";
import { EditorStateModel } from "./model/editorStateModel";
import { ImageBufferModel } from "./model/imageBufferModel";
import { NavigationModel } from "./model/navigationModel";
import { DragInteractionModel } from "./model/dragInteractionModel";
import { ToolManagerModel, ToolType } from "./model/tools/toolManagerModel";
import { ImageTransformToolModel } from "./model/tools/imageTransformToolModel";

// Views
import { ImageLayerView } from "./view/imageLayerView";
import { FrameLayerView } from "./view/frameLayerView";

// Controllers
import { ModeController } from "./controller/modeController";
import { ImageUploadController } from "./controller/imageUploadController";
import { MouseInteractionController } from "./controller/mouseInteractionController";
import { DragInteractionController } from "./controller/dragInteractionController";
import { ToolManagerController } from "./controller/tools/toolManagerController";
import { ImageCreateToolController } from "./controller/tools/imageCreateToolController";
import { ImageMoveToolController } from "./controller/tools/imageMoveToolController";
import { ImageResizeToolController } from "./controller/tools/imageResizeToolController";
import { ImageRotateToolController } from "./controller/tools/imageRotateToolController";
import { PdfUpdateController } from "./controller/input/pdfUpdateController";
import { ImageUpdateController } from "./controller/input/imageUpdateController";
import { BufferUpdateController } from "./controller/input/bufferUpdateController";
import {
  getCanvasRelativePositionFromWorldPoint,
  getWorldPointFromEvent,
} from "./utils/project";

export class Editor {
  private models: CanvasModel;
  private views: CanvasView;
  public controllers: CanvasController;
  private listeners: CanvasEventListeners;

  constructor(
    imageCanvas: HTMLCanvasElement,
    frameCanvas: HTMLCanvasElement,
    canvasWidth: number,
    canvasHeight: number
  ) {
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
      pdfUpdateController: new PdfUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      imageUpdateController: new ImageUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      bufferUpdateController: new BufferUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
    };
  }

  // Public methods for updating content
  public async updatePdf(url: string, pageNumber: number): Promise<void> {
    await this.controllers.pdfUpdateController.execute({ url, pageNumber });
  }

  public async updateImage(url: string): Promise<void> {
    await this.controllers.imageUpdateController.execute({ url });
  }

  public updateBuffer(buffer: HTMLCanvasElement): void {
    this.controllers.bufferUpdateController.execute({ buffer });
  }

  onMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    const worldPos = getWorldPointFromEvent(
      e,
      this.models.frameLayerModel.element,
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

    // Update mouse interaction state
    this.controllers.mouseInteractionController.execute({ e });
    this.controllers.dragInteractionController.execute({ e });
    this.controllers.toolManagerController.execute({ e });
    this.executeInteraction(e);
  }

  onMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStateModel.isLoaded) return;

    const worldPos = getWorldPointFromEvent(
      e,
      this.models.frameLayerModel.element,
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
      mouseUpWorldPosition: null,
      mouseUpScreenPosition: null,
    });

    this.controllers.mouseInteractionController.execute({ e });
    this.controllers.dragInteractionController.execute({ e });
    this.controllers.toolManagerController.execute({ e });
    this.executeInteraction(e);
  }

  onMouseUp(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStateModel.isLoaded) return;

    const worldPos = getWorldPointFromEvent(
      e,
      this.models.frameLayerModel.element,
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
    if (!this.models.editorStateModel.isLoaded) return;
    if (e.code === "Space") {
      this.models.mouseInteractionModel.reset();
    }
  }

  onWheel(e: WheelEvent): void {
    if (!this.models.editorStateModel.isLoaded) return;
    this.controllers.mouseInteractionController.execute({
      e: e as unknown as React.WheelEvent<HTMLCanvasElement>,
    });
  }

  executeInteraction(e: React.MouseEvent<HTMLCanvasElement>): void {
    if (!this.models.editorStateModel.isLoaded) return;
    const { activeTool } = this.models.toolManagerModel;
    if (!activeTool) {
      return;
    }
    console.log("executeInteraction", activeTool);
    switch (activeTool) {
      case ToolType.IMAGE_CREATE:
        this.controllers.imageCreateToolController.execute({ e });
        break;
      case ToolType.IMAGE_MOVE:
        this.controllers.imageMoveToolController.execute({ e });
        break;
      case ToolType.IMAGE_RESIZE:
        this.controllers.imageResizeToolController.execute({ e });
        break;
      case ToolType.IMAGE_ROTATE:
        this.controllers.imageRotateToolController.execute({ e });
        break;
    }
    this.render();
  }

  render(): void {
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.clear();
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
