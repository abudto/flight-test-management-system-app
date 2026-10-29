
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

NAVY = colors.HexColor("#17365D")
LIGHT = colors.HexColor("#EDF1F5")


def make_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="FTMSTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=NAVY,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="FTMSBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        spaceAfter=5,
    ))
    styles.add(ParagraphStyle(
        name="FTMSHeading",
        parent=styles["Heading2"],
        fontSize=10,
        leading=13,
        textColor=NAVY,
        spaceBefore=9,
        spaceAfter=4,
        keepwithNext=1,
    ))
    styles.add(ParagraphStyle(
        name="FTMSCell",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        name="FTMSCellHeader",
        parent=styles["FTMSCell"],
        fontName="Helvetica-Bold",
        textColor=colors.white,
    ))
    return styles


def paragraph(value, style):
    # Escape database text before passing it to ReportLab's
    # Paragraph markup parser.
    text = escape(str(value if value is not None else "-"))
    return Paragraph(text.replace("\n", "<br/>"), style)


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setStrokeColor(colors.grey)
    canvas.line(12 * mm, 13 * mm, 198 * mm, 13 * mm)
    canvas.drawString(12 * mm, 9 * mm, "FTMS | Generated document")
    canvas.drawRightString(
        198 * mm, 9 * mm, f"Page {doc.page}"
    )
    canvas.restoreState()


def make_document(buffer):
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=19 * mm,
        title="FTMS Flight Test Document",
    )


def styled_table(rows, widths, header=True):
    table = Table(
        rows, colWidths=widths, repeatRows=1 if header else 0,
        hAlign="LEFT",
    )
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.35, colors.lightgrey),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, LIGHT]),
        ])
    table.setStyle(TableStyle(commands))
    return table


def generate_sequence_pdf(sequence):
    buffer = BytesIO()
    doc = make_document(buffer)
    s = make_styles()
    story = []

    story.append(Paragraph("FLIGHT TEST SEQUENCE", s["FTMSTitle"]))
    story.append(paragraph(
        f"{sequence.sequence_number} | Rev {sequence.revision}",
        s["FTMSBody"],
    ))

    metadata = [
        ("Program", sequence.program.name),
        ("Title", sequence.title),
        ("Planned date", sequence.planned_date or "Not scheduled"),
        ("Objective", sequence.objective or "-"),
    ]
    for label, value in metadata:
        story.append(Paragraph(
            f"<b>{escape(label)}:</b> {escape(str(value))}",
            s["FTMSBody"],
        ))

    story.append(Paragraph("Execution Sequence", s["FTMSHeading"]))

    widths = [12 * mm, 26 * mm, 64 * mm, 32 * mm, 18 * mm, 34 * mm]
    headers = ["No.", "Test Point", "Test", "Card", "Min", "Remarks"]
    rows = [[paragraph(h, s["FTMSCellHeader"]) for h in headers]]

    for item in sequence.items.select_related(
        "test_point__test", "test_card"
    ).order_by("order"):
        rows.append([
            paragraph(item.order, s["FTMSCell"]),
            paragraph(item.test_point.test_point_number, s["FTMSCell"]),
            paragraph(item.test_point.test.test_title, s["FTMSCell"]),
            paragraph(
                item.test_card.card_number if item.test_card else "-",
                s["FTMSCell"],
            ),
            paragraph(item.estimated_duration_min, s["FTMSCell"]),
            paragraph(item.remarks, s["FTMSCell"]),
        ])

    if len(rows) == 1:
        rows.append([
            paragraph("-", s["FTMSCell"]) for _ in headers
        ])

    story.append(styled_table(rows, widths))

    total = sum(
        item.estimated_duration_min or 0
        for item in sequence.items.all()
    )
    story.append(Spacer(1, 8 * mm))
    story.append(paragraph(
        f"Total estimated test duration: {total} minutes",
        s["FTMSBody"],
    ))
    story.append(Paragraph("Sequence Notes", s["FTMSHeading"]))
    story.append(paragraph(sequence.remarks or "-", s["FTMSBody"]))

    doc.build(story, onFirstPage=page_footer,
              onLaterPages=page_footer)
    return buffer.getvalue()


def generate_card_pdf(card):
    buffer = BytesIO()
    doc = make_document(buffer)
    s = make_styles()
    story = []

    test = card.test
    program = test.engineering_requirement.program

    story.append(Paragraph("FLIGHT TEST CARD", s["FTMSTitle"]))
    story.append(paragraph(
        f"{card.card_number} | Rev {card.revision}",
        s["FTMSBody"],
    ))

    metadata = [
        ("Program", program.name),
        ("Card title", card.title),
        ("Test number", test.test_number),
        ("Test objective", test.objective),
    ]
    for label, value in metadata:
        story.append(Paragraph(
            f"<b>{escape(label)}:</b> {escape(str(value))}",
            s["FTMSBody"],
        ))

    sections = [
        ("Preparation", card.preparation),
        ("Test Procedure", card.procedure),
        ("Pass / Fail Criteria", test.pass_fail_criteria),
        ("Safety Notes", card.safety_notes),
        ("Remarks", card.remarks),
    ]

    for heading, content in sections:
        story.append(Paragraph(
            heading,
            s["FTMSHeading"],
        ))
        story.append(paragraph(
            content or "-",
            s["FTMSBody"],
        ))

    story.append(Paragraph("Associated Test Points", s["FTMSHeading"]))

    widths = [34 * mm, 30 * mm, 30 * mm, 30 * mm, 62 * mm]
    headers = ["Test Point", "Weight", "CG", "Reps", "Conditions"]
    rows = [[paragraph(h, s["FTMSCellHeader"]) for h in headers]]

    # Show test points actually assigned to this card in sequences.
    # This avoids assuming every point in the test uses the card.
    point_ids = card.sequence_items.values_list(
        "test_point_id", flat=True
    ).distinct()

    points = test.test_points.filter(
        pk__in=point_ids
    ).prefetch_related("conditions").order_by("test_point_number")

    for point in points:
        conditions = "; ".join(
            f"{c.name}: {c.value} {c.unit}".strip()
            for c in point.conditions.all()
        )
        rows.append([
            paragraph(point.test_point_number, s["FTMSCell"]),
            paragraph(point.get_weight_category_display(), s["FTMSCell"]),
            paragraph(point.get_cg_category_display(), s["FTMSCell"]),
            paragraph(point.repetition_required, s["FTMSCell"]),
            paragraph(conditions or "-", s["FTMSCell"]),
        ])

    if len(rows) == 1:
        rows.append([
            paragraph("-", s["FTMSCell"]) for _ in headers
        ])

    story.append(styled_table(rows, widths))

    doc.build(story, onFirstPage=page_footer,
              onLaterPages=page_footer)
    return buffer.getvalue()
