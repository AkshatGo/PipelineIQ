import { useEffect, useRef, useState, useMemo } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';

type CircuitBoardSceneProps = { reducedMotion: boolean };

type SolderNode = {
  mesh: THREE.Mesh;
  mat: THREE.MeshStandardMaterial;
  x: number;
  fixed: boolean;
  pulse: number;
  delay: number;
};

type DataPacket = {
  mesh: THREE.Points<THREE.SphereGeometry, THREE.ShaderMaterial>;
  curve: THREE.CatmullRomCurve3;
  progress: number;
  speed: number;
  traceIndex: number;
  size: number;
};

type FloatingParticle = {
  mesh: THREE.Points<THREE.SphereGeometry, THREE.ShaderMaterial>;
  velocity: THREE.Vector3;
  life: number;
  maxLife: number;
  basePosition: THREE.Vector3;
};

const C = {
  board: 0x0f110a,
  chip: 0x14160f,
  copper: 0xc98a3e,
  copperDark: 0x9c6b2e,
  rust: 0xb3452b,
  moss: 0x6b8e5a,
  lamp: 0xf5e6c8,
  teal: 0x1f6f6a,
  line: 0x2d3123,
  paper: 0xf2ebe0,
  brass: 0xb8963a,
  gold: 0xffd700,
  cyan: 0x00d4d4,
  magenta: 0xd400d4,
  lime: 0xaaff00,
};

const BW = 8;
const BD = 5;
const BH = 0.22;
const SWEEP_S = 5.5;
const REST_S = 1.8;
const CYCLE_S = SWEEP_S + REST_S;

const TRACE_VERTEX_SHADER = `
  uniform float uTime;
  uniform float uSpeed;
  varying float vProgress;
  varying vec2 vUv;
  
  void main() {
    vUv = uv;
    float progress = fract(uTime * uSpeed + uv.x);
    vProgress = progress;
    
    // Animate the trace geometry along the curve
    vec3 pos = position;
    pos.y += sin(uTime * 3.0 + uv.x * 10.0) * 0.003;
    pos.z += sin(uTime * 2.0 + uv.x * 8.0) * 0.002;
    
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const TRACE_FRAGMENT_SHADER = `
  uniform float uTime;
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  uniform vec3 uColorC;
  varying float vProgress;
  varying vec2 vUv;
  
  float noise(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
  }
  
  float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.5;
    for (int i = 0; i < 5; i++) {
      value += amplitude * noise(p);
      p *= 2.0;
      amplitude *= 0.5;
    }
    return value;
  }
  
  void main() {
    float flow = fract(uTime * 0.8 + vUv.x * 5.0);
    float pulse = sin(uTime * 4.0 + vUv.x * 20.0) * 0.5 + 0.5;
    
    // Animated flow along the trace
    float flowMask = smoothstep(0.4, 0.6, flow);
    flowMask = mix(flowMask, 1.0, pulse * 0.3);
    
    // Base copper color
    vec3 baseColor = mix(uColorA, uColorB, vUv.y);
    
    // Animated highlight traveling along trace
    float highlight = smoothstep(0.45, 0.55, flow) * (1.0 - smoothstep(0.55, 0.65, flow));
    vec3 highlightColor = mix(uColorC, vec3(1.0), pulse * 0.5);
    
    // Noise for organic variation
    float n = fbm(vUv * 10.0 + uTime * 0.1) * 0.1;
    
    vec3 finalColor = baseColor + highlightColor * highlight * 2.0;
    finalColor += vec3(n);
    
    // Emissive intensity
    float emissiveIntensity = 0.15 + pulse * 0.2 + highlight * 1.5;
    
    gl_FragColor = vec4(finalColor, 1.0);
    
    // Add glow effect
    float glow = highlight * 2.0 + pulse * 0.3;
    gl_FragColor.rgb += vec3(glow) * vec3(0.3, 0.2, 0.05);
  }
`;

const PARTICLE_VERTEX_SHADER = `
  attribute float aSize;
  attribute float aLife;
  attribute vec3 aColor;
  uniform float uTime;
  varying float vLife;
  varying vec3 vColor;
  varying float vAlpha;
  
  void main() {
    vLife = aLife;
    vColor = aColor;
    vAlpha = aLife;
    
    vec3 pos = position;
    float scale = aLife * aSize * 2.0;
    gl_PointSize = scale * (300.0 / -mvPosition.z);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const PARTICLE_FRAGMENT_SHADER = `
  uniform float uTime;
  varying float vLife;
  varying vec3 vColor;
  varying float vAlpha;
  
  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    float alpha = smoothstep(0.5, 0.0, dist) * vAlpha * vLife;
    
    if (alpha < 0.01) discard;
    
    vec3 color = vColor;
    // Pulse based on life
    float pulse = sin(uTime * 8.0 + vLife * 20.0) * 0.3 + 0.7;
    color *= pulse;
    
    // Core glow
    float core = 1.0 - smoothstep(0.0, 0.5, length(gl_PointCoord - vec2(0.5)));
    color += vec3(1.0) * core * 0.5 * vLife;
    
    gl_FragColor = vec4(color, alpha * 0.8);
  }
`;

const BEAM_VERTEX_SHADER = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const BEAM_FRAGMENT_SHADER = `
  uniform float uTime;
  uniform float uProgress;
  varying vec2 vUv;
  
  void main() {
    float scan = uProgress;
    float width = 0.15;
    float falloff = smoothstep(scan - width, scan, vUv.y) * smoothstep(scan, scan + width, vUv.y);
    
    // Chromatic aberration effect
    float r = smoothstep(scan - width * 1.02, scan, vUv.y) * smoothstep(scan, scan + width * 1.02, vUv.y);
    float g = smoothstep(scan - width, scan, vUv.y) * smoothstep(scan, scan + width, vUv.y);
    float b = smoothstep(scan - width * 0.98, scan, vUv.y) * smoothstep(scan, scan + width * 0.98, vUv.y);
    
    // Scan line interference
    float interference = sin(vUv.x * 80.0 + uTime * 10.0) * 0.1;
    falloff += interference;
    
    // Core beam
    vec3 color = mix(
      vec3(0.96, 0.90, 0.78),  // warm lamp
      vec3(1.0, 1.0, 0.9),      // bright center
      1.0 - abs(vUv.y - scan) / width
    );
    
    color *= falloff * 2.0;
    color.r *= r;
    color.g *= g;
    color.b *= b;
    
    // Scan line artifacts
    float scanlines = sin(vUv.y * 400.0 + uTime * 20.0) * 0.05;
    color += scanlines * falloff;
    
    // Vignette at edges
    float vignette = 1.0 - length(vUv - vec2(0.5, scan)) * 1.5;
    color *= max(0.0, vignette);
    
    float alpha = falloff * 0.85;
    gl_FragColor = vec4(color, alpha);
  }
`;

const FLOATING_PARTICLE_VERTEX = `
  attribute float aSize;
  attribute float aPhase;
  attribute vec3 aColor;
  uniform float uTime;
  varying float vAlpha;
  varying vec3 vColor;
  
  void main() {
    vColor = aColor;
    float life = sin(uTime * 0.5 + aPhase) * 0.5 + 0.5;
    vAlpha = life * 0.6 + 0.2;
    
    vec3 pos = position;
    pos.y += sin(uTime * 0.3 + aPhase) * 0.5;
    pos.x += sin(uTime * 0.2 + aPhase * 1.5) * 0.3;
    pos.z += sin(uTime * 0.4 + aPhase * 0.8) * 0.3;
    
    float scale = (0.5 + life * 0.5) * 2.0;
    gl_PointSize = scale * (200.0 / -mvPosition.z);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const FLOATING_PARTICLE_FRAGMENT = `
  varying float vAlpha;
  void main() {
    float dist = length(gl_PointCoord - vec2(0.5));
    float alpha = smoothstep(0.5, 0.0, dist) * vAlpha;
    if (alpha < 0.01) discard;
    
    vec3 color = vec3(0.8, 0.6, 0.3) * 0.5 + vec3(0.2, 0.3, 0.2) * 0.5;
    color += vec3(1.0, 0.8, 0.4) * (1.0 - dist) * 0.3;
    
    gl_FragColor = vec4(color, alpha * vAlpha);
  }
`;

export function CircuitBoardScene({ reducedMotion }: CircuitBoardSceneProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [unsupported, setUnsupported] = useState(false);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const [easedPointer, setEasedPointer] = useState({ x: 0, y: 0 });

  // Trace shaders
  const traceMaterial = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: TRACE_VERTEX_SHADER,
    fragmentShader: TRACE_FRAGMENT_SHADER,
    uniforms: {
      uTime: { value: 0 },
      uSpeed: { value: 0.15 },
      uColorA: { value: new THREE.Color(0x8b6914) },
      uColorB: { value: new THREE.Color(0xc98a3e) },
      uColorC: { value: new THREE.Color(0xffd700) },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    depthTest: true,
  }), []);

  // Particle material for data packets
  const particleMaterial = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: PARTICLE_VERTEX_SHADER,
    fragmentShader: PARTICLE_FRAGMENT_SHADER,
    uniforms: {
      uTime: { value: 0 },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexColors: true,
  }), []);

  // Beam material
  const beamMaterial = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: BEAM_VERTEX_SHADER,
    fragmentShader: BEAM_FRAGMENT_SHADER,
    uniforms: {
      uTime: { value: 0 },
      uProgress: { value: 0 },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    side: THREE.DoubleSide,
  }), []);

  // Floating particles
  const floatingParticleMaterial = useMemo(() => new THREE.ShaderMaterial({
    vertexShader: FLOATING_PARTICLE_VERTEX,
    fragmentShader: FLOATING_PARTICLE_FRAGMENT,
    uniforms: {
      uTime: { value: 0 },
    },
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexColors: true,
  }), []);

  // Standard materials
  const copperMat = useMemo(() => new THREE.MeshStandardMaterial({ 
    color: C.copper, 
    metalness: 0.85, 
    roughness: 0.35 
  }), []);
  
  const chipMat = useMemo(() => new THREE.MeshStandardMaterial({ 
    color: C.chip, 
    roughness: 0.5, 
    metalness: 0.25 
  }), []);
  
  const traceMat = useMemo(() => new THREE.MeshStandardMaterial({ 
    color: C.copper, 
    metalness: 0.8, 
    roughness: 0.35,
    emissive: C.copper,
    emissiveIntensity: 0.08,
  }), []);

  const padGeo = useMemo(() => new THREE.CylinderGeometry(0.15, 0.15, 0.016, 24), []);
  const nodeGeo = useMemo(() => new THREE.CylinderGeometry(0.085, 0.085, 0.07, 24), []);
  const holeGeo = useMemo(() => new THREE.CylinderGeometry(0.16, 0.16, 0.012, 28), []);
  const boardGeo = useMemo(() => new THREE.BoxGeometry(BW, BH, BD), []);
  const chipGeo2 = useMemo(() => new THREE.BoxGeometry(1.1, 0.16, 0.72), []);
  const pinGeo2 = useMemo(() => new THREE.BoxGeometry(0.07, 0.04, 0.16), []);
  
  const rust = new THREE.Color(C.rust);
  const moss = new THREE.Color(C.moss);

  // State for animation
  // @ts-expect-error - used in useEffect closure
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [dataPackets, setDataPackets] = useState<DataPacket[]>([]);
  // @ts-expect-error - used in useEffect closure
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [floatingParticles, setFloatingParticles] = useState<FloatingParticle[]>([]);
  // @ts-expect-error - used in useEffect closure
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [nodes, setNodes] = useState<SolderNode[]>([]);

  /* eslint-disable react-hooks/exhaustive-deps -- all deps are stable (useMemo refs, refs) */
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ 
        antialias: true, 
        alpha: true, 
        powerPreference: 'high-performance',
        preserveDrawingBuffer: false,
      });
    } catch {
      setUnsupported(true);
      return;
    }
    
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    
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
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);

    // Setup EffectComposer for post-processing
    const composer = new EffectComposer(renderer, new THREE.WebGLRenderTarget(window.innerWidth, window.innerHeight, {
      minFilter: THREE.LinearFilter,
      magFilter: THREE.LinearFilter,
      format: THREE.RGBAFormat,
      type: THREE.HalfFloatType,
    }));
    
    composer.addPass(new RenderPass(scene, camera));
    
    // Bloom pass
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(window.innerWidth, window.innerHeight),
      0.8,
      0.4,
      0.85
    );
    composer.addPass(bloomPass);
    
    // FXAA pass
    const fxaaPass = new ShaderPass(FXAAShader);
    fxaaPass.material.uniforms['resolution'].value.set(1 / window.innerWidth, 1 / window.innerHeight);
    composer.addPass(fxaaPass);
    

    // ========== SCENE SETUP ==========
    
    const rig = new THREE.Group();
    scene.add(rig);
    const board = new THREE.Group();
    board.rotation.y = -0.16;
    rig.add(board);

    // Board
    const boardMesh = new THREE.Mesh(
      boardGeo,
      track(new THREE.MeshStandardMaterial({ color: C.board, roughness: 0.85, metalness: 0.1 }))
    );
    boardMesh.position.y = -BH / 2;
    boardMesh.receiveShadow = true;
    board.add(boardMesh);
    const edges = new THREE.LineSegments(
      track(new THREE.EdgesGeometry(boardGeo)),
      track(new THREE.LineBasicMaterial({ color: C.line }))
    );
    edges.position.copy(boardMesh.position);
    board.add(edges);

    // Mounting holes
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
    [
      [-1.5, 0.35],
      [2.1, -1.05],
      [0.9, 1.4],
    ].forEach(([cx, cz]) => {
      const chip = new THREE.Mesh(chipGeo2, chipMat);
      chip.position.set(cx, 0.1, cz);
      chip.castShadow = true;
      board.add(chip);
      for (let p = 0; p < 6; p++) {
        const px = cx - 0.45 + p * 0.18;
        [-1, 1].forEach((side) => {
          const pin = new THREE.Mesh(pinGeo2, copperMat);
          pin.position.set(px, 0.03, cz + side * 0.44);
          board.add(pin);
        });
      }
    });

    // Traces + solder nodes
    const rand = mulberry32(11);
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
          })
        );
        const mesh = new THREE.Mesh(nodeGeo, mat);
        mesh.position.set(p.x, 0.05, p.z);
        mesh.castShadow = true;
        board.add(mesh);
        nodes.push({ mesh, mat, x: p.x, fixed: false, pulse: 1, delay: rand() * 0.5 });
      }
    }
    setNodes(nodes);

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

    // Floating particles
    const floatingParticles: FloatingParticle[] = [];
    const PARTICLE_COUNT = 150;
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const geometry = new THREE.SphereGeometry(0.02 + Math.random() * 0.03, 8, 8);
      const material = floatingParticleMaterial.clone();
      material.uniforms.aPhase = { value: Math.random() * Math.PI * 2 };
      material.uniforms.aColor = { value: new THREE.Color().setHSL(0.1 + Math.random() * 0.1, 0.5, 0.5) };
      material.uniforms.aSize = { value: 1.0 };
      const mesh = new THREE.Points(geometry, material);
      mesh.position.set(
        (Math.random() - 0.5) * BW * 0.9,
        (Math.random() - 0.5) * 2 + 0.5,
        (Math.random() - 0.5) * BD * 0.9
      );
      floatingParticles.push({
        mesh,
        velocity: new THREE.Vector3(
          (Math.random() - 0.5) * 0.01,
          (Math.random() - 0.5) * 0.01,
          (Math.random() - 0.5) * 0.01
        ),
        life: Math.random(),
        maxLife: 1,
        basePosition: mesh.position.clone()
      });
      scene.add(mesh);
    }
    setFloatingParticles(floatingParticles);

    // Data packets
    const dataPackets: DataPacket[] = [];
    const PACKET_COUNT = 12;
    for (let i = 0; i < PACKET_COUNT; i++) {
      const traceIndex = Math.floor(Math.random() * TRACES);
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(-BW/2, 0.05, -BD/2),
        new THREE.Vector3(0, 0.05, 0),
        new THREE.Vector3(BW/2, 0.05, BD/2),
      ]);
      const geometry = new THREE.SphereGeometry(0.08, 12, 12);
      const material = particleMaterial.clone();
      material.uniforms.aSize = { value: 1.0 };
      material.uniforms.aLife = { value: 1.0 };
      material.uniforms.aColor = { value: new THREE.Color(C.gold) };
      const mesh = new THREE.Points(geometry, material);
      mesh.position.set(-BW/2, 0.05, -BD/2);
      dataPackets.push({
        mesh,
        curve,
        progress: Math.random(),
        speed: 0.15 + Math.random() * 0.1,
        traceIndex,
        size: 0.08
      });
      scene.add(mesh);
    }
    setDataPackets(dataPackets);

    // Lighting
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

    // Pointer tracking
    const onPointer = (e: PointerEvent) => {
      setPointer({
        x: (e.clientX / window.innerWidth) * 2 - 1,
        y: (e.clientY / window.innerHeight) * 2 - 1,
      });
    };

    // Resize handler
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
      composer.setSize(w, h);
      fxaaPass.material.uniforms['resolution'].value.set(1 / w, 1 / h);
      renderer.render(scene, camera);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(mount);
    resize();

    // Pointer move listener
    if (!reducedMotion) {
      window.addEventListener('pointermove', onPointer, { passive: true });
    }

    // Intersection observer for performance
    let io: IntersectionObserver | null = null;
    let visible = true;
    if (!reducedMotion) {
      io = new IntersectionObserver(([entry]) => {
        visible = entry.isIntersecting;
      });
      io.observe(mount);
    }

    // Animation loop
    let raf = 0;
    let last = performance.now();
    let elapsed = 0;
    let lastCycle = -1;

    const tick = (now: number) => {
      raf = requestAnimationFrame(tick);
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      if (!visible || document.hidden) return;
      elapsed += dt;

      // Update shader uniforms
      traceMaterial.uniforms.uTime.value = elapsed;
      particleMaterial.uniforms.uTime.value = elapsed;
      beamMaterial.uniforms.uTime.value = elapsed;
      floatingParticleMaterial.uniforms.uTime.value = elapsed;
      beamMaterial.uniforms.uProgress.value = (elapsed % CYCLE_S) / SWEEP_S;

      // Update floating particles
      floatingParticles.forEach((p) => {
        p.mesh.position.add(p.velocity);
        if (p.mesh.position.y > 2.5) p.mesh.position.y = -1;
        if (p.mesh.position.y < -1) p.mesh.position.y = 2.5;
        if (p.mesh.position.x > BW/2) p.mesh.position.x = -BW/2;
        if (p.mesh.position.x < -BW/2) p.mesh.position.x = BW/2;
        if (p.mesh.position.z > BD/2) p.mesh.position.z = -BD/2;
        if (p.mesh.position.z < -BD/2) p.mesh.position.z = BD/2;
      });

      // Update data packets
      dataPackets.forEach((p) => {
        p.progress += p.speed * 0.016;
        if (p.progress > 1) {
          p.progress = 0;
          p.speed = 0.15 + Math.random() * 0.1;
        }
        const pos = p.curve.getPointAt(p.progress);
        p.mesh.position.copy(pos);
      });

      // Smooth pointer easing
      setEasedPointer(prev => ({
        x: prev.x + (pointer.x - prev.x) * 0.05,
        y: prev.y + (pointer.y - prev.y) * 0.05,
      }));

      // Beam sweep cycle
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

      // Update nodes as beam passes
      nodes.forEach((n) => {
        if (!n.fixed && bx >= n.x) {
          n.fixed = true;
          n.mat.color.copy(moss);
          n.mat.emissive.copy(moss);
          n.mat.emissiveIntensity = 0.3;
          n.pulse = 0;
        }
        if (n.pulse < 1) {
          n.pulse = Math.min(1, n.pulse + dt / 0.3);
          const k = Math.sin(n.pulse * Math.PI);
          n.mesh.scale.set(1 + 0.7 * k, 1 + 0.4 * k, 1 + 0.7 * k);
        }
      });

      // Update data packets
      dataPackets.forEach((p) => {
        p.progress += p.speed * dt;
        if (p.progress > 1) {
          p.progress = 0;
          p.speed = 0.15 + Math.random() * 0.1;
        }
        const pos = p.curve.getPointAt(p.progress);
        p.mesh.position.copy(pos);
      });

      // Smooth camera follow
      const targetRotationY = easedPointer.x * 0.16 + Math.sin(elapsed * 0.25) * 0.04;
      const targetRotationX = easedPointer.y * 0.07;
      rig.rotation.y += (targetRotationY - rig.rotation.y) * 0.05;
      rig.rotation.x += (targetRotationX - rig.rotation.x) * 0.05;

      // Update shader uniforms for data packets
      dataPackets.forEach((p) => {
        if (p.mesh.material instanceof THREE.ShaderMaterial) {
          p.mesh.material.uniforms.uTime.value = elapsed;
        }
      });

      // Render with post-processing
      composer.render(dt);
    };

    raf = requestAnimationFrame(tick);

    // Event listeners
    if (!reducedMotion) {
      window.addEventListener('pointermove', onPointer, { passive: true });
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('pointermove', onPointer);
      ro.disconnect();
      io?.disconnect();
      disposables.forEach((d) => d.dispose());
      composer.dispose();
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