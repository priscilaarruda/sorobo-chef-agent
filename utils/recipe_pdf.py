from pathlib import Path
import datetime
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    Table,
    TableStyle,
)
from reportlab.lib.units import cm
from reportlab.lib import colors


def save_recipe_pdf(recipe_text: str, output_dir: Path, filename_hint: str = "receita") -> Path:
    if not isinstance(recipe_text, str):
        recipe_text = str(recipe_text)
    
    if isinstance(output_dir, str):
        output_dir = Path(output_dir)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(
        c for c in filename_hint.lower().replace(" ", "_")
        if c.isalnum() or c in "._-"
    ) or "receita"

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = output_dir / f"{safe_name}_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=24,
        leading=28,
        alignment=1,
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=16,
        leading=20,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=12,
        leading=16,
        spaceAfter=6,
    )

    lines = [l.rstrip() for l in recipe_text.strip().splitlines()]
    story = []

    # título
    if lines:
        title = lines[0].lstrip("# ").strip()
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 6))
        content_lines = lines[1:]
    else:
        content_lines = []

    meta_prefixes = [
        "Tipo de receita:",
        "Tempo de preparo:",
        "Porções:",
        "Dificuldade:",
        "Nível de bagunça:",
    ]

    meta_lines = []
    rest_lines = []
    meta_done = False

    for line in content_lines:
        stripped = line.strip()
        if not meta_done and any(stripped.startswith(p) for p in meta_prefixes):
            if stripped:
                meta_lines.append(stripped)
        else:
            if stripped != "":
                meta_done = True
            rest_lines.append(line)

    if meta_lines:
        meta_html = "<br/>".join(f"<b>{l}</b>" for l in meta_lines)
        meta_para = Paragraph(meta_html, body_style)
        table = Table([[meta_para]], colWidths=[doc.width])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("INNERPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 12))

    current_paragraph_lines: list[str] = []
    current_list_items: list[str] = []
    current_list_type: str | None = None

    def flush_paragraph():
        nonlocal current_paragraph_lines
        if current_paragraph_lines:
            text = "\n".join(current_paragraph_lines).strip()
            if text:
                story.append(Paragraph(text.replace("\n", "<br/>"), body_style))
                story.append(Spacer(1, 6))
        current_paragraph_lines = []

    def flush_list():
        nonlocal current_list_items, current_list_type
        if current_list_items and current_list_type:
            items = [
                ListItem(Paragraph(item, body_style), leftIndent=12)
                for item in current_list_items
            ]
            bullet_type = "bullet" if current_list_type == "bullet" else "1"
            story.append(ListFlowable(items, bulletType=bullet_type))
            story.append(Spacer(1, 6))
        current_list_items = []
        current_list_type = None

    for raw_line in rest_lines:
        line = raw_line.rstrip()

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        if line.startswith("## "):
            flush_paragraph()
            flush_list()
            heading = line.lstrip("# ").strip()
            story.append(Paragraph(heading, heading_style))
            story.append(Spacer(1, 4))
            continue

        bullet_match = re.match(r"^- (.*)", line)
        if bullet_match:
            flush_paragraph()
            text = bullet_match.group(1).strip()
            if current_list_type not in (None, "bullet"):
                flush_list()
            current_list_type = "bullet"
            current_list_items.append(text)
            continue

        num_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if num_match:
            flush_paragraph()
            text = num_match.group(2).strip()
            if current_list_type not in (None, "numbered"):
                flush_list()
            current_list_type = "numbered"
            current_list_items.append(text)
            continue

        flush_list()
        current_paragraph_lines.append(line)

    flush_paragraph()
    flush_list()

    doc.build(story)
    return pdf_path