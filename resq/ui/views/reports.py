"""Page 8: Reports & Export Center (JSON, CSV, Scenario CSV, Markdown, HTML, and PDF)."""

import streamlit as st

from resq.services.pdf_report import generate_pdf_report
from resq.services.report_generator import (
    build_min_cut_dataframe,
    build_road_flows_dataframe,
    build_routes_dataframe,
    build_shelters_dataframe,
    build_sources_dataframe,
    generate_html_report,
    generate_markdown_report,
)
from resq.services.scenario_io import export_network_to_json
from resq.services.scenario_lab import (
    ScenarioEvaluation,
    build_scenario_lab_comparison_dataframe,
)
from resq.ui.components import render_pending_analysis_guard
from resq.ui.state import (
    get_active_network,
    get_analysis_bundle,
    get_comparison_result,
)
from resq.ui.theme import render_table


def _safe_filename_stem(raw_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in raw_id).strip("_")
    return cleaned or "resq_network"


def render_reports_page() -> None:
    """Render exportable JSON, CSV tables, scenario comparison CSV, and PDF/HTML/MD reports."""
    net = get_active_network()
    bundle = get_analysis_bundle()
    comparison = get_comparison_result()
    safe_stem = _safe_filename_stem(net.network_id)

    st.markdown(
        '<div class="resq-section-title">Network Configuration Export</div>',
        unsafe_allow_html=True,
    )
    network_json = export_network_to_json(net)
    st.download_button(
        label="Download Network Configuration (JSON)",
        data=network_json,
        file_name=f"{safe_stem}_network.json",
        mime="application/json",
        key="dl_network_json",
    )

    if bundle is None:
        report = net.validate()
        if report.is_valid:
            render_pending_analysis_guard("Reports & Exports", "reports")
        else:
            st.error("Network validation errors: " + " | ".join(report.errors))
        return

    st.markdown(
        '<div class="resq-section-title">Analysis & Executive Report Downloads</div>',
        unsafe_allow_html=True,
    )
    roads_df = build_road_flows_dataframe(bundle)
    sources_df = build_sources_dataframe(bundle)
    shelters_df = build_shelters_dataframe(bundle)
    routes_df = build_routes_dataframe(bundle)
    cut_df = build_min_cut_dataframe(bundle)

    # Scenario comparison DataFrame (uses Scenario Lab suite if evaluated, else baseline from bundle)
    lab_suite: dict[str, ScenarioEvaluation] = st.session_state.get(
        "scenario_lab_suite", {}
    )
    if lab_suite:
        scenario_evals = list(lab_suite.values())
    else:
        scenario_evals = [
            ScenarioEvaluation(
                scenario_key="scenario_1_baseline",
                scenario_name="Scenario 1: Normal Conditions (Baseline)",
                scenario_kind="baseline",
                description="Current evaluated baseline network.",
                network=bundle.network,
                bundle=bundle,
                baseline_delta=0,
                baseline_delta_pct=0.0,
                observations=(),
            )
        ]
    scn_comp_df = build_scenario_lab_comparison_dataframe(scenario_evals)

    md_report = generate_markdown_report(bundle, comparison)
    html_report = generate_html_report(bundle, comparison)
    pdf_bytes = generate_pdf_report(
        bundle,
        comparison=comparison,
        scenario_evaluations=scenario_evals if lab_suite else None,
    )

    p1, p2, p3, p4 = st.columns(4)
    p1.download_button(
        "Download PDF Report (.pdf)",
        data=pdf_bytes,
        file_name=f"{safe_stem}_resq_report.pdf",
        mime="application/pdf",
        type="primary",
        width="stretch",
        key="dl_pdf",
    )
    p2.download_button(
        "Analysis Results / Road Flows (.csv)",
        data=roads_df.to_csv(index=False),
        file_name=f"{safe_stem}_analysis_results.csv",
        mime="text/csv",
        width="stretch",
        key="dl_roads_csv",
    )
    p3.download_button(
        "Scenario Comparison (.csv)",
        data=scn_comp_df.to_csv(index=False),
        file_name=f"{safe_stem}_scenario_comparison.csv",
        mime="text/csv",
        width="stretch",
        key="dl_scn_csv",
    )
    p4.download_button(
        "Printable Briefing (.html)",
        data=html_report,
        file_name=f"{safe_stem}_report.html",
        mime="text/html",
        width="stretch",
        key="dl_html",
    )

    s1, s2, s3 = st.columns(3)
    s1.download_button(
        "Min-Cut Bottlenecks (.csv)",
        data=cut_df.to_csv(index=False),
        file_name=f"{safe_stem}_bottlenecks.csv",
        mime="text/csv",
        width="stretch",
        key="dl_cut_csv",
    )
    s2.download_button(
        "Evacuation Routes (.csv)",
        data=routes_df.to_csv(index=False),
        file_name=f"{safe_stem}_routes.csv",
        mime="text/csv",
        width="stretch",
        key="dl_routes_csv",
    )
    s3.download_button(
        "Markdown Report (.md)",
        data=md_report,
        file_name=f"{safe_stem}_report.md",
        mime="text/markdown",
        width="stretch",
        key="dl_md",
    )

    t_md, t_roads, t_entities, t_cuts, t_scn = st.tabs(
        [
            "Situation Briefing",
            "Road Flows",
            "Sources & Shelters",
            "Min-Cut Audit",
            "Scenario Comparison",
        ]
    )
    with t_md:
        st.markdown(md_report)
    with t_roads:
        render_table(roads_df)
    with t_entities:
        c1, c2 = st.columns(2)
        with c1:
            render_table(sources_df)
        with c2:
            render_table(shelters_df)
    with t_cuts:
        render_table(cut_df)
    with t_scn:
        render_table(scn_comp_df)
