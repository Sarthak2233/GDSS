/**
 * Shared TypeScript contract for GDSS Local API (`gdss serve`).
 * Mirrors gdss/api/service.py response shapes — single source of truth for web/.
 */

/** Envelope for successful API responses */
export interface ApiOkEnvelope<T> {
  version?: string;
  timestamp?: string;
  repo?: string;
  status: "ok";
  data: T;
  warnings?: string[];
}

export interface ApiErrorEnvelope {
  status?: "error";
  error: {
    code: string;
    details: {
      what: string;
      why: string;
      fix: string;
    };
  };
}

export type ApiResponse<T> = ApiOkEnvelope<T> | ApiErrorEnvelope;

export interface HealthData {
  version: string;
  status: string;
  repo?: string | null;
}

export interface RemoteSyncInfo {
  label: string;
  ahead?: number;
  behind?: number;
}

export interface OperatorSummary {
  type: string;
  file: string;
  name?: string;
  symbol_id?: string;
  changed_block_count?: number;
}

export interface StatusData {
  active_branch: string;
  reference: string;
  remote_sync?: RemoteSyncInfo;
  committed_operators?: OperatorSummary[];
  uncommitted_operators?: OperatorSummary[];
}

export interface AffectedSymbol {
  id: string;
  name: string;
  distance?: number;
  reason?: string;
}

export interface ConflictProbability {
  score: number;
  reasons: string[];
  heuristic: "flat" | string;
}

export type ConvergenceLabel = "converging" | "diverging" | "stable";

export interface DriftBranch {
  branch: string;
  magnitude: number;
  tip_distance: number;
  trajectory_integral: number;
  velocity: number;
  convergence_score: number;
  convergence_label: ConvergenceLabel;
  affected: AffectedSymbol[];
  conflict_probability?: ConflictProbability;
  history?: DriftHistoryPoint[];
}

export interface DriftData {
  reference: string;
  drift: DriftBranch[];
}

export interface DriftAlertItem {
  branch: string;
  severity: "low" | "medium" | "high" | string;
  message: string;
  magnitude: number;
  affected: AffectedSymbol[];
}

export interface DriftHistoryPoint {
  timestamp: number;
  magnitude: number;
}

export interface DriftHistoryData {
  branch: string;
  history: DriftHistoryPoint[];
}

export interface BranchesData {
  branches: string[];
  all_branches?: string[];
  active_branch: string | null;
  repo: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  location: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
}

export interface GraphData {
  summary: { total_nodes: number; total_edges: number; [key: string]: unknown };
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SymbolItem {
  id: string;
  name: string;
  type: string;
  location: string;
}

export interface SymbolsData {
  symbols: SymbolItem[];
}

export interface LogCommit {
  sha: string;
  timestamp: string;
  operators: OperatorSummary[];
}

export interface SimilarHit {
  id: string;
  score: number;
  name: string;
  location: string;
}

export interface SimilarData {
  assistive: true;
  hits: SimilarHit[];
}

export interface EmbeddingProjectionPoint {
  id: string;
  name: string;
  type: string;
  location: string;
  x: number;
  y: number;
  z?: number;
}

export interface EmbeddingProjectionData {
  assistive: true;
  method: "pca" | string;
  dims: 2 | 3 | number;
  encoder: "bag" | "onnx" | string;
  dim_full: number;
  points: EmbeddingProjectionPoint[];
}

export type CommutativityClassLabel = "commute" | "interfere" | "independent";

export interface TensorEntry {
  i: string;
  j: string;
  omega: number;
  reasons: string[];
}

export interface CommutativityPair {
  a: string;
  b: string;
  class: CommutativityClassLabel | string;
}

/** Flat pairwise Omega from GET /v1/tensor (deterministic; not geometric). */
export interface TensorData {
  reference: string;
  form: "flat";
  branches: string[];
  entries: TensorEntry[];
  merge_risk: number;
  commutativity: CommutativityPair[];
  message?: string;
}

/** Evidence phase badge labels for honest UI depiction */
export type EvidencePhase =
  | "deterministic"
  | "assistive-heuristic"
  | "not-available";
