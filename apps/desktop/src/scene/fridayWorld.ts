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

function makeTerrain(): THREE.Mesh {
  const geo = new THREE.PlaneGeometry(42, 42, 90, 90);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const z = pos.getZ(i);
    const d = Math.hypot(x, z);
    const y =
      Math.sin(x * 0.28) * Math.cos(z * 0.24) * 0.28 +
      Math.sin(x * 0.8 + z * 0.5) * 0.08 -
      Math.exp(-d * d * 0.014) * 0.5;
    pos.setY(i, y);
  }
  geo.computeVertexNormals();
  const mat = new THREE.MeshStandardMaterial({
    color: 0x0a1520,
    roughness: 0.94,
    metalness: 0.08,
  });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = true;
  mesh.position.y = -1.05;
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
         float wave = sin(transformed.x * 1.55 + uTime * 0.22)
                    * sin(transformed.y * 1.35 + 0.25)
                    * sin(transformed.z * 1.7 + uTime * 0.15);
         transformed += normalize(transformed + 0.0001) * wave * uMorph;`
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
    color: 0xd7e8f2,
    roughness: 0.42,
    metalness: 0.12,
    clearcoat: 0.55,
    clearcoatRoughness: 0.28,
    sheen: 0.4,
    sheenColor: new THREE.Color(0x3ad6e8),
    emissive: new THREE.Color(0x0a2a36),
    emissiveIntensity: 0.18,
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
    color: 0xb8d4e0,
    roughness: 0.35,
    metalness: 0.2,
    emissive: 0x123848,
    emissiveIntensity: 0.25,
  });
  for (let i = 0; i < 14; i++) {
    const geo =
      i % 2 === 0
        ? new THREE.IcosahedronGeometry(0.035 + Math.random() * 0.04, 0)
        : new THREE.BoxGeometry(0.02, 0.1 + Math.random() * 0.08, 0.015);
    const mesh = new THREE.Mesh(geo, mat);
    const phi = Math.acos(2 * Math.random() - 1);
    const theta = Math.random() * Math.PI * 2;
    const r = 1.28 + Math.random() * 0.45;
    mesh.position.set(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.cos(phi) * 0.7,
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
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x050a12, 1);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x050a12, 0.048);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 80);
  camera.position.set(0.1, 0.68, 4.9);
  camera.lookAt(0, 0.4, 0);

  scene.add(new THREE.AmbientLight(0x14304a, 0.45));
  scene.add(new THREE.HemisphereLight(0x6eb8d8, 0x061018, 0.7));

  const key = new THREE.DirectionalLight(0xd8f4ff, 1.85);
  key.position.set(-4.6, 5.8, 3.2);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.near = 1;
  key.shadow.camera.far = 20;
  key.shadow.camera.left = -5;
  key.shadow.camera.right = 5;
  key.shadow.camera.top = 5;
  key.shadow.camera.bottom = -5;
  scene.add(key);

  const rim = new THREE.DirectionalLight(0x3ad6e8, 0.55);
  rim.position.set(4.8, 1.4, -2.8);
  scene.add(rim);

  const fill = new THREE.PointLight(0x1a6a88, 1.1, 12, 2);
  fill.position.set(0, 0.4, 2.2);
  scene.add(fill);

  const terrain = makeTerrain();
  scene.add(terrain);

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.68, 64, 64),
    new THREE.MeshPhysicalMaterial({
      color: 0xe8f6ff,
      roughness: 0.28,
      metalness: 0.15,
      clearcoat: 0.7,
      clearcoatRoughness: 0.2,
      emissive: new THREE.Color(0x146078),
      emissiveIntensity: 0.35,
    })
  );
  core.castShadow = true;
  core.receiveShadow = true;

  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(0.78, 32, 32),
    new THREE.MeshBasicMaterial({
      color: 0x3ad6e8,
      transparent: true,
      opacity: 0.08,
      depthWrite: false,
    })
  );

  const shellA = makeShell(1.02, 5, fibonacciSphere(34, 0.1), 0.048, 0.07, "shell-a");
  const shellB = makeShell(1.16, 4, fibonacciSphere(22, 0.14), 0.038, 0.1, "shell-b");
  shellB.rotation.set(0.35, 0.55, 0.12);

  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(1.32, 0.006, 8, 100),
    new THREE.MeshPhysicalMaterial({
      color: 0x7ed7ea,
      roughness: 0.25,
      metalness: 0.35,
      emissive: 0x3ad6e8,
      emissiveIntensity: 0.35,
    })
  );
  ring.rotation.x = Math.PI * 0.4;

  const shards = makeShards();
  const rig = new THREE.Group();
  rig.position.y = 0.52;
  rig.add(core, glow, shellA, shellB, ring, shards);
  scene.add(rig);

  let status = "idle";
  const disposables: THREE.Object3D[] = [terrain, core, glow, shellA, shellB, ring, shards];

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
    const spin = speaking ? 0.011 : listening ? 0.0065 : thinking ? 0.0035 : 0.0028;

    shellA.rotation.y += spin;
    shellB.rotation.y -= spin * 0.7;
    shellB.rotation.z += spin * 0.1;
    core.rotation.y -= spin * 0.2;
    ring.rotation.z += spin * 0.35;
    shards.rotation.y += spin * 0.45;

    const breath = 1 + Math.sin(t * (speaking ? 3.8 : listening ? 2.2 : 1.2)) * (speaking ? 0.016 : 0.009);
    rig.scale.setScalar(breath);
    glow.scale.setScalar(1 + Math.sin(t * 2.1) * 0.04);

    const coreMat = core.material as THREE.MeshPhysicalMaterial;
    coreMat.emissiveIntensity = speaking ? 0.7 : listening ? 0.48 : 0.32;
    rim.intensity = speaking ? 1.05 : listening ? 0.7 : 0.45;

    camera.position.x = 0.1 + Math.sin(t * 0.11) * 0.14;
    camera.position.y = 0.68 + Math.sin(t * 0.08) * 0.05;
    camera.lookAt(0, 0.4, 0);

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
