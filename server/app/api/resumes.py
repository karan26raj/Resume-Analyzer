import logging
import os
from pathlib import Path, PureWindowsPath
import tempfile
import uuid
import zipfile

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeDetailResponse, ResumeResponse, ResumeUploadResponse
from app.services import cache
from app.services.indexing import remove_document_from_index, schedule_indexing
from app.utils.pdf_parser import extract_text_from_docx, extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _get_owned_resume(resume_id: int, user_id: int, db: Session) -> Resume:
    resume = (
        db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
    )
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
    return resume


def _stored_file(resume: Resume) -> Path:
    return Path(settings.UPLOAD_DIR).resolve() / PureWindowsPath(resume.file_path).name


def _validate_file_contents(file_path: Path, file_extension: str) -> None:
    with file_path.open("rb") as uploaded_file:
        header = uploaded_file.read(4)

    if file_extension == ".pdf":
        if header != b"%PDF":
            raise ValueError("The uploaded file is not a valid PDF")
        return

    if not zipfile.is_zipfile(file_path):
        raise ValueError("The uploaded file is not a valid DOCX document")

    with zipfile.ZipFile(file_path) as archive:
        filenames = set(archive.namelist())
    if "[Content_Types].xml" not in filenames or "word/document.xml" not in filenames:
        raise ValueError("The uploaded file is not a valid DOCX document")


def _extract_text(file_path: Path, file_extension: str) -> str:
    if file_extension == ".pdf":
        return extract_text_from_pdf(str(file_path))
    return extract_text_from_docx(str(file_path))


@router.get("/", response_model=list[ResumeResponse])
def get_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Resume).filter(Resume.user_id == current_user.id).all()

@router.get("/{resume_id}", response_model=ResumeDetailResponse)
def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return _get_owned_resume(resume_id, current_user.id, db)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume = _get_owned_resume(resume_id, current_user.id, db)
    file_path = _stored_file(resume)

    db.delete(resume)
    db.commit()
    cache.invalidate_resume(current_user.id, resume_id)

    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Failed to delete stored file for resume %s", resume_id)

    remove_document_from_index(
        user_id=current_user.id,
        document_type="resume",
        document_id=resume_id,
    )


@router.post(
    "/upload",
    response_model=ResumeUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required",
        )

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed"
        )

    content = file.file.read(settings.MAX_UPLOAD_SIZE_BYTES + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty",
        )
    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File must be no larger than {settings.MAX_UPLOAD_SIZE_BYTES} bytes",
        )

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    final_path: Path | None = None
    database_record_created = False

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=file_extension, dir=upload_dir, delete=False
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        _validate_file_contents(temporary_path, file_extension)
        raw_text = _extract_text(temporary_path, file_extension)

        final_path = upload_dir / f"{uuid.uuid4()}{file_extension}"
        os.replace(temporary_path, final_path)
        temporary_path = None

        resume = Resume(
            user_id=current_user.id,
            filename=file.filename,
            file_type=file_extension,
            file_path=final_path.name,
            raw_text=raw_text,
        )
        db.add(resume)
        db.commit()
        database_record_created = True
        db.refresh(resume)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unable to extract text from the uploaded document",
        )
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        if final_path and final_path.exists() and not database_record_created:
            final_path.unlink()

    cache.invalidate_user_recommendations(current_user.id)

    if raw_text:
        schedule_indexing(db, resume, background_tasks)

    return {
        "message": "Resume uploaded successfully",
        "resume_id": resume.id,
        "filename": resume.filename,
        "text_length": len(raw_text),
        "index_status": resume.index_status,
    }

@router.get("/{resume_id}/text")
def get_resume_text(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume = _get_owned_resume(resume_id, current_user.id, db)

    return {
        "resume_id": resume.id,
         "text": resume.raw_text[:2000] if resume.raw_text else ""
    }
