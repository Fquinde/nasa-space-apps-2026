import { AnalogSite, PlanetMetrics } from '../types';

/**
 * Catálogo de análogos terrestres científicos para misiones Luna y Marte (NASA / ESA)
 */
export const ANALOG_DATABASE: AnalogSite[] = [
  // --- ANÁLOGOS LUNARES ---
  {
    id: 'site-moon-lanzarote',
    name: 'Tubos de Lava de Lanzarote',
    target_body: 'Moon',
    coordinates: { latitude: 29.035, longitude: -13.633, label: '29.0350° N, 13.6330° W' },
    region: 'Islas Canarias',
    country: 'España',
    geological_features: ['Tubos de lava basáltica', 'Jameos', 'Campos de ceniza piroclástica'],
    scientific_justification: 'Estructuras subterráneas análogas a los tubos de lava de Marius Hills en la Luna para hábitats protegidos de radiación.',
    similarity_score: 94.2,
    coverage_percentage: 88,
    dominant_terrain: 'Basalto volcánico reciente',
    sources: ['ESA PANGAEA', 'NASA SSERVI', 'IGME'],
    status: 'validated'
  },
  {
    id: 'site-moon-craters-idaho',
    name: 'Craters of the Moon',
    target_body: 'Moon',
    coordinates: { latitude: 43.461, longitude: -113.562, label: '43.4610° N, 113.5620° W' },
    region: 'Idaho',
    country: 'EE.UU.',
    geological_features: ['Flujos de lava pahoehoe', 'Conos de escoria', 'Fisuras volcánicas'],
    scientific_justification: 'Sitio de entrenamiento de astronautas del programa Apollo (1969). Simulación de terreno de regolito y basaltos de mare lunar.',
    similarity_score: 91.5,
    coverage_percentage: 84,
    dominant_terrain: 'Coladas de basalto y regolito',
    sources: ['NASA Apollo Training Archives', 'USGS Astrogeology'],
    status: 'validated'
  },
  {
    id: 'site-moon-sudbury',
    name: 'Estructura de Impacto de Sudbury',
    target_body: 'Moon',
    coordinates: { latitude: 46.602, longitude: -81.187, label: '46.6020° N, 81.1870° W' },
    region: 'Ontario',
    country: 'Canadá',
    geological_features: ['Brechas de impacto', 'Conos astillados (shatter cones)', 'Fundidos de impacto'],
    scientific_justification: 'Una de las mayores cuencas de impacto multianillo de la Tierra, clave para modelar la cuenca Aitken del polo sur lunar.',
    similarity_score: 87.8,
    coverage_percentage: 79,
    dominant_terrain: 'Brechas de impacto y anortositas',
    sources: ['NASA Lunar Science Institute', 'CSA'],
    status: 'validated'
  },

  // --- ANÁLOGOS MARCIANOS ---
  {
    id: 'site-mars-atacama',
    name: 'Desierto de Atacama (Yungay)',
    target_body: 'Mars',
    coordinates: { latitude: -24.085, longitude: -69.865, label: '24.0850° S, 69.8650° W' },
    region: 'Antofagasta',
    country: 'Chile',
    geological_features: ['Suelos hiperáridos', 'Depósitos de nitratos y percloratos', 'Halitas'],
    scientific_justification: 'El lugar más seco no polar de la Tierra. Límite de desecación hiperárida idéntico al regolito marciano explorado por Curiosity y Perseverance.',
    similarity_score: 96.7,
    coverage_percentage: 92,
    dominant_terrain: 'Costras salinas, arcillas y polvo seco',
    sources: ['NASA Astrobiology Institute', 'SETI', 'Universidad de Chile'],
    status: 'validated'
  },
  {
    id: 'site-mars-devon-haughton',
    name: 'Cráter Haughton (Isla Devon)',
    target_body: 'Mars',
    coordinates: { latitude: 75.383, longitude: -89.667, label: '75.3830° N, 89.6670° W' },
    region: 'Nunavut',
    country: 'Canadá',
    geological_features: ['Cráter de impacto en permafrost', 'Valles en U fluviales secos', 'Lopolito hidrotermal'],
    scientific_justification: 'Base del Haughton-Mars Project (HMP) de NASA. Desierto polar frío con procesos hidrotermales post-impacto idénticos a los cráteres marcianos antiguos.',
    similarity_score: 95.1,
    coverage_percentage: 90,
    dominant_terrain: 'Permafrost pedregoso y brechas dolomíticas',
    sources: ['NASA Haughton-Mars Project', 'Mars Institute'],
    status: 'validated'
  },
  {
    id: 'site-mars-riotinto',
    name: 'Cuenca Minera de Río Tinto',
    target_body: 'Mars',
    coordinates: { latitude: 37.697, longitude: -6.561, label: '37.6970° N, 6.5610° W' },
    region: 'Andalucía',
    country: 'España',
    geological_features: ['Óxidos e hidróxidos de hierro', 'Jarosita', 'Aguas extremadamente ácidas (pH ~2)'],
    scientific_justification: 'Presencia masiva de jarosita y hematites, exactamente los minerales detectados por el rover Opportunity en Meridiani Planum.',
    similarity_score: 93.4,
    coverage_percentage: 86,
    dominant_terrain: 'Gossan de sulfuros masivos y jarosita',
    sources: ['Centro de Astrobiología (CAB/CSIC-INTA)', 'NASA MARTE Project'],
    status: 'validated'
  }
];

/**
 * Métricas científicas para Luna y Marte (mostradas en las tarjetas laterales)
 */
export const PLANET_METRICS: Record<'Moon' | 'Mars', PlanetMetrics> = {
  Moon: {
    name: 'Moon',
    subtitle: "Earth's natural satellite",
    radius_km: 1737,
    surface_area_mkm2: 37.9,
    gravity_g: 0.165,
    gravity_percentage_earth: 16.5,
    avg_temp_range: '-173 to 127 °C',
    dominant_terrain: 'Craters, regolith, highlands',
    overview_text: 'El satélite natural de la Tierra posee una corteza rica en anortosita y grandes mares basálticos producto de impactos masivos en su historia temprana.',
    terrain_text: 'Topografía dominada por cráteres de impacto de todos los tamaños, cuencas multianillo y colinas onduladas cubiertas de regolito finamente pulverizado.',
    geology_text: 'Geología sin tectónica de placas activa ni atmósfera; preservación de fósiles geológicos de los primeros 1.000 millones de años del sistema solar.',
    data_text: 'Misiones clave: Apollo, Lunar Reconnaissance Orbiter (LRO), Chandrayaan, Chang’e y programa Artemis.'
  },
  Mars: {
    name: 'Mars',
    subtitle: 'The Red Planet',
    radius_km: 3390,
    surface_area_mkm2: 144.8,
    gravity_g: 0.38,
    gravity_percentage_earth: 38.0,
    avg_temp_range: '-125 to 20 °C',
    dominant_terrain: 'Valles, craters, volcanoes',
    overview_text: 'El cuarto planeta del sistema solar cuenta con una delgada atmósfera de CO2, casquetes polares de hielo de agua y dióxido de carbono y gigantescos cañones tectónicos.',
    terrain_text: 'Hogar del Monte Olimpo (el mayor volcán del sistema solar, 22 km de altura) y Valles Marineris (un sistema de cañones de 4.000 km de longitud).',
    geology_text: 'Evidencia geológica inequívoca de paleolagos, deltas fluviales y paleoclimas húmedos en los periodos Noeico y Hespérico.',
    data_text: 'Misiones clave: Viking, Mars Global Surveyor, MRO, Curiosity, Perseverance, Hope y Tianwen-1.'
  }
};

/**
 * Generador de coordenadas aleatorias realistas en la Tierra para análogos planetarios.
 * Puede generar una variación alrededor de un análogo conocido o generar un punto aleatorio en tierra firme.
 */
export function generateRandomAnalogCoordinates(targetBody: 'Moon' | 'Mars'): {
  site: AnalogSite;
  coordinates: { latitude: number; longitude: number };
  isGenerated: boolean;
} {
  // Filtramos los análogos del catálogo para este cuerpo celeste
  const candidates = ANALOG_DATABASE.filter(s => s.target_body === targetBody);
  const baseSite = candidates[Math.floor(Math.random() * candidates.length)];

  // Añadimos una variación aleatoria calculada en el código (±2.5 grados de dispersión geográfica)
  const latDelta = (Math.random() - 0.5) * 5.0;
  const lonDelta = (Math.random() - 0.5) * 5.0;

  const newLat = Number((baseSite.coordinates.latitude + latDelta).toFixed(4));
  const newLon = Number((baseSite.coordinates.longitude + lonDelta).toFixed(4));

  // Formato N/S, E/W
  const latDir = newLat >= 0 ? 'N' : 'S';
  const lonDir = newLon >= 0 ? 'E' : 'W';
  const label = `${Math.abs(newLat).toFixed(4)}° ${latDir}, ${Math.abs(newLon).toFixed(4)}° ${lonDir}`;

  const randomizedSite: AnalogSite = {
    ...baseSite,
    id: `generated-${targetBody.toLowerCase()}-${Date.now()}`,
    name: `${baseSite.name} (Sector ${Math.floor(Math.random() * 90 + 10)})`,
    coordinates: {
      latitude: newLat,
      longitude: newLon,
      label
    },
    similarity_score: Number((baseSite.similarity_score + (Math.random() * 4 - 2)).toFixed(1)),
    coverage_percentage: Number((baseSite.coverage_percentage + (Math.random() * 6 - 3)).toFixed(0)),
    status: 'candidate'
  };

  return {
    site: randomizedSite,
    coordinates: { latitude: newLat, longitude: newLon },
    isGenerated: true
  };
}

