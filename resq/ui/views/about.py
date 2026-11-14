"""Page 9: About ResQ (Algorithm Architecture & DAA Theory Reference)."""

import streamlit as st


def render_about_resq_page() -> None:
    """Render DAA algorithmic reference, complexity proofs, and engineering notes."""
    st.markdown(
        '<div class="resq-section-title">System Overview & Mathematical Formulation</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
**ResQ** models a disaster-impacted region as a directed weighted-capacity network $G = (V, E, c)$
to optimize multi-zone evacuation throughput and isolate exact infrastructural bottlenecks.

1. **Multi-Source & Multi-Shelter Reduction:**
   - A virtual **Super-Source ($S^*$)** connects to every affected area $s_i$ with capacity equal to its evacuee population $P(s_i)$.
   - Every shelter $t_j$ connects to a virtual **Super-Sink ($T^*$)** with capacity equal to its bed capacity $C(t_j)$.
   - Physical roads $(u \\to v)$ carry non-negative integer capacities $c(u, v)$, keeping original modeled capacities strictly separated from mutable residual capacities.
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="resq-section-title">Dinic\'s Maximum Flow (From Scratch)</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
- **Phase 1 — BFS Level Graph ($O(V + E)$):**
  Starts at $S^*$ and traverses edges with positive residual capacity ($c_f(u,v) > 0$) to assign shortest-hop levels `level[v] = level[u] + 1`. Terminates immediately when $T^*$ becomes unreachable.
- **Phase 2 — DFS Blocking Flow ($O(VE)$ per phase):**
  Routes flow strictly along level-advancing edges (`level[v] == level[u] + 1`) using a **current-edge pointer (`ptr[u]`)** so exhausted dead ends are skipped in $O(1)$ amortized time.
- **Residual Reverse Edges:**
  Every directed road $(u, v)$ is paired with a $0$-capacity reverse edge $(v, u)$. Pushing $\\Delta$ forward increases backward residual capacity by $\\Delta$, enabling later phases to cancel suboptimal shortcuts and reroute flow globally.
- **Worst-Case Complexity:** $O(V^2 E)$ on general directed networks (at most $V - 1$ phases because `level[T*]` strictly increases each phase).
            """
        )

    with c2:
        st.markdown(
            '<div class="resq-section-title">Minimum Cut & Greedy Baseline</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            """
- **Minimum Cut Extraction:**
  Upon Dinic termination, a residual BFS from $S^*$ partitions vertices into **Reachable ($A$)** and **Unreachable ($B$)**. Every forward edge crossing $A \\to B$ forms the minimum cut, satisfying the **Max-Flow Min-Cut Theorem**:
  $$|f^*| = \\sum_{(u,v) \\in E,\\; u \\in A,\\; v \\in B} c(u,v)$$
- **Semantic Bottleneck Separation:**
  ResQ separates cut edges into **Road Corridor Bottlenecks**, **Shelter Capacity Limits** ($t_j \\to T^*$), and **Source Demand Limits** ($S^* \\to s_i$), while filtering out saturated non-cut roads whose endpoints both lie inside $A$ or $B$.
- **Why Greedy Baseline Fails:**
  Forward-only heuristics (*Shortest-Hop*, *Widest-Path*, *Lexicographic DFS*) never traverse backward residual edges. Committing flow early to a shared shortcut permanently blocks parallel corridors, exposing quantifiable optimality gaps on cross-linked networks.
            """
        )

    st.markdown(
        '<div class="resq-section-title">Optional Educational Extension: Dijkstra\'s Shortest Path</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
- **Data Structures & Complexity ($O((V + E) \\log V)$):**
  Uses a directed **adjacency list** weighted by non-negative road distances (`distance >= 0`, strictly separate from integer road capacities) paired with Python's `heapq` **binary min-heap** and lazy deletion.
- **Alternative Route Search:**
  Computes a second-shortest simple path (`Yen's k=2 spur step`) when another distinct corridor exists from the chosen affected area to the selected shelter.
- **Shortest Path vs. Maximum Flow Distinction:**
  Dijkstra solves **single-pair uncapacitated distance minimization** ($\\min \\sum d(e)$), whereas Dinic solves **multi-source, multi-shelter capacity maximization** ($\\max |f|$). A shortest-distance corridor can carry zero or partial flow in max-flow if downstream roads saturate or global capacity favors longer parallel bypasses.
        """
    )
