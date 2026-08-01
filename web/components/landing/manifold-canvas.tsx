"use client";

import { useEffect, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import { colors } from "@/lib/tokens";

interface Node {
  id: number;
  x: number;
  y: number;
  anchorX: number;
  anchorY: number;
  vx: number;
  vy: number;
  baseRadius: number;
  phase: number;
  speed: number;
  color: string;
  isConflict?: boolean;
  label: string;
  isDragged?: boolean;
}

interface Edge {
  from: number;
  to: number;
  flowPhase: number;
  isConflict?: boolean;
}

interface Shockwave {
  x: number;
  y: number;
  radius: number;
  maxRadius: number;
  opacity: number;
}

export function ManifoldCanvas() {
  const reduced = useReducedMotion();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (reduced) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let isVisible = true;

    // Handle Resize & DPR
    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = window.innerWidth;
      const height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener("resize", resize);

    // Visibility change handler to pause when tab hidden
    const handleVisibilityChange = () => {
      isVisible = !document.hidden;
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Seed deterministic node grid
    const nodeCount = 36;
    const nodes: Node[] = [];
    const width = window.innerWidth;
    const height = window.innerHeight;

    const labels = [
      "AST_Parse", "Transform_T1", "Symbol_Identity", "Drift_Engine", "Conflict_Omega",
      "Geodesic_Path", "Attractor_State", "Tangent_Vector", "Merge_Convergence", "Bag_Encoder",
      "Vector_Store", "Context_Stream", "AST_Fingerprint", "Code_Graph", "Operator_Algebra"
    ];

    for (let i = 0; i < nodeCount; i++) {
      const isConflictNode = i === 7 || i === 18 || i === 29;
      const posX = (0.1 + (i % 6) * 0.16 + (Math.sin(i * 1.5) * 0.05)) * width;
      const posY = (0.12 + Math.floor(i / 6) * 0.14 + (Math.cos(i * 1.2) * 0.05)) * height;
      nodes.push({
        id: i,
        x: posX,
        y: posY,
        anchorX: posX,
        anchorY: posY,
        vx: 0,
        vy: 0,
        baseRadius: isConflictNode ? 6 : 4 + (i % 3),
        phase: i * 0.4,
        speed: 0.0015 + (i % 4) * 0.0005,
        color: isConflictNode ? colors.conflict : i % 5 === 0 ? colors.trajectory : colors.node,
        isConflict: isConflictNode,
        label: isConflictNode ? `Conflict_Ω_${i}` : labels[i % labels.length],
      });
    }

    // Build edges between nearby nodes
    const edges: Edge[] = [];
    const rebuildEdges = () => {
      edges.length = 0;
      const w = window.innerWidth;
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < w * 0.22) {
            const isConflictEdge = Boolean(nodes[i].isConflict && nodes[j].isConflict);
            edges.push({
              from: i,
              to: j,
              flowPhase: (i + j) * 0.1,
              isConflict: isConflictEdge,
            });
          }
        }
      }
    };
    rebuildEdges();

    // Mouse & Touch Interaction State
    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let draggedNodeIndex: number | null = null;
    let hoveredNodeIndex: number | null = null;
    const shockwaves: Shockwave[] = [];

    const getCanvasCoords = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    };

    const handleMouseDown = (e: MouseEvent) => {
      const coords = getCanvasCoords(e);
      mouseX = coords.x;
      mouseY = coords.y;

      // Find closest node within click radius
      let closestIdx: number | null = null;
      let minDist = 32;

      nodes.forEach((node, idx) => {
        const dx = node.x - mouseX;
        const dy = node.y - mouseY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < minDist) {
          minDist = dist;
          closestIdx = idx;
        }
      });

      if (closestIdx !== null) {
        draggedNodeIndex = closestIdx;
        nodes[closestIdx].isDragged = true;
      } else {
        // Shockwave impulse on empty canvas click
        shockwaves.push({
          x: mouseX,
          y: mouseY,
          radius: 10,
          maxRadius: 180,
          opacity: 0.7,
        });

        // Push nearby nodes away from shockwave origin
        nodes.forEach((node) => {
          const dx = node.x - mouseX;
          const dy = node.y - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / 180 * 8;
            node.vx += (dx / dist) * force;
            node.vy += (dy / dist) * force;
          }
        });
      }
    };

    const handleMouseMove = (e: MouseEvent) => {
      const coords = getCanvasCoords(e);
      mouseX = coords.x;
      mouseY = coords.y;

      if (draggedNodeIndex !== null) {
        nodes[draggedNodeIndex].x = mouseX;
        nodes[draggedNodeIndex].y = mouseY;
        nodes[draggedNodeIndex].vx = 0;
        nodes[draggedNodeIndex].vy = 0;
      } else {
        // Check hovered node
        let closestIdx: number | null = null;
        let minDist = 24;
        nodes.forEach((node, idx) => {
          const dx = node.x - mouseX;
          const dy = node.y - mouseY;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < minDist) {
            minDist = dist;
            closestIdx = idx;
          }
        });
        hoveredNodeIndex = closestIdx;
        canvas.style.cursor = hoveredNodeIndex !== null ? "grab" : "default";
      }
    };

    const handleMouseUp = () => {
      if (draggedNodeIndex !== null) {
        nodes[draggedNodeIndex].isDragged = false;
        draggedNodeIndex = null;
      }
      canvas.style.cursor = hoveredNodeIndex !== null ? "grab" : "default";
    };

    const handleDblClick = (e: MouseEvent) => {
      const coords = getCanvasCoords(e);
      const newNodeId = nodes.length;
      nodes.push({
        id: newNodeId,
        x: coords.x,
        y: coords.y,
        anchorX: coords.x,
        anchorY: coords.y,
        vx: (Math.random() - 0.5) * 4,
        vy: (Math.random() - 0.5) * 4,
        baseRadius: 5,
        phase: Math.random() * Math.PI,
        speed: 0.002,
        color: colors.accent,
        label: `UserNode_${newNodeId}`,
      });
      rebuildEdges();
    };

    canvas.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    canvas.addEventListener("dblclick", handleDblClick);

    let time = 0;

    const render = () => {
      if (!isVisible) {
        animationFrameId = requestAnimationFrame(render);
        return;
      }

      time += 1;
      const w = window.innerWidth;
      const h = window.innerHeight;

      ctx.clearRect(0, 0, w, h);

      // Subtle parallax offset
      const offsetX = (mouseX - w / 2) * 0.01;
      const offsetY = (mouseY - h / 2) * 0.01;

      // Update Node Physics
      nodes.forEach((node, idx) => {
        if (node.isDragged) return;

        // Spring force back to anchor
        const dxAnchor = node.anchorX - node.x;
        const dyAnchor = node.anchorY - node.y;
        node.vx += dxAnchor * 0.002;
        node.vy += dyAnchor * 0.002;

        // Magnetic attraction to cursor if close
        const dxMouse = mouseX - node.x;
        const dyMouse = mouseY - node.y;
        const distMouse = Math.sqrt(dxMouse * dxMouse + dyMouse * dyMouse);
        if (distMouse < 110 && distMouse > 5) {
          const magForce = ((110 - distMouse) / 110) * 0.15;
          node.vx += (dxMouse / distMouse) * magForce;
          node.vy += (dyMouse / distMouse) * magForce;
        }

        // Apply velocity with damping
        node.x += node.vx;
        node.y += node.vy;
        node.vx *= 0.93;
        node.vy *= 0.93;
      });

      // Render Shockwaves
      for (let i = shockwaves.length - 1; i >= 0; i--) {
        const wave = shockwaves[i];
        wave.radius += 5;
        wave.opacity -= 0.018;

        if (wave.opacity <= 0 || wave.radius >= wave.maxRadius) {
          shockwaves.splice(i, 1);
          continue;
        }

        ctx.beginPath();
        ctx.arc(wave.x, wave.y, wave.radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(124, 92, 255, ${wave.opacity})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Render Edges
      edges.forEach((edge) => {
        const p1 = nodes[edge.from];
        const p2 = nodes[edge.to];
        if (!p1 || !p2) return;

        const x1 = p1.x + offsetX;
        const y1 = p1.y + offsetY;
        const x2 = p2.x + offsetX;
        const y2 = p2.y + offsetY;

        const isHighlighted =
          edge.from === hoveredNodeIndex ||
          edge.to === hoveredNodeIndex ||
          edge.from === draggedNodeIndex ||
          edge.to === draggedNodeIndex;

        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.strokeStyle = isHighlighted
          ? colors.accent
          : edge.isConflict
          ? "rgba(255, 107, 107, 0.45)"
          : "rgba(58, 66, 86, 0.35)";
        ctx.lineWidth = isHighlighted ? 2.5 : edge.isConflict ? 1.5 : 1;
        ctx.stroke();

        // Flowing particle along edge
        const flowSpeed = isHighlighted ? 0.016 : 0.008;
        const flowT = (time * flowSpeed + edge.flowPhase) % 1;
        const flowX = x1 + (x2 - x1) * flowT;
        const flowY = y1 + (y2 - y1) * flowT;

        ctx.beginPath();
        ctx.arc(flowX, flowY, isHighlighted ? 3 : edge.isConflict ? 2 : 1.5, 0, Math.PI * 2);
        ctx.fillStyle = isHighlighted ? colors.accent : edge.isConflict ? colors.conflict : colors.trajectory;
        ctx.fill();
      });

      // Render Trajectory main path
      if (nodes[0] && nodes[10] && nodes[20] && nodes[35]) {
        ctx.beginPath();
        ctx.moveTo(nodes[0].x + offsetX, nodes[0].y + offsetY);
        ctx.bezierCurveTo(
          nodes[10].x + offsetX,
          nodes[10].y + offsetY,
          nodes[20].x + offsetX,
          nodes[20].y + offsetY,
          nodes[35].x + offsetX,
          nodes[35].y + offsetY
        );
        ctx.strokeStyle = colors.trajectory;
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        ctx.lineDashOffset = -time * 0.5;
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Render Nodes
      nodes.forEach((node, idx) => {
        const nx = node.x + offsetX;
        const ny = node.y + offsetY;
        const isHovered = idx === hoveredNodeIndex || idx === draggedNodeIndex;
        const radiusPulse = Math.sin(time * node.speed * 2 + node.phase) * 1.2;
        const currentRadius = Math.max(1, (node.baseRadius + radiusPulse) * (isHovered ? 1.4 : 1));

        // Glow halo for conflict or hovered nodes
        if (node.isConflict || isHovered) {
          const glowRadius = currentRadius + 8 + Math.sin(time * 0.05) * 3;
          ctx.beginPath();
          ctx.arc(nx, ny, glowRadius, 0, Math.PI * 2);
          ctx.fillStyle = isHovered ? "rgba(124, 92, 255, 0.25)" : "rgba(255, 107, 107, 0.15)";
          ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(nx, ny, currentRadius, 0, Math.PI * 2);
        ctx.fillStyle = isHovered ? colors.accent : node.color;
        ctx.fill();

        // Render Tooltip Label for Hovered/Dragged Nodes
        if (isHovered) {
          ctx.font = "600 11px ui-sans-serif, system-ui, sans-serif";
          const labelText = `${node.label} (x:${Math.round(node.x)}, y:${Math.round(node.y)})`;
          const textWidth = ctx.measureText(labelText).width;

          // Label background badge
          ctx.fillStyle = "rgba(17, 20, 27, 0.9)";
          ctx.strokeStyle = colors.borderStrong;
          ctx.lineWidth = 1;
          const rectX = nx - textWidth / 2 - 8;
          const rectY = ny - 32;
          const rectW = textWidth + 16;
          const rectH = 22;

          ctx.beginPath();
          ctx.roundRect ? ctx.roundRect(rectX, rectY, rectW, rectH, 6) : ctx.rect(rectX, rectY, rectW, rectH);
          ctx.fill();
          ctx.stroke();

          // Label text
          ctx.fillStyle = colors.text;
          ctx.fillText(labelText, nx - textWidth / 2, ny - 17);
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      canvas.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
      canvas.removeEventListener("dblclick", handleDblClick);
    };
  }, [reduced]);

  if (reduced) {
    return (
      <div className="absolute inset-0 z-base pointer-events-none opacity-40 flex items-center justify-center">
        <svg className="w-full h-full" viewBox="0 0 1000 600" aria-label="Static semantic manifold grid">
          <line x1="100" y1="100" x2="300" y2="200" stroke={colors.edge} strokeWidth="1" />
          <line x1="300" y1="200" x2="500" y2="150" stroke={colors.edge} strokeWidth="1" />
          <line x1="500" y1="150" x2="800" y2="400" stroke={colors.trajectory} strokeWidth="2" strokeDasharray="4 4" />
          <circle cx="100" cy="100" r="4" fill={colors.node} />
          <circle cx="300" cy="200" r="4" fill={colors.node} />
          <circle cx="500" cy="150" r="5" fill={colors.conflict} />
          <circle cx="800" cy="400" r="4" fill={colors.trajectory} />
        </svg>
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 z-base w-full h-full select-none"
      data-testid="manifold-canvas"
    />
  );
}
