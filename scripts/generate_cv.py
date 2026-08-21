#!/usr/bin/env python3
"""
Generate a CV / resume PDF from craftify.nl's index.html.

The script parses the public content sections of index.html (About Me,
Technologies, Skills, Resume/Experience, Featured Work, Honors & Awards,
Speaking, Testimonials, Contact) so the generated PDF stays in sync with
the website content without needing to be manually rewritten every time
the site copy changes.

Usage:
    python generate_cv.py [--input index.html] [--output dist/CV.pdf]
"""
import argparse
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PRIMARY = HexColor("#D63129")
DARK = HexColor("#222222")
GRAY = HexColor("#555555")
TRACK = HexColor("#EEEEEE")  # unfilled portion of the skill bars

# Contact details that should never end up on a public CV, even though they
# are published on the website's contact section (chamber of commerce
# number, VAT number, bank account number, etc.).
CONTACT_EXCLUDE_PATTERNS = [
    re.compile(r"^KvK", re.I),
    re.compile(r"^VAT", re.I),
    re.compile(r"^NL\d{2}\s?BUNQ", re.I),  # IBAN
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_site(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "lxml")
    data = {}

    # ---- Header ----
    home = soup.select_one("#home-text")
    data["name"] = clean_text(home.select_one("h1").get_text()) if home and home.select_one("h1") else ""
    data["subtitle"] = clean_text(home.select_one("p.subtitle").get_text()) if home and home.select_one("p.subtitle") else ""

    social_links = []
    for a in soup.select("#home-social a[href]"):
        social_links.append(a["href"].strip())
    data["social_links"] = social_links

    contact_info = []
    for p in soup.select("#home-text p.contact-info"):
        contact_info.append(clean_text(p.get_text()))
    data["header_contact"] = contact_info

    # ---- About Me ----
    profile = soup.select_one("#profile")
    about_paragraphs = []
    if profile:
        for p in profile.select(".twelve.columns p"):
            text = clean_text(p.get_text())
            if text:
                about_paragraphs.append(text)
    data["about"] = about_paragraphs

    # ---- Technologies ----
    tech_section = soup.select_one("#tech")
    tech_text = ""
    if tech_section:
        strong = tech_section.find("strong")
        if strong:
            tech_text = clean_text(strong.get_text())
    data["technologies"] = tech_text

    # ---- Skills ----
    skills = []
    skills_section = soup.select_one("#skills")
    if skills_section:
        pending_labels = []
        for el in skills_section.select(".twelve.columns > *"):
            if el.name == "strong":
                label = clean_text(el.get_text())
                if label:
                    pending_labels.append(label)
            elif el.name == "div" and "progress" in el.get("class", []):
                bar = el.select_one(".bar")
                pct = 0
                if bar and bar.get("style"):
                    m = re.search(r"width:\s*(\d+)%", bar["style"])
                    if m:
                        pct = int(m.group(1))
                label = " / ".join(pending_labels) if pending_labels else "Skill"
                skills.append((label, pct))
                pending_labels = []
    data["skills"] = skills

    # ---- Experience / Resume ----
    experience = []
    resume_section = soup.select_one("#resume")
    if resume_section:
        for entry in resume_section.select(".resume-entry"):
            title_el = entry.select_one(".resume-title")
            company_el = entry.select_one(".resume-company")
            dates_el = entry.select_one(".text-right")
            desc_el = entry.select_one("p")
            title = clean_text(title_el.get_text()) if title_el else ""
            company = clean_text(company_el.get_text()) if company_el else ""
            dates = clean_text(dates_el.get_text()) if dates_el else ""
            desc = clean_text(desc_el.get_text()) if desc_el else ""
            if title or company:
                experience.append((title, company, dates, desc))
    data["experience"] = experience

    # ---- Featured Work ----
    featured = []
    for section in soup.select('section[id^="featured-project-"]'):
        job_title_el = section.select_one(".job-title")
        company_el = section.select_one("h3")
        desc_paragraphs = [
            clean_text(p.get_text())
            for p in section.select(".featured-project-description p")
            if "job-title" not in p.get("class", [])
        ]
        details = {}
        detail_container = section.select_one(".featured-project-details")
        if detail_container:
            labels = detail_container.find_all("p", class_="detail-label")
            for label_el in labels:
                label = clean_text(label_el.get_text()).rstrip(":")
                value_el = label_el.find_next_sibling("span")
                value = clean_text(value_el.get_text()) if value_el else ""
                details[label] = value
        featured.append(
            {
                "job_title": clean_text(job_title_el.get_text()) if job_title_el else "",
                "company": clean_text(company_el.get_text()) if company_el else "",
                "description": " ".join(desc_paragraphs),
                "dates": details.get("Year", ""),
            }
        )
    data["featured"] = featured

    # ---- Honors and Awards ----
    honors = []
    honor_section = soup.select_one("#honor")
    if honor_section:
        for entry in honor_section.select(".honor-entry"):
            title_el = entry.select_one(".resume-title")
            company_el = entry.select_one(".resume-company")
            dates_el = entry.select_one(".text-right")
            desc_el = entry.select_one("p")
            title = clean_text(title_el.get_text()) if title_el else ""
            company = clean_text(company_el.get_text()) if company_el else ""
            dates = clean_text(dates_el.get_text()) if dates_el else ""
            desc = clean_text(desc_el.get_text()) if desc_el else ""
            if title or company:
                honors.append((title, company, dates, desc))
    data["honors"] = honors

    # ---- Speaking ----
    speaking_intro = []
    speaking_quotes = []
    speaking_section = soup.select_one("#speaking")
    if speaking_section:
        for p in speaking_section.find_all("p", recursive=False):
            text = clean_text(p.get_text())
            if text:
                speaking_intro.append(text)
        for bq in speaking_section.find_all("blockquote"):
            cite = bq.find("cite")
            cite_text = clean_text(cite.get_text()) if cite else ""
            # Get only this blockquote's own direct text, excluding nested
            # child blockquotes (the source HTML nests them).
            own_text = "".join(
                str(c) for c in bq.contents
                if not (getattr(c, "name", None) in ("blockquote", "cite"))
            )
            quote_text = clean_text(BeautifulSoup(own_text, "lxml").get_text())
            if quote_text:
                speaking_quotes.append((quote_text, cite_text))
    data["speaking_intro"] = speaking_intro
    data["speaking_quotes"] = speaking_quotes

    # ---- Testimonials ----
    testimonials = []
    for section in soup.select("section.divider"):
        bq = section.find("blockquote")
        author_el = section.select_one(".testimonial-author")
        if bq and author_el:
            quote = clean_text(bq.get_text())
            author = clean_text(author_el.get_text()).lstrip("-").strip()
            testimonials.append((quote, author))
    data["testimonials"] = testimonials

    # ---- Contact ----
    contact_details = []
    for li in soup.select("#contact ul.contact-detail > li"):
        text = clean_text(li.get_text())
        if text and not any(p.search(text) for p in CONTACT_EXCLUDE_PATTERNS):
            contact_details.append(text)
    data["contact_details"] = contact_details

    return data


def build_pdf(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"{data.get('name', 'CV')} - CV",
        author=data.get("name", ""),
    )

    styles = getSampleStyleSheet()

    name_style = ParagraphStyle("Name", parent=styles["Normal"], fontName="Helvetica-Bold",
                                 fontSize=22, leading=26, textColor=DARK, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontName="Helvetica",
                                     fontSize=13, leading=16, textColor=PRIMARY, spaceAfter=6)
    contact_style = ParagraphStyle("Contact", parent=styles["Normal"], fontName="Helvetica",
                                    fontSize=9.5, textColor=GRAY, spaceAfter=10, leading=13)
    heading_style = ParagraphStyle("Heading", parent=styles["Normal"], fontName="Helvetica-Bold",
                                    fontSize=13, leading=16, textColor=PRIMARY, spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=9.7, textColor=DARK, leading=13, spaceAfter=6)
    bold_body_style = ParagraphStyle("BoldBody", parent=body_style, fontName="Helvetica-Bold")
    title_style = ParagraphStyle("EntryTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
                                  fontSize=10.5, leading=13, textColor=DARK, spaceBefore=6, spaceAfter=0)
    dates_style = ParagraphStyle("Dates", parent=styles["Normal"], fontName="Helvetica-Bold",
                                  fontSize=9.3, leading=13, textColor=GRAY, alignment=2)
    company_style = ParagraphStyle("Company", parent=styles["Normal"], fontName="Helvetica-Oblique",
                                    fontSize=9.7, leading=12, textColor=PRIMARY, spaceAfter=3)
    desc_style = ParagraphStyle("Desc", parent=styles["Normal"], fontName="Helvetica",
                                 fontSize=9.3, textColor=DARK, leading=12.5, spaceAfter=6)
    quote_style = ParagraphStyle("Quote", parent=styles["Normal"], fontName="Helvetica-Oblique",
                                  fontSize=9.2, textColor=DARK, leading=12, spaceAfter=1)
    author_style = ParagraphStyle("Author", parent=styles["Normal"], fontName="Helvetica-Bold",
                                   fontSize=8.8, leading=11, textColor=PRIMARY, spaceAfter=7)
    skill_style = ParagraphStyle("Skill", parent=styles["Normal"], fontName="Helvetica",
                                  fontSize=9.2, textColor=DARK)
    pct_style = ParagraphStyle("Pct", parent=styles["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, textColor=PRIMARY)

    story = []

    def skill_bar(pct, width=68 * mm, height=2.6 * mm):
        """A crisp, vector-drawn progress bar (avoids relying on font glyph
        support for Unicode block characters, which can render as missing
        glyphs in some PDF viewers/printers)."""
        d = Drawing(width, height)
        d.add(Rect(0, 0, width, height, fillColor=TRACK, strokeColor=None))
        filled = width * max(0, min(100, pct)) / 100
        if filled > 0:
            d.add(Rect(0, 0, filled, height, fillColor=PRIMARY, strokeColor=None))
        return d

    def heading(text):
        story.append(Paragraph(text.upper(), heading_style))
        story.append(HRFlowable(width="100%", thickness=1.3, color=PRIMARY, spaceAfter=6, spaceBefore=0))

    def entry(title, company, dates, description):
        t = Table(
            [[Paragraph(title, title_style), Paragraph(dates, dates_style)]],
            colWidths=[130 * mm, 34 * mm],
        )
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        t.hAlign = "LEFT"
        block = [t]
        if company:
            block.append(Paragraph(company, company_style))
        if description:
            block.append(Paragraph(description, desc_style))
        story.append(KeepTogether(block))

    # ---------- HEADER ----------
    story.append(Paragraph(data.get("name", ""), name_style))
    if data.get("subtitle"):
        story.append(Paragraph(data["subtitle"], subtitle_style))

    contact_line_parts = list(data.get("header_contact", []))
    social_line = " &nbsp;|&nbsp; ".join(data.get("social_links", []))
    contact_html = " &nbsp;|&nbsp; ".join(contact_line_parts)
    if social_line:
        contact_html += "<br/>" + social_line
    if contact_html:
        story.append(Paragraph(contact_html, contact_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=4, spaceBefore=0))

    # ---------- ABOUT ----------
    if data.get("about"):
        heading("About Me")
        for para in data["about"]:
            story.append(Paragraph(para, body_style))

    # ---------- TECHNOLOGIES ----------
    if data.get("technologies"):
        heading("Technologies")
        story.append(Paragraph(data["technologies"], bold_body_style))

    # ---------- SKILLS ----------
    if data.get("skills"):
        heading("Skills")
        rows = []
        for name, pct in data["skills"]:
            rows.append([
                Paragraph(name, skill_style),
                skill_bar(pct),
                Paragraph(f"{pct}%", pct_style),
            ])
        skill_table = Table(rows, colWidths=[65 * mm, 72 * mm, 15 * mm])
        skill_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (1, 0), (1, -1), 6),
        ]))
        skill_table.hAlign = "LEFT"
        story.append(skill_table)
        story.append(Spacer(1, 6))

    # ---------- EXPERIENCE ----------
    if data.get("experience"):
        heading("Experience")
        for title, company, dates, desc in data["experience"]:
            entry(title, company, dates, desc)

    # ---------- FEATURED WORK ----------
    if data.get("featured"):
        heading("Featured Work")
        for item in data["featured"]:
            entry(item["job_title"], item["company"], item["dates"], item["description"])

    # ---------- HONORS AND AWARDS ----------
    if data.get("honors"):
        heading("Honors and Awards")
        for title, org, dates, desc in data["honors"]:
            entry(title, org, dates, desc)

    # ---------- SPEAKING ----------
    if data.get("speaking_intro") or data.get("speaking_quotes"):
        heading("Speaking")
        for para in data.get("speaking_intro", []):
            story.append(Paragraph(para, body_style))
        for quote, author in data.get("speaking_quotes", []):
            suffix = f" &mdash; {author}" if author else ""
            story.append(Paragraph(f"&ldquo;{quote}&rdquo;{suffix}", quote_style))
        story.append(Spacer(1, 4))

    # ---------- RECOMMENDATIONS ----------
    if data.get("testimonials"):
        heading("Recommendations")
        for quote, author in data["testimonials"]:
            story.append(KeepTogether([
                Paragraph(f"&ldquo;{quote}&rdquo;", quote_style),
                Paragraph(f"&mdash; {author}", author_style),
            ]))

    # ---------- CONTACT ----------
    if data.get("contact_details"):
        heading("Contact")
        story.append(Paragraph(" &nbsp;|&nbsp; ".join(data["contact_details"]), body_style))

    doc.build(story)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="index.html", type=Path, help="Path to index.html")
    parser.add_argument(
        "--output",
        default="dist/Pieter_Joost_van_de_Sande_CV.pdf",
        type=Path,
        help="Path to write the generated PDF",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 1

    data = parse_site(args.input)
    if not data.get("name"):
        print("Could not find a name in the parsed site content.", file=sys.stderr)
        return 1

    build_pdf(data, args.output)
    print(f"CV PDF written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
