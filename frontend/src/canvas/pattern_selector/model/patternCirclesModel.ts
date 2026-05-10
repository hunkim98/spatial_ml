import { IModel } from "./base";
import { PatternCircle, Point } from "../types";

export interface PatternCirclesModelType {
  circles: PatternCircle[];
}

export class PatternCirclesModel
  extends IModel<PatternCirclesModelType>
  implements PatternCirclesModelType
{
  private _circles: PatternCircle[];
  private _isCreating: boolean;
  private _creatingCenter: Point | null;
  private _creatingRadius: number;

  constructor() {
    super();
    this._circles = [];
    this._isCreating = false;
    this._creatingCenter = null;
    this._creatingRadius = 0;
  }

  get circles(): PatternCircle[] {
    return this._circles;
  }
  set circles(circles: PatternCircle[]) {
    this._circles = circles;
  }

  get isCreating(): boolean {
    return this._isCreating;
  }
  set isCreating(value: boolean) {
    this._isCreating = value;
  }

  get creatingCenter(): Point | null {
    return this._creatingCenter;
  }
  set creatingCenter(center: Point | null) {
    this._creatingCenter = center;
  }

  get creatingRadius(): number {
    return this._creatingRadius;
  }
  set creatingRadius(radius: number) {
    this._creatingRadius = radius;
  }

  addCircle(circle: PatternCircle): void {
    this._circles = [...this._circles, circle];
  }

  removeCircle(id: string): void {
    this._circles = this._circles.filter((c) => c.id !== id);
  }

  renameCircle(id: string, name: string): void {
    this._circles = this._circles.map((c) =>
      c.id === id ? { ...c, name } : c
    );
  }

  reset() {
    this._circles = [];
    this._isCreating = false;
    this._creatingCenter = null;
    this._creatingRadius = 0;
  }
}
