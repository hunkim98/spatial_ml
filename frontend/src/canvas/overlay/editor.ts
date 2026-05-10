import { CanvasModel } from "./model";
import { CanvasController } from "./controller";
import { CanvasView } from "./view";
import { CanvasEvent, CanvasEventListeners } from "./events";
import { HandleType, Location, Point, ScreenCorners } from "./types";

// Models
import { ImageLayerModel } from "./model/layers/imageLayerModel";
import { FrameLayerModel } from "./model/layers/frameLayerModel";
import { MouseInteractionModel } from "./model/mouseInteractionModel";
import { EditorStateModel } from "./model/editorStateModel";
import { ImageBufferModel } from "./model/imageBufferModel";
import { NavigationModel } from "./model/navigationModel";
import { TransformSessionModel } from "./model/transformSessionModel";
import { DragInteractionModel } from "./model/dragInteractionModel";
import { ToolManagerModel, ToolType } from "./model/tools/toolManagerModel";
import { ImageTransformToolModel } from "./model/tools/imageTransformToolModel";
import { GeoJSONEditModel } from "./model/tools/geojsonEditModel";
import { KeyboardInteractionModel } from "./model/keyboardInteractionModel";

// Views
import { ImageLayerView } from "./view/imageLayerView";
import { FrameLayerView } from "./view/frameLayerView";
import { PolygonLayerView } from "./view/polygonLayerView";

// Controllers
import { ModeController } from "./controller/modeController";
import { MouseInteractionController } from "./controller/mouseInteractionController";
import { DragInteractionController } from "./controller/dragInteractionController";
import { ToolManagerController } from "./controller/tools/toolManagerController";
import { ImageCreateToolController } from "./controller/tools/imageCreateToolController";
import { ImageMoveToolController } from "./controller/tools/imageMoveToolController";
import { ImageResizeToolController } from "./controller/tools/imageResizeToolController";
import { ImageRotateToolController } from "./controller/tools/imageRotateToolController";
import { PolygonHitTestController } from "./controller/tools/polygonHitTestController";
import { PolygonVertexMoveController } from "./controller/tools/polygonVertexMoveController";
import { PolygonMoveController } from "./controller/tools/polygonMoveController";
import { PolygonSelectController } from "./controller/tools/polygonSelectController";
import { PolygonVertexAddController } from "./controller/tools/polygonVertexAddController";
import { PolygonVertexDeleteController } from "./controller/tools/polygonVertexDeleteController";
import { PolygonDeleteController } from "./controller/tools/polygonDeleteController";
import { ProjectionController } from "./controller/projectionController";
import { PdfUpdateController } from "./controller/input/pdfUpdateController";
import { ImageUpdateController } from "./controller/input/imageUpdateController";
import { BufferUpdateController } from "./controller/input/bufferUpdateController";
import { CanvasSizeScaleController } from "./controller/settings/canvasSizeScaleController";
import {
  getCanvasRelativePositionFromWorldPoint,
  getWorldPointFromEvent,
} from "./utils/project";
import { ImagePropertyController } from "./controller/imagePropertyController";
import { KeyboardInteractionController } from "./controller/keyboardInteractionController";
import { TransformSessionController } from "./controller/transformSessionController";

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
      mouseInteractionModel: new MouseInteractionModel(),
      editorStateModel: new EditorStateModel(),
      imageBufferModel: new ImageBufferModel({
        buffer: null,
        width: null,
        height: null,
        leftTop: { x: 0, y: 0 },
        opacity: 0.5,
      }),
      navigationModel: new NavigationModel({
        scale: 1,
        offset: { x: 0, y: 0 },
      }),
      dragInteractionModel: new DragInteractionModel({}),
      toolManagerModel: new ToolManagerModel({}),
      imageTransformToolModel: new ImageTransformToolModel({}),
      geojsonEditModel: new GeoJSONEditModel(),
      keyboardInteractionModel: new KeyboardInteractionModel(),
      transformSessionModel: new TransformSessionModel(),
    };
  }

  private _createViews(): CanvasView {
    return {
      frameLayerView: new FrameLayerView(this.models),
      imageLayerView: new ImageLayerView(this.models),
      polygonLayerView: new PolygonLayerView(this.models),
    };
  }

  private _createControllers(): CanvasController {
    return {
      modeController: new ModeController(
        this.models,
        this.views,
        this.listeners
      ),
      imageUpdateController: new ImageUpdateController(
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
      polygonHitTestController: new PolygonHitTestController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonVertexMoveController: new PolygonVertexMoveController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonMoveController: new PolygonMoveController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonSelectController: new PolygonSelectController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonVertexAddController: new PolygonVertexAddController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonVertexDeleteController: new PolygonVertexDeleteController(
        this.models,
        this.views,
        this.listeners
      ),
      polygonDeleteController: new PolygonDeleteController(
        this.models,
        this.views,
        this.listeners
      ),
      projectionController: new ProjectionController(
        this.models,
        this.views,
        this.listeners
      ),
      pdfUpdateController: new PdfUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      bufferUpdateController: new BufferUpdateController(
        this.models,
        this.views,
        this.listeners
      ),
      canvasSizeScaleController: new CanvasSizeScaleController(
        this.models,
        this.views,
        this.listeners
      ),
      imagePropertyController: new ImagePropertyController(
        this.models,
        this.views,
        this.listeners
      ),
      keyboardInteractionController: new KeyboardInteractionController(
        this.models,
        this.views,
        this.listeners
      ),
      transformSessionController: new TransformSessionController(
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

  // ---- Polygon editing public API ----

  /** Load GeoJSON for polygon editing */
  setGeoJSON(fc: GeoJSON.FeatureCollection | null): void {
    this.models.geojsonEditModel.reset();
    this.models.geojsonEditModel.featureCollection = fc;
    this.render();
  }

  /** Get the current GeoJSON (with any edits applied) */
  getGeoJSON(): GeoJSON.FeatureCollection | null {
    return this.models.geojsonEditModel.featureCollection;
  }

  /** Bind map projection functions for geo ↔ screen conversion */
  setProjection(
    project: (lngLat: Location) => Point,
    unproject: (point: Point) => Location
  ): void {
    this.controllers.projectionController.bind(project, unproject);
  }

  /** Whether a polygon drag is in progress (vertex move, polygon move) */
  get isPolygonDragging(): boolean {
    return this.models.geojsonEditModel.isEditing;
  }

  private get isPolygonMode(): boolean {
    return this.models.geojsonEditModel.featureCollection !== null;
  }

  // ---- Mouse event handlers ----

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

    this.controllers.mouseInteractionController.execute({ e });
    if (this.isPolygonMode) {
      this.controllers.projectionController.computeGeoPositions();
      this.controllers.polygonHitTestController.execute({ e });
    } else {
      this.controllers.dragInteractionController.execute({ e });
      this.controllers.toolManagerController.execute({ e });
    }
    this.executeInteraction(e);
  }

  onMouseMove(e: React.MouseEvent<Element>): void {
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
    if (this.isPolygonMode) {
      this.controllers.projectionController.computeGeoPositions();
      this.controllers.polygonHitTestController.execute({ e });
    } else {
      this.controllers.dragInteractionController.execute({ e });
      this.controllers.toolManagerController.execute({ e });
    }
    this.executeInteraction(e);
  }

  onMouseUp(e: React.MouseEvent<Element>): void {
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
    if (this.isPolygonMode) {
      this.controllers.projectionController.computeGeoPositions();
    } else {
      this.controllers.dragInteractionController.execute({ e });
      this.controllers.toolManagerController.execute({ e });
    }
    this.executeInteraction(e);
  }

  onKeyDown(e: KeyboardEvent): void {
    this.controllers.keyboardInteractionController.execute({ e });

    if (this.isPolygonMode) {
      const model = this.models.geojsonEditModel;

      if (e.code === "Delete" || e.code === "Backspace") {
        e.preventDefault();
        if (model.activeVertex) {
          this.controllers.polygonVertexDeleteController.execute({
            vertexRef: model.activeVertex,
          });
          this.render();
        } else if (model.selectedFeatureIndex !== null) {
          this.controllers.polygonDeleteController.execute({
            featureIndex: model.selectedFeatureIndex,
          });
          this.render();
        }
      } else if (e.code === "Escape") {
        model.selectedFeatureIndex = null;
        model.activeVertex = null;
        model.candidateVertex = null;
        model.candidateEdge = null;
        this.render();
      }
    }
  }

  onKeyUp(e: KeyboardEvent): void {
    this.controllers.keyboardInteractionController.execute({ e });
  }

  onDoubleClick(_e: React.MouseEvent<Element>): void {
    if (!this.isPolygonMode) return;
    if (this.models.geojsonEditModel.candidateEdge) {
      this.controllers.polygonVertexAddController.execute();
      this.render();
    }
  }

  onWheel(e: WheelEvent): void {
    if (!this.models.editorStateModel.isLoaded) return;
    this.controllers.mouseInteractionController.execute({
      e: e as unknown as React.WheelEvent<HTMLCanvasElement>,
    });
  }

  executeInteraction(e: React.MouseEvent<Element>): void {
    if (!this.models.editorStateModel.isLoaded) return;
    const { activeTool } = this.models.toolManagerModel;

    if (!activeTool) {
      // In polygon mode, clicking outside any polygon deselects
      if (this.isPolygonMode && e.type === "mousedown") {
        this.models.geojsonEditModel.selectedFeatureIndex = null;
        this.models.geojsonEditModel.activeVertex = null;
      }
      this.render();
      return;
    }

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
      case ToolType.POLYGON_VERTEX_MOVE:
        this.controllers.polygonVertexMoveController.execute({ e });
        break;
      case ToolType.POLYGON_MOVE:
        this.controllers.polygonMoveController.execute({ e });
        break;
      case ToolType.POLYGON_SELECT:
        this.controllers.polygonSelectController.execute({ e });
        break;
    }
    this.render();
  }

  render(): void {
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.clear();
    this.controllers.projectionController.execute();
    this.views.frameLayerView.render();
    this.views.polygonLayerView.render();
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

  getCursor(): string {
    if (!this.models.editorStateModel.isLoaded) return "default";

    const tool = this.models.toolManagerModel.candidateTool;
    const handle = this.models.imageTransformToolModel.candidateHandle;
    const dragStart = this.models.dragInteractionModel.dragStartWorldPosition;

    // Polygon tool cursors
    if (tool === ToolType.POLYGON_VERTEX_MOVE) return "pointer";
    if (tool === ToolType.POLYGON_MOVE) return "move";
    if (tool === ToolType.POLYGON_SELECT) return "pointer";

    if (!tool) {
      if (this.isPolygonMode) return "default";
      if (dragStart) return "grabbing";
      return "grab";
    }
    if (tool === ToolType.IMAGE_CREATE) return "crosshair";
    if (tool === ToolType.IMAGE_MOVE) return "move";
    if (tool === ToolType.IMAGE_RESIZE || tool === ToolType.IMAGE_ROTATE) {
      if (!handle) return "grab";
      return this._getCursorForHandle(handle);
    }
    return "grab";
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

  // Getters for external access
  get isLoaded(): boolean {
    return this.models.editorStateModel.isLoaded;
  }

  get isInitialized(): boolean {
    return this.models.editorStateModel.isInitialized;
  }

  get isSpaceHeld(): boolean {
    return this.models.keyboardInteractionModel.spaceHeld;
  }

  get isTransformActive(): boolean {
    return this.models.transformSessionModel.isActive;
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
  }

  /**
   * Compute the screen corners of the image as currently displayed on the canvas.
   * Derives from buffer dimensions, leftTop position, navigation offset and scale.
   */
  getScreenCorners(): ScreenCorners | null {
    const { width, height, leftTop } = this.models.imageBufferModel;
    if (!width || !height) return null;

    const { offset, scale } = this.models.navigationModel;
    const toScreen = (worldPoint: Point): Point =>
      getCanvasRelativePositionFromWorldPoint(worldPoint, offset, scale);

    return {
      corner1: toScreen({ x: leftTop.x, y: leftTop.y }),                  // top-left
      corner2: toScreen({ x: leftTop.x + width, y: leftTop.y }),           // top-right
      corner3: toScreen({ x: leftTop.x, y: leftTop.y + height }),          // bottom-left
      corner4: toScreen({ x: leftTop.x + width, y: leftTop.y + height }), // bottom-right
    };
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
