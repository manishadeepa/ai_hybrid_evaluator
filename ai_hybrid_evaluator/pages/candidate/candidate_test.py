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
                    CandidateState.active_assessment_name + " - " + CandidateState.active_test_name,
                    font_family=FONT_DISPLAY,
                    size="4",
                    weight="bold",
                    color="#111827",
                ),
                rx.box(
                    rx.text(
                        CandidateState.current_question_number.to_string() + " of 20",
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

def question_card() -> rx.Component:
    q = CandidateState.current_question

    return rx.box(
        rx.vstack(
            # Top Section: Header + Text + Guidelines
            rx.vstack(
                # Card Top Row: Question Title + Mark for Review
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
                            "Mark for Review",
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

                # Question prompt
                rx.text(
                    q["text"],
                    font_family=FONT_BODY,
                    size="3",
                    color="#1F2937",
                    line_height="1.65",
                    padding_top="1.4em",
                ),

                # Guidelines Heading
                rx.text(
                    "Guidelines:",
                    font_family=FONT_BODY,
                    size="2",
                    weight="bold",
                    color="#111827",
                    padding_top="1.4em",
                ),

                # Guidelines Bullet Points
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

            rx.spacer(),

            # Bottom Navigation Buttons: Previous / Next
            rx.hstack(
                rx.button(
                    rx.hstack(
                        rx.icon("arrow-left", size=14),
                        rx.text("Previous", font_family=FONT_BODY, size="2", weight="medium"),
                        spacing="1",
                        align_items="center",
                    ),
                    on_click=CandidateState.prev_question,
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
                rx.button(
                    rx.hstack(
                        rx.text("Next", font_family=FONT_BODY, size="2", weight="medium"),
                        rx.icon("arrow-right", size=14),
                spacing="1",
                        align_items="center",
                    ),
                    on_click=CandidateState.next_question,
                    disabled=CandidateState.current_question_index == 19,
                    size="2",
                    background="#4338CA",
                    color="white",
                    border_radius="8px",
                    padding="0.5em 1.5em",
                    _hover={"background": "#3730A3"},
                ),
                width="100%",
                align_items="center",
                padding_top="1.5em",
            ),

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


# ─────────────────────────────────────────────────────────────────────────────
# Right Column: Answer Editor Card
# ─────────────────────────────────────────────────────────────────────────────

# ── Rich-Text Editor JS helpers ──────────────────────────────────────────────
# Runs execCommand on the contenteditable editor, then syncs the updated HTML
# back to the backend state via the hidden relay input.
_EXEC_CMD_JS = """
(function(cmd, arg) {
    var ed = document.getElementById('rte-editor');
    if (!ed) return;
    ed.focus();
    document.execCommand(cmd, false, arg || null);
    // Sync updated HTML back to state via the hidden relay input
    var relay = document.getElementById('rte-relay');
    if (relay) {
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(relay, ed.innerHTML);
        relay.dispatchEvent(new Event('input', { bubbles: true }));
    }
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
        # ── Hidden relay input: bridges the contenteditable -> Reflex state ──
        # The JS oninput handler writes editor.innerHTML into this input,
        # which Reflex picks up as a normal on_change event.
        rx.el.input(
            id="rte-relay",
            type="hidden",
            value=CandidateState.current_answer_text,
            on_change=CandidateState.set_answer_html,
            style={"display": "none"},
        ),

        rx.vstack(
            # Top Header Row: Your Answer + Auto-saved badge + Words count
            rx.hstack(
                rx.text(
                    "Your Answer",
                    font_family=FONT_DISPLAY,
                    size="4",
                    weight="bold",
                    color="#111827",
                ),
                rx.hstack(
                    rx.icon("circle-check", size=14, color="#16A34A"),
                    rx.text("Auto-saved", font_family=FONT_BODY, size="1", weight="medium", color="#16A34A"),
                    spacing="1",
                    align_items="center",
                ),
                rx.spacer(),
                rx.text(
                    "Words: " + CandidateState.current_word_count.to_string(),
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
                # Script: hydrate editor content from state on mount/question-change,
                # and wire the oninput sync to the relay.
                rx.script(
                    """
                    (function() {
                        function initRTE() {
                            var ed = document.getElementById('rte-editor');
                            var relay = document.getElementById('rte-relay');
                            if (!ed || !relay) { setTimeout(initRTE, 80); return; }

                            // Sync relay value -> editor HTML (restores content on
                            // question navigation or page hydration).
                            if (ed.innerHTML !== relay.value) {
                                ed.innerHTML = relay.value || '';
                            }

                            // Attach oninput once (guard against double-attach).
                            if (!ed.__rteAttached) {
                                ed.__rteAttached = true;
                                ed.addEventListener('input', function() {
                                    var niv = Object.getOwnPropertyDescriptor(
                                        window.HTMLInputElement.prototype, 'value').set;
                                    niv.call(relay, ed.innerHTML);
                                    relay.dispatchEvent(new Event('input', { bubbles: true }));
                                });
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
                            "Warning #" + CandidateState.violation_count.to_string() + " of " + CandidateState.max_violations.to_string(),
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
                            CandidateState.active_assessment_name + " — " + CandidateState.active_test_name,
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
                            rx.text("20", font_family=FONT_BODY, size="2", weight="bold"),
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


def test_submitted_screen() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.vstack(
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
                    rx.heading(
                        rx.cond(
                            CandidateState.is_time_expired,
                            "Time Expired — Test Automatically Submitted",
                            "Test Submitted Successfully",
                        ),
                        font_family=FONT_DISPLAY,
                        size="6",
                        weight="bold",
                        color=COLORS["ink"],
                        text_align="center",
                    ),
                    rx.text(
                        rx.cond(
                            CandidateState.is_time_expired,
                            "The allotted test duration has elapsed (00:00:00). Your answers have been automatically saved and submitted for evaluation.",
                            "Your examination answers have been securely submitted and logged for evaluation.",
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
                                    CandidateState.is_time_expired,
                                    rx.badge("Time Expired (Auto-Submitted)", color_scheme="red", variant="soft", size="1"),
                                    rx.badge("Submitted", color_scheme="green", variant="soft", size="1"),
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
                                rx.text(CandidateState.active_assessment_name + " — " + CandidateState.active_test_name, font_family=FONT_BODY, size="1", weight="medium", color=COLORS["ink"]),
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
                    spacing="3",
                    align_items="center",
                    width="100%",
                ),
                background=COLORS["surface"],
                border=f"1px solid {COLORS['line']}",
                border_radius="16px",
                padding="3em 2.5em",
                max_width="560px",
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
    return rx.cond(
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
            rx.script(
                """
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

                    // ── RTE relay watcher ─────────────────────────────────────────
                    // When Reflex updates the relay input's value (e.g. question
                    // navigation), push that HTML into the contenteditable editor.
                    function watchRelay() {
                        var relay = document.getElementById('rte-relay');
                        var ed    = document.getElementById('rte-editor');
                        if (!relay || !ed) { setTimeout(watchRelay, 100); return; }
                        if (window.__rteRelayObserver) window.__rteRelayObserver.disconnect();
                        window.__rteRelayObserver = new MutationObserver(function() {
                            if (ed.innerHTML !== relay.value) {
                                // Temporarily detach oninput to avoid feedback loop
                                ed.__rteAttached = false;
                                ed.innerHTML = relay.value || '';
                                ed.__rteAttached = true;
                                // Re-wire the input listener
                                ed.addEventListener('input', function onInput() {
                                    var niv = Object.getOwnPropertyDescriptor(
                                        window.HTMLInputElement.prototype, 'value').set;
                                    niv.call(relay, ed.innerHTML);
                                    relay.dispatchEvent(new Event('input', { bubbles: true }));
                                });
                            }
                        });
                        window.__rteRelayObserver.observe(relay, { attributes: true, attributeFilter: ['value'] });
                    }
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', watchRelay);
                    } else {
                        watchRelay();
                    }
                })();
                """
            ),
            rx.vstack(
                test_header(),
                # Main Two-Column Body
                rx.box(
                    rx.hstack(
                        question_card(),
                        answer_card(),
                        spacing="4",
                        width="100%",
                        align_items="stretch",
                    ),
                    padding="1.8em 2.5em",
                    width="100%",
                    flex="1",
                    background="#F9FAFB",
                ),
                bottom_status_bar(),
                proctoring_warning_dialog(),
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
    )