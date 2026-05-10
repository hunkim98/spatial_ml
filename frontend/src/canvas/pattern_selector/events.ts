import { PatternSelectorModel } from "./model";

export enum PatternSelectorEvent {
  IMAGE_LOADED = "IMAGE_LOADED",
  PATTERN_ADDED = "PATTERN_ADDED",
  PATTERN_REMOVED = "PATTERN_REMOVED",
}

export type PatternSelectorEventHandler = (
  args: Partial<PatternSelectorModel>
) => void;

export type PatternSelectorEventListeners = {
  [key in PatternSelectorEvent]?: Array<PatternSelectorEventHandler>;
};
