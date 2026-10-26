"""
Gen AI Hybrid Evaluator — Role-Selection Home Page
Matches reference UI design with TVS branding, flowing waves, and 3 role cards.

Single-screen layout at standard desktop resolution.
Frontend UI only — buttons trigger role-selected alerts.
"""

import reflex as rx
from ai_hybrid_evaluator.theme import COLORS, FONT_BODY, FONT_DISPLAY


# ─────────────────────────────────────────────────────────────────────────────
# Responsive helper
# ─────────────────────────────────────────────────────────────────────────────

def _bp(**kwargs):
    """Shorthand for rx.breakpoints(**kwargs)."""
    return rx.breakpoints(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Background Wave SVG (Subtle Red & Blue flowing ribbons)
# ─────────────────────────────────────────────────────────────────────────────

def _wave_background() -> rx.Component:
    """Subtle flowing curved wave lines in TVS red and blue."""
    return rx.html(
        """
        <svg viewBox="0 0 1440 900" fill="none" preserveAspectRatio="none"
             xmlns="http://www.w3.org/2000/svg"
             style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;overflow:hidden;">
          <defs>
            <linearGradient id="redWaveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#E11D48" stop-opacity="0.32"/>
              <stop offset="60%" stop-color="#FB7185" stop-opacity="0.14"/>
              <stop offset="100%" stop-color="#FDA4AF" stop-opacity="0.0"/>
            </linearGradient>
            <linearGradient id="blueWaveGrad" x1="100%" y1="0%" x2="0%" y2="0%">
              <stop offset="0%" stop-color="#2563EB" stop-opacity="0.30"/>
              <stop offset="60%" stop-color="#60A5FA" stop-opacity="0.14"/>
              <stop offset="100%" stop-color="#BFDBFE" stop-opacity="0.0"/>
            </linearGradient>
          </defs>

          <!-- Top-left sweeping red waves -->
          <path d="M-80,240 C160,290 320,130 540,190 C760,250 940,150 1480,220"
                stroke="url(#redWaveGrad)" stroke-width="1.8" fill="none"/>
          <path d="M-80,265 C140,315 300,155 520,215 C740,275 920,175 1480,245"
                stroke="url(#redWaveGrad)" stroke-width="1.2" opacity="0.75" fill="none"/>
          <path d="M-80,215 C180,265 340,105 560,165 C780,225 960,125 1480,195"
                stroke="url(#redWaveGrad)" stroke-width="1.0" opacity="0.5" fill="none"/>

          <!-- Top-right sweeping blue waves -->
          <path d="M1480,120 C1200,80 1020,220 780,150 C540,80 280,180 -80,110"
                stroke="url(#blueWaveGrad)" stroke-width="1.8" fill="none"/>
          <path d="M1480,145 C1180,105 1000,245 760,175 C520,105 260,205 -80,135"
                stroke="url(#blueWaveGrad)" stroke-width="1.2" opacity="0.75" fill="none"/>
          <path d="M1480,95 C1220,55 1040,195 800,125 C560,55 300,155 -80,85"
                stroke="url(#blueWaveGrad)" stroke-width="1.0" opacity="0.5" fill="none"/>
        </svg>
        """
    )


# ─────────────────────────────────────────────────────────────────────────────
# Role Card Illustrations (Vector SVGs)
# ─────────────────────────────────────────────────────────────────────────────

def _admin_illustration() -> rx.Component:
    """Administrator monitor + target badge + user silhouette."""
    return rx.html(
        """
        <svg viewBox="0 0 160 115" xmlns="http://www.w3.org/2000/svg"
             style="width:135px;height:100px;display:block;margin:0 auto;">
          <!-- Soft lavender circle glow -->
          <circle cx="80" cy="56" r="44" fill="#EDE9FE"/>

          <!-- Administrator user silhouette -->
          <circle cx="80" cy="27" r="10" fill="#7C3AED"/>
          <path d="M66,50 C66,40 72,39 80,39 C88,39 94,40 94,50 Z" fill="#8B5CF6"/>

          <!-- Monitor screen frame -->
          <rect x="42" y="44" width="76" height="50" rx="8" fill="#FFFFFF" stroke="#8B5CF6" stroke-width="2.5"/>

          <!-- Monitor stand -->
          <path d="M75,94 L85,94 L87,103 L73,103 Z" fill="#8B5CF6"/>
          <rect x="65" y="102" width="30" height="3" rx="1.5" fill="#7C3AED"/>

          <!-- Screen UI lines -->
          <rect x="50" y="52" width="28" height="4" rx="2" fill="#C4B5FD"/>
          <rect x="50" y="59" width="36" height="3" rx="1.5" fill="#DDD6FE"/>
          <rect x="50" y="65" width="24" height="3" rx="1.5" fill="#DDD6FE"/>

          <!-- Target/gear badge on screen -->
          <circle cx="102" cy="58" r="7" fill="none" stroke="#7C3AED" stroke-width="2"/>
          <circle cx="102" cy="58" r="2.5" fill="#7C3AED"/>
        </svg>
        """
    )


def _facilitator_illustration() -> rx.Component:
    """Evaluator clipboard + checkmark badge illustration."""
    return rx.html(
        """
        <svg viewBox="0 0 160 115" xmlns="http://www.w3.org/2000/svg"
             style="width:135px;height:100px;display:block;margin:0 auto;">
          <!-- Soft mint circle glow -->
          <circle cx="80" cy="56" r="44" fill="#DCFCE7"/>

          <!-- Clipboard body -->
          <rect x="52" y="28" width="56" height="70" rx="8" fill="#FFFFFF" stroke="#059669" stroke-width="2.5"/>

          <!-- Clipboard top clip -->
          <path d="M68,28 L68,23 C68,21 70,19 72,19 L88,19 C90,19 92,21 92,23 L92,28 Z" fill="#047857"/>
          <rect x="73" y="24" width="14" height="6" rx="2" fill="#34D399"/>
          <circle cx="80" cy="15" r="4" fill="#059669"/>

          <!-- Lines inside clipboard -->
          <rect x="62" y="42" width="22" height="3" rx="1.5" fill="#6EE7B7"/>
          <rect x="62" y="49" width="34" height="2.5" rx="1.25" fill="#A7F3D0"/>
          <rect x="62" y="55" width="30" height="2.5" rx="1.25" fill="#A7F3D0"/>
          <rect x="62" y="61" width="26" height="2.5" rx="1.25" fill="#A7F3D0"/>
          <rect x="62" y="67" width="18" height="2.5" rx="1.25" fill="#A7F3D0"/>

          <!-- Checkmark badge on bottom right -->
          <circle cx="98" cy="85" r="11" fill="#059669" stroke="#FFFFFF" stroke-width="2"/>
          <path d="M93.5,85 L96.5,88 L102.5,81.5" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
    )


def _candidate_illustration() -> rx.Component:
    """Test taker laptop + question mark + star badge illustration."""
    return rx.html(
        """
        <svg viewBox="0 0 160 115" xmlns="http://www.w3.org/2000/svg"
             style="width:135px;height:100px;display:block;margin:0 auto;">
          <!-- Soft light blue circle glow -->
          <circle cx="80" cy="56" r="44" fill="#DBEAFE"/>

          <!-- Laptop screen frame -->
          <rect x="44" y="32" width="72" height="52" rx="7" fill="#FFFFFF" stroke="#2563EB" stroke-width="2.5"/>

          <!-- Laptop base -->
          <path d="M35,84 L125,84 C127,84 128,86 127,88 L122,92 L38,92 L33,88 C32,86 33,84 35,84 Z" fill="#2563EB"/>

          <!-- Big question mark in center -->
          <text x="80" y="66" font-family="system-ui, -apple-system, sans-serif" font-size="28" font-weight="800" fill="#2563EB" text-anchor="middle">?</text>

          <!-- Star badge on top-left of screen -->
          <circle cx="56" cy="30" r="8" fill="#3B82F6" stroke="#FFFFFF" stroke-width="1.5"/>
          <path d="M56,25.5 L57.2,28.5 L60.2,28.8 L57.9,30.8 L58.6,33.8 L56,32.2 L53.4,33.8 L54.1,30.8 L51.8,28.8 L54.8,28.5 Z" fill="#FFFFFF"/>

          <!-- Small circular bubble on top-right -->
          <circle cx="106" cy="28" r="5" fill="#60A5FA" opacity="0.85"/>
          <circle cx="114" cy="20" r="3" fill="#93C5FD"/>
        </svg>
        """
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top Bar (TVS Logo top-left)
# ─────────────────────────────────────────────────────────────────────────────

def _top_bar() -> rx.Component:
    """TVS Logo positioned at top-left."""
    return rx.hstack(
        rx.image(
            src="/tvs_logo.png",
            alt="TVS Motor Company",
            height=_bp(initial="32px", sm="36px", md="40px"),
            object_fit="contain",
        ),
        width="100%",
        justify_content="flex-start",
        align_items="center",
        padding_top=_bp(initial="1rem", md="1.25rem"),
        padding_x=_bp(initial="1.5rem", sm="2.5rem", md="4rem"),
        z_index="1",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Centered Hero Header
# ─────────────────────────────────────────────────────────────────────────────

def _hero_header() -> rx.Component:
    """
    Centered heading:
    - Red 'WELCOME TO'
    - 'Gen AI Hybrid Evaluator' (Evaluator in red)
    - Subtitle
    """
    return rx.vstack(
        rx.text(
            "WELCOME TO",
            font_family=FONT_BODY,
            font_size=_bp(initial="0.75rem", md="0.825rem"),
            font_weight="700",
            letter_spacing="0.25em",
            color="#E11D48",
            text_align="center",
        ),
        rx.heading(
            rx.text("Gen AI Hybrid ", as_="span", color="#0F172A"),
            rx.text("Evaluator", as_="span", color="#E11D48"),
            font_family=FONT_DISPLAY,
            font_size=_bp(initial="1.85rem", sm="2.4rem", md="3.15rem"),
            font_weight="800",
            letter_spacing="-0.025em",
            line_height="1.15",
            text_align="center",
        ),
        rx.text(
            "An intelligent evaluation platform by TVS Motor Company,",
            rx.html("<br/>"),
            "combining AI insights with human expertise.",
            font_family=FONT_BODY,
            font_size=_bp(initial="0.85rem", sm="0.925rem", md="0.975rem"),
            color="#64748B",
            line_height="1.5",
            text_align="center",
            max_width="620px",
        ),
        spacing="2",
        align_items="center",
        justify_content="center",
        width="100%",
        padding_x="1rem",
        margin_top=_bp(initial="0.5rem", md="0.75rem"),
        margin_bottom=_bp(initial="1.25rem", md="1.75rem"),
        z_index="1",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Role Card Component
# ─────────────────────────────────────────────────────────────────────────────

def _role_card(
    illustration: rx.Component,
    pastel_bg: str,
    badge_icon: str,
    badge_label: str,
    badge_color: str,
    badge_bg: str,
    badge_border: str,
    title: str,
    description: str,
    button_label: str,
    button_color: str,
    button_hover_color: str,
    button_shadow_color: str,
    target_route: str,
) -> rx.Component:
    """Individual rounded role card matching reference design."""
    return rx.box(
        rx.vstack(
            # Top Pastel Illustration Banner
            rx.box(
                illustration,
                background=pastel_bg,
                border_radius="16px",
                width="100%",
                height="140px",
                display="flex",
                align_items="center",
                justify_content="center",
                overflow="hidden",
            ),

            # Card Body
            rx.vstack(
                # Role Pill Badge
                rx.hstack(
                    rx.icon(badge_icon, size=13, color=badge_color),
                    rx.text(
                        badge_label,
                        font_family=FONT_BODY,
                        font_size="0.675rem",
                        font_weight="700",
                        letter_spacing="0.06em",
                        color=badge_color,
                    ),
                    background=badge_bg,
                    border=f"1px solid {badge_border}",
                    padding="0.25rem 0.75rem",
                    border_radius="999px",
                    spacing="1",
                    align_items="center",
                    justify_content="center",
                ),

                # Role Title
                rx.text(
                    title,
                    font_family=FONT_DISPLAY,
                    font_size="1.45rem",
                    font_weight="800",
                    color="#0F172A",
                    letter_spacing="-0.015em",
                ),

                # Role Description
                rx.text(
                    description,
                    font_family=FONT_BODY,
                    font_size="0.825rem",
                    color="#64748B",
                    text_align="center",
                    line_height="1.55",
                    padding_x="0.25rem",
                    min_height="52px",
                ),

                # Full-Width Button with Arrow
                rx.button(
                    rx.hstack(
                        rx.text(button_label, font_family=FONT_BODY, font_weight="600", font_size="0.925rem"),
                        rx.icon("arrow-right", size=16),
                        spacing="2",
                        align_items="center",
                        justify_content="center",
                        width="100%",
                    ),
                    on_click=rx.redirect(target_route),
                    background=button_color,
                    color="#FFFFFF",
                    width="100%",
                    height="46px",
                    border_radius="12px",
                    border="none",
                    cursor="pointer",
                    box_shadow=f"0 4px 14px {button_shadow_color}",
                    transition="all 0.18s ease-in-out",
                    _hover={
                        "background": button_hover_color,
                        "transform": "translateY(-1px)",
                        "box_shadow": f"0 6px 18px {button_shadow_color}",
                    },
                    _active={"transform": "translateY(0)"},
                ),

                spacing="3",
                align_items="center",
                justify_content="space-between",
                width="100%",
                padding_top="0.75rem",
                padding_x="0.5rem",
                flex="1",
            ),

            spacing="2",
            align_items="center",
            width="100%",
            height="100%",
        ),
        background="#FFFFFF",
        border="1px solid #E2E8F0",
        border_radius="24px",
        padding="1rem",
        box_shadow="0 10px 30px -4px rgba(15, 23, 42, 0.06), 0 4px 12px -2px rgba(15, 23, 42, 0.03)",
        width=_bp(initial="100%", sm="330px", md="335px", lg="345px"),
        max_width="360px",
        flex="1",
        transition="all 0.2s ease-in-out",
        _hover={
            "transform": "translateY(-3px)",
            "box_shadow": "0 16px 36px -6px rgba(15, 23, 42, 0.10), 0 6px 16px -2px rgba(15, 23, 42, 0.04)",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# Three Role Cards Row
# ─────────────────────────────────────────────────────────────────────────────

def _role_cards_container() -> rx.Component:
    """Three side-by-side role cards."""
    return rx.flex(
        # 1. Admin (Purple)
        _role_card(
            illustration=_admin_illustration(),
            pastel_bg="#F5F3FF",
            badge_icon="shield",
            badge_label="ADMINISTRATOR",
            badge_color="#7C3AED",
            badge_bg="#F5F3FF",
            badge_border="#DDD6FE",
            title="Admin",
            description="Manage the entire evaluation ecosystem — configure assessments, oversee facilitators, and analyse comprehensive reports.",
            button_label="Enter as Admin",
            button_color="#6D28D9",
            button_hover_color="#5B21B6",
            button_shadow_color="rgba(109, 40, 217, 0.28)",
            target_route="/signin",
        ),

        # 2. Facilitator (Green)
        _role_card(
            illustration=_facilitator_illustration(),
            pastel_bg="#F0FDF4",
            badge_icon="clipboard-list",
            badge_label="EVALUATOR",
            badge_color="#059669",
            badge_bg="#F0FDF4",
            badge_border="#BBF7D0",
            title="Facilitator",
            description="Conduct and oversee assessments, manage candidate sessions, and provide expert human evaluation feedback.",
            button_label="Enter as Facilitator",
            button_color="#059669",
            button_hover_color="#047857",
            button_shadow_color="rgba(5, 150, 105, 0.28)",
            target_route="/facilitator/signin",
        ),

        # 3. Candidate (Blue)
        _role_card(
            illustration=_candidate_illustration(),
            pastel_bg="#EFF6FF",
            badge_icon="user",
            badge_label="TEST TAKER",
            badge_color="#1D4ED8",
            badge_bg="#EFF6FF",
            badge_border="#BFDBFE",
            title="Candidate",
            description="Take your assigned assessments in a secure environment and track your results and performance analytics.",
            button_label="Enter as Candidate",
            button_color="#0066FF",
            button_hover_color="#0052CC",
            button_shadow_color="rgba(0, 102, 255, 0.28)",
            target_route="/candidate/login",
        ),

        direction=_bp(initial="column", md="row"),
        gap=_bp(initial="1.25rem", lg="1.75rem"),
        align_items="center",
        justify_content="center",
        width="100%",
        max_width="1140px",
        margin="0 auto",
        padding_x="1rem",
        z_index="1",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Page Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def home_page() -> rx.Component:
    """
    Gen AI Hybrid Evaluator role-selection home page.
    Single screen layout matching the reference screenshot.
    """
    return rx.box(
        _wave_background(),
        _top_bar(),
        rx.vstack(
            _hero_header(),
            _role_cards_container(),
            width="100%",
            align_items="center",
            justify_content="center",
            flex="1",
            z_index="1",
        ),
        background="#FFFFFF",
        min_height="100vh",
        width="100%",
        position="relative",
        overflow_x="hidden",
        display="flex",
        flex_direction="column",
        justify_content="flex-start",
        padding_bottom=_bp(initial="2rem", md="2.5rem"),
    )
