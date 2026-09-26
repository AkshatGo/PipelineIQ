from fastapi import APIRouter

from pipelineiq.contracts import RiskAssessment, RiskAssessmentRequest
from pipelineiq.services.risk import assess_risk

router = APIRouter(prefix="/risk", tags=["risk"])


@router.post("/assess", response_model=RiskAssessment)
async def create_risk_assessment(payload: RiskAssessmentRequest) -> RiskAssessment:
    return assess_risk(payload.signals, payload.profile)

