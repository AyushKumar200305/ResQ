"""Page 2: Interactive Network Builder."""

import pandas as pd
import streamlit as st

from resq.domain.enums import NodeType
from resq.domain.exceptions import ResQError
from resq.services.presets import list_presets
from resq.services.scenario_io import import_network_from_json
from resq.ui.components import build_network_figure
from resq.ui.state import (
    get_active_network,
    invalidate_analysis,
    load_demo_network,
    reset_network_to_empty,
    run_primary_analysis,
    set_flash,
)
from resq.ui.theme import render_chart, render_table


def _default_coords_for_role(role: NodeType, current_count: int) -> tuple[float, float]:
    col = current_count // 5
    row = current_count % 5
    base_x = {
        NodeType.AFFECTED_AREA: 0.0 - col * 1.4,
        NodeType.JUNCTION: 4.5 + (col % 2) * 1.2 - (col // 2) * 1.2,
        NodeType.SHELTER: 9.0 + col * 1.4,
    }[role]
    y_offset = 3.0 - row * 1.5
    return base_x, y_offset


def render_network_builder_page() -> None:
    """Render interactive graph creation, editing, deletion, and live preview."""
    net = get_active_network()
    rev = st.session_state.get("network_revision", 1)

    # Top utility bar inside Builder
    u1, u2, u3, u4 = st.columns([2.2, 1.3, 1.2, 1.3], vertical_alignment="bottom")
    presets = list_presets()
    with u1:
        preset_choice = st.selectbox(
            "Load Built-in Topology",
            options=[p.key for p in presets],
            format_func=lambda k: next(p.title for p in presets if p.key == k),
            key="builder_preset_select",
        )
    with u2:
        if st.button("Load Selected Preset", width="stretch", key="builder_load_preset"):
            ok, msg = load_demo_network(preset_choice)
            set_flash("success" if ok else "error", msg)
            st.rerun()
    with u3:
        if st.button("Clear / Blank Graph", width="stretch", key="builder_clear_blank"):
            reset_network_to_empty()
            set_flash("info", "Cleared network to a blank canvas. Add nodes and roads below.")
            st.rerun()
    with u4:
        if st.button("Validate & Run Analysis", type="primary", width="stretch", key="builder_run"):
            with st.spinner("Validating topology and solving max flow..."):
                ok, msg = run_primary_analysis(trace=True)
            set_flash("success" if ok else "error", msg)
            st.rerun()

    left_col, right_col = st.columns([1.1, 1.3], gap="large")

    with left_col:
        # Network Metadata Editor
        with st.expander("Network Metadata", expanded=False):
            with st.form(f"meta_form_{rev}"):
                new_net_name = st.text_input("Scenario Name", value=net.name)
                new_desc = st.text_area("Description", value=net.description, height=70)
                if st.form_submit_button("Update Metadata"):
                    if not new_net_name.strip():
                        st.error("Scenario name cannot be empty.")
                    else:
                        net.name = new_net_name.strip()
                        net.description = new_desc
                        set_flash("success", "Scenario metadata updated.")
                        st.rerun()

        tab_add_node, tab_add_road, tab_edit_node, tab_edit_road, tab_import = st.tabs(
            ["Add Node", "Add Road", "Edit / Delete Node", "Edit / Delete Road", "Import JSON"]
        )

        # ---- TAB 1: ADD NODE ----
        with tab_add_node:
            role_str = st.selectbox(
                "Node Type",
                options=[
                    NodeType.AFFECTED_AREA.value,
                    NodeType.JUNCTION.value,
                    NodeType.SHELTER.value,
                ],
                format_func=lambda v: {
                    "affected_area": "Affected Area (Source)",
                    "junction": "Junction (Intermediate)",
                    "shelter": "Shelter (Destination)",
                }[v],
                key=f"add_node_type_{rev}",
            )
            parsed_role = NodeType.parse(role_str)
            role_count = len(net.get_nodes_by_type(parsed_role))
            def_x, def_y = _default_coords_for_role(parsed_role, role_count)

            with st.form(f"add_node_form_{rev}_{role_str}"):
                c_id, c_nm = st.columns(2)
                node_id = c_id.text_input(
                    "Unique Node ID",
                    placeholder="e.g., A4, J6, S4",
                    key=f"add_node_id_{rev}_{role_str}",
                )
                node_name = c_nm.text_input(
                    "Display Name",
                    placeholder="e.g., North Pier",
                    key=f"add_node_name_{rev}_{role_str}",
                )

                pop_val = 0
                shl_val = 0
                if parsed_role == NodeType.AFFECTED_AREA:
                    pop_val = int(
                        st.number_input(
                            "Affected Population (Evacuees)",
                            min_value=0,
                            step=50,
                            value=500,
                            key=f"add_node_pop_{rev}_{role_str}",
                        )
                    )
                elif parsed_role == NodeType.SHELTER:
                    shl_val = int(
                        st.number_input(
                            "Shelter Capacity (Beds)",
                            min_value=0,
                            step=50,
                            value=600,
                            key=f"add_node_cap_{rev}_{role_str}",
                        )
                    )
                else:
                    st.caption("Junction vertices forward evacuation flow without supply or shelter intake.")

                cx, cy = st.columns(2)
                coord_x = cx.number_input(
                    "Map X",
                    value=float(def_x),
                    step=0.5,
                    key=f"add_node_x_{rev}_{role_str}",
                )
                coord_y = cy.number_input(
                    "Map Y",
                    value=float(def_y),
                    step=0.5,
                    key=f"add_node_y_{rev}_{role_str}",
                )

                if st.form_submit_button("Add Node", type="primary"):
                    try:
                        created = net.add_node(
                            node_id=node_id.strip(),
                            name=node_name.strip(),
                            node_type=parsed_role,
                            population=pop_val,
                            shelter_capacity=shl_val,
                            x=float(coord_x),
                            y=float(coord_y),
                        )
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        invalidate_analysis()
                        set_flash("success", f"Added {created.node_type.value} node '{created.node_id}'.")
                        st.rerun()

        # ---- TAB 2: ADD ROAD ----
        with tab_add_road:
            node_ids = list(net.nodes.keys())
            if len(node_ids) < 2:
                st.info("Add at least two nodes before creating directed road connections.")
            else:
                with st.form(f"add_road_form_{rev}"):
                    r_col1, r_col2 = st.columns(2)
                    road_id = r_col1.text_input(
                        "Unique Road ID",
                        placeholder="e.g., R_A1_J4",
                        key=f"add_road_id_{rev}",
                    )
                    road_name = r_col2.text_input(
                        "Road Name (Optional)",
                        placeholder="e.g., West Bridge",
                        key=f"add_road_name_{rev}",
                    )

                    e_col1, e_col2 = st.columns(2)
                    src_id = e_col1.selectbox(
                        "From Node",
                        options=node_ids,
                        format_func=lambda nid: f"{nid} ({net.nodes[nid].name})",
                        key=f"add_road_src_{rev}",
                    )
                    dst_id = e_col2.selectbox(
                        "To Node",
                        options=node_ids,
                        index=min(1, len(node_ids) - 1),
                        format_func=lambda nid: f"{nid} ({net.nodes[nid].name})",
                        key=f"add_road_dst_{rev}",
                    )

                    m_col1, m_col2, m_col3 = st.columns(3)
                    road_cap = int(
                        m_col1.number_input(
                            "Road Capacity",
                            min_value=0,
                            step=50,
                            value=400,
                            key=f"add_road_cap_{rev}",
                        )
                    )
                    road_dist = float(
                        m_col2.number_input(
                            "Distance (km)",
                            min_value=0.0,
                            step=0.5,
                            value=2.5,
                            key=f"add_road_dist_{rev}",
                        )
                    )
                    travel_min = float(
                        m_col3.number_input(
                            "Travel Time (min)",
                            min_value=0.0,
                            step=1.0,
                            value=10.0,
                            key=f"add_road_time_{rev}",
                        )
                    )
                    add_bidirectional = st.checkbox(
                        "Also create opposite-direction corridor (two-way road)",
                        value=False,
                        key=f"add_road_bidir_{rev}",
                    )

                    if st.form_submit_button("Connect Road", type="primary"):
                        try:
                            clean_rid = road_id.strip()
                            rev_id = f"{clean_rid}_REV"
                            if add_bidirectional and rev_id in net.roads:
                                from resq.domain.exceptions import DuplicateIdentifierError

                                raise DuplicateIdentifierError(
                                    f"Cannot add two-way road: reverse road identifier '{rev_id}' already exists."
                                )
                            net.add_road(
                                road_id=clean_rid,
                                source_id=src_id,
                                target_id=dst_id,
                                capacity=road_cap,
                                name=road_name.strip(),
                                distance=road_dist,
                                travel_time_min=travel_min,
                            )
                            if add_bidirectional:
                                rev_name = f"{road_name.strip()} (Return)" if road_name.strip() else ""
                                net.add_road(
                                    road_id=rev_id,
                                    source_id=dst_id,
                                    target_id=src_id,
                                    capacity=road_cap,
                                    name=rev_name,
                                    distance=road_dist,
                                    travel_time_min=travel_min,
                                )
                        except ResQError as exc:
                            st.error(str(exc))
                        else:
                            invalidate_analysis()
                            msg = f"Connected {src_id} -> {dst_id} (Road '{clean_rid}')."
                            if add_bidirectional:
                                msg += f" Also created return road '{clean_rid}_REV'."
                            set_flash("success", msg)
                            st.rerun()

        # ---- TAB 3: EDIT / DELETE NODE ----
        with tab_edit_node:
            node_ids = list(net.nodes.keys())
            if not node_ids:
                st.info("No nodes available to edit.")
            else:
                sel_nid = st.selectbox(
                    "Select Node",
                    options=node_ids,
                    format_func=lambda nid: f"{nid} — {net.nodes[nid].name} ({net.nodes[nid].node_type.value})",
                    key=f"edit_node_sel_{rev}",
                )
                target_node = net.get_node(sel_nid)
                new_role_str = st.selectbox(
                    "Node Role",
                    options=[t.value for t in NodeType],
                    index=[t.value for t in NodeType].index(target_node.node_type.value),
                    key=f"edit_node_role_{rev}_{sel_nid}",
                )
                parsed_new_role = NodeType.parse(new_role_str)

                with st.form(f"edit_node_form_{rev}_{sel_nid}_{new_role_str}"):
                    edit_name = st.text_input(
                        "Display Name",
                        value=target_node.name,
                        key=f"edit_node_name_{rev}_{sel_nid}",
                    )
                    edit_pop = 0
                    edit_cap = 0
                    if parsed_new_role == NodeType.AFFECTED_AREA:
                        edit_pop = int(
                            st.number_input(
                                "Affected Population",
                                min_value=0,
                                step=50,
                                value=target_node.population,
                                key=f"edit_node_pop_{rev}_{sel_nid}",
                            )
                        )
                    elif parsed_new_role == NodeType.SHELTER:
                        edit_cap = int(
                            st.number_input(
                                "Shelter Capacity",
                                min_value=0,
                                step=50,
                                value=target_node.shelter_capacity,
                                key=f"edit_node_cap_{rev}_{sel_nid}",
                            )
                        )
                    ex, ey = st.columns(2)
                    edit_x = ex.number_input(
                        "Map X",
                        value=float(target_node.x if target_node.x is not None else 0.0),
                        step=0.5,
                        key=f"edit_node_x_{rev}_{sel_nid}_{new_role_str}",
                    )
                    edit_y = ey.number_input(
                        "Map Y",
                        value=float(target_node.y if target_node.y is not None else 0.0),
                        step=0.5,
                        key=f"edit_node_y_{rev}_{sel_nid}_{new_role_str}",
                    )

                    if st.form_submit_button("Save Node Changes", type="primary"):
                        try:
                            net.edit_node(
                                sel_nid,
                                name=edit_name.strip(),
                                node_type=parsed_new_role,
                                population=edit_pop,
                                shelter_capacity=edit_cap,
                                x=float(edit_x),
                                y=float(edit_y),
                            )
                        except ResQError as exc:
                            st.error(str(exc))
                        else:
                            invalidate_analysis()
                            set_flash("success", f"Updated node '{sel_nid}'.")
                            st.rerun()

                incident = net.get_outgoing_roads(sel_nid) + net.get_incoming_roads(sel_nid)
                if incident:
                    st.caption(
                        f"Deleting '{sel_nid}' will also remove {len(incident)} connected road(s): "
                        + ", ".join(r.road_id for r in incident)
                    )
                if st.button(f"Delete Node '{sel_nid}'", key=f"del_node_btn_{rev}_{sel_nid}"):
                    try:
                        removed = net.delete_node(sel_nid, cascade=True)
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        invalidate_analysis()
                        set_flash(
                            "warning",
                            f"Deleted node '{sel_nid}' and {len(removed)} incident road(s).",
                        )
                        st.rerun()

        # ---- TAB 4: EDIT / DELETE ROAD ----
        with tab_edit_road:
            road_ids = list(net.roads.keys())
            if not road_ids:
                st.info("No roads available to edit.")
            else:
                sel_rid = st.selectbox(
                    "Select Road",
                    options=road_ids,
                    format_func=lambda rid: (
                        f"{rid}: {net.roads[rid].source_id} -> {net.roads[rid].target_id} "
                        f"(cap {net.roads[rid].capacity:,})"
                    ),
                    key=f"edit_road_sel_{rev}",
                )
                target_road = net.get_road(sel_rid)
                node_ids = list(net.nodes.keys())

                with st.form(f"edit_road_form_{rev}_{sel_rid}"):
                    er_name = st.text_input(
                        "Road Name",
                        value=target_road.name,
                        key=f"edit_road_name_{rev}_{sel_rid}",
                    )
                    ec1, ec2 = st.columns(2)
                    er_src = ec1.selectbox(
                        "From Node",
                        options=node_ids,
                        index=node_ids.index(target_road.source_id),
                        key=f"edit_road_src_{rev}_{sel_rid}",
                    )
                    er_dst = ec2.selectbox(
                        "To Node",
                        options=node_ids,
                        index=node_ids.index(target_road.target_id),
                        key=f"edit_road_dst_{rev}_{sel_rid}",
                    )
                    em1, em2, em3 = st.columns(3)
                    er_cap = int(
                        em1.number_input(
                            "Road Capacity",
                            min_value=0,
                            step=50,
                            value=target_road.capacity,
                            key=f"edit_road_cap_{rev}_{sel_rid}",
                        )
                    )
                    er_dist = float(
                        em2.number_input(
                            "Distance (km)",
                            min_value=0.0,
                            step=0.5,
                            value=float(target_road.distance),
                            key=f"edit_road_dist_{rev}_{sel_rid}",
                        )
                    )
                    er_time = float(
                        em3.number_input(
                            "Travel Time (min)",
                            min_value=0.0,
                            step=1.0,
                            value=float(target_road.travel_time_min),
                            key=f"edit_road_time_{rev}_{sel_rid}",
                        )
                    )
                    er_active = st.checkbox(
                        "Road Operational (Active)",
                        value=target_road.is_active,
                        key=f"edit_road_active_{rev}_{sel_rid}",
                    )

                    if st.form_submit_button("Save Road Changes", type="primary"):
                        try:
                            net.edit_road(
                                sel_rid,
                                source_id=er_src,
                                target_id=er_dst,
                                capacity=er_cap,
                                name=er_name.strip(),
                                distance=er_dist,
                                travel_time_min=er_time,
                                is_active=er_active,
                            )
                        except ResQError as exc:
                            st.error(str(exc))
                        else:
                            invalidate_analysis()
                            set_flash("success", f"Updated road '{sel_rid}'.")
                            st.rerun()

                if st.button(f"Delete Road '{sel_rid}'", key=f"del_road_btn_{rev}_{sel_rid}"):
                    try:
                        net.delete_road(sel_rid)
                    except ResQError as exc:
                        st.error(str(exc))
                    else:
                        invalidate_analysis()
                        set_flash("warning", f"Deleted road '{sel_rid}'.")
                        st.rerun()

        # ---- TAB 5: IMPORT JSON ----
        with tab_import:
            uploaded = st.file_uploader("Upload Network JSON File", type=["json"], key="builder_json_up")
            if uploaded is not None:
                try:
                    imported = import_network_from_json(uploaded.getvalue().decode("utf-8"))
                except (ResQError, UnicodeDecodeError) as exc:
                    st.error(f"Import failed: {exc}")
                else:
                    if st.button("Apply Imported Network", type="primary", key="apply_imported_json"):
                        st.session_state["active_network"] = imported
                        st.session_state["active_preset_key"] = None
                        invalidate_analysis()
                        set_flash("success", f"Imported network '{imported.name}'.")
                        st.rerun()

    with right_col:
        st.markdown(
            '<div class="resq-section-title">Live Topology Preview</div>',
            unsafe_allow_html=True,
        )
        report = net.validate()
        if not report.is_valid:
            st.error("Validation errors: " + " | ".join(report.errors))
        elif report.warnings:
            st.warning("Advisories: " + " | ".join(report.warnings))
        else:
            st.success("Topology valid and ready for Dinic maximum-flow analysis.")

        fig = build_network_figure(net, mode="topology", height=430)
        render_chart(fig, key="builder_live_preview")

        t_nodes, t_roads = st.tabs([f"Nodes ({len(net.nodes)})", f"Roads ({len(net.roads)})"])
        with t_nodes:
            if net.nodes:
                df_n = pd.DataFrame(
                    [
                        {
                            "ID": n.node_id,
                            "Name": n.name,
                            "Type": n.node_type.value,
                            "Population": n.population,
                            "Shelter Cap": n.shelter_capacity,
                        }
                        for n in net.nodes.values()
                    ]
                )
                render_table(df_n, height=240)
            else:
                st.caption("No nodes added yet.")
        with t_roads:
            if net.roads:
                df_r = pd.DataFrame(
                    [
                        {
                            "Road ID": r.road_id,
                            "From": r.source_id,
                            "To": r.target_id,
                            "Capacity": r.capacity,
                            "Distance (km)": round(r.distance, 2),
                            "Active": "Yes" if r.is_active else "Closed",
                        }
                        for r in net.roads.values()
                    ]
                )
                render_table(df_r, height=240)
            else:
                st.caption("No roads connected yet.")
