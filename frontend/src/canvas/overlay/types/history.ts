import { Location } from "./location";

export abstract class BaseHistoryItem<T> {
  state: T;
  static type: string;

  constructor(state: T) {
    this.state = state;
  }
}

export type ImageHistoryItemState = {
  tl: Location;
  tr: Location;
  br: Location;
  bl: Location;
};

export class ImageHistoryItem extends BaseHistoryItem<ImageHistoryItemState> {
  static type = "image";

  constructor(state: ImageHistoryItemState) {
    super(state);
  }
}

export type PolygonItemState = {
  polygons: Array<{
    points: Array<Location>;
  }>;
};

export class PolygonHistoryItem extends BaseHistoryItem<PolygonItemState> {
  static type = "polygon";

  constructor(state: PolygonItemState) {
    super(state);
  }
}
