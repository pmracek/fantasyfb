"""
Data models for ADP collection system
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel

@dataclass
class ADPSource:
    name: str
    base_url: str
    endpoints: Dict[str, str]  # scoring_format -> endpoint
    parser_class: str
    rate_limit_delay: float = 1.0
    requires_auth: bool = False
    headers: Optional[Dict[str, str]] = None

class PlayerADP(BaseModel):
    player_name: str
    player_id: Optional[str] = None
    position: str
    team: Optional[str] = None
    overall_adp: float
    position_rank: Optional[int] = None
    tier: Optional[int] = None
    total_drafts: Optional[int] = None
    std_deviation: Optional[float] = None
    min_pick: Optional[int] = None
    max_pick: Optional[int] = None

class CollectionResult(BaseModel):
    collection_id: str
    collection_timestamp: datetime
    source: str
    season: int
    scoring_format: str
    league_size: int
    draft_type: str
    players: List[PlayerADP]
    success: bool
    error_message: Optional[str] = None

class PlayerCrosswalk(BaseModel):
    canonical_player_id: str
    canonical_name: str
    position: str
    nfl_team: Optional[str] = None
    source: str
    source_player_id: Optional[str] = None
    source_name: str
    confidence_score: float
    is_active: bool = True

class TrendData(BaseModel):
    canonical_player_id: str
    player_name: str
    position: str
    nfl_team: Optional[str] = None
    scoring_format: str
    trend_date: date
    current_adp: float
    adp_7d_change: Optional[float] = None
    adp_14d_change: Optional[float] = None
    adp_30d_change: Optional[float] = None
    volatility_score: Optional[float] = None
    momentum_score: Optional[float] = None
    opportunity_rank: Optional[int] = None