"""Interactive Plotly directed evacuation graph renderer with playback support."""

from collections import defaultdict
import math
import plotly.graph_objects as go

from resq.domain.enums import NodeType
from resq.domain.models import EvacuationNetwork
from resq.domain.results import AlgorithmComparisonResult, DijkstraResult
from resq.services.evacuation_simulator import FullAnalysisBundle
from resq.services.playback import PlaybackFrame
from resq.ui.theme import (
    BG_CANVAS,
    BG_SURFACE,
    BORDER_SUBTLE,
    COLOR_CRIT,
    COLOR_IDLE,
    COLOR_INFO,
    COLOR_WARN,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

COLOR_NODE_AREA = "#EF4444"     # Red for affected areas
COLOR_NODE_JUNCTION = "#3B82F6" # Blue for junctions
COLOR_NODE_SHELTER = "#22C55E"  # Green for shelters
COLOR_PLAYBACK_PATH = "#FACC15" # Signal gold for active playback path


def _compute_node_positions(network: EvacuationNetwork) -> dict[str, tuple[float, float]]:
    """Use stored node coordinates or fall back to clean layered role-based layout."""
    positions: dict[str, tuple[float, float]] = {}
    missing_by_role: dict[NodeType, list[str]] = {
        NodeType.AFFECTED_AREA: [],
        NodeType.JUNCTION: [],
        NodeType.SHELTER: [],
    }
    for node_id, node in network.nodes.items():
        if node.x is not None and node.y is not None:
            positions[node_id] = (node.x, node.y)
        else:
            missing_by_role[node.node_type].append(node_id)

    role_x = {
        NodeType.AFFECTED_AREA: 0.0,
        NodeType.JUNCTION: 4.5,
        NodeType.SHELTER: 9.0,
    }
    for role, ids in missing_by_role.items():
        count = len(ids)
        if count == 0:
            continue
        for idx, nid in enumerate(ids):
            y_val = (count - 1) * 1.1 - idx * 2.2
            positions[nid] = (role_x[role], y_val)

    return positions


def _quadratic_bezier_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    offset: float,
    steps: int = 15,
) -> tuple[list[float], list[float], tuple[float, float], tuple[float, float], tuple[float, float]]:
    """Return curve xs, ys, midpoint (t=0.5), arrow tail (t=0.70), arrow tip (t=0.84)."""
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    length = math.hypot(dx, dy) or 1.0
    nx = -dy / length
    ny = dx / length
    cx = (p0[0] + p1[0]) * 0.5 + nx * offset
    cy = (p0[1] + p1[1]) * 0.5 + ny * offset

    def eval_t(t: float) -> tuple[float, float]:
        mt = 1.0 - t
        return (
            mt * mt * p0[0] + 2.0 * mt * t * cx + t * t * p1[0],
            mt * mt * p0[1] + 2.0 * mt * t * cy + t * t * p1[1],
        )

    xs: list[float] = []
    ys: list[float] = []
    for i in range(steps + 1):
        px, py = eval_t(i / steps)
        xs.append(px)
        ys.append(py)

    return xs, ys, eval_t(0.5), eval_t(0.70), eval_t(0.84)


def build_network_figure(
    network: EvacuationNetwork,
    *,
    bundle: FullAnalysisBundle | None = None,
    mode: str = "auto",
    comparison: AlgorithmComparisonResult | None = None,
    playback_frame: PlaybackFrame | None = None,
    dijkstra_result: DijkstraResult | None = None,
    height: int = 500,
    show_edge_labels: bool = True,
) -> go.Figure:
    """Render an interactive dark-theme Plotly network graph with directed arrowheads."""
    resolved_mode = mode
    if resolved_mode == "auto":
        if dijkstra_result is not None:
            resolved_mode = "shortest_path"
        elif playback_frame is not None:
            resolved_mode = "playback"
        elif bundle is not None:
            resolved_mode = "flow"
        else:
            resolved_mode = "topology"

    fig = go.Figure()

    if not network.nodes:
        fig.add_annotation(
            text="Network is empty. Add affected areas, junctions, and shelters in Network Builder.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(color=TEXT_MUTED, size=14),
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=BG_SURFACE,
            plot_bgcolor=BG_CANVAS,
            height=height,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    positions = _compute_node_positions(network)

    # Group roads between undirected vertex pairs so parallel & 2-way roads get distinct curves.
    pair_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for road_id, road in network.roads.items():
        pair_key = tuple(sorted((road.source_id, road.target_id)))
        pair_groups[(pair_key[0], pair_key[1])].append(road_id)

    edge_offsets: dict[str, float] = {}
    for pair_key, road_ids in pair_groups.items():
        total = len(road_ids)
        if total == 1:
            edge_offsets[road_ids[0]] = 0.0
            continue
        for idx, rid in enumerate(road_ids):
            road = network.roads[rid]
            slot_offset = (idx - (total - 1) / 2.0) * 0.75
            edge_offsets[rid] = (
                slot_offset if road.source_id == pair_key[0] else -slot_offset
            )

    cut_road_ids = (
        {e.edge_id for e in bundle.min_cut.road_bottlenecks}
        if bundle is not None
        else set()
    )
    comp_map = (
        {rc.road_id: rc for rc in comparison.road_comparisons}
        if comparison is not None
        else {}
    )
    active_playback_roads = (
        set(playback_frame.active_road_ids) if playback_frame is not None else set()
    )
    rerouted_playback_roads = (
        set(playback_frame.rerouted_road_ids) if playback_frame is not None else set()
    )
    shortest_road_ids = (
        set(dijkstra_result.shortest_route.road_ids)
        if dijkstra_result is not None and dijkstra_result.shortest_route is not None
        else set()
    )
    alternative_road_ids = (
        set(dijkstra_result.alternative_route.road_ids)
        if dijkstra_result is not None and dijkstra_result.alternative_route is not None
        else set()
    )

    hover_x: list[float] = []
    hover_y: list[float] = []
    hover_text: list[str] = []
    hover_colors: list[str] = []
    label_x: list[float] = []
    label_y: list[float] = []
    label_text: list[str] = []
    annotations: list[dict] = []

    road_style_catalog = {
        "normal": ("Normal Road", COLOR_INFO, 2.4, "solid"),
        "saturated": ("Saturated Road", COLOR_WARN, 3.2, "dash"),
        "min_cut": ("Minimum-Cut Road", COLOR_CRIT, 4.2, "solid"),
        "closed": ("Closed Road", COLOR_IDLE, 1.7, "dot"),
        "playback": ("Active Step Path", COLOR_PLAYBACK_PATH, 4.8, "solid"),
        "shortest": ("Shortest Path (Dijkstra)", "#2DD4BF", 4.8, "solid"),
        "alternative": ("Alternative Route", "#A855F7", 3.4, "dash"),
    }
    used_road_styles: set[str] = set()

    for road_id, road in network.roads.items():
        p0 = positions[road.source_id]
        p1 = positions[road.target_id]
        offset = edge_offsets.get(road_id, 0.0)
        xs, ys, mid, tail, tip = _quadratic_bezier_points(p0, p1, offset)

        if not road.is_active:
            style_key = "closed"
            edge_label = f"{road_id}: CLOSED"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {road.capacity:,} (CLOSED)<br>"
                f"Flow = 0<br>"
                f"Remaining capacity = 0<br>"
                f"Utilization = 0.0%<br>"
                f"Status = Closed Road"
            )
        elif resolved_mode == "shortest_path" and dijkstra_result is not None:
            if road_id in shortest_road_ids and road_id in alternative_road_ids:
                style_key = "shortest"
                route_tag = "Shared by Shortest & Alternative Routes"
            elif road_id in shortest_road_ids:
                style_key = "shortest"
                route_tag = "Shortest-Distance Path (Dijkstra)"
            elif road_id in alternative_road_ids:
                style_key = "alternative"
                route_tag = "Alternative Route (2nd Shortest)"
            else:
                style_key = "normal"
                route_tag = "Other Active Road"
            edge_label = f"{road.distance:.1f} km | Cap {road.capacity:,}"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {road.effective_capacity:,}<br>"
                f"Travel time = {road.travel_time_min:.0f} min<br>"
                f"Route Role = {route_tag}"
            )
        elif resolved_mode == "playback" and playback_frame is not None:
            orig_cap = road.effective_capacity
            flow_val = playback_frame.road_flows.get(road_id, 0)
            rem_cap = playback_frame.road_remaining.get(road_id, orig_cap - flow_val)
            util_pct = (flow_val / orig_cap * 100.0) if orig_cap > 0 else 0.0
            is_sat = orig_cap > 0 and rem_cap == 0

            if road_id in active_playback_roads:
                style_key = "playback"
                step_tag = (
                    "ACTIVE STEP (REVERSE REROUTE)"
                    if road_id in rerouted_playback_roads
                    else "ACTIVE STEP PATH"
                )
            elif is_sat:
                style_key = "saturated"
                step_tag = "Saturated Road"
            else:
                style_key = "normal"
                step_tag = "Normal Road"

            edge_label = f"{flow_val:,}/{orig_cap:,} ({util_pct:.0f}%)"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {orig_cap:,}<br>"
                f"Flow = {flow_val:,}<br>"
                f"Remaining capacity = {rem_cap:,}<br>"
                f"Utilization = {util_pct:.1f}%<br>"
                f"Saturated = {'Yes' if is_sat else 'No'}<br>"
                f"Playback Status = {step_tag}"
            )
        elif resolved_mode == "topology" or bundle is None:
            style_key = "normal"
            edge_label = f"Cap {road.capacity:,} · {road.distance:.1f} km"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {road.capacity:,}<br>"
                f"Travel time = {road.travel_time_min:.0f} min<br>"
                f"Status = Normal Road (Pre-Analysis)"
            )
        elif resolved_mode == "diff" and comparison is not None:
            rc = comp_map.get(road_id)
            d_flow = rc.dinic_flow if rc else 0
            g_flow = rc.greedy_flow if rc else 0
            diff = d_flow - g_flow
            if diff > 0:
                style_key = "normal"
            elif diff < 0:
                style_key = "saturated"
            else:
                style_key = "closed"
            edge_label = f"D:{d_flow:,} | G:{g_flow:,}"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {road.capacity:,}<br>"
                f"Dinic Flow = {d_flow:,}<br>"
                f"Greedy Flow = {g_flow:,}<br>"
                f"Delta (Dinic - Greedy) = {diff:+,}"
            )
        else:
            detail = bundle.dinic_result.road_flows.get(road_id)
            flow_val = detail.flow if detail else 0
            orig_cap = detail.original_capacity if detail else road.effective_capacity
            rem_cap = detail.remaining_capacity if detail else (orig_cap - flow_val)
            util_pct = (detail.utilization_ratio * 100.0) if detail else 0.0
            is_sat = detail.is_saturated if detail else False
            is_cut = road_id in cut_road_ids

            if is_cut:
                style_key = "min_cut"
                tag = "Minimum-Cut Bottleneck"
            elif is_sat:
                style_key = "saturated"
                tag = "Saturated Road (Non-Cut)"
            else:
                style_key = "normal"
                tag = "Normal Road"

            edge_label = f"{flow_val:,}/{orig_cap:,} ({util_pct:.0f}%)"
            hover = (
                f"<b>{road_id}</b> — {road.name or 'Road'}<br>"
                f"Direction: {road.source_id} -> {road.target_id}<br>"
                f"Road distance = {road.distance:.2f} km<br>"
                f"Road capacity = {orig_cap:,}<br>"
                f"Flow = {flow_val:,}<br>"
                f"Remaining capacity = {rem_cap:,}<br>"
                f"Utilization = {util_pct:.1f}%<br>"
                f"Saturated = {'Yes' if is_sat else 'No'}<br>"
                f"Minimum Cut = {'Yes' if is_cut else 'No'}<br>"
                f"Status = {tag}"
            )

        legend_label, color, width, dash_style = road_style_catalog[style_key]
        used_road_styles.add(style_key)

        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=legend_label,
                legendgroup=f"road_{style_key}",
                line=dict(color=color, width=width, dash=dash_style),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Directional arrowhead near destination
        annotations.append(
            dict(
                x=tip[0],
                y=tip[1],
                ax=tail[0],
                ay=tail[1],
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.05,
                arrowwidth=max(1.5, width * 0.65),
                arrowcolor=color,
            )
        )

        hover_x.append(mid[0])
        hover_y.append(mid[1])
        hover_text.append(hover)
        hover_colors.append(color)

        if show_edge_labels:
            label_x.append(mid[0])
            label_y.append(mid[1])
            label_text.append(edge_label)

    # Add legend entries for road styles so clicking toggles the whole group
    if resolved_mode == "shortest_path":
        ordered_legend_keys = ("shortest", "alternative", "normal", "closed")
    elif resolved_mode == "playback":
        ordered_legend_keys = ("playback", "normal", "saturated", "min_cut", "closed")
    else:
        ordered_legend_keys = ("normal", "saturated", "min_cut", "closed")
    for style_key in ordered_legend_keys:
        if resolved_mode == "diff" and style_key not in used_road_styles:
            continue
        if style_key in ("playback", "alternative") and style_key not in used_road_styles:
            continue
        legend_label, color, width, dash_style = road_style_catalog[style_key]
        if resolved_mode == "diff":
            legend_label = {
                "normal": "Dinic > Greedy Flow",
                "saturated": "Greedy > Dinic Flow",
                "closed": "Equal Flow",
            }.get(style_key, legend_label)
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                name=legend_label,
                legendgroup=f"road_{style_key}",
                line=dict(color=color, width=width, dash=dash_style),
                showlegend=True,
                hoverinfo="skip",
            )
        )

    # Invisible midpoint hover anchors + optional edge labels
    if hover_x:
        fig.add_trace(
            go.Scatter(
                x=hover_x,
                y=hover_y,
                mode="markers",
                marker=dict(size=12, color=hover_colors, opacity=0.01),
                hovertext=hover_text,
                hoverinfo="text",
                showlegend=False,
            )
        )
    if show_edge_labels and label_x:
        fig.add_trace(
            go.Scatter(
                x=label_x,
                y=label_y,
                mode="text",
                text=label_text,
                textfont=dict(size=10, color=TEXT_PRIMARY),
                textposition="top center",
                hoverinfo="skip",
                showlegend=False,
            )
        )

    # Render nodes with required distinguishable colors:
    # Affected Areas = Red, Junctions = Blue, Shelters = Green
    reachable_set = (
        set(bundle.min_cut.reachable_domain_nodes)
        if bundle is not None and resolved_mode == "min_cut"
        else set()
    )
    active_path_node_set = (
        set(playback_frame.active_path_nodes)
        if playback_frame is not None and resolved_mode == "playback"
        else set()
    )

    role_specs = [
        (NodeType.AFFECTED_AREA, "Affected Area", "diamond", 19, COLOR_NODE_AREA),
        (NodeType.JUNCTION, "Junction", "circle", 15, COLOR_NODE_JUNCTION),
        (NodeType.SHELTER, "Shelter", "triangle-up", 19, COLOR_NODE_SHELTER),
    ]

    for role, role_label, symbol, size, role_color in role_specs:
        role_nodes = network.get_nodes_by_type(role)
        if not role_nodes:
            continue
        nx_vals: list[float] = []
        ny_vals: list[float] = []
        n_labels: list[str] = []
        n_hovers: list[str] = []
        n_borders: list[str] = []
        n_border_widths: list[float] = []
        n_opacities: list[float] = []

        for node in role_nodes:
            px, py = positions[node.node_id]
            nx_vals.append(px)
            ny_vals.append(py)
            n_labels.append(f"{node.node_id}<br>{node.name}")

            if resolved_mode == "min_cut" and bundle is not None:
                is_reach = node.node_id in reachable_set
                n_borders.append(COLOR_INFO if is_reach else "#475569")
                n_border_widths.append(3.2 if is_reach else 1.5)
                n_opacities.append(1.0 if is_reach else 0.6)
                part_tag = (
                    "Min-Cut Partition: Reachable (A)"
                    if is_reach
                    else "Min-Cut Partition: Unreachable (B)"
                )
            elif resolved_mode == "playback" and node.node_id in active_path_node_set:
                n_borders.append(COLOR_PLAYBACK_PATH)
                n_border_widths.append(3.4)
                n_opacities.append(1.0)
                part_tag = "Active in current Dinic step"
            elif resolved_mode == "shortest_path" and dijkstra_result is not None and node.node_id in {
                dijkstra_result.source_id,
                dijkstra_result.shelter_id,
            }:
                n_borders.append("#2DD4BF")
                n_border_widths.append(3.4)
                n_opacities.append(1.0)
                part_tag = (
                    "Selected Origin (Affected Area)"
                    if node.node_id == dijkstra_result.source_id
                    else "Selected Destination (Shelter)"
                )
            else:
                n_borders.append("#F8FAFC")
                n_border_widths.append(1.6)
                n_opacities.append(1.0)
                part_tag = ""

            extra = ""
            if role == NodeType.AFFECTED_AREA:
                extra = f"Population = {node.population:,}"
                if resolved_mode == "playback" and playback_frame is not None:
                    evac = playback_frame.source_evacuated.get(node.node_id, 0)
                    extra += f"<br>Evacuated (step {playback_frame.step_index}) = {evac:,}<br>Remaining = {node.population - evac:,}"
                elif bundle is not None and node.node_id in bundle.dinic_result.source_evacuations:
                    src_d = bundle.dinic_result.source_evacuations[node.node_id]
                    extra += f"<br>Evacuated = {src_d.evacuated:,}<br>Unallocated = {src_d.unmet_demand:,}"
            elif role == NodeType.SHELTER:
                extra = f"Shelter capacity = {node.shelter_capacity:,}"
                if resolved_mode == "playback" and playback_frame is not None:
                    assigned = playback_frame.shelter_assigned.get(node.node_id, 0)
                    extra += f"<br>Assigned (step {playback_frame.step_index}) = {assigned:,}<br>Remaining = {node.shelter_capacity - assigned:,}"
                elif bundle is not None and node.node_id in bundle.dinic_result.shelter_intakes:
                    shl_d = bundle.dinic_result.shelter_intakes[node.node_id]
                    extra += f"<br>Assigned flow = {shl_d.assigned_flow:,}<br>Remaining capacity = {shl_d.remaining_capacity:,}"
            else:
                extra = "Intermediate Routing Junction"

            if resolved_mode == "playback" and playback_frame is not None:
                lvl = playback_frame.bfs_node_levels.get(node.node_id)
                if lvl is not None:
                    extra += f"<br>BFS Level = {lvl}"
            elif resolved_mode == "shortest_path" and dijkstra_result is not None:
                dist_val = dijkstra_result.distances_from_source.get(node.node_id)
                if dist_val is not None:
                    extra += f"<br>Shortest distance from {dijkstra_result.source_id} = {dist_val:.2f} km"
                else:
                    extra += f"<br>Unreachable from {dijkstra_result.source_id}"

            hover_str = f"<b>{node.node_id} — {node.name}</b><br>Role: {role_label}<br>{extra}"
            if part_tag:
                hover_str += f"<br>{part_tag}"
            n_hovers.append(hover_str)

        fig.add_trace(
            go.Scatter(
                x=nx_vals,
                y=ny_vals,
                mode="markers+text",
                name=role_label,
                marker=dict(
                    symbol=symbol,
                    size=size,
                    color=role_color,
                    opacity=n_opacities,
                    line=dict(color=n_borders, width=n_border_widths),
                ),
                text=n_labels,
                textposition="bottom center",
                textfont=dict(size=10, color=TEXT_PRIMARY),
                hovertext=n_hovers,
                hoverinfo="text",
                showlegend=True,
            )
        )

    all_x = [pos[0] for pos in positions.values()]
    all_y = [pos[1] for pos in positions.values()]
    x_pad = max(1.2, (max(all_x) - min(all_x)) * 0.16)
    y_pad = max(1.2, (max(all_y) - min(all_y)) * 0.24)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_SURFACE,
        plot_bgcolor=BG_CANVAS,
        height=height,
        margin=dict(l=16, r=16, t=34, b=16),
        annotations=annotations,
        hovermode="closest",
        xaxis=dict(
            showgrid=True,
            gridcolor="#162032",
            zeroline=False,
            showticklabels=False,
            range=[min(all_x) - x_pad, max(all_x) + x_pad],
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#162032",
            zeroline=False,
            showticklabels=False,
            range=[min(all_y) - y_pad, max(all_y) + y_pad],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="left",
            x=0.0,
            bgcolor="rgba(17, 24, 39, 0.85)",
            bordercolor=BORDER_SUBTLE,
            borderwidth=1,
            font=dict(size=11, color=TEXT_PRIMARY),
        ),
    )
    return fig
