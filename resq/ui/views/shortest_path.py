"""Page 8 (Optional Educational Extension): Dijkstra Shortest-Path & Max-Flow Comparison."""

import pandas as pd
import streamlit as st

from resq.algorithms.dijkstra import solve_shortest_path_dijkstra
from resq.domain.exceptions import ResQError
from resq.domain.results import ShortestPathRoute
from resq.services.shortest_path_service import (
    PROBLEM_DISTINCTION_SUMMARY,
    compare_shortest_path_with_max_flow,
)
from resq.ui.components import KpiMetric, build_network_figure, render_kpi_grid
from resq.ui.state import (
    get_active_network,
    get_analysis_bundle,
    get_dijkstra_result,
    run_primary_analysis,
    set_dijkstra_result,
    set_flash,
)
from resq.ui.theme import render_chart, render_table


def _render_route_breakdown(route: ShortestPathRoute, *, heading: str) -> None:
    """Render ordered locations and per-road segment details for one route."""
    st.markdown(f"**{heading}**")
    st.caption(
        f"Total Distance: **{route.total_distance:.2f} km** · "
        f"Bottleneck Capacity: **{route.bottleneck_capacity:,}** · "
        f"Est. Travel Time: **{route.total_travel_time_min:.0f} min**"
    )

    ordered_md = "\n".join(
        f"{idx}. `{nid}` — {nname}"
        for idx, (nid, nname) in enumerate(zip(route.node_path, route.node_names), start=1)
    )
    st.markdown("**Ordered List of Locations:**\n" + ordered_md)

    road_rows = [
        {
            "Hop": idx,
            "Road ID": rid,
            "Road Name": rname,
            "Segment": f"{u} -> {v}",
            "Distance (km)": round(dist, 2),
            "Capacity": cap,
        }
        for idx, (rid, rname, u, v, dist, cap) in enumerate(
            zip(
                route.road_ids,
                route.road_names,
                route.node_path[:-1],
                route.node_path[1:],
                route.road_distances,
                route.road_capacities,
            ),
            start=1,
        )
    ]
    render_table(pd.DataFrame(road_rows), height=200)


def render_shortest_path_page() -> None:
    """Render the optional educational Dijkstra Shortest-Path & Max-Flow Comparison view."""
    st.markdown(
        '<div class="resq-section-title">Dijkstra Shortest-Path Explorer (Optional Educational Extension)</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Computes single-pair minimum road-distance paths using an adjacency list and binary min-heap "
        "in O((V + E) log V) worst-case time, using non-negative road distances strictly separate from flow capacities."
    )

    net = get_active_network()
    areas = net.affected_areas
    shelters = net.shelters
    rev = st.session_state.get("network_revision", 1)

    if not areas or not shelters:
        st.warning(
            "Shortest-path queries require at least one Affected Area and one Shelter. "
            "Add them in Network Builder or load a preset network."
        )
        return

    area_ids = [n.node_id for n in areas]
    shelter_ids = [n.node_id for n in shelters]

    c1, c2, c3, c4 = st.columns([1.4, 1.4, 1.1, 1.2], vertical_alignment="bottom")
    with c1:
        selected_src = st.selectbox(
            "Select Affected Area (Origin)",
            options=area_ids,
            format_func=lambda nid: f"{nid} — {net.nodes[nid].name} (Pop {net.nodes[nid].population:,})",
            key=f"sp_source_sel_{rev}",
        )
    with c2:
        selected_dst = st.selectbox(
            "Select Shelter (Destination)",
            options=shelter_ids,
            format_func=lambda nid: f"{nid} — {net.nodes[nid].name} (Cap {net.nodes[nid].shelter_capacity:,})",
            key=f"sp_shelter_sel_{rev}",
        )
    with c3:
        if st.button(
            "Calculate Shortest Path",
            type="primary",
            width="stretch",
            help="Run O((V + E) log V) heap-based Dijkstra and Yen's 2nd-shortest alternative route.",
            key="sp_calc_btn",
        ):
            try:
                res = solve_shortest_path_dijkstra(
                    net,
                    selected_src,
                    selected_dst,
                    active_roads_only=True,
                    require_area_and_shelter=True,
                    find_alternative=True,
                )
            except ResQError as exc:
                st.error(str(exc))
            else:
                set_dijkstra_result(res)
                if res.reachable and res.shortest_route is not None:
                    set_flash(
                        "success",
                        f"Shortest route {selected_src} -> {selected_dst}: "
                        f"{res.shortest_route.total_distance:.2f} km ({len(res.shortest_route.road_ids)} road(s)).",
                    )
                else:
                    set_flash(
                        "warning",
                        f"No active directed path connects '{selected_src}' to '{selected_dst}'.",
                    )
                st.rerun()
    with c4:
        if st.button(
            "Run Max-Flow & Compare",
            width="stretch",
            help="Compute Dinic's Maximum Flow alongside this shortest-distance route.",
            key="sp_compare_dinic_btn",
        ):
            try:
                dijk_res = solve_shortest_path_dijkstra(
                    net,
                    selected_src,
                    selected_dst,
                    active_roads_only=True,
                    require_area_and_shelter=True,
                    find_alternative=True,
                )
                set_dijkstra_result(dijk_res)
                ok, msg = run_primary_analysis(trace=True)
            except ResQError as exc:
                st.error(str(exc))
            else:
                set_flash("success" if ok else "error", msg)
                st.rerun()

    dijkstra_res = get_dijkstra_result()
    if dijkstra_res is None:
        st.info(
            "Select an Affected Area and a Shelter above, then click **Calculate Shortest Path** "
            "(or **Run Max-Flow & Compare**) to compute the minimum-distance route, inspect an alternative path, "
            "and contrast distance optimization with maximum evacuation flow."
        )
        return

    bundle = get_analysis_bundle()
    comp = compare_shortest_path_with_max_flow(
        net,
        dijkstra_res.source_id,
        dijkstra_res.shelter_id,
        bundle=bundle,
        dijkstra_result=dijkstra_res,
    )

    if comp.dijkstra_result.source_id != selected_src or comp.dijkstra_result.shelter_id != selected_dst:
        st.caption(
            f"Showing stored shortest-path calculation for `{comp.dijkstra_result.source_id} -> "
            f"{comp.dijkstra_result.shelter_id}`. Click **Calculate Shortest Path** to update for "
            f"`{selected_src} -> {selected_dst}`."
        )

    shortest = comp.shortest_route
    alt = comp.alternative_route

    alt_val = f"{alt.total_distance:.2f} km" if alt is not None else "None"
    alt_sub = (
        f"+{alt.total_distance - shortest.total_distance:.2f} km vs shortest ({len(alt.road_ids)} road(s))"
        if (alt is not None and shortest is not None)
        else "No distinct loopless detour"
    )

    render_kpi_grid(
        [
            KpiMetric(
                label="Shortest Distance (Dijkstra)",
                value=f"{shortest.total_distance:.2f} km" if shortest else "Unreachable",
                subtext=(
                    f"{' -> '.join(shortest.node_path)}"
                    if shortest
                    else f"No active path {comp.source_id} -> {comp.shelter_id}"
                ),
                tone="info" if shortest else "crit",
            ),
            KpiMetric(
                label="Alternative Route",
                value=alt_val,
                subtext=alt_sub,
                tone="neutral" if alt else "warn",
            ),
            KpiMetric(
                label="Shortest-Route Bottleneck Cap",
                value=f"{shortest.bottleneck_capacity:,}" if shortest else "0",
                subtext=f"Pair: {comp.source_id} (Pop {comp.source_population:,}) -> {comp.shelter_id} (Cap {comp.shelter_capacity:,})",
                tone="warn" if (shortest and shortest.bottleneck_capacity < comp.source_population) else "safe",
            ),
            KpiMetric(
                label="Dijkstra Runtime / Ops",
                value=f"{comp.dijkstra_result.execution_time_ms:.3f} ms",
                subtext=f"{comp.dijkstra_result.heap_pops} min-heap pops · {comp.dijkstra_result.relaxed_edges_count} relaxations",
                tone="safe",
            ),
        ]
    )

    st.markdown(
        '<div class="resq-section-title">Shortest Path vs. Alternative Route Topology Map</div>',
        unsafe_allow_html=True,
    )
    render_chart(
        build_network_figure(
            net,
            mode="shortest_path",
            dijkstra_result=comp.dijkstra_result,
            height=430,
        ),
        key="sp_network_map",
    )

    if shortest is None:
        st.warning(
            f"No active directed road path connects **{comp.source_id}** to **{comp.shelter_id}**. "
            "Check road directions or reopen closed corridors in Network Builder / Live Simulation."
        )
    else:
        col_primary, col_alt = st.columns(2, gap="medium")
        with col_primary:
            _render_route_breakdown(
                shortest,
                heading=f"Primary Shortest Path ({comp.source_id} -> {comp.shelter_id})",
            )
        with col_alt:
            if alt is not None:
                _render_route_breakdown(
                    alt,
                    heading=f"Alternative Route ({comp.source_id} -> {comp.shelter_id})",
                )
            else:
                st.markdown("**Alternative Route**")
                st.info(
                    "No alternative simple path is available between this affected area and shelter "
                    "on active directed roads."
                )

    st.markdown(
        '<div class="resq-section-title">Why Shortest Distance and Maximum Evacuation Flow Differ</div>',
        unsafe_allow_html=True,
    )
    st.info(PROBLEM_DISTINCTION_SUMMARY)

    theory_df = pd.DataFrame(
        [
            {
                "Dimension": "Optimization Objective",
                "Dijkstra Shortest Path": "Minimize sum of road distances along ONE origin -> destination route",
                "Dinic Maximum Flow": "Maximize TOTAL evacuees across ALL sources -> ALL shelters simultaneously",
            },
            {
                "Dimension": "Edge Weight Respected",
                "Dijkstra Shortest Path": "Non-negative road distance (km); ignores capacities & demand",
                "Dinic Maximum Flow": "Non-negative integer road & shelter capacities; ignores distance",
            },
            {
                "Dimension": "Path Multiplicity",
                "Dijkstra Shortest Path": "Single shortest path (plus optional k=2 alternative)",
                "Dinic Maximum Flow": "Splits flow across parallel & longer detour paths simultaneously",
            },
            {
                "Dimension": "Core Data Structures & Complexity",
                "Dijkstra Shortest Path": "Adjacency list + binary min-heap · O((V + E) log V)",
                "Dinic Maximum Flow": "Residual graph (fwd + rev edges) + BFS + DFS · O(V^2 E)",
            },
        ]
    )
    render_table(theory_df)

    if not comp.flow_analysis_available:
        st.warning(
            "Maximum-Flow analysis has not been run on the current network yet. "
            "Click **Run Max-Flow & Compare** above (or **Run Analysis** in the top toolbar) "
            "to compare Dinic's actual evacuation paths against this shortest route."
        )
        return

    st.markdown(
        '<div class="resq-section-title">Comparison Against Active Dinic Maximum-Flow Solution</div>',
        unsafe_allow_html=True,
    )
    for note in comp.observations:
        st.markdown(f"- {note}")

    flow_col1, flow_col2 = st.columns(2, gap="medium")
    with flow_col1:
        st.markdown(f"**Dinic Routes Departing `{comp.source_id}` (Total Dispatched: {comp.source_dispatched_flow:,})**")
        if comp.source_flow_routes:
            route_rows = [
                {
                    "Route #": r.route_index,
                    "Destination": r.shelter_id,
                    "Path": " -> ".join(r.node_path),
                    "Roads": ", ".join(r.road_ids),
                    "Max-Flow Volume": r.flow_allocated,
                    "Distance (km)": round(r.total_distance, 2),
                    "Shortest Pair Match": "Yes" if r.matches_shortest_pair_route else "No",
                }
                for r in comp.source_flow_routes
            ]
            render_table(pd.DataFrame(route_rows), height=220)
        else:
            st.caption(f"Dinic dispatched 0 flow from '{comp.source_id}'.")

    with flow_col2:
        st.markdown(f"**Dinic Utilization Along Shortest-Path Roads**")
        if comp.shortest_road_statuses:
            status_rows = [
                {
                    "Road ID": s.road_id,
                    "Segment": f"{s.from_node} -> {s.to_node}",
                    "Dist (km)": round(s.distance, 2),
                    "Capacity": s.capacity,
                    "Dinic Flow": s.dinic_flow,
                    "Util (%)": round(s.utilization_pct, 1),
                    "Saturated": "Yes" if s.is_saturated else "No",
                    "Min-Cut": "Yes" if s.is_min_cut else "No",
                }
                for s in comp.shortest_road_statuses
            ]
            render_table(pd.DataFrame(status_rows), height=220)
        else:
            st.caption("No shortest path available to inspect road utilization.")
