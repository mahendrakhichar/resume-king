"""FastAPI router for resume export services."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.database import get_db
from api.dependencies import get_db_user
from models.user import User
from models.session import Session, SessionStatus
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])

PROFESSIONAL_TEMPLATE_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {
        size: letter;
        margin: 0.5in;
    }
    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
        line-height: 1.4;
        font-size: 10pt;
    }
    h1 {
        font-size: 20pt;
        margin: 0 0 5px 0;
        text-align: center;
        color: #111;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .contact-info {
        text-align: center;
        margin-bottom: 15px;
        font-size: 9pt;
        color: #555;
    }
    .contact-info span {
        margin: 0 5px;
    }
    .section-title {
        font-size: 11pt;
        font-weight: bold;
        color: #0f172a;
        border-bottom: 1px solid #cbd5e1;
        margin-top: 15px;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .item-header {
        display: flex;
        justify-content: space-between;
        font-weight: bold;
        margin-bottom: 2px;
    }
    .item-subheader {
        display: flex;
        justify-content: space-between;
        font-style: italic;
        color: #475569;
        margin-bottom: 4px;
        font-size: 9.5pt;
    }
    ul {
        margin: 0 0 10px 0;
        padding-left: 20px;
    }
    li {
        margin-bottom: 3px;
        text-align: justify;
    }
    .skills-list {
        margin-bottom: 10px;
        line-height: 1.5;
    }
</style>
</head>
<body>

    <h1>{{ contact.name }}</h1>
    <div class="contact-info">
        {% if contact.email %}<span>{{ contact.email }}</span>|{% endif %}
        {% if contact.phone %}<span>{{ contact.phone }}</span>|{% endif %}
        {% if contact.location %}<span>{{ contact.location }}</span>|{% endif %}
        {% if contact.linkedin %}<span>LinkedIn: {{ contact.linkedin }}</span>|{% endif %}
        {% if contact.github %}<span>GitHub: {{ contact.github }}</span>{% endif %}
    </div>

    {% if summary %}
    <div class="section-title">Professional Summary</div>
    <div style="text-align: justify; margin-bottom: 10px;">{{ summary }}</div>
    {% endif %}

    {% if skills %}
    <div class="section-title">Technical Skills</div>
    <div class="skills-list">
        <strong>Languages & Frameworks:</strong> {{ skills | join(', ') }}
    </div>
    {% endif %}

    {% if experience %}
    <div class="section-title">Professional Experience</div>
    {% for job in experience %}
    <div style="margin-bottom: 10px; page-break-inside: avoid;">
        <div class="item-header">
            <span>{{ job.company }}</span>
            <span>{{ job.start_date }} – {{ job.end_date if job.end_date else 'Present' }}</span>
        </div>
        <div class="item-subheader">
            <span>{{ job.title }}</span>
            <span>{{ job.location if job.location else '' }}</span>
        </div>
        <ul>
            {% for bullet in job.bullets %}
            <li>{{ bullet }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endfor %}
    {% endif %}

    {% if projects %}
    <div class="section-title">Technical Projects</div>
    {% for proj in projects %}
    <div style="margin-bottom: 10px; page-break-inside: avoid;">
        <div class="item-header">
            <span>{{ proj.name }}</span>
            <span>{{ proj.technologies | join(', ') if proj.technologies else '' }}</span>
        </div>
        <ul>
            {% for bullet in proj.bullets %}
            <li>{{ bullet }}</li>
            {% endfor %}
        </ul>
    </div>
    {% endfor %}
    {% endif %}

    {% if education %}
    <div class="section-title">Education</div>
    {% for edu in education %}
    <div style="margin-bottom: 8px; page-break-inside: avoid;">
        <div class="item-header">
            <span>{{ edu.institution }}</span>
            <span>{{ edu.start_date }} – {{ edu.end_date }}</span>
        </div>
        <div class="item-subheader">
            <span>{{ edu.degree }} in {{ edu.field_of_study }}</span>
            <span>{{ 'GPA: ' ~ edu.gpa if edu.gpa else '' }}</span>
        </div>
    </div>
    {% endfor %}
    {% endif %}

</body>
</html>
"""


@router.get("/{session_id}/pdf", response_class=Response)
async def export_session_resume_pdf(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """
    Export the final tailored resume as an elegant, ATS-friendly PDF.
    Renders structured resume data via a Jinja2 HTML template and compiles it using WeasyPrint.
    """
    # 1. Fetch completed session
    stmt = select(Session).where(Session.id == session_id, Session.user_id == current_user.id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.final_resume_data:
        raise HTTPException(
            status_code=400,
            detail="Final tailored resume dataset is not available yet. Please complete the review step."
        )

    try:
        from jinja2 import Template
        
        # 2. Compile and render Jinja2 HTML template
        template = Template(PROFESSIONAL_TEMPLATE_HTML)
        html_content = template.render(**session.final_resume_data)

        # 3. Render HTML to elegant PDF bytes
        pdf_bytes = None
        
        # Try WeasyPrint first if fully configured with native dynamic libraries
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            logger.info("PDF generated successfully using WeasyPrint.")
        except Exception as weasy_err:
            logger.warning(
                f"WeasyPrint is missing native dynamic libraries (e.g. libgobject-2.0-0 on Windows): {weasy_err}. "
                "Falling back to pure-Python xhtml2pdf compiler."
            )
            
            # Pure-Python fallback using xhtml2pdf (works flawlessly out-of-the-box on Windows)
            import io
            from xhtml2pdf import pisa
            
            pdf_io = io.BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_io)
            if not pisa_status.err:
                pdf_bytes = pdf_io.getvalue()
                logger.info("PDF generated successfully using pure-Python xhtml2pdf compiler fallback.")
            else:
                raise Exception(f"xhtml2pdf compiler failed with error code: {pisa_status.err}")

        filename = f"{session.final_resume_data.get('contact', {}).get('name', 'Tailored_Resume')}.pdf"
        
        logger.info(f"Successfully generated PDF for session {session_id} ({len(pdf_bytes)} bytes)")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Failed to generate resume PDF: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compile PDF: {str(e)}"
        )
