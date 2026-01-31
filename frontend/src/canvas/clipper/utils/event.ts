import { Point } from "../types/geometry";

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

  const rect = canvasElement.getBoundingClientRect();
  eventPoint.x -= rect.left;
  eventPoint.y -= rect.top;

  // Account for canvas resolution vs CSS size (DPR)
  const scaleX = canvasElement.width / rect.width;
  const scaleY = canvasElement.height / rect.height;

  return {
    x: eventPoint.x * scaleX,
    y: eventPoint.y * scaleY,
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
