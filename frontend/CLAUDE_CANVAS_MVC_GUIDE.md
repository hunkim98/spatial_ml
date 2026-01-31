# Canvas MVC Architecture Guide

This document describes the MVC (Model-View-Controller) architecture used in the canvas editor (`src/canvas/clipper/`). **All AI coding assistants must follow these patterns.**

## Core Principles

1. **Models store data only** - No logic unless absolutely necessary
2. **Views render only** - No state changes, no business logic
3. **Controllers contain all logic** - Event handling, calculations, state updates
4. **Editor is a thin coordinator** - Delegates to controllers, minimal logic

---

## Directory Structure

```
src/canvas/clipper/
├── model/           # Data storage
│   ├── layers/      # Canvas layer models (element, ctx)
│   ├── tools/       # Tool state models
│   └── *.ts         # Other state models
├── view/            # Rendering
├── controller/      # All logic
├── actions/         # Action type definitions
├── events/          # Event type definitions
├── types/           # Type definitions
├── utils/           # Pure utility functions
└── editor.ts        # Thin coordinator
```

---

## Models (`model/`)

Models are **data containers only**. They store state and provide getters/setters.

### DO:
- Store primitive values, objects, and references
- Provide getters and setters
- Have a `reset()` method to restore initial state
- Extend `IModel` or `ILayerModel` base classes

### DO NOT:
- Perform calculations
- Call other models
- Call views or controllers
- Handle events
- Contain conditional business logic

### Example - Good Model:

```typescript
export class NavigationModel extends IModel<NavigationModelType> {
  private _scale: number;
  private _offset: Point;

  constructor(props: NavigationModelType) {
    super();
    this._scale = props.scale;
    this._offset = props.offset;
  }

  get scale(): number {
    return this._scale;
  }

  set scale(value: number) {
    // Simple clamping is OK - it's data validation, not business logic
    if (value > this._maxScale) value = this._maxScale;
    if (value < this._minScale) value = this._minScale;
    this._scale = value;
  }

  reset() {
    this._scale = 1;
    this._offset = { x: 0, y: 0 };
  }
}
```

### Example - Bad Model (DO NOT DO THIS):

```typescript
// BAD: Model should not contain logic
export class NavigationModel {
  centerOnImage(imageModel: ImageModel) {
    // BAD: This logic belongs in a controller
    const scale = Math.min(
      this.canvasWidth / imageModel.width,
      this.canvasHeight / imageModel.height
    );
    this._scale = scale;
  }
}
```

### Model Categories:

1. **Layer Models** (`model/layers/`) - Canvas elements with `element`, `ctx`, `width`, `height`
2. **Tool Models** (`model/tools/`) - Tool-specific state (e.g., clip rect position)
3. **State Models** - Editor state, navigation, history, mouse control
4. **Data Models** - Pure data like `ImageModel` (image, blob, dimensions)

---

## Views (`view/`)

Views **render only**. They read from models and draw to canvas.

### DO:
- Read from models (read-only access)
- Draw to canvas using `ctx`
- Have `render()` and `clear()` methods
- Extend `IView` base class

### DO NOT:
- Modify model state
- Contain business logic
- Handle events
- Call controllers
- Make decisions about what to render (models decide state, views just render it)

### Example - Good View:

```typescript
export class PdfLayerView extends IView<Models> {
  render(): void {
    const { ctx } = this.models.pdfLayerModel;
    const { image, leftTop, width, height } = this.models.imageModel;
    const { offset, scale } = this.models.navigationModel;

    if (!image) return;

    // Convert world to canvas coordinates
    const canvasPoint = getCanvasRelativePositionFromWorldPoint(
      leftTop, offset, scale
    );

    ctx.save();
    ctx.drawImage(image, canvasPoint.x, canvasPoint.y, width * scale, height * scale);
    ctx.restore();
  }

  clear(): void {
    const { element, ctx } = this.models.pdfLayerModel;
    ctx.clearRect(0, 0, element.width, element.height);
  }
}
```

### Example - Bad View (DO NOT DO THIS):

```typescript
// BAD: View should not modify state or contain logic
export class PdfLayerView {
  render(): void {
    // BAD: View should not modify model state
    if (this.models.imageModel.width === 0) {
      this.models.editorStatusModel.isLoaded = false;
      return;
    }

    // BAD: View should not calculate navigation
    const scale = this.calculateBestFitScale();
    this.models.navigationModel.scale = scale;
  }
}
```

---

## Controllers (`controller/`)

Controllers contain **all logic**. They handle events, update models, and trigger view renders.

### DO:
- Handle all business logic
- Read and write to models
- Call view `render()` and `clear()` methods
- Use utility functions for calculations
- Extend `BaseController` class
- Define typed `ExecuteParams` for input

### DO NOT:
- Store state (use models for that)
- Directly manipulate canvas (use views for that)
- Handle multiple unrelated concerns (create separate controllers)

### Example - Good Controller:

```typescript
type Models = Pick<ClipperModel, "pdfLayerModel" | "imageModel" | "navigationModel">;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;
type ExecuteParams = { padding?: number };

export class ImageUpdateController extends BaseController<Models, Views, ExecuteParams> {
  execute(params: ExecuteParams = {}): void {
    const { padding = 0.9 } = params;

    const { width: imageWidth, height: imageHeight } = this.models.imageModel;
    const { element } = this.models.pdfLayerModel;

    if (imageWidth === 0 || imageHeight === 0) return;

    // Calculate scale to fit
    const scaleX = (element.width * padding) / imageWidth;
    const scaleY = (element.height * padding) / imageHeight;
    const scale = Math.min(scaleX, scaleY);

    // Calculate centered offset
    const offsetX = (element.width - imageWidth * scale) / 2;
    const offsetY = (element.height - imageHeight * scale) / 2;

    // Update models
    this.models.navigationModel.scale = scale;
    this.models.navigationModel.offset = { x: offsetX, y: offsetY };

    // Trigger render
    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }
}
```

### Controller Naming:

- `PanZoomController` - Handles pan and zoom interactions
- `ImageUpdateController` - Handles image load/update events
- `MoveController` - Handles moving elements
- `ResizeController` - Handles resizing elements
- `HitTestController` - Handles hit detection
- `UndoController` / `RedoController` - Handles history

---

## Editor (`editor.ts`)

The editor is a **thin coordinator**. It creates models, views, and controllers, then delegates all work.

### DO:
- Create and wire up models, views, controllers
- Expose public event handlers that delegate to controllers
- Expose public getters for state
- Keep methods short (delegate to controllers)

### DO NOT:
- Contain business logic (use controllers)
- Directly manipulate canvas (use views)
- Store computed state (use models)

### Example - Good Editor Pattern:

```typescript
export class ClipperEditor {
  // Delegate to controller
  onWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    e.preventDefault();
    this.controllers.panZoomController.execute({ e });
  }

  // Delegate to controller
  async load(): Promise<void> {
    this.models.editorStatusModel.isLoading = true;
    await this._loadPdf();
    this.models.editorStatusModel.isLoading = false;
    this.models.editorStatusModel.isLoaded = true;

    // Delegate centering to controller
    this.controllers.imageUpdateController.execute({});
  }
}
```

### Example - Bad Editor Pattern (DO NOT DO THIS):

```typescript
// BAD: Editor should not contain this logic
export class ClipperEditor {
  onWheel(e: React.WheelEvent): void {
    // BAD: This logic belongs in PanZoomController
    if (e.ctrlKey) {
      const zoom = 1 - e.deltaY / 100;
      let newScale = this.models.navigationModel.scale * zoom;
      // ... 20 more lines of zoom logic
    } else {
      // ... 10 more lines of pan logic
    }
  }
}
```

---

## Utilities (`utils/`)

Utilities are **pure functions** with no side effects.

### DO:
- Create pure functions (same input = same output)
- Handle coordinate transformations
- Handle math operations
- Keep functions small and focused

### DO NOT:
- Access models, views, or controllers
- Have side effects
- Store state

### Example:

```typescript
// utils/math.ts
export const addPoints = (a: Point, b: Point): Point => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

// utils/event.ts
export const getCanvasRelativePositionFromWorldPoint = (
  worldPoint: Point,
  canvasOffset: Point,
  canvasScale: number
): Point => ({
  x: worldPoint.x * canvasScale + canvasOffset.x,
  y: worldPoint.y * canvasScale + canvasOffset.y,
});
```

---

## Decision Guide: Where Does This Code Go?

| If you need to... | Put it in... |
|-------------------|--------------|
| Store a value | Model |
| Draw something | View |
| Calculate something | Controller (or utility if pure) |
| Handle an event | Controller (called from Editor) |
| Coordinate multiple controllers | Editor |
| Transform coordinates | Utility |

---

## Adding New Features

### Adding a New Controller:

1. Create `controller/myController.ts`
2. Define `Models`, `Views`, `ExecuteParams` types
3. Extend `BaseController`
4. Implement `execute(params)`
5. Add to `controller/index.ts`
6. Create instance in `editor._createControllers()`
7. Call from editor event handlers

### Adding a New Model:

1. Create `model/myModel.ts`
2. Define interface and class
3. Extend `IModel` or `ILayerModel`
4. Add to `model/index.ts` (ClipperModel type)
5. Create instance in `editor._createModels()`

### Adding a New View:

1. Create `view/myView.ts`
2. Define `Models` type
3. Extend `IView`
4. Implement `render()` and `clear()`
5. Add to `view/index.ts`
6. Create instance in `editor._createViews()`

---

## Summary

| Component | Responsibility | State | Logic |
|-----------|---------------|-------|-------|
| Model | Data storage | YES | NO |
| View | Rendering | NO | NO |
| Controller | Business logic | NO | YES |
| Editor | Coordination | NO | Minimal |
| Utility | Pure functions | NO | YES (pure) |

**Remember: When in doubt, put logic in a Controller.**
