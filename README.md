# GDSS: Geometric Distributed Software Synchronizer

<div align='center'>

![Python Version](https://img.shields.io/badge/python-3.10+%2B-blue.svg)
![Architecture](https://img.shields.io/badge/Architecture-10--Layer-blueviolet.svg)

</div>
A Semantic Intelligence Layer Above Git that transforms traditional, text-based software collaboration into continuous geometric-semantic manifold synchronization. 

---

## 📖 Project Overview

### The Philosophy: Code as a Semantic Manifold 

Could the geodesic output enviroment be in 3D for Merge id what I believe. 

Traditional version control systems (like Git) treat code as static, flat lines of text. Merges are done by string matching (diffs), which frequently leads to syntax breaks, silent semantic failures, and costly merge conflicts.

GDSS reframes software evolution through **Differential Geometry** and **Operator Algebra**:

| Concept | Traditional Git | GDSS Mathematical Mapping |
| :--- | :--- | :--- |
| **Codebase** | Files & lines of text | Semantic manifold $\mathcal{M}$ |
| **Commit** | String diff patch | Tangent vector/operator $dC$ |
| **Branch** | Commits list | Trajectory $\gamma_i(t) = \int dC_i$ |
| **Conflict** | Text overlap | Non-commutativity $[\mathcal{T}_i, \mathcal{T}_j] \neq 0$ |
| **Merge** | String alignment | Geometric path convergence |

<p align="center">
  <img src="./assets/diagrams/pipeline.svg" alt="GDSS pipeline" width="100%">
</p>

<details>
<summary>📐 Mermaid source (click to expand)</summary>

```mermaid
flowchart LR
    subgraph Repo["📁 Raw Repository"]
        RepoFile[("🗄️ Files & Commits")]
    end

    AST[/'⚙️ AST Parser Engine'/]
    TX[("🔄 Transformation Operator<br>Engine")]
    DG[("🔗 Dependency<br>Graph Builder")]
    SM[/'🧠 Semantic Manifold<br>Model'/]

    RepoFile --> AST --> TX --> DG --> SM

    style RepoFile fill:#06b6d4,stroke:#035e66,stroke-width:2px,color:#02111a
    style AST fill:#2563eb,stroke:#1e40af,stroke-width:2px,color:#fff
    style TX fill:#7c3aed,stroke:#4c1d95,stroke-width:2px,color:#fff
    style DG fill:#f59e0b,stroke:#92400e,stroke-width:2px,color:#fff
    style SM fill:#10b981,stroke:#065f46,stroke-width:2px,color:#fff

    linkStyle default stroke:#94a3b8,stroke-width:1.5px
```

</details>

---

## 🚀 Quick Start & Usage

### 🛠 Installation

GDSS is designed to run locally on low-end hardware without requiring a GPU.

```bash
# Clone the repository and install in editable mode
git clone https://github.com/sbasnet/GDSS.git
cd GDSS
pip install -e .
```

### 💻 CLI Operations

GDSS provides both a standard CLI and a rich interactive shell for deep repository awareness.

```bash
# 1. Start the GDSS Interactive Shell (Recommended)
gdss start

# 2. Check active branch trajectory divergence (one-off)
gdss status

# 3. View semantic transformation log
gdss log -n 5
```

#### Interactive Shell Commands:
- `status`: Show distributed status and semantic drift.
- `analyze`: Deep semantic analysis and dependency mapping of the codebase.
- `impact <symbol>`: Analyze downstream impact of a specific symbol.
- `log`: Show semantic commit log.
- `watch`: Real-time monitoring of the distributed event bus.
- `hierarchy`: Show the distributed priority chain.
- `clear`: Clear the console and show the banner.

---

## 🗺 Project Direction & Phases

This section details the development roadmap towards building the full 10-layer GDSS architecture.

### Current Status: **Phase 0 & 1 Complete (45%)**

The **Distributed Runtime Foundation (Phase 0)** is fully implemented and optimized, providing GitHub awareness, local/remote observers, an event bus, and a rich interactive interface.

<p align="center">
  <img src="./assets/diagrams/roadmap.svg" alt="Roadmap — Phase status" width="100%">
</p>

<details>
<summary>🗺️ Mermaid source (click to expand)</summary>

```mermaid
graph TD
    subgraph Done["✅ Completed - 40%"]
        P1["Phase 1: AST & Dependency Graph"]
    end
    
    subgraph Next["🚀 In Progress"]
        P2["Phase 2: Semantic Embeddings<br>(all-MiniLM-L6-v2 ONNX)"]
    end
    
    subgraph Future["🔮 Planned"]
        P3["Phase 3: Continuous Drift Monitor"]
        P4["Phase 4: Conflict Tensor"]
        P5["Phase 5: AI Semantic Rebase"]
        P6["Phase 6: Validation Sandbox"]
        P7["Phase 7: Geometric Research Library"]
    end
    
    P1 --> P2
    P2 --> P3
    P3 --> P4
    P4 --> P5
    P5 --> P6
    P6 --> P7

    style Done fill:#16a34a,stroke:#15803d,stroke-width:2px,color:#fff
    style Next fill:#2563eb,stroke:#1d4ed8,stroke-width:2px,color:#fff
    style Future fill:#475569,stroke:#334155,stroke-width:2px,color:#fff
```

</details>


## 🔬 Core Concepts

### Branch Drift Energy

GDSS quantifies how far a branch has diverged from the main semantic manifold:

$$I(B_i) = \int_0^T \| \dot{\gamma}_i(t) - \dot{\gamma}_{\text{main}}(t) \|_{\mathcal{M}} \, dt$$

- **Low drift** → Seamless integration
- **High drift** → Automatic conflict anticipation

### Conflict Tensor

Branch interaction matrix $\Omega_{ij}$ predicts merge compatibility before checkout:

<p align="center">
  <img src="./assets/diagrams/conflict_tensor.svg" alt="Conflict Tensor Matrix" width="100%">
</p>

<details>
<summary>⚡ Mermaid source (click to expand)</summary>

```mermaid
flowchart LR
    subgraph Branches["🌿 Branch Manifold"]
        A["Feature A"]
        B["Feature B"]
        C["Main"]
    end
    
    A -- "Ω₁₂ = 0.12" --> Conflict["✅ Compatible Merge"]
    B -- "Ω₂₃ = 0.89" --> Conflict2["⚠️ Conflict Predicted"]
    C -- "Ω₁₃ = 0.05" --> Conflict3["✅ Clean Merge"]
    
    style A fill:#3b82f6,stroke:#1e3a8a,color:#fff
    style B fill:#f97316,stroke:#9a3412,color:#fff
    style C fill:#10b981,stroke:#065f46,color:#fff
    style Conflict fill:#22c55e,stroke:#166534,color:#fff
    style Conflict2 fill:#ef4444,stroke:#7f1d1d,color:#fff
    style Conflict3 fill:#22c55e,stroke:#166534,color:#fff

    linkStyle 0,2 stroke:#22c55e,stroke-width:2px
    linkStyle 1 stroke:#ef4444,stroke-width:2px
```

</details>

### Semantic Merge Geometry

<p align="center">
  <img src="./assets/diagrams/merge_geometry.svg" alt="Semantic Merge Geometry" width="100%">
</p>

<details>
<summary>🌀 Mermaid source (click to expand)</summary>

```mermaid
flowchart TB
    subgraph Manifold["🌐 Semantic Manifold M"]
        A["Branch A trajectory γ₁(t)"]
        B["Branch B trajectory γ₂(t)"]
        C["Geodesic merge path<br>optimal convergence"]
    end

    A -- "non-commuting operators" --> Conflict["⚠️ Conflict Tensor Ω₁₂ ≠ 0"]
    B -- "divergence drift" --> Conflict
    Conflict -- "geometric correction" --> C

    style A fill:#3b82f6,stroke:#1e3a8a,color:#fff
    style B fill:#f97316,stroke:#9a3412,color:#fff
    style Conflict fill:#ef4444,stroke:#7f1d1d,color:#fff
    style C fill:#10b981,stroke:#065f46,color:#fff
    style Manifold fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,stroke-dasharray: 5,color:#422006
```

</details>

---

## 📊 Architecture Overview

<p align="center">
  <img src="./assets/diagrams/architecture.svg" alt="GDSS Architecture Overview" width="100%">
</p>

<details>
<summary>🏗️ Mermaid source (click to expand)</summary>

```mermaid
flowchart TD
    subgraph Input["📥 Input Layer"]
        Git[Git Repository]
        Files[Source Files]
    end
    
    subgraph Processing["⚙️ Processing Pipeline"]
        AST[AST Parser]
        Embed[Semantic Embedder]
        Graph[Dependency Graph]
        Manifold[Manifold Builder]
    end
    
    subgraph Analysis["📈 Analysis Layer"]
        Drift[Drift Monitor]
        Tensor[Conflict Tensor]
        Predict[Predictive Engine]
    end
    
    subgraph Output["💡 Output Layer"]
        Status[Branch Status]
        Warnings[Conflict Warnings]
        Suggestions[Resolution Suggestions]
    end
    
    Input --> Processing
    Processing --> Analysis
    Analysis --> Output
    
    style Input fill:#1e293b,stroke:#475569,color:#fff
    style Processing fill:#1e40af,stroke:#3b82f6,color:#fff
    style Analysis fill:#7c3aed,stroke:#a78bfa,color:#fff
    style Output fill:#065f46,stroke:#10b981,color:#fff
```

</details>

---
### Next Milestones:
1. **Phase 2 (Embeddings)**: Integrate local all-MiniLM-L6-v2 ONNX embeddings to represent codebase symbols in $\mathbb{R}^d$.
2. **Phase 3 (Drift Monitoring)**: Compute branch drift energy: $I(B_i) = \int \|B_i(t) - D(t)\| dt$.
3. **Phase 4 (Conflict Tensor)**: Compute branch interaction matrix $\Omega_{ij}$ to predict merge compatibility before checkout.

---

<p align="center">
  <b>GDSS</b> &copy; 2026<br>
  Maintained by <b><a href="https://github.com/sbasnet">S. Basnet</a></b>
</p>

