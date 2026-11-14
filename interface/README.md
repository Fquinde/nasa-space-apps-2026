# TERRAIN-X | Prototipo de Interfaz 3D Planetaria (BabylonJS)
**NASA Space Apps Challenge 2026**

Plataforma de visualización científica y comparación de terrenos planetarios (**Luna** / **Marte**) con análogos terrestres reales, construida con **BabylonJS** para la escena 3D y **Leaflet / Esri World Imagery** para la cartografía satelital 2D de alta resolución.

---

## 🌟 Novedades y Mejoras Implementadas

### 1. Espacio Profundo Fotorrealista (Deep Space)
- **Cúpula estelar cósmica de 360°**: Incluye la banda de la Vía Láctea, nebulosas de gas interestelar con sutiles gradientes de color (azul, cian, púrpura) y miles de estrellas de diversas magnitudes astronómicas.
- **Sistema de partículas estelares 3D**: Estrellas tridimensionales independientes que proporcionan un auténtico efecto de **paralaje** al orbitar con la cámara.

### 2. Planetas con Texturas Fotorrealistas de la NASA
- **Tierra Fotorrealista**:
  - Textura difusa en alta definición de **NASA Blue Marble**.
  - **Mapa de normales (*Normal Bump Map*)**: Relieve real visible en cordilleras y montañas (Himalaya, Andes, Rocosas).
  - **Mapa especular (*Specular Ocean Map*)**: Los océanos reflejan intensamente la luz solar directa mientras que los continentes permanecen mate.
  - **Luces nocturnas de ciudades (*Earth Night Lights*)**: Visibles en el hemisferio nocturno en sombra.
  - **Capa de nubes independiente**: Gira a velocidad orbital propia con canales de transparencia y sombra suave.
  - **Atmósfera con dispersión de Rayleigh (*Fresnel Glow*)**: Brillo azul celeste concentrado en el borde del horizonte planetario.
- **Luna**: Superficie fotorrealista basada en la sonda LRO (*Lunar Reconnaissance Orbiter*) con sombras profundas en cráteres y mares de basalto.
- **Marte**: Textura global con relieve del cráter Olympus Mons, casquetes de hielo polar y la falla de Valles Marineris.

### 3. Inmersión Atmosférica y Transición a Mapa 2D
- **Zambullida Cinematográfica**: Al elegir Luna o Marte, el sistema genera coordenadas aleatorias de análogos geológicos y la cámara orbital acelera en picado penetrando la atmósfera.
- **Efecto de Reentrada**: Fricción de aire, estelas de vapor nuboso a alta velocidad, telemetría de altitud en tiempo real y sonido de zambullida (*whoosh*).
- **Cartografía Satelital 2D de Alta Definición**:
  - Al cruzar las nubes, la vista se disuelve suavemente en un **mapa satelital interactivo 2D** centrado exactamente en las coordenadas generadas.
  - Provisto por **Esri World Imagery** (imágenes satelitales reales de alta resolución para geología y terreno).
  - Baliza de radar pulsante georreferenciada sobre el análogo terrestre con ficha técnica del terreno.
  - Botón flotante **`🚀 Regresar a Órbita (3D)`**: Permite ascender de nuevo a través de las nubes y volver a la vista orbital en el espacio.

---

## 🚀 Arranque Rápido para Principiantes

Sitúate en la terminal dentro de esta carpeta:
```bash
cd "C:\Users\Elias Méndez\Desktop\github\nasa-space-apps-2026\interface"
```

### 1. Iniciar servidor de desarrollo
```bash
npm run dev
```

Abre en tu navegador:  
👉 **[http://localhost:3000](http://localhost:3000)**

---

## 🧪 Tests y Validación

Para ejecutar las pruebas unitarias automatizadas con **Vitest**:
```bash
npm test
```

Para generar la compilación de producción optimizada:
```bash
npm run build
```

---

## 🎮 Controles y Navegación

| Control | Descripción |
| :--- | :--- |
| **Tarjeta "Moon" o Selector "Moon"** | Genera coordenadas para análogo lunar y realiza la inmersión al mapa 2D. |
| **Tarjeta "Mars" o Selector "Mars"** | Genera coordenadas para análogo marciano e inicia el descenso al mapa 2D. |
| **Arrastrar ratón sobre la Tierra 3D** | Rota libremente la órbita de la cámara alrededor del globo y el espacio exterior. |
| **Rueda del ratón** | Control continuo de zoom orbital. |
| **Botón "Regresar a Órbita (3D)"** | Asciende desde el mapa satelital 2D de vuelta a la vista 3D en el espacio profundo. |
| **Botón de Mira Telescópica (HUD)** | Genera nuevas coordenadas aleatorias y vuelve a zambullirse en la Tierra. |
| **Botón Flecha (HUD)** | Restablece la vista orbital global. |
