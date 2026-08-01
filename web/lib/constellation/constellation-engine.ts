/**
 * GDSS 3D force simulation engine.
 *
 * Wraps d3-force-3d to compute 3D positions for the code graph.
 * Outputs { x, y, z } per node for consumption by Three.js.
 */

export interface GraphNode {
  id: string;
  name: string;
  type: "file" | "function" | "class" | "module_dependency" | string;
  location: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: "imports" | "defines" | "calls" | string;
}

export interface GraphSummary {
  total_nodes: number;
  total_edges: number;
  node_types: Record<string, number>;
  edge_relations: Record<string, number>;
}

export interface GraphResponse {
  summary: GraphSummary;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SimilarHit {
  id: string;
  score: number;
  name: string;
  location: string;
}

export interface SimilarResponse {
  assistive: boolean;
  hits: SimilarHit[];
}

export interface SimulationNode extends GraphNode {
  x: number;
  y: number;
  z: number;
  vx: number;
  vy: number;
  vz: number;
  index?: number;
}

export interface SimulationEdge {
  source: SimulationNode | string;
  target: SimulationNode | string;
  relationship: string;
}

import { colors } from "@/lib/tokens";

/**
 * Node color mapping by type, using GDSS design tokens.
 */
export const NODE_COLORS: Record<string, string> = {
  function: colors.success,
  class: colors.merge,
  file: colors.accent,
  module_dependency: colors.textSubtle,
};

/**
 * Node scale mapping by type.
 */
export const NODE_SCALES: Record<string, number> = {
  function: 1.0,
  class: 1.3,
  file: 0.8,
  module_dependency: 0.5,
};

/**
 * Node opacity mapping by type.
 */
export const NODE_OPACITIES: Record<string, number> = {
  function: 1.0,
  class: 1.0,
  file: 0.8,
  module_dependency: 0.3,
};
