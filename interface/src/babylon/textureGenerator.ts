import * as BABYLON from 'babylonjs';

/**
 * Generador procedural de texturas planetarias de alta fidelidad.
 * Garantiza que la escena 3D en BabylonJS funcione al 100% de inmediato,
 * offline y sin problemas de CORS ni caídas de servidores externos.
 */
export class PlanetaryTextureGenerator {
  /**
   * Genera la textura de la Tierra (océanos, continentes, atmósfera)
   */
  public static createEarthTexture(scene: BABYLON.Scene): BABYLON.DynamicTexture {
    const width = 2048;
    const height = 1024;
    const dynamicTexture = new BABYLON.DynamicTexture('earthTexture', { width, height }, scene, false);
    const ctx = dynamicTexture.getContext();

    // 1. Océanos azul profundo con gradiente
    const oceanGrad = ctx.createLinearGradient(0, 0, 0, height);
    oceanGrad.addColorStop(0, '#0c2340');
    oceanGrad.addColorStop(0.3, '#103762');
    oceanGrad.addColorStop(0.5, '#17487f');
    oceanGrad.addColorStop(0.7, '#103762');
    oceanGrad.addColorStop(1, '#0c2340');
    ctx.fillStyle = oceanGrad;
    ctx.fillRect(0, 0, width, height);

    // 2. Continentes terrestres simplificados pero estéticos y reconocibles
    ctx.fillStyle = '#2d6a4f'; // Verde vegetación

    // América del Norte
    this.drawContinent(ctx, [
      [300, 180], [450, 160], [550, 220], [500, 350], [420, 420],
      [340, 390], [280, 300], [270, 220]
    ], '#386641');

    // América del Sur
    this.drawContinent(ctx, [
      [420, 460], [490, 490], [520, 580], [460, 720], [420, 780],
      [390, 680], [380, 540]
    ], '#2d6a4f');

    // Europa
    this.drawContinent(ctx, [
      [950, 180], [1050, 160], [1120, 220], [1080, 300], [980, 310], [930, 250]
    ], '#4f772d');

    // África
    this.drawContinent(ctx, [
      [930, 330], [1060, 330], [1140, 440], [1110, 620], [1040, 700],
      [980, 680], [920, 520], [900, 400]
    ], '#a3704c'); // Tono desértico/sabana

    // Asia
    this.drawContinent(ctx, [
      [1120, 160], [1500, 140], [1620, 250], [1550, 400], [1380, 420],
      [1250, 460], [1160, 350], [1100, 250]
    ], '#588157');

    // Australia
    this.drawContinent(ctx, [
      [1500, 580], [1620, 590], [1650, 680], [1580, 740], [1480, 700], [1460, 630]
    ], '#b07d58');

    // Casquetes polares (Ártico y Antártida)
    ctx.fillStyle = '#eaf4f4';
    ctx.fillRect(0, 0, width, 65); // Ártico
    ctx.fillRect(0, height - 90, width, 90); // Antártida

    // Detalles costeros y archipiélagos
    ctx.fillStyle = '#40916c';
    ctx.beginPath();
    ctx.arc(880, 230, 18, 0, Math.PI * 2); // Reino Unido
    ctx.arc(1620, 380, 22, 0, Math.PI * 2); // Japón
    ctx.arc(1280, 580, 30, 0, Math.PI * 2); // Indonesia
    ctx.arc(630, 430, 20, 0, Math.PI * 2); // Caribe
    ctx.fill();

    dynamicTexture.update();
    return dynamicTexture;
  }

  /**
   * Genera la textura de las nubes de la Tierra con canal alfa
   */
  public static createCloudsTexture(scene: BABYLON.Scene): BABYLON.DynamicTexture {
    const width = 1024;
    const height = 512;
    const dynamicTexture = new BABYLON.DynamicTexture('cloudsTexture', { width, height }, scene, true);
    const ctx = dynamicTexture.getContext();

    // Fondo transparente
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = 'rgba(255, 255, 255, 0.55)';
    // Generar franjas y remolinos de nubes
    for (let i = 0; i < 40; i++) {
      const cx = Math.random() * width;
      const cy = 60 + Math.random() * (height - 120);
      const rx = 40 + Math.random() * 120;
      const ry = 15 + Math.random() * 45;

      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, (Math.random() - 0.5) * 0.4, 0, Math.PI * 2);
      ctx.fill();
    }

    dynamicTexture.hasAlpha = true;
    dynamicTexture.update();
    return dynamicTexture;
  }

  /**
   * Genera la textura de la Luna (cráteres, mares lunares, regolito)
   */
  public static createMoonTexture(scene: BABYLON.Scene): BABYLON.DynamicTexture {
    const width = 1024;
    const height = 512;
    const dynamicTexture = new BABYLON.DynamicTexture('moonTexture', { width, height }, scene, false);
    const ctx = dynamicTexture.getContext();

    // Fondo gris regolito
    ctx.fillStyle = '#8a8d91';
    ctx.fillRect(0, 0, width, height);

    // Mares lunares (zonas basálticas oscuras)
    ctx.fillStyle = '#5c5e62';
    const maria = [
      [350, 180, 90, 70], // Mare Imbrium
      [480, 220, 80, 60], // Mare Serenitatis
      [580, 250, 70, 50], // Mare Tranquillitatis
      [280, 280, 110, 80] // Oceanus Procellarum
    ];
    maria.forEach(([x, y, rx, ry]) => {
      ctx.beginPath();
      ctx.ellipse(x, y, rx, ry, 0.2, 0, Math.PI * 2);
      ctx.fill();
    });

    // Cráteres de impacto con sombra y borde iluminado
    for (let i = 0; i < 90; i++) {
      const cx = Math.random() * width;
      const cy = Math.random() * height;
      const r = 4 + Math.random() * 20;

      // Sombra interior
      ctx.fillStyle = '#424447';
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      // Borde brillante
      ctx.strokeStyle = '#c4c8cc';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx - 1, cy - 1, r, Math.PI * 0.8, Math.PI * 1.8);
      ctx.stroke();
    }

    dynamicTexture.update();
    return dynamicTexture;
  }

  /**
   * Genera la textura de Marte (óxidos de hierro, casquetes polares, Valles Marineris)
   */
  public static createMarsTexture(scene: BABYLON.Scene): BABYLON.DynamicTexture {
    const width = 1024;
    const height = 512;
    const dynamicTexture = new BABYLON.DynamicTexture('marsTexture', { width, height }, scene, false);
    const ctx = dynamicTexture.getContext();

    // Fondo rojizo anaranjado marciano
    const marsGrad = ctx.createLinearGradient(0, 0, 0, height);
    marsGrad.addColorStop(0, '#c1440e');
    marsGrad.addColorStop(0.5, '#d95d1e');
    marsGrad.addColorStop(1, '#a6380a');
    ctx.fillStyle = marsGrad;
    ctx.fillRect(0, 0, width, height);

    // Zonas de albedo oscuro (Syrtis Major, Acidalia Planitia)
    ctx.fillStyle = '#6e2b10';
    ctx.beginPath();
    ctx.ellipse(450, 260, 120, 70, -0.3, 0, Math.PI * 2);
    ctx.ellipse(750, 290, 140, 80, 0.1, 0, Math.PI * 2);
    ctx.fill();

    // Valles Marineris (hendidura tectónica longitudinal)
    ctx.strokeStyle = '#4a1b08';
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.moveTo(250, 280);
    ctx.bezierCurveTo(340, 275, 420, 295, 520, 290);
    ctx.stroke();

    // Casquetes polares de CO2 y agua congelada
    ctx.fillStyle = '#f8f9fa';
    ctx.beginPath();
    ctx.ellipse(width / 2, 20, 140, 20, 0, 0, Math.PI * 2); // Polo norte
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(width / 2, height - 15, 110, 15, 0, 0, Math.PI * 2); // Polo sur
    ctx.fill();

    dynamicTexture.update();
    return dynamicTexture;
  }

  private static drawContinent(ctx: CanvasRenderingContext2D, points: number[][], color: string) {
    if (points.length === 0) return;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i++) {
      ctx.lineTo(points[i][0], points[i][1]);
    }
    ctx.closePath();
    ctx.fill();
  }
}

