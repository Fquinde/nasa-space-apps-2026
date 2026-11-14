/**
 * TERRAIN-X: Contratos y tipos para la interfaz de visualización planetaria
 * Versión de contrato 1.0 (NASA Space Apps 2026)
 */

export type CelestialBody = 'Moon' | 'Earth' | 'Mars';

export interface GeoCoordinates {
  latitude: number;   // -90 a +90
  longitude: number;  // -180 a +180
  altitude_m?: number;
  label?: string;
}

export interface AnalogSite {
  id: string;
  name: string;
  target_body: 'Moon' | 'Mars';
  coordinates: GeoCoordinates;
  region: string;
  country: string;
  geological_features: string[];
  scientific_justification: string;
  similarity_score: number; // 0 - 100%
  coverage_percentage: number;
  surface_area_km2?: number;
  avg_temp_c?: string;
  dominant_terrain?: string;
  gravity_ratio?: number;
  sources: string[];
  status: 'validated' | 'candidate' | 'local_only';
}

export interface PlanetMetrics {
  name: string;
  subtitle: string;
  radius_km: number;
  surface_area_mkm2: number;
  gravity_g: number;
  gravity_percentage_earth: number;
  avg_temp_range: string;
  dominant_terrain: string;
  overview_text: string;
  terrain_text: string;
  geology_text: string;
  data_text: string;
}

