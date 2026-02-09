import { Point } from "../types";

export const getWorldPointFromEvent = (
  event: React.MouseEvent | React.TouchEvent,
  canvasElement: HTMLCanvasElement,
  canvasOffset: Point,
  canvasScale: number
): Point => {
  const eventPoint = getEventRelativePositionToCanvas(event, canvasElement);

  return getWorldPointFromRelativePositionToCanvas(
    eventPoint,
    canvasOffset,
    canvasScale
  );
};

export const getWorldPointFromRelativePositionToCanvas = (
  relativePosition: Point,
  canvasOffset: Point,
  canvasScale: number
): Point => {
  return {
    x: (relativePosition.x - canvasOffset.x) / canvasScale,
    y: (relativePosition.y - canvasOffset.y) / canvasScale,
  };
};

export const getEventRelativePositionToCanvas = (
  event: React.MouseEvent | React.TouchEvent | React.WheelEvent,
  canvasElement: HTMLCanvasElement
): Point => {
  const eventPoint = {
    x: 0,
    y: 0,
  };

  // if 'clientX' and 'clientY' are in event it is a mouse event
  if ("clientX" in event && "clientY" in event) {
    eventPoint.x = event.clientX;
    eventPoint.y = event.clientY;
  } else {
    // this is for mobile
    eventPoint.x = event.touches[0].clientX;
    eventPoint.y = event.touches[0].clientY;
  }
  eventPoint.x -= canvasElement.getBoundingClientRect().left;
  eventPoint.y -= canvasElement.getBoundingClientRect().top;
  return {
    x: eventPoint.x,
    y: eventPoint.y,
  };
};

export const getCanvasRelativePositionFromWorldPoint = (
  worldPoint: Point,
  canvasOffset: Point,
  canvasScale: number
): Point => {
  return {
    x: worldPoint.x * canvasScale + canvasOffset.x,
    y: worldPoint.y * canvasScale + canvasOffset.y,
  };
};
