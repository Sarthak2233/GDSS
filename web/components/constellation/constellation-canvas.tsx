"use client";

import React, { useRef, useMemo, useCallback, useState, useEffect } from "react";
import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, Stars, Html } from "@react-three/drei";
import * as THREE from "three";
import { duration, easing } from "@/lib/motion";
import { colors } from "@/lib/tokens";
import type { GraphNode, GraphEdge } from "@/lib/constellation/constellation-engine";
import {
  NODE_COLORS,
  NODE_SCALES,
  NODE_OPACITIES,
} from "@/lib/constellation/constellation-engine";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export interface ConstellationCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeSelect?: (nodeId: string) => void;
  highlightedNodes?: Set<string>;
  selectedNodeId?: string | null;
}

interface SimNode {
  id: string;
  name: string;
  type: string;
  location: string;
  x: number;
  y: number;
  z: number;
}

/* ------------------------------------------------------------------ */
/*  3D layout: deterministic spiral sphere                            */
/* ------------------------------------------------------------------ */

function layoutNodes(nodes: GraphNode[]): SimNode[] {
  const result: SimNode[] = [];
  const total = nodes.length;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const spread = Math.max(40, Math.cbrt(total) * 8);

  for (let i = 0; i < total; i++) {
    const t = i / Math.max(1, total - 1);
    const inclination = Math.acos(1 - 2 * t);
    const azimuth = goldenAngle * i;
    const r = spread * Math.cbrt(t + 0.1);

    result.push({
      ...nodes[i],
      x: r * Math.sin(inclination) * Math.cos(azimuth),
      y: r * Math.sin(inclination) * Math.sin(azimuth),
      z: r * Math.cos(inclination),
    });
  }
  return result;
}

/* ------------------------------------------------------------------ */
/*  Instanced node spheres                                            */
/* ------------------------------------------------------------------ */

function NodeSpheres({
  simNodes,
  onNodeSelect,
  highlightedNodes,
  selectedNodeId,
  onNodeHover,
  connectedNodeIds,
}: {
  simNodes: SimNode[];
  onNodeSelect?: (id: string) => void;
  highlightedNodes?: Set<string>;
  selectedNodeId?: string | null;
  onNodeHover?: (node: SimNode | null) => void;
  connectedNodeIds?: Set<string>;
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colorArray = useMemo(() => new Float32Array(simNodes.length * 3), [simNodes.length]);

  const hasHighlight = highlightedNodes && highlightedNodes.size > 0;
  const hasTrace = Boolean(selectedNodeId && connectedNodeIds);

  useEffect(() => {
    if (!meshRef.current || typeof meshRef.current.setMatrixAt !== "function") return;
    const c = new THREE.Color();

    for (let i = 0; i < simNodes.length; i++) {
      const node = simNodes[i];
      const scale = (NODE_SCALES[node.type] ?? 0.8) * 0.5;
      let opacity = NODE_OPACITIES[node.type] ?? 0.8;

      if (hasHighlight && !highlightedNodes!.has(node.id)) {
        opacity = 0.08;
      }
      if (hasTrace) {
        if (selectedNodeId === node.id || connectedNodeIds?.has(node.id)) {
          opacity = 1.0;
        } else {
          opacity = 0.15;
        }
      }
      if (selectedNodeId === node.id) {
        opacity = 1.0;
      }

      dummy.position.set(node.x, node.y, node.z);
      const activeScale =
        selectedNodeId === node.id
          ? scale * 1.6
          : connectedNodeIds?.has(node.id)
          ? scale * 1.25
          : scale;
      dummy.scale.setScalar(activeScale);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);

      const hexColor = NODE_COLORS[node.type] ?? colors.accent;
      c.set(hexColor);
      colorArray[i * 3] = c.r * opacity;
      colorArray[i * 3 + 1] = c.g * opacity;
      colorArray[i * 3 + 2] = c.b * opacity;
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.geometry.attributes.color) {
      (meshRef.current.geometry.attributes.color as THREE.BufferAttribute).needsUpdate = true;
    }
  }, [simNodes, dummy, colorArray, hasHighlight, highlightedNodes, selectedNodeId, hasTrace, connectedNodeIds]);

  const handleClick = useCallback(
    (e: ThreeEvent<MouseEvent>) => {
      e.stopPropagation();
      if (e.instanceId !== undefined && onNodeSelect) {
        onNodeSelect(simNodes[e.instanceId].id);
      }
    },
    [simNodes, onNodeSelect]
  );

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, simNodes.length]}
      onClick={handleClick}
      onPointerOver={(e) => {
        e.stopPropagation();
        if (e.instanceId !== undefined && onNodeHover) {
          onNodeHover(simNodes[e.instanceId]);
        }
      }}
      onPointerOut={() => {
        if (onNodeHover) onNodeHover(null);
      }}
    >
      <sphereGeometry args={[1, 16, 12]}>
        <instancedBufferAttribute
          attach="attributes-color"
          args={[colorArray, 3]}
        />
      </sphereGeometry>
      <meshBasicMaterial vertexColors toneMapped={false} transparent opacity={0.9} />
    </instancedMesh>
  );
}

/* ------------------------------------------------------------------ */
/*  Small always-visible node labels in 3D canvas                     */
/* ------------------------------------------------------------------ */

function NodeLabels({
  simNodes,
  selectedNodeId,
  connectedNodeIds,
}: {
  simNodes: SimNode[];
  selectedNodeId?: string | null;
  connectedNodeIds?: Set<string>;
}) {
  return (
    <>
      {simNodes.map((n) => {
        const isSelected = selectedNodeId === n.id;
        const isConnected = connectedNodeIds?.has(n.id);
        const borderColor = NODE_COLORS[n.type] ?? colors.accent;

        return (
          <Html key={n.id} position={[n.x, n.y + 2.2, n.z]} center distanceFactor={30}>
            <div
              className={`px-1.5 py-0.5 rounded border bg-surface/90 backdrop-blur-xs font-mono text-[9px] text-text whitespace-nowrap shadow-sm select-none pointer-events-none transition-all ${
                isSelected
                  ? "ring-2 ring-accent font-bold scale-110"
                  : isConnected
                  ? "ring-1 ring-accent/60 font-semibold"
                  : "opacity-80 hover:opacity-100"
              }`}
              style={{ borderColor }}
            >
              {n.name || n.id}
            </div>
          </Html>
        );
      })}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Edge lines (Background + Traversed highlighted trace)             */
/* ------------------------------------------------------------------ */

function EdgeLines({
  simNodes,
  edges,
  highlightedNodes,
  selectedNodeId,
}: {
  simNodes: SimNode[];
  edges: GraphEdge[];
  highlightedNodes?: Set<string>;
  selectedNodeId?: string | null;
}) {
  const { normalPositions, tracePositions } = useMemo(() => {
    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
    const normalArr: number[] = [];
    const traceArr: number[] = [];
    const hasHighlight = highlightedNodes && highlightedNodes.size > 0;

    for (const e of edges) {
      const src = nodeMap.get(e.source as string);
      const tgt = nodeMap.get(e.target as string);
      if (!src || !tgt) continue;
      if (hasHighlight && !highlightedNodes!.has(src.id) && !highlightedNodes!.has(tgt.id)) {
        continue;
      }

      const isTraceEdge =
        selectedNodeId && (e.source === selectedNodeId || e.target === selectedNodeId);

      if (isTraceEdge) {
        traceArr.push(src.x, src.y, src.z, tgt.x, tgt.y, tgt.z);
      } else {
        normalArr.push(src.x, src.y, src.z, tgt.x, tgt.y, tgt.z);
      }
    }
    return {
      normalPositions: new Float32Array(normalArr),
      tracePositions: new Float32Array(traceArr),
    };
  }, [simNodes, edges, highlightedNodes, selectedNodeId]);

  return (
    <>
      {normalPositions.length > 0 && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[normalPositions, 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color={colors.edge} transparent opacity={0.15} />
        </lineSegments>
      )}
      {tracePositions.length > 0 && (
        <lineSegments>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[tracePositions, 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color={colors.accent} transparent opacity={0.85} />
        </lineSegments>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Reduced-motion table fallback                                     */
/* ------------------------------------------------------------------ */

function TableFallback({
  nodes,
  onNodeSelect,
  onNodeHover,
  selectedNodeId,
  connectedNodeIds,
}: {
  nodes: GraphNode[];
  onNodeSelect?: (id: string) => void;
  onNodeHover?: (node: GraphNode | null) => void;
  selectedNodeId?: string | null;
  connectedNodeIds?: Set<string>;
}) {
  return (
    <div
      className="w-full h-full overflow-auto rounded-xl border border-border bg-surface p-4"
      data-testid="constellation-table-fallback"
    >
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-border text-textMuted text-xs uppercase tracking-wider">
            <th className="p-2">Name</th>
            <th className="p-2">Type</th>
            <th className="p-2">Location</th>
            <th className="p-2">Traversal Trace</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((n) => {
            const isSelected = selectedNodeId === n.id;
            const isConnected = connectedNodeIds?.has(n.id);
            return (
              <tr
                key={n.id}
                className={`border-b border-border/50 hover:bg-surfaceElevated cursor-pointer transition-colors ${
                  isSelected ? "bg-accent/15" : isConnected ? "bg-accent/5" : ""
                }`}
                onClick={() => onNodeSelect?.(n.id)}
                onMouseEnter={() => onNodeHover?.(n)}
                onMouseLeave={() => onNodeHover?.(null)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") onNodeSelect?.(n.id);
                }}
              >
                <td className="p-2 text-text font-semibold">{n.name || n.id}</td>
                <td className="p-2">
                  <span
                    className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                    style={{
                      backgroundColor: `${NODE_COLORS[n.type] ?? colors.accent}22`,
                      color: NODE_COLORS[n.type] ?? colors.accent,
                    }}
                  >
                    {n.type}
                  </span>
                </td>
                <td className="p-2 text-textSubtle font-mono text-xs">{n.location || "—"}</td>
                <td className="p-2 text-xs font-mono">
                  {isSelected ? (
                    <span className="text-accent font-bold">Selected Node</span>
                  ) : isConnected ? (
                    <span className="text-accent/80">Traversed Neighbor</span>
                  ) : (
                    <span className="text-textMuted/60">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main ConstellationCanvas                                          */
/* ------------------------------------------------------------------ */

export function ConstellationCanvas({
  nodes,
  edges,
  onNodeSelect,
  highlightedNodes,
  selectedNodeId,
}: ConstellationCanvasProps) {
  const [reduceMotion, setReduceMotion] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduceMotion(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReduceMotion(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  const simNodes = useMemo(() => layoutNodes(nodes), [nodes]);

  // Compute traversal trace statistics when selectedNodeId changes
  const { selectedNode, connectedNodeIds, callersCount, depsCount } = useMemo(() => {
    if (!selectedNodeId) {
      return {
        selectedNode: null,
        connectedNodeIds: new Set<string>(),
        callersCount: 0,
        depsCount: 0,
      };
    }
    const sel = nodes.find((n) => n.id === selectedNodeId) || null;
    const connected = new Set<string>();
    let callers = 0;
    let deps = 0;

    for (const e of edges) {
      if (e.target === selectedNodeId) {
        connected.add(e.source as string);
        callers++;
      } else if (e.source === selectedNodeId) {
        connected.add(e.target as string);
        deps++;
      }
    }
    return {
      selectedNode: sel,
      connectedNodeIds: connected,
      callersCount: callers,
      depsCount: deps,
    };
  }, [selectedNodeId, nodes, edges]);

  const renderTooltip = () => {
    if (!hoveredNode) return null;
    return (
      <div
        role="tooltip"
        data-testid="constellation-hover-tooltip"
        className="absolute top-4 right-4 z-20 pointer-events-none max-w-xs p-3 rounded-lg border border-border bg-card/95 backdrop-blur-md shadow-xl space-y-1 text-left"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-sm text-foreground truncate">
            {hoveredNode.name || hoveredNode.id}
          </span>
          <span
            className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: `${NODE_COLORS[hoveredNode.type] ?? colors.accent}22`,
              color: NODE_COLORS[hoveredNode.type] ?? colors.accent,
            }}
          >
            {hoveredNode.type}
          </span>
        </div>
        {hoveredNode.location && (
          <p className="font-mono text-xs text-muted-foreground truncate">{hoveredNode.location}</p>
        )}
        <p className="text-[10px] text-primary pt-0.5 font-medium">
          Click sphere to inspect & traverse connections
        </p>
      </div>
    );
  };

  const renderTraversalTraceHud = () => {
    if (!selectedNode) return null;
    return (
      <div
        data-testid="traversal-trace-hud"
        className="absolute top-4 left-4 z-20 max-w-md p-3 rounded-xl border border-accent/40 bg-surfaceGlass backdrop-blur-md shadow-xl flex items-center justify-between gap-4"
      >
        <div className="flex flex-col text-left">
          <span className="text-xs font-semibold text-text">
            Active Traversal Trace: <strong className="text-accent">{selectedNode.name || selectedNode.id}</strong>
          </span>
          <span className="text-[11px] text-textMuted font-mono">
            {connectedNodeIds.size} connected symbols ({callersCount} callers, {depsCount} dependencies)
          </span>
        </div>
        <button
          type="button"
          onClick={() => onNodeSelect?.("")}
          aria-label="Clear Trace"
          className="px-2.5 py-1 rounded-lg border border-border bg-surface hover:bg-surfaceElevated text-xs font-semibold text-textMuted hover:text-text transition-colors"
        >
          Clear Trace
        </button>
      </div>
    );
  };

  if (reduceMotion) {
    return (
      <div className="w-full h-full relative">
        {renderTraversalTraceHud()}
        <TableFallback
          nodes={nodes}
          onNodeSelect={onNodeSelect}
          onNodeHover={(n) => setHoveredNode(n)}
          selectedNodeId={selectedNodeId}
          connectedNodeIds={connectedNodeIds}
        />
        {renderTooltip()}
      </div>
    );
  }

  return (
    <div
      className="w-full h-full relative"
      data-testid="constellation-canvas"
      role="img"
      aria-label={`3D code constellation with ${nodes.length} symbols and ${edges.length} connections`}
    >
      {renderTraversalTraceHud()}
      {renderTooltip()}
      <Canvas
        camera={{ position: [0, 0, 80], fov: 60 }}
        style={{ background: colors.bg }}
        dpr={[1, 1.5]}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[50, 50, 50]} intensity={0.8} />

        <Stars radius={200} depth={100} count={300} factor={2} saturation={0} fade speed={0} />

        <NodeSpheres
          simNodes={simNodes}
          onNodeSelect={onNodeSelect}
          highlightedNodes={highlightedNodes}
          selectedNodeId={selectedNodeId}
          onNodeHover={(node) => setHoveredNode(node)}
          connectedNodeIds={connectedNodeIds}
        />
        <NodeLabels
          simNodes={simNodes}
          selectedNodeId={selectedNodeId}
          connectedNodeIds={connectedNodeIds}
        />
        <EdgeLines
          simNodes={simNodes}
          edges={edges}
          highlightedNodes={highlightedNodes}
          selectedNodeId={selectedNodeId}
        />

        <OrbitControls
          enableDamping
          dampingFactor={0.12}
          minDistance={10}
          maxDistance={300}
          enablePan
        />
      </Canvas>
    </div>
  );
}
