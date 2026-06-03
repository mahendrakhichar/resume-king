"""FastAPI router for resume uploads, listing, and detailing."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.database import get_db
from api.dependencies import get_db_user
from models.user import User
from models.resume import Resume, FileType
from schemas.resume import ResumeUploadResponse, ResumeListItem, ResumeDetail
from utils.file_handler import save_upload, delete_file
from parsers.pdf_parser import extract_text
from parsers.resume_extractor import extract_structured_resume
from services.vector_service import VectorService
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """
    Upload a resume (PDF/DOCX), extract raw text, parse it into structured JSON,
    index it in ChromaDB for semantic matching, and persist it in PostgreSQL.
    """
    logger.info(f"Resume upload request: {file.filename} by user {current_user.email}")
    
    file_path = None
    try:
        # 1. Save file locally
        file_path, file_type_str = await save_upload(file, str(current_user.id))
        file_type = FileType(file_type_str)

        # 2. Extract plain text
        raw_text = extract_text(file_path)
        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Successfully saved file, but failed to extract any readable text."
            )

        # 3. Parse text into structured JSON via Gemini
        parsed_data = await extract_structured_resume(raw_text)

        # 4. Save to PostgreSQL database
        resume = Resume(
            user_id=current_user.id,
            original_filename=file.filename,
            file_path=file_path,
            file_type=file_type,
            raw_text=raw_text,
            parsed_data=parsed_data,
            version=1,
            is_tailored=False
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        # 5. Index into ChromaDB vector store for matching operations
        await VectorService.index_resume(
            resume_id=str(resume.id),
            user_id=str(current_user.id),
            parsed_data=parsed_data,
            raw_text=raw_text
        )

        logger.info(f"Successfully processed and saved resume {resume.id}")
        return resume

    except Exception as e:
        logger.error(f"Error handling upload: {e}")
        # Clean up file from filesystem if database save or parsing failed
        if file_path:
            await delete_file(file_path)
        
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during resume processing: {str(e)}"
        )


@router.get("", response_model=List[ResumeListItem])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """List all resumes uploaded by the current authenticated user."""
    stmt = select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{resume_id}", response_model=ResumeDetail)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """Retrieve full detail of a specific resume."""
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_db_user)
):
    """Delete a resume from database, local file, and vector indexes."""
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    result = await db.execute(stmt)
    resume = result.scalars().first()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # 1. Delete associated sessions to prevent ForeignKeyViolationError
    from models.session import Session
    await db.execute(delete(Session).where(Session.resume_id == resume_id))

    # 2. Delete child resume versions (e.g. tailored versions) along with their files and vectors
    stmt_children = select(Resume).where(Resume.parent_id == resume_id)
    res_children = await db.execute(stmt_children)
    children = res_children.scalars().all()
    for child in children:
        await delete_file(child.file_path)
        await VectorService.delete_resume_vectors(str(child.id))
        
        # Eagerly delete sessions for child versions too
        await db.execute(delete(Session).where(Session.resume_id == child.id))
        await db.delete(child)

    # 3. Delete original resume files and vectors
    await delete_file(resume.file_path)
    await VectorService.delete_resume_vectors(str(resume.id))

    # 4. Delete the parent resume itself from database
    await db.delete(resume)
    await db.commit()
    
    logger.info(f"Resume {resume_id} and all its tailored versions/sessions fully deleted.")
    return None
