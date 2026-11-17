// Latitude and longitude to UTM zone 43N (EPSG:32643), the map's ground coordinates, and
// back. Snyder's series on WGS 84; well under a meter of error across Bengaluru.

const A = 6378137;
const F = 1 / 298.257223563;
const K0 = 0.9996;
const CENTRAL_MERIDIAN = 75;
const FALSE_EASTING = 500000;

const E2 = F * (2 - F);
const EP2 = E2 / (1 - E2);
const E4 = E2 * E2;
const E6 = E4 * E2;
const ARC_PER_RADIAN = A * (1 - E2 / 4 - (3 * E4) / 64 - (5 * E6) / 256);

function meridianArc(phi: number): number {
  return (
    ARC_PER_RADIAN * phi -
    A *
      (((3 * E2) / 8 + (3 * E4) / 32 + (45 * E6) / 1024) * Math.sin(2 * phi) -
        ((15 * E4) / 256 + (45 * E6) / 1024) * Math.sin(4 * phi) +
        ((35 * E6) / 3072) * Math.sin(6 * phi))
  );
}

export function toUtm(lon: number, lat: number): [number, number] {
  const phi = (lat * Math.PI) / 180;
  const lambda = ((lon - CENTRAL_MERIDIAN) * Math.PI) / 180;
  const sin = Math.sin(phi);
  const cos = Math.cos(phi);
  const tan = Math.tan(phi);
  const n = A / Math.sqrt(1 - E2 * sin * sin);
  const t = tan * tan;
  const c = EP2 * cos * cos;
  const a = lambda * cos;
  const easting =
    FALSE_EASTING +
    K0 *
      n *
      (a + ((1 - t + c) * a ** 3) / 6 + ((5 - 18 * t + t * t + 72 * c - 58 * EP2) * a ** 5) / 120);
  const northing =
    K0 *
    (meridianArc(phi) +
      n *
        tan *
        ((a * a) / 2 +
          ((5 - t + 9 * c + 4 * c * c) * a ** 4) / 24 +
          ((61 - 58 * t + t * t + 600 * c - 330 * EP2) * a ** 6) / 720));
  return [easting, northing];
}

export function fromUtm(easting: number, northing: number): [number, number] {
  const mu = northing / K0 / ARC_PER_RADIAN;
  const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
  const phi1 =
    mu +
    ((3 * e1) / 2 - (27 * e1 ** 3) / 32) * Math.sin(2 * mu) +
    ((21 * e1 * e1) / 16 - (55 * e1 ** 4) / 32) * Math.sin(4 * mu) +
    ((151 * e1 ** 3) / 96) * Math.sin(6 * mu) +
    ((1097 * e1 ** 4) / 512) * Math.sin(8 * mu);
  const sin = Math.sin(phi1);
  const cos = Math.cos(phi1);
  const tan = Math.tan(phi1);
  const c = EP2 * cos * cos;
  const t = tan * tan;
  const n = A / Math.sqrt(1 - E2 * sin * sin);
  const r = (A * (1 - E2)) / (1 - E2 * sin * sin) ** 1.5;
  const d = (easting - FALSE_EASTING) / (n * K0);
  const phi =
    phi1 -
    ((n * tan) / r) *
      ((d * d) / 2 -
        ((5 + 3 * t + 10 * c - 4 * c * c - 9 * EP2) * d ** 4) / 24 +
        ((61 + 90 * t + 298 * c + 45 * t * t - 252 * EP2 - 3 * c * c) * d ** 6) / 720);
  const lambda =
    (d -
      ((1 + 2 * t + c) * d ** 3) / 6 +
      ((5 - 2 * c + 28 * t - 3 * c * c + 8 * EP2 + 24 * t * t) * d ** 5) / 120) /
    cos;
  return [CENTRAL_MERIDIAN + (lambda * 180) / Math.PI, (phi * 180) / Math.PI];
}
