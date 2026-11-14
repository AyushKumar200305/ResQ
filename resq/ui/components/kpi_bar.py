"""Control-center header, KPI telemetry grid, and analysis-guard banners."""

from dataclasses import dataclass
import html
import streamlit as st

from resq.domain.models import EvacuationNetwork
from resq.services.evacuation_simulator import FullAnalysisBundle
from resq.ui.state import run_primary_analysis, set_flash


@dataclass(frozen=True, slots=True)
class KpiMetric:
    """Single KPI tile descriptor."""

    label: str
    value: str
    subtext: str = ""
    tone: str = "neutral"  # neutral | safe | warn | crit | info


def render_kpi_grid(metrics: list[KpiMetric]) -> None:
    """Render a 4-column responsive grid of dark control-center KPI cards."""
    cards_html: list[str] = []
    for m in metrics:
        tone = m.tone if m.tone in ("neutral", "safe", "warn", "crit", "info") else "neutral"
        cards_html.append(
            f'<div class="resq-kpi-card tone-{tone}">'
            f'<div class="resq-kpi-label">{html.escape(m.label)}</div>'
            f'<div class="resq-kpi-value">{html.escape(m.value)}</div>'
            f'<div class="resq-kpi-sub">{html.escape(m.subtext)}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="resq-kpi-grid">{"".join(cards_html)}</div>',
        unsafe_allow_html=True,
    )


def render_control_header(
    network: EvacuationNetwork,
    bundle: FullAnalysisBundle | None,
    analysis_timestamp: str | None,
) -> None:
    """Render the top operational header showing active scenario and analysis status."""
    title = html.escape(network.name)
    meta = (
        f"ID: {html.escape(network.network_id)} · "
        f"{len(network.affected_areas)} Sources · "
        f"{len(network.junctions)} Junctions · "
        f"{len(network.shelters)} Shelters · "
        f"{len(network.roads)} Roads"
    )

    if bundle is not None:
        rate = bundle.dinic_result.evacuation_rate * 100.0
        if bundle.dinic_result.unmet_demand == 0:
            badge = '<span class="resq-badge resq-badge-safe">Full Evacuation Feasible</span>'
        elif rate >= 70.0:
            badge = '<span class="resq-badge resq-badge-warn">Partial Capacity Deficit</span>'
        else:
            badge = '<span class="resq-badge resq-badge-crit">Severe Bottleneck</span>'
        ts_badge = (
            f'<span class="resq-badge resq-badge-info">Analyzed {html.escape(analysis_timestamp or "")}</span>'
        )
    else:
        badge = '<span class="resq-badge resq-badge-warn">Pending Analysis</span>'
        ts_badge = '<span class="resq-badge resq-badge-info">Topology Mode</span>'

    st.markdown(
        f'<div class="resq-header">'
        f'<div class="resq-title-wrap">'
        f'<div class="resq-title">ResQ Control Center — {title}</div>'
        f'<div class="resq-subtitle">{meta}</div>'
        f"</div>"
        f'<div class="resq-status-row">{badge}{ts_badge}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_pending_analysis_guard(page_label: str, key_suffix: str) -> None:
    """Show a helpful guard banner when analysis hasn't been executed yet."""
    st.info(
        f"No Dinic flow analysis has been run on the current network yet. "
        f"Click **Run Analysis** below (or in the command bar) to compute exact flows, "
        f"minimum-cut bottlenecks, and {page_label} diagnostics."
    )
    if st.button(
        "Run Analysis Now",
        type="primary",
        key=f"inline_run_analysis_{key_suffix}",
    ):
        with st.spinner("Running Dinic Maximum Flow and Minimum Cut extraction..."):
            ok, msg = run_primary_analysis(trace=True)
        set_flash("success" if ok else "error", msg)
        st.rerun()
