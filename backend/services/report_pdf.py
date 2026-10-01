"""Render finalized report data in memory; never load or modify business stores."""
from io import BytesIO
from xml.sax.saxutils import escape


def render_report_pdf(report):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 13
    def p(value, style='BodyText'):
        return Paragraph(escape(str(value if value is not None else 'Not available')).replace('\n', '<br/>'), styles[style])
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=36, leftMargin=36,
                            topMargin=36, bottomMargin=40, title='Test Evaluation Report')
    story = [p('Test Evaluation Report', 'Title'), p(report['assessment_name'], 'Heading1'),
             p(report['test_name'] + ' | ' + report['test_category'], 'Heading2'),
             p('Assessment ID: ' + report['assessment_id']), p('Test ID: ' + report['test_id']),
             p('Question type: ' + str(report.get('test_type') or 'Not available')),
             p('Generated (UTC): ' + report['generated_at']), Spacer(1, 12),
             p('Finalized results only. Missing or unfinished evaluations are not scored.'), Spacer(1, 12)]
    rows = [[p(v) for v in ['Candidate / ID', 'Marks', 'Maximum', 'Percentage', 'Status']]]
    for result in report['candidates']:
        rows.append([p(result['candidate_name'] + '\n' + result['candidate_id']),
                     p(result['total_marks']), p(result['max_marks']), p(str(result['percentage'])+'%'),
                     p(result['evaluation_status'])])
    table = Table(rows, colWidths=[205, 65, 70, 85, 98], repeatRows=1, splitByRow=1, splitInRow=1)
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8EDF7')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),0.3,colors.lightgrey)]))
    story.append(table)
    for result in report['candidates']:
        story.extend([PageBreak(), p(result['candidate_name'] + ' (' + result['candidate_id'] + ')','Heading1'),
                      p(report['assessment_name'] + ' / ' + report['test_name'], 'Heading2'),
                      p(f"Marks: {result['total_marks']} / {result['max_marks']} | {result['percentage']}% | {result['evaluation_status']}"),
                      p('Evaluation source: ' + result['evaluation_type']),
                      p('Evaluated: ' + str(result.get('evaluated_at') or 'Not available'))])
        for q in result['questions']:
            story.extend([p(str(q['question_no']) + ' - ' + str(q['awarded_marks']) + ' / ' + str(q['maximum_marks']), 'Heading2'),
                          p(q.get('question', '')), p('Candidate answer: ' + str(q.get('candidate_answer', ''))),
                          p('Remarks: ' + str(q.get('justification', '')))])
            for label, key in [('Score (%)','percentage'), ('Status','status'), ('Answer status','answer_status'), ('CO','co'), ('LO','lo'), ('Knowledge type','knowledge_type'),
                               ('Domain','domain'), ('RBT level','rbt_level'), ('Correct option','correct_option'),
                               ('Correctness','correctness'), ('Relevance','relevance'), ('Completeness','completeness'),
                               ('Strengths','strengths'), ('Missing points','missing_points'), ('Incorrect points','incorrect_points')]:
                value = q.get(key)
                if value is not None and value != "" and value != []:
                    story.append(p(label + ': ' + ('; '.join(map(str, value)) if isinstance(value, list) else str(value))))
            story.append(Spacer(1, 8))
    def footer(canvas, document):
        canvas.saveState(); canvas.setFont('Helvetica', 8)
        canvas.drawRightString(A4[0]-36, 22, 'Page ' + str(document.page)); canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
