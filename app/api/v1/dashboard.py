from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog
from pydantic import BaseModel, HttpUrl
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.client import Client
from app.models.competitor import Competitor
from app.models.briefing_history import BriefingHistory
from app.schemas.competitor import CompetitorResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

class BriefingHistoryResponse(BaseModel):
    id: int
    competitor_id: int
    competitor_name: Optional[str] = None
    scrape_date: datetime
    insight_json: dict
    delivery_status: str
    
    model_config = {"from_attributes": True}

class PortalCompetitorCreate(BaseModel):
    """What the portal sends: the client comes from the token, not the body."""
    name: str
    website_url: HttpUrl
    apify_actor_id: str = "apify/website-content-crawler"

class SlackSettings(BaseModel):
    slack_webhook_url: Optional[str] = None

bearer = HTTPBearer(auto_error=False)

async def verify_client_ownership(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db)
) -> Client:
    """
    Returns the client named in the portal's signed access token.

    This used to trust an X-Client-Id header, so any caller could read any client's briefings by
    changing a number; the portal never sent that header, so its calls failed instead.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        client_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")
    client = db.query(Client).filter(Client.id == client_id, Client.is_active == True).first()
    if not client:
        raise HTTPException(status_code=401, detail="Unauthorized client access")
    return client

@router.get("/competitors", response_model=List[CompetitorResponse])
def list_competitors(client: Client = Depends(verify_client_ownership), db: Session = Depends(get_db)):
    """The authenticated client's competitors (the portal used the admin list of every client's)."""
    return db.query(Competitor).filter(Competitor.client_id == client.id).order_by(Competitor.name).all()

@router.put("/slack", status_code=204)
def update_slack(settings_in: SlackSettings, client: Client = Depends(verify_client_ownership), db: Session = Depends(get_db)):
    """Saves the Slack webhook the briefing is also posted to."""
    client.slack_webhook_url = settings_in.slack_webhook_url or None
    db.commit()
    return None

@router.get("/briefings", response_model=List[BriefingHistoryResponse])
def get_client_briefings(
    skip: int = 0, 
    limit: int = 50,
    client: Client = Depends(verify_client_ownership),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated list of past briefings for the authenticated client.
    """
    briefings = (
        db.query(BriefingHistory)
        .filter(BriefingHistory.client_id == client.id)
        .order_by(BriefingHistory.scrape_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return briefings

@router.post("/competitors", response_model=CompetitorResponse, status_code=201)
def add_competitor(
    competitor_in: PortalCompetitorCreate,
    client: Client = Depends(verify_client_ownership),
    db: Session = Depends(get_db)
):
    """
    Adds a new competitor for the authenticated client.
    """
    new_competitor = Competitor(
        client_id=client.id,
        name=competitor_in.name,
        website_url=str(competitor_in.website_url),
        apify_actor_id=competitor_in.apify_actor_id,
    )
    
    db.add(new_competitor)
    db.commit()
    db.refresh(new_competitor)
    return new_competitor

@router.delete("/competitors/{competitor_id}", status_code=204)
def remove_competitor(
    competitor_id: int,
    client: Client = Depends(verify_client_ownership),
    db: Session = Depends(get_db)
):
    """
    Stops tracking a competitor for the authenticated client.
    """
    competitor = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.client_id == client.id).first()
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found or not owned by client.")
        
    db.delete(competitor)
    db.commit()
    return None
