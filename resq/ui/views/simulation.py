"""Page 3: Live Simulation (Step-by-Step Dinic Playback & Disaster Disruption Sandbox)."""

import pandas as pd
import streamlit as st

from resq.services.evacuation_simulator import DisruptionSpec, FullAnalysisBundle
from resq.services.playback import PlaybackFrame, build_playback_frames
from resq.ui.components import (
    KpiMetric,
    build_network_figure,
    build_wave_timeline_chart,
    render_kpi_grid,
    render_pending_analysis_guard,
)
from resq.ui.state import (
    get_active_network,
    get_analysis_bundle,
    run_primary_analysis,
    run_simulation_overlay,
    save_simulated_scenario,
    set_flash,
)
from resq.ui.theme import render_chart, render_table


def _render_playback_tab(
    base_bundle: FullAnalysisBundle | None,
    sim_bundle: FullAnalysisBundle | None,
) -> None:
    """Render deterministic step-by-step Dinic graph-flow playback."""
    rev = st.session_state.get("network_revision", 1)

    target_options = ["base"]
    if sim_bundle is not None:
        target_options.append("simulated")

    current_target = st.session_state.get("playback_target", "base")
    if current_target not in target_options:
        current_target = "base"
        st.session_state["playback_target"] = "base"

    c_top1, c_top2, c_top3 = st.columns([1.8, 1.2, 1.0])
    with c_top1:
        chosen_target = st.radio(
            "Playback Target Network",
            options=target_options,
            index=target_options.index(current_target),
            format_func=lambda k: (
                "Active Network"
                if k == "base"
                else "Simulated Disrupted Network"
            ),
            horizontal=True,
            key=f"pb_target_radio_{rev}_{len(target_options)}",
        )
        if chosen_target != current_target:
            st.session_state["playback_target"] = chosen_target
            st.session_state["playback_step"] = 0
            st.session_state["playback_playing"] = False
            st.rerun()

    target_bundle = base_bundle if chosen_target == "base" else sim_bundle
    if target_bundle is None:
        render_pending_analysis_guard("Step-by-Step Evacuation Playback", "playback")
        return

    frames: list[PlaybackFrame] = build_playback_frames(
        target_bundle.network, target_bundle.dinic_result
    )
    total_steps = len(frames) - 1

    with c_top2:
        step_interval = float(
            st.selectbox(
                "Auto-Play Interval",
                options=[0.8, 1.2, 2.0],
                index=1,
                format_func=lambda s: f"{s:.1f}s / step",
                key="pb_speed_sec",
            )
        )
    with c_top3:
        show_labels = st.checkbox("Show Flow Labels", value=True, key="pb_show_labels")

    is_playing: bool = bool(st.session_state.get("playback_playing", False))
    run_every = step_interval if is_playing and total_steps > 0 else None

    @st.fragment(run_every=run_every)
    def _playback_viewport() -> None:
        playing = bool(st.session_state.get("playback_playing", False))
        step_idx = int(st.session_state.get("playback_step", 0))
        step_idx = max(0, min(step_idx, total_steps))

        # Playback controls row (evaluated BEFORE timer auto-advance so Pause/Step act cleanly)
        b1, b2, b3, b4, b5 = st.columns(5, gap="small")
        start_clicked = b1.button(
            "Start Simulation",
            type="primary",
            width="stretch",
            disabled=(total_steps == 0 or playing),
            key="pb_start",
        )
        pause_clicked = b2.button(
            "Pause",
            width="stretch",
            disabled=not playing,
            key="pb_pause",
        )
        prev_clicked = b3.button(
            "Previous Step",
            width="stretch",
            disabled=(step_idx <= 0),
            key="pb_prev",
        )
        next_clicked = b4.button(
            "Next Step",
            width="stretch",
            disabled=(step_idx >= total_steps),
            key="pb_next",
        )
        reset_clicked = b5.button(
            "Reset Simulation",
            width="stretch",
            key="pb_reset",
        )

        if start_clicked:
            if step_idx >= total_steps:
                st.session_state["playback_step"] = 1 if total_steps >= 1 else 0
            elif step_idx == 0 and total_steps >= 1:
                st.session_state["playback_step"] = 1
            st.session_state["playback_playing"] = True
            st.session_state["_pb_just_started"] = True
            st.rerun(scope="app")

        if pause_clicked:
            st.session_state["playback_playing"] = False
            st.rerun(scope="app")

        def _commit_step(new_step: int) -> None:
            st.session_state["playback_playing"] = False
            st.session_state["playback_step"] = new_step
            if playing:
                st.rerun(scope="app")
            st.rerun()

        if prev_clicked:
            _commit_step(max(0, step_idx - 1))

        if next_clicked:
            _commit_step(min(total_steps, step_idx + 1))

        if reset_clicked:
            _commit_step(0)

        # Auto-advance ONLY on non-button timer ticks while playing
        if playing and st.session_state.pop("_pb_just_started", False) is False:
            if step_idx < total_steps:
                step_idx += 1
                st.session_state["playback_step"] = step_idx
            if step_idx >= total_steps:
                st.session_state["playback_playing"] = False
                st.rerun(scope="app")

        frame = frames[step_idx]

        if total_steps > 0:
            scrub = st.slider(
                "Step Timeline",
                min_value=0,
                max_value=total_steps,
                value=step_idx,
                disabled=playing,
                key=f"pb_slider_{rev}_{chosen_target}_{step_idx}",
            )
            if scrub != step_idx and not playing:
                st.session_state["playback_step"] = scrub
                st.rerun()

        max_possible = target_bundle.dinic_result.max_flow
        pct = (
            frame.cumulative_flow / target_bundle.dinic_result.total_population * 100.0
            if target_bundle.dinic_result.total_population > 0
            else 100.0
        )
        path_display = (
            " -> ".join(frame.active_path_nodes)
            if frame.active_path_nodes
            else "None (Initial / Terminated)"
        )
        render_kpi_grid(
            [
                KpiMetric(
                    label="Simulation Step",
                    value=f"{frame.step_index} / {frame.total_steps}",
                    subtext=(
                        f"BFS Phase {frame.phase_index} (Sink Level {frame.bfs_sink_level})"
                        if frame.phase_index > 0
                        else "Pre-augmentation state"
                    ),
                    tone="info",
                ),
                KpiMetric(
                    label="Flow Sent This Step",
                    value=f"+{frame.flow_sent_this_step:,}",
                    subtext=(
                        f"Reverse reroute on {', '.join(frame.rerouted_road_ids)}"
                        if frame.rerouted_road_ids
                        else "Forward level-graph augmentation"
                    ),
                    tone="warn" if frame.rerouted_road_ids else "safe",
                ),
                KpiMetric(
                    label="Cumulative Flow",
                    value=f"{frame.cumulative_flow:,}",
                    subtext=f"Target optimal max flow: {max_possible:,}",
                    tone="safe" if frame.cumulative_flow == max_possible else "info",
                ),
                KpiMetric(
                    label="Population Evacuated",
                    value=f"{pct:.1f}%",
                    subtext=f"Active path: {path_display}",
                    tone="safe" if pct >= 99.9 else "warn",
                ),
            ]
        )

        st.info(f"**Algorithm Step Explanation:** {frame.explanation}")

        fig = build_network_figure(
            target_bundle.network,
            bundle=target_bundle,
            mode="playback",
            playback_frame=frame,
            height=480,
            show_edge_labels=show_labels,
        )
        render_chart(fig, key=f"pb_plot_{rev}_{chosen_target}_{frame.step_index}")

        t1, t2 = st.columns([1.3, 1.0])
        with t1:
            st.markdown(
                '<div class="resq-section-title">Corridor State at Current Step</div>',
                unsafe_allow_html=True,
            )
            road_rows = []
            active_set = set(frame.active_road_ids)
            for rid, road in target_bundle.network.roads.items():
                cap = road.effective_capacity
                flw = frame.road_flows.get(rid, 0)
                rem = frame.road_remaining.get(rid, cap - flw)
                util = (flw / cap * 100.0) if cap > 0 else 0.0
                road_rows.append(
                    {
                        "Road ID": rid,
                        "Corridor": f"{road.source_id} -> {road.target_id}",
                        "Capacity": cap,
                        "Flow": flw,
                        "Remaining": rem,
                        "Util (%)": round(util, 1),
                        "Saturated": "Yes" if (cap > 0 and rem == 0) else "No",
                        "In Step": "ACTIVE" if rid in active_set else "-",
                    }
                )
            render_table(pd.DataFrame(road_rows), height=260)

        with t2:
            st.markdown(
                '<div class="resq-section-title">Sources & Shelters Progress</div>',
                unsafe_allow_html=True,
            )
            entity_rows = []
            for area in target_bundle.network.affected_areas:
                evac = frame.source_evacuated.get(area.node_id, 0)
                entity_rows.append(
                    {
                        "Entity": f"{area.node_id} ({area.name})",
                        "Role": "Source",
                        "Total Cap/Pop": area.population,
                        "Flow": evac,
                        "Remaining": area.population - evac,
                    }
                )
            for shl in target_bundle.network.shelters:
                asgn = frame.shelter_assigned.get(shl.node_id, 0)
                entity_rows.append(
                    {
                        "Entity": f"{shl.node_id} ({shl.name})",
                        "Role": "Shelter",
                        "Total Cap/Pop": shl.shelter_capacity,
                        "Flow": asgn,
                        "Remaining": shl.shelter_capacity - asgn,
                    }
                )
            render_table(pd.DataFrame(entity_rows), height=260)

    _playback_viewport()


def _render_disruption_tab(base_bundle: FullAnalysisBundle | None) -> None:
    """Render non-destructive disaster disruption simulation and time-wave projection."""
    net = get_active_network()
    rev = st.session_state.get("network_revision", 1)
    sim_bundle = st.session_state.get("sim_bundle")
    active_disruption: DisruptionSpec = st.session_state.get(
        "sim_disruption", DisruptionSpec()
    )

    st.caption(
        "Simulate disaster impacts (road closures, capacity degradation, shelter outages, "
        "and population surges) on an isolated copy without altering your base network."
    )

    default_factor_pct = 50
    if active_disruption.road_capacity_factors:
        first_factor = next(iter(active_disruption.road_capacity_factors.values()))
        default_factor_pct = max(10, min(100, int(round(first_factor * 100))))

    default_surge_pct = 125
    if active_disruption.demand_multipliers:
        first_mult = next(iter(active_disruption.demand_multipliers.values()))
        default_surge_pct = max(100, min(200, int(round(first_mult * 100))))

    with st.form(f"live_sim_form_{rev}"):
        c1, c2 = st.columns(2)
        with c1:
            disabled_roads = st.multiselect(
                "Severed / Closed Roads",
                options=list(net.roads.keys()),
                default=[r for r in active_disruption.disabled_roads if r in net.roads],
                format_func=lambda rid: (
                    f"{rid}: {net.roads[rid].source_id} -> {net.roads[rid].target_id}"
                ),
            )
            degraded_roads = st.multiselect(
                "Partially Degraded Corridors",
                options=list(net.roads.keys()),
                default=[
                    r
                    for r in active_disruption.road_capacity_factors
                    if r in net.roads and r not in active_disruption.disabled_roads
                ],
                format_func=lambda rid: f"{rid} (base cap {net.roads[rid].capacity:,})",
            )
            road_factor_pct = st.slider(
                "Remaining Capacity (%) on Degraded Corridors",
                min_value=10,
                max_value=100,
                value=default_factor_pct,
                step=5,
            )

        with c2:
            disabled_shelters = st.multiselect(
                "Offline / Compromised Shelters",
                options=[s.node_id for s in net.shelters],
                default=[s for s in active_disruption.disabled_shelters if s in net.nodes],
                format_func=lambda sid: f"{sid} ({net.nodes[sid].name})",
            )
            surge_areas = st.multiselect(
                "Affected Areas Experiencing Demand Surge",
                options=[a.node_id for a in net.affected_areas],
                default=[a for a in active_disruption.demand_multipliers if a in net.nodes],
                format_func=lambda aid: f"{aid} ({net.nodes[aid].name})",
            )
            surge_pct = st.slider(
                "Population Surge Multiplier (%)",
                min_value=100,
                max_value=200,
                value=default_surge_pct,
                step=5,
            )
            wave_hours = st.slider(
                "Evacuation Wave Horizon (Hours)",
                min_value=3,
                max_value=24,
                value=8,
            )

        b1, b2 = st.columns([1.4, 1.2])
        run_sim_clicked = b1.form_submit_button(
            "Run Disruption Simulation", type="primary", width="stretch"
        )
        reset_sim_clicked = b2.form_submit_button("Clear Disruptions", width="stretch")

    if reset_sim_clicked:
        st.session_state["sim_disruption"] = DisruptionSpec()
        st.session_state["sim_bundle"] = None
        st.session_state["playback_target"] = "base"
        st.session_state["playback_step"] = 0
        set_flash("info", "Cleared all disruption overrides.")
        st.rerun()

    if run_sim_clicked:
        disruption = DisruptionSpec(
            disabled_roads=frozenset(disabled_roads),
            road_capacity_factors={
                rid: road_factor_pct / 100.0
                for rid in degraded_roads
                if rid not in disabled_roads
            },
            disabled_shelters=frozenset(disabled_shelters),
            demand_multipliers={aid: surge_pct / 100.0 for aid in surge_areas},
        )
        with st.spinner("Evaluating disrupted network and projecting hourly waves..."):
            if base_bundle is None:
                run_primary_analysis(trace=True, wave_hours=wave_hours)
            ok, msg = run_simulation_overlay(disruption, wave_hours=wave_hours)
        if ok:
            st.session_state["playback_target"] = "simulated"
        set_flash("success" if ok else "error", msg)
        st.rerun()

    if sim_bundle is None:
        st.info(
            "Configure disaster disruptions above and click **Run Disruption Simulation** to inspect impact."
        )
        if base_bundle is not None:
            st.markdown(
                '<div class="resq-section-title">Baseline Wave Evacuation Projection</div>',
                unsafe_allow_html=True,
            )
            render_chart(
                build_wave_timeline_chart(base_bundle.wave_timeline), key="sim_base_wave"
            )
        return

    sv1, sv2 = st.columns([2.2, 1.2], vertical_alignment="bottom")
    with sv1:
        sim_label = st.text_input(
            "Snapshot Label (Optional)",
            placeholder="e.g., Bridge Outage Simulation",
            key=f"sim_save_label_{rev}",
        )
    with sv2:
        if st.button("Save Simulated Scenario", width="stretch", key=f"sim_save_btn_{rev}"):
            ok, msg = save_simulated_scenario(sim_label)
            set_flash("success" if ok else "warning", msg)
            st.rerun()

    base_bundle = get_analysis_bundle()
    sim_d = sim_bundle.dinic_result
    sim_mc = sim_bundle.min_cut

    flow_delta = (
        sim_d.max_flow - base_bundle.dinic_result.max_flow
        if base_bundle is not None
        else 0
    )
    unmet_delta = (
        sim_d.unmet_demand - base_bundle.dinic_result.unmet_demand
        if base_bundle is not None
        else 0
    )

    render_kpi_grid(
        [
            KpiMetric(
                label="Simulated Max Flow",
                value=f"{sim_d.max_flow:,}",
                subtext=(
                    f"{flow_delta:+,} vs. baseline"
                    if base_bundle
                    else "Disrupted throughput"
                ),
                tone="safe" if flow_delta >= 0 else "crit",
            ),
            KpiMetric(
                label="Simulated Unallocated",
                value=f"{sim_d.unmet_demand:,}",
                subtext=(
                    f"{unmet_delta:+,} vs. baseline"
                    if base_bundle
                    else "Remaining evacuees"
                ),
                tone="safe" if sim_d.unmet_demand == 0 else "crit",
            ),
            KpiMetric(
                label="Disrupted Completion",
                value=f"{sim_d.evacuation_rate * 100:.1f}%",
                subtext=f"Pop {sim_d.total_population:,} | Beds {sim_d.total_shelter_capacity:,}",
                tone="warn" if sim_d.evacuation_rate < 1.0 else "safe",
            ),
            KpiMetric(
                label="Active Cut Bottlenecks",
                value=f"{len(sim_mc.road_bottlenecks) + len(sim_mc.shelter_capacity_cuts)}",
                subtext=(
                    f"{len(sim_mc.road_bottlenecks)} roads · "
                    f"{len(sim_mc.shelter_capacity_cuts)} shelters"
                ),
                tone=(
                    "crit"
                    if (len(sim_mc.road_bottlenecks) + len(sim_mc.shelter_capacity_cuts))
                    > 0
                    else "safe"
                ),
            ),
        ]
    )

    col_map, col_wave = st.columns([1.25, 1.0], gap="medium")
    with col_map:
        st.markdown(
            '<div class="resq-section-title">Disrupted Network Flow State</div>',
            unsafe_allow_html=True,
        )
        render_chart(
            build_network_figure(
                sim_bundle.network, bundle=sim_bundle, mode="flow", height=420
            ),
            key="sim_network_map",
        )
    with col_wave:
        st.markdown(
            '<div class="resq-section-title">Hourly Cumulative Evacuation Wave</div>',
            unsafe_allow_html=True,
        )
        render_chart(
            build_wave_timeline_chart(sim_bundle.wave_timeline), key="sim_wave_chart"
        )

    wave_df = pd.DataFrame(
        [
            {
                "Hour": w.hour,
                "Evacuated This Hour": w.evacuated_this_hour,
                "Cumulative Evacuated": w.cumulative_evacuated,
                "Remaining Population": w.remaining_population,
                "Remaining Shelter Beds": w.remaining_shelter_capacity,
                "Completion (%)": round(w.completion_pct, 1),
            }
            for w in sim_bundle.wave_timeline
        ]
    )
    render_table(wave_df)


def render_live_simulation_page() -> None:
    """Render Step-by-Step Dinic Flow Playback and Disaster Disruption Simulation."""
    net = get_active_network()
    report = net.validate()
    if not report.is_valid:
        st.error(
            "Fix network validation errors before running live simulations: "
            + " | ".join(report.errors)
        )
        return

    base_bundle = get_analysis_bundle()
    sim_bundle = st.session_state.get("sim_bundle")

    tab_playback, tab_disruption = st.tabs(
        ["Step-by-Step Flow Playback", "Disruption & Wave Sandbox"]
    )
    with tab_playback:
        _render_playback_tab(base_bundle, sim_bundle)
    with tab_disruption:
        _render_disruption_tab(base_bundle)
