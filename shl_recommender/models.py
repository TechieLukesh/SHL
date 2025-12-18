from pydantic import BaseModel
from typing import List, Optional, Any


class RecommendationRequest(BaseModel):
    job_description: Optional[str] = None
    url: Optional[str] = None
    top_k: Optional[int] = 10
    # Optional flags to control recommendation behavior
    balanced: Optional[bool] = False
    exclude_prepackaged: Optional[bool] = False
    # Optional tuning parameters (dev use)
    w_skill: Optional[float] = None
    w_embed: Optional[float] = None
    w_diff: Optional[float] = None
    prefer_ratio: Optional[float] = None


class Assessment(BaseModel):
    # make fields optional to tolerate variable catalog entries
    assessment_id: Optional[str] = None
    url: Optional[str] = None
    adaptive_support: Optional[Any] = None
    description: Optional[str] = None
    duration: Optional[Any] = None
    remote_support: Optional[Any] = None
    test_type: Optional[List[str]] = None
    score: Optional[float] = None
    skills: Optional[List[str]] = None


class RecommendationResponse(BaseModel):
    recommended_assessments: List[Assessment]
