"""
Insurer CRUD router for BrasilIntel API.

Provides endpoints for managing insurers (insurance companies):
- List all insurers with pagination
- Search and filter insurers (DATA-02)
- Get single insurer by ANS code
- Create new insurer (DATA-01)
- Update insurer details (DATA-03)
- Delete insurer
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.insurer import Insurer
from app.schemas.insurer import InsurerCreate, InsurerUpdate, InsurerResponse

router = APIRouter(prefix="/api/insurers", tags=["insurers"])


@router.get("/", response_model=list[InsurerResponse])
def list_insurers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> list[Insurer]:
    """
    List all insurers with pagination.

    Args:
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return (max 100)

    Returns:
        List of insurers
    """
    insurers = db.query(Insurer).offset(skip).limit(limit).all()
    return insurers


@router.get("/search")
def search_insurers(
    query: str | None = None,
    category: str | None = None,
    enabled: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> dict:
    """
    Search and filter insurers (DATA-02).

    Args:
        query: Search term for name or ANS code
        category: Filter by category (Health, Dental, Group Life)
        enabled: Filter by enabled status
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Dict with total count and filtered results
    """
    q = db.query(Insurer)

    # Apply search filter - searches name and ans_code
    if query:
        search_pattern = f"%{query}%"
        q = q.filter(
            or_(
                Insurer.name.ilike(search_pattern),
                Insurer.ans_code.contains(query)
            )
        )

    # Apply category filter
    if category:
        q = q.filter(Insurer.category == category)

    # Apply enabled filter
    if enabled is not None:
        q = q.filter(Insurer.enabled == enabled)

    # Get total count before pagination
    total = q.count()

    # Apply pagination
    results = q.offset(skip).limit(limit).all()

    return {
        "total": total,
        "results": [InsurerResponse.model_validate(r) for r in results]
    }


@router.get("/{ans_code}", response_model=InsurerResponse)
def get_insurer(
    ans_code: str,
    db: Session = Depends(get_db)
) -> Insurer:
    """
    Get a single insurer by ANS code.

    Args:
        ans_code: 6-digit ANS registration code

    Returns:
        Insurer details

    Raises:
        HTTPException 404: If insurer not found
    """
    insurer = db.query(Insurer).filter(Insurer.ans_code == ans_code).first()
    if not insurer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insurer with ANS code {ans_code} not found"
        )
    return insurer


@router.post("/", response_model=InsurerResponse, status_code=status.HTTP_201_CREATED)
def create_insurer(
    data: InsurerCreate,
    db: Session = Depends(get_db)
) -> Insurer:
    """
    Create a new insurer (DATA-01).

    Args:
        data: Insurer creation data

    Returns:
        Created insurer

    Raises:
        HTTPException 400: If ANS code already exists (DATA-08)
        HTTPException 500: On database error
    """
    insurer = Insurer(**data.model_dump())
    try:
        db.add(insurer)
        db.commit()
        db.refresh(insurer)
        return insurer
    except IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower()
        if "unique" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ANS Code {data.ans_code} already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )


@router.patch("/{ans_code}", response_model=InsurerResponse)
def update_insurer(
    ans_code: str,
    data: InsurerUpdate,
    db: Session = Depends(get_db)
) -> Insurer:
    """
    Update an insurer's details (DATA-03).

    Supports partial updates - only provided fields are updated.

    Args:
        ans_code: 6-digit ANS registration code
        data: Fields to update (name, enabled, search_terms)

    Returns:
        Updated insurer

    Raises:
        HTTPException 404: If insurer not found
    """
    insurer = db.query(Insurer).filter(Insurer.ans_code == ans_code).first()
    if not insurer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insurer with ANS code {ans_code} not found"
        )

    # Only update fields that were explicitly set
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(insurer, key, value)

    db.commit()
    db.refresh(insurer)
    return insurer


@router.delete("/{ans_code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_insurer(
    ans_code: str,
    db: Session = Depends(get_db)
) -> None:
    """
    Delete an insurer.

    Args:
        ans_code: 6-digit ANS registration code

    Raises:
        HTTPException 404: If insurer not found
    """
    insurer = db.query(Insurer).filter(Insurer.ans_code == ans_code).first()
    if not insurer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Insurer with ANS code {ans_code} not found"
        )

    db.delete(insurer)
    db.commit()
