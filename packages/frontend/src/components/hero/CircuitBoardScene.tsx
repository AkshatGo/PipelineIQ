import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

type CircuitBoardSceneProps = { reducedMotion: boolean };

type SolderNode = {
  mesh: THREE.Mesh;
  mat: THREE.MeshStandardMaterial;
  x: number;
  fixed: boolean;
  pulse: number;
};

const C = {
  board: 0x1f221a,
  chip: 0x171912,
  copper: 0xc98a3e,
  rust: 0xb3452f,
  moss: 0x7c9a6b,
  lamp: 0xf3e6c8,
  teal: 0x2f6e6a,
  line: 0x33362a,
  paper: 0xede6d6,
};

const BW = 8;
const BD = 5;
const BH = 0.22;
const SWEEP_S = 4.2;
const REST_S = 1.4;
const CYCLE_S = SWEEP_S + REST_S;

export function CircuitBoardScene({ reducedMotion }: CircuitBoardSceneProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [unsupported, setUnsupported] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
    } catch {
      setUnsupported(true);
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const canvas = renderer.domElement;
    canvas.style.display = 'block';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    mount.appendChild(canvas);

    const disposables: { dispose: () => void }[] = [];
    const track = <T extends { dispose: () => void }>(obj: T): T => {
      disposables.push(obj);
      return obj;
    };

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);

    // Lighting: one warm bench lamp, one dim teal fill
    scene.add(new THREE.AmbientLight(C.paper, 0.16));
    const lamp = new THREE.SpotLight(C.lamp, 120, 0, Math.PI / 5.2, 0.55, 2);
    lamp.position.set(-2.6, 8.4, 2.6);
    lamp.target.position.set(0.5, 0, 0);
    lamp.castShadow = true;
    lamp.shadow.mapSize.set(1024, 1024);
    lamp.shadow.bias = -0.0006;
    scene.add(lamp, lamp.target);
    const fill = new THREE.DirectionalLight(C.teal, 1.2);
    fill.position.set(6, 3, -5);
    scene.add(fill);

    const rig = new THREE.Group();
    scene.add(rig);
    const board = new THREE.Group();
    board.rotation.y = -0.16;
    rig.add(board);

    // Board
    const boardGeo = track(new THREE.BoxGeometry(BW, BH, BD));
    const boardMesh = new THREE.Mesh(
      boardGeo,
      track(new THREE.MeshStandardMaterial({ color: C.board, roughness: 0.85, metalness: 0.1 })),
    );
    boardMesh.position.y = -BH / 2;
    boardMesh.receiveShadow = true;
    board.add(boardMesh);
    const edges = new THREE.LineSegments(
      track(new THREE.EdgesGeometry(boardGeo)),
      track(new THREE.LineBasicMaterial({ color: C.line })),
    );
    edges.position.copy(boardMesh.position);
    board.add(edges);

    const copperMat = track(new THREE.MeshStandardMaterial({ color: C.copper, metalness: 0.85, roughness: 0.38 }));

    // Mounting holes
    const holeGeo = track(new THREE.CylinderGeometry(0.16, 0.16, 0.012, 28));
    [
      [-BW / 2 + 0.3, -BD / 2 + 0.3],
      [BW / 2 - 0.3, -BD / 2 + 0.3],
      [-BW / 2 + 0.3, BD / 2 - 0.3],
      [BW / 2 - 0.3, BD / 2 - 0.3],
    ].forEach(([x, z]) => {
      const hole = new THREE.Mesh(holeGeo, copperMat);
      hole.position.set(x, 0.006, z);
      board.add(hole);
    });

    // Chips with pins
    const chipGeo = track(new THREE.BoxGeometry(1.1, 0.16, 0.72));
    const chipMat = track(new THREE.MeshStandardMaterial({ color: C.chip, roughness: 0.5, metalness: 0.25 }));
    const pinGeo = track(new THREE.BoxGeometry(0.07, 0.04, 0.16));
    [
      [-1.5, 0.35],
      [2.1, -1.05],
      [0.9, 1.4],
    ].forEach(([cx, cz]) => {
      const chip = new THREE.Mesh(chipGeo, chipMat);
      chip.position.set(cx, 0.1, cz);
      chip.castShadow = true;
      board.add(chip);
      for (let p = 0; p < 6; p++) {
        const px = cx - 0.45 + p * 0.18;
        [-1, 1].forEach((side) => {
          const pin = new THREE.Mesh(pinGeo, copperMat);
          pin.position.set(px, 0.03, cz + side * 0.44);
          board.add(pin);
        });
      }
    });

    // Traces + solder nodes
    const rand = mulberry32(11);
    const traceMat = track(
      new THREE.MeshStandardMaterial({
        color: C.copper,
        metalness: 0.8,
        roughness: 0.35,
        emissive: C.copper,
        emissiveIntensity: 0.08,
      }),
    );
    const padGeo = track(new THREE.CylinderGeometry(0.15, 0.15, 0.016, 24));
    const nodeGeo = track(new THREE.CylinderGeometry(0.085, 0.085, 0.07, 24));
    const rust = new THREE.Color(C.rust);
    const moss = new THREE.Color(C.moss);
    const nodes: SolderNode[] = [];
    const TRACES = 7;

    for (let i = 0; i < TRACES; i++) {
      const z0 = -BD / 2 + 0.6 + (i * (BD - 1.2)) / (TRACES - 1);
      const xStart = -BW / 2 + 0.35 + rand() * 0.9;
      const xEnd = BW / 2 - 0.35 - rand() * 0.9;
      const segs = 7;
      const pts: THREE.Vector3[] = [];
      let z = z0;
      for (let s = 0; s <= segs; s++) {
        const x = xStart + (s / segs) * (xEnd - xStart);
        if (s > 0 && s < segs) z = clamp(z + (rand() - 0.5) * 0.7, -BD / 2 + 0.35, BD / 2 - 0.35);
        pts.push(new THREE.Vector3(x, 0.02, z));
      }
      const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.2);
      const tube = new THREE.Mesh(track(new THREE.TubeGeometry(curve, 160, 0.026, 8, false)), traceMat);
      tube.castShadow = true;
      board.add(tube);

      const count = 2 + Math.floor(rand() * 2);
      for (let n = 0; n < count; n++) {
        const t = clamp((n + 0.5) / count + (rand() - 0.5) * 0.14, 0.06, 0.94);
        const p = curve.getPointAt(t);
        const pad = new THREE.Mesh(padGeo, copperMat);
        pad.position.set(p.x, 0.008, p.z);
        board.add(pad);
        const mat = track(
          new THREE.MeshStandardMaterial({
            color: C.rust,
            emissive: C.rust,
            emissiveIntensity: 0.45,
            metalness: 0.4,
            roughness: 0.45,
          }),
        );
        const mesh = new THREE.Mesh(nodeGeo, mat);
        mesh.position.set(p.x, 0.05, p.z);
        mesh.castShadow = true;
        board.add(mesh);
        nodes.push({ mesh, mat, x: p.x, fixed: false, pulse: 1 });
      }
    }

    // Scan beam
    const beam = new THREE.Group();
    board.add(beam);
    const beamMat = (opacity: number) =>
      track(
        new THREE.MeshBasicMaterial({
          color: C.lamp,
          transparent: true,
          opacity,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
          side: THREE.DoubleSide,
        }),
      );
    const core = new THREE.Mesh(track(new THREE.PlaneGeometry(0.05, BD + 0.3)), beamMat(0.95));
    core.rotation.x = -Math.PI / 2;
    core.position.y = 0.1;
    const halo = new THREE.Mesh(track(new THREE.PlaneGeometry(0.5, BD + 0.3)), beamMat(0.12));
    halo.rotation.x = -Math.PI / 2;
    halo.position.y = 0.09;
    const curtain = new THREE.Mesh(track(new THREE.PlaneGeometry(BD + 0.3, 0.7)), beamMat(0.07));
    curtain.rotation.y = Math.PI / 2;
    curtain.position.y = 0.4;
    beam.add(core, halo, curtain);

    const xFrom = -BW / 2 - 0.3;
    const xTo = BW / 2 + 0.3;

    const setNode = (node: SolderNode, fixed: boolean) => {
      node.fixed = fixed;
      node.mat.color.copy(fixed ? moss : rust);
      node.mat.emissive.copy(fixed ? moss : rust);
      node.mat.emissiveIntensity = fixed ? 0.3 : 0.45;
    };

    const resize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      const d = w / h < 1.1 ? 1.45 : 1;
      camera.position.set(0.6 * d, 8.2 * d, 8.4 * d);
      camera.lookAt(0, -0.2, 0);
      camera.updateProjectionMatrix();
      renderer.render(scene, camera);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(mount);
    resize();

    const pointer = { x: 0, y: 0 };
    const eased = { x: 0, y: 0 };
    const onPointer = (e: PointerEvent) => {
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
    };

    let raf = 0;
    let io: IntersectionObserver | null = null;

    if (reducedMotion) {
      const frozenX = xFrom + (xTo - xFrom) * 0.6;
      beam.position.x = frozenX;
      nodes.forEach((n) => setNode(n, n.x < frozenX));
      renderer.render(scene, camera);
    } else {
      window.addEventListener('pointermove', onPointer, { passive: true });
      let visible = true;
      io = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
      });
      io.observe(mount);

      let last = performance.now();
      let elapsed = 0;
      let lastCycle = -1;

      const tick = (now: number) => {
        raf = requestAnimationFrame(tick);
        const dt = Math.min((now - last) / 1000, 0.05);
        last = now;
        if (!visible || document.hidden) return;
        elapsed += dt;

        const cycle = Math.floor(elapsed / CYCLE_S);
        const local = elapsed - cycle * CYCLE_S;
        if (cycle !== lastCycle) {
          lastCycle = cycle;
          nodes.forEach((n) => setNode(n, false));
        }
        const progress = Math.min(local / SWEEP_S, 1);
        const bx = xFrom + (xTo - xFrom) * progress;
        beam.position.x = bx;
        beam.visible = local < SWEEP_S;

        for (const n of nodes) {
          if (!n.fixed && bx >= n.x) {
            setNode(n, true);
            n.pulse = 0;
          }
          if (n.pulse < 1) {
            n.pulse = Math.min(1, n.pulse + dt / 0.3);
            const k = Math.sin(n.pulse * Math.PI);
            n.mesh.scale.set(1 + 0.7 * k, 1 + 0.4 * k, 1 + 0.7 * k);
          }
        }

        eased.x += (pointer.x - eased.x) * 0.05;
        eased.y += (pointer.y - eased.y) * 0.05;
        rig.rotation.y = eased.x * 0.16 + Math.sin(elapsed * 0.25) * 0.04;
        rig.rotation.x = eased.y * 0.07;

        renderer.render(scene, camera);
      };
      raf = requestAnimationFrame(tick);
    }

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io?.disconnect();
      window.removeEventListener('pointermove', onPointer);
      disposables.forEach((d) => d.dispose());
      renderer.dispose();
      if (canvas.parentNode === mount) mount.removeChild(canvas);
    };
  }, [reducedMotion]);

  if (unsupported) return null;
  return <div ref={mountRef} className="h-full w-full" />;
}

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v));
}

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}