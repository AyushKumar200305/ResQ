"""ResQ — Disaster Evacuation Flow and Bottleneck Analysis Optimizer (Streamlit Entry Point)."""

import streamlit as st

st.set_page_config(
    page_title="ResQ — Evacuation Flow & Bottleneck Optimizer",
    layout="wide",
    initial_sidebar_state="expanded",
)

from resq.domain.exceptions import ResQError  # noqa: E402
from resq.ui.components import render_control_header  # noqa: E402
from resq.ui.state import (  # noqa: E402
    PAGES,
    consume_flash,
    get_active_network,
    get_analysis_bundle,
    load_demo_network,
    navigate_to,
    reset_workspace,
    run_primary_analysis,
    save_current_scenario,
    set_flash,
    init_session_state,
)
from resq.ui.theme import inject_control_center_css  # noqa: E402
from resq.ui.views import (  # noqa: E402
    render_about_resq_page,
    render_algorithm_comparison_page,
    render_bottleneck_analysis_page,
    render_flow_analysis_page,
    render_live_simulation_page,
    render_network_builder_page,
    render_overview_page,
    render_reports_page,
    render_scenario_lab_page,
    render_shortest_path_page,
)

init_session_state()
inject_control_center_css()

# ---- Sidebar Navigation & Operational Context ----
with st.sidebar:
    st.markdown("### ResQ Operations")
    st.caption("Disaster Evacuation Flow & Min-Cut Optimizer")
    st.divider()

    selected_page = st.radio(
        "Navigation",
        options=PAGES,
        key="nav_radio",
        label_visibility="collapsed",
    )
    st.session_state["active_page"] = selected_page

    st.divider()
    active_net = get_active_network()
    has_analysis = get_analysis_bundle() is not None
    st.markdown("**Active Topology Summary**")
    st.caption(
        f"Scenario: {active_net.name}\n\n"
        f"Population: {active_net.total_population:,} | "
        f"Shelter Cap: {active_net.total_shelter_capacity:,}\n\n"
        f"Sources: {len(active_net.affected_areas)} | "
        f"Junctions: {len(active_net.junctions)} | "
        f"Shelters: {len(active_net.shelters)} | "
        f"Roads: {len(active_net.roads)}\n\n"
        f"Status: {'Analyzed' if has_analysis else 'Pending Analysis'}"
    )

# ---- Top Control Header & Primary Action Toolbar ----
active_net = get_active_network()
bundle = get_analysis_bundle()
render_control_header(
    active_net,
    bundle,
    st.session_state.get("analysis_timestamp"),
)

cmd1, cmd2, cmd3, cmd4, cmd5, cmd6 = st.columns(6, gap="small")
with cmd1:
    if st.button(
        "Load Demo Network",
        width="stretch",
        help="Restore the Metro River Basin Flood demo topology.",
        key="cmd_load_demo",
    ):
        ok, msg = load_demo_network("metro_flood_baseline")
        set_flash("success" if ok else "error", msg)
        st.rerun()

with cmd2:
    if st.button(
        "Build Network",
        width="stretch",
        help="Open Network Builder to add, edit, or delete nodes and roads.",
        key="cmd_build_net",
    ):
        navigate_to("Network Builder")

with cmd3:
    if st.button(
        "Run Analysis",
        type="primary",
        width="stretch",
        help="Run Dinic Maximum Flow, Minimum Cut, and Route Decomposition.",
        key="cmd_run_analysis",
    ):
        with st.spinner("Running Dinic's Max Flow, Minimum Cut, and Route Decomposition..."):
            ok, msg = run_primary_analysis(trace=True)
        set_flash("success" if ok else "error", msg)
        st.rerun()

with cmd4:
    if st.button(
        "Reset",
        width="stretch",
        help="Clear derived analysis outputs and temporary simulation disruptions.",
        key="cmd_reset",
    ):
        msg = reset_workspace()
        set_flash("info", msg)
        st.rerun()

with cmd5:
    if st.button(
        "Save Scenario",
        width="stretch",
        help="Save an independent snapshot of the current network into Scenario Lab.",
        key="cmd_save_scenario",
    ):
        ok, msg = save_current_scenario()
        set_flash("success" if ok else "error", msg)
        st.rerun()

with cmd6:
    if st.button(
        "Export Results",
        width="stretch",
        help="Open Reports & Export center for JSON, CSV, HTML, Markdown, and PDF.",
        key="cmd_export_results",
    ):
        navigate_to("Reports")

flash = consume_flash()
if flash is not None:
    level, text = flash
    if level == "success":
        st.success(text)
    elif level == "warning":
        st.warning(text)
    elif level == "error":
        st.error(text)
    else:
        st.info(text)

# ---- Active Page Router ----
PAGE_RENDERERS = {
    "Overview": render_overview_page,
    "Network Builder": render_network_builder_page,
    "Live Simulation": render_live_simulation_page,
    "Flow Analysis": render_flow_analysis_page,
    "Bottleneck Analysis": render_bottleneck_analysis_page,
    "Scenario Lab": render_scenario_lab_page,
    "Algorithm Comparison": render_algorithm_comparison_page,
    "Shortest Path (Dijkstra)": render_shortest_path_page,
    "Reports": render_reports_page,
    "About ResQ": render_about_resq_page,
}

try:
    PAGE_RENDERERS[selected_page]()
except ResQError as exc:
    st.error(f"Operational error: {exc}")
except Exception as exc:
    st.error(
        f"Unexpected application error while rendering '{selected_page}': {exc}. "
        "Try clicking Reset or Load Demo Network to recover cleanly."
    )
