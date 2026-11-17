import { fromUtm, toUtm } from "./utm";

// Where a view's image sits on the ground: image pixels = matrix × ground meters + offset.
export interface Frame {
  matrix: [number, number, number, number];
  x_offset: number;
  y_offset: number;
}

export interface View extends Frame {
  pyramid: string;
}

// The view whose screen-up is true north; the site opens in it, and a link without a view
// means it.
export const NORTH_UP_VIEW = "315";

// The views the site shows, in turning order: each step turns the scene clockwise.
export function viewOrder(views: Record<string, View>): string[] {
  return Object.keys(views).sort((a, b) => Number(a) - Number(b));
}

export function northAngle(view: View): number {
  const [a, b] = view.matrix;
  return (Math.atan2(b, a) * 180) / Math.PI;
}

function toGround(x: number, y: number, frame: Frame): [number, number] {
  const [a, b, d, e] = frame.matrix;
  const screenX = x - frame.x_offset;
  const screenY = y - frame.y_offset;
  const determinant = a * e - b * d;
  return [(e * screenX - b * screenY) / determinant, (a * screenY - d * screenX) / determinant];
}

function fromGround(groundX: number, groundY: number, frame: Frame): [number, number] {
  const [a, b, d, e] = frame.matrix;
  return [
    Math.round(a * groundX + b * groundY + frame.x_offset),
    Math.round(d * groundX + e * groundY + frame.y_offset),
  ];
}

export function convertPoint(x: number, y: number, from: Frame, to: Frame): [number, number] {
  return fromGround(...toGround(x, y, from), to);
}

// A place on the earth as a view's image pixels, and back. Links carry longitude and
// latitude, so they outlive a rebuild and a wider map.
export function toImage(frame: Frame, lon: number, lat: number): [number, number] {
  return fromGround(...toUtm(lon, lat), frame);
}

export function toLonLat(frame: Frame, x: number, y: number): [number, number] {
  return fromUtm(...toGround(x, y, frame));
}
