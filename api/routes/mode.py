from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.deps import get_mode, set_mode

router = APIRouter()


class SetModeRequest(BaseModel):
    mode: Literal["paper", "live"]


class ModeResponse(BaseModel):
    mode: str


@router.post("/mode", response_model=ModeResponse)
def switch_mode(req: SetModeRequest):
    set_mode(req.mode)
    return ModeResponse(mode=get_mode())
