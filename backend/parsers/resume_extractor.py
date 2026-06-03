"""AI-enhanced structured resume data extractor using Gemini."""

import json
import re
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from services.llm_service import llm_service
from schemas.resume import ParsedResume
from utils.logger import get_logger

logger = get_logger(__name__)

EXTRACTOR_SYSTEM_PROMPT = """You are a highly precise AI Resume Parsing Agent.
Your objective is to read raw text extracted from a resume (PDF/DOCX) and organize it into a structured, clean JSON representation.

You MUST extract the following sections accurately, identifying diverse synonyms:
1. contact: name, email, phone, linkedin, github, portfolio, location.
2. summary: A professional technical summary if present.
3. skills: A flat array of specialized tools, languages, frameworks, or skills (synonyms: "Technical Skills", "Technologies", "Expertise", "Languages & Tools", "Core Competencies").
4. experience: Array of jobs. Extract company, title, location, start_date, end_date, is_current, bullets (synonyms: "Work Experience", "Professional Experience", "Employment History", "Work History", "Career Background", "Internships", "Co-op").
5. education: Array of education. Extract institution, degree, field_of_study, start_date, end_date, gpa, highlights (synonyms: "Academic Background", "Academic History", "Degrees", "University Education").
6. projects: Array of projects. Extract name, description, technologies (array), url, bullets (synonyms: "Academic Projects", "Personal Projects", "Technical Projects", "Portfolios", "Relevant Projects").
7. certifications: Array of certifications. Name, issuer, date, url (synonyms: "Licenses", "Credentials", "Professional Certifications").
8. achievements: Array of major awards, accomplishments, or metrics (synonyms: "Awards", "Honors", "Key Achievements").
9. languages: Array of languages spoken.

You MUST extract ALL sections. Look specifically for these headings:
- Work Experience, Professional Experience, Employment History, Experience
- Projects, Personal Projects, Side Projects
- Education, Academic Background
- Achievements, Awards

For experience, extract company name, title, dates, and ALL bullet points.
If a section has content but is not perfectly formatted, still extract it.
Never return null for lists. Use empty array [] instead.

Rules:
- Output must be valid JSON matching the schema perfectly.
- Clean up bad formatting, double spaces, and layout artifacts from extraction.
- For every list or array field (skills, experience, education, projects, certifications, achievements, highlights, bullets, technologies, languages), always return an empty array [] instead of null/None if no items exist. Never return null for list fields.
- Return ONLY the JSON object. Do not include markdown code block syntax (like ```json ... ```). Output raw JSON.
"""

EXTRACTOR_USER_TEMPLATE = """Please parse the following raw resume text.

{detection_hints}

--- RAW RESUME TEXT ---
{raw_text}
--- END RAW RESUME TEXT ---
"""


def detect_resume_sections(raw_text: str) -> str:
    """Pre-identifies presence of key resume sections in the raw text and generates prompt hints for the LLM."""
    hints = []
    
    # Common patterns for section headers (case-insensitive, matching full lines or strong boundaries)
    patterns = {
        "experience": r"(?i)(?:work\s+experience|professional\s+experience|employment\s+history|experience|work\s+history|employment)",
        "projects": r"(?i)(?:projects|personal\s+projects|side\s+projects|technical\s+projects|academic\s+projects)",
        "education": r"(?i)(?:education|academic\s+background|academic\s+history|degrees|university\s+education)",
        "skills": r"(?i)(?:technical\s+skills|skills|technologies|expertise|languages\s*(?:&|and)\s*tools|core\s+competencies)",
        "certifications": r"(?i)(?:certifications|licenses|credentials|professional\s+certifications)",
        "achievements": r"(?i)(?:achievements|awards|honors|key\s+achievements)"
    }
    
    found_sections = []
    for section_name, pattern in patterns.items():
        matches = list(re.finditer(pattern, raw_text))
        if matches:
            found_sections.append(section_name.upper())
            # Grab a small snippet around the first match to guide the LLM
            first_match = matches[0]
            start_pos = max(0, first_match.start() - 20)
            end_pos = min(len(raw_text), first_match.end() + 150)
            snippet = raw_text[start_pos:end_pos].replace("\n", " ").strip()
            hints.append(f"- Detected '{section_name}' heading around: \"... {snippet} ...\"")
            
    if found_sections:
        summary_hint = f"PRE-DETECTION HINTS (The parser pre-identified these sections, you MUST extract them):\n"
        summary_hint += f"Detected Sections: {', '.join(found_sections)}\n"
        summary_hint += "\n".join(hints)
        return summary_hint
    return "PRE-DETECTION HINTS: No clear standard section headers pre-detected. Please parse the plain text carefully."


def fix_parsed_resume(data: Any) -> Any:
    """Recursively clean up None list values to empty lists and default missing fields."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if v is None and k in [
                "skills", "experience", "education", "projects", 
                "certifications", "achievements", "languages", 
                "highlights", "bullets", "technologies"
            ]:
                cleaned[k] = []
            else:
                cleaned[k] = fix_parsed_resume(v)
        return cleaned
    elif isinstance(data, list):
        return [fix_parsed_resume(item) for item in data]
    return data


async def extract_structured_resume(raw_text: str) -> Dict[str, Any]:
    """
    Parse plain resume text into a structured JSON dictionary using Gemini/LLM.
    """
    detection_hints = detect_resume_sections(raw_text)
    user_prompt = EXTRACTOR_USER_TEMPLATE.format(
        raw_text=raw_text,
        detection_hints=detection_hints
    )

    try:
        # Use our LLM Service with task-based routing (routes to HEAVY_MODEL via OpenRouter)
        response_text = await llm_service.invoke_with_fallback(
            system_prompt=EXTRACTOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0,  # Highly deterministic
            task_type="resume_parsing",
        )

        # Save raw LLM response
        try:
            import os
            raw_llm_out = os.path.join(os.path.dirname(__file__), "raw_llm_response.json")
            with open(raw_llm_out, "w", encoding="utf-8") as f:
                f.write(response_text)
            print(f"Saved raw LLM response to {raw_llm_out}")
        except Exception as log_err:
            logger.warning(f"Failed to log raw LLM response: {log_err}")

        # Remove markdown code blocks if the LLM included them
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            # Strip first line
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        # Parse JSON
        parsed_json = json.loads(clean_text)
        
        # Recursively scrub None list values to empty arrays
        parsed_json = fix_parsed_resume(parsed_json)
        
        # Validate with Pydantic to ensure default schemas are fulfilled
        validated_data = ParsedResume(**parsed_json)
        return validated_data.model_dump()

    except Exception as e:
        logger.error(f"Structured resume extraction failed: {e}")
        # Return a minimal schema fallback so the API doesn't fail
        return ParsedResume(
            contact={"name": "Unknown Candidate"},
            skills=[],
            experience=[],
            education=[],
            projects=[]
        ).model_dump()
