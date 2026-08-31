"""
Design tokens for the GenAI Hybrid Evaluator UI.
Enterprise light theme — Microsoft 365 / Google Workspace style.
Fixed for real contrast: dark ink text, visible borders, one consistent primary color.
"""

COLORS = {
    "canvas": "#F5F6FA",        # page background
    "surface": "#FFFFFF",       # cards, panels
    "ink": "#101828",           # primary text — strong, dark, readable
    "slate": "#475467",         # secondary text — readable, not washed out
    "placeholder": "#98A2B3",   # input placeholder text
    "line": "#D0D5DD",          # visible input/card borders
    "primary": "#4338CA",       # single indigo used everywhere (buttons + links)
    "primary_hover": "#362FA3",
    "primary_soft": "#EEF2FF",  # focus ring / tint background
    "success": "#027A48",
    "success_soft": "#ECFDF3",
    "danger": "#D92D20",
}

FONT_BODY = "'Inter', -apple-system, sans-serif"
FONT_DISPLAY = "'Inter', -apple-system, sans-serif"

FONT_STYLESHEETS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
]