import { ClipperModel } from "../model";

export enum ClipperEvent {
  CLIP_CHANGED = "CLIP_CHANGED",
  MODE_CHANGED = "MODE_CHANGED",
}

export type ClipperEventHandler = (args: Partial<ClipperModel>) => void;

export type ClipperEventListeners = {
  [key in ClipperEvent]?: Array<ClipperEventHandler>;
};
