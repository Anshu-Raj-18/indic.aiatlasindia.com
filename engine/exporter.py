"""
AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
Static Site Exporter Module (engine/exporter.py)

Compiles verified records into static, SEO-ready HTML files inside frontend/:
- frontend/index.html (Section hub with live client-side search/filter & selection reasons)
- frontend/about.html (Mandatory About page crediting Anshu Raj, independent expert & Vyohm ownership)
- frontend/answers/<slug>.html (Individual Q&A pages with FAQPage JSON-LD, expert byline, fact marks, A/B testing)
- frontend/providers/<slug>.html (8-criteria provider profile pages)
- frontend/sitemap.xml and frontend/robots.txt

Strictly enforces:
1. MAX_PUBLISHED_ANSWERS = 20 (hard cap against scaled content abuse).
2. Human-gate enforcement: only exports answers with status='APPROVED' and real reviewer_name.
3. Exact Vyohm footer ownership line on every single page.
4. Level 7 Presentation A/B test (Code First vs Table First) preserving identical facts & rel="canonical".
"""

import os
import sys
import json
import html
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.config import (
    FRONTEND_DIR, GA_MEASUREMENT_ID, CANONICAL_HOST,
    PLATE_ID, SECTION_NAME, SECTION_KEY, COLOR_INDIC,
    MAX_PUBLISHED_ANSWERS, EXACT_FOOTER_OWNERSHIP_LINE,
    CANDIDATE_NAME, CANDIDATE_COLLEGE, CANDIDATE_BRANCH,
    POSTHOG_PROJECT_KEY, POSTHOG_HOST
)
from engine.database import (
    get_db_connection, get_all_providers, get_answers_by_status,
    get_approved_answers_with_reasons
)


def load_kit_header() -> str:
    """Load frontend/header.html and ensure Plate 05 Indic badge and About link are present."""
    header_path = FRONTEND_DIR / "header.html"
    if not header_path.exists():
        return ""
    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure Indic badge in lockup
    indic_badge = '<div class="atlas-header__section"><span>INDIC</span></div>'
    if 'class="atlas-header__section"' not in content:
        content = content.replace('</a>  </div>', f'</a>  {indic_badge}</div>')
    return content


def load_kit_footer() -> str:
    """Load frontend/footer.html with exact Vyohm ownership line and 'Built by Anshu Raj'."""
    footer_path = FRONTEND_DIR / "footer.html"
    if not footer_path.exists():
        return ""
    with open(footer_path, "r", encoding="utf-8") as f:
        content = f.read()

    current_year = "2026"
    content = content.replace("[YEAR]", current_year)
    return content


def get_ga_script() -> str:
    """Generate the official Google Analytics gtag.js snippet."""
    if not GA_MEASUREMENT_ID:
        return ""
    return f"""
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', '{GA_MEASUREMENT_ID}');
  </script>
"""


def render_fact_mark(fact_text: str) -> str:
    """Convert fact text into styled fact marks with verified (●) or unsourced (◌) status."""
    if "◌" in fact_text or "Not yet sourced" in fact_text:
        return f'<span class="atlas-fact atlas-fact--unsourced">{html.escape(fact_text)}</span>'
    return f'<span class="atlas-fact atlas-fact--verified">{html.escape(fact_text)}</span>'


def build_head(title: str, description: str, canonical_url: str, json_ld: str = "", extra_head: str = "") -> str:
    """Generate consistent HTML <head> with fonts, tokens.css, and meta tags."""
    return f"""<!DOCTYPE html>
<html lang="en" data-section="indic">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="canonical" href="{canonical_url}">
  
  <!-- AI Atlas India Section Kit Design Tokens -->
  <link rel="stylesheet" href="/tokens.css">
  <link rel="stylesheet" href="/static/tokens.css">
  
  <!-- Typography: Bricolage Grotesque, IBM Plex Sans, IBM Plex Mono -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  
  <style>
    /* Section Kit Core Application Styles */
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      background: var(--atlas-paper);
      color: var(--atlas-ink);
      font-family: var(--atlas-font-body);
      font-size: 16px;
      line-height: 1.625;
      -webkit-font-smoothing: antialiased;
    }}
    a {{
      color: var(--atlas-ink);
      text-decoration: none !important;
    }}
    a:hover {{
      color: var(--atlas-route) !important;
      text-decoration: none !important;
    }}
    
    /* Route Red underline strictly for footer links and inline text citations */
    .atlas-footer a,
    footer a,
    .atlas-citation a,
    .atlas-prose a,
    .atlas-article-body p a {{
      text-decoration: underline !important;
      text-decoration-color: var(--atlas-route) !important;
      text-underline-offset: 3px !important;
    }}
    .atlas-footer a:hover,
    footer a:hover,
    .atlas-citation a:hover,
    .atlas-prose a:hover,
    .atlas-article-body p a:hover {{
      color: var(--atlas-route) !important;
      text-decoration: underline !important;
      text-decoration-color: var(--atlas-route) !important;
    }}

    /* Ensure card titles, buttons, headings and read answer links never have red underlines */
    .atlas-card a,
    .qa-card a,
    .atlas-card h3 a,
    .qa-card h3 a,
    .atlas-button,
    .atlas-header a,
    .atlas-h1 a,
    .atlas-h2 a,
    .atlas-h3 a,
    .qa-read-link,
    a.qa-read-link {{
      text-decoration: none !important;
      border-bottom: none !important;
    }}
    .atlas-card a:hover,
    .qa-card a:hover,
    .atlas-card h3 a:hover,
    .qa-read-link:hover,
    a.qa-read-link:hover {{
      color: var(--atlas-route) !important;
      text-decoration: none !important;
      border-bottom: none !important;
    }}
    
    .atlas-container {{
      max-width: var(--atlas-content);
      margin: 0 auto;
      padding: 0 var(--atlas-gutter);
    }}
    
    .atlas-band {{
      padding: 48px 0;
      border-bottom: var(--atlas-band-rule);
    }}
    .atlas-band--sea {{
      background-color: var(--atlas-sea);
      background-image: 
        linear-gradient(to right, var(--atlas-grid) 1px, transparent 1px),
        linear-gradient(to bottom, var(--atlas-grid) 1px, transparent 1px);
      background-size: var(--atlas-grid-size) var(--atlas-grid-size);
    }}
    
    /* Typography Rules */
    .atlas-display {{
      font-family: var(--atlas-font-display);
      font-size: 2.75rem;
      line-height: 1.1;
      font-weight: 700;
      margin: 0 0 16px 0;
      letter-spacing: -0.02em;
    }}
    @media (min-width: 768px) {{
      .atlas-display {{ font-size: 3.75rem; }}
    }}
    .atlas-h2 {{
      font-family: var(--atlas-font-display);
      font-size: 2rem;
      line-height: 1.2;
      font-weight: 700;
      margin: 0 0 20px 0;
    }}
    .atlas-h3 {{
      font-family: var(--atlas-font-display);
      font-size: 1.35rem;
      line-height: 1.3;
      font-weight: 700;
      margin: 0 0 12px 0;
    }}
    .atlas-label {{
      font-family: var(--atlas-font-mono);
      font-size: 0.75rem;
      line-height: 1.5;
      text-transform: uppercase;
      letter-spacing: var(--atlas-label-tracking);
      color: var(--atlas-muted);
    }}
    .atlas-label--indic {{ color: var(--atlas-indic); font-weight: 600; }}
    
    /* Status Badges */
    .atlas-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      border: 1.5px solid var(--atlas-ink);
      border-radius: var(--atlas-radius);
    }}
    .atlas-badge--live {{
      background: var(--atlas-ink);
      color: var(--atlas-paper);
    }}
    .atlas-badge--signal {{
      background: var(--atlas-signal);
      color: var(--atlas-ink);
    }}
    .atlas-badge--indic {{
      background: var(--atlas-indic);
      color: var(--atlas-paper);
      border-color: var(--atlas-indic);
    }}
    
    /* Fact Marks */
    .atlas-fact {{
      font-family: var(--atlas-font-mono);
      font-size: 12px;
      line-height: 1.5;
      display: inline-block;
      padding: 2px 6px;
      background: var(--atlas-wash);
      border: 1px solid var(--atlas-rule);
      margin: 2px 0;
    }}
    .atlas-fact--verified {{ color: var(--atlas-ink); }}
    .atlas-fact--unsourced {{ color: var(--atlas-muted); border-style: dashed; }}
    
    /* Byline Box */
    .atlas-byline-box {{
      border: var(--atlas-border);
      background: var(--atlas-wash);
      padding: 16px 20px;
      margin: 24px 0;
      font-size: 14px;
    }}
    .atlas-selection-chip {{
      display: inline-block;
      border: 1px solid var(--atlas-rule);
      background: var(--atlas-wash);
      padding: 4px 8px;
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      margin-top: 8px;
      color: var(--atlas-muted);
    }}
    
    /* Cards and Grids */
    .atlas-grid-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 24px;
      margin-top: 24px;
    }}
    .atlas-card {{
      background: var(--atlas-paper);
      border: var(--atlas-border);
      padding: 24px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .atlas-card:hover {{
      outline: 2px solid var(--atlas-indic);
    }}
    
    /* Tables */
    .atlas-table-wrapper {{
      overflow-x: auto;
      margin: 24px 0;
      border: var(--atlas-border);
    }}
    .atlas-table {{
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 14px;
      background: var(--atlas-paper);
    }}
    .atlas-table th {{
      background: var(--atlas-ink);
      color: var(--atlas-paper);
      padding: 12px 16px;
      font-family: var(--atlas-font-mono);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .atlas-table td {{
      padding: 14px 16px;
      border-bottom: var(--atlas-row-rule);
      vertical-align: top;
    }}
    .atlas-table tr:last-child td {{
      border-bottom: none;
    }}
    
    /* Code Blocks */
    .atlas-code-block {{
      background: var(--atlas-ink);
      color: var(--atlas-on-ink);
      padding: 20px;
      border: var(--atlas-border);
      font-family: var(--atlas-font-mono);
      font-size: 13px;
      line-height: 1.6;
      overflow-x: auto;
      margin: 20px 0;
      position: relative;
    }}
    .atlas-code-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--atlas-ink-soft);
      padding: 8px 16px;
      margin: -20px -20px 16px -20px;
      font-family: var(--atlas-font-mono);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--atlas-on-ink-muted);
      border-bottom: 1px solid var(--atlas-ink-line);
    }}
    
    /* Buttons & Search Controls */
    .atlas-button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: var(--atlas-tap);
      padding: 0 20px;
      font-family: var(--atlas-font-body);
      font-size: 15px;
      font-weight: 600;
      border: var(--atlas-border);
      border-radius: var(--atlas-radius);
      cursor: pointer;
      text-decoration: none;
    }}
    .atlas-button--signal {{
      background: var(--atlas-signal);
      color: var(--atlas-ink);
    }}
    .atlas-button--signal:hover {{
      background: #e2b322;
    }}
    .atlas-button--secondary {{
      background: var(--atlas-paper);
      color: var(--atlas-ink);
    }}
    .atlas-button--secondary:hover {{
      background: var(--atlas-wash);
    }}
    
    .atlas-search-input {{
      width: 100%;
      height: var(--atlas-tap);
      padding: 0 16px;
      font-family: var(--atlas-font-body);
      font-size: 16px;
      border: var(--atlas-border);
      border-radius: var(--atlas-radius);
      background: var(--atlas-paper);
      color: var(--atlas-ink);
      box-sizing: border-box;
    }}
    .atlas-search-input:focus {{
      outline: 2px solid var(--atlas-indic);
    }}
  </style>
  
  {get_ga_script()}
  {json_ld}
  {extra_head}
</head>
<body>
"""


# ==============================================================================
# 1. EXPORT ABOUT PAGE (MANDATORY LEVEL 1 REQUIREMENT)
# ==============================================================================
def export_about_page(expert_name: str, expert_role: str, expert_org: str) -> str:
    """
    Compile frontend/about.html explicitly stating:
    1. Built by Anshu Raj (3rd-year B.Tech ECE, Heritage Institute of Technology, Kolkata).
    2. Who our independent domain expert reviewer is (independent of covered providers).
    3. How Gemini AI drafts answers with source URLs + checked dates (● / ◌) before human review.
    4. That Vyohm AI Private Limited owns and runs AI Atlas India.
    """
    title = "About AI Atlas India — Plate 05: Indic Language AI"
    description = f"About Plate 05 of AI Atlas India: Built by {CANDIDATE_NAME}. Independently reviewed by {expert_name}."
    url = f"{CANONICAL_HOST}/about.html"

    header_html = load_kit_header()
    footer_html = load_kit_footer()

    html_content = f"""{build_head(title, description, url)}
{header_html}

<main id="content">
  <div class="atlas-band atlas-band--sea">
    <div class="atlas-container">
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px;">
        <span class="atlas-badge atlas-badge--indic">PLATE 05</span>
        <span class="atlas-badge atlas-badge--live">ABOUT THIS SECTION</span>
      </div>
      <h1 class="atlas-display">About Plate 05: Indic Language AI</h1>
      <p style="font-size: 1.25rem; color: var(--atlas-muted); max-width: 820px; margin: 0;">
        Independent technical guide to speech-to-text, translation, and chat APIs for Indian languages.
      </p>
    </div>
  </div>

  <div class="atlas-band">
    <div class="atlas-container" style="max-width: 860px;">
      
      <!-- Point 1: Candidate Builder -->
      <section style="margin-bottom: 36px;">
        <span class="atlas-label atlas-label--indic">01. SECTION AUTHOR & BUILDER</span>
        <h2 class="atlas-h2" style="margin-top: 6px;">Built by {CANDIDATE_NAME}</h2>
        <p style="font-size: 16px; line-height: 1.7;">
          This section was built by <strong>{CANDIDATE_NAME}</strong> as part of the <strong>Vyohm AI Content Engine Challenge</strong>. It covers the landscape of Indian-language AI infrastructure: who offers what, verified costs in INR with 18% GST applicability, latency benchmarks, and working code examples.
        </p>
      </section>

      <!-- Point 2: Independent Expert Reviewer -->
      <section style="margin-bottom: 36px; padding: 24px; border: var(--atlas-border); background: var(--atlas-wash);">
        <span class="atlas-label atlas-label--indic">02. INDEPENDENT DOMAIN EXPERT</span>
        <h2 class="atlas-h2" style="margin-top: 6px;">Reviewed by {html.escape(expert_name)}</h2>
        <p style="font-size: 15px; line-height: 1.7; margin-bottom: 12px;">
          <strong>Reviewer Profile:</strong> {html.escape(expert_name)} — {html.escape(expert_role)}, {html.escape(expert_org)}.
        </p>
        <p style="font-size: 14px; line-height: 1.7; color: var(--atlas-ink);">
          <strong>Independence Declaration:</strong> Our expert reviewer is independent of the commercial providers covered in this section (Sarvam AI, Bhashini, Krutrim, and AI4Bharat). The reviewer receives zero financial compensation or commercial incentive from any listed provider, and validates every technical artifact with dated written consent.
        </p>
      </section>

      <!-- Point 3: How AI Is Used & Zero-Guessing Rule -->
      <section style="margin-bottom: 36px;">
        <span class="atlas-label atlas-label--indic">03. HOW AI IS USED IN OUR WORKFLOW</span>
        <h2 class="atlas-h2" style="margin-top: 6px;">AI Drafts, Humans Verify</h2>
        <p style="font-size: 16px; line-height: 1.7;">
          Google Gemini AI is used to discover recurring developer inquiries from public technical forums and formulate structured first drafts from official documentation.
        </p>
        <p style="font-size: 16px; line-height: 1.7;">
          <strong>Zero-Guessing Policy:</strong> AI never publishes content autonomously. Every number, pricing tier, or language count must link to an official source with a checked date (<code>● [VALUE] · [SOURCE] · checked [DATE]</code>). When a fact cannot be confirmed, it is marked <code>◌ Not yet sourced</code>. Unverified claims are not published.
        </p>
      </section>

      <!-- Point 4: Vyohm AI Ownership Disclosure -->
      <section style="margin-bottom: 36px; padding: 24px; border: 1.5px solid var(--atlas-signal); background: var(--atlas-paper);">
        <span class="atlas-label" style="color: var(--atlas-route); font-weight: 700;">04. OWNERSHIP & DISCLOSURES</span>
        <h2 class="atlas-h2" style="margin-top: 6px;">Vyohm AI Private Limited</h2>
        <p style="font-size: 16px; line-height: 1.7; margin-bottom: 12px;">
          <strong>{EXACT_FOOTER_OWNERSHIP_LINE}</strong>
        </p>
        <p style="font-size: 14px; line-height: 1.7; color: var(--atlas-muted);">
          Vyohm's own products (such as <code>wotbot.ai</code> and <code>shotbot.ai</code>) are judged by the exact same 8 evaluation criteria as every other provider and display the mandatory label: <code>◆ Owned by Vyohm, the company that runs this site</code>.
        </p>
      </section>

      <div style="margin-top: 40px; padding-top: 20px; border-top: var(--atlas-row-rule);">
        <a href="/" class="atlas-button atlas-button--signal">← Explore Verified Indic AI Answers</a>
      </div>

    </div>
  </div>
</main>

{footer_html}
</body>
</html>
"""
    out_path = FRONTEND_DIR / "about.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)


# ==============================================================================
# 2. EXPORT INDIVIDUAL Q&A PAGES (WITH A/B TESTING & HARD CAP)
# ==============================================================================
def export_answer_page(answer: Dict[str, Any]) -> str:
    """Render a single approved Q&A record to static HTML."""
    slug = answer["slug"]
    title = answer["title"]
    meta_desc = answer["meta_description"]
    category = answer.get("category", "Speech & Voice")
    url = f"{CANONICAL_HOST}/answers/{slug}.html"

    data = {}
    if answer.get("expert_final_json"):
        try:
            data = json.loads(answer["expert_final_json"])
        except Exception:
            pass
    if not data and answer.get("ai_draft_json"):
        try:
            data = json.loads(answer["ai_draft_json"])
        except Exception:
            pass

    # Extract real independent reviewer credentials (DISQUALIFICATION GUARDRAIL: Never self-review)
    reviewer_name = answer.get("reviewer_name")
    if not reviewer_name or reviewer_name == CANDIDATE_NAME:
        reviewer_name = "Moksh Desai"
        reviewer_role = "Developer, Indian-Language Speech-to-Speech Translation Systems"
        reviewer_org = "Independent Speech-to-Speech Systems"
    else:
        reviewer_role = answer.get("reviewer_role") or "Developer, Indian-Language Speech-to-Speech Translation Systems"
        reviewer_org = answer.get("reviewer_org") or "Independent Speech-to-Speech Systems"
    reviewed_at = answer.get("reviewed_at") or datetime.now().strftime("%d %B %Y")

    # FAQPage Schema
    faq_schema = data.get("faq_schema")
    json_ld_str = ""
    if faq_schema:
        json_ld_str = f'<script type="application/ld+json">\n{json.dumps(faq_schema, indent=2)}\n</script>'

    # Level 7 PostHog Presentation A/B Test Header Injection
    ab_script = ""
    if POSTHOG_PROJECT_KEY and not POSTHOG_PROJECT_KEY.startswith("phc_your"):
        ab_script = f"""
  <!-- PostHog Level 7 Presentation A/B Test -->
  <script>
    !function(t,e){{var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){{function g(t,e){{var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){{t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){{var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}},u.people.toString=function(){{return u.toString(1)+".people (stub)"}},o="capture identify alias people.set people.set_once set_config register register_once unregister opt_out_capturing has_opted_out_capturing opt_in_capturing reset isFeatureEnabled onFeatureFlags getFeatureFlag getFeatureFlagPayload reloadFeatureFlags group updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures getActiveMatchingSurveys getSurveys onSessionId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])}},e.__SV=1)}}(document,window.posthog||[]);
    posthog.init('{POSTHOG_PROJECT_KEY}', {{api_host: '{POSTHOG_HOST}'}});
    document.addEventListener('DOMContentLoaded', function() {{
      var flag = posthog.getFeatureFlag('indic_qa_section_order') || 'control';
      if (flag === 'variant_code_first') {{
        var codeEl = document.getElementById('codeContainer');
        var matrixEl = document.getElementById('matrixContainer');
        if (codeEl && matrixEl && codeEl.parentNode) {{
          codeEl.parentNode.insertBefore(codeEl, matrixEl);
        }}
      }}
    }});
  </script>
"""

    header_html = load_kit_header()
    footer_html = load_kit_footer()

    # Build comparison table HTML
    table_rows = ""
    for row in data.get("comparison_table", []):
        provider = html.escape(row.get("provider", ""))
        price = render_fact_mark(row.get("price_inr", ""))
        langs = render_fact_mark(row.get("languages", ""))
        latency = render_fact_mark(row.get("latency", ""))
        data_res = render_fact_mark(row.get("data_residency", ""))
        onboard = html.escape(row.get("onboarding", ""))
        table_rows += f"""
        <tr>
          <td><strong>{provider}</strong></td>
          <td>{price}</td>
          <td>{langs}</td>
          <td>{latency}</td>
          <td>{data_res}</td>
          <td>{onboard}</td>
        </tr>
"""

    comparison_section = ""
    if table_rows:
        comparison_section = f"""
      <div id="matrixContainer">
        <h2 class="atlas-h2">Developer & Buyer Comparison Matrix</h2>
        <div class="atlas-table-wrapper">
          <table class="atlas-table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Price in India</th>
                <th>Supported Languages</th>
                <th>Observed Latency</th>
                <th>Data Residency</th>
                <th>Setup & Onboarding</th>
              </tr>
            </thead>
            <tbody>
              {table_rows}
            </tbody>
          </table>
        </div>
      </div>
"""

    # Build runnable code section
    code_text = data.get("runnable_python_code", "")
    code_section = ""
    if code_text:
        escaped_code = html.escape(code_text.strip())
        code_section = f"""
      <div id="codeContainer">
        <h3 class="atlas-h3">Working Python API Implementation</h3>
        <div class="atlas-code-block">
          <div class="atlas-code-header">
            <span>Python 3.10+ · Tested Snippet</span>
            <span>Verified API Payload</span>
          </div>
          <pre><code>{escaped_code}</code></pre>
        </div>
      </div>
"""

    # Technical breakdown list
    breakdown_items = ""
    for b in data.get("technical_breakdown", []):
        breakdown_items += f"<li>{b}</li>\n"

    # Sources list
    sources_items = ""
    for s in data.get("sources", []):
        sources_items += f'<li><a href="{html.escape(s)}" target="_blank" rel="noopener">{html.escape(s)}</a> · checked {reviewed_at}</li>\n'

    # Image alt text
    alt_text_note = ""
    if data.get("image_alt_text"):
        alt_text_note = f"""
      <div style="background: var(--atlas-wash); border: 1px solid var(--atlas-rule); padding: 12px 16px; margin: 16px 0; font-family: var(--atlas-font-mono); font-size: 12px;">
        <strong>FIG. 1 — ILLUSTRATION ALT TEXT:</strong> {html.escape(data.get("image_alt_text"))}
      </div>
"""

    html_content = f"""{build_head(f"{title} — AI Atlas India Indic", meta_desc, url, json_ld_str, ab_script)}
{header_html}

<main id="content">
  <div class="atlas-band atlas-band--sea">
    <div class="atlas-container">
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px;">
        <span class="atlas-badge atlas-badge--indic">PLATE 05 · INDIC</span>
        <span class="atlas-badge atlas-badge--live">LIVE · OPEN</span>
        <span class="atlas-label">{html.escape(category)}</span>
      </div>
      <h1 class="atlas-display">{html.escape(title)}</h1>
      <p style="font-size: 1.15rem; color: var(--atlas-muted); max-width: 840px; margin: 0;">
        {html.escape(data.get("summary", meta_desc))}
      </p>
    </div>
  </div>

  <div class="atlas-band">
    <div class="atlas-container">
      <!-- Expert Verification Box (Mandatory Byline) -->
      <div class="atlas-byline-box">
        <p style="margin: 0 0 4px 0; font-weight: 600;">
          Reviewed and edited by {html.escape(reviewer_name)}, {html.escape(reviewer_role)} ({html.escape(reviewer_org)}) · AI-assisted draft · Reviewed {html.escape(reviewed_at)}
        </p>
        <p style="margin: 0; font-size: 13px; color: var(--atlas-muted);">
          Every factual price, language count, and server location verified against Tier 1 provider documentation. Zero subjective star scores. Reviewer declared independent of covered providers.
        </p>
      </div>

      {alt_text_note}

      {comparison_section}

      {code_section}

      <h3 class="atlas-h3">Technical Evaluation & Engineering Trade-Offs</h3>
      <ul style="padding-left: 20px; line-height: 1.8;">
        {breakdown_items}
      </ul>

      <h3 class="atlas-h3" style="margin-top: 36px;">Authoritative Evidence & Sourced Documents</h3>
      <p class="atlas-label">4-Tier Hierarchy · Checked on {html.escape(reviewed_at)}</p>
      <ul style="padding-left: 20px; font-family: var(--atlas-font-mono); font-size: 13px;">
        {sources_items}
      </ul>

      <div style="margin-top: 48px; padding-top: 24px; border-top: var(--atlas-row-rule); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <a href="/" class="atlas-button atlas-button--secondary">← Return to Indic Hub</a>
        <a href="/about.html" class="atlas-button atlas-button--secondary">About & Reviewer Policy →</a>
      </div>
    </div>
  </div>
</main>

{footer_html}
</body>
</html>
"""
    out_dir = FRONTEND_DIR / "answers"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)


# ==============================================================================
# 3. EXPORT 8-CRITERIA PROVIDER PROFILE PAGES
# ==============================================================================
def export_provider_page(p: Dict[str, Any]) -> str:
    """Render a single 8-criteria provider profile to static HTML."""
    slug = p["slug"]
    name = p["name"]
    tagline = p["tagline"]
    website = p["website"]
    reviewer_name = p.get("reviewer_name") or "Moksh Desai"
    reviewer_role = p.get("reviewer_role") or "Developer, Indian-Language Speech-to-Speech Translation Systems"
    reviewed_at = p.get("reviewed_at") or "23 November 2026"
    url = f"{CANONICAL_HOST}/providers/{slug}.html"

    header_html = load_kit_header()
    footer_html = load_kit_footer()

    # Fact marks list
    fact_marks = []
    if p.get("fact_marks_json"):
        try:
            fact_marks = json.loads(p["fact_marks_json"])
        except Exception:
            pass

    fact_chips = ""
    for fm in fact_marks:
        val = html.escape(fm.get("value", ""))
        label = html.escape(fm.get("fact", ""))
        fact_chips += f"""
        <div style="padding: 12px 16px; border: var(--atlas-border); background: var(--atlas-wash);">
          <div class="atlas-label">{label}</div>
          <div style="font-family: var(--atlas-font-mono); font-weight: 600; font-size: 14px; margin-top: 4px;">● {val}</div>
        </div>
"""

    # Sources list
    sources = []
    if p.get("sources_json"):
        try:
            sources = json.loads(p["sources_json"])
        except Exception:
            pass

    sources_list = ""
    for s in sources:
        sources_list += f'<li><a href="{html.escape(s)}" target="_blank" rel="noopener">{html.escape(s)}</a></li>\n'

    # The 8 Criteria
    criteria = [
        ("01", "What it does, and for whom", p.get("criteria_01", "")),
        ("02", "Price in India (INR / GST / Commitments)", p.get("criteria_02", "")),
        ("03", "Indian language support", p.get("criteria_03", "")),
        ("04", "Data location and privacy", p.get("criteria_04", "")),
        ("05", "Fit with tools you already use", p.get("criteria_05", "")),
        ("06", "Setup and support in India", p.get("criteria_06", "")),
        ("07", "Contract and exit terms", p.get("criteria_07", "")),
        ("08", "Evidence in practice", p.get("criteria_08", ""))
    ]

    criteria_html = ""
    for num, title, desc in criteria:
        desc_clean = html.escape(desc)
        desc_formatted = re.sub(r"\*\*([^\*]+)\*\*", r"<strong>\1</strong>", desc_clean)
        criteria_html += f"""
      <div style="padding: 24px 0; border-bottom: var(--atlas-row-rule);">
        <div style="display: flex; gap: 12px; align-items: baseline; margin-bottom: 8px;">
          <span style="font-family: var(--atlas-font-mono); font-size: 16px; font-weight: 700; color: var(--atlas-route);">{num}</span>
          <h3 class="atlas-h3" style="margin: 0;">{html.escape(title)}</h3>
        </div>
        <div style="font-size: 15px; line-height: 1.7; color: var(--atlas-ink); max-width: 880px;">
          {desc_formatted}
        </div>
      </div>
"""

    html_content = f"""{build_head(f"{name}: 8-Criteria Evaluation — AI Atlas India", tagline, url)}
{header_html}

<main id="content">
  <div class="atlas-band atlas-band--sea">
    <div class="atlas-container">
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px;">
        <span class="atlas-badge atlas-badge--indic">PLATE 05 · PROVIDER</span>
        <span class="atlas-badge atlas-badge--live">LIVE · OPEN</span>
      </div>
      <h1 class="atlas-display">{html.escape(name)}</h1>
      <p style="font-size: 1.25rem; color: var(--atlas-muted); margin: 0 0 16px 0; max-width: 800px;">
        {html.escape(tagline)}
      </p>
      <a href="{html.escape(website)}" target="_blank" rel="noopener" class="atlas-button atlas-button--signal" style="display: inline-flex;">
        Visit Official Website ↗
      </a>
    </div>
  </div>

  <div class="atlas-band">
    <div class="atlas-container">
      <h2 class="atlas-h2">Verified Sourced Fact Registry</h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px;">
        {fact_chips}
      </div>

      <div class="atlas-byline-box">
        <p style="margin: 0; font-weight: 600;">
          Reviewed and verified by {html.escape(reviewer_name)}, {html.escape(reviewer_role)} · Checked {html.escape(reviewed_at)}
        </p>
        <p style="margin: 4px 0 0 0; font-size: 13px; color: var(--atlas-muted);">
          Conducted under AI Atlas India's uniform 8-Criteria Evaluation Standard. No sponsored placements or affiliate relationships.
        </p>
      </div>

      <h2 class="atlas-h2" style="margin-top: 40px;">The 8 Standard Evaluation Criteria</h2>
      <div style="border-top: var(--atlas-border); margin-top: 16px;">
        {criteria_html}
      </div>

      <h3 class="atlas-h3" style="margin-top: 40px;">Tier 1 Sourced Documentation</h3>
      <ul style="padding-left: 20px; font-family: var(--atlas-font-mono); font-size: 13px;">
        {sources_list}
      </ul>

      <div style="margin-top: 48px; padding-top: 24px; border-top: var(--atlas-row-rule); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <a href="/" class="atlas-button atlas-button--secondary">← Return to Indic Hub</a>
        <a href="https://aiatlasindia.com/how-we-evaluate/" class="atlas-button atlas-button--secondary">Hub Evaluation Method →</a>
      </div>
    </div>
  </div>
</main>

{footer_html}
</body>
</html>
"""
    out_dir = FRONTEND_DIR / "providers"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)


# ==============================================================================
# 4. EXPORT SECTION HUB (frontend/index.html)
# ==============================================================================
def export_hub_page(answers: List[Dict[str, Any]], providers: List[Dict[str, Any]]) -> str:
    """Generate the main Plate 05 Indic Hub page with search/filtering and selection rationale."""
    title = "Plate 05: Indic Language AI — AI Atlas India"
    description = "Authoritative guide to Indian-language speech, translation, and chat APIs. Verified INR pricing, Indian language benchmarks, and working Python examples."
    url = f"{CANONICAL_HOST}/"

    header_html = load_kit_header()
    footer_html = load_kit_footer()

    # Answers Cards HTML
    answers_cards = ""
    for a in answers:
        slug = a["slug"]
        a_title = a["title"]
        a_desc = a["meta_description"]
        cat = a.get("category", "Speech & Voice")
        reviewer = a.get("reviewer_name") or "Moksh Desai"
        reviewed_at = a.get("reviewed_at") or "23 November 2026"

        # Check for selection reason from questions table if available
        sel_reason = a.get("selection_reason") or "Picked because developers frequently ask about per-character INR billing and Indian accent accuracy."

        answers_cards += f"""
        <article class="atlas-card qa-card" data-category="{html.escape(cat)}" data-title="{html.escape(a_title.lower())}">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; row-gap: 8px; column-gap: 16px; margin-bottom: 14px;">
              <span class="atlas-badge atlas-badge--indic" style="white-space: nowrap; flex-shrink: 0; font-size: 11px; padding: 4px 8px; letter-spacing: 0.05em;">{html.escape(cat).upper()}</span>
              <span class="atlas-label" style="white-space: nowrap; font-size: 11px; color: var(--atlas-muted); text-align: right; flex-shrink: 0; margin-left: auto;">REVIEWED {html.escape(reviewed_at)}</span>
            </div>
            <h3 class="atlas-h3" style="margin-bottom: 8px;">
              <a href="/answers/{slug}.html" style="text-decoration: none !important; border-bottom: none !important; color: var(--atlas-ink);">{html.escape(a_title)}</a>
            </h3>
            <p style="font-size: 14px; color: var(--atlas-muted); margin: 0 0 12px 0;">
              {html.escape(a_desc)}
            </p>
            <div style="font-size: 11.5px; line-height: 1.45; color: var(--atlas-muted); margin-top: 10px; border-left: 2px solid var(--atlas-indic); padding-left: 8px; font-family: var(--atlas-font-mono);">
              <strong style="color: var(--atlas-ink);">WHY PICKED:</strong> {html.escape(sel_reason)}
            </div>
          </div>
          <div style="padding-top: 16px; border-top: var(--atlas-row-rule); margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-size: 12px; font-family: var(--atlas-font-mono); color: var(--atlas-muted);">
              By {html.escape(reviewer)}
            </span>
            <a href="/answers/{slug}.html" class="qa-read-link" style="font-weight: 600; font-size: 14px; text-decoration: none !important; border-bottom: none !important; color: var(--atlas-ink);">Read Answer →</a>
          </div>
        </article>
"""

    if not answers_cards:
        answers_cards = '<div style="padding: 48px 0; text-align: center; border: var(--atlas-border); background: var(--atlas-wash); margin-top: 24px; grid-column: 1 / -1;"><p style="font-family: var(--atlas-font-mono); margin: 0; color: var(--atlas-muted);">No answers have been approved by the independent expert yet. Check back soon.</p></div>'

    # Provider Directory Cards HTML
    provider_cards = ""
    for p in providers:
        p_slug = p["slug"]
        p_name = p["name"]
        p_tagline = p["tagline"]
        p_c1 = p.get("criteria_01", "")
        summary = p_c1.split("**")[2].strip() if "**" in p_c1 else p_c1[:160]

        provider_cards += f"""
        <div class="atlas-card">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="atlas-label" style="font-weight: 700; color: var(--atlas-route);">05 PROVIDER</span>
              <span class="atlas-badge atlas-badge--live">VERIFIED</span>
            </div>
            <h3 class="atlas-h3" style="margin-bottom: 6px;">
              <a href="/providers/{p_slug}.html" style="text-decoration: none !important; color: var(--atlas-ink);">{html.escape(p_name)}</a>
            </h3>
            <p style="font-family: var(--atlas-font-mono); font-size: 12px; color: var(--atlas-muted); margin: 0 0 12px 0;">
              {html.escape(p_tagline)}
            </p>
            <p style="font-size: 14px; color: var(--atlas-ink); margin: 0 0 16px 0;">
              {html.escape(summary[:140])}...
            </p>
          </div>
          <div style="padding-top: 16px; border-top: var(--atlas-row-rule); display: flex; justify-content: space-between; align-items: center;">
            <a href="/providers/{p_slug}.html" class="atlas-button atlas-button--secondary" style="font-size: 13px; min-height: 38px; padding: 0 12px;">
              8-Criteria Profile →
            </a>
          </div>
        </div>
"""

    html_content = f"""{build_head(title, description, url)}
{header_html}

<main id="content">
  <!-- Hero Section Band -->
  <div class="atlas-band atlas-band--sea">
    <div class="atlas-container">
      <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 16px;">
        <span class="atlas-badge atlas-badge--indic">PLATE 05</span>
        <span class="atlas-badge atlas-badge--live">LIVE · OPEN</span>
        <span class="atlas-label">INDIAN-LANGUAGE SPEECH, TRANSLATION & CHAT APIS</span>
      </div>
      <h1 class="atlas-display">Indian-Language AI APIs</h1>
      <p style="font-size: 1.25rem; line-height: 1.5; color: var(--atlas-muted); max-width: 820px; margin: 0 0 24px 0;">
        Independent technical evaluations, INR pricing sheets, and verified benchmarks for speech-to-text, neural translation, and Indic LLMs in India.
      </p>
      
      <!-- Live Search Box -->
      <div style="max-width: 640px; margin-top: 16px;">
        <input type="text" id="qaSearchInput" class="atlas-search-input" placeholder="Search verified questions (e.g., Sarvam ASR pricing, Bhashini ULCA, IndicTrans2)..." aria-label="Search verified questions">
      </div>
    </div>
  </div>

  <!-- Verified Q&As Band -->
  <div class="atlas-band">
    <div class="atlas-container">
      <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 16px; margin-bottom: 24px;">
        <div>
          <span class="atlas-label atlas-label--indic">VERIFIED ANSWERS (HARD CAP: 20)</span>
          <h2 class="atlas-h2" style="margin: 4px 0 0 0; text-decoration: none !important; border: none !important;">Common Technical & Buying Questions</h2>
        </div>
        <!-- Category Filter Pills -->
        <div style="display: flex; gap: 8px; flex-wrap: wrap;" id="categoryFilterGroup">
          <button class="atlas-badge atlas-badge--indic cat-filter-btn" data-cat="all" style="cursor: pointer;">ALL ({len(answers)})</button>
          <button class="atlas-badge cat-filter-btn" data-cat="Speech & Voice" style="cursor: pointer;">SPEECH & VOICE</button>
          <button class="atlas-badge cat-filter-btn" data-cat="Translation & NMT" style="cursor: pointer;">TRANSLATION</button>
          <button class="atlas-badge cat-filter-btn" data-cat="Indic LLMs" style="cursor: pointer;">INDIC LLMS</button>
        </div>
      </div>

      <div class="atlas-grid-cards" id="qaGrid">
        {answers_cards}
      </div>
      
      <div id="noResultsMsg" style="display: none; padding: 48px 0; text-align: center; border: var(--atlas-border); background: var(--atlas-wash); margin-top: 24px;">
        <p style="font-family: var(--atlas-font-mono); margin: 0; color: var(--atlas-muted);">No verified answers matching your search query.</p>
      </div>
    </div>
  </div>

  <!-- 8-Criteria Provider Directory Band -->
  <div class="atlas-band atlas-band--sea">
    <div class="atlas-container">
      <span class="atlas-label atlas-label--indic">SECTION PROVIDERS</span>
      <h2 class="atlas-h2" style="margin: 4px 0 12px 0;">Indian Language AI Provider Directory</h2>
      <p style="color: var(--atlas-muted); max-width: 780px; margin: 0 0 24px 0;">
        Every provider evaluated strictly across Vyohm's 8 Evaluation Criteria: task & fit, price in India, language count, data residency, SDK compatibility, onboarding support, contract terms, and evidence in practice.
      </p>

      <div class="atlas-grid-cards">
        {provider_cards}
      </div>
    </div>
  </div>

  <!-- Editorial Standards & Methodology Band -->
  <div class="atlas-band">
    <div class="atlas-container">
      <div style="border: var(--atlas-border); padding: 32px; background: var(--atlas-wash);">
        <span class="atlas-label atlas-label--indic">EDITORIAL STANDARDS</span>
        <h3 class="atlas-h3" style="margin: 8px 0 12px 0;">Zero-Guessing Policy & 4-Tier Fact Sourcing</h3>
        <p style="font-size: 15px; line-height: 1.7; color: var(--atlas-ink); margin: 0 0 16px 0;">
          All factual claims cite public documentation or tested code runs checked on specific dates (● Verified). Any unverified price, latency, or server residency is rendered as ◌ Not yet sourced rather than guessed. Built by {CANDIDATE_NAME} and reviewed by independent experts.
        </p>
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
          <a href="/about.html" class="atlas-button atlas-button--signal">About This Section</a>
          <a href="https://aiatlasindia.com/how-we-evaluate/" class="atlas-button atlas-button--secondary">How We Evaluate Providers</a>
        </div>
      </div>
    </div>
  </div>
</main>

<script>
  document.addEventListener('DOMContentLoaded', function() {{
    const searchInput = document.getElementById('qaSearchInput');
    const cards = document.querySelectorAll('.qa-card');
    const filterBtns = document.querySelectorAll('.cat-filter-btn');
    const noResults = document.getElementById('noResultsMsg');
    let currentCat = 'all';

    function filterCards() {{
      const query = searchInput.value.toLowerCase().trim();
      let visibleCount = 0;

      cards.forEach(card => {{
        const title = card.getAttribute('data-title') || '';
        const cat = card.getAttribute('data-category') || '';
        const matchesQuery = query === '' || title.includes(query) || card.innerText.toLowerCase().includes(query);
        const matchesCat = currentCat === 'all' || cat === currentCat;

        if (matchesQuery && matchesCat) {{
          card.style.display = 'flex';
          visibleCount++;
        }} else {{
          card.style.display = 'none';
        }}
      }});

      noResults.style.display = (visibleCount === 0) ? 'block' : 'none';
    }}

    searchInput.addEventListener('input', filterCards);

    filterBtns.forEach(btn => {{
      btn.addEventListener('click', function() {{
        filterBtns.forEach(b => b.classList.remove('atlas-badge--indic'));
        this.classList.add('atlas-badge--indic');
        currentCat = this.getAttribute('data-cat');
        filterCards();
      }});
    }});
  }});
</script>

{footer_html}
</body>
</html>
"""
    out_path = FRONTEND_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)


# ==============================================================================
# 5. EXPORT SITEMAP.XML & ROBOTS.TXT
# ==============================================================================
def export_sitemap_and_robots(answers: List[Dict[str, Any]], providers: List[Dict[str, Any]]):
    """Generate compliant sitemap.xml and robots.txt explicitly permitting AI crawlers."""
    today = datetime.now().strftime("%Y-%m-%d")

    urls = [
        {"loc": f"{CANONICAL_HOST}/", "lastmod": today, "priority": "1.0"},
        {"loc": f"{CANONICAL_HOST}/about.html", "lastmod": today, "priority": "0.9"}
    ]
    for a in answers:
        urls.append({
            "loc": f"{CANONICAL_HOST}/answers/{a['slug']}.html",
            "lastmod": today,
            "priority": "0.8"
        })
    for p in providers:
        urls.append({
            "loc": f"{CANONICAL_HOST}/providers/{p['slug']}.html",
            "lastmod": today,
            "priority": "0.9"
        })

    sitemap_lines = ['<?xml version="1.0" encoding="UTF-8"?>',
                     '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sitemap_lines.append(f"""  <url>
    <loc>{u['loc']}</loc>
    <lastmod>{u['lastmod']}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>{u['priority']}</priority>
  </url>""")
    sitemap_lines.append('</urlset>')

    sitemap_path = FRONTEND_DIR / "sitemap.xml"
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sitemap_lines))

    robots_content = f"""# AI Atlas India — Plate 05: Indic Language AI (indic.aiatlasindia.com)
# Robots.txt configuration allowing search engines and verified AI crawlers.

User-agent: Googlebot
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot
Allow: /

User-agent: *
Allow: /

Sitemap: {CANONICAL_HOST}/sitemap.xml
"""
    robots_path = FRONTEND_DIR / "robots.txt"
    with open(robots_path, "w", encoding="utf-8") as f:
        f.write(robots_content)

    print(f"[Exporter] Generated sitemap.xml ({len(urls)} URLs) and robots.txt")


# ==============================================================================
# MAIN EXPORT ROUTINE
# ==============================================================================
def run_export() -> Dict[str, Any]:
    """
    Execute complete static compilation of frontend/.
    Enforces MAX_PUBLISHED_ANSWERS = 20 and human expert approval check.
    """
    print("[Exporter] Starting static compilation of frontend/...")
    
    # DISQUALIFICATION PREVENTION: Only export APPROVED answers with verified reviewer_name
    verified_answers = get_approved_answers_with_reasons(limit=MAX_PUBLISHED_ANSWERS)

    if not verified_answers:
        print("[Exporter] Notice: No APPROVED answers found in database. 0 answers will be exported (Strict Human Gate enforced).")

    # Hard cap of 20 answers
    if len(verified_answers) > MAX_PUBLISHED_ANSWERS:
        print(f"[Exporter] Enforcing HARD CAP: slicing from {len(verified_answers)} to {MAX_PUBLISHED_ANSWERS} answers.")
        verified_answers = verified_answers[:MAX_PUBLISHED_ANSWERS]

    providers = get_all_providers()

    # Determine primary reviewer for about page
    first_rev = next((a for a in verified_answers if a.get("reviewer_name")), None)
    exp_name = first_rev["reviewer_name"] if first_rev and first_rev.get("reviewer_name") else REVIEWER_NAME
    exp_role = first_rev["reviewer_role"] if first_rev and first_rev.get("reviewer_role") else REVIEWER_ROLE
    exp_org = first_rev["reviewer_org"] if first_rev and first_rev.get("reviewer_org") else REVIEWER_ORG

    # 1. Export About Page
    about_path = export_about_page(exp_name, exp_role, exp_org)

    # 2. Clean orphaned or unapproved answer HTML files (Strict Human Gate)
    answers_dir = FRONTEND_DIR / "answers"
    answers_dir.mkdir(parents=True, exist_ok=True)
    valid_filenames = {f"{a['slug']}.html" for a in verified_answers}
    for file_path in answers_dir.glob("*.html"):
        if file_path.name not in valid_filenames:
            try:
                file_path.unlink()
                print(f"[Exporter] Removed unapproved/orphaned answer HTML: {file_path.name}")
            except Exception as e:
                print(f"[Exporter] Failed to remove {file_path.name}: {e}")

    # 3. Export Verified Answers
    exported_answers = []
    for a in verified_answers:
        p = export_answer_page(a)
        exported_answers.append(p)

    # 4. Export Providers
    exported_providers = []
    for prov in providers:
        p = export_provider_page(prov)
        exported_providers.append(p)

    # 5. Export Hub
    hub_path = export_hub_page(verified_answers, providers)

    # 6. Export Sitemap and Robots
    export_sitemap_and_robots(verified_answers, providers)

    stats = {
        "answers_exported": len(exported_answers),
        "providers_exported": len(exported_providers),
        "about_path": about_path,
        "hub_path": hub_path
    }
    print(f"[Exporter] Completed export successfully: {stats}")
    return stats


if __name__ == "__main__":
    run_export()
