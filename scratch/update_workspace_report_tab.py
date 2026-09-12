code_to_insert = '''
def _report_nav_item(label: str, icon_name: str, sec_id: str, section_key: str) -> rx.Component:
    is_active = (FacilitatorState.active_report_section == section_key)
    return rx.box(
        rx.hstack(
            rx.icon(
                icon_name,
                size=16,
                color=rx.cond(is_active, COLORS["primary"], COLORS["slate"]),
            ),
            rx.text(
                label,
                font_family=FONT_BODY,
                size="2",
                weight=rx.cond(is_active, "bold", "medium"),
                color=rx.cond(is_active, COLORS["primary"], "#334155"),
            ),
            spacing="3",
            align_items="center",
            width="100%",
        ),
        padding="0.65em 0.9em",
        border_radius="8px",
        background=rx.cond(is_active, "#F3E8FF", "transparent"),
        cursor="pointer",
        transition="all 0.15s ease",
        _hover={"background": rx.cond(is_active, "#F3E8FF", "#F8FAFC")},
        on_click=[
            FacilitatorState.set_active_report_section(section_key),
            rx.call_script(f"const el = document.getElementById('{sec_id}'); if (el) el.scrollIntoView({{behavior: 'smooth', block: 'start'}});"),
        ],
        width="100%",
    )


def _report_doc_section_banner(icon_name: str, title: str, sec_id: str) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon(icon_name, size=15, color="#4F46E5"),
            rx.text(title, font_family=FONT_BODY, size="2", weight="bold", color="#1E293B"),
            spacing="2",
            align_items="center",
        ),
        id=sec_id,
        background="#EEF2FF",
        border="1px solid #E0E7FF",
        border_radius="6px",
        padding="0.5em 0.85em",
        width="100%",
        margin_top="1.8em",
        margin_bottom="0.8em",
    )


def _report_candidate_status_pill(status: str) -> rx.Component:
    return rx.match(
        status,
        ("Passed", rx.box(rx.text("Passed", font_family=FONT_BODY, size="1", weight="bold", color="#03543F"), background="#DEF7EC", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Failed", rx.box(rx.text("Failed", font_family=FONT_BODY, size="1", weight="bold", color="#9B1C1C"), background="#FDE8E8", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        rx.box(rx.text("Pending", font_family=FONT_BODY, size="1", weight="bold", color="#854D0E"), background="#FEF08A", border_radius="12px", padding="0.2em 0.8em", display="inline-flex"),
    )


def _report_difficulty_pill(diff: str) -> rx.Component:
    return rx.match(
        diff,
        ("Easy", rx.box(rx.text("Easy", font_family=FONT_BODY, size="1", weight="bold", color="#03543F"), background="#DEF7EC", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Medium", rx.box(rx.text("Medium", font_family=FONT_BODY, size="1", weight="bold", color="#92400E"), background="#FEF3C7", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        ("Hard", rx.box(rx.text("Hard", font_family=FONT_BODY, size="1", weight="bold", color="#9B1C1C"), background="#FDE8E8", border_radius="12px", padding="0.2em 0.8em", display="inline-flex")),
        rx.text(diff, font_family=FONT_BODY, size="2", color="#475467"),
    )


def _pdf_viewer_toolbar() -> rx.Component:
    return rx.hstack(
        # Page indicator
        rx.box(
            rx.text("1 / 6", font_family=FONT_BODY, size="1", weight="medium", color="#E2E8F0"),
            background="#1E2024",
            padding="0.2em 0.6em",
            border_radius="4px",
        ),
        rx.box(width="1px", height="16px", background="#475569", margin_x="0.6em"),
        # Zoom controls
        rx.icon("minus", size=14, color="#CBD5E1", cursor="pointer"),
        rx.text("100%", font_family=FONT_BODY, size="1", color="#CBD5E1", margin_x="0.5em"),
        rx.icon("plus", size=14, color="#CBD5E1", cursor="pointer"),
        rx.box(width="1px", height="16px", background="#475569", margin_x="0.6em"),
        rx.icon("expand", size=14, color="#CBD5E1", cursor="pointer"),
        rx.icon("rotate-cw", size=14, color="#CBD5E1", cursor="pointer", margin_left="0.4em"),
        rx.spacer(),
        # Action icons
        rx.icon(
            "download",
            size=15,
            color="#CBD5E1",
            cursor="pointer",
            on_click=FacilitatorState.download_report_action(""),
        ),
        rx.icon(
            "printer",
            size=15,
            color="#CBD5E1",
            cursor="pointer",
            margin_left="0.8em",
            on_click=rx.call_script("window.print()"),
        ),
        rx.icon("ellipsis-vertical", size=15, color="#CBD5E1", cursor="pointer", margin_left="0.8em"),
        background="#252830",
        padding="0.6em 1.2em",
        border_radius="10px 10px 0 0",
        width="100%",
        align_items="center",
    )


def report_detail_tab() -> rx.Component:
    """Detailed report page matching reference design — driven entirely by real state data."""
    stats = FacilitatorState.report_summary_stats
    meta = FacilitatorState.report_metadata

    return rx.vstack(
        # ── 1. Top Bar: Back to Reports link ───────────────────────────────────
        rx.hstack(
            rx.button(
                rx.icon("arrow-left", size=14),
                "Back to Reports",
                on_click=FacilitatorState.back_to_reports,
                variant="ghost",
                color=COLORS["primary"],
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                cursor="pointer",
                _hover={"background": COLORS["primary_soft"]},
                border_radius="8px",
                padding_x="0.5em",
                padding_y="0.3em",
            ),
            width="100%",
            align_items="center",
            margin_bottom="0.4em",
        ),

        # ── 2. Header Row: Title, badge, subtitle, and Print/Download buttons ──
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.text(
                        FacilitatorState.selected_report_test_name,
                        " Report",
                        font_family=FONT_DISPLAY,
                        size="6",
                        weight="bold",
                        color="#0F172A",
                    ),
                    rx.badge(
                        meta["badge"],
                        color_scheme=meta["badge_scheme"],
                        variant="soft",
                        size="2",
                        border_radius="12px",
                        padding_x="0.7em",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.text(
                    "Detailed performance report for ",
                    FacilitatorState.selected_report_test_name,
                    ".",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),
                spacing="1",
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("printer", size=14),
                    "Print",
                    variant="outline",
                    color="#1E293B",
                    font_family=FONT_BODY,
                    size="2",
                    weight="medium",
                    border="1px solid #CBD5E1",
                    background="white",
                    border_radius="8px",
                    cursor="pointer",
                    padding_x="1em",
                    _hover={"background": "#F8FAFC", "border_color": "#94A3B8"},
                    on_click=rx.call_script("window.print()"),
                ),
                rx.button(
                    rx.icon("download", size=14),
                    "Download PDF",
                    background=COLORS["primary"],
                    color="white",
                    font_family=FONT_BODY,
                    size="2",
                    weight="medium",
                    border_radius="8px",
                    cursor="pointer",
                    padding_x="1.2em",
                    _hover={"background": COLORS["primary_hover"]},
                    on_click=[
                        FacilitatorState.download_report_action(""),
                        rx.call_script("window.print()"),
                    ],
                ),
                spacing="3",
                align_items="center",
            ),
            width="100%",
            align_items="center",
            margin_bottom="1.5em",
        ),

        # ── 3. Main Split View: Left Navigation + Right PDF Viewer ─────────────
        rx.hstack(
            # ── Left Navigation Sidebar Card ──────────────────────────────────
            rx.box(
                rx.vstack(
                    _report_nav_item("Report Summary", "file-text", "sec-summary", "summary"),
                    _report_nav_item("Candidate Performance", "users", "sec-candidates", "candidates"),
                    _report_nav_item("Question-wise Analysis", "square-check", "sec-questions", "questions"),
                    _report_nav_item("Pass/Fail Summary", "circle-check", "sec-passfail", "passfail"),
                    _report_nav_item("Remarks", "message-square", "sec-remarks", "remarks"),
                    spacing="1",
                    width="100%",
                    align_items="stretch",
                ),
                background="white",
                border="1px solid #E2E8F0",
                border_radius="12px",
                padding="1em 0.8em",
                width="240px",
                min_width="240px",
                box_shadow="0 1px 3px rgba(0,0,0,0.04)",
            ),

            # ── Right PDF Viewer Card ─────────────────────────────────────────
            rx.box(
                rx.vstack(
                    # PDF Toolbar
                    _pdf_viewer_toolbar(),

                    # PDF Document Scroll Area
                    rx.box(
                        # Document Page Sheet
                        rx.box(
                            rx.vstack(
                                # TVS Document Header
                                rx.hstack(
                                    rx.image(
                                        src="/tvs_logo.png",
                                        height="34px",
                                        width="auto",
                                        object_fit="contain",
                                    ),
                                    rx.spacer(),
                                    rx.text(
                                        "GEN AI HYBRID EVALUATOR",
                                        font_family=FONT_BODY,
                                        size="3",
                                        weight="bold",
                                        color="#1E293B",
                                        letter_spacing="0.04em",
                                    ),
                                    rx.spacer(),
                                    rx.text(
                                        "Assessment Report",
                                        font_family=FONT_BODY,
                                        size="3",
                                        weight="bold",
                                        color="#1E293B",
                                    ),
                                    width="100%",
                                    align_items="center",
                                ),
                                rx.box(width="100%", height="1px", background="#E2E8F0", margin_y="1.2em"),

                                # Report Metadata Header
                                rx.hstack(
                                    rx.vstack(
                                        rx.text(
                                            FacilitatorState.selected_report_test_name,
                                            " Report",
                                            font_family=FONT_DISPLAY,
                                            size="6",
                                            weight="bold",
                                            color="#0F172A",
                                        ),
                                        rx.text(
                                            FacilitatorState.selected_assessment_name,
                                            " Assessment",
                                            font_family=FONT_BODY,
                                            size="2",
                                            weight="bold",
                                            color="#334155",
                                        ),
                                        rx.text(
                                            "Assessment Type: ",
                                            meta["badge"],
                                            font_family=FONT_BODY,
                                            size="2",
                                            color="#64748B",
                                        ),
                                        spacing="1",
                                        align_items="start",
                                    ),
                                    rx.spacer(),
                                    rx.vstack(
                                        rx.hstack(
                                            rx.text("Test Date", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["test_date"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.hstack(
                                            rx.text("Generated On", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["generated_on"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.hstack(
                                            rx.text("Generated By", width="105px", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(":", font_family=FONT_BODY, size="1", color="#64748B"),
                                            rx.text(meta["generated_by"], font_family=FONT_BODY, size="1", color="#0F172A", weight="medium"),
                                            spacing="1", align_items="center",
                                        ),
                                        spacing="1",
                                        align_items="start",
                                    ),
                                    width="100%",
                                    align_items="start",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 1: Assessment Summary ──────────────
                                _report_doc_section_banner("file-text", "Assessment Summary", "sec-summary"),
                                rx.box(
                                    rx.hstack(
                                        # Left column
                                        rx.vstack(
                                            rx.hstack(
                                                rx.text("Total Candidates", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["total"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Evaluated", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["evaluated"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Pending", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["pending"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            spacing="3",
                                            flex="1",
                                            align_items="stretch",
                                        ),
                                        # Divider
                                        rx.box(width="1px", background="#E2E8F0", margin_x="2em", align_self="stretch"),
                                        # Right column
                                        rx.vstack(
                                            rx.hstack(
                                                rx.text("Pass Percentage (Set by Facilitator)", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["pass_pct"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Candidates Passed", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["passed"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            rx.hstack(
                                                rx.text("Candidates Failed", font_family=FONT_BODY, size="2", color="#475467"),
                                                rx.spacer(),
                                                rx.text(stats["failed"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A"),
                                                width="100%",
                                            ),
                                            spacing="3",
                                            flex="1",
                                            align_items="stretch",
                                        ),
                                        width="100%",
                                        align_items="start",
                                    ),
                                    background="#F8FAFC",
                                    border="1px solid #E2E8F0",
                                    border_radius="6px",
                                    padding="1.2em 1.5em",
                                    width="100%",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 2: Candidate Performance ───────────
                                _report_doc_section_banner("users", "Candidate Performance", "sec-candidates"),
                                rx.cond(
                                    FacilitatorState.report_candidate_rows.length() == 0,
                                    rx.box(
                                        rx.text("No candidates assigned to this assessment.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                        padding="1em",
                                    ),
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell(rx.text("#", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Candidate ID", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Candidate Name", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Normalized Score (%)", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Status", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                            ),
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                FacilitatorState.report_candidate_rows,
                                                lambda row: rx.table.row(
                                                    rx.table.cell(rx.text(row["idx"], font_family=FONT_BODY, size="2", color="#64748B")),
                                                    rx.table.cell(rx.text(row["cand_id"], font_family=FONT_BODY, size="2", color="#334155")),
                                                    rx.table.cell(rx.text(row["cand_name"], font_family=FONT_BODY, size="2", color="#0F172A", weight="medium")),
                                                    rx.table.cell(rx.text(row["score_str"], font_family=FONT_BODY, size="2", color="#0F172A", weight="bold")),
                                                    rx.table.cell(_report_candidate_status_pill(row["status"])),
                                                ),
                                            ),
                                        ),
                                        width="100%",
                                        variant="surface",
                                        margin_bottom="1.2em",
                                    ),
                                ),

                                # ── Section 3: Question-wise Analysis ──────────
                                _report_doc_section_banner("square-check", "Question-wise Analysis", "sec-questions"),
                                rx.cond(
                                    FacilitatorState.report_question_rows.length() == 0,
                                    rx.box(
                                        rx.hstack(
                                            rx.icon("info", size=16, color="#64748B"),
                                            rx.text(
                                                "No question-wise data available yet. Please complete AI or manual evaluation for this test.",
                                                font_family=FONT_BODY, size="2", color=COLORS["slate"],
                                            ),
                                            spacing="2", align_items="center",
                                        ),
                                        background="#F8FAFC",
                                        border="1px solid #E2E8F0",
                                        border_radius="6px",
                                        padding="1em 1.2em",
                                        margin_bottom="1.2em",
                                        width="100%",
                                    ),
                                    rx.table.root(
                                        rx.table.header(
                                            rx.table.row(
                                                rx.table.column_header_cell(rx.text("Q. No.", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Question", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Max Marks", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Average Score", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                                rx.table.column_header_cell(rx.text("Difficulty", font_family=FONT_BODY, size="2", weight="bold", color="#64748B")),
                                            ),
                                        ),
                                        rx.table.body(
                                            rx.foreach(
                                                FacilitatorState.report_question_rows,
                                                lambda row: rx.table.row(
                                                    rx.table.cell(rx.text(row["qno"], font_family=FONT_BODY, size="2", color="#64748B")),
                                                    rx.table.cell(rx.text(row["question"], font_family=FONT_BODY, size="2", color="#0F172A"), min_width="220px"),
                                                    rx.table.cell(rx.text(row["max_marks"], font_family=FONT_BODY, size="2", color="#334155")),
                                                    rx.table.cell(rx.text(row["avg_score"], font_family=FONT_BODY, size="2", weight="bold", color="#0F172A")),
                                                    rx.table.cell(_report_difficulty_pill(row["difficulty"])),
                                                ),
                                            ),
                                        ),
                                        width="100%",
                                        variant="surface",
                                        margin_bottom="1.2em",
                                    ),
                                ),

                                # ── Section 4: Pass / Fail Summary ─────────────
                                _report_doc_section_banner("circle-check", "Pass/Fail Summary", "sec-passfail"),
                                rx.box(
                                    rx.hstack(
                                        rx.vstack(
                                            rx.text("Passed", font_family=FONT_BODY, size="2", color="#059669", weight="medium"),
                                            rx.text(stats["passed"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#059669"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.vstack(
                                            rx.text("Failed", font_family=FONT_BODY, size="2", color="#DC2626", weight="medium"),
                                            rx.text(stats["failed"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#DC2626"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        rx.vstack(
                                            rx.text("Pending", font_family=FONT_BODY, size="2", color="#D97706", weight="medium"),
                                            rx.text(stats["pending"], font_family=FONT_DISPLAY, size="7", weight="bold", color="#D97706"),
                                            rx.text("candidates", font_family=FONT_BODY, size="1", color="#64748B"),
                                            spacing="1", align_items="center",
                                        ),
                                        spacing="8",
                                        justify="center",
                                        width="100%",
                                    ),
                                    background="#F8FAFC",
                                    border="1px solid #E2E8F0",
                                    border_radius="6px",
                                    padding="1.5em",
                                    width="100%",
                                    margin_bottom="1.2em",
                                ),

                                # ── Section 5: Remarks ─────────────────────────
                                _report_doc_section_banner("message-square", "Remarks", "sec-remarks"),
                                rx.cond(
                                    FacilitatorState.report_remarks_rows.length() == 0,
                                    rx.box(
                                        rx.text("No remarks available yet. Remarks are populated from evaluation feedback.", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                                        padding="1em",
                                    ),
                                    rx.vstack(
                                        rx.foreach(
                                            FacilitatorState.report_remarks_rows,
                                            lambda row: rx.box(
                                                rx.vstack(
                                                    rx.text(row["candidate"], font_family=FONT_BODY, size="2", weight="bold", color=COLORS["ink"]),
                                                    rx.text(row["remarks"], font_family=FONT_BODY, size="2", color="#475467", line_height="1.6"),
                                                    spacing="1",
                                                    align_items="start",
                                                ),
                                                background="#F8FAFC",
                                                border="1px solid #E2E8F0",
                                                border_left=f"3px solid {COLORS['primary']}",
                                                border_radius="6px",
                                                padding="0.9em 1.2em",
                                                width="100%",
                                            ),
                                        ),
                                        spacing="3",
                                        width="100%",
                                    ),
                                ),

                                spacing="0",
                                width="100%",
                                align_items="stretch",
                            ),
                            background="white",
                            border_radius="4px",
                            box_shadow="0 6px 24px rgba(0,0,0,0.3)",
                            padding="3em 3.5em",
                            max_width="860px",
                            margin="0 auto",
                            width="100%",
                        ),
                        background="#383C45",
                        padding="2em 1.5em",
                        border_radius="0 0 10px 10px",
                        max_height="calc(100vh - 210px)",
                        overflow_y="auto",
                        width="100%",
                    ),

                    spacing="0",
                    width="100%",
                    align_items="stretch",
                ),
                flex="1",
                min_width="0",
                border_radius="10px",
                border="1px solid #334155",
                overflow="hidden",
                box_shadow="0 4px 12px rgba(0,0,0,0.12)",
            ),

            spacing="5",
            width="100%",
            align_items="start",
        ),

        spacing="0",
        width="100%",
        align_items="stretch",
    )
'''

with open("ai_hybrid_evaluator/pages/facilitator/assessment_workspace.py", "r", encoding="utf-8") as f:
    content = f.read()

start_marker = "# Report Detail Tab  (opened via \"View Report\" from the Reports tab)\n# ──────────────────────────────────────────────────────────────────────────────"
end_marker = "def assessment_workspace_page() -> rx.Component:"

idx_start = content.find(start_marker)
idx_end = content.find(end_marker)

if idx_start == -1 or idx_end == -1:
    print(f"Error: start={idx_start}, end={idx_end}")
else:
    new_content = content[:idx_start + len(start_marker)] + "\n" + code_to_insert + "\n\n" + content[idx_end:]
    with open("ai_hybrid_evaluator/pages/facilitator/assessment_workspace.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Successfully updated assessment_workspace.py!")
