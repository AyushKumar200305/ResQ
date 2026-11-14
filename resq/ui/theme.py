"""Semantic color palette and Plotly theme defaults for ResQ control-center UI."""

from pathlib import Path
import streamlit as st

BG_CANVAS = "#0B0F17"
BG_SURFACE = "#111827"
BG_SURFACE_ALT = "#161F30"
BORDER_SUBTLE = "#263244"

TEXT_PRIMARY = "#F1F5F9"
TEXT_MUTED = "#94A3B8"
TEXT_SUBTLE = "#64748B"

COLOR_SAFE = "#22C55E"
COLOR_WARN = "#F59E0B"
COLOR_CRIT = "#EF4444"
COLOR_ORANGE = "#F97316"
COLOR_INFO = "#38BDF8"
COLOR_IDLE = "#475569"

_CSS_PATH = Path(__file__).resolve().parents[2] / "assets" / "styles.css"


def inject_control_center_css() -> None:
    """Inject the custom dark emergency-management CSS into Streamlit."""
    if _CSS_PATH.exists():
        css = _CSS_PATH.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def apply_plotly_dark_theme(fig, *, height: int = 440, title: str | None = None):
    """Apply consistent dark navy control-center styling to a Plotly figure."""
    layout_kwargs = dict(
        template="plotly_dark",
        paper_bgcolor=BG_SURFACE,
        plot_bgcolor=BG_CANVAS,
        height=height,
        font=dict(
            family="Inter, Segoe UI, system-ui, sans-serif",
            color=TEXT_PRIMARY,
            size=12,
        ),
        margin=dict(l=28, r=24, t=44 if title else 24, b=28),
        xaxis=dict(automargin=True),
        yaxis=dict(automargin=True),
        legend=dict(
            bgcolor="rgba(17, 24, 39, 0.85)",
            bordercolor=BORDER_SUBTLE,
            borderwidth=1,
            font=dict(size=11, color=TEXT_MUTED),
        ),
    )
    if title:
        layout_kwargs["title"] = dict(
            text=title,
            font=dict(size=14, color=TEXT_PRIMARY),
            x=0.01,
            xanchor="left",
        )
    fig.update_layout(**layout_kwargs)
    return fig


def render_chart(fig, *, key: str | None = None) -> None:
    """Render a Plotly figure sized cleanly to container width."""
    st.plotly_chart(fig, width="stretch", key=key)


def render_table(df, *, hide_index: bool = True, height: int | None = None) -> None:
    """Render a Pandas DataFrame sized cleanly to container width."""
    kwargs = {"width": "stretch", "hide_index": hide_index}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df, **kwargs)
