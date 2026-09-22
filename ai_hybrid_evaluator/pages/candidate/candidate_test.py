"""
Candidate Test Environment — Full-screen assessment interface matching the reference UI.
Layout features:
  - Header: Exit Full Screen (left), "Quality - Test 1" + "3 of 20" (center), Timer box + Submit Test (right)
  - Red Proctoring Alert Banner with "Monitoring Active" green indicator
  - Two-Column Body:
      - Left: Question Card (Title, Question text, Guidelines bullets, Previous / Next buttons)
      - Right: Answer Card (Your Answer + Auto-saved + Word count, formatting toolbar, clean textarea)
  - Bottom Status Bar: Fullscreen & Tab Lock notice (left), Mic Active, Camera Active, Tab Locked (right)
"""

import reflex as rx
from ai_hybrid_evaluator.state.auth_state import AuthState
from ai_hybrid_evaluator.state.candidate_state import CandidateState
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────────────────────
# Header Component — 3-Column Grid for exact center alignment & corner TVS logo
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Header Component — 3-Column Grid for exact center alignment & corner TVS logo
# ─────────────────────────────────────────────────────────────────────────────

def test_header() -> rx.Component:
    return rx.box(
        rx.box(
            # Column 1 (Left): TVS Logo + Fullscreen Active / Exit Full Screen
            rx.hstack(
                rx.image(
                    src="/tvs_logo.png",
                    height="36px",
                    width="auto",
                    max_width="70px",
                    object_fit="contain",
                ),
                rx.box(width="1px", height="26px", background="#E5E7EB", margin_x="0.5em"),
                rx.cond(
                    CandidateState.is_fullscreen,
                    rx.hstack(
                        rx.box(
                            width="8px",
                            height="8px",
                            border_radius="50%",
                            background="#16A34A",
                        ),
                        rx.text(
                            "Fullscreen Active",
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color="#16A34A",
                        ),
                        rx.box(width="1px", height="16px", background="#E5E7EB", margin_x="0.4em"),
                        rx.hstack(
                            rx.icon("minimize", size=14, color="#6B7280"),
                            rx.text(
                                "Exit Full Screen",
                                font_family=FONT_BODY,
                                size="2",
                                weight="medium",
                                color="#6B7280",
                            ),
                            spacing="1",
                            align_items="center",
                            cursor="pointer",
                            on_click=CandidateState.exit_fullscreen,
                            _hover={"color": "#111827"},
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    rx.hstack(
                        rx.icon("maximize", size=16, color="#DC2626"),
                        rx.text(
                            "Enter Fullscreen",
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color="#DC2626",
                        ),
                        spacing="2",
                        align_items="center",
                        cursor="pointer",
                        on_click=[
                            CandidateState.handle_fullscreen_entered,
                            rx.call_script("if (!document.fullscreenElement) { (document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen || function(){}).call(document.documentElement).catch(function(e){console.warn(e);}); }"),
                        ],
                    ),
                ),
                spacing="2",
                align_items="center",
                justify_self="start",
            ),

            # Column 2 (Center): Quality - Test 1 & 3 of 20
            rx.vstack(
                rx.text(
                    CandidateState.active_assessment_name + " - " + CandidateState.display_test_name,
                    font_family=FONT_DISPLAY,
                    size="4",
                    weight="bold",
                    color="#111827",
                ),
                rx.box(
                    rx.text(
                        CandidateState.current_question_number.to_string() + " of " + CandidateState.total_questions.to_string(),
                        font_family=FONT_BODY,
                        size="1",
                        weight="medium",
                        color="#6B7280",
                    ),
                    background="#F3F4F6",
                    padding="0.15em 0.8em",
                    border_radius="999px",
                ),
                spacing="1",
                align_items="center",
                justify_self="center",
            ),

            # Column 3 (Right): Timer Box + Submit Test Button
            rx.hstack(
                # Timer box
                rx.box(
                    rx.hstack(
                        rx.icon(
                            "clock",
                            size=18,
                            color=rx.cond(CandidateState.is_time_expired, "#DC2626", "#4B5563"),
                        ),
                        rx.vstack(
                            rx.text(
                                rx.cond(CandidateState.is_time_expired, "Time Expired", "Time Remaining"),
                                font_family=FONT_BODY,
                                size="1",
                                color=rx.cond(CandidateState.is_time_expired, "#DC2626", "#6B7280"),
                            ),
                            rx.text(
                                CandidateState.time_display,
                                font_family="monospace",
                                size="3",
                                weight="bold",
                                color=rx.cond(CandidateState.is_time_expired, "#DC2626", "#111827"),
                            ),
                            spacing="0",
                            align_items="start",
                        ),
                        spacing="2",
                        align_items="center",
                    ),
                    border=rx.cond(CandidateState.is_time_expired, "1px solid #FDA29B", "1px solid #E5E7EB"),
                    border_radius="8px",
                    padding="0.35em 0.9em",
                    background=rx.cond(CandidateState.is_time_expired, "#FEF2F2", "white"),
                ),

                # Submit Test button
                rx.button(
                    "Submit Test",
                    on_click=CandidateState.open_submit_dialog,
                    disabled=CandidateState.is_test_submitted | CandidateState.is_time_expired,
                    size="2",
                    background="#4338CA",
                    color="white",
                    font_family=FONT_BODY,
                    font_weight="medium",
                    padding="0.6em 1.4em",
                    border_radius="8px",
                    _hover={"background": "#3730A3"},
                ),
                spacing="3",
                align_items="center",
                justify_self="end",
            ),

            display="grid",
            grid_template_columns="1fr auto 1fr",
            width="100%",
            align_items="center",
        ),
        padding="0.85em 2.5em",
        background="white",
        border_bottom="1px solid #E5E7EB",
        position="sticky",
        top="0",
        z_index="40",
        width="100%",
    )




# ─────────────────────────────────────────────────────────────────────────────
# Left Column: Question Card
# ─────────────────────────────────────────────────────────────────────────────

def _meta_pill(label: str, value: str) -> rx.Component:
    """Small metadata pill shown on the Question Card (CO, LO, RBT Level, Max Marks)."""
    return rx.hstack(
        rx.text(
            label + ":",
            font_family=FONT_BODY,
            size="1",
            weight="bold",
            color="#6B7280",
        ),
        rx.text(
            rx.cond(value != "", value, "—"),
            font_family=FONT_BODY,
            size="1",
            color="#111827",
        ),
        spacing="1",
        align_items="center",
        background="#F3F4F6",
        border_radius="6px",
        padding="0.2em 0.6em",
    )


def question_card() -> rx.Component:
    q = CandidateState.current_question

    return rx.box(
        rx.vstack(
            # Top Section: Header + Text + Guidelines
            rx.vstack(
                # Card Top Row: Question Number + Mark for Review
                rx.hstack(
                    rx.text(
                        "Question " + CandidateState.current_question_number.to_string(),
                        font_family=FONT_DISPLAY,
                        size="5",
                        weight="bold",
                        color="#111827",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.icon(
                            "bookmark",
                            size=16,
                            color=rx.cond(CandidateState.is_current_marked, "#D97706", "#4B5563"),
                        ),
                        rx.text(
                            rx.cond(
                                CandidateState.is_current_marked,
                                "Marked for Review",
                                "Mark for Review",
                            ),
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color=rx.cond(CandidateState.is_current_marked, "#D97706", "#4B5563"),
                        ),
                        spacing="1",
                        align_items="center",
                        cursor="pointer",
                        on_click=CandidateState.toggle_mark_for_review,
                    ),
                    width="100%",
                    align_items="center",
                ),

                # Metadata row: CO / LO / RBT Level / Marks / Question Type
                rx.hstack(
                    _meta_pill("CO", CandidateState.current_question_co),
                    _meta_pill("LO", CandidateState.current_question_lo),
                    _meta_pill("RBT Level", CandidateState.current_question_rbt),
                    _meta_pill("Max Marks", CandidateState.current_question_marks),
                    rx.cond(
                        CandidateState.current_question_type == "Objective",
                        rx.box(
                            rx.text("Objective", font_family=FONT_BODY, size="1", weight="bold", color="#4338CA"),
                            background="#EEF2FF",
                            border="1px solid #C7D2FE",
                            border_radius="6px",
                            padding="0.2em 0.7em",
                        ),
                        rx.box(
                            rx.text("Subjective", font_family=FONT_BODY, size="1", weight="bold", color="#027A48"),
                            background="#ECFDF5",
                            border="1px solid #A7F3D0",
                            border_radius="6px",
                            padding="0.2em 0.7em",
                        ),
                    ),
                    spacing="2",
                    padding_top="0.8em",
                    flex_wrap="wrap",
                ),

                # Question prompt
                rx.text(
                    q["text"],
                    font_family=FONT_BODY,
                    size="3",
                    color="#1F2937",
                    line_height="1.65",
                    padding_top="1.2em",
                ),

                # Guidelines Heading + Bullet Points (Subjective only)
                rx.cond(
                    CandidateState.current_question_type == "Subjective",
                    rx.vstack(
                        rx.text(
                            "Guidelines:",
                            font_family=FONT_BODY,
                            size="2",
                            weight="bold",
                            color="#111827",
                            padding_top="1.4em",
                        ),
                        rx.vstack(
                            rx.hstack(
                                rx.text("•", size="3", color="#4B5563"),
                                rx.text("Your answer should be structured and clear.", font_family=FONT_BODY, size="2", color="#4B5563"),
                                spacing="2",
                                align_items="start",
                            ),
                            rx.hstack(
                                rx.text("•", size="3", color="#4B5563"),
                                rx.text("Support your points with relevant examples.", font_family=FONT_BODY, size="2", color="#4B5563"),
                                spacing="2",
                                align_items="start",
                            ),
                            rx.hstack(
                                rx.text("•", size="3", color="#4B5563"),
                                rx.text("Write in your own words.", font_family=FONT_BODY, size="2", color="#4B5563"),
                                spacing="2",
                                align_items="start",
                            ),
                            spacing="1",
                            padding_top="0.3em",
                            align_items="start",
                        ),
                        spacing="0",
                        align_items="start",
                        width="100%",
                    ),
                    rx.fragment(),
                ),

                spacing="0",
                align_items="start",
                width="100%",
            ),

            rx.spacer(),

            # Bottom Navigation Buttons: Previous | Next (skip) | Save & Next / Save & Submit
            _test_bottom_nav_buttons(),

            spacing="0",
            width="100%",
            height="100%",
            justify_content="space-between",
        ),
        background="white",
        border="1px solid #E5E7EB",
        border_radius="12px",
        padding="2em",
        width="50%",
        min_height="580px",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.05)",
    )


def _test_bottom_nav_buttons() -> rx.Component:
    return rx.hstack(
        # Previous
        rx.button(
            rx.hstack(
                rx.icon("arrow-left", size=14),
                rx.text("Previous", font_family=FONT_BODY, size="2", weight="medium"),
                spacing="1",
                align_items="center",
            ),
            on_click=[
                rx.call_script("if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();"),
                CandidateState.prev_question,
            ],
            disabled=CandidateState.current_question_index == 0,
            variant="outline",
            color_scheme="gray",
            size="2",
            border="1px solid #D1D5DB",
            border_radius="8px",
            padding="0.5em 1.2em",
            background="white",
        ),
        rx.spacer(),
        # Next → (skip, only visible when not on last question)
        rx.cond(
            ~CandidateState.is_last_question,
            rx.button(
                rx.hstack(
                    rx.text("Next", font_family=FONT_BODY, size="2", weight="medium"),
                    rx.icon("arrow-right", size=14),
                    spacing="1",
                    align_items="center",
                ),
                on_click=[
                    rx.call_script("if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();"),
                    CandidateState.next_question,
                ],
                size="2",
                variant="outline",
                color_scheme="gray",
                border="1px solid #D1D5DB",
                border_radius="8px",
                padding="0.5em 1.2em",
                background="white",
            ),
            rx.fragment(),
        ),
        # Save & Next (saves answer + advance) — only on non-last questions
        # Save & Submit — on the final question
        rx.cond(
            CandidateState.is_last_question,
            rx.button(
                rx.hstack(
                    rx.text("Save & Submit", font_family=FONT_BODY, size="2", weight="medium"),
                    rx.icon("send", size=14),
                    spacing="1",
                    align_items="center",
                ),
                on_click=[
                    rx.call_script("if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();"),
                    CandidateState.save_and_next_question,
                    CandidateState.open_submit_dialog,
                ],
                size="2",
                background="#027A48",
                color="white",
                border_radius="8px",
                padding="0.5em 1.5em",
                _hover={"background": "#05603A"},
            ),
            rx.button(
                rx.hstack(
                    rx.text("Save & Next", font_family=FONT_BODY, size="2", weight="medium"),
                    rx.icon("arrow-right", size=14),
                    spacing="1",
                    align_items="center",
                ),
                on_click=[
                    rx.call_script("if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();"),
                    CandidateState.save_and_next_question,
                ],
                size="2",
                background="#4338CA",
                color="white",
                border_radius="8px",
                padding="0.5em 1.5em",
                _hover={"background": "#3730A3"},
            ),
        ),
        width="100%",
        align_items="center",
        padding_top="1.5em",
        spacing="2",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Right Column: Answer Editor Card
# ─────────────────────────────────────────────────────────────────────────────

# ── Rich-Text Editor JS helpers ──────────────────────────────────────────────
# Runs execCommand on the contenteditable editor, then syncs the updated HTML
# back to the backend state and localStorage, and updates live word count.
_EXEC_CMD_JS = """
(function(cmd, arg) {
    var ed = document.getElementById('rte-editor');
    if (!ed) return;
    ed.focus();
    document.execCommand(cmd, false, arg || null);
    if (window.__updateWordCount) window.__updateWordCount(ed.innerHTML);
    if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();
})('{cmd}', {arg});
"""


def _exec_cmd(cmd: str, arg: str = "null") -> rx.event.EventSpec:
    """Return a call_script that fires document.execCommand and syncs state."""
    js = _EXEC_CMD_JS.replace("'{cmd}'", f"'{cmd}'").replace("{arg}", arg)
    return rx.call_script(js)


def _toolbar_btn(icon_name: str, cmd: str, arg: str = "null") -> rx.Component:
    """A toolbar icon button that fires execCommand on the rich-text editor."""
    return rx.icon_button(
        rx.icon(icon_name, size=15),
        size="1",
        variant="ghost",
        color_scheme="gray",
        cursor="pointer",
        on_click=_exec_cmd(cmd, arg),
    )


def answer_card() -> rx.Component:
    return rx.box(
        # ── Hidden relay textarea: bridges the contenteditable -> Reflex state ──
        # Uses textarea (not type="hidden" input) so React synthetic onChange fires correctly.
        rx.el.textarea(
            id="rte-relay",
            on_change=CandidateState.set_answer_html,
            style={
                "position": "fixed",
                "top": "-9999px",
                "left": "-9999px",
                "width": "1px",
                "height": "1px",
                "opacity": "0",
                "pointerEvents": "none",
                "zIndex": "-1",
            },
        ),

        rx.vstack(
            # Top Header Row: Your Answer + Auto-save status badge + Word count
            rx.hstack(
                rx.text(
                    "Your Answer",
                    font_family=FONT_DISPLAY,
                    size="4",
                    weight="bold",
                    color="#111827",
                ),
                # Dynamic auto-save status badge
                rx.cond(
                    CandidateState.auto_save_status == "Saving...",
                    rx.hstack(
                        rx.icon("loader", size=14, color="#D97706"),
                        rx.text("Saving...", font_family=FONT_BODY, size="1", weight="medium", color="#D97706"),
                        spacing="1",
                        align_items="center",
                    ),
                    rx.cond(
                        CandidateState.auto_save_status == "Save failed",
                        rx.hstack(
                            rx.icon("circle-x", size=14, color="#DC2626"),
                            rx.text("Save failed", font_family=FONT_BODY, size="1", weight="medium", color="#DC2626"),
                            spacing="1",
                            align_items="center",
                        ),
                        rx.cond(
                            CandidateState.auto_save_status == "Auto-saved",
                            rx.hstack(
                                rx.icon("circle-check", size=14, color="#16A34A"),
                                rx.text("Auto-saved", font_family=FONT_BODY, size="1", weight="medium", color="#16A34A"),
                                spacing="1",
                                align_items="center",
                            ),
                            rx.fragment(),
                        ),
                    ),
                ),
                rx.spacer(),
                rx.text(
                    "Words: " + CandidateState.current_word_count.to_string(),
                    id="rte-word-count",
                    font_family=FONT_BODY,
                    size="1",
                    color="#6B7280",
                ),
                width="100%",
                align_items="center",
            ),

            # ── Formatting Toolbar ────────────────────────────────────────
            rx.hstack(
                # Undo / Redo
                _toolbar_btn("undo-2",        "undo"),
                _toolbar_btn("redo-2",        "redo"),
                rx.box(width="1px", height="16px", background="#E5E7EB", margin="0 0.3em"),
                # Inline formatting
                _toolbar_btn("bold",          "bold"),
                _toolbar_btn("italic",        "italic"),
                _toolbar_btn("underline",     "underline"),
                rx.box(width="1px", height="16px", background="#E5E7EB", margin="0 0.3em"),
                # Lists
                _toolbar_btn("list",          "insertUnorderedList"),
                _toolbar_btn("list-ordered",  "insertOrderedList"),
                rx.box(width="1px", height="16px", background="#E5E7EB", margin="0 0.3em"),
                # Alignment
                _toolbar_btn("align-left",    "justifyLeft"),
                _toolbar_btn("align-center",  "justifyCenter"),
                _toolbar_btn("align-right",   "justifyRight"),
                rx.box(width="1px", height="16px", background="#E5E7EB", margin="0 0.3em"),
                _toolbar_btn("align-justify", "justifyFull"),
                _toolbar_btn("strikethrough", "strikeThrough"),
                spacing="1",
                align_items="center",
                padding="0.45em 0.8em",
                border="1px solid #E5E7EB",
                border_radius="8px 8px 0 0",
                border_bottom="none",
                background="#FAFAFA",
                width="100%",
                margin_top="1.2em",
            ),


            # ── Rich-Text Editor (contenteditable div) ────────────────────
            rx.box(
                rx.script(
                    """
                    (function() {
                        function initRTE() {
                            var ed = document.getElementById('rte-editor');
                            var relay = document.getElementById('rte-relay');
                            if (!ed || !relay) { setTimeout(initRTE, 80); return; }
                            if (window.bindRteInput) {
                                window.bindRteInput(ed);
                            }
                            if (window.__updateWordCount) {
                                window.__updateWordCount(ed.innerHTML);
                            }
                        }
                        initRTE();
                    })();
                    """
                ),
                id="rte-editor",
                content_editable=rx.cond(
                    CandidateState.is_test_submitted | CandidateState.is_time_expired,
                    "false",
                    "true",
                ),
                min_height="440px",
                width="100%",
                font_family=FONT_BODY,
                font_size="var(--font-size-3)",
                line_height="1.7",
                padding="1.2em",
                border="1px solid #E5E7EB",
                border_radius="0 0 8px 8px",
                background=rx.cond(
                    CandidateState.is_test_submitted | CandidateState.is_time_expired,
                    "#F9FAFB",
                    "white",
                ),
                overflow_y="auto",
                outline="none",
                _focus={"border_color": "#4338CA", "box_shadow": "0 0 0 2px rgba(67,56,202,0.12)"},
                white_space="pre-wrap",
                word_break="break-word",
            ),

            spacing="0",
            width="100%",
            height="100%",
        ),
        background="white",
        border="1px solid #E5E7EB",
        border_radius="12px",
        padding="2em",
        width="50%",
        min_height="580px",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.05)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Right Column: MCQ (Objective) Answer Card
# ─────────────────────────────────────────────────────────────────────────────

def _mcq_option_card(letter: str, text_var: rx.Var) -> rx.Component:
    is_selected = CandidateState.current_mcq_answer == letter
    return rx.cond(
        text_var != "",
        rx.box(
            rx.hstack(
                # Radio button indicator matching reference UI
                rx.cond(
                    is_selected,
                    rx.box(
                        rx.box(
                            width="8px",
                            height="8px",
                            border_radius="50%",
                            background="#4F46E5",
                        ),
                        width="20px",
                        height="20px",
                        border_radius="50%",
                        border="2px solid #4F46E5",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        flex_shrink="0",
                    ),
                    rx.box(
                        width="20px",
                        height="20px",
                        border_radius="50%",
                        border="2px solid #D1D5DB",
                        flex_shrink="0",
                    ),
                ),
                # Option letter
                rx.text(
                    letter + ".",
                    font_family=FONT_BODY,
                    size="3",
                    weight="bold",
                    color=rx.cond(is_selected, "#4F46E5", "#374151"),
                    margin_left="0.4em",
                    margin_right="0.5em",
                ),
                # Option text
                rx.text(
                    text_var,
                    font_family=FONT_BODY,
                    size="3",
                    color=rx.cond(is_selected, "#1E1B4B", "#1F2937"),
                    weight=rx.cond(is_selected, "medium", "regular"),
                    line_height="1.5",
                ),
                align_items="center",
                width="100%",
            ),
            width="100%",
            padding="1.1em 1.4em",
            border_radius="10px",
            border=rx.cond(is_selected, "1.5px solid #6366F1", "1px solid #E5E7EB"),
            background=rx.cond(is_selected, "#F5F3FF", "white"),
            box_shadow=rx.cond(is_selected, "0 1px 3px rgba(99, 102, 241, 0.12)", "0 1px 2px rgba(0, 0, 0, 0.02)"),
            cursor=rx.cond(
                CandidateState.is_test_submitted | CandidateState.is_time_expired | CandidateState.is_disqualified,
                "not-allowed",
                "pointer",
            ),
            transition="all 0.15s ease",
            _hover=rx.cond(
                CandidateState.is_test_submitted | CandidateState.is_time_expired | CandidateState.is_disqualified,
                {},
                rx.cond(
                    is_selected,
                    {"background": "#EDE9FE", "border_color": "#6366F1"},
                    {"background": "#F9FAFB", "border_color": "#D1D5DB"},
                ),
            ),
            on_click=CandidateState.select_mcq_option(letter),
        ),
        rx.fragment(),
    )


def objective_question_card() -> rx.Component:
    """Single full-width Question & Answer Card for Objective questions matching reference UI."""
    return rx.box(
        rx.vstack(
            # Top Section: Header + Metadata + Prompt + Options + Clear Answer
            rx.vstack(
                # Card Top Row: Question Number + Mark for Review
                rx.hstack(
                    rx.text(
                        "Question " + CandidateState.current_question_number.to_string(),
                        font_family=FONT_DISPLAY,
                        size="5",
                        weight="bold",
                        color="#111827",
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.icon(
                            "bookmark",
                            size=16,
                            color=rx.cond(CandidateState.is_current_marked, "#D97706", "#4B5563"),
                        ),
                        rx.text(
                            rx.cond(
                                CandidateState.is_current_marked,
                                "Marked for Review",
                                "Mark for Review",
                            ),
                            font_family=FONT_BODY,
                            size="2",
                            weight="medium",
                            color=rx.cond(CandidateState.is_current_marked, "#D97706", "#4B5563"),
                        ),
                        spacing="1",
                        align_items="center",
                        cursor="pointer",
                        on_click=CandidateState.toggle_mark_for_review,
                    ),
                    width="100%",
                    align_items="center",
                ),

                # Metadata row: CO / LO / RBT Level / Marks / Objective Badge
                rx.hstack(
                    _meta_pill("CO", CandidateState.current_question_co),
                    _meta_pill("LO", CandidateState.current_question_lo),
                    _meta_pill("RBT Level", CandidateState.current_question_rbt),
                    _meta_pill("Max Marks", CandidateState.current_question_marks),
                    rx.box(
                        rx.text("Objective", font_family=FONT_BODY, size="1", weight="bold", color="#4338CA"),
                        background="#EEF2FF",
                        border="1px solid #C7D2FE",
                        border_radius="6px",
                        padding="0.2em 0.7em",
                    ),
                    spacing="2",
                    padding_top="0.8em",
                    flex_wrap="wrap",
                ),

                # Question prompt
                rx.text(
                    CandidateState.current_question["text"],
                    font_family=FONT_BODY,
                    size="3",
                    color="#1F2937",
                    line_height="1.65",
                    padding_top="1.2em",
                ),

                # MCQ Options Stack (cards A, B, C, D)
                rx.vstack(
                    _mcq_option_card("A", CandidateState.current_option_a),
                    _mcq_option_card("B", CandidateState.current_option_b),
                    _mcq_option_card("C", CandidateState.current_option_c),
                    _mcq_option_card("D", CandidateState.current_option_d),
                    spacing="3",
                    width="100%",
                    padding_top="1.5em",
                ),

                # Clear Answer Button (Right-aligned matching UI)
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Clear Answer",
                        on_click=CandidateState.clear_mcq_answer,
                        variant="outline",
                        size="2",
                        color_scheme="gray",
                        border="1px solid #D1D5DB",
                        border_radius="8px",
                        background="white",
                        color="#374151",
                        font_family=FONT_BODY,
                        font_weight="medium",
                        padding="0.5em 1.2em",
                        cursor=rx.cond(
                            (CandidateState.current_mcq_answer == "") | CandidateState.is_test_submitted | CandidateState.is_time_expired | CandidateState.is_disqualified,
                            "not-allowed",
                            "pointer",
                        ),
                        _hover={"background": "#F3F4F6", "color": "#111827"},
                        disabled=(CandidateState.current_mcq_answer == "") | CandidateState.is_test_submitted | CandidateState.is_time_expired | CandidateState.is_disqualified,
                    ),
                    width="100%",
                    padding_top="1.2em",
                ),

                spacing="0",
                align_items="start",
                width="100%",
            ),

            rx.spacer(),

            # Bottom Navigation Buttons: Previous | Next | Save & Next
            _test_bottom_nav_buttons(),

            spacing="0",
            width="100%",
            height="100%",
            justify_content="space-between",
        ),
        background="white",
        border="1px solid #E5E7EB",
        border_radius="12px",
        padding="2em",
        width="100%",
        min_height="580px",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.05)",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Right Column: Question Navigation Sidebar Components
# ─────────────────────────────────────────────────────────────────────────────

def _nav_question_button(item: dict) -> rx.Component:
    return rx.box(
        rx.text(item["number"], font_family=FONT_BODY, size="2"),
        border=rx.cond(
            item["status"] == "current",
            "1.5px solid #6366F1",
            rx.cond(
                item["status"] == "marked",
                "1.5px solid #F59E0B",
                rx.cond(
                    item["status"] == "answered",
                    "1px solid #16A34A",
                    "1px solid #E5E7EB",
                ),
            ),
        ),
        background=rx.cond(
            item["status"] == "current",
            "#EEF2FF",
            rx.cond(
                item["status"] == "marked",
                "#FEF08A",
                rx.cond(
                    item["status"] == "answered",
                    "#22C55E",
                    "#F3F4F6",
                ),
            ),
        ),
        color=rx.cond(
            item["status"] == "current",
            "#4338CA",
            rx.cond(
                item["status"] == "marked",
                "#92400E",
                rx.cond(
                    item["status"] == "answered",
                    "white",
                    "#374151",
                ),
            ),
        ),
        font_weight=rx.cond(item["status"] == "unanswered", "medium", "bold"),
        border_radius="8px",
        height="44px",
        width="100%",
        display="flex",
        align_items="center",
        justify_content="center",
        cursor="pointer",
        transition="all 0.15s ease",
        _hover=rx.cond(
            item["status"] == "current",
            {"background": "#E0E7FF"},
            rx.cond(
                item["status"] == "marked",
                {"background": "#FDE047"},
                rx.cond(
                    item["status"] == "answered",
                    {"background": "#16A34A"},
                    {"background": "#E5E7EB"},
                ),
            ),
        ),
        on_click=[
            rx.call_script("if (window.__rteSaveCurrentAnswer) window.__rteSaveCurrentAnswer();"),
            CandidateState.jump_to_question(item["id"]),
        ],
    )


def question_navigation_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # 1. Header: [::] Question Navigation
            rx.hstack(
                rx.icon("layout-grid", size=18, color="#4F46E5"),
                rx.text(
                    "Question Navigation",
                    font_family=FONT_DISPLAY,
                    size="3",
                    weight="bold",
                    color="#111827",
                ),
                spacing="2",
                align_items="center",
                width="100%",
            ),

            # 2. Status Legend
            rx.vstack(
                rx.hstack(
                    # Answered
                    rx.hstack(
                        rx.box(width="14px", height="14px", border_radius="3px", background="#22C55E", flex_shrink="0"),
                        rx.text("Answered", font_family=FONT_BODY, size="1", color="#374151"),
                        spacing="2",
                        align_items="center",
                        width="50%",
                    ),
                    # Not Answered
                    rx.hstack(
                        rx.box(width="14px", height="14px", border_radius="3px", background="#D1D5DB", flex_shrink="0"),
                        rx.text("Not Answered", font_family=FONT_BODY, size="1", color="#374151"),
                        spacing="2",
                        align_items="center",
                        width="50%",
                    ),
                    width="100%",
                    align_items="center",
                ),
                rx.hstack(
                    # Marked for Review
                    rx.hstack(
                        rx.box(width="14px", height="14px", border_radius="3px", background="#FACC15", flex_shrink="0"),
                        rx.text("Marked for Review", font_family=FONT_BODY, size="1", color="#374151"),
                        spacing="2",
                        align_items="center",
                        width="50%",
                    ),
                    # Current Question
                    rx.hstack(
                        rx.box(width="14px", height="14px", border_radius="3px", background="#8B5CF6", flex_shrink="0"),
                        rx.text("Current Question", font_family=FONT_BODY, size="1", color="#374151"),
                        spacing="2",
                        align_items="center",
                        width="50%",
                    ),
                    width="100%",
                    align_items="center",
                ),
                spacing="2",
                width="100%",
                padding_y="0.8em",
            ),

            # Grid of Question Buttons (5 columns) — all uploaded questions
            rx.grid(
                rx.foreach(CandidateState.nav_questions, _nav_question_button),
                columns="5",
                spacing="2",
                width="100%",
            ),

            spacing="2",
            width="100%",
        ),
        background="white",
        border="1px solid #E5E7EB",
        border_radius="12px",
        padding="1.4em",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.05)",
        width="100%",
    )


def instructions_card() -> rx.Component:
    return rx.box(
        rx.vstack(
            # Header with toggle chevron
            rx.hstack(
                rx.hstack(
                    rx.box(
                        rx.icon("info", size=14, color="#4F46E5"),
                        border="1.5px solid #4F46E5",
                        border_radius="50%",
                        padding="2px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                    ),
                    rx.text(
                        "Instructions",
                        font_family=FONT_DISPLAY,
                        size="2",
                        weight="bold",
                        color="#111827",
                    ),
                    spacing="2",
                    align_items="center",
                ),
                rx.spacer(),
                rx.icon(
                    rx.cond(CandidateState.show_instructions, "chevron-up", "chevron-down"),
                    size=16,
                    color="#6B7280",
                ),
                width="100%",
                align_items="center",
                cursor="pointer",
                on_click=CandidateState.toggle_instructions,
            ),

            # Instructions List (collapsible)
            rx.cond(
                CandidateState.show_instructions,
                rx.vstack(
                    rx.hstack(
                        rx.text("1.", font_family=FONT_BODY, size="1", color="#6B7280", weight="medium"),
                        rx.text("Read each question carefully.", font_family=FONT_BODY, size="1", color="#4B5563"),
                        spacing="2",
                        align_items="start",
                    ),
                    rx.hstack(
                        rx.text("2.", font_family=FONT_BODY, size="1", color="#6B7280", weight="medium"),
                        rx.text("Answer all questions.", font_family=FONT_BODY, size="1", color="#4B5563"),
                        spacing="2",
                        align_items="start",
                    ),
                    rx.hstack(
                        rx.text("3.", font_family=FONT_BODY, size="1", color="#6B7280", weight="medium"),
                        rx.text("You can mark questions for review and come back to them later.", font_family=FONT_BODY, size="1", color="#4B5563"),
                        spacing="2",
                        align_items="start",
                    ),
                    rx.hstack(
                        rx.text("4.", font_family=FONT_BODY, size="1", color="#6B7280", weight="medium"),
                        rx.text("Click on Submit Test after completing all questions.", font_family=FONT_BODY, size="1", color="#4B5563"),
                        spacing="2",
                        align_items="start",
                    ),
                    spacing="2",
                    width="100%",
                    padding_top="0.8em",
                    border_top="1px solid #F3F4F6",
                ),
                rx.fragment(),
            ),

            spacing="2",
            width="100%",
        ),
        background="white",
        border="1px solid #E5E7EB",
        border_radius="12px",
        padding="1.2em",
        box_shadow="0 1px 3px rgba(0, 0, 0, 0.05)",
        width="100%",
    )


def question_navigation_sidebar() -> rx.Component:
    return rx.vstack(
        question_navigation_card(),
        instructions_card(),
        spacing="3",
        width="310px",
        min_width="290px",
        max_width="340px",
        flex_shrink="0",
    )



# ─────────────────────────────────────────────────────────────────────────────
# Bottom Status Bar
# ─────────────────────────────────────────────────────────────────────────────

def bottom_status_bar() -> rx.Component:
    return rx.box(
        rx.hstack(
            # Left: Fullscreen & Tab Lock status notice
            rx.hstack(
                rx.icon("lock", size=16, color="#4B5563"),
                rx.vstack(
                    rx.text(
                        rx.cond(
                            CandidateState.is_fullscreen,
                            "Fullscreen & Tab Lock is Active",
                            "Fullscreen Inactive - Proctoring Flagged",
                        ),
                        font_family=FONT_BODY,
                        size="2",
                        weight="bold",
                        color=rx.cond(CandidateState.is_fullscreen, "#111827", "#DC2626"),
                    ),
                    rx.text(
                        "Exiting fullscreen or switching tabs will be flagged and may result in disqualification.",
                        font_family=FONT_BODY,
                        size="1",
                        color="#6B7280",
                    ),
                    spacing="0",
                    align_items="start",
                ),
                spacing="2",
                align_items="center",
            ),

            rx.spacer(),

            # Right: Device & Proctoring live badges
            rx.hstack(
                # Fullscreen Active Badge
                rx.hstack(
                    rx.icon(
                        rx.cond(CandidateState.is_fullscreen, "maximize", "minimize"),
                        size=15,
                        color=rx.cond(CandidateState.is_fullscreen, "#16A34A", "#DC2626"),
                    ),
                    rx.text(
                        rx.cond(CandidateState.is_fullscreen, "Fullscreen Active", "Fullscreen Inactive"),
                        font_family=FONT_BODY,
                        size="1",
                        weight="medium",
                        color=rx.cond(CandidateState.is_fullscreen, "#16A34A", "#DC2626"),
                    ),
                    spacing="1",
                    align_items="center",
                ),
                # Mic Active
                rx.hstack(
                    rx.icon("mic", size=15, color="#16A34A"),
                    rx.text("Mic Active", font_family=FONT_BODY, size="1", weight="medium", color="#16A34A"),
                    spacing="1",
                    align_items="center",
                ),
                # Camera Active
                rx.hstack(
                    rx.icon("video", size=15, color="#16A34A"),
                    rx.text("Camera Active", font_family=FONT_BODY, size="1", weight="medium", color="#16A34A"),
                    spacing="1",
                    align_items="center",
                ),
                # Tab Locked
                rx.hstack(
                    rx.icon("lock", size=15, color="#4338CA"),
                    rx.text("Tab Locked", font_family=FONT_BODY, size="1", weight="medium", color="#4338CA"),
                    spacing="1",
                    align_items="center",
                ),
                spacing="5",
                align_items="center",
            ),
            width="100%",
            align_items="center",
        ),
        padding="0.85em 2.5em",
        background="white",
        border_top="1px solid #E5E7EB",
        position="sticky",
        bottom="0",
        z_index="30",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Modals & Submission Screen
# ─────────────────────────────────────────────────────────────────────────────

def proctoring_warning_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("shield-alert", size=24, color=COLORS["danger"]),
                        background="#FEF2F2",
                        padding="0.6em",
                        border_radius="50%",
                    ),
                    rx.vstack(
                        rx.dialog.title("Proctoring Alert: Violation Detected"),
                        rx.text(
                            "Warning " + CandidateState.violation_count.to_string() + " of " + CandidateState.max_violations.to_string(),
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["danger"],
                            weight="bold",
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                ),
                rx.dialog.description(
                    rx.cond(
                        CandidateState.violation_warning_msg != "",
                        CandidateState.violation_warning_msg,
                        "You have exited fullscreen or navigated away from the assessment window. "
                        "This action has been logged by the proctoring monitor. Exceeding 3 violations "
                        "will flag your examination for immediate administrative review.",
                    ),
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                    padding_y="1em",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.cond(
                        CandidateState.is_disqualified,
                        rx.button(
                            "Return to Dashboard",
                            on_click=CandidateState.return_to_dashboard,
                            background=COLORS["danger"],
                            color="white",
                            font_family=FONT_BODY,
                            size="2",
                            _hover={"background": "#B91C1C"},
                        ),
                        rx.button(
                            "I Understand, Return to Test",
                            on_click=[
                                CandidateState.dismiss_violation_modal,
                                rx.call_script("if (!document.fullscreenElement) { (document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen || function(){}).call(document.documentElement).catch(function(e){console.warn(e);}); }"),
                            ],
                            background=COLORS["primary"],
                            color="white",
                            font_family=FONT_BODY,
                            size="2",
                        ),
                    ),
                    width="100%",
                ),
                spacing="2",
                align_items="stretch",
            ),
            max_width="480px",
            padding="1.8em",
            border_radius="14px",
        ),
        open=CandidateState.show_violation_modal,
    )


def submit_confirmation_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.box(
                        rx.icon("send", size=22, color=COLORS["primary"]),
                        background=COLORS["primary_soft"],
                        padding="0.6em",
                        border_radius="50%",
                    ),
                    rx.vstack(
                        rx.dialog.title("Submit Assessment Examination?"),
                        rx.text(
                            CandidateState.active_assessment_name + " — " + CandidateState.display_test_name,
                            font_family=FONT_BODY,
                            size="1",
                            color=COLORS["slate"],
                        ),
                        spacing="0",
                        align_items="start",
                    ),
                    spacing="3",
                    align_items="center",
                ),

                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.text("Total Questions:", font_family=FONT_BODY, size="2", color=COLORS["slate"]),
                            rx.spacer(),
                            rx.text(CandidateState.total_questions.to_string(), font_family=FONT_BODY, size="2", weight="bold"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.text("Answered:", font_family=FONT_BODY, size="2", color="#027A48"),
                            rx.spacer(),
                            rx.text(CandidateState.answered_count.to_string(), font_family=FONT_BODY, size="2", weight="bold", color="#027A48"),
                            width="100%",
                        ),
                        rx.hstack(
                            rx.text("Marked for Review:", font_family=FONT_BODY, size="2", color="#D97706"),
                            rx.spacer(),
                            rx.text(CandidateState.marked_count.to_string(), font_family=FONT_BODY, size="2", weight="bold", color="#D97706"),
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    background=COLORS["canvas"],
                    border=f"1px solid {COLORS['line']}",
                    border_radius="8px",
                    padding="1em",
                    margin_y="1em",
                    width="100%",
                ),

                rx.text(
                    "Are you sure you want to submit? Once submitted, you cannot modify your answers.",
                    font_family=FONT_BODY,
                    size="2",
                    color=COLORS["slate"],
                ),

                rx.hstack(
                    rx.button(
                        "Cancel, Continue Test",
                        on_click=CandidateState.close_submit_dialog,
                        variant="outline",
                        color_scheme="gray",
                        font_family=FONT_BODY,
                        size="2",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Confirm & Submit Test",
                        on_click=CandidateState.confirm_submit_test,
                        background="#027A48",
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        _hover={"background": "#05603A"},
                    ),
                    width="100%",
                    padding_top="0.8em",
                ),
                spacing="2",
                align_items="stretch",
            ),
            max_width="480px",
            padding="1.8em",
            border_radius="14px",
        ),
        open=CandidateState.show_submit_dialog,
    )



def _candidate_feedback_question(question: dict) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text(
                question["text"],
                font_family=FONT_BODY,
                size="2",
                weight="medium",
                color=COLORS["ink"],
            ),
            rx.cond(
                question["required"],
                rx.text("Required", font_family=FONT_BODY, size="1", color="#B42318"),
                rx.fragment(),
            ),
            spacing="2",
            align_items="center",
            width="100%",
        ),
        rx.text_area(
            on_change=CandidateState.set_candidate_feedback_answer(question["id"]),
            placeholder="Enter your response...",
            min_height="88px",
            width="100%",
            font_family=FONT_BODY,
            border=f"1px solid {COLORS['line']}",
            border_radius="8px",
        ),
        spacing="2",
        width="100%",
        align_items="stretch",
    )


def candidate_feedback_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.vstack(
                    rx.text(
                        "Test Feedback",
                        font_family=FONT_DISPLAY,
                        size="4",
                        weight="bold",
                        color=COLORS["ink"],
                    ),
                    rx.text(
                        "Please provide your feedback for this assessment.",
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                    ),
                    spacing="1",
                    align_items="start",
                    width="100%",
                ),
                rx.cond(
                    CandidateState.candidate_feedback_error != "",
                    rx.text(
                        CandidateState.candidate_feedback_error,
                        font_family=FONT_BODY,
                        size="2",
                        color="#B42318",
                    ),
                    rx.fragment(),
                ),
                rx.cond(
                    CandidateState.candidate_feedback_questions.length() > 0,
                    rx.vstack(
                        rx.foreach(
                            CandidateState.candidate_feedback_questions,
                            _candidate_feedback_question,
                        ),
                        spacing="4",
                        width="100%",
                        align_items="stretch",
                    ),
                    # Empty integration state until backend provides Admin-created form
                    rx.center(
                        rx.vstack(
                            rx.icon("clipboard-list", size=32, color=COLORS["slate"]),
                            rx.text(
                                "No feedback questions configured",
                                font_family=FONT_BODY,
                                size="3",
                                weight="bold",
                                color=COLORS["ink"],
                            ),
                            rx.text(
                                "The feedback form for this assessment will appear here once configured by the administrator.",
                                font_family=FONT_BODY,
                                size="2",
                                color=COLORS["slate"],
                                text_align="center",
                                max_width="400px",
                            ),
                            spacing="2",
                            align_items="center",
                        ),
                        padding="2.5em 1em",
                        width="100%",
                    ),
                ),
                rx.hstack(
                    rx.button(
                        "Close",
                        on_click=CandidateState.skip_candidate_feedback,
                        variant="outline",
                        color=COLORS["slate"],
                        border=f"1px solid {COLORS['line']}",
                        font_family=FONT_BODY,
                        size="2",
                        cursor="pointer",
                        _hover={"background": COLORS["canvas"]},
                    ),
                    rx.spacer(),
                    rx.button(
                        "Submit Feedback",
                        on_click=CandidateState.submit_candidate_test_feedback,
                        background=COLORS["primary"],
                        color="white",
                        font_family=FONT_BODY,
                        size="2",
                        disabled=CandidateState.candidate_feedback_questions.length() == 0,
                        opacity=rx.cond(
                            CandidateState.candidate_feedback_questions.length() == 0,
                            "0.5",
                            "1.0",
                        ),
                        cursor=rx.cond(
                            CandidateState.candidate_feedback_questions.length() == 0,
                            "not-allowed",
                            "pointer",
                        ),
                        _hover=rx.cond(
                            CandidateState.candidate_feedback_questions.length() == 0,
                            {},
                            {"background": COLORS["primary_hover"]},
                        ),
                    ),
                    width="100%",
                    align_items="center",
                    margin_top="0.5em",
                ),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),
            style={"maxWidth": "600px", "width": "90vw"},
            max_height="85vh",
            overflow_y="auto",
            padding="1.8em",
            border_radius="14px",
        ),
        open=CandidateState.show_candidate_feedback_modal,
    )
def test_submitted_screen() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.vstack(
                    rx.cond(
                        CandidateState.is_disqualified,
                        rx.box(
                            rx.icon("shield-alert", size=48, color="#DC2626"),
                            background="#FEF2F2",
                            padding="1.2em",
                            border_radius="50%",
                            margin_bottom="0.5em",
                        ),
                        rx.cond(
                            CandidateState.is_time_expired,
                            rx.box(
                                rx.icon("clock-alert", size=48, color="#DC2626"),
                                background="#FEF2F2",
                                padding="1.2em",
                                border_radius="50%",
                                margin_bottom="0.5em",
                            ),
                            rx.box(
                                rx.icon("circle-check", size=48, color="#027A48"),
                                background="#ECFDF3",
                                padding="1.2em",
                                border_radius="50%",
                                margin_bottom="0.5em",
                            ),
                        ),
                    ),
                    rx.heading(
                        rx.cond(
                            CandidateState.is_disqualified,
                            "Test Terminated — Proctoring Disqualification",
                            rx.cond(
                                CandidateState.is_time_expired,
                                "Time Expired — Test Automatically Submitted",
                                "Test Submitted Successfully!",
                            ),
                        ),
                        font_family=FONT_DISPLAY,
                        size="6",
                        weight="bold",
                        color=COLORS["ink"],
                        text_align="center",
                    ),
                    rx.text(
                        rx.cond(
                            CandidateState.is_disqualified,
                            "You have reached the maximum allowed proctoring violations (3 of 3). Your test session has been terminated and flagged as Disqualified.",
                            rx.cond(
                                CandidateState.is_time_expired,
                                "The allotted test duration has elapsed (00:00:00). Your answers have been automatically saved and submitted for evaluation.",
                                "Your examination answers have been securely submitted and logged for evaluation.",
                            ),
                        ),
                        font_family=FONT_BODY,
                        size="2",
                        color=COLORS["slate"],
                        text_align="center",
                    ),
                    rx.box(
                        rx.vstack(
                            rx.hstack(
                                rx.text("Status", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.cond(
                                    CandidateState.is_disqualified,
                                    rx.badge("Disqualified (Proctoring Violation)", color_scheme="red", variant="soft", size="1"),
                                    rx.cond(
                                        CandidateState.is_time_expired,
                                        rx.badge("Time Expired (Auto-Submitted)", color_scheme="red", variant="soft", size="1"),
                                        rx.badge("Submitted", color_scheme="green", variant="soft", size="1"),
                                    ),
                                ),
                                width="100%",
                            ),
                            rx.divider(color_scheme="gray", size="4"),
                            rx.hstack(
                                rx.text("Submission Receipt", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.text(CandidateState.submission_receipt, font_family="monospace", size="1", weight="bold", color=COLORS["ink"]),
                                width="100%",
                            ),
                            rx.divider(color_scheme="gray", size="4"),
                            rx.hstack(
                                rx.text("Assessment", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.text(CandidateState.active_assessment_name, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("Test", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.text(CandidateState.display_test_name, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("Candidate", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.text(AuthState.candidate_name + " (" + AuthState.candidate_emp_id + ")", font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
                                width="100%",
                            ),
                            rx.hstack(
                                rx.text("Submitted At", font_family=FONT_BODY, size="1", color=COLORS["slate"]),
                                rx.spacer(),
                                rx.text(CandidateState.submitted_at, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
                                width="100%",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        background=COLORS["canvas"],
                        border=f"1px solid {COLORS['line']}",
                        border_radius="10px",
                        padding="1.2em",
                        margin_y="1.2em",
                        width="100%",
                    ),

                    # Feedback section shown for successful submissions

                    # Action buttons
                    rx.cond(
                        CandidateState.is_disqualified,
                        rx.button(
                            rx.icon("arrow-left", size=14),
                            "Return to My Assessments",
                            on_click=CandidateState.return_to_dashboard,
                            size="3",
                            background=COLORS["primary"],
                            color="white",
                            font_family=FONT_BODY,
                            margin_top="1.5em",
                            _hover={"background": COLORS["primary_hover"]},
                        ),
                        rx.button(
                            "Continue to Feedback",
                            on_click=CandidateState.open_candidate_feedback_form,
                            size="3",
                            background=COLORS["primary"],
                            color="white",
                            font_family=FONT_BODY,
                            margin_top="1.5em",
                            _hover={"background": COLORS["primary_hover"]},
                        ),
                    ),
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="16px",
                padding="3em 2.5em",
                max_width="660px",
                width="100%",
                box_shadow="0 10px 25px -5px rgba(0, 0, 0, 0.05)",
            ),
            align_items="center",
            justify_content="center",
            width="100%",
            min_height="100vh",
            padding="2em",
        ),
        background=COLORS["canvas"],
        width="100%",
        min_height="100vh",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main Page Entry Point
# ─────────────────────────────────────────────────────────────────────────────


def candidate_test_page() -> rx.Component:
    return rx.box(
        proctoring_warning_dialog(),
        candidate_feedback_modal(),
        rx.cond(
            CandidateState.show_candidate_feedback_modal,
            # Feedback View: The submission confirmation is closed/dismissed.
            # Ensures the confirmation UI and feedback modal never appear simultaneously or overlap.
            rx.box(
                width="100%",
                min_height="100vh",
                background=COLORS["canvas"],
            ),
            rx.cond(
                CandidateState.is_test_submitted,
                test_submitted_screen(),
                rx.box(
                    rx.button(
                        id="fs-exit-btn",
                        on_click=CandidateState.handle_fullscreen_exited,
                        style={"display": "none"},
                    ),
                    rx.button(
                        id="fs-enter-btn",
                        on_click=CandidateState.handle_fullscreen_entered,
                        style={"display": "none"},
                    ),
                    # Hidden bridge button for tab-switch / window-blur violation
                    rx.button(
                        id="tab-switch-btn",
                        on_click=CandidateState.trigger_proctoring_warning,
                        disabled=CandidateState.is_test_submitted | CandidateState.is_time_expired,
                        style={"display": "none"},
                    ),
                    rx.script(
                        r"""
                        (function() {
                            // ── Fullscreen detection ──────────────────────────────────────
                            function checkFS() {
                                var isFS = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
                                if (!isFS) {
                                    var exitBtn = document.getElementById('fs-exit-btn');
                                    if (exitBtn) exitBtn.click();
                                } else {
                                    var enterBtn = document.getElementById('fs-enter-btn');
                                    if (enterBtn) enterBtn.click();
                                }
                            }
                            if (window.__candidate_fs_handler) {
                                document.removeEventListener('fullscreenchange', window.__candidate_fs_handler);
                                document.removeEventListener('webkitfullscreenchange', window.__candidate_fs_handler);
                            }
                            window.__candidate_fs_handler = checkFS;
                            document.addEventListener('fullscreenchange', checkFS);
                            document.addEventListener('webkitfullscreenchange', checkFS);
    
                            // ── Tab-switch / window-blur detection ────────────────────────
                            // Use a 600ms debounce: both visibilitychange and window blur
                            // can fire for the same switch event (e.g. Alt+Tab sometimes
                            // triggers both). The debounce ensures exactly one violation per
                            // actual switch, regardless of which events fire together.
                            var __tabSwitchLastMs = 0;
                            function triggerTabSwitch() {
                                var btn = document.getElementById('tab-switch-btn');
                                if (btn && btn.disabled) return; // test over
                                var now = Date.now();
                                if (now - __tabSwitchLastMs < 600) return; // debounce
                                __tabSwitchLastMs = now;
                                btn.click();
                            }
                            // Remove any previous listeners before re-attaching
                            if (window.__candidate_vis_handler) {
                                document.removeEventListener('visibilitychange', window.__candidate_vis_handler);
                            }
                            if (window.__candidate_blur_handler) {
                                window.removeEventListener('blur', window.__candidate_blur_handler);
                            }
                            // visibilitychange: fires when switching browser tabs
                            window.__candidate_vis_handler = function() {
                                if (document.hidden) triggerTabSwitch();
                            };
                            // blur: fires when Alt+Tabbing to another application.
                            // No document.hidden check — blur is the primary signal for app-switch.
                            window.__candidate_blur_handler = function() {
                                triggerTabSwitch();
                            };
                            document.addEventListener('visibilitychange', window.__candidate_vis_handler);
                            window.addEventListener('blur', window.__candidate_blur_handler);
    
                            // ── Auto-refocus when candidate returns to the tab ────────────
                            if (window.__candidate_focus_handler) {
                                document.removeEventListener('visibilitychange', window.__candidate_focus_handler);
                            }
                            window.__candidate_focus_handler = function() {
                                if (!document.hidden) { setTimeout(function(){ window.focus(); }, 50); }
                            };
                            document.addEventListener('visibilitychange', window.__candidate_focus_handler);
    
                            // ── Block keyboard tab-switch shortcuts ───────────────────────
                            // Ctrl+W (close tab), Ctrl+T (new tab), Ctrl+N (new window),
                            // Ctrl+Tab / Ctrl+Shift+Tab (cycle tabs), Alt+F4 (close window)
                            if (window.__candidate_key_handler) {
                                document.removeEventListener('keydown', window.__candidate_key_handler, true);
                            }
                            window.__candidate_key_handler = function(e) {
                                var btn = document.getElementById('tab-switch-btn');
                                if (btn && btn.disabled) return; // test already over
                                var ctrl = e.ctrlKey || e.metaKey;
                                var blocked = false;
                                if (ctrl && (e.key === 'w' || e.key === 'W'))             blocked = true;
                                if (ctrl && (e.key === 't' || e.key === 'T'))             blocked = true;
                                if (ctrl && (e.key === 'n' || e.key === 'N'))             blocked = true;
                                if (ctrl && e.key === 'Tab')                               blocked = true;
                                if (ctrl && e.shiftKey && e.key === 'Tab')                blocked = true;
                                if (e.altKey && e.key === 'F4')                           blocked = true;
                                if (blocked) {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    triggerTabSwitch(); // count as a violation attempt
                                }
                            };
                            document.addEventListener('keydown', window.__candidate_key_handler, true);
    
                            // ── Warn on unload / navigation away ─────────────────────────
                            if (window.__candidate_beforeunload) {
                                window.removeEventListener('beforeunload', window.__candidate_beforeunload);
                            }
                            window.__candidate_beforeunload = function(e) {
                                var btn = document.getElementById('tab-switch-btn');
                                if (btn && btn.disabled) return; // test over, allow navigation
                                e.preventDefault();
                                e.returnValue = 'Leaving this page will be flagged as a proctoring violation.';
                                return e.returnValue;
                            };
                            window.addEventListener('beforeunload', window.__candidate_beforeunload);
    
                            // ── localStorage helpers ───────────────────────────────────────
                            // Key: candidate_id::assessment_name::test_name::question_id
                            // Data attributes are written on #rte-relay by _restore_rte_script.
                            window.__rteGetStorageKey = function(qidOverride) {
                                var relay = document.getElementById('rte-relay');
                                if (!relay) return null;
                                var cid  = relay.dataset.candidateId || 'unknown';
                                var asmn = relay.dataset.assessment   || 'unknown';
                                var test = relay.dataset.testName     || 'unknown';
                                var qid  = qidOverride || relay.dataset.questionId || '1';
                                return cid + '::' + asmn + '::' + test + '::' + qid;
                            };
                            window.__rteSaveToStorage = function(html) {
                                var key = window.__rteGetStorageKey();
                                if (!key) return;
                                try { localStorage.setItem(key, html); } catch(e) {}
                            };
                            window.__rteLoadFromStorage = function(qid) {
                                var relay = document.getElementById('rte-relay');
                                if (!relay) return null;
                                var cid  = relay.dataset.candidateId || 'unknown';
                                var asmn = relay.dataset.assessment   || 'unknown';
                                var test = relay.dataset.testName     || 'unknown';
                                var key  = cid + '::' + asmn + '::' + test + '::' + (qid || '1');
                                try { return localStorage.getItem(key); } catch(e) { return null; }
                            };
    
                            // ── Word count helper ─────────────────────────────────────────
                            function countWords(html) {
                                if (!html) return 0;
                                var text = html.replace(/<(br|\/div|\/p|\/li)\s*\/?>/gi, ' ');
                                text = text.replace(/<[^>]+>/g, ' ');
                                text = text.replace(/&nbsp;/gi, ' ');
                                text = text.replace(/&[a-z0-9#]+;/gi, ' ');
                                text = text.trim();
                                if (!text) return 0;
                                var words = text.split(/\s+/).filter(function(w) { return w.length > 0; });
                                return words.length;
                            }
    
                            window.__updateWordCount = function(html) {
                                var el = document.getElementById('rte-word-count');
                                if (!el) return;
                                var val = (html !== undefined && html !== null) ? html : (document.getElementById('rte-editor') ? document.getElementById('rte-editor').innerHTML : '');
                                el.textContent = 'Words: ' + countWords(val);
                            };
    
                            // ── Relay sync helper ─────────────────────────────────────────
                            function syncRelay(html) {
                                var relay = document.getElementById('rte-relay');
                                if (!relay) return;
                                var setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
                                if (setter) {
                                    setter.call(relay, html);
                                } else {
                                    relay.value = html;
                                }
                                if (relay._valueTracker) {
                                    relay._valueTracker.setValue(html + '_chg');
                                }
                                relay.dispatchEvent(new Event('input', { bubbles: true }));
                                relay.dispatchEvent(new Event('change', { bubbles: true }));
                            }
    
                            window.__rteSaveCurrentAnswer = function() {
                                var ed = document.getElementById('rte-editor');
                                if (!ed) return;
                                window.__rteSaveToStorage(ed.innerHTML);
                                syncRelay(ed.innerHTML);
                            };
    
                            // ── Shared input binder (attaches once per editor lifetime) ────
                            window.bindRteInput = function(ed) {
                                if (ed.__rteInputBound) return;
                                ed.__rteInputBound = true;
                                function onInput() {
                                    window.__updateWordCount(ed.innerHTML);
                                    window.__rteSaveToStorage(ed.innerHTML);
                                    syncRelay(ed.innerHTML);
                                }
                                ed.addEventListener('input', onInput);
                                ed.addEventListener('keyup', function() {
                                    window.__updateWordCount(ed.innerHTML);
                                });
                                ed.addEventListener('paste', function() {
                                    setTimeout(onInput, 15);
                                });
                            };
    
                            // ── RTE restore (called via rx.call_script after navigation) ──
                            window.__rteRestoreAnswer = function(savedHtml, qid) {
                                var ed = document.getElementById('rte-editor');
                                if (!ed) return;
                                // localStorage is freshest; fall back to backend state
                                var localHtml = qid ? window.__rteLoadFromStorage(qid) : null;
                                var html = (localHtml !== null && localHtml !== '') ? localHtml : (savedHtml || '');
                                ed.__rteAttached = false;
                                ed.innerHTML = html;
                                ed.__rteAttached = true;
                                window.bindRteInput(ed);
                                window.__updateWordCount(html);
                            };
    
                            // ── Seed editor on first page load ────────────────────────────
                            (function seedOnLoad() {
                                var ed = document.getElementById('rte-editor');
                                var relay = document.getElementById('rte-relay');
                                if (!ed || !relay) { setTimeout(seedOnLoad, 100); return; }
                                window.bindRteInput(ed);
                                var qid = relay.dataset.questionId || '1';
                                var localHtml = window.__rteLoadFromStorage(qid);
                                var html = (localHtml !== null) ? localHtml : (relay.dataset.saved || '');
                                if (html && (!ed.innerHTML || ed.innerHTML === '<br>')) {
                                    ed.__rteAttached = false;
                                    ed.innerHTML = html;
                                    ed.__rteAttached = true;
                                }
                                window.__updateWordCount(ed.innerHTML);
                            })();
                        })();
                        """
                    ),
                    rx.vstack(
                        test_header(),
                        # Main Body: Active Question Area (flex="1") + Question Navigation Sidebar (width="310px")
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.cond(
                                        CandidateState.current_question_type == "Objective",
                                        objective_question_card(),
                                        rx.hstack(
                                            question_card(),
                                            answer_card(),
                                            spacing="3",
                                            width="100%",
                                            align_items="stretch",
                                        ),
                                    ),
                                    flex="1",
                                    width="100%",
                                ),
                                question_navigation_sidebar(),
                                spacing="4",
                                width="100%",
                                align_items="start",
                            ),
                            padding="1.8em 2.5em",
                            width="100%",
                            flex="1",
                            background="#F9FAFB",
                        ),
                        bottom_status_bar(),
                        submit_confirmation_dialog(),
                        spacing="0",
                        width="100%",
                        min_height="100vh",
                        background="#F9FAFB",
                    ),
                    width="100%",
                    min_height="100vh",
                    background="#F9FAFB",
                ),

            ),
        ),
        width="100%",
        min_height="100vh",
        background="#F9FAFB",
    )
