import * as BABYLON from 'babylonjs';

export function latLonToVector3(lat: number, lon: number, radius: number): BABYLON.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.sin(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.cos(theta);

  return new BABYLON.Vector3(x, y, z);
}

export class TargetPin {
  private root: BABYLON.TransformNode;
  private ringMesh: BABYLON.Mesh;
  private coreMesh: BABYLON.Mesh;
  private beamMesh: BABYLON.Mesh;
  private glowMaterial: BABYLON.StandardMaterial;
  private earthRadius: number;

  constructor(scene: BABYLON.Scene, earthRadius: number) {
    this.earthRadius = earthRadius;
    this.root = new BABYLON.TransformNode('targetPinRoot', scene);

    // Material holográfico cian/ámbar translúcido refinado
    this.glowMaterial = new BABYLON.StandardMaterial('targetPinGlowMat', scene);
    this.glowMaterial.emissiveColor = new BABYLON.Color3(0.13, 0.83, 0.93);
    this.glowMaterial.diffuseColor = new BABYLON.Color3(0.2, 0.9, 1.0);
    this.glowMaterial.alpha = 0.75;
    this.glowMaterial.disableLighting = true;

    // 1. Núcleo central del marcador
    this.coreMesh = BABYLON.MeshBuilder.CreateSphere('pinCore', { diameter: 0.08 }, scene);
    this.coreMesh.material = this.glowMaterial;
    this.coreMesh.parent = this.root;

    // 2. Anillo holográfico pulsante en la superficie
    this.ringMesh = BABYLON.MeshBuilder.CreateTorus('pinRing', {
      diameter: 0.28,
      thickness: 0.015,
      tessellation: 32
    }, scene);
    this.ringMesh.material = this.glowMaterial;
    this.ringMesh.parent = this.root;

    // 3. Haz de luz vertical elegante
    this.beamMesh = BABYLON.MeshBuilder.CreateCylinder('pinBeam', {
      height: 0.45,
      diameterTop: 0.005,
      diameterBottom: 0.025
    }, scene);
    this.beamMesh.material = this.glowMaterial;
    this.beamMesh.parent = this.root;
    this.beamMesh.position.y = 0.225;

    let time = 0;
    scene.onBeforeRenderObservable.add(() => {
      time += 0.04;
      const scale = 1 + Math.sin(time * 3) * 0.2;
      this.ringMesh.scaling.set(scale, scale, scale);
      this.glowMaterial.alpha = 0.5 + Math.sin(time * 3) * 0.25;
    });

    this.setVisible(false);
  }

  public setCoordinates(lat: number, lon: number) {
    const pos = latLonToVector3(lat, lon, this.earthRadius);
    this.root.position = pos;

    const normal = pos.clone().normalize();
    const up = new BABYLON.Vector3(0, 1, 0);

    const axis = BABYLON.Vector3.Cross(up, normal);
    const angle = Math.acos(BABYLON.Vector3.Dot(up, normal));
    if (axis.lengthSquared() > 0.0001) {
      this.root.rotationQuaternion = BABYLON.Quaternion.RotationAxis(axis.normalize(), angle);
    } else {
      this.root.rotationQuaternion = BABYLON.Quaternion.Identity();
    }

    this.setVisible(true);
  }

  public setVisible(visible: boolean) {
    this.coreMesh.setEnabled(visible);
    this.ringMesh.setEnabled(visible);
    this.beamMesh.setEnabled(visible);
  }

  public setColor(color: BABYLON.Color3) {
    this.glowMaterial.emissiveColor = color;
  }

  public getRoot(): BABYLON.TransformNode {
    return this.root;
  }
}
