"""PDF Report Generator Service for AI Hybrid Evaluator.

Contains:
- build_all_candidates_pdf_html: A4 portrait All Candidates Results Report
- build_individual_test_pdf_html: Individual candidate detailed test results
- generate_iframe_print_script: Client-side print via hidden iframe
"""

import html
import json
from datetime import datetime


def build_all_candidates_pdf_html(data: dict) -> str:
    """Generate standalone professional HTML document for All Candidates Results PDF.
    
    Reuses the exact design, components, typography, cards, and styles from Individual Candidate PDF.
    """
    assessment_name = html.escape(str(data.get("assessment_name", "Assessment")))
    selected_tests = data.get("selected_tests", [])
    selected_tests_str = html.escape(", ".join(selected_tests) if selected_tests else "All Tests")
    test_type = html.escape(str(data.get("test_type", "Formative")))
    pass_percentage = int(data.get("pass_percentage", 50))
    pass_mark_str = f"{pass_percentage}%"

    summary = data.get("summary", {})
    total_candidates = summary.get("total_candidates", 0)
    passed_count = summary.get("passed", 0)
    failed_count = summary.get("failed", 0)
    avg_score = html.escape(str(summary.get("avg_score", "0%")))

    candidates = data.get("candidates", [])
    co_items = data.get("co_items", [])
    lo_items = data.get("lo_items", [])
    kt_items = data.get("kt_items", [])
    domain_items = data.get("domain_items", [])
    rbt_items = data.get("rbt_items", [])
    questions = data.get("questions", [])

    # ── Dimension mini bar chart helper (exact component from Individual PDF) ──
    def render_dimension_bars(items, title, icon_symbol):
        if not items:
            return f"""
            <div class="mini-chart-card">
                <div class="mini-chart-header">
                    <span class="chart-icon">{icon_symbol}</span>
                    <span class="mini-chart-title">{html.escape(title)}</span>
                </div>
                <div class="empty-chart-note">No mapped data for this dimension in the selected test.</div>
            </div>
            """
        bars_html = []
        for it in items:
            name = html.escape(str(it.get("name", "")))
            try:
                sc = float(it.get("score", 0))
            except (ValueError, TypeError):
                sc = 0.0
            sc_int = int(round(sc))
            bar_color = "#4F46E5" if sc >= pass_percentage else "#EF4444"
            score_color = "#059669" if sc >= pass_percentage else "#DC2626"
            bar_height = max(4, min(100, sc_int))

            bars_html.append(f"""
            <div class="mini-bar-col">
                <span class="mini-score-label" style="color: {score_color};">{sc_int}%</span>
                <div class="mini-bar-track">
                    <div class="mini-pass-line" style="bottom: {pass_percentage}%;"></div>
                    <div class="mini-bar-fill" style="height: {bar_height}%; background: {bar_color};"></div>
                </div>
                <span class="mini-x-label" title="{name}">{name}</span>
            </div>
            """)

        joined_bars = "\n".join(bars_html)
        return f"""
        <div class="mini-chart-card">
            <div class="mini-chart-header">
                <span class="chart-icon">{icon_symbol}</span>
                <span class="mini-chart-title">{html.escape(title)}</span>
            </div>
            <div class="mini-bars-container">
                {joined_bars}
            </div>
        </div>
        """

    co_card = render_dimension_bars(co_items, "CO Performance", "🎯")
    lo_card = render_dimension_bars(lo_items, "LO Performance", "🎓")
    kt_card = render_dimension_bars(kt_items, "Knowledge Type Performance", "📖")
    domain_card = render_dimension_bars(domain_items, "Domain Performance", "🏢")
    rbt_card = render_dimension_bars(rbt_items, "RBT Level Performance", "🧠")

    # ── Question-wise Performance (exact component from Individual PDF) ──
    q_bars_html = []
    for i, q in enumerate(questions, 1):
        q_disp = html.escape(str(q.get("q_display", f"Q{i}")))
        try:
            pct_val = float(q.get("score_pct_num", 0))
        except (ValueError, TypeError):
            pct_val = 0.0
        pct_int = int(round(pct_val))
        q_pass = (pct_val >= pass_percentage)
        bar_color = "#4F46E5" if q_pass else "#EF4444"
        score_color = "#059669" if q_pass else "#DC2626"
        bar_height = max(4, min(100, pct_int))

        q_bars_html.append(f"""
        <div class="q-bar-col">
            <span class="q-score-label" style="color: {score_color};">{pct_int}%</span>
            <div class="q-bar-track">
                <div class="q-bar-fill" style="height: {bar_height}%; background: {bar_color};"></div>
            </div>
            <span class="q-x-label">{q_disp}</span>
        </div>
        """)

    q_bars_rendered = "\n".join(q_bars_html) if q_bars_html else '<div class="empty-chart-note">No question evaluation records available for the selected test.</div>'

    # ── Candidate-wise Performance Table Rows ──
    cand_rows_html = []
    for i, c in enumerate(candidates, 1):
        cid = html.escape(str(c.get("cand_id", "—")))
        cname = html.escape(str(c.get("cand_name", "—")))
        score_pct = c.get("score_pct", "Not Evaluated")
        marks_str = html.escape(str(c.get("marks_str", "—")))
        result = str(c.get("result", "Not Evaluated")).strip()
        evaluated = c.get("evaluated", False)

        if not evaluated:
            status_label = "Not Evaluated"
            status_color = "#64748B"
            status_bg = "#F1F5F9"
            status_border = "#E2E8F0"
            score_color = "#64748B"
            score_display = "Not Evaluated"
            marks_display = "—"
        else:
            is_pass = result.lower() in ("pass", "passed")
            status_label = "Pass" if is_pass else "Fail"
            status_color = "#059669" if is_pass else "#DC2626"
            status_bg = "#ECFDF5" if is_pass else "#FEF2F2"
            status_border = "#A7F3D0" if is_pass else "#FECACA"
            score_color = status_color
            score_display = html.escape(str(score_pct))
            marks_display = marks_str

        cand_rows_html.append(f"""
        <tr>
            <td class="td-center font-bold">{i}</td>
            <td class="td-center font-mono">{cid}</td>
            <td class="font-bold">{cname}</td>
            <td class="td-center font-bold" style="color: {score_color};">{score_display}</td>
            <td class="td-center font-bold">{marks_display}</td>
            <td class="td-center">
                <span class="status-pill" style="color: {status_color}; background: {status_bg}; border: 1px solid {status_border};">
                    {status_label}
                </span>
            </td>
        </tr>
        """)

    cand_table_rendered = "\n".join(cand_rows_html) if cand_rows_html else '<tr><td colspan="6" class="td-empty">No candidate records available.</td></tr>'

    test_type_badge = f'<span class="badge badge-{"purple" if test_type.lower() == "summative" else "blue"}">{test_type}</span>'

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Candidates Results Report - {assessment_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #0F172A;
            background: #FFFFFF;
            line-height: 1.45;
            font-size: 13px;
            padding: 24px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        
        @page {{
            size: A4;
            margin: 12mm 14mm;
        }}
        
        @media print {{
            body {{
                padding: 0;
                background: #FFFFFF;
            }}
            .no-print {{
                display: none !important;
            }}
            .page-break {{
                page-break-before: always;
            }}
        }}
        
        .no-break {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}
        
        .report-wrapper {{
            max-width: 900px;
            margin: 0 auto;
            background: #FFFFFF;
        }}
        
        /* ── Header ── */
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 14px;
            border-bottom: 1.5px solid #E2E8F0;
            margin-bottom: 18px;
        }}
        
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .header-logo {{
            height: 32px;
            width: auto;
            object-fit: contain;
        }}
        
        .brand-title {{
            font-size: 15px;
            font-weight: 800;
            color: #1E293B;
            letter-spacing: 0.04em;
        }}
        
        .brand-subtitle {{
            font-size: 11px;
            color: #64748B;
            font-weight: 500;
        }}
        
        .header-doc-tag {{
            font-size: 13px;
            font-weight: 700;
            color: #4F46E5;
            background: #EEF2FF;
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid #E0E7FF;
        }}
        
        /* ── Section Cards ── */
        .section-box {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 18px;
        }}
        
        .section-heading-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 14px;
            padding-bottom: 8px;
            border-bottom: 1px solid #F1F5F9;
        }}
        
        .section-num-pill {{
            background: #4F46E5;
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}
        
        .section-heading {{
            font-size: 14px;
            font-weight: 700;
            color: #0F172A;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        
        .section-subtext {{
            margin-left: auto;
            font-size: 11px;
            color: #64748B;
            font-weight: 500;
        }}
        
        /* ── 1. Details ── */
        .details-grid-3 {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}
        
        .detail-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
        }}
        
        .detail-label {{
            font-size: 10.5px;
            color: #64748B;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
        }}
        
        .detail-val {{
            font-size: 13px;
            color: #0F172A;
            font-weight: 600;
        }}
        
        .font-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        
        .badge-purple {{
            background: #F3E8FF;
            color: #7E22CE;
            border: 1px solid #E9D5FF;
        }}
        
        .badge-blue {{
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #DBEAFE;
        }}
        
        /* ── 2. Summary Statistics Grid ── */
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 14px;
        }}
        
        .result-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 16px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        
        .result-card.highlight {{
            background: #FAF5FF;
            border-color: #E9D5FF;
        }}
        
        .result-label {{
            font-size: 11px;
            font-weight: 600;
            color: #475467;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }}
        
        .result-score-val {{
            font-size: 26px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.1;
        }}
        
        .status-pill {{
            font-size: 12px;
            font-weight: 700;
            padding: 3px 12px;
            border-radius: 6px;
            display: inline-block;
        }}
        
        /* ── 3 & 4. Dimensions Layouts ── */
        .dimensions-grid-2 {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 12px;
        }}
        
        .mini-chart-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
            position: relative;
        }}
        
        .mini-chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        
        .chart-icon {{
            font-size: 13px;
            margin-right: 4px;
        }}
        
        .mini-chart-title {{
            font-size: 11.5px;
            font-weight: 700;
            color: #1E293B;
            flex: 1;
        }}
        
        .mini-pass-hint {{
            display: none;
        }}
        
        .mini-bars-container {{
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            height: 118px;
            padding-bottom: 46px;
            position: relative;
        }}
        
        .mini-bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            height: 100%;
            position: relative;
            flex: 1;
            min-width: 18px;
            overflow: visible;
        }}
        
        .mini-score-label {{
            font-size: 7.5px;
            font-weight: 700;
            color: inherit;
            white-space: nowrap;
            margin-bottom: 2px;
            line-height: 1;
        }}
        
        .mini-bar-track {{
            width: 60%;
            max-width: 28px;
            min-width: 14px;
            height: 62px;
            background: #E2E8F0;
            border-radius: 4px 4px 0 0;
            position: relative;
            display: flex;
            align-items: flex-end;
        }}
        
        .mini-bar-fill {{
            width: 100%;
            border-radius: 4px 4px 0 0;
            transition: height 0.2s ease;
        }}
        
        .mini-pass-line {{
            position: absolute;
            left: -4px;
            right: -4px;
            border-top: 1.5px dashed #EF4444;
            z-index: 2;
        }}
        
        .mini-x-label {{
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%) rotate(-40deg);
            transform-origin: top center;
            margin-top: 2px;
            font-size: 8.5px;
            font-weight: 600;
            color: #64748B;
            white-space: nowrap;
            text-align: left;
        }}
        
        .empty-chart-note {{
            font-size: 11px;
            color: #94A3B8;
            font-style: italic;
            text-align: center;
            padding: 24px 8px;
        }}
        
        /* ── Question-wise Chart ── */
        .qwise-chart-wrapper {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px 14px;
        }}
        
        .qwise-chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        
        .qwise-title {{
            font-size: 12px;
            font-weight: 700;
            color: #1E293B;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .qwise-legend {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 10.5px;
            font-weight: 600;
            color: #DC2626;
        }}
        
        .legend-dashed-line {{
            width: 18px;
            height: 0px;
            border-top: 1.5px dashed #EF4444;
            display: inline-block;
        }}
        
        .qwise-canvas {{
            display: flex;
            align-items: flex-end;
            height: 120px;
            position: relative;
            border-left: 1px solid #CBD5E1;
            border-bottom: 1px solid #CBD5E1;
            margin-left: 38px;
            margin-bottom: 22px;
            padding: 0 8px;
        }}
        
        .qwise-y-axis {{
            position: absolute;
            left: -38px;
            top: 0;
            bottom: 0;
            width: 32px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: flex-end;
            padding-right: 4px;
            font-size: 9px;
            font-weight: 500;
            color: #94A3B8;
        }}
        
        .qwise-gridline-100 {{
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            border-top: 1px dashed #E2E8F0;
            z-index: 1;
        }}
        
        .qwise-gridline-50 {{
            position: absolute;
            left: 0;
            right: 0;
            top: 50%;
            border-top: 1px dashed #E2E8F0;
            z-index: 1;
        }}
        
        .qwise-pass-line {{
            position: absolute;
            left: 0;
            right: 0;
            border-top: 1.5px dashed #EF4444;
            z-index: 2;
        }}
        
        .q-bars-row {{
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            width: 100%;
            height: 100%;
            z-index: 3;
            position: relative;
        }}
        
        .q-bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            position: relative;
            flex: 1;
            max-width: 48px;
            min-width: 22px;
            height: 100%;
        }}
        
        .q-score-label {{
            font-size: 9.5px;
            font-weight: 700;
            margin-bottom: 3px;
            white-space: nowrap;
        }}
        
        .q-bar-track {{
            width: 58%;
            max-width: 34px;
            min-width: 14px;
            height: 100%;
            display: flex;
            align-items: flex-end;
            position: relative;
            background: #E2E8F0;
            border-radius: 4px 4px 0 0;
        }}
        
        .q-bar-fill {{
            width: 100%;
            border-radius: 4px 4px 0 0;
        }}
        
        .q-x-label {{
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-top: 4px;
            font-size: 10px;
            font-weight: 700;
            color: #64748B;
            white-space: nowrap;
        }}
        
        /* ── Table ── */
        .q-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-top: 4px;
        }}
        
        .q-table th {{
            background: #F1F5F9;
            color: #475467;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.03em;
            padding: 8px 10px;
            border-top: 1px solid #E2E8F0;
            border-bottom: 1px solid #CBD5E1;
            text-align: left;
        }}
        
        .q-table td {{
            padding: 9px 10px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: top;
            color: #1E293B;
            line-height: 1.4;
        }}
        
        .q-table tbody tr:nth-child(even) {{
            background: #F8FAFC;
        }}
        
        .td-center {{
            text-align: center !important;
        }}
        
        .font-bold {{
            font-weight: 700;
        }}
        
        .font-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        
        .text-muted {{
            color: #64748B;
        }}
        
        .td-empty {{
            text-align: center;
            padding: 20px;
            color: #94A3B8;
            font-style: italic;
        }}
        
        /* ── Document Footer ── */
        .report-footer {{
            margin-top: 16px;
            padding-top: 10px;
            border-top: 1px solid #E2E8F0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 10px;
            color: #94A3B8;
        }}
    </style>
</head>
<body>
    <div class="report-wrapper">
        <!-- Document Branding Header (Exact same as Individual Candidate PDF) -->
        <div class="header-container no-break">
            <div class="header-brand">
                <img src="/tvs_logo.png" alt="TVS Motor Logo" class="header-logo" onerror="this.style.display='none'" />
                <div>
                    <div class="brand-title">TVS MOTOR COMPANY</div>
                    <div class="brand-subtitle">GEN AI HYBRID EVALUATOR</div>
                </div>
            </div>
            <div class="header-doc-tag">
                Evaluation Report
            </div>
        </div>

        <!-- 1. ASSESSMENT & TEST DETAILS -->
        <div class="section-box no-break">
            <div class="section-heading-row">
                <span class="section-num-pill">1</span>
                <span class="section-heading">Assessment &amp; Test Details</span>
            </div>
            <div class="details-grid-3">
                <div class="detail-card">
                    <div class="detail-label">Assessment Name</div>
                    <div class="detail-val">{assessment_name}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-label">Selected Test(s)</div>
                    <div class="detail-val">{selected_tests_str}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-label">Test Type</div>
                    <div class="detail-val">{test_type_badge}</div>
                </div>
            </div>
        </div>

        <!-- 2. SUMMARY STATISTICS -->
        <div class="section-box no-break">
            <div class="section-heading-row">
                <span class="section-num-pill">2</span>
                <span class="section-heading">Summary Statistics</span>
            </div>
            <div class="summary-grid">
                <div class="result-card">
                    <div class="result-label">Total Candidates</div>
                    <div class="result-score-val">{total_candidates}</div>
                </div>
                <div class="result-card">
                    <div class="result-label">Passed</div>
                    <div class="result-score-val" style="color: #059669;">{passed_count}</div>
                </div>
                <div class="result-card">
                    <div class="result-label">Failed</div>
                    <div class="result-score-val" style="color: #DC2626;">{failed_count}</div>
                </div>
                <div class="result-card highlight">
                    <div class="result-label">Average Score</div>
                    <div class="result-score-val" style="color: #4F46E5;">{avg_score}</div>
                </div>
            </div>
        </div>

        <!-- 3. CANDIDATE-WISE PERFORMANCE -->
        <div class="section-box">
            <div class="section-heading-row no-break">
                <span class="section-num-pill">3</span>
                <span class="section-heading">Candidate-wise Performance</span>
            </div>
            <table class="q-table">
                <thead>
                    <tr>
                        <th style="width: 50px; text-align: center;">#</th>
                        <th style="width: 140px; text-align: center;">Candidate ID</th>
                        <th>Candidate Name</th>
                        <th style="width: 110px; text-align: center;">Score (%)</th>
                        <th style="width: 170px; text-align: center;">Marks Obtained / Max Marks</th>
                        <th style="width: 120px; text-align: center;">Result</th>
                    </tr>
                </thead>
                <tbody>
                    {cand_table_rendered}
                </tbody>
            </table>
        </div>

        <!-- 4. PERFORMANCE ANALYSIS (Contains ALL 6 Visualizations) -->
        <div class="section-box">
            <div class="section-heading-row no-break">
                <span class="section-num-pill">4</span>
                <span class="section-heading">Performance Analysis</span>
                <span class="section-subtext">All scores in percentage (%)</span>
            </div>

            <!-- Row 1: CO + LO -->
            <div class="dimensions-grid-2 no-break">
                {co_card}
                {lo_card}
            </div>

            <!-- Row 2: Knowledge Type + Domain -->
            <div class="dimensions-grid-2 no-break">
                {kt_card}
                {domain_card}
            </div>

            <!-- Row 3: RBT Level full width -->
            <div class="no-break" style="margin-bottom: 14px;">
                {rbt_card}
            </div>

            <!-- Row 4: Question-wise full width -->
            <div class="qwise-chart-wrapper no-break">
                <div class="qwise-chart-header">
                    <div class="qwise-title">
                        <span>📊</span> Question-wise Performance
                    </div>
                    <div class="qwise-legend">
                        <span class="legend-dashed-line"></span>
                        <span>{pass_mark_str} Pass Mark</span>
                    </div>
                </div>
                <div class="qwise-canvas">
                    <div class="qwise-y-axis">
                        <span>100%</span>
                        <span>50%</span>
                        <span>0%</span>
                    </div>
                    <div class="qwise-gridline-100"></div>
                    <div class="qwise-gridline-50"></div>
                    <div class="qwise-pass-line" style="bottom: {pass_percentage}%;"></div>
                    <div class="q-bars-row">
                        {q_bars_rendered}
                    </div>
                </div>
            </div>
        </div>

        <!-- Document Footer -->
        <div class="report-footer no-break">
            <span>TVS Motor Company • Confidential Assessment Record</span>
            <span>Generated via Gen AI Hybrid Evaluator</span>
        </div>
    </div>
</body>
</html>
"""
    return html_template


def build_individual_test_pdf_html(data: dict) -> str:
    """Generate standalone professional HTML document for candidate test results PDF."""

    assessment_name = html.escape(str(data.get("assessment_name", "Assessment")))
    test_type = html.escape(str(data.get("test_type", "Formative")))
    candidate_name = html.escape(str(data.get("candidate_name", "Candidate")))
    candidate_id = html.escape(str(data.get("candidate_id", "—")))
    
    score = html.escape(str(data.get("score", "0%")))
    marks_str = html.escape(str(data.get("marks_obtained_str", "—")))
    pass_status = str(data.get("pass_status", "Fail")).strip()
    is_passed = (pass_status.lower() in ("pass", "passed"))
    status_label = "Pass" if is_passed else "Fail"
    status_color = "#059669" if is_passed else "#DC2626"
    status_bg = "#ECFDF5" if is_passed else "#FEF2F2"
    status_border = "#A7F3D0" if is_passed else "#FECACA"

    pass_percentage = int(data.get("pass_percentage", 50))
    pass_mark_str = f"{pass_percentage}%"

    co_items = data.get("co_items", [])
    lo_items = data.get("lo_items", [])
    kt_items = data.get("kt_items", [])
    domain_items = data.get("domain_items", [])
    rbt_items = data.get("rbt_items", [])
    questions = data.get("questions", [])

    def render_dimension_bars(items, title, icon_symbol):
        if not items:
            return f"""
            <div class="mini-chart-card">
                <div class="mini-chart-header">
                    <span class="chart-icon">{icon_symbol}</span>
                    <span class="mini-chart-title">{html.escape(title)}</span>
                </div>
                <div class="empty-chart-note">No mapped data for this dimension in the selected test.</div>
            </div>
            """
        bars_html = []
        for it in items:
            name = html.escape(str(it.get("name", "")))
            try:
                sc = float(it.get("score", 0))
            except (ValueError, TypeError):
                sc = 0.0
            sc_int = int(round(sc))
            bar_color = "#4F46E5" if sc >= pass_percentage else "#EF4444"
            score_color = "#059669" if sc >= pass_percentage else "#DC2626"
            bar_height = max(4, min(100, sc_int))

            bars_html.append(f"""
            <div class="mini-bar-col">
                <span class="mini-score-label" style="color: {score_color};">{sc_int}%</span>
                <div class="mini-bar-track">
                    <div class="mini-pass-line" style="bottom: {pass_percentage}%;"></div>
                    <div class="mini-bar-fill" style="height: {bar_height}%; background: {bar_color};"></div>
                </div>
                <span class="mini-x-label" title="{name}">{name}</span>
            </div>
            """)

        joined_bars = "\n".join(bars_html)
        return f"""
        <div class="mini-chart-card">
            <div class="mini-chart-header">
                <span class="chart-icon">{icon_symbol}</span>
                <span class="mini-chart-title">{html.escape(title)}</span>
            </div>
            <div class="mini-bars-container">
                {joined_bars}
            </div>
        </div>
        """

    co_card = render_dimension_bars(co_items, "CO Performance", "🎯")
    lo_card = render_dimension_bars(lo_items, "LO Performance", "🎓")
    kt_card = render_dimension_bars(kt_items, "Knowledge Type Performance", "📖")
    domain_card = render_dimension_bars(domain_items, "Domain Performance", "🏢")
    rbt_card = render_dimension_bars(rbt_items, "RBT Level Performance", "🧠")

    # ── Question-wise Visualization (6th Visualization) ──
    q_bars_html = []
    for i, q in enumerate(questions, 1):
        q_disp = html.escape(str(q.get("q_display", f"Q{i}")))
        try:
            pct_val = float(q.get("score_pct_num", 0))
        except (ValueError, TypeError):
            pct_val = 0.0
        pct_int = int(round(pct_val))
        q_pass = (pct_val >= pass_percentage)
        bar_color = "#4F46E5" if q_pass else "#EF4444"
        score_color = "#059669" if q_pass else "#DC2626"
        bar_height = max(4, min(100, pct_int))

        q_bars_html.append(f"""
        <div class="q-bar-col">
            <span class="q-score-label" style="color: {score_color};">{pct_int}%</span>
            <div class="q-bar-track">
                <div class="q-bar-fill" style="height: {bar_height}%; background: {bar_color};"></div>
            </div>
            <span class="q-x-label">{q_disp}</span>
        </div>
        """)

    q_bars_rendered = "\n".join(q_bars_html) if q_bars_html else '<div class="empty-chart-note">No question evaluation records available for the selected test.</div>'

    # ── Question-wise Detailed Table ──
    table_rows_html = []
    for i, q in enumerate(questions, 1):
        q_disp = html.escape(str(q.get("q_display", f"Q{i}")))
        q_text = html.escape(str(q.get("question", f"Question {i}")))
        m_obt = html.escape(str(q.get("marks_obtained", "0")))
        m_max = html.escape(str(q.get("max_marks", "0")))
        s_pct = html.escape(str(q.get("score_pct", "0%")))
        try:
            pct_val = float(q.get("score_pct_num", 0))
        except (ValueError, TypeError):
            pct_val = 0.0
        pct_color = "#059669" if pct_val >= pass_percentage else "#DC2626"
        just = html.escape(str(q.get("justification", "—")))

        table_rows_html.append(f"""
        <tr>
            <td class="td-center font-bold">{q_disp}</td>
            <td class="td-question">{q_text}</td>
            <td class="td-center font-bold">{m_obt}</td>
            <td class="td-center text-muted">{m_max}</td>
            <td class="td-center font-bold" style="color: {pct_color};">{s_pct}</td>
            <td class="td-justification">{just}</td>
        </tr>
        """)

    table_rows_rendered = "\n".join(table_rows_html) if table_rows_html else '<tr><td colspan="6" class="td-empty">No question evaluation records available.</td></tr>'

    test_type_badge = f'<span class="badge badge-{"purple" if test_type.lower() == "summative" else "blue"}">{test_type}</span>'

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{candidate_name} - {assessment_name} - {test_type} Results</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #0F172A;
            background: #FFFFFF;
            line-height: 1.45;
            font-size: 13px;
            padding: 24px;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        
        @page {{
            size: A4;
            margin: 12mm 14mm;
        }}
        
        @media print {{
            body {{
                padding: 0;
                background: #FFFFFF;
            }}
            .no-print {{
                display: none !important;
            }}
            .page-break {{
                page-break-before: always;
            }}
        }}
        
        .no-break {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}
        
        .report-wrapper {{
            max-width: 900px;
            margin: 0 auto;
            background: #FFFFFF;
        }}
        
        /* ── Header ── */
        .header-container {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 14px;
            border-bottom: 1.5px solid #E2E8F0;
            margin-bottom: 18px;
        }}
        
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .header-logo {{
            height: 32px;
            width: auto;
            object-fit: contain;
        }}
        
        .brand-title {{
            font-size: 15px;
            font-weight: 800;
            color: #1E293B;
            letter-spacing: 0.04em;
        }}
        
        .brand-subtitle {{
            font-size: 11px;
            color: #64748B;
            font-weight: 500;
        }}
        
        .header-doc-tag {{
            font-size: 13px;
            font-weight: 700;
            color: #4F46E5;
            background: #EEF2FF;
            padding: 5px 12px;
            border-radius: 6px;
            border: 1px solid #E0E7FF;
        }}
        
        /* ── Section Cards ── */
        .section-box {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
            padding: 16px 18px;
            margin-bottom: 18px;
        }}
        
        .section-heading-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 14px;
            padding-bottom: 8px;
            border-bottom: 1px solid #F1F5F9;
        }}
        
        .section-num-pill {{
            background: #4F46E5;
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }}
        
        .section-heading {{
            font-size: 14px;
            font-weight: 700;
            color: #0F172A;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        
        .section-subtext {{
            margin-left: auto;
            font-size: 11px;
            color: #64748B;
            font-weight: 500;
        }}
        
        /* ── 1. Test Details ── */
        .details-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}
        
        .detail-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
        }}
        
        .detail-label {{
            font-size: 10.5px;
            color: #64748B;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 4px;
        }}
        
        .detail-val {{
            font-size: 13px;
            color: #0F172A;
            font-weight: 600;
        }}
        
        .font-mono {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        
        .badge {{
            display: inline-flex;
            align-items: center;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }}
        
        .badge-purple {{
            background: #F3E8FF;
            color: #7E22CE;
            border: 1px solid #E9D5FF;
        }}
        
        .badge-blue {{
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #DBEAFE;
        }}
        
        /* ── 2. Test Result ── */
        .result-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }}
        
        .result-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 14px 16px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        
        .result-card.highlight {{
            background: #FAF5FF;
            border-color: #E9D5FF;
        }}
        
        .result-label {{
            font-size: 11px;
            font-weight: 600;
            color: #475467;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 6px;
        }}
        
        .result-score-val {{
            font-size: 26px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.1;
        }}
        
        .result-marks-val {{
            font-size: 22px;
            font-weight: 800;
            color: #4F46E5;
            line-height: 1.1;
        }}
        
        .status-pill {{
            font-size: 13px;
            font-weight: 700;
            padding: 4px 16px;
            border-radius: 6px;
            display: inline-block;
        }}
        
        /* ── 3. Performance Analysis ── */
        .perf-subheading {{
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .dimensions-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }}
        
        .dimensions-grid-bottom {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 18px;
        }}
        
        .mini-chart-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 10px 12px;
            position: relative;
        }}
        
        .mini-chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        
        .chart-icon {{
            font-size: 13px;
            margin-right: 4px;
        }}
        
        .mini-chart-title {{
            font-size: 11.5px;
            font-weight: 700;
            color: #1E293B;
            flex: 1;
        }}
        
        .mini-pass-hint {{
            display: none;
        }}
        
        .mini-bars-container {{
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            height: 118px;
            padding-bottom: 46px;
            position: relative;
        }}
        
        .mini-bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            height: 100%;
            position: relative;
            flex: 1;
            min-width: 18px;
            overflow: visible;
        }}
        
        .mini-score-label {{
            font-size: 7.5px;
            font-weight: 700;
            color: inherit;
            white-space: nowrap;
            margin-bottom: 2px;
            line-height: 1;
        }}
        
        .mini-bar-track {{
            width: 60%;
            max-width: 28px;
            min-width: 14px;
            height: 62px;
            background: #E2E8F0;
            border-radius: 4px 4px 0 0;
            position: relative;
            display: flex;
            align-items: flex-end;
        }}
        
        .mini-bar-fill {{
            width: 100%;
            border-radius: 4px 4px 0 0;
            transition: height 0.2s ease;
        }}
        
        .mini-pass-line {{
            position: absolute;
            left: -4px;
            right: -4px;
            border-top: 1.5px dashed #EF4444;
            z-index: 2;
        }}
        
        .mini-x-label {{
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%) rotate(-40deg);
            transform-origin: top center;
            margin-top: 2px;
            font-size: 8.5px;
            font-weight: 600;
            color: #64748B;
            white-space: nowrap;
            text-align: left;
        }}
        
        .empty-chart-note {{
            font-size: 11px;
            color: #94A3B8;
            font-style: italic;
            text-align: center;
            padding: 24px 8px;
        }}
        
        /* ── Question-wise Chart (Inside Performance Analysis) ── */
        .qwise-chart-wrapper {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            padding: 12px 14px;
        }}
        
        .qwise-chart-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        
        .qwise-title {{
            font-size: 12px;
            font-weight: 700;
            color: #1E293B;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .qwise-legend {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 10.5px;
            font-weight: 600;
            color: #DC2626;
        }}
        
        .legend-dashed-line {{
            width: 18px;
            height: 0px;
            border-top: 1.5px dashed #EF4444;
            display: inline-block;
        }}
        
        .qwise-canvas {{
            display: flex;
            align-items: flex-end;
            height: 120px;
            position: relative;
            border-left: 1px solid #CBD5E1;
            border-bottom: 1px solid #CBD5E1;
            margin-left: 38px;
            margin-bottom: 22px;
            padding: 0 8px;
        }}
        
        .qwise-y-axis {{
            position: absolute;
            left: -38px;
            top: 0;
            bottom: 0;
            width: 32px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: flex-end;
            padding-right: 4px;
            font-size: 9px;
            font-weight: 500;
            color: #94A3B8;
        }}
        
        .qwise-gridline-100 {{
            position: absolute;
            left: 0;
            right: 0;
            top: 0;
            border-top: 1px dashed #E2E8F0;
            z-index: 1;
        }}
        
        .qwise-gridline-50 {{
            position: absolute;
            left: 0;
            right: 0;
            top: 50%;
            border-top: 1px dashed #E2E8F0;
            z-index: 1;
        }}
        
        .qwise-pass-line {{
            position: absolute;
            left: 0;
            right: 0;
            border-top: 1.5px dashed #EF4444;
            z-index: 2;
        }}
        
        .q-bars-row {{
            display: flex;
            align-items: flex-end;
            justify-content: space-around;
            width: 100%;
            height: 100%;
            z-index: 3;
            position: relative;
        }}
        
        .q-bar-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-end;
            position: relative;
            flex: 1;
            max-width: 48px;
            min-width: 22px;
            height: 100%;
        }}
        
        .q-score-label {{
            font-size: 9.5px;
            font-weight: 700;
            margin-bottom: 3px;
            white-space: nowrap;
        }}
        
        .q-bar-track {{
            width: 58%;
            max-width: 34px;
            min-width: 14px;
            height: 100%;
            display: flex;
            align-items: flex-end;
            position: relative;
            background: #E2E8F0;
            border-radius: 4px 4px 0 0;
        }}
        
        .q-bar-fill {{
            width: 100%;
            border-radius: 4px 4px 0 0;
        }}
        
        .q-x-label {{
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            margin-top: 4px;
            font-size: 10px;
            font-weight: 700;
            color: #64748B;
            white-space: nowrap;
        }}
        
        /* ── 4. Question-wise Detailed Table ── */
        .q-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
            margin-top: 4px;
        }}
        
        .q-table th {{
            background: #F1F5F9;
            color: #475467;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.03em;
            padding: 8px 10px;
            border-top: 1px solid #E2E8F0;
            border-bottom: 1px solid #CBD5E1;
            text-align: left;
        }}
        
        .q-table td {{
            padding: 9px 10px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: top;
            color: #1E293B;
            line-height: 1.4;
        }}
        
        .q-table tbody tr:nth-child(even) {{
            background: #F8FAFC;
        }}
        
        .td-center {{
            text-align: center !important;
        }}
        
        .font-bold {{
            font-weight: 700;
        }}
        
        .text-muted {{
            color: #64748B;
        }}
        
        .td-question {{
            min-width: 160px;
            color: #0F172A;
            font-weight: 500;
        }}
        
        .td-justification {{
            min-width: 220px;
            color: #334155;
            font-size: 11px;
        }}
        
        .td-empty {{
            text-align: center;
            padding: 20px;
            color: #94A3B8;
            font-style: italic;
        }}
        
        /* ── Document Footer ── */
        .report-footer {{
            margin-top: 16px;
            padding-top: 10px;
            border-top: 1px solid #E2E8F0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 10px;
            color: #94A3B8;
        }}
    </style>
</head>
<body>
    <div class="report-wrapper">
        <!-- Document Branding Header -->
        <div class="header-container no-break">
            <div class="header-brand">
                <img src="/tvs_logo.png" alt="TVS Motor Logo" class="header-logo" onerror="this.style.display='none'" />
                <div>
                    <div class="brand-title">TVS MOTOR COMPANY</div>
                    <div class="brand-subtitle">GEN AI HYBRID EVALUATOR</div>
                </div>
            </div>
            <div class="header-doc-tag">
                Evaluation Report
            </div>
        </div>

        <!-- 1. TEST DETAILS -->
        <div class="section-box no-break">
            <div class="section-heading-row">
                <span class="section-num-pill">1</span>
                <span class="section-heading">Test Details</span>
            </div>
            <div class="details-grid">
                <div class="detail-card">
                    <div class="detail-label">Assessment Name</div>
                    <div class="detail-val">{assessment_name}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-label">Test Type</div>
                    <div class="detail-val">{test_type_badge}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-label">Candidate Name</div>
                    <div class="detail-val">{candidate_name}</div>
                </div>
                <div class="detail-card">
                    <div class="detail-label">Candidate ID</div>
                    <div class="detail-val font-mono">{candidate_id}</div>
                </div>
            </div>
        </div>

        <!-- 2. TEST RESULT -->
        <div class="section-box no-break">
            <div class="section-heading-row">
                <span class="section-num-pill">2</span>
                <span class="section-heading">Test Result</span>
            </div>
            <div class="result-grid">
                <div class="result-card highlight">
                    <div class="result-label">Score</div>
                    <div class="result-score-val" style="color: {status_color};">{score}</div>
                </div>
                <div class="result-card">
                    <div class="result-label">Marks Obtained / Maximum Marks</div>
                    <div class="result-marks-val">{marks_str}</div>
                </div>
                <div class="result-card">
                    <div class="result-label">Pass / Fail Status</div>
                    <div>
                        <span class="status-pill" style="color: {status_color}; background: {status_bg}; border: 1px solid {status_border};">
                            {status_label}
                        </span>
                    </div>
                </div>
            </div>
        </div>

        <!-- 3. PERFORMANCE ANALYSIS (Contains ALL 6 Visualizations) -->
        <div class="section-box">
            <div class="section-heading-row no-break">
                <span class="section-num-pill">3</span>
                <span class="section-heading">Performance Analysis</span>
                <span class="section-subtext">All scores in percentage (%)</span>
            </div>

            <!-- Visualizations 1, 2, 3: CO, LO, Knowledge Type -->
            <div class="dimensions-grid no-break">
                {co_card}
                {lo_card}
                {kt_card}
            </div>

            <!-- Visualizations 4, 5: Domain, RBT Level -->
            <div class="dimensions-grid-bottom no-break">
                {domain_card}
                {rbt_card}
            </div>

            <!-- Visualization 6: Question-wise Performance -->
            <div class="qwise-chart-wrapper no-break">
                <div class="qwise-chart-header">
                    <div class="qwise-title">
                        <span>📊</span> Question-wise Performance
                    </div>
                    <div class="qwise-legend">
                        <span class="legend-dashed-line"></span>
                        <span>{pass_mark_str} Pass Mark</span>
                    </div>
                </div>
                <div class="qwise-canvas">
                    <div class="qwise-y-axis">
                        <span>100%</span>
                        <span>50%</span>
                        <span>0%</span>
                    </div>
                    <div class="qwise-gridline-100"></div>
                    <div class="qwise-gridline-50"></div>
                    <div class="qwise-pass-line" style="bottom: {pass_percentage}%;"></div>
                    <div class="q-bars-row">
                        {q_bars_rendered}
                    </div>
                </div>
            </div>
        </div>

        <!-- 4. QUESTION-WISE DETAILED TABLE -->
        <div class="section-box">
            <div class="section-heading-row no-break">
                <span class="section-num-pill">4</span>
                <span class="section-heading">Question-wise Detailed Table</span>
                <span class="section-subtext">Selected Test Evaluation Breakdown</span>
            </div>
            <table class="q-table">
                <thead>
                    <tr>
                        <th style="width: 65px; text-align: center;">Q. No.</th>
                        <th>Question</th>
                        <th style="width: 100px; text-align: center;">Marks Obtained</th>
                        <th style="width: 85px; text-align: center;">Max Marks</th>
                        <th style="width: 90px; text-align: center;">Score (%)</th>
                        <th style="min-width: 220px;">Evaluation Justification</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows_rendered}
                </tbody>
            </table>
        </div>

        <!-- Document Footer -->
        <div class="report-footer no-break">
            <span>TVS Motor Company • Confidential Assessment Record</span>
            <span>Generated via Gen AI Hybrid Evaluator</span>
        </div>
    </div>
</body>
</html>
"""
    return html_template


def generate_iframe_print_script(html_content: str) -> str:
    """Generate client-side script that renders the HTML into a hidden iframe and triggers native print/Save as PDF."""
    escaped_json = json.dumps(html_content)
    return f"""
    (function() {{
        try {{
            const htmlData = {escaped_json};
            const existingFrame = document.getElementById('temp-pdf-report-frame');
            if (existingFrame) {{
                document.body.removeChild(existingFrame);
            }}
            const printFrame = document.createElement('iframe');
            printFrame.id = 'temp-pdf-report-frame';
            printFrame.style.position = 'fixed';
            printFrame.style.right = '0';
            printFrame.style.bottom = '0';
            printFrame.style.width = '0';
            printFrame.style.height = '0';
            printFrame.style.border = '0';
            printFrame.style.zIndex = '-9999';
            document.body.appendChild(printFrame);
            
            const frameDoc = printFrame.contentWindow.document;
            frameDoc.open();
            frameDoc.write(htmlData);
            frameDoc.close();
            
            printFrame.contentWindow.focus();
            setTimeout(function() {{
                try {{
                    printFrame.contentWindow.print();
                }} catch (e) {{
                    console.error('Print error:', e);
                }}
                setTimeout(function() {{
                    const frameToRemove = document.getElementById('temp-pdf-report-frame');
                    if (frameToRemove) {{
                        document.body.removeChild(frameToRemove);
                    }}
                }}, 60000);
            }}, 350);
        }} catch (err) {{
            console.error('Error generating PDF report:', err);
        }}
    }})();
    """
