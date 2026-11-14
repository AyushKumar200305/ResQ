"""Area priority assessment service for disaster evacuation decision support.

Evaluates hazard severity, time to impact, population at risk, vulnerable population,
and outgoing road accessibility to generate an explainable, deterministic triage ranking.
"""

from typing import Sequence
from resq.algorithms.min_cut import MinCutExtractor
from resq.domain.enums import NodeType
from resq.domain.models import EvacuationNetwork, Node
from resq.domain.relief_models import (
    AreaPriorityAssessment,
    HazardSeverity,
    PriorityTier,
)
from resq.services.evacuation_simulator import FullAnalysisBundle, run_full_evacuation_analysis


def assess_area_priorities(
    network: EvacuationNetwork,
    bundle: FullAnalysisBundle | None = None,
) -> list[AreaPriorityAssessment]:
    """Calculate deterministic evacuation priority rankings and explainable tiers for all affected areas.

    Multi-Criteria Triage Formula:
      Score = SeverityWeight(0..40) + UrgencyWeight(0..30) + VulnerabilityWeight(0..20) + AccessibilityDeficit(0..10)
    """
    if bundle is None:
        bundle = run_full_evacuation_analysis(network, trace=False)

    cut_road_ids = {e.edge_id for e in bundle.min_cut.road_bottlenecks}
    affected_nodes = network.affected_areas
    if not affected_nodes:
        return []

    raw_assessments = []

    for area in affected_nodes:
        # 1. Extract or infer hazard attributes from metadata
        meta = area.metadata or {}
        raw_sev = meta.get("hazard_severity", "moderate")
        sev = HazardSeverity.parse(raw_sev)

        # Default time-to-impact based on severity if omitted
        default_time = {
            HazardSeverity.CRITICAL: 1.5,
            HazardSeverity.HIGH: 3.0,
            HazardSeverity.MODERATE: 6.0,
            HazardSeverity.LOW: 12.0,
        }[sev]
        time_to_impact = float(meta.get("time_to_impact_hours", meta.get("time_to_inundation_hr", default_time)))
        time_to_impact = max(0.25, time_to_impact)

        # Vulnerable population (elderly, infants, patients)
        vulnerable_pop = int(meta.get("vulnerable_population", 0))
        if vulnerable_pop <= 0 and area.population > 0:
            # Default baseline vulnerability ratio (25%)
            vulnerable_pop = int(area.population * float(meta.get("vulnerability_ratio", 0.25)))
        vulnerable_pop = min(area.population, max(0, vulnerable_pop))
        vuln_pct = (vulnerable_pop / area.population * 100.0) if area.population > 0 else 0.0

        # Outgoing road accessibility
        outgoing_roads = [r for r in network.roads.values() if r.source_id == area.node_id and r.is_active]
        outgoing_cap = sum(r.effective_capacity for r in outgoing_roads)
        cap_deficit = max(0, area.population - outgoing_cap)

        # Check if immediate outgoing roads or immediate downstream links are bottleneck cut edges
        spans_cut = any(r.road_id in cut_road_ids for r in outgoing_roads)

        # 2. Multi-Criteria Scoring
        # Severity score (0 to 40)
        sev_scores = {
            HazardSeverity.CRITICAL: 40.0,
            HazardSeverity.HIGH: 28.0,
            HazardSeverity.MODERATE: 15.0,
            HazardSeverity.LOW: 5.0,
        }
        score_sev = sev_scores[sev]

        # Urgency / Time-to-impact score (0 to 30): shorter time = higher score
        # <=1h -> 30, 2h -> 25, 4h -> 15, 8h -> 5, >=12h -> 0
        if time_to_impact <= 1.0:
            score_urgency = 30.0
        elif time_to_impact <= 2.0:
            score_urgency = 25.0
        elif time_to_impact <= 4.0:
            score_urgency = 18.0
        elif time_to_impact <= 6.0:
            score_urgency = 12.0
        elif time_to_impact <= 10.0:
            score_urgency = 6.0
        else:
            score_urgency = 2.0

        # Vulnerability score (0 to 20): percentage of population needing assisted transport
        score_vuln = min(20.0, (vuln_pct / 50.0) * 20.0)

        # Accessibility deficit & bottleneck vulnerability (0 to 10)
        score_access = 0.0
        if cap_deficit > 0:
            score_access += min(5.0, (cap_deficit / max(1, area.population)) * 5.0)
        if spans_cut:
            score_access += 5.0

        total_score = round(score_sev + score_urgency + score_vuln + score_access, 1)

        # 3. Determine Explainable Priority Tier
        if total_score >= 68.0 or (sev == HazardSeverity.CRITICAL and time_to_impact <= 2.0):
            tier = PriorityTier.CRITICAL
        elif total_score >= 48.0 or (sev in (HazardSeverity.CRITICAL, HazardSeverity.HIGH) and time_to_impact <= 4.0):
            tier = PriorityTier.HIGH
        elif total_score >= 28.0:
            tier = PriorityTier.MODERATE
        else:
            tier = PriorityTier.LOW

        # 4. Generate Explainable Justification Narrative ("Why?")
        reasons: list[str] = []
        if sev == HazardSeverity.CRITICAL:
            reasons.append(f"Extreme hazard exposure ({sev.value.upper()}) with rapid inundation in {time_to_impact:.1f}h")
        elif sev == HazardSeverity.HIGH:
            reasons.append(f"High hazard risk with projected impact within {time_to_impact:.1f}h")
        else:
            reasons.append(f"{sev.value.capitalize()} hazard severity with {time_to_impact:.1f}h evacuation window")

        if vuln_pct >= 25.0:
            reasons.append(f"elevated vulnerable population ({vulnerable_pop:,} residents / {vuln_pct:.1f}%) requiring dedicated transit")

        if spans_cut:
            reasons.append("egress corridor is a critical minimum-cut bottleneck at risk of premature saturation")
        elif cap_deficit > 0:
            reasons.append(f"egress road capacity ({outgoing_cap:,} p/h) cannot clear local population ({area.population:,}) in hour 1")
        else:
            reasons.append(f"sufficient local road capacity ({outgoing_cap:,} p/h)")

        explanation = f"Classified as {tier.value.upper()}: " + "; ".join(reasons) + "."

        raw_assessments.append({
            "area_id": area.node_id,
            "area_name": area.name,
            "population": area.population,
            "hazard_severity": sev,
            "time_to_impact_hours": time_to_impact,
            "vulnerable_population": vulnerable_pop,
            "vulnerability_pct": round(vuln_pct, 1),
            "outgoing_capacity": outgoing_cap,
            "capacity_deficit": cap_deficit,
            "spans_minimum_cut": spans_cut,
            "priority_score": total_score,
            "priority_tier": tier,
            "explanation": explanation,
        })

    # Sort descending by priority_score, then ascending by time_to_impact, then descending by population
    raw_assessments.sort(
        key=lambda item: (-item["priority_score"], item["time_to_impact_hours"], -item["population"])
    )

    # Assign dispatch order
    results: list[AreaPriorityAssessment] = []
    for idx, item in enumerate(raw_assessments, start=1):
        results.append(
            AreaPriorityAssessment(
                area_id=item["area_id"],
                area_name=item["area_name"],
                population=item["population"],
                hazard_severity=item["hazard_severity"],
                time_to_impact_hours=item["time_to_impact_hours"],
                vulnerable_population=item["vulnerable_population"],
                vulnerability_pct=item["vulnerability_pct"],
                outgoing_capacity=item["outgoing_capacity"],
                capacity_deficit=item["capacity_deficit"],
                spans_minimum_cut=item["spans_minimum_cut"],
                priority_score=item["priority_score"],
                priority_tier=item["priority_tier"],
                dispatch_order=idx,
                explanation=item["explanation"],
            )
        )

    return results
