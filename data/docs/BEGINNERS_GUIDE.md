# 🎓 TERRAIN-X Beginner's Manual: Geospatial Science, Python & Planetary Analogs

Welcome! If you are new to geospatial data science, Python, GIS, or planetary science, this guide will walk you through all core concepts from first principles without assuming any prior knowledge.

---

## 1. What is a DEM and a Raster?

Imagine taking a high-altitude photograph of a mountain. 
* A normal photo records **color** (Red, Green, Blue) for every pixel.
* A **Raster** is any 2D grid of numbers (like a spreadsheet with rows and columns of cells).
* A **Digital Elevation Model (DEM)** is a special raster where every pixel value is **altitude (height in meters)** above sea level or planetary datum.

```
DEM Grid Example (each number is height in meters):
+------+------+------+
| 102m | 105m | 110m |
+------+------+------+
| 101m | 104m | 108m |
+------+------+------+
|  99m | 102m | 105m |
+------+------+------+
```

---

## 2. What is a CRS (Coordinate Reference System)?

A globe is round, but computer screens and maps are flat. A **CRS** tells the computer how to translate coordinates on a sphere into positions on a flat grid.

### Geographic CRS (e.g. `EPSG:4326` / WGS84)
* Uses **Latitude and Longitude in degrees** (e.g., $29.15^\circ\text{ N}, -13.45^\circ\text{ W}$).
* **Crucial Beginner Warning:** Degrees are NOT equal in distance! 
  At the equator, $1^\circ$ of longitude is roughly $111\text{ km}$, but near the poles, $1^\circ$ shrinks to zero!
* **Golden Rule:** **NEVER calculate slope directly on degrees.** You will get nonsense. You must first project to a metric system.

### Projected CRS (e.g. UTM Zones / `EPSG:32628`)
* Projects a slice of the Earth onto a flat cylinder with coordinates measured in **METERS ($X$ and $Y$)**.
* Once your data is in meters, cell sizes $dx$ and $dy$ are physically meaningful ($30\text{m} \times 30\text{m}$), allowing accurate slope, area, and volume calculus.

### Planetary Datums (Moon and Mars)
* The Earth is an ellipsoid with an average radius of $\sim 6,371\text{ km}$.
* The Moon is much smaller (mean radius $R = 1,737.4\text{ km}$).
* Mars has a semi-major axis of $A = 3,396.2\text{ km}$.
* **Planetary Guard:** You cannot use `EPSG:4326` for a Moon or Mars crater. Extraterrestrial rasters must use IAU datums (such as `IAU_2015:30100` for the Moon and `IAU_2015:49900` for Mars).

---

## 3. NASA Data Ecosystem: CMR, PDS, and ODE

NASA provides petabytes of free scientific data, but it is organized across different centers:

1. **NASA CMR (Common Metadata Repository):**
   * The central catalog for all Earth science missions (Terra, Aqua, Landsat, Sentinel, ICESat).
   * Search for collections to dynamically get a `concept_id` without hardcoding old URLs.
2. **NASA POWER API:**
   * Global solar and meteorological data provided by NASA Langley. Useful for getting daily temperature and precipitation for any spot on Earth.
3. **NASA PDS (Planetary Data System):**
   * The official archive for deep-space and planetary missions (LRO, Curiosity, Perseverance, MGS).
4. **WUSTL ODE (Orbital Data Explorer):**
   * A service by Washington University in St. Louis that indexes PDS data by spatial coordinates (lat/lon) on Moon, Mars, Mercury, and Venus.
5. **NASA Trek (Moon Trek / Mars Trek):**
   * Interactive web map tile services (WMTS). Great for viewing maps in a browser, but remember: **WMTS tiles are 8-bit visual images, not metric elevation rasters!**

---

## 4. How TERRAIN-X Computes Terrain Roughness & Slope

### Horn's Finite-Difference Slope Formula
To find how steep a point is, the algorithm looks at a $3 \times 3$ moving window of neighbor elevation cells:
$$\left[\begin{matrix} a & b & c \\ d & e & f \\ g & h & i \end{matrix}\right]$$
* West-to-East slope:
  $$\frac{\partial z}{\partial x} = \frac{(c + 2f + i) - (a + 2d + g)}{8 \cdot \Delta x}$$
* South-to-North slope:
  $$\frac{\partial z}{\partial y} = \frac{(g + 2h + i) - (a + 2b + c)}{8 \cdot \Delta y}$$
* Slope in degrees:
  $$\text{Slope}^\circ = \arctan\left(\sqrt{\left(\frac{\partial z}{\partial x}\right)^2 + \left(\frac{\partial z}{\partial y}\right)^2}\right) \times \frac{180}{\pi}$$

### Riley's Terrain Ruggedness Index (TRI)
Measures obstacle roughness for rovers and robots. It takes the difference between the central cell and its 8 neighbors:
$$\text{TRI} = \sqrt{\frac{\sum_{k=1}^8 (z_k - z_\text{center})^2}{8}}$$
* $\text{TRI} < 1\text{m}$: Smooth plain.
* $\text{TRI} = 2 - 4\text{m}$: Rough basaltic lava flow (good test ground for quadruped robots).
* $\text{TRI} > 5\text{m}$: Extremely jagged cliff/breakdown boulders.

---

## 5. The Scoring Method: Functional Mission Matching

We do not claim Earth has "lunar gravity" (the Moon has $1/6 g$) or "lunar vacuum". Instead, TERRAIN-X assesses **functional mission suitability**:
> *"Can a robotic team test lava tube descent, subterranean lidar mapping, and boulder navigation in this Earth site under conditions similar to Marius Hills on the Moon?"*

### Formulas
1. **Per-feature similarity ($s_i \in [0, 1]$):**
   Continuous features use a Gaussian bell curve centered on the mission target:
   $$s_i = \exp\left( -0.5 \cdot \left(\frac{x_i - \text{target}_i}{\text{tolerance}_i}\right)^2 \right)$$
2. **Overall Suitability Score ($S$):**
   $$S = \frac{\sum w_i \cdot s_i}{\sum w_i\text{ available}}$$
3. **Completeness ($C$):**
   $$C = \frac{\sum w_i\text{ available}}{\sum w_i\text{ required}}$$
4. **Insufficient Evidence Safeguard:**
   If a mandatory feature (such as `cave_accessibility_evidence`) is unknown or unmeasured, TERRAIN-X **withholds the score** (`score = None`) and outputs an `insufficient_evidence` warning. This prevents false positives.

