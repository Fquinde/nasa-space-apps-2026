import * as BABYLON from 'babylonjs';
import { PlanetaryTextureGenerator } from './textureGenerator';

/**
 * Renderizador fotorrealista de mini esferas 3D de Luna y Marte
 */
export class MiniPlanetViewer {
  private engine: BABYLON.Engine;
  private scene: BABYLON.Scene;
  private mesh: BABYLON.Mesh;

  constructor(canvas: HTMLCanvasElement, type: 'Moon' | 'Mars') {
    this.engine = new BABYLON.Engine(canvas, true, {
      preserveDrawingBuffer: true,
      antialias: true
    });

    this.scene = new BABYLON.Scene(this.engine);
    this.scene.clearColor = new BABYLON.Color4(0, 0, 0, 0);

    const camera = new BABYLON.ArcRotateCamera(
      'miniCam',
      -Math.PI / 2,
      Math.PI / 2.2,
      2.5,
      BABYLON.Vector3.Zero(),
      this.scene
    );
    camera.attachControl(canvas, false);
    camera.lowerRadiusLimit = 2.0;
    camera.upperRadiusLimit = 4.0;

    // Iluminación solar angular para resaltar sombras de cráteres lunares y cañones marcianos
    const sun = new BABYLON.DirectionalLight(
      'miniSun',
      new BABYLON.Vector3(-1.4, -0.2, 0.8).normalize(),
      this.scene
    );
    sun.intensity = 1.9;
    sun.diffuse = new BABYLON.Color3(1.0, 0.98, 0.92);

    const fillLight = new BABYLON.HemisphericLight(
      'miniFill',
      new BABYLON.Vector3(0, 1, 0),
      this.scene
    );
    fillLight.intensity = 0.22;
    fillLight.diffuse = new BABYLON.Color3(0.3, 0.4, 0.55);

    this.mesh = BABYLON.MeshBuilder.CreateSphere(`mini_${type}`, {
      diameter: 1.55,
      segments: 64
    }, this.scene);

    const mat = new BABYLON.StandardMaterial(`miniMat_${type}`, this.scene);

    if (type === 'Moon') {
      const moonTex = new BABYLON.Texture(
        './textures/moon.jpg',
        this.scene,
        false,
        true,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE,
        null,
        () => {
          mat.diffuseTexture = PlanetaryTextureGenerator.createMoonTexture(this.scene);
        }
      );
      mat.diffuseTexture = moonTex;
      mat.specularColor = new BABYLON.Color3(0.04, 0.04, 0.04);
      mat.roughness = 0.9;
    } else {
      const marsTex = new BABYLON.Texture(
        './textures/mars.jpg',
        this.scene,
        false,
        true,
        BABYLON.Texture.TRILINEAR_SAMPLINGMODE,
        null,
        () => {
          mat.diffuseTexture = PlanetaryTextureGenerator.createMarsTexture(this.scene);
        }
      );
      mat.diffuseTexture = marsTex;

      const marsBump = new BABYLON.Texture('./textures/mars_bump.jpg', this.scene);
      mat.bumpTexture = marsBump;
      mat.bumpTexture.level = 0.5;
      mat.specularColor = new BABYLON.Color3(0.08, 0.04, 0.02);
    }

    this.mesh.material = mat;

    this.engine.runRenderLoop(() => {
      this.mesh.rotation.y += 0.0035;
      this.scene.render();
    });

    window.addEventListener('resize', () => {
      this.engine.resize();
    });
  }

  public spinFast() {
    let count = 0;
    const interval = setInterval(() => {
      this.mesh.rotation.y += 0.045;
      count++;
      if (count > 25) clearInterval(interval);
    }, 16);
  }
}
