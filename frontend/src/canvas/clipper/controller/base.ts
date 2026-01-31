import { ClipperEvent, ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { IModel } from "../model/base";
import { ClipperView } from "../view";
import { IView } from "../view/base";

export abstract class BaseController<
  M extends Partial<ClipperModel>,
  V extends Partial<ClipperView>,
  P,
> {
  models: M;
  views: V;
  listeners: ClipperEventListeners;

  constructor(
    models: ClipperModel,
    views: ClipperView,
    listeners: ClipperEventListeners
  ) {
    const neededModelKeys = Object.keys(models) as Array<keyof ClipperModel>;
    const neededViewKeys = Object.keys(views) as Array<keyof ClipperView>;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof ClipperModel]: IModel<M> }
    ) as M;
    this.views = neededViewKeys.reduce(
      (viewKeys, key) => {
        viewKeys[key] = views[key] as unknown;
        return viewKeys;
      },
      {} as { [key in keyof ClipperView]: unknown }
    ) as V;
    this.listeners = listeners;
  }

  abstract execute(params: P): void;

  dispatchEvent(eventName: ClipperEvent) {
    const listeners = this.listeners[eventName];

    if (listeners) {
      listeners.forEach((listener) =>
        listener(this.models as Partial<ClipperModel>)
      );
    }
  }
}
