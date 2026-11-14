import { describe, it, expect } from 'vitest';
import { latLonToVector3 } from '../src/babylon/targetPin';
import { generateRandomAnalogCoordinates, ANALOG_DATABASE, PLANET_METRICS } from '../src/data/analogs';

describe('Cálculos Geográficos y de Esfera en BabylonJS', () => {
  const radius = 2.8;

  it('Debe convertir el Polo Norte (90° N, 0° E) a coordenadas 3D correctas (Y positivo)', () => {
    const v = latLonToVector3(90, 0, radius);
    expect(v.y).toBeCloseTo(radius, 2);
    expect(Math.abs(v.x)).toBeCloseTo(0, 2);
    expect(Math.abs(v.z)).toBeCloseTo(0, 2);
  });

  it('Debe convertir el Polo Sur (-90° S, 0° E) a coordenadas 3D correctas (Y negativo)', () => {
    const v = latLonToVector3(-90, 0, radius);
    expect(v.y).toBeCloseTo(-radius, 2);
    expect(Math.abs(v.x)).toBeCloseTo(0, 2);
    expect(Math.abs(v.z)).toBeCloseTo(0, 2);
  });

  it('Debe situar un punto sobre la superficie exactamente a la distancia del radio de la Tierra', () => {
    const lat = 28.1234;
    const lon = -15.4321;
    const v = latLonToVector3(lat, lon, radius);
    const computedRadius = Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    expect(computedRadius).toBeCloseTo(radius, 4);
  });
});

describe('Generador de Coordenadas Aleatorias de Análogos Terrestres', () => {
  it('Debe generar coordenadas válidas para análogos lunares', () => {
    const result = generateRandomAnalogCoordinates('Moon');
    expect(result.site.target_body).toBe('Moon');
    expect(result.coordinates.latitude).toBeGreaterThanOrEqual(-90);
    expect(result.coordinates.latitude).toBeLessThanOrEqual(90);
    expect(result.coordinates.longitude).toBeGreaterThanOrEqual(-180);
    expect(result.coordinates.longitude).toBeLessThanOrEqual(180);
    expect(result.site.name).toBeDefined();
    expect(result.site.similarity_score).toBeGreaterThan(0);
  });

  it('Debe generar coordenadas válidas para análogos marcianos', () => {
    const result = generateRandomAnalogCoordinates('Mars');
    expect(result.site.target_body).toBe('Mars');
    expect(result.coordinates.latitude).toBeGreaterThanOrEqual(-90);
    expect(result.coordinates.latitude).toBeLessThanOrEqual(90);
    expect(result.coordinates.longitude).toBeGreaterThanOrEqual(-180);
    expect(result.coordinates.longitude).toBeLessThanOrEqual(180);
    expect(result.site.scientific_justification).toBeDefined();
  });

  it('Debe generar variación aleatoria entre ejecuciones sucesivas', () => {
    const run1 = generateRandomAnalogCoordinates('Mars');
    const run2 = generateRandomAnalogCoordinates('Mars');
    const isDifferent = run1.coordinates.latitude !== run2.coordinates.latitude ||
                        run1.coordinates.longitude !== run2.coordinates.longitude ||
                        run1.site.id !== run2.site.id;
    expect(isDifferent).toBe(true);
  });
});

describe('Catálogo de Datos Científicos (Fidelidad NASA/ESA)', () => {
  it('Todos los sitios del catálogo deben tener fuentes contrastadas y estado válido', () => {
    expect(ANALOG_DATABASE.length).toBeGreaterThanOrEqual(6);
    ANALOG_DATABASE.forEach(site => {
      expect(site.sources.length).toBeGreaterThan(0);
      expect(['validated', 'candidate', 'local_only']).toContain(site.status);
      expect(site.similarity_score).toBeGreaterThan(50);
    });
  });

  it('Las métricas de Luna y Marte deben tener valores astronómicos reales', () => {
    expect(PLANET_METRICS.Moon.radius_km).toBe(1737);
    expect(PLANET_METRICS.Mars.radius_km).toBe(3390);
    expect(PLANET_METRICS.Moon.gravity_g).toBe(0.165);
    expect(PLANET_METRICS.Mars.gravity_g).toBe(0.38);
  });
});

