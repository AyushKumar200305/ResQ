# ResQ — Algorithmic Disaster Evacuation & Resource Routing System

[![Python 3.14](https://img.shields.io/badge/python-3.14.7%20tested-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6.svg)](https://www.typescriptlang.org)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-4-38B2AC.svg)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/tests-159%20passed-brightgreen.svg)]()

ResQ is an algorithmic decision-support platform designed to model municipal evacuation logistics and relief resource distribution under crisis scenarios. It models urban road networks as capacitated directed graphs, solves system-optimal network flow and shortest-path problems from first principles, and evaluates shelter resource allocations using structured humanitarian planning figures.

The system is a **deterministic, scenario-based simulation and decision-support tool**. It does not ingest live GPS, IoT sensor, or real-time telemetry feeds. All outputs are computed directly by internal Python solvers on loaded network graph models.

---

## 1. Problem Formulation

During municipal emergencies (e.g., riverine flash floods, bridge structural failures), road networks experience localized capacity degradation, node isolation, and sharp outward evacuation demand. Uncoordinated routing heuristics (such as selfish shortest-path navigation) route evacuees onto common arterials, causing severe congestion collapses.

ResQ addresses this coordination challenge through four discrete algorithmic capabilities:
1. **System-Optimal Multi-Source Multi-Sink Evacuation:** Maximizes total evacuee clearance rate (people/hour) by executing Dinic's Algorithm on an augmented directed residual network with virtual Super-Source ($S^*$) and Super-Sink ($T^*$).
2. **Physical Bottleneck Identification:** Identifies saturated cut edges using the Max-Flow Min-Cut Theorem to determine binding throughput constraints.
3. **Emergency Point-to-Point Transit:** Computes shortest-distance routes using binary min-heap Dijkstra and computes second-shortest simple bypass paths via Yen's K=2 algorithm.
4. **Relief Resource Distribution:** Evaluates multi-resource shelter demands (drinking water, food rations, medical kits, medicines, bedding, hygiene kits) and allocates limited central depot inventory via proportional fair-share allocation using Hamilton's largest-remainder method.

---

## 2. Implemented Algorithms & Complexity

All core algorithms are implemented from scratch in pure Python (`resq/algorithms/`) without external graph solver libraries:

| Algorithm | Module | Worst-Case Time | Auxiliary Space | Implementation Mechanism |
| :--- | :--- | :--- | :--- | :--- |
| **Dinic's Maximum Flow** | `resq/algorithms/dinic.py` | $O(V^2 E)$ | $O(V + E)$ | Two-phase solver: at most $V - 1$ BFS level-graph phases; each blocking flow is computed in $O(VE)$ via DFS with `ptr[u]` current-edge pointer pruning. Backwards residual edges enable rerouting. |
| **Max-Flow Min-Cut** | `resq/algorithms/min_cut.py` | $O(V + E)$ | $O(V + E)$ | BFS reachability on residual graph $G_f$ from $S^*$ following $c_f > 0$. Saturated edges bridging $(S^*, T^*)$ partition form the minimum cut. |
| **Dijkstra Shortest Path** | `resq/algorithms/dijkstra.py` | $O((V + E) \log E)$<br>*($O((V+E)\log V)$ on simple graphs)* | $O(V + E)$ | Adjacency list with indexed integer vertices and binary min-heap (`heapq`). Lazy deletion prunes duplicate entries in $O(1)$. General multigraph bound accounts for parallel road edges. |
| **Yen's K=2 Detour** | `resq/algorithms/dijkstra.py` | $O(P \cdot (V + E) \log E)$<br>*($P \le V - 1$)* | $O(V + E)$ | Runs Dijkstra across $P$ spur positions along the primary path with root nodes and spur edges blocked; stores single best alternative candidate. |
| **Greedy: Shortest Hop** | `resq/algorithms/greedy.py` | $O(k \cdot (V + E))$<br>*($k \le E$)* | $O(V + E)$ | Forward-only BFS augmenting path. Never uses backward residual edges; permanently saturates at least one edge per augmentation. |
| **Greedy: Widest Path** | `resq/algorithms/greedy.py` | $O(k \cdot (V + E) \log E)$<br>*($k \le E$)* | $O(V + E)$ | Forward-only priority queue (`heapq`) maximizing bottleneck capacity $\min_{e \in P} c(e)$ with minimum-hop tie breaking. |
| **Greedy: Lexicographic DFS** | `resq/algorithms/greedy.py` | $O(k \cdot (V + E))$<br>*($k \le E$)* | $O(V + E)$ | Forward-only iterative DFS traversing alphabetically sorted outgoing edges. |

*Empirical Execution Note:* On the baseline 11-node, 15-road network (`metro_flood_baseline.json`), Dinic achieves the optimal 2,250 p/h flow in **1 active BFS phase** (2 total BFS calls) and **8 augmentations** (observed execution time ~0.32 ms on the test benchmark host). The playback animation sequence produces **9 frames** on this baseline (Frame 0 initial state + 8 augmentation steps). On general networks with $k$ augmentations, playback dynamically produces $1 + k$ frames.

---

## 3. System Architecture & Component Interaction

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RESQ ARCHITECTURE                                   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   ┌─────────────────────────────────────────┐   ┌──────────────────────────────────┐   │
│   │   Enterprise React + TS Frontend        │   │   Legacy Streamlit Fallback      │   │
│   │   (Vite, TailwindCSS, Lucide Icons)     │   │   (app.py - Standalone Script)   │   │
│   │   Port: 5173                            │   │   Port: 8501                         │   │
│   └────────────────────┬────────────────────┘   └─────────────────┬────────────────┘   │
│                        │ HTTP REST                                │ Python Direct      │
│                        ▼                                          │ Import             │
│   ┌─────────────────────────────────────────┐                     │                    │
│   │   FastAPI REST API Backend              │                     │                    │
│   │   (backend/main.py, Port: 8000)         │                     │                    │
│   │   - 8 Routers, 42 API Route Operations  │                     │                    │
│   │   - In-Memory StateManager (RAM)        │                     │                    │
│   └────────────────────┬────────────────────┘                     │                    │
│                        │ Python Calls                             │                    │
│                        ▼                                          ▼                    │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │   Core Python Engine (resq/)                                                   │   │
│   │   - resq/algorithms/ (Dinic, Dijkstra, Min-Cut, Greedy, FlowBuilder)           │   │
│   │   - resq/domain/     (EvacuationNetwork, Node, Road, Shelter, Zone)            │   │
│   │   - resq/services/   (DinicSolver, DijkstraSolver, CampResourceService)        │   │
│   └─────────────────────────────────────────┬──────────────────────────────────────┘   │
│                                             │ File Read (Read-Only)                    │
│                                             ▼                                          │
│                        ┌─────────────────────────────────────────┐                     │
│                        │   JSON Scenario Presets (data/scenarios)│                     │
│                        │   - metro_flood_baseline.json           │                     │
│                        │   - bridge_collapse_crisis.json         │                     │
│                        │   - coastal_cyclone_surge.json          │                     │
│                        │   - greedy_trap_benchmark.json          │                     │
│                        │   - presentation_demo_dataset.json      │                     │
│                        └─────────────────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Architectural Distinctions:
* **Streamlit Monolith:** `app.py` directly imports the domain and services layer (`from resq.services import ...`). It operates independently without communicating through FastAPI.
* **FastAPI Service:** The React frontend communicates strictly via HTTP REST endpoints (`http://localhost:8000/api/...`).
* **In-Memory State Lifecycle:** `backend/state.py` maintains graph state in RAM. If the backend process restarts, all dynamic edits made in the Network Builder reset back to `metro_flood_baseline.json`. There is no SQL/NoSQL database.

---

## 4. API Endpoints Contract

The backend exposes **42 API route operations across 36 distinct `/api` paths** (plus 1 root `GET /` endpoint):

| Router | Method & Exact Route | Description |
| :--- | :--- | :--- |
| **Solve** | `POST /api/solve/dinic`<br>`GET /api/solve/dinic` | Computes or retrieves Dinic maximum flow and execution metrics. |
| | `POST /api/solve/mincut`<br>`GET /api/solve/mincut` | Extracts saturated minimum-cut partition $(S^*, T^*)$. |
| | `POST /api/solve/full` | Runs complete diagnostics (Dinic, MinCut, decomposition, wave timeline). |
| | `GET /api/solve/trace` | Returns step-by-step BFS levels and DFS augmentation traces. |
| | `POST /api/solve/playback` | Generates $1 + k$ animation frames from Dinic's trace (9 frames on baseline). |
| | `POST /api/solve/waves` | Generates hour-by-hour population clearance projections. |
| **Network** | `GET /api/network`<br>`POST /api/network` | Retrieves or replaces the active evacuation network. |
| | `POST /api/network/demo` | Resets active network to demo baseline. |
| | `GET /api/network/presets` | Lists available JSON preset scenario keys. |
| | `POST /api/network/presets/{preset_key}` | Loads a specific preset into memory. |
| | `GET /api/network/validate` | Validates graph connectivity and capacity invariants. |
| | `POST /api/network/nodes`<br>`PUT /api/network/nodes/{node_id}`<br>`DELETE /api/network/nodes/{node_id}` | Adds, updates, or deletes network nodes. |
| | `POST /api/network/roads`<br>`PUT /api/network/roads/{road_id}`<br>`DELETE /api/network/roads/{road_id}` | Adds, updates, or deletes directed roads. |
| **Comparison** | `POST /api/comparison/greedy` | Executes Dinic vs. 3 Greedy strategies on active network. |
| | `POST /api/comparison/benchmark` | Loads Greedy Trap benchmark and evaluates optimality gap. |
| **Dijkstra** | `POST /api/dijkstra/solve` | Computes shortest-distance route and Yen K=2 bypass detour. |
| **Relief** | `GET /api/relief/priorities` | Evaluates hazard triage priority ranking for affected areas. |
| | `GET /api/relief/routes` | Generates evacuation route advisories (primary, alternative, safety status). |
| | `POST /api/relief/routes/verify` | Updates operational safety verification status of a road. |
| | `GET /api/relief/shelters` | Assesses shelter occupancy and projected saturation. |
| | `POST /api/relief/resources`<br>`GET /api/relief/resources` | Computes camp resource demands and allocates depot stock. |
| | `GET /api/relief/overview` | Returns consolidated relief executive briefing. |
| **Reports** | `GET /api/reports/json` | Exports active network and solution as JSON file. |
| | `GET /api/reports/csv/roads` | Exports road flow and residual capacity telemetry as CSV. |
| | `GET /api/reports/csv/scenarios` | Exports multi-scenario comparative metrics as CSV. |
| | `GET /api/reports/pdf` | Generates and streams executive evacuation summary PDF. |
| **Scenarios** | `POST /api/scenarios/baseline`<br>`POST /api/scenarios/road-closure`<br>`POST /api/scenarios/reduced-shelter`<br>`POST /api/scenarios/increased-shelter`<br>`POST /api/scenarios/multi-road-failure`<br>`POST /api/scenarios/custom`<br>`POST /api/scenarios/all` | Runs preset or custom disaster disruptions and multi-scenario matrices. |
| **Health** | `GET /api/health` | Returns backend operational health and active scenario key. |

---

## 5. Relief Resource Allocation Logic

The camp resource module evaluates multi-resource demands across shelters over a planning horizon:

* **Official Sphere Standards Reference (*The Sphere Handbook*, 4th ed., 2018):**
  * Water Standard 2.1: **15 L / person / day** basic survival water planning figure (covers survival drinking 2.5–3 L/day, basic sanitation, and basic cooking combined).
  * Food Security Standard 1.1: **2,100 kcal / person / day** nutritional intake benchmark (specifies energy requirement, not meal frequency).
* **Project-Configured Default Rates (`ResourceConsumptionConfig`):**
  * Direct Drinking Water: **3.0 L / person / day** (direct emergency hydration distribution).
  * Food Rations: **2.0 meal rations / person / day**.
  * Trauma & First-Aid Kits: **0.05 kits / person** (1 kit per 20 evacuees; project planning assumption).
  * Essential Medicines: **0.10 doses / person / day**.
  * Emergency Bedding: **1.0 unit / person**.
  * Hygiene Packs: **0.20 packs / person** (1 pack per 5 evacuees).

*Allocation Method:*
Depot inventory is distributed using **proportional fair-share allocation with Hamilton's largest-remainder method**. In scarcity, each shelter receives an integer floor proportional to its net demand share, and remaining units are awarded to shelters with the largest fractional remainders.

*Baseline Evaluation (3-Day Horizon, 2,250 Evacuees):*
* Central Depot Stock: Water 28,000 L, Food 18,000 rations, Medical Kits **500 kits**, Medicines 1,200 doses, Bedding 4,000 units, Hygiene 1,000 packs.
* Medical Kit Demand: Shelter North (950) = 48 kits; Shelter South (800) = 40 kits; Shelter East (500) = 25 kits $\implies$ **Total Demand = 113 kits**.
* Allocation: All 113 kits are allocated (100% satisfaction); **387 kits remain in central depot inventory**.

---

## 6. Installation & Setup

### Prerequisites
* **Operating System:** Tested on Windows 11 (Expected cross-platform compatibility on Linux / macOS via standard Python and Node.js toolchains).
* **Python:** Tested and verified on Python 3.14.7. Compatibility with other Python versions has not been independently verified.
* **Node.js:** Tested and verified on **Node.js v24.19.0** and **npm 11.17.0**.

### Backend Setup
```powershell
# Clone the repository
git clone https://github.com/AyushKumar200305/ResQ.git
cd ResQ

# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI backend (Port 8000)
python -m uvicorn backend.main:app --port 8000 --reload
```
*API interactive documentation: `http://localhost:8000/docs`*

### Frontend Setup
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
*Frontend application: `http://localhost:5173`*

### Verification Tests
```powershell
# Run backend pytest suite (159 tests passing)
python -m pytest

# Run frontend production build check (0 errors)
cd frontend
npm run build
```

### Standalone Fallback UI (Streamlit)
```powershell
streamlit run app.py
```
*Runs on `http://localhost:8501` without requiring FastAPI or Node.js.*
