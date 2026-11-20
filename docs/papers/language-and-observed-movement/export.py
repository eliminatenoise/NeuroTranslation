"""Export editable article HTML to a PDF and a LaTeX chapter fragment.

From this directory, run python export.py. Requires Python 3, ReportLab and
Liberation Sans. Set LIBERATION_FONT_DIR to the directory holding the four
LiberationSans TrueType files when they are outside the standard font paths.
The LaTeX fragment uses hyperref in its host document.
The reviewed copy uses ReportLab's deterministic PDF mode. No network input.
"""
from copy import copy
from html import escape
import os
from pathlib import Path
from xml.etree import ElementTree as ET

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
NAME = "language-and-movement"
INK = "#172b32"
TEAL = "#0a5360"
MUTED = "#405958"


def register_fonts():
    locations = [Path(p) for p in (
        os.getenv("LIBERATION_FONT_DIR"), "/usr/share/fonts/liberation",
        "/usr/share/fonts/truetype/liberation2", "/usr/share/fonts/truetype/liberation",
        "/Library/Fonts", str(Path.home() / "Library/Fonts"), os.getenv("WINDIR") and
        str(Path(os.environ["WINDIR"]) / "Fonts"),
    ) if p]
    folder = next((p for p in locations if (p / "LiberationSans-Regular.ttf").is_file()), None)
    if not folder:
        raise SystemExit("Set LIBERATION_FONT_DIR to the directory containing Liberation Sans.")
    for style in ("Regular", "Bold", "Italic", "BoldItalic"):
        pdfmetrics.registerFont(TTFont("Article" + style, str(folder / f"LiberationSans-{style}.ttf")))
    pdfmetrics.registerFontFamily("ArticleRegular", normal="ArticleRegular", bold="ArticleBold",
                                  italic="ArticleItalic", boldItalic="ArticleBoldItalic")


def pdf_markup(node):
    parts = [escape(node.text or "")]
    for child in node:
        content = pdf_markup(child)
        if child.tag == "a":
            content = f'<link href="{escape(child.attrib["href"], quote=True)}" color="{TEAL}"><u>{content}</u></link>'
        elif child.tag in {"em", "strong"}:
            tag = {"em": "i", "strong": "b"}[child.tag]
            content = f"<{tag}>{content}</{tag}>"
        else:
            raise ValueError(f"Unexpected inline element {child.tag}")
        parts.extend((content, escape(child.tail or "")))
    return "".join(parts)


def make_style(name, size, leading, *, bold=False, before=0, after=0, color=INK):
    return ParagraphStyle(name=name, fontName="ArticleBold" if bold else "ArticleRegular",
                          fontSize=size, leading=leading, textColor=colors.HexColor(color),
                          spaceBefore=before, spaceAfter=after, splitLongWords=False)


def footer(canvas, doc):
    width, _ = A4
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#b6c7c7"))
    canvas.line(55, 40, width-55, 40)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.setFont("ArticleRegular", 8.6)
    canvas.drawString(55, 25, "NeuroTranslation  /  Language and observed movement")
    canvas.drawRightString(width-55, 25, str(doc.page))
    canvas.restoreState()


def pdf_export(sections):
    register_fonts()
    width, height = A4
    text_width = width - 110
    doc = BaseDocTemplate(str(ROOT / f"{NAME}.pdf"), pagesize=A4,
                          title="How precisely do words identify a recorded movement?",
                          author="NeuroTranslation", subject="Language and observed movement",
                          creator="NeuroTranslation supplement", invariant=1)
    frame = Frame(55, 55, text_width, height-105, leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0, id="article")
    doc.addPageTemplates(PageTemplate(id="article", frames=[frame], onPage=footer))
    styles = {
        "p": make_style("body", 12.0, 16.4, after=8),
        "source": make_style("sources", 11.5, 15.3, after=7),
        "series": make_style("series", 10.2, 13.5, after=11, color=MUTED),
        "date": make_style("date", 9.6, 13, after=12, color=MUTED),
        "h1": make_style("title", 32, 34, bold=True, after=9),
        "h2": make_style("heading", 23, 26, bold=True, after=12),
        "h3": make_style("subheading", 14.2, 17, bold=True, before=5, after=6),
        "caption": make_style("caption", 10.4, 13, bold=True, before=2, after=5),
        "cell": make_style("cell", 11.0, 14.0),
        "column": make_style("column", 10.8, 13.5, bold=True),
    }
    for key in ("caption", "h1", "h2", "h3"):
        styles[key].keepWithNext = True
    story = []
    for i, section in enumerate(sections):
        if i:
            story.append(PageBreak())
        for node in section:
            if node.tag != "table":
                key = node.get("class", node.tag)
                if i == 3 and key == "p":
                    key = "source"
                story.append(Paragraph(pdf_markup(node), styles[key]))
                continue
            story.append(Paragraph(pdf_markup(node.find("caption")), styles["caption"]))
            numeric = node.get("class") == "numeric"
            parts = []
            for row in node.findall("thead/tr") + node.findall("tbody/tr"):
                cells = []
                for index, cell in enumerate(row):
                    cell_style = copy(styles["column" if cell.tag == "th" else "cell"])
                    if numeric and index:
                        cell_style.alignment = TA_RIGHT
                    cells.append(Paragraph(pdf_markup(cell), cell_style))
                parts.append(cells)
            fractions = (0.56, 0.18, 0.26) if numeric else (0.29, 0.34, 0.37)
            table = Table(parts, colWidths=[text_width * x for x in fractions], repeatRows=1,
                          hAlign="LEFT")
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "ArticleRegular"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9f0ed")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.65, colors.HexColor("#8ba5a0")),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9e2df")),
                ("TOPPADDING", (0, 0), (-1, -1), 3.4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
            ]))
            story.extend((table, Spacer(1, 9)))
    def deterministic_canvas(*args, **kwargs):
        kwargs["invariant"] = 1
        kwargs["initialFontName"] = "ArticleRegular"
        return Canvas(*args, **kwargs)
    doc.build(story, canvasmaker=deterministic_canvas)


def tex_escape(text):
    replacements = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
                    "{": r"\{", "}": r"\}", "−": r"\textminus{}",
                    "½": r"\ensuremath{1/2}", "⅓": r"\ensuremath{1/3}",
                    "·": r"\textperiodcentered{}", "–": "--", "’": "'"}
    return "".join(replacements.get(c, c) for c in text)


def tex_inline(node):
    parts = [tex_escape(node.text or "")]
    for child in node:
        content = tex_inline(child)
        if child.tag == "a":
            content = r"\href{" + child.attrib["href"] + "}{" + content + "}"
        else:
            content = {"em": r"\emph", "strong": r"\textbf"}[child.tag] + "{" + content + "}"
        parts.extend((content, tex_escape(child.tail or "")))
    return "".join(parts)


def tex_export(sections):
    output = ["% Editable supplement. Include with \\input{language-and-movement.tex}.",
              "% Required packages in the host preamble: hyperref.",
              r"\begingroup", r"\sffamily"]
    for section in sections:
        for item in section:
            if item.tag == "table":
                output.extend([r"\par\medskip\noindent\textbf{" + tex_inline(item.find("caption")) + "}",
                               r"\par\smallskip\noindent"])
                columns = (r"@{}p{.51\linewidth}p{.17\linewidth}p{.23\linewidth}@{}"
                           if item.get("class") == "numeric" else
                           r"@{}p{.28\linewidth}p{.28\linewidth}p{.35\linewidth}@{}")
                output.append(r"\begin{tabular}{" + columns + "}")
                for row in item.findall("thead/tr") + item.findall("tbody/tr"):
                    values = [tex_inline(cell) for cell in row]
                    if row[0].tag == "th":
                        values = [r"\textbf{" + value + "}" for value in values]
                    output.append(" & ".join(values) + r" \\")
                    if row[0].tag == "th":
                        output.append(r"\hline")
                output.append(r"\end{tabular}\par\medskip")
            elif item.tag in ("h1", "h2", "h3"):
                heading = {"h1": "section", "h2": "subsection", "h3": "subsubsection"}[item.tag]
                output.append("\\" + heading + "*{" + tex_inline(item) + "}")
            else:
                output.append(r"\noindent " + tex_inline(item) + r"\par")
            output.append("")
    output.append(r"\endgroup")
    (ROOT / f"{NAME}.tex").write_text("\n".join(output) + "\n", encoding="utf-8")


if __name__ == "__main__":
    document = ET.parse(ROOT / f"{NAME}.html")
    sections = document.findall("body/main/section")
    if len(sections) != 4:
        raise ValueError("The supplement has four sections.")
    tex_export(sections)
    pdf_export(sections)
