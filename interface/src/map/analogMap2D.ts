import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { AnalogSite } from '../types';
import { sound } from '../audio';

export class AnalogMap2DManager {
  private mapContainer: HTMLElement;
  private transitionOverlay: HTMLElement;
  private map: L.Map | null = null;
  private currentMarker: L.Marker | null = null;
  private currentCircle: L.Circle | null = null;
  private onReturnToOrbitCallback?: () => void;
  private isReturning = false;

  constructor(mapContainerId: string, transitionOverlayId: string) {
    this.mapContainer = document.getElementById(mapContainerId) as HTMLElement;
    this.transitionOverlay = document.getElementById(transitionOverlayId) as HTMLElement;
  }

  public setOnReturnToOrbit(callback: () => void) {
    this.onReturnToOrbitCallback = callback;
  }

  /**
   * Inicia la secuencia cinematográfica de inmersión y despliega el mapa satelital 2D
   */
  public triggerAtmosphericDive(site: AnalogSite) {
    this.isReturning = false;
    sound.playTargetLock();

    // 1. Activar efecto sutil de transición
    this.transitionOverlay.classList.remove('hidden', 'fade-out', 'ascent-effect');
    this.transitionOverlay.classList.add('active', 'dive-effect');

    setTimeout(() => {
      sound.playWhoosh();
    }, 300);

    // 2. Cargar mapa satelital 2D
    setTimeout(() => {
      this.display2DMap(site);

      this.transitionOverlay.classList.remove('dive-effect');
      this.transitionOverlay.classList.add('fade-out');

      setTimeout(() => {
        this.transitionOverlay.classList.remove('active', 'fade-out');
        this.transitionOverlay.classList.add('hidden');
      }, 600);
    }, 1500);
  }

  /**
   * Carga y renderiza el mapa satelital Leaflet con capa Esri World Imagery
   */
  private display2DMap(site: AnalogSite) {
    this.mapContainer.classList.remove('hidden');
    this.mapContainer.classList.add('active');

    const lat = site.coordinates.latitude;
    const lon = site.coordinates.longitude;

    if (!this.map) {
      this.map = L.map('leafletMap', {
        center: [lat, lon],
        zoom: 12,
        minZoom: 2,
        zoomControl: false,
        attributionControl: false
      });

      // Capa de satélite fotorrealista de alta definición de Esri
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 18,
        attribution: 'Esri, Maxar, Earthstar Geographics'
      }).addTo(this.map);

      L.control.zoom({ position: 'bottomright' }).addTo(this.map);

      // =========================================================================
      // SOLICITUD CLAVE:
      // "Cuando me aleje con la ruleta del ratón hasta casi llegar a ver el mapa
      // de la tierra, quiero que cambie el mapa 2D por la interfaz 3D"
      // =========================================================================
      this.map.on('zoomend', () => {
        if (!this.map || this.isReturning) return;
        // Si el usuario hace zoom-out con la rueda del ratón hasta nivel 3 o menos (vista casi global)
        if (this.map.getZoom() <= 3) {
          this.returnToSpaceOrbit();
        }
      });

      // Detectar también el scroll directo hacia afuera si ya está en nivel bajo
      const mapElem = document.getElementById('leafletMap');
      if (mapElem) {
        mapElem.addEventListener('wheel', (e) => {
          if (!this.map || this.isReturning) return;
          if (e.deltaY > 0 && this.map.getZoom() <= 4) {
            this.returnToSpaceOrbit();
          }
        }, { passive: true });
      }
    } else {
      this.map.setView([lat, lon], 12, { animate: false });
      this.map.invalidateSize();
    }

    // Limpiar marcadores anteriores
    if (this.currentMarker) {
      this.map.removeLayer(this.currentMarker);
    }
    if (this.currentCircle) {
      this.map.removeLayer(this.currentCircle);
    }

    // Anillo pulsante de radar sobre el análogo
    const accentColor = site.target_body === 'Moon' ? '#22d3ee' : '#f97316';
    this.currentCircle = L.circle([lat, lon], {
      color: accentColor,
      fillColor: accentColor,
      fillOpacity: 0.2,
      radius: 2000,
      weight: 2
    }).addTo(this.map);

    // Marcador personalizado de alta tecnología
    const customIcon = L.divIcon({
      className: 'analog-radar-marker',
      html: `
        <div class="radar-ping" style="border-color:${accentColor};"></div>
        <div class="radar-core" style="background:${accentColor}; box-shadow:0 0 14px ${accentColor};"></div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    this.currentMarker = L.marker([lat, lon], { icon: customIcon }).addTo(this.map);

    this.currentMarker.bindPopup(`
      <div class="map-popup-card">
        <span class="popup-tag ${site.target_body.toLowerCase()}">${site.target_body} Analog</span>
        <h4>${site.name}</h4>
        <p class="popup-coords">${site.coordinates.label}</p>
        <p class="popup-desc">${site.scientific_justification}</p>
        <div class="popup-score">
          <span>Fidelidad de Terreno:</span>
          <strong>${site.similarity_score}%</strong>
        </div>
      </div>
    `).openPopup();

    this.updateMapHUD(site);
  }

  private updateMapHUD(site: AnalogSite) {
    const titleEl = document.getElementById('mapSiteTitle');
    const coordsEl = document.getElementById('mapSiteCoords');
    const badgeEl = document.getElementById('mapTargetBadge');
    const scoreEl = document.getElementById('mapSiteScore');

    if (titleEl) titleEl.textContent = site.name;
    if (coordsEl) coordsEl.textContent = `${site.region}, ${site.country} | ${site.coordinates.label}`;
    if (badgeEl) {
      badgeEl.textContent = `${site.target_body.toUpperCase()} ANALOG`;
      badgeEl.className = `map-hud-badge ${site.target_body.toLowerCase()}-badge`;
    }
    if (scoreEl) scoreEl.textContent = `${site.similarity_score}%`;
  }

  /**
   * Regresa desde el mapa 2D a la interfaz 3D en el espacio
   */
  public returnToSpaceOrbit() {
    if (this.isReturning) return;
    this.isReturning = true;
    sound.playClick(600);

    this.transitionOverlay.classList.remove('hidden', 'fade-out');
    this.transitionOverlay.classList.add('active', 'ascent-effect');

    setTimeout(() => {
      this.mapContainer.classList.remove('active');
      this.mapContainer.classList.add('hidden');

      if (this.onReturnToOrbitCallback) {
        this.onReturnToOrbitCallback();
      }

      setTimeout(() => {
        this.transitionOverlay.classList.remove('ascent-effect');
        this.transitionOverlay.classList.add('fade-out');

        setTimeout(() => {
          this.transitionOverlay.classList.remove('active', 'fade-out');
          this.transitionOverlay.classList.add('hidden');
          this.isReturning = false;
        }, 500);
      }, 500);
    }, 450);
  }
}
