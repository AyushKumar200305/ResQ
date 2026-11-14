"""Step-by-step Dinic flow playback state generator from real execution traces."""

from dataclasses import dataclass

from resq.algorithms.dinic import solve_max_flow_dinic
from resq.domain.models import EvacuationNetwork
from resq.domain.results import DinicResult
from resq.domain.validation import SUPER_SINK_ID, SUPER_SOURCE_ID


@dataclass(frozen=True, slots=True)
class PlaybackFrame:
    """Exact graph flow snapshot at step `step_index` of Dinic's execution."""

    step_index: int
    total_steps: int
    phase_index: int
    bfs_sink_level: int | None
    bfs_node_levels: dict[str, int]
    active_path_nodes: tuple[str, ...]
    active_road_ids: tuple[str, ...]
    rerouted_road_ids: tuple[str, ...]
    flow_sent_this_step: int
    cumulative_flow: int
    road_flows: dict[str, int]
    road_remaining: dict[str, int]
    source_evacuated: dict[str, int]
    shelter_assigned: dict[str, int]
    explanation: str


def build_playback_frames(
    network: EvacuationNetwork,
    dinic_result: DinicResult | None = None,
) -> list[PlaybackFrame]:
    """Build deterministic step-by-step playback frames from Dinic's real execution trace."""
    result = dinic_result
    if result is None or result.trace is None:
        result = solve_max_flow_dinic(network, trace=True)

    assert result.trace is not None

    road_flows: dict[str, int] = {rid: 0 for rid in network.roads}
    road_caps: dict[str, int] = {
        rid: road.effective_capacity for rid, road in network.roads.items()
    }
    source_evac: dict[str, int] = {area.node_id: 0 for area in network.affected_areas}
    shelter_assigned: dict[str, int] = {shl.node_id: 0 for shl in network.shelters}

    total_steps = result.trace.total_augmentations

    initial_levels: dict[str, int] = {}
    if result.trace.phases:
        initial_levels = {
            k: v
            for k, v in result.trace.phases[0].node_levels.items()
            if k not in (SUPER_SOURCE_ID, SUPER_SINK_ID)
        }

    if total_steps == 0:
        initial_expl = (
            "No augmenting path found from any affected area to any shelter. "
            "Super-Sink is unreachable in the initial residual graph (Max Flow = 0)."
        )
    else:
        initial_expl = (
            f"Initial network state before flow routing. {total_steps} augmenting path "
            f"steps across {result.bfs_phases} Dinic BFS phase(s) are ready for playback."
        )

    frames: list[PlaybackFrame] = [
        PlaybackFrame(
            step_index=0,
            total_steps=total_steps,
            phase_index=0,
            bfs_sink_level=result.trace.phases[0].sink_level
            if result.trace.phases
            else None,
            bfs_node_levels=initial_levels,
            active_path_nodes=(),
            active_road_ids=(),
            rerouted_road_ids=(),
            flow_sent_this_step=0,
            cumulative_flow=0,
            road_flows=dict(road_flows),
            road_remaining=dict(road_caps),
            source_evacuated=dict(source_evac),
            shelter_assigned=dict(shelter_assigned),
            explanation=initial_expl,
        )
    ]

    cumulative_flow = 0

    for phase in result.trace.phases:
        if not phase.sink_reachable:
            continue

        domain_levels = {
            k: v
            for k, v in phase.node_levels.items()
            if k not in (SUPER_SOURCE_ID, SUPER_SINK_ID)
        }

        for step in phase.augmentations:
            delta = step.flow_sent
            cumulative_flow += delta

            active_roads: list[str] = []
            rerouted_roads: list[str] = []

            for upd in step.edge_updates:
                is_ss = (
                    upd.edge_kind == "super_source"
                    or upd.traversed_from == SUPER_SOURCE_ID
                    or upd.traversed_to == SUPER_SOURCE_ID
                )
                is_st = (
                    upd.edge_kind == "super_sink"
                    or upd.traversed_from == SUPER_SINK_ID
                    or upd.traversed_to == SUPER_SINK_ID
                )

                if is_ss:
                    if upd.used_reverse_edge:
                        source_evac[upd.edge_id] -= delta
                    else:
                        source_evac[upd.edge_id] += delta
                elif is_st:
                    if upd.used_reverse_edge:
                        shelter_assigned[upd.edge_id] -= delta
                    else:
                        shelter_assigned[upd.edge_id] += delta
                else:
                    active_roads.append(upd.edge_id)
                    if upd.used_reverse_edge:
                        road_flows[upd.edge_id] -= delta
                        rerouted_roads.append(upd.edge_id)
                    else:
                        road_flows[upd.edge_id] += delta

            domain_path = tuple(
                nid
                for nid in step.selected_path
                if nid not in (SUPER_SOURCE_ID, SUPER_SINK_ID)
            )
            path_str = " -> ".join(domain_path)
            road_rem = {
                rid: road_caps[rid] - road_flows[rid] for rid in network.roads
            }

            reroute_note = ""
            if rerouted_roads:
                reroute_note = (
                    f" Rerouted via reverse residual edge(s): {', '.join(rerouted_roads)}."
                )
            final_note = (
                " Optimal maximum flow reached; no residual S*->T* path remains."
                if step.step_index == total_steps
                else ""
            )

            explanation = (
                f"BFS Phase {step.phase_index} (Sink Level {phase.sink_level}) · "
                f"Step {step.step_index}/{total_steps}: Sent {delta:,} flow units along "
                f"{path_str}. Cumulative evacuated flow: {cumulative_flow:,}."
                f"{reroute_note}{final_note}"
            )

            frames.append(
                PlaybackFrame(
                    step_index=step.step_index,
                    total_steps=total_steps,
                    phase_index=step.phase_index,
                    bfs_sink_level=phase.sink_level,
                    bfs_node_levels=domain_levels,
                    active_path_nodes=domain_path,
                    active_road_ids=tuple(active_roads),
                    rerouted_road_ids=tuple(rerouted_roads),
                    flow_sent_this_step=delta,
                    cumulative_flow=cumulative_flow,
                    road_flows=dict(road_flows),
                    road_remaining=road_rem,
                    source_evacuated=dict(source_evac),
                    shelter_assigned=dict(shelter_assigned),
                    explanation=explanation,
                )
            )

    return frames
