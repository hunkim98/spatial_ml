import { CanvasModel } from "../model";

export enum CanvasEvent {
  WHEEL_SCROLL = "WHEEL_SCROLL",
  MODE_CHANGED = "MODE_CHANGED",
  TRANSFORM_CHANGED = "TRANSFORM_CHANGED",
  BOUNDS_CREATED = "BOUNDS_CREATED", // Fired when initial bounds are created via drag
}

export type CanvasEventHandler = (args: Partial<CanvasModel>) => void;

export type CanvasEventListeners = {
  [key in CanvasEvent]?: Array<CanvasEventHandler>;
};
