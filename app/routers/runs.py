"""
Run orchestration router for BrasilIntel.

Provides endpoints to execute the end-to-end vertical slice pipeline:
scrape -> classify -> store -> report -> email
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.run import Run
from app.models.news_item import NewsItem
from app.models.insurer import Insurer
from app.services.scraper import ApifyScraperService
from app.services.classifier import ClassificationService
from app.services.emailer import GraphEmailService
from app.services.reporter import ReportService
from app.schemas.run import RunRead, RunStatus
from app.schemas.news import NewsItemWithClassification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["Runs"])


class ExecuteRequest(BaseModel):
    category: str = Field(description="Category: Health, Dental, or Group Life")
    insurer_id: Optional[int] = Field(None, description="Specific insurer ID (or first enabled if None)")
    send_email: bool = Field(True, description="Whether to send email report")
    max_news_items: int = Field(10, ge=1, le=50, description="Max news items to scrape per insurer")


class ExecuteResponse(BaseModel):
    run_id: int
    status: str
    insurers_processed: int
    items_found: int
    email_sent: bool
    message: str


@router.post("/execute", response_model=ExecuteResponse)
async def execute_run(
    request: ExecuteRequest,
    db: Session = Depends(get_db),
) -> ExecuteResponse:
    # Create run record
    run = Run(
        category=request.category,
        trigger_type="manual",
        status=RunStatus.RUNNING.value,
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    logger.info(f"Starting run {run.id} for category {request.category}")
    
    try:
        # Get insurer
        if request.insurer_id:
            insurer = db.query(Insurer).filter(Insurer.id == request.insurer_id).first()
            if not insurer:
                raise HTTPException(status_code=404, detail=f"Insurer {request.insurer_id} not found")
        else:
            # Get first enabled insurer in category
            insurer = db.query(Insurer).filter(
                Insurer.category == request.category,
                Insurer.enabled == True
            ).first()
            if not insurer:
                raise HTTPException(status_code=404, detail=f"No enabled insurers in {request.category}")
        
        logger.info(f"Processing insurer: {insurer.name} (ANS: {insurer.ans_code})")
        
        # Initialize services
        scraper = ApifyScraperService()
        classifier = ClassificationService()
        
        # Scrape news
        logger.info(f"Scraping news for {insurer.name}...")
        scraped_items = scraper.search_insurer(
            insurer_name=insurer.name,
            ans_code=insurer.ans_code,
            max_results=request.max_news_items,
        )
        
        logger.info(f"Found {len(scraped_items)} news items")
        
        items_stored = 0
        
        # Classify and store each news item
        for scraped in scraped_items:
            logger.info(f"Classifying: {scraped.title[:100]}...")
            
            # Classify the news item
            classification = classifier.classify_single_news(
                insurer_name=insurer.name,
                news_title=scraped.title,
                news_description=scraped.description,
            )
            
            # Store news item with classification
            news_item = NewsItem(
                run_id=run.id,
                insurer_id=insurer.id,
                title=scraped.title,
                description=scraped.description,
                source_url=scraped.url,
                source_name=scraped.source,
                published_at=scraped.published_at,
                status=classification.status if classification else None,
                sentiment=classification.sentiment if classification else None,
                summary="\n".join(classification.summary_bullets) if classification else None,
            )
            db.add(news_item)
            items_stored += 1
        
        db.commit()
        logger.info(f"Stored {items_stored} news items")
        
        # Generate HTML report
        logger.info("Generating HTML report...")
        report_service = ReportService()
        html_report = report_service.generate_report_from_db(
            category=request.category,
            run_id=run.id,
            db_session=db,
        )
        
        # Send email if requested and configured
        email_sent = False
        if request.send_email:
            logger.info("Sending email report...")
            email_service = GraphEmailService()
            report_date = datetime.now().strftime("%Y-%m-%d")
            email_result = await email_service.send_report_email(
                category=request.category,
                html_content=html_report,
                report_date=report_date,
            )
            
            if email_result.get("status") == "ok":
                email_sent = True
                logger.info("Email sent successfully")
            else:
                logger.warning(f"Email not sent: {email_result.get('message')}")
        
        # Update run status to completed
        run.status = RunStatus.COMPLETED.value
        run.completed_at = datetime.utcnow()
        run.insurers_processed = 1
        run.items_found = items_stored
        db.commit()
        
        logger.info(f"Run {run.id} completed successfully")
        
        return ExecuteResponse(
            run_id=run.id,
            status=run.status,
            insurers_processed=1,
            items_found=items_stored,
            email_sent=email_sent,
            message=f"Successfully processed {insurer.name} with {items_stored} news items",
        )
    
    except Exception as e:
        logger.error(f"Run {run.id} failed: {e}")
        
        # Update run status to failed
        run.status = RunStatus.FAILED.value
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()
        
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[RunRead])
def list_runs(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> list[Run]:
    query = db.query(Run)
    
    if category:
        query = query.filter(Run.category == category)
    
    if status:
        query = query.filter(Run.status == status)
    
    runs = query.order_by(Run.started_at.desc()).limit(limit).all()
    
    return runs


@router.get("/{run_id}", response_model=RunRead)
def get_run(
    run_id: int,
    db: Session = Depends(get_db),
) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    return run


@router.get("/{run_id}/news", response_model=list[NewsItemWithClassification])
def get_run_news(
    run_id: int,
    db: Session = Depends(get_db),
) -> list[NewsItem]:
    run = db.query(Run).filter(Run.id == run_id).first()
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    news_items = db.query(NewsItem).filter(NewsItem.run_id == run_id).all()
    
    return news_items
