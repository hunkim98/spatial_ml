import { CanvasEvent, CanvasEventListeners } from "../events";
import { CanvasModel } from "../model";
import { IModel } from "../model/base";
import { CanvasView } from "../view";
import { IView } from "../view/base";

export abstract class BaseController<
  M extends Partial<CanvasModel>,
  V extends Partial<CanvasView>,
  P,
> {
  models: M;
  views: V;
  listeners: CanvasEventListeners;

  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    const neededModelKeys = Object.keys(models) as Array<keyof CanvasModel>;
    const neededViewKeys = Object.keys(views) as Array<keyof CanvasView>;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof CanvasModel]: IModel<M> }
    ) as M;
    this.views = neededViewKeys.reduce(
      (viewKeys, key) => {
        viewKeys[key] = views[key] as IView<M>;
        return viewKeys;
      },
      {} as { [key in keyof CanvasView]: IView<M> }
    ) as V;
    // we should directly inherit the listeners from main parent class that connects the controller and model
    this.listeners = listeners;
  }

  abstract execute(params: P): void;

  dispatchEvent(eventName: CanvasEvent) {
    const listeners = this.listeners[eventName];

    if (listeners) {
      listeners.forEach((listener) =>
        listener(this.models as Partial<CanvasModel>)
      );
    }
  }
}
