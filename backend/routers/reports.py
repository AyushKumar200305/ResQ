"""Report export endpoints: JSON configuration, CSV tables, and PDF situation reports."""

import json
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import Response

from resq.domain.exceptions import GraphValidationError
from resq.services.evacuation_simulator import run_full_evacuation_analysis
from resq.services.pdf_report import generate_pdf_report
from resq.services.report_generator import build_road_flows_dataframe
from resq.services.scenario_lab import build_scenario_lab_comparison_dataframe
from backend.routers.scenarios import run_all_standard_scenarios

from backend.state import state_manager

router = APIRouter(prefix="/api/reports", tags=["Reports & Exports"])


@router.get("/json", summary="Export active network as JSON")
def export_network_json() -> Response:
    """Download the current active evacuation network topology as JSON."""
    net = state_manager.get_network(make_copy=False)
    content = json.dumps(net.to_dict(), indent=2)
    filename = f"{net.network_id}_network.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv/roads", summary="Export road flow analysis as CSV")
def export_roads_csv() -> Response:
    """Download calculated road flows, capacity utilization, and bottleneck flags as CSV."""
    net = state_manager.get_network(make_copy=True)
    try:
        bundle = state_manager.get_bundle()
        if bundle is None:
            bundle = run_full_evacuation_analysis(net, trace=False)
            state_manager.set_bundle(bundle)

        df = build_road_flows_dataframe(bundle)
        csv_text = df.to_csv(index=False)
        filename = f"{net.network_id}_road_flows.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/csv/scenarios", summary="Export scenario comparison matrix as CSV")
def export_scenarios_csv() -> Response:
    """Download what-if scenario comparison table as CSV."""
    net = state_manager.get_network(make_copy=True)
    try:
        scenarios = state_manager.get_scenarios()
        if not scenarios:
            scenarios = run_all_standard_scenarios(net)
            state_manager.set_scenarios(scenarios)

        df = build_scenario_lab_comparison_dataframe(scenarios)
        csv_text = df.to_csv(index=False)
        filename = f"{net.network_id}_scenario_comparison.csv"
        return Response(
            content=csv_text,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/pdf", summary="Generate and stream professional PDF situation report")
def export_pdf_report() -> Response:
    """Generate and stream a vector-charted PDF evacuation situation report."""
    net = state_manager.get_network(make_copy=True)
    try:
        bundle = state_manager.get_bundle()
        if bundle is None:
            bundle = run_full_evacuation_analysis(net, trace=False)
            state_manager.set_bundle(bundle)

        comparison = state_manager.get_comparison()
        scenarios = state_manager.get_scenarios()
        if not scenarios:
            try:
                scenarios = run_all_standard_scenarios(net)
                state_manager.set_scenarios(scenarios)
            except Exception:
                scenarios = None

        pdf_bytes = generate_pdf_report(
            bundle,
            comparison=comparison,
            scenario_evaluations=scenarios or None,
        )

        filename = f"ResQ_Situation_Report_{net.network_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except GraphValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
