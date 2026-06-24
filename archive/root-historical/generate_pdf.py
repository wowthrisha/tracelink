import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Define custom canvas for headers, footers, and page numbers
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header text
        self.drawString(45, 758, "PROJECT SECUREDOC: PITCH DECK & TECHNICAL BLUEPRINT")
        self.setFont("Helvetica-Oblique", 8)
        self.drawRightString(567, 758, "CAPM / Lean Six Sigma CSE Final Year Design")
        
        # Header Line
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(45, 750, 567, 750)
        
        # Footer Line
        self.line(45, 42, 567, 42)
        
        # Footer text
        self.setFont("Helvetica", 7.5)
        self.drawString(45, 28, "Confidential - For Internal Review & Investor Presentation Only")
        self.drawRightString(567, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def create_pitch_pdf(output_path):
    # Setup document: letter size, 50 pt top/bottom margins, 45 pt side margins
    # Printable width: 612 - 90 = 522 pt
    # Printable height: 792 - 100 = 692 pt
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=50,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    # Primary color: #1E3A8A (Navy), Secondary: #0F766E (Teal), Neutral Dark: #1E293B (Slate)
    primary_color = colors.HexColor("#1E3A8A")
    secondary_color = colors.HexColor("#0F766E")
    text_color = colors.HexColor("#1E293B")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=19,
        textColor=primary_color,
        spaceAfter=2
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8
    )
    
    h1_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13,
        textColor=primary_color,
        spaceBefore=7,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_color,
        spaceAfter=4
    )
    
    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=8.5,
        textColor=text_color
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=8.5,
        textColor=colors.white
    )

    story = []

    # PAGE 1: TITLE & SECTIONS 1 - 5
    story.append(Paragraph("PROJECT SECUREDOC: SHARK TANK PITCH & STRUCTURAL BLUEPRINT", title_style))
    story.append(Paragraph("<b>Author:</b> CSE Final Year Lead (CAPM, Lean Six Sigma Green Belt) | <b>Version:</b> 1.0-EXEC-SPEC", subtitle_style))
    
    # 1. Executive Summary & Shark Tank Hook
    story.append(Paragraph("1. Executive Summary & Shark Tank Hook (The Elevator Pitch)", h1_style))
    exec_summary_text = (
        "Corporate documents are the load-bearing pillars of enterprise IP, yet standard sharing practices "
        "rely on weak scaffolding. Generic lockers (Google Drive, Dropbox) offer no visual protection, while trackable "
        "SaaS platforms (DocSend, FlipLink) charge high subscription fees and compromise data sovereignty by storing "
        "files on third-party servers. <b>SecureDoc</b> is a self-hostable, zero-trust sharing gateway. Deployed as a "
        "single-container Docker stack, it keeps all assets in your private S3/R2 storage, ensuring 100% data sovereignty. "
        "We protect the document itself: by rasterizing PDFs into secure images and overlaying session-unique watermarks "
        "(with dynamic email, time, and randomized angle jitter that blocks visual alignment extraction) alongside "
        "near-invisible forensic stamps and EXIF tracking, SecureDoc establishes an ironclad audit trail at near-zero cost."
    )
    story.append(Paragraph(exec_summary_text, body_style))
    
    # 2. Problem Statement (Lean Waste & Structural Cracks)
    story.append(Paragraph("2. Problem Statement (Structural Failure Modes)", h1_style))
    story.append(Paragraph("• <b>Scaffolding Bias (Data Leakage):</b> Portals secure the link but leave document contents unprotected. Viewers can easily download, extract, print, or redistribute files.", bullet_style))
    story.append(Paragraph("• <b>Static Watermark Evasion:</b> Conventional watermarks are easily bypassed using contrast adjustments or image alignment-overlay cancellation scripts.", bullet_style))
    story.append(Paragraph("• <b>Compliance Exposure:</b> Out-of-network document sharing violates GDPR and HIPAA regulations by storing proprietary and PII data on vendor servers.", bullet_style))
    story.append(Paragraph("• <b>Operational Resource Waste:</b> Enterprise SaaS subscriptions cost $50–$150/user/month. This is unnecessary overhead ('Muda') in the budget ledger.", bullet_style))

    # 3. Target End Users (Key Stakeholders & Occupants)
    story.append(Paragraph("3. Target End Users (Operational Stakeholders)", h1_style))
    story.append(Paragraph("• <b>Construction & Real Estate Developers:</b> Securely sharing bids, blueprints, and engineering calculations with sub-contractors, preventing direct file downloads.", bullet_style))
    story.append(Paragraph("• <b>Legal & Corporate M&A Teams:</b> Exposing pre-launch financials, audits, and NDAs to external auditors under strict IP/CIDR gates and view-cap limits.", bullet_style))
    story.append(Paragraph("• <b>Training & Professional Institutions:</b> Distributing proprietary curriculum materials and lecture slides to students while blocking bulk offline scraping.", bullet_style))
    story.append(Paragraph("• <b>Venture Capital & Tech Founders:</b> Pitching proprietary decks to passive investors with self-destructing links and live page-by-page viewing telemetry.", bullet_style))

    # 4. Novelty & Value Proposition (Load-Bearing Innovations)
    story.append(Paragraph("4. Novelty & Value Proposition (Load-Bearing Innovations)", h1_style))
    story.append(Paragraph("• <b>Anti-Removal Session Jitter:</b> SecureDoc hashes the viewer's session ID to generate a randomized dynamic jitter angle (base &plusmn; 5&deg;). Multiple page screenshots cannot be aligned to strip out the watermark.", bullet_style))
    story.append(Paragraph("• <b>Dual Forensic Layering:</b> Integrates a 3% opacity corner stamp (<code>SD:hash:page</code>) into page images and injects the document ID into EXIF tag 270. Traceability remains intact even if visual text is cropped.", bullet_style))
    story.append(Paragraph("• <b>Sovereign Architecture:</b> 100% self-hosted via Docker. Raw bytes are proxied directly from your private R2/S3 storage via FastAPI; direct storage links are never exposed to the client.", bullet_style))
    story.append(Paragraph("• <b>Multi-Format Adapter Interface:</b> Unified processing registry for PDFs (image-rasterized) and text-based formats (DOCX, TXT, LOG, MD) viewed via a secure hybrid client.", bullet_style))

    # 5. Tech Stack & Existing Architecture Flow (Material Specifications & Blueprint)
    story.append(Paragraph("5. Tech Stack & Existing Architecture Flow (Material Specifications & Blueprint)", h1_style))
    story.append(Paragraph("• <b>Material Specifications:</b> FastAPI (Python 3.12, asyncpg, SQLAlchemy) | PostgreSQL (metadata) | Redis (L2 page/session cache & Celery queue) | Celery (async rasterization worker) | Supabase/Cloudflare R2 (S3-compatible storage) | Single-file React SPA client.", bullet_style))
    story.append(Paragraph("• <b>Workflow Mechanics:</b>", bullet_style))
    story.append(Paragraph("  1. <i>Upload & Render:</i> Document uploaded &rarr; Poppler rasterizes PDF to WEBP &rarr; Forensic stamps applied &rarr; Pages stored in private S3/R2.", bullet_style))
    story.append(Paragraph("  2. <i>Access Gate:</i> Viewer requests token &rarr; Server validates password, IP/CIDR ranges, and email gates &rarr; Generates 128-bit CSPRNG Session ID.", bullet_style))
    story.append(Paragraph("  3. <i>Proxy & Serve:</i> Page GET requested &rarr; Checked against L1 (RAM) and L2 (Redis) cache &rarr; Server-side PIL engine applies dynamic visual watermark and jitter &rarr; Streamed as WEBP with <code>no-store</code> headers.", bullet_style))

    story.append(PageBreak())

    # PAGE 2: SECTIONS 6 - 9 (Competitor Analysis, Scalability, Cost, Future Scope)
    story.append(Paragraph("6. Competitor Gap Analysis (Process Capability Comparison)", h1_style))
    
    # Competitor Table setup
    # Column widths (total printable width is 522 pt)
    col_widths = [120, 82, 80, 80, 80, 80]
    
    table_data = [
        [
            Paragraph("<b>Security Feature</b>", table_header_style),
            Paragraph("<b>SecureDoc (Ours)</b>", table_header_style),
            Paragraph("<b>DocSend</b>", table_header_style),
            Paragraph("<b>FlipLink.me</b>", table_header_style),
            Paragraph("<b>Google Drive</b>", table_header_style),
            Paragraph("<b>Box</b>", table_header_style)
        ],
        [
            Paragraph("<b>IP/CIDR Allowlist</b>", table_cell_style),
            Paragraph("<b>Yes (Per-Link)</b>", table_cell_style),
            Paragraph("Yes (Enterprise)", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style)
        ],
        [
            Paragraph("<b>Dynamic Watermark</b>", table_cell_style),
            Paragraph("<b>Yes (Per-Session)</b>", table_cell_style),
            Paragraph("Yes (Static Text)", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("Yes (Enterprise)", table_cell_style)
        ],
        [
            Paragraph("<b>Session Jitter Angle</b>", table_cell_style),
            Paragraph("<b>Yes (Anti-removal)</b>", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style)
        ],
        [
            Paragraph("<b>Forensic Corner Stamp</b>", table_cell_style),
            Paragraph("<b>Yes (3% Opacity)</b>", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style)
        ],
        [
            Paragraph("<b>EXIF Metadata ID</b>", table_cell_style),
            Paragraph("<b>Yes (Traceable)</b>", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style)
        ],
        [
            Paragraph("<b>Page-Level Analytics</b>", table_cell_style),
            Paragraph("<b>Yes (Per-Second)</b>", table_cell_style),
            Paragraph("Yes", table_cell_style),
            Paragraph("Yes (Basic)", table_cell_style),
            Paragraph("No", table_cell_style),
            Paragraph("No", table_cell_style)
        ],
        [
            Paragraph("<b>Sovereignty / Self-Host</b>", table_cell_style),
            Paragraph("<b>Yes (Docker)</b>", table_cell_style),
            Paragraph("No (SaaS Cloud)", table_cell_style),
            Paragraph("No (SaaS Cloud)", table_cell_style),
            Paragraph("No (SaaS Cloud)", table_cell_style),
            Paragraph("No (SaaS Cloud)", table_cell_style)
        ],
        [
            Paragraph("<b>Supported Formats</b>", table_cell_style),
            Paragraph("<b>PDF, DOCX, TXT, LOG</b>", table_cell_style),
            Paragraph("PDF, DOCX, PPTX", table_cell_style),
            Paragraph("PDF Only", table_cell_style),
            Paragraph("All Files", table_cell_style),
            Paragraph("All Files", table_cell_style)
        ],
        [
            Paragraph("<b>Pricing / Cost Basis</b>", table_cell_style),
            Paragraph("<b>Self-Host (~$2/mo)</b>", table_cell_style),
            Paragraph("$10 - $150/user/mo", table_cell_style),
            Paragraph("$15 - $45/mo", table_cell_style),
            Paragraph("$12/user/mo", table_cell_style),
            Paragraph("$15 - $35/user/mo", table_cell_style)
        ]
    ]
    
    comp_table = Table(table_data, colWidths=col_widths)
    comp_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 0), (-1, 0), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2.5),
        ('TOPPADDING', (0, 1), (-1, -1), 2.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F8FAFC"), colors.white]),
    ]))
    
    story.append(comp_table)
    story.append(Spacer(1, 5))
    
    # 7. Current Scalability & Constraints (Structural Load Factors)
    story.append(Paragraph("7. Current Scalability & Constraints (Structural Load Factors)", h1_style))
    story.append(Paragraph("• <b>Processing Limits (Load Envelopes):</b> Celery document processing is memory-intensive. Rasterization page limits are capped at <code>max_pages_per_doc = 500</code>. PDF download generation requires compiling images in-memory and is restricted to 100 pages to prevent Out-Of-Memory (OOM) failures.", bullet_style))
    story.append(Paragraph("• <b>Database Connection Bottleneck:</b> The active session enforcer performs a synchronous database query on every page fetch. This creates significant DB read pressure under high concurrency. Moving session verification to Redis is the planned structural remedy.", bullet_style))
    story.append(Paragraph("• <b>Office Conversion Overhead:</b> Headless LibreOffice has a 2–3s cold startup cost for DOCX to PDF conversions, which introduces task queue latency during batch uploads. Mitigated by async task processing, but remains an optimization target.", bullet_style))
    story.append(Paragraph("• <b>Storage Operations I/O Bound:</b> Rasterizing a 100-page PDF produces 100 full-page images and 100 thumbnails. Total processing time is bound by R2 concurrent write operations (currently managed by executing async uploads in batches of 8).", bullet_style))

    # 8. Cost Incurred & Resource Allocation (Bill of Materials & OpEx)
    story.append(Paragraph("8. Cost Incurred & Resource Allocation (Bill of Materials & OpEx)", h1_style))
    story.append(Paragraph("Operating SecureDoc eliminates high SaaS middleware markup, routing costs directly to commodity cloud resources:", bullet_style))
    story.append(Paragraph("• <b>Compute Infrastructure:</b> $5.00 - $10.00/month. The lightweight FastAPI backend and compiled React SPA client run comfortably on a single-core, 1GB RAM virtual machine instance (e.g., AWS EC2 t3.micro or equivalent VPS).", bullet_style))
    story.append(Paragraph("• <b>Storage Assets:</b> $0.015/GB-month. Bandwidth egress charges are $0.00 due to Cloudflare R2's pricing model. For a library of 1,000 documents (average size 5MB) and 10,000 monthly page views, storage costs are under $0.10/month.", bullet_style))
    story.append(Paragraph("• <b>Metadata Database:</b> $0.00 (managed free tier) or $5.00/month for a shared DB micro-instance, which easily manages thousands of links.", bullet_style))
    story.append(Paragraph("• <b>Total Operating Budget:</b> Under $15.00/month. Compared to DocSend's corporate pricing ($1,500/month for a 10-user seat allocation), SecureDoc eliminates 99% of operational budget waste ('Muda'), yielding massive ROI.", bullet_style))

    # 9. Future Scope & Roadmap (Expansion Blueprint)
    story.append(Paragraph("9. Future Scope & Roadmap (Expansion Blueprint)", h1_style))
    story.append(Paragraph("• <b>Phase II — Caching & Rate Limit Redundancy:</b> Migrate session verification from PostgreSQL to Redis. Transition slowapi local rate limiting to Redis-backed storage to support horizontal API container scaling (multiple instances).", bullet_style))
    story.append(Paragraph("• <b>Phase III — Subprocess Daemonization:</b> Implement a headless <code>unoserver</code> daemon pool to eliminate the 2s LibreOffice subprocess startup latency. Add Celery Beat health monitoring and alert triggers.", bullet_style))
    story.append(Paragraph("• <b>Phase IV — Presentation & Search Support:</b> Integrate <code>python-pptx</code> slide text extraction. Implement PDF optical text layer extraction to enable full-text in-viewer search. Embed e-Signature / NDA agreement gate flows.", bullet_style))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)

if __name__ == "__main__":
    output_pdf = "/Users/thrisha/traceview/securedoc/securedoc_pitch.pdf"
    create_pitch_pdf(output_pdf)
    print(f"PDF generated successfully at {output_pdf}")
