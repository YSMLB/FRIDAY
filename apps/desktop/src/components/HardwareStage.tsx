import { useEffect, useRef } from "react";
import * as THREE from "three";

export interface HardwareLabels {
  cpu: string;
  gpu: string;
  ram: string;
  disk: string;
}

interface HardwareStageProps {
  labels: HardwareLabels;
  status: string;
}

const CYAN = 0x3ad6e8;

function wire(geo: THREE.BufferGeometry, color = CYAN, opacity = 0.95) {
  return new THREE.LineSegments(
    new THREE.EdgesGeometry(geo),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity })
  );
}

function fill(geo: THREE.BufferGeometry, opacity = 0.12) {
  return new THREE.Mesh(
    geo,
    new THREE.MeshBasicMaterial({
      color: CYAN,
      transparent: true,
      opacity,
      depthWrite: false,
    })
  );
}

function labeledGroup(name: string, build: (g: THREE.Group) => void) {
  const g = new THREE.Group();
  g.name = name;
  build(g);
  return g;
}

function makeGpu() {
  return labeledGroup("gpu", (g) => {
    const pcb = new THREE.BoxGeometry(2.6, 0.08, 1.15);
    g.add(fill(pcb, 0.16), wire(pcb));
    const shroud = new THREE.BoxGeometry(2.5, 0.42, 1.05);
    const shroudMesh = fill(shroud, 0.08);
    shroudMesh.position.y = 0.28;
    g.add(shroudMesh, wire(shroud).translateY(0.28));
    for (const x of [-0.55, 0.55]) {
      const fan = new THREE.CylinderGeometry(0.38, 0.38, 0.06, 16);
      const fm = fill(fan, 0.1);
      fm.position.set(x, 0.52, 0);
      g.add(fm, wire(fan, CYAN, 0.7).translateX(x).translateY(0.52));
    }
    const io = new THREE.BoxGeometry(0.12, 0.55, 1.05);
    const iom = fill(io, 0.2);
    iom.position.set(-1.38, 0.12, 0);
    g.add(iom, wire(io).translateX(-1.38).translateY(0.12));
  });
}

function makeCpu() {
  return labeledGroup("cpu", (g) => {
    const ihs = new THREE.BoxGeometry(0.95, 0.12, 0.95);
    g.add(fill(ihs, 0.2), wire(ihs));
    const hs = new THREE.BoxGeometry(1.35, 0.55, 1.35);
    const hsm = fill(hs, 0.08);
    hsm.position.y = 0.38;
    g.add(hsm, wire(hs).translateY(0.38));
    for (let i = -4; i <= 4; i++) {
      const fin = new THREE.BoxGeometry(1.2, 0.42, 0.04);
      const m = fill(fin, 0.06);
      m.position.set(0, 0.4, i * 0.12);
      g.add(m);
    }
  });
}

function makeRam() {
  return labeledGroup("ram", (g) => {
    for (let i = 0; i < 4; i++) {
      const stick = new THREE.BoxGeometry(0.12, 0.72, 1.35);
      const m = fill(stick, 0.14);
      m.position.x = (i - 1.5) * 0.28;
      g.add(m, wire(stick).translateX(m.position.x));
    }
  });
}

function makeSsd() {
  return labeledGroup("disk", (g) => {
    const body = new THREE.BoxGeometry(1.7, 0.12, 0.85);
    g.add(fill(body, 0.18), wire(body));
    const chip = new THREE.BoxGeometry(0.45, 0.06, 0.35);
    const cm = fill(chip, 0.25);
    cm.position.y = 0.1;
    g.add(cm, wire(chip).translateY(0.1));
  });
}

export function HardwareStage({ labels, status }: HardwareStageProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const statusRef = useRef(status);
  statusRef.current = status;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
    camera.position.set(0, 2.4, 8.2);
    camera.lookAt(0, 0, 0);

    const rig = new THREE.Group();
    const gpu = makeGpu();
    gpu.position.set(0, 0.35, 0);
    const cpu = makeCpu();
    cpu.position.set(-2.6, 0.5, 1.4);
    const ram = makeRam();
    ram.position.set(2.5, 0.4, 1.2);
    const ssd = makeSsd();
    ssd.position.set(0.2, -1.15, 1.6);
    rig.add(gpu, cpu, ram, ssd);
    scene.add(rig);

    const grid = new THREE.GridHelper(14, 18, CYAN, 0x0a3340);
    grid.position.y = -1.7;
    scene.add(grid);

    scene.add(new THREE.AmbientLight(0x88ddff, 0.8));

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const w = parent.clientWidth;
      const h = parent.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / Math.max(h, 1);
      camera.updateProjectionMatrix();
    };
    resize();
    const ro = new ResizeObserver(resize);
    if (canvas.parentElement) ro.observe(canvas.parentElement);

    let raf = 0;
    const tick = () => {
      const st = statusRef.current;
      const spin = st === "speaking" ? 0.018 : st === "thinking" ? 0.012 : 0.006;
      gpu.rotation.y += spin;
      cpu.rotation.y -= spin * 0.7;
      ram.rotation.y += spin * 0.5;
      ssd.rotation.y -= spin * 0.4;
      rig.rotation.y = Math.sin(performance.now() / 9000) * 0.12;
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      renderer.dispose();
    };
  }, []);

  return (
    <div className="hw-stage">
      <canvas ref={canvasRef} />
      <div className="hw-captions">
        <span>GPU // {labels.gpu}</span>
        <span>CPU // {labels.cpu}</span>
        <span>RAM // {labels.ram}</span>
        <span>SSD // {labels.disk}</span>
      </div>
    </div>
  );
}
