import * as BABYLON from 'babylonjs';

/**
 * Fondo de espacio profundo realista: negro espacial absoluto con miles de estrellas
 * puntuales nítidas (estilo Google Earth / NASA Apollo).
 */
export class DeepSpaceEnvironment {
  private skyDome: BABYLON.Mesh;
  private starParticles: BABYLON.PointsCloudSystem;

  constructor(scene: BABYLON.Scene) {
    // 1. Cúpula estelar de fondo infinito
    this.skyDome = BABYLON.MeshBuilder.CreateSphere('deepSpaceDome', {
      diameter: 700,
      segments: 32,
      sideOrientation: BABYLON.Mesh.BACKSIDE
    }, scene);

    const skyMat = new BABYLON.StandardMaterial('deepSpaceMat', scene);
    skyMat.backFaceCulling = false;
    skyMat.disableLighting = true;
    skyMat.emissiveTexture = this.generateRealisticStarTexture(scene);
    this.skyDome.material = skyMat;

    // 2. Sistema de estrellas 3D con efecto de paralaje suave
    this.starParticles = new BABYLON.PointsCloudSystem('starCloud', 1, scene);
    const starCount = 3000;

    this.starParticles.addPoints(starCount, (particle) => {
      const radius = 140 + Math.random() * 160;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos((Math.random() * 2) - 1);

      particle.position.x = radius * Math.sin(phi) * Math.cos(theta);
      particle.position.y = radius * Math.sin(phi) * Math.sin(theta);
      particle.position.z = radius * Math.cos(phi);

      const brightness = 0.5 + Math.random() * 0.5;
      particle.color = new BABYLON.Color4(brightness, brightness, brightness, 0.95);
    });

    this.starParticles.buildMeshAsync();

    // Rotación sutil casi imperceptible de la esfera celeste
    scene.onBeforeRenderObservable.add(() => {
      this.skyDome.rotation.y += 0.00002;
    });
  }

  private generateRealisticStarTexture(scene: BABYLON.Scene): BABYLON.DynamicTexture {
    const width = 2048;
    const height = 1024;
    const tex = new BABYLON.DynamicTexture('realisticStarTex', { width, height }, scene, false);
    const ctx = tex.getContext();

    // 1. Fondo negro espacial puro (sin gradientes ni niebla azulada)
    ctx.fillStyle = '#010204';
    ctx.fillRect(0, 0, width, height);

    // 2. Banda muy tenue de la Vía Láctea en gris neutro sutil
    const mwGrad = ctx.createLinearGradient(0, height * 0.15, width, height * 0.85);
    mwGrad.addColorStop(0, 'rgba(0,0,0,0)');
    mwGrad.addColorStop(0.48, 'rgba(255, 255, 255, 0.03)');
    mwGrad.addColorStop(0.52, 'rgba(255, 255, 255, 0.03)');
    mwGrad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = mwGrad;
    ctx.fillRect(0, 0, width, height);

    // 3. Estrellas puntuales nítidas (blancas y diminutas, idénticas a fotos reales de satélite)
    for (let i = 0; i < 3500; i++) {
      const x = Math.random() * width;
      const y = Math.random() * height;
      const radius = Math.random() < 0.94 ? (0.35 + Math.random() * 0.6) : (1.1 + Math.random() * 0.9);
      const alpha = 0.4 + Math.random() * 0.6;

      ctx.fillStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
    }

    tex.update();
    return tex;
  }
}
