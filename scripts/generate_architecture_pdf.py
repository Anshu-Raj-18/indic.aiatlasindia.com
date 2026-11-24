"""
Script to generate Indic_AI_Atlas_Pipeline_Architecture.pdf using ReportLab.
Produces a beautiful, publication-grade architectural specification PDF
covering Levels 1-6 + Bonus Level 7 and Disqualification Prevention Guardrails.
"""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = DOCS_DIR / "Indic_AI_Atlas_Pipeline_Architecture.pdf"

# Design Tokens from tokens.css
COLOR_INK = colors.HexColor("#0F1B2D")
COLOR_PAPER = colors.HexColor("#FFFFFF")
COLOR_SEA = colors.HexColor("#E4EDF2")
COLOR_GRID = colors.HexColor("#D5E1E9")
COLOR_MUTED = colors.HexColor("#43536B")
COLOR_RULE = colors.HexColor("#C5D1DB")
COLOR_SIGNAL = colors.HexColor("#F4C430")
COLOR_ROUTE = colors.HexColor("#C9361A")
COLOR_INDIC = colors.HexColor("#8A5A1C")
COLOR_WASH = colors.HexColor("#F6F8FA")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic total page numbers and running header/footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_INK)

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 756, "AI ATLAS INDIA · PLATE 05: INDIC LANGUAGE AI (indic.aiatlasindia.com)")
            self.drawRightString(576, 756, "SYSTEM ARCHITECTURE & SPECIFICATION")
            self.setStrokeColor(COLOR_INK)
            self.setLineWidth(1)
            self.line(36, 750, 576, 750)

        # Footer (all pages)
        self.setStrokeColor(COLOR_RULE)
        self.setLineWidth(1)
        self.line(36, 42, 576, 42)

        self.setFont("Helvetica", 8)
        self.setFillColor(COLOR_MUTED)
        self.drawString(36, 30, "Built by Anshu Raj · Review: Moksh Desai · Owned by Vyohm AI Private Limited · GA4: G-WK0D46CCQZ")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 30, page_str)
        self.restoreState()


def generate_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=COLOR_INK,
        spaceAfter=6
    )
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=COLOR_MUTED,
        spaceAfter=12
    )
    style_h1 = ParagraphStyle(
        'Heading1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=COLOR_INK,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'Heading2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=COLOR_INDIC,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=COLOR_INK,
        spaceAfter=5
    )
    style_body_bold = ParagraphStyle(
        'BodyBold',
        parent=style_body,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Metadata Banner
    story.append(Paragraph("AI ATLAS INDIA — PLATE 05: INDIC LANGUAGE AI", style_title))
    story.append(Paragraph("Complete Technical Architecture, Data Flow, Levels 1–7 Compliance & Disqualification Guardrails", style_subtitle))

    # Meta Table (Author, Subdomain, Section, Owner)
    meta_data = [
        [
            Paragraph("<b>Section:</b> 05 Indic Language AI", style_body),
            Paragraph("<b>Subdomain:</b> indic.aiatlasindia.com", style_body),
            Paragraph("<b>Candidate Author:</b> Anshu Raj", style_body)
        ],
        [
            Paragraph("<b>Owner:</b> Vyohm AI Private Limited", style_body),
            Paragraph("<b>Author / Builder:</b> Anshu Raj", style_body),
            Paragraph("<b>Expert Reviewer:</b> Moksh Desai", style_body)
        ],
        [
            Paragraph("<b>Design Token:</b> #8A5A1C (5.9:1 AA)", style_body),
            Paragraph("<b>GA4 ID:</b> G-WK0D46CCQZ", style_body),
            Paragraph("<b>Hard Cap:</b> MAX 20 Published Answers", style_body)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[180, 180, 180])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SEA),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_RULE),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Section 1: Executive Summary & Two-Layer Architecture
    story.append(Paragraph("1. System Architecture Overview", style_h1))
    story.append(Paragraph(
        "AI Atlas India (Plate 05) is built on a strictly decoupled <b>two-layer architecture</b>. "
        "Layer 1 is an offline, private Python automation pipeline that discovers community demand, drafts structured evidence-grounded answers, and provides a web-based expert review portal. "
        "Layer 2 is a 100% static, lightning-fast public website deployed standalone to Vercel/Cloudflare Pages, completely isolated from databases, API credentials, and internal tooling.",
        style_body
    ))

    arch_table_data = [
        [
            Paragraph("<b>Layer</b>", style_body_bold),
            Paragraph("<b>Components & Technologies</b>", style_body_bold),
            Paragraph("<b>Primary Purpose & Public Exposure</b>", style_body_bold)
        ],
        [
            Paragraph("<b>Layer 1<br/>Engine<br/>(Private)</b>", style_body),
            Paragraph("• Python 3.12, FastAPI, SQLite (<code>indic_atlas.db</code>)<br/>"
                      "• <code>engine/1_discover.py</code> (YouTube & HN APIs)<br/>"
                      "• <code>engine/2_draft.py</code> (Gemini-Flash Single-Pass)<br/>"
                      "• <code>engine/3_expert_dispatch.py</code> (Gmail/SMTP Dispatch)<br/>"
                      "• <code>engine/main.py</code> (/review, /diffs, /analytics, /social)<br/>"
                      "• <code>engine/5_social.py</code> (ATProto Bluesky Publisher)<br/>"
                      "• <code>engine/6_measure.py</code> (Telemetry, Crawlers & AI Topics)", style_body),
            Paragraph("Private automation, audit logging, expert email sign-off gate, and static site compilation. <b>NEVER deployed to public web</b>; excluded via <code>.vercelignore</code>.", style_body)
        ],
        [
            Paragraph("<b>Layer 2<br/>Frontend<br/>(Public)</b>", style_body),
            Paragraph("• Static HTML5 / CSS3 (<code>frontend/tokens.css</code>)<br/>"
                      "• <code>frontend/index.html</code> (Section Hub & Live Search)<br/>"
                      "• <code>frontend/about.html</code> (Disclosures & Team)<br/>"
                      "• <code>frontend/answers/*.html</code> (FAQPage JSON-LD)<br/>"
                      "• <code>frontend/providers/*.html</code> (8 Criteria Profiles)<br/>"
                      "• <code>sitemap.xml</code> & <code>robots.txt</code> (AI Crawlers)", style_body),
            Paragraph("High-performance public static web assets served cleanly on Vercel at <code>indic.aiatlasindia.com</code>. Pre-rendered, crawlable by search engines and LLM agents.", style_body)
        ]
    ]
    t_arch = Table(arch_table_data, colWidths=[70, 240, 230])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_INK),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PAPER),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 10))

    # Section 2: Pipeline Stages & Levels
    story.append(Paragraph("2. Levels 1–7 Pipeline Stages & Technical Implementation", style_h1))

    stages_data = [
        [
            Paragraph("<b>Level & Stage</b>", style_body_bold),
            Paragraph("<b>Module & Source</b>", style_body_bold),
            Paragraph("<b>Rules, Guards & Implementation Scope</b>", style_body_bold)
        ],
        [
            Paragraph("<b>Level 2<br/>Discover</b>", style_body),
            Paragraph("<code>engine/1_discover.py</code><br/>YouTube Data v3 & HN Algolia", style_body),
            Paragraph("• Queries only official public APIs (zero scraping).<br/>"
                      "• Interrogative regex filters real developer queries.<br/>"
                      "• SHA256 exact hash + <b>0.85 cosine similarity</b> deduplication.<br/>"
                      "• <code>selection_reason</code> audit logging for prioritized questions.<br/>"
                      "• <b>Strict privacy:</b> NEVER stores or displays commenter usernames.", style_body)
        ],
        [
            Paragraph("<b>Level 3<br/>Draft</b>", style_body),
            Paragraph("<code>engine/2_draft.py</code><br/>Google GenAI (Gemini-Flash)", style_body),
            Paragraph("• Single-pass structured JSON output to conserve free quota.<br/>"
                      "• Generates runnable Python code & INR pricing tables (+18% GST).<br/>"
                      "• <b>Grounding format:</b> <code>● [VALUE] · [SOURCE] · checked [DATE]</code>.<br/>"
                      "• <b>Zero-Guessing Rule:</b> Unsourced items rendered as <code>◌ Not yet sourced</code>.<br/>"
                      "• Full SEO metadata drafted: title, meta_description, alt_text.", style_body)
        ],
        [
            Paragraph("<b>Level 4<br/>Email Review</b>", style_body),
            Paragraph("<code>engine/3_expert_dispatch.py</code><br/>Gmail API & SMTP Dispatch", style_body),
            Paragraph("• Dispatched by Developer <b>Moksh Desai</b>.<br/>"
                      "• Generates unique secret token URLs (<code>/review/&lt;token&gt;</code>).<br/>"
                      "• Reviewer replies (APPROVED, EDITED, REJECTED) recorded in SQLite.<br/>"
                      "• <code>/admin/diffs</code> renders side-by-side comparison of AI vs Expert text.", style_body)
        ],
        [
            Paragraph("<b>Level 5<br/>Social</b>", style_body),
            Paragraph("<code>engine/5_social.py</code><br/>ATProto / Bluesky", style_body),
            Paragraph("• Auto-posts published canonical URLs to <code>@vyohm-bot.bsky.social</code>.<br/>"
                      "• <b>Idempotency:</b> SQLite unique URL constraint prevents duplicate posts.<br/>"
                      "• Scheduled posting via ISO timestamps (<code>--run-scheduled</code>).<br/>"
                      "• Human approval queue at <code>/admin/social</code>; <code>--purge-commenters</code> command.", style_body)
        ],
        [
            Paragraph("<b>Level 6<br/>Telemetry</b>", style_body),
            Paragraph("<code>engine/6_measure.py</code><br/>Analytics & Topic Engine", style_body),
            Paragraph("• Tracks human visits, AI referrers (ChatGPT, Perplexity), and AI crawlers (GPTBot).<br/>"
                      "• Imports Google Search Console CSV metrics.<br/>"
                      "• <b>AI Topic Recommender:</b> Suggests 3 next high-impact questions to write with 'Approve Topic' button.", style_body)
        ],
        [
            Paragraph("<b>Level 7<br/>A/B Test</b>", style_body),
            Paragraph("<code>engine/exporter.py</code><br/>PostHog Presentation Test", style_body),
            Paragraph("• Tests Code First vs Table First (Control) with identical facts and canonical URL.<br/>"
                      "• <b>Honest Reporting:</b> Reports <i>'Not enough data to call it'</i> when sessions &lt; 100.", style_body)
        ]
    ]
    t_stages = Table(stages_data, colWidths=[65, 155, 320])
    t_stages.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_INK),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PAPER),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_stages)
    story.append(Spacer(1, 10))

    # Page Break for Disqualification & Methodology
    story.append(PageBreak())

    # Section 3: Disqualification Prevention Guardrails
    story.append(Paragraph("3. Disqualification Prevention Guardrails", style_h1))
    story.append(Paragraph(
        "To protect the editorial integrity of AI Atlas India and strictly prevent candidate disqualification, the following guardrails are enforced across the codebase:",
        style_body
    ))

    guardrails_data = [
        [
            Paragraph("<b>Rule & Guardrail</b>", style_body_bold),
            Paragraph("<b>Disqualification Risk</b>", style_body_bold),
            Paragraph("<b>Technical Enforcement & Verification</b>", style_body_bold)
        ],
        [
            Paragraph("<b>1. No Self-Review</b>", style_body),
            Paragraph("Candidate reviewing their own section or using placeholder names.", style_body),
            Paragraph("Candidate Author is <b>Anshu Raj</b>. Independent Expert Reviewer is <b>Moksh Desai</b> (Developer, Indian-Language Speech-to-Speech Translation Systems). Database and FastAPI routes reject approval if reviewer name is Anshu Raj (HTTP 400).", style_body)
        ],
        [
            Paragraph("<b>2. Exact Footer Ownership</b>", style_body),
            Paragraph("Omitting or modifying the required ownership sentence.", style_body),
            Paragraph("Every HTML page displays verbatim:<br/><code>AI Atlas India is owned by Vyohm AI Private Limited, which also sells AI products. We cover every provider, Vyohm included, by the same rules.</code><br/>alongside <code>Built by Anshu Raj</code>. Verified by test.", style_body)
        ],
        [
            Paragraph("<b>3. Hard Cap of 20 Answers</b>", style_body),
            Paragraph("Publishing mass unverified answers (content spam).", style_body),
            Paragraph("<code>engine/exporter.py</code> enforces <code>MAX_PUBLISHED_ANSWERS = 20</code>. Only approved answers with real independent reviewer credentials are exported.", style_body)
        ],
        [
            Paragraph("<b>4. Commenter Privacy</b>", style_body),
            Paragraph("Storing community usernames or profile data.", style_body),
            Paragraph("Zero storage of YouTube/HN usernames. Social replies store only technical routing IDs. Command <code>python engine/5_social.py --purge-commenters</code> wipes all records at assignment end.", style_body)
        ],
        [
            Paragraph("<b>5. Zero-Guessing Rule</b>", style_body),
            Paragraph("Inventing unverified prices, latencies, or server locations.", style_body),
            Paragraph("Verified claims use solid dot <code>● [VALUE] · [SOURCE] · checked [DATE]</code>. Unsourced metrics rendered as dashed ring <code>◌ Not yet sourced</code>. Untraced claims permanently removed.", style_body)
        ],
        [
            Paragraph("<b>6. Secret Masking</b>", style_body),
            Paragraph("Exposing API keys, passwords, or personal emails.", style_body),
            Paragraph("FastAPI templates mask emails and tokens (e.g. <code>qi••••@gmail.com</code>). Excluded from Vercel via <code>.vercelignore</code>.", style_body)
        ],
        [
            Paragraph("<b>7. Honest A/B Reporting</b>", style_body),
            Paragraph("Declaring a premature winner in presentation experiments.", style_body),
            Paragraph("When sessions are &lt; 100, the analytics dashboard strictly reports <i>'Not enough data to call it'</i>.", style_body)
        ]
    ]
    t_guard = Table(guardrails_data, colWidths=[90, 150, 300])
    t_guard.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_INK),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PAPER),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_guard)
    story.append(Spacer(1, 10))

    # Section 4: Vyohm's 8 Evaluation Criteria
    story.append(Paragraph("4. Vyohm's Eight Evaluation Criteria Standard", style_h1))
    story.append(Paragraph(
        "Every provider profile (Sarvam AI, Bhashini, Krutrim, AI4Bharat) is structured around Vyohm's uniform 8 evaluation criteria. "
        "No subjective star ratings, numerical scores, or paid rankings are permitted.",
        style_body
    ))

    crit_data = [
        [
            Paragraph("<b>#</b>", style_body_bold),
            Paragraph("<b>Criterion</b>", style_body_bold),
            Paragraph("<b>Evaluation Scope for Indic Language AI</b>", style_body_bold),
            Paragraph("<b>Evidence Standard</b>", style_body_bold)
        ],
        [
            Paragraph("<b>01</b>", style_body),
            Paragraph("What it does, & for whom", style_body),
            Paragraph("ASR speech-to-text, NMT translation, TTS voice, Indic LLM. Target developer & enterprise team size.", style_body),
            Paragraph("Official docs & product pages", style_body)
        ],
        [
            Paragraph("<b>02</b>", style_body),
            Paragraph("Price in India", style_body),
            Paragraph("Pricing in INR, 18% GST applicability, minimum commitment term, and extra usage fees.", style_body),
            Paragraph("Public pricing page or dated quote", style_body)
        ],
        [
            Paragraph("<b>03</b>", style_body),
            Paragraph("Indian language support", style_body),
            Paragraph("Specific Indian languages and scripts supported for input, output, and developer support.", style_body),
            Paragraph("Official docs or tested benchmark", style_body)
        ],
        [
            Paragraph("<b>04</b>", style_body),
            Paragraph("Data location & privacy", style_body),
            Paragraph("Where customer payloads are stored (India data residency) and training permission terms.", style_body),
            Paragraph("Privacy policy & terms of service", style_body)
        ],
        [
            Paragraph("<b>05</b>", style_body),
            Paragraph("Fit with existing tools", style_body),
            Paragraph("SDKs (Python/Node), REST APIs, Exotel/Twilio voice pipelines, and WhatsApp integration.", style_body),
            Paragraph("API documentation & OpenAPI spec", style_body)
        ],
        [
            Paragraph("<b>06</b>", style_body),
            Paragraph("Setup & support in India", style_body),
            Paragraph("Instant self-serve API key vs entity vetting (Bhashini PAN/DPIIT), support hours & channels.", style_body),
            Paragraph("Support portal & named developers", style_body)
        ],
        [
            Paragraph("<b>07</b>", style_body),
            Paragraph("Contract & exit", style_body),
            Paragraph("Vendor lock-in, data export capabilities, credit expiration, and cancellation clauses.", style_body),
            Paragraph("Terms of service & MSA", style_body)
        ],
        [
            Paragraph("<b>08</b>", style_body),
            Paragraph("Evidence in practice", style_body),
            Paragraph("What named production users and our human expert say works well and what does not.", style_body),
            Paragraph("Dated quotes from named users", style_body)
        ]
    ]
    t_crit = Table(crit_data, colWidths=[20, 130, 254, 136])
    t_crit.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_INK),
        ('TEXTCOLOR', (0, 0), (-1, 0), COLOR_PAPER),
        ('BOX', (0, 0), (-1, -1), 1.5, COLOR_INK),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t_crit)
    story.append(Spacer(1, 10))

    # Page Break for Section Kit & Deployment
    story.append(PageBreak())

    # Section 5: Section Kit Design Compliance
    story.append(Paragraph("5. Section Kit Design Compliance (Plate 05)", style_h1))
    story.append(Paragraph(
        "The public frontend strictly enforces the printed-atlas aesthetic defined in <code>frontend/tokens.css</code>. "
        "No custom colours or rounded corners are introduced.",
        style_body
    ))

    design_rules = [
        Paragraph("• <b>Geometry:</b> <code>border-radius: 0</code> everywhere (sharp square corners, NO rounded cards or pills, NO drop shadows).", style_body),
        Paragraph("• <b>Borders & Rules:</b> <code>1.5px solid #0F1B2D</code> on boxes and buttons; <code>2px solid #0F1B2D</code> band rules; <code>1px solid #C5D1DB</code> row dividers.", style_body),
        Paragraph("• <b>Colour Tokens:</b> Ink <code>#0F1B2D</code>, Paper <code>#FFFFFF</code>, Sea <code>#E4EDF2</code>, Grid <code>#D5E1E9</code>, Muted <code>#43536B</code>, Signal <code>#F4C430</code>, Route <code>#C9361A</code>, and Plate 05 Indic <code>#8A5A1C</code> (5.9:1 contrast with white text).", style_body),
        Paragraph("• <b>Typography:</b> <code>Bricolage Grotesque</code> (700 headings), <code>IBM Plex Sans</code> (400/600 body), <code>IBM Plex Mono</code> (12px uppercase labels & dates).", style_body),
        Paragraph("• <b>Logo Usage:</b> Rendered directly from <code>frontend/logo.svg</code> unchanged. Never recoloured to <code>#8A5A1C</code>, never stretched, and never paired with provider logos.", style_body),
        Paragraph("• <b>Required Bylines:</b> <code>Reviewed and edited by [REVIEWER NAME], [ROLE] · AI-assisted draft · Reviewed [DATE]</code>.", style_body),
        Paragraph("• <b>Fact Marks:</b> Solid dot (<code>●</code>) for verified claims; dashed ring (<code>◌</code>) for <code>Not yet sourced</code>.", style_body),
        Paragraph("• <b>Vyohm Ownership Disclosure:</b> <code>◆ Owned by Vyohm, the company that runs this site</code> displayed whenever wotbot.ai or shotbot.ai appears.", style_body)
    ]
    for r in design_rules:
        story.append(r)
    story.append(Spacer(1, 10))

    # Section 6: Vercel Deployment & DNS Configuration
    story.append(Paragraph("6. Vercel Hosting & Production Setup Guide", style_h1))
    story.append(Paragraph(
        "To host <code>indic.aiatlasindia.com</code> cleanly on Vercel's free tier while keeping the private engine confidential, follow these steps:",
        style_body
    ))

    deploy_steps = [
        Paragraph("<b>Step 1: Git Push</b> — Commit the repository and push to GitHub. <code>.vercelignore</code> automatically excludes <code>engine/</code>, <code>*.db</code>, <code>.env</code>, <code>credentials.json</code>, <code>references/</code>, and <code>rules/</code> from the deployment artifact.", style_body),
        Paragraph("<b>Step 2: Vercel Project Setup</b> — In Vercel, click <i>Add New Project</i> and import the repository. The root <code>vercel.json</code> sets <code>\"outputDirectory\": \"frontend\"</code> and <code>\"cleanUrls\": true</code>, ensuring only static web assets are served.", style_body),
        Paragraph("<b>Step 3: Custom Domain Mapping</b> — In the Vercel project settings, navigate to <b>Domains</b> and enter <code>indic.aiatlasindia.com</code>.", style_body),
        Paragraph("<b>Step 4: DNS Configuration Reply</b> — Vercel displays the target CNAME (typically <code>cname.vercel-dns.com</code>). Reply to Soham Madnani's email (<code>careers@vyohm.com</code>) with the exact record type, name, and value. Vyohm maps the subdomain within 12 hours.", style_body),
        Paragraph("<b>Step 5: Search Console & Analytics Verification</b> — Verify traffic in GA4 (<code>G-WK0D46CCQZ</code>) and submit <code>https://indic.aiatlasindia.com/sitemap.xml</code> in Google Search Console via <code>qismcdeltat@gmail.com</code>.", style_body)
    ]
    for ds in deploy_steps:
        story.append(ds)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[PDF] Architecture document generated successfully at {PDF_PATH}")


if __name__ == "__main__":
    generate_pdf()
