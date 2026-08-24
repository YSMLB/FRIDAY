import * as THREE from "three";

export type WorldHandle = {
  setStatus: (status: string) => void;
  dispose: () => void;
};

function fibonacciSphere(count: number, jitter = 0): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / Math.max(count - 1, 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i;
    const v = new THREE.Vector3(Math.cos(theta) * r, y, Math.sin(theta) * r);
    if (jitter) {
      v.x += (Math.random() - 0.5) * jitter;
      v.y += (Math.random() - 0.5) * jitter;
      v.z += (Math.random() - 0.5) * jitter;
      v.normalize();
    }
    pts.push(v);
  }
  return pts;
}

function noise2(x: number, z: number): number {
  return (
    Math.sin(x * 0.31) * Math.cos(z * 0.27) * 0.55 +
    Math.sin(x * 0.73 + z * 0.41) * 0.22 +
    Math.sin(x * 1.6) * Math.cos(z * 1.35) * 0.07
  );
}

function makeTerrain(): THREE.Mesh {
  const geo = new THREE.PlaneGeometry(48, 48, 110, 110);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const d = Math.hypot(x, z);
    const crater = -Math.exp(-d * d * 0.012) * 0.55;
    pos.setY(i, noise2(x, z) * 0.42 + crater);
  }
  geo.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({
    color: 0x16181c,
    roughness: 0.96,
    metalness: 0.04,
    flatShading: false,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.position.y = -1.15;
  return mesh;
}

function patchShell(
  mat: THREE.MeshPhysicalMaterial,
  sites: THREE.Vector3[],
  wall: number,
  morph: number,
  key: string
): void {
  mat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = { value: 0 };
    shader.uniforms.uWall = { value: wall };
    shader.uniforms.uMorph = { value: morph };
    shader.uniforms.uSites = { value: sites };
    const n = sites.length;

    shader.vertexShader = `
      uniform float uTime;
      uniform float uMorph;
      varying vec3 vObjPos;
    ${shader.vertexShader}`
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
         float wave = sin(transformed.x * 2.05 + uTime * 0.31)
                    * sin(transformed.y * 1.72 + 0.4)
                    * sin(transformed.z * 2.28 + uTime * 0.19);
         float swell = sin(uTime * 0.45 + transformed.y * 3.0) * 0.35;
         transformed += normalize(transformed + 0.0001) * (wave + swell) * uMorph;`
      )
      .replace(
        "#include <project_vertex>",
        `#include <project_vertex>
         vObjPos = transformed;`
      );

    shader.fragmentShader = `
      uniform float uWall;
      uniform vec3 uSites[${n}];
      varying vec3 vObjPos;
      float voronoiEdge(vec3 dir) {
        float f1 = 8.0;
        float f2 = 8.0;
        for (int i = 0; i < ${n}; i++) {
          float d = 1.0 - dot(dir, uSites[i]);
          if (d < f1) { f2 = f1; f1 = d; }
          else if (d < f2) { f2 = d; }
        }
        return f2 - f1;
      }
    ${shader.fragmentShader}`.replace(
      "#include <clipping_planes_fragment>",
      `#include <clipping_planes_fragment>
       vec3 dir = normalize(vObjPos);
       float edge = voronoiEdge(dir);
       if (edge > uWall) discard;`
    );

    mat.userData.shader = shader;
  };
  mat.customProgramCacheKey = () => key;
}

function makeShell(radius: number, detail: number, sites: THREE.Vector3[], wall: number, morph: number, key: string) {
  const geo = new THREE.IcosahedronGeometry(radius, detail);
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xe7e2d8,
    roughness: 0.72,
    metalness: 0.04,
    clearcoat: 0.18,
    clearcoatRoughness: 0.55,
    sheen: 0.25,
    sheenColor: new THREE.Color(0xd8d2c6),
    side: THREE.DoubleSide,
    shadowSide: THREE.DoubleSide,
  });
  patchShell(mat, sites, wall, morph, key);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function makeShards(): THREE.Group {
  const group = new THREE.Group();
  const mat = new THREE.MeshPhysicalMaterial({
    color: 0xded9d0,
    roughness: 0.5,
    metalness: 0.08,
  });
  for (let i = 0; i < 18; i++) {
    const geo =
      i % 3 === 0
        ? new THREE.IcosahedronGeometry(0.045 + Math.random() * 0.05, 0)
        : new THREE.BoxGeometry(0.03, 0.12 + Math.random() * 0.1, 0.02);
    const mesh = new THREE.Mesh(geo, mat);
    const phi = Math.acos(2 * Math.random() - 1);
    const theta = Math.random() * Math.PI * 2;
    const r = 1.35 + Math.random() * 0.55;
    mesh.position.set(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.cos(phi) * 0.75,
      r * Math.sin(phi) * Math.sin(theta)
    );
    mesh.rotation.set(Math.random() * 6, Math.random() * 6, Math.random() * 6);
    mesh.castShadow = true;
    group.add(mesh);
  }
  return group;
}

export function createFridayWorld(canvas: HTMLCanvasElement): WorldHandle {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x0b0d11, 1);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0b0d11, 0.046);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 80);
  camera.position.set(0.15, 0.72, 5.15);
  camera.lookAt(0, 0.42, 0);

  scene.add(new THREE.AmbientLight(0x1c2430, 0.32));
  const hemi = new THREE.HemisphereLight(0x8ea0b4, 0x1a1612, 0.65);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xfff3e4, 2.15);
  key.position.set(-5.2, 6.4, 3.4);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 22;
  key.shadow.camera.left = -6;
  key.shadow.camera.right = 6;
  key.shadow.camera.top = 6;
  key.shadow.camera.bottom = -6;
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x3ad6e8, 0.22);
  rim.position.set(5.4, 1.2, -3.2);
  scene.add(rim);

  const fill = new THREE.DirectionalLight(0x4a5564, 0.28);
  fill.position.set(2.2, -0.6, 5);
  scene.add(fill);

  const terrain = makeTerrain();
  scene.add(terrain);

  const coreMat = new THREE.MeshPhysicalMaterial({
    color: 0xefeae1,
    roughness: 0.48,
    metalness: 0.06,
    clearcoat: 0.35,
    clearcoatRoughness: 0.4,
  });
  const core = new THREE.Mesh(new THREE.SphereGeometry(0.7, 64, 64), coreMat);
  core.castShadow = true;
  core.receiveShadow = true;

  const shellA = makeShell(1.05, 5, fibonacciSphere(38, 0.12), 0.055, 0.11, "shell-a");
  const shellB = makeShell(1.2, 4, fibonacciSphere(24, 0.16), 0.042, 0.16, "shell-b");
  shellB.rotation.set(0.4, 0.7, 0.15);

  const ringGeo = new THREE.TorusGeometry(1.38, 0.007, 8, 96);
  const ringMat = new THREE.MeshPhysicalMaterial({
    color: 0xd8d4cc,
    roughness: 0.35,
    metalness: 0.12,
  });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI * 0.42;
  ring.rotation.y = 0.3;

  const shards = makeShards();

  const rig = new THREE.Group();
  rig.position.y = 0.55;
  rig.add(core, shellA, shellB, ring, shards);
  scene.add(rig);

  let status = "idle";
  const disposables: THREE.Object3D[] = [terrain, core, shellA, shellB, ring, shards];

  const resize = () => {
    const parent = canvas.parentElement;
    const w = parent?.clientWidth || window.innerWidth;
    const h = parent?.clientHeight || window.innerHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  };
  resize();
  const ro = new ResizeObserver(resize);
  if (canvas.parentElement) ro.observe(canvas.parentElement);

  let raf = 0;
  const tick = (now: number) => {
    const t = now / 1000;
    const speaking = status === "speaking";
    const listening = status === "listening";
    const thinking = status === "thinking";
    const spin = speaking ? 0.012 : listening ? 0.007 : thinking ? 0.004 : 0.0032;

    shellA.rotation.y += spin;
    shellB.rotation.y -= spin * 0.65;
    shellB.rotation.z += spin * 0.12;
    core.rotation.y -= spin * 0.25;
    ring.rotation.z += spin * 0.4;
    shards.rotation.y += spin * 0.5;
    shards.rotation.x = Math.sin(t * 0.2) * 0.08;

    const breath = 1 + Math.sin(t * (speaking ? 4.2 : listening ? 2.4 : 1.3)) * (speaking ? 0.018 : 0.01);
    rig.scale.setScalar(breath);

    camera.position.x = 0.15 + Math.sin(t * 0.12) * 0.18;
    camera.position.y = 0.72 + Math.sin(t * 0.09) * 0.06;
    camera.lookAt(0, 0.42, 0);

    rim.intensity = speaking ? 0.7 : listening ? 0.42 : 0.2;
    key.intensity = thinking ? 1.55 : 2.15;

    const shaderA = (shellA.material as THREE.MeshPhysicalMaterial).userData.shader;
    const shaderB = (shellB.material as THREE.MeshPhysicalMaterial).userData.shader;
    if (shaderA) shaderA.uniforms.uTime.value = t;
    if (shaderB) shaderB.uniforms.uTime.value = t;

    renderer.render(scene, camera);
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);

  return {
    setStatus: (next) => {
      status = next;
    },
    dispose: () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      disposables.forEach((obj) => {
        obj.traverse((child) => {
          const mesh = child as THREE.Mesh;
          mesh.geometry?.dispose();
          const m = mesh.material;
          if (Array.isArray(m)) m.forEach((x) => x.dispose());
          else m?.dispose?.();
        });
      });
      renderer.dispose();
    },
  };
}
