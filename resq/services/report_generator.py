"""Structured CSV, Pandas DataFrame, Markdown, and HTML report generation."""

from datetime import datetime, timezone
import html
import pandas as pd

from resq.domain.results import AlgorithmComparisonResult
from resq.services.evacuation_simulator import FullAnalysisBundle


def build_road_flows_dataframe(bundle: FullAnalysisBundle) -> pd.DataFrame:
    """Build a DataFrame of directed road capacities, flows, utilization, and min-cut flags."""
    cut_road_ids = {edge.edge_id for edge in bundle.min_cut.road_bottlenecks}
    non_cut_sat = set(bundle.min_cut.saturated_non_cut_roads)

    rows = []
    for road_id, detail in bundle.dinic_result.road_flows.items():
        if not detail.is_active:
            status = "Closed"
        elif road_id in cut_road_ids:
            status = "Min-Cut Bottleneck"
        elif road_id in non_cut_sat:
            status = "Saturated (Non-Cut)"
        elif detail.utilization_ratio >= 0.75:
            status = "Near Capacity"
        elif detail.flow > 0:
            status = "Operational"
        else:
            status = "Idle"

        rows.append(
            {
                "Road ID": detail.road_id,
                "Name": detail.road_name or "-",
                "From": detail.source_id,
                "To": detail.target_id,
                "Capacity": detail.original_capacity,
                "Flow": detail.flow,
                "Remaining": detail.remaining_capacity,
                "Utilization (%)": round(detail.utilization_ratio * 100.0, 1),
                "Status": status,
            }
        )
    return pd.DataFrame(rows)


def build_sources_dataframe(bundle: FullAnalysisBundle) -> pd.DataFrame:
    """Build a DataFrame summarizing affected-area evacuation completion."""
    rows = []
    for area_id, detail in bundle.dinic_result.source_evacuations.items():
        pct = (detail.evacuated / detail.population * 100.0) if detail.population > 0 else 100.0
        rows.append(
            {
                "Source ID": area_id,
                "Affected Area": detail.name,
                "Population": detail.population,
                "Evacuated": detail.evacuated,
                "Unallocated": detail.unmet_demand,
                "Evacuation (%)": round(pct, 1),
            }
        )
    return pd.DataFrame(rows)


def build_shelters_dataframe(bundle: FullAnalysisBundle) -> pd.DataFrame:
    """Build a DataFrame summarizing shelter capacity and assigned inflows."""
    cut_shelter_ids = {edge.edge_id for edge in bundle.min_cut.shelter_capacity_cuts}
    rows = []
    for shelter_id, detail in bundle.dinic_result.shelter_intakes.items():
        pct = (
            detail.assigned_flow / detail.shelter_capacity * 100.0
            if detail.shelter_capacity > 0
            else 0.0
        )
        rows.append(
            {
                "Shelter ID": shelter_id,
                "Shelter Name": detail.name,
                "Capacity": detail.shelter_capacity,
                "Assigned Flow": detail.assigned_flow,
                "Available": detail.remaining_capacity,
                "Occupancy (%)": round(pct, 1),
                "At Cut Limit": "Yes" if shelter_id in cut_shelter_ids else "No",
            }
        )
    return pd.DataFrame(rows)


def build_routes_dataframe(bundle: FullAnalysisBundle) -> pd.DataFrame:
    """Build a DataFrame of decomposed source-to-shelter evacuation routes."""
    roads = bundle.network.roads
    rows = [
        {
            "Route #": route.route_index,
            "Origin": f"{route.source_id} ({route.source_name})",
            "Destination": f"{route.shelter_id} ({route.shelter_name})",
            "Corridor Sequence": " -> ".join(route.node_path),
            "Roads Used": ", ".join(route.road_ids),
            "Evacuees": route.flow,
            "Distance (km)": round(
                sum(roads[rid].distance for rid in route.road_ids if rid in roads), 2
            ),
            "Est. Travel Time (min)": round(route.total_travel_time_min, 1),
        }
        for route in bundle.routes
    ]
    return pd.DataFrame(rows)


def build_min_cut_dataframe(bundle: FullAnalysisBundle) -> pd.DataFrame:
    """Build a DataFrame listing all Minimum Cut edges categorized by bottleneck type."""
    kind_labels = {
        "road": "Road Corridor Bottleneck",
        "super_sink": "Shelter Capacity Bottleneck",
        "super_source": "Source Demand Limit",
    }
    rows = [
        {
            "Category": kind_labels.get(edge.edge_kind, edge.edge_kind),
            "Element ID": edge.edge_id,
            "Label": edge.label,
            "From": edge.source_id,
            "To": edge.target_id,
            "Cut Capacity": edge.original_capacity,
            "Flow": edge.flow,
        }
        for edge in bundle.min_cut.cut_edges
    ]
    return pd.DataFrame(rows)


def generate_markdown_report(
    bundle: FullAnalysisBundle,
    comparison: AlgorithmComparisonResult | None = None,
) -> str:
    """Create a complete Markdown evacuation analysis and bottleneck audit report."""
    net = bundle.network
    d = bundle.dinic_result
    mc = bundle.min_cut
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# ResQ Evacuation Analysis Report — {net.name}",
        "",
        f"- **Network ID:** `{net.network_id}`",
        f"- **Generated:** {timestamp}",
        f"- **Topology:** {len(net.affected_areas)} Affected Areas | {len(net.junctions)} Junctions | {len(net.shelters)} Shelters | {len(net.roads)} Directed Roads",
        "",
        "## Executive Summary",
        "",
        f"| Metric | Value |",
        f"| :--- | ---: |",
        f"| Total Affected Population | {d.total_population:,} |",
        f"| Total Available Shelter Capacity | {d.total_shelter_capacity:,} |",
        f"| Maximum Evacuation Flow (Dinic) | {d.max_flow:,} |",
        f"| Remaining Unallocated Population | {d.unmet_demand:,} |",
        f"| Evacuation Completion | {d.evacuation_rate * 100:.1f}% |",
        f"| Minimum Cut Total Capacity | {mc.total_cut_capacity:,} |",
        f"| Critical Road Bottlenecks in Cut | {len(mc.road_bottlenecks)} |",
        f"| Shelter Capacity Bottlenecks in Cut | {len(mc.shelter_capacity_cuts)} |",
        "",
        "## Critical Bottlenecks (Minimum Cut Decomposition)",
        "",
        f"- **Road Cut Capacity:** {mc.road_cut_capacity:,}",
        f"- **Shelter Intake Cut Capacity:** {mc.shelter_cut_capacity:,}",
        f"- **Source Demand Cut Capacity:** {mc.super_source_cut_capacity:,}",
        "",
    ]

    if mc.road_bottlenecks:
        lines.extend(
            [
                "| Road ID | Corridor | Cut Capacity | Flow |",
                "| :--- | :--- | ---: | ---: |",
            ]
        )
        for rb in mc.road_bottlenecks:
            lines.append(
                f"| `{rb.edge_id}` | {rb.source_id} -> {rb.target_id} | {rb.original_capacity:,} | {rb.flow:,} |"
            )
    else:
        lines.append("_No physical road edges lie across the S*-T* minimum cut._")

    if bundle.upgrade_candidates:
        lines.extend(
            [
                "",
                "## Infrastructure Upgrade Sensitivity",
                "",
                "| Target | Type | Current Cap | Added Cap | Marginal Flow Gain |",
                "| :--- | :--- | ---: | ---: | ---: |",
            ]
        )
        for cand in bundle.upgrade_candidates[:10]:
            lines.append(
                f"| {cand.label} | {cand.target_kind} | {cand.current_capacity:,} | +{cand.added_capacity:,} | +{cand.marginal_flow_gain:,} |"
            )

    if comparison is not None:
        lines.extend(
            [
                "",
                "## Dinic vs. Greedy Baseline Comparison",
                "",
                f"- **Dinic Optimal Flow:** {comparison.dinic_max_flow:,} ({comparison.dinic_time_ms:.4f} ms)",
                f"- **Greedy Flow (`{comparison.greedy_result.rule}`):** {comparison.greedy_flow:,} ({comparison.greedy_time_ms:.4f} ms)",
                f"- **Flow Optimality Gap:** {comparison.flow_difference:,} evacuees ({comparison.optimality_gap_pct:.1f}%)",
                f"- **Behavioral Note:** {comparison.rule_explanation}",
            ]
        )

    return "\n".join(lines) + "\n"


def generate_html_report(
    bundle: FullAnalysisBundle,
    comparison: AlgorithmComparisonResult | None = None,
) -> str:
    """Create a self-contained dark-slate printable HTML situation briefing."""
    net = bundle.network
    d = bundle.dinic_result
    mc = bundle.min_cut
    escaped_name = html.escape(net.name)
    road_df = build_road_flows_dataframe(bundle)
    cut_df = build_min_cut_dataframe(bundle)

    comp_block = ""
    if comparison is not None:
        comp_block = f"""
        <section>
          <h2>Algorithm Benchmark (Dinic vs. Greedy)</h2>
          <p><strong>Dinic Max Flow:</strong> {comparison.dinic_max_flow:,} ({comparison.dinic_time_ms:.4f} ms)
          &nbsp;|&nbsp; <strong>Greedy ({html.escape(comparison.greedy_result.rule)}):</strong>
          {comparison.greedy_flow:,} ({comparison.greedy_time_ms:.4f} ms)
          &nbsp;|&nbsp; <strong>Gap:</strong> {comparison.flow_difference:,} ({comparison.optimality_gap_pct:.1f}%)</p>
          <p>{html.escape(comparison.rule_explanation)}</p>
        </section>
        """

    cut_table_html = (
        "<p><em>No minimum-cut edges identified (maximum flow is 0 with zero source demand or capacity).</em></p>"
        if cut_df.empty
        else cut_df.to_html(index=False, border=0)
    )
    road_table_html = (
        "<p><em>No directed road corridors present in this network.</em></p>"
        if road_df.empty
        else road_df.to_html(index=False, border=0)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>ResQ Situation Report - {escaped_name}</title>
<style>
  body {{ font-family: Inter, Segoe UI, Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 32px; line-height: 1.5; }}
  h1, h2 {{ color: #f8fafc; border-bottom: 1px solid #334155; padding-bottom: 6px; }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0 24px; }}
  .kpi {{ background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 12px 16px; }}
  .kpi .lbl {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; }}
  .kpi .val {{ font-size: 22px; font-weight: 700; color: #f8fafc; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; font-size: 13px; }}
  th, td {{ border: 1px solid #334155; padding: 8px 10px; text-align: left; }}
  th {{ background: #1e293b; color: #cbd5e1; }}
</style>
</head>
<body>
  <h1>ResQ Evacuation &amp; Bottleneck Report: {escaped_name}</h1>
  <div class="kpi-grid">
    <div class="kpi"><div class="lbl">Affected Population</div><div class="val">{d.total_population:,}</div></div>
    <div class="kpi"><div class="lbl">Shelter Capacity</div><div class="val">{d.total_shelter_capacity:,}</div></div>
    <div class="kpi"><div class="lbl">Max Evacuation Flow</div><div class="val">{d.max_flow:,}</div></div>
    <div class="kpi"><div class="lbl">Unallocated Evacuees</div><div class="val">{d.unmet_demand:,}</div></div>
  </div>
  <section>
    <h2>Minimum Cut Partition &amp; Critical Bottlenecks</h2>
    <p>Max-Flow = Min-Cut Verified: <strong>{d.max_flow:,} = {mc.total_cut_capacity:,}</strong>
    &nbsp;|&nbsp; Reachable Nodes: {len(mc.reachable_domain_nodes)} &nbsp;|&nbsp; Unreachable Nodes: {len(mc.unreachable_domain_nodes)}</p>
    {cut_table_html}
  </section>
  <section>
    <h2>Road Corridor Utilization</h2>
    {road_table_html}
  </section>
  {comp_block}
</body>
</html>
"""
