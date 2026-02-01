export function preprocessImageForCanvas(
  desiredMaxWidth: number,
  desiredMaxHeight: number,
  imageWidth: number,
  imageHeight: number
) {
  const isWidthResizeCriterion =
    imageWidth / desiredMaxWidth > imageHeight / desiredMaxHeight;
  const resizeRatio = isWidthResizeCriterion
    ? desiredMaxWidth / imageWidth
    : desiredMaxHeight / imageHeight;
  const resizedImageWidth = imageWidth * resizeRatio;
  const resizedImageHeight = imageHeight * resizeRatio;

  return {
    resizedImageWidth,
    resizedImageHeight,
    resizeRatio,
  };
}

export const getInitialOffsetForImage = (
  imageWidth: number,
  imageHeight: number,
  canvasWidth: number,
  canvasHeight: number,
  scale: number
) => {
  const canvasMiddlePoint = { x: canvasWidth / 2, y: canvasHeight / 2 };

  return {
    x: (canvasMiddlePoint.x - imageWidth / 2) / scale,
    y: (canvasMiddlePoint.y - imageHeight / 2) / scale,
  };
};
