"""Unit tests for EvacuationNetwork graph CRUD, validation, copying, and JSON I/O."""

from pathlib import Path
import pytest

from resq import (
    DuplicateIdentifierError,
    EntityNotFoundError,
    EvacuationNetwork,
    GraphValidationError,
    NetworkSerializationError,
    NodeType,
    SUPER_SINK_ID,
    SUPER_SOURCE_ID,
    copy_network,
    export_network_to_json,
    import_network_from_json,
    load_network_json,
    save_network_json,
)


def test_add_and_query_nodes_and_parallel_roads(sample_evacuation_network: EvacuationNetwork) -> None:
    net = sample_evacuation_network
    assert len(net.nodes) == 6
    assert len(net.roads) == 9
    assert net.total_population == 1000
    assert net.total_shelter_capacity == 1050

    parallel = net.get_roads_between("J1", "S1")
    assert [road.road_id for road in parallel] == ["R5_MAIN", "R5_ALT"]
    assert sum(road.capacity for road in parallel) == 550


def test_edit_node_valid_and_atomic_rejection(sample_evacuation_network: EvacuationNetwork) -> None:
    net = sample_evacuation_network
    updated = net.edit_node("A1", name="Harbor Ward North", population=750, x=None)
    assert updated.name == "Harbor Ward North"
    assert updated.population == 750
    assert updated.x is None
    assert net.get_node("A1").population == 750

    # Changing affected_area to junction without zeroing population must fail atomically
    with pytest.raises(GraphValidationError):
        net.edit_node("A1", node_type=NodeType.JUNCTION)
    assert net.get_node("A1").node_type == NodeType.AFFECTED_AREA
    assert net.get_node("A1").population == 750

    # Explicit zeroing succeeds
    retyped = net.edit_node("A1", node_type=NodeType.JUNCTION, population=0)
    assert retyped.node_type == NodeType.JUNCTION
    assert retyped.population == 0


def test_delete_node_cascade_and_non_cascade(sample_evacuation_network: EvacuationNetwork) -> None:
    net = sample_evacuation_network
    with pytest.raises(GraphValidationError):
        net.delete_node("J1", cascade=False)
    assert "J1" in net.nodes

    removed_roads = net.delete_node("J1", cascade=True)
    removed_ids = {road.road_id for road in removed_roads}
    assert removed_ids == {"R1", "R4_N2S", "R4_S2N", "R5_MAIN", "R5_ALT"}
    assert "J1" not in net.nodes
    for rid in removed_ids:
        assert rid not in net.roads


def test_add_edit_delete_road(sample_evacuation_network: EvacuationNetwork) -> None:
    net = sample_evacuation_network
    added = net.add_road("R_EXTRA", "A2", "J1", 120, name="Emergency Detour")
    assert added.capacity == 120
    assert "R_EXTRA" in net.roads

    edited = net.edit_road("R_EXTRA", capacity=180, is_active=False)
    assert edited.capacity == 180
    assert edited.effective_capacity == 0
    assert edited.is_active is False

    # Invalid edit preserves existing road intact
    with pytest.raises(EntityNotFoundError):
        net.edit_road("R_EXTRA", target_id="UNKNOWN_NODE")
    assert net.get_road("R_EXTRA").target_id == "J1"

    deleted = net.delete_road("R_EXTRA")
    assert deleted.road_id == "R_EXTRA"
    assert "R_EXTRA" not in net.roads


@pytest.mark.parametrize(
    "bad_cap",
    [-1, -50, 12.5, True, False, "100", None],
)
def test_rejects_invalid_non_integer_or_negative_capacities(bad_cap: object) -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Zone A", NodeType.AFFECTED_AREA, population=100)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=100)

    with pytest.raises(GraphValidationError):
        net.add_road("R1", "A1", "S1", bad_cap)  # type: ignore[arg-type]

    with pytest.raises(GraphValidationError):
        net.add_node("A2", "Zone B", NodeType.AFFECTED_AREA, population=bad_cap)  # type: ignore[arg-type]


def test_prevents_duplicate_ids_self_loops_missing_nodes_and_reserved_ids() -> None:
    net = EvacuationNetwork()
    net.add_node("A1", "Zone A", NodeType.AFFECTED_AREA, population=100)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=100)

    with pytest.raises(DuplicateIdentifierError):
        net.add_node("A1", "Duplicate", NodeType.JUNCTION)

    with pytest.raises(GraphValidationError):
        net.add_node(SUPER_SOURCE_ID, "Reserved", NodeType.AFFECTED_AREA, population=10)

    with pytest.raises(GraphValidationError):
        net.add_node(SUPER_SINK_ID, "Reserved", NodeType.SHELTER, shelter_capacity=10)

    with pytest.raises(EntityNotFoundError):
        net.add_road("R_BAD_SRC", "MISSING", "S1", 50)

    with pytest.raises(EntityNotFoundError):
        net.add_road("R_BAD_DST", "A1", "MISSING", 50)

    with pytest.raises(GraphValidationError):
        net.add_road("R_LOOP", "A1", "A1", 50)

    net.add_road("R1", "A1", "S1", 50)
    with pytest.raises(DuplicateIdentifierError):
        net.add_road("R1", "S1", "A1", 50)


def test_prevents_invalid_source_and_shelter_configurations() -> None:
    net = EvacuationNetwork()
    with pytest.raises(GraphValidationError):
        net.add_node(
            "A_BAD",
            "Invalid Area",
            NodeType.AFFECTED_AREA,
            population=100,
            shelter_capacity=50,
        )
    with pytest.raises(GraphValidationError):
        net.add_node(
            "J_BAD_POP",
            "Invalid Junction",
            NodeType.JUNCTION,
            population=10,
        )
    with pytest.raises(GraphValidationError):
        net.add_node(
            "J_BAD_CAP",
            "Invalid Junction",
            NodeType.JUNCTION,
            shelter_capacity=10,
        )
    with pytest.raises(GraphValidationError):
        net.add_node(
            "S_BAD",
            "Invalid Shelter",
            NodeType.SHELTER,
            population=20,
            shelter_capacity=100,
        )


def test_validate_network_reports_errors_and_warnings() -> None:
    net = EvacuationNetwork()
    net.add_node("J1", "Lonely Junction", NodeType.JUNCTION)
    report = net.validate()
    assert not report.is_valid
    assert len(report.errors) == 2  # missing affected_area and missing shelter

    net.add_node("A1", "Zone A", NodeType.AFFECTED_AREA, population=500)
    net.add_node("S1", "Shelter 1", NodeType.SHELTER, shelter_capacity=200)
    report_warn = net.validate()
    assert report_warn.is_valid
    assert len(report_warn.warnings) >= 3  # shelter deficit, isolated source, isolated shelter


def test_independent_copy_preserves_original_network(
    sample_evacuation_network: EvacuationNetwork,
) -> None:
    original = sample_evacuation_network
    original.metadata["scenario_tag"] = {"severity": "baseline"}

    cloned = copy_network(original, new_network_id="disrupted-v1", new_name="Bridge Out")
    cloned.edit_node("A1", population=999)
    cloned.edit_road("R1", capacity=0, is_active=False)
    cloned.delete_road("R5_ALT")
    cloned.add_node("S3", "Backup School", NodeType.SHELTER, shelter_capacity=300)
    cloned.metadata["scenario_tag"]["severity"] = "critical"

    assert original.network_id == "coastal-sector-1"
    assert original.get_node("A1").population == 600
    assert original.get_road("R1").capacity == 450
    assert original.get_road("R1").is_active is True
    assert "R5_ALT" in original.roads
    assert "S3" not in original.nodes
    assert original.metadata["scenario_tag"]["severity"] == "baseline"


def test_json_roundtrip_and_file_save_load(
    sample_evacuation_network: EvacuationNetwork,
    tmp_path: Path,
) -> None:
    raw_json = export_network_to_json(sample_evacuation_network)
    restored = import_network_from_json(raw_json)
    assert restored.to_dict() == sample_evacuation_network.to_dict()

    file_path = tmp_path / "scenarios" / "coastal.json"
    saved_path = save_network_json(sample_evacuation_network, file_path)
    assert saved_path.exists()

    loaded = load_network_json(saved_path)
    assert loaded.to_dict() == sample_evacuation_network.to_dict()


def test_import_rejects_malformed_or_invalid_json(tmp_path: Path) -> None:
    with pytest.raises(NetworkSerializationError):
        import_network_from_json("{invalid json")

    with pytest.raises(NetworkSerializationError):
        import_network_from_json('{"schema_version": "9.9", "nodes": [], "roads": []}')

    with pytest.raises(EntityNotFoundError):
        import_network_from_json(
            '{"schema_version": "1.0", "nodes": [], '
            '"roads": [{"road_id": "R1", "source_id": "X", "target_id": "Y", "capacity": 10}]}'
        )

    with pytest.raises(NetworkSerializationError):
        load_network_json(tmp_path / "does_not_exist.json")
