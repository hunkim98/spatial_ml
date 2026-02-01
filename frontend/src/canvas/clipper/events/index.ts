import { ClipperModel } from "../model";

export enum ClipperEvent {
  CLIP_CHANGED = "CLIP_CHANGED",
  MODE_CHANGED = "MODE_CHANGED",
  INTERACTION_MOUSE_DOWN = "INTERACTION_MOUSE_DOWN",
  INTERACTION_MOUSE_MOVE = "INTERACTION_MOUSE_MOVE",
  INTERACTION_MOUSE_UP = "INTERACTION_MOUSE_UP",
}

export type ClipperEventHandler = (args: Partial<ClipperModel>) => void;

export type ClipperEventListeners = {
  [key in ClipperEvent]?: Array<ClipperEventHandler>;
};
