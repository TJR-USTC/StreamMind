# -*- coding: utf-8 -*-
"""直播路由 — 卡片流 + 控制"""
import asyncio, json, time
from typing import List
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from config import DIM_LABELS
from agents.live_host import LiveHostAgent
from services import live_service

router = APIRouter(prefix="/api/live", tags=["live"])
_users_loader = None

def setup(loader):
    global _users_loader
    _users_loader = loader

@router.get("/stats")
def live_stats():
    s = live_service.aggregate_online_users(_users_loader())
    p = s["preferences"]
    peak = live_service.get_peak_moment()
    return {
        "room_id": live_service.get_live_state()["room_id"],
        "is_live": live_service.get_live_state()["is_live"],
        "online_count": s["count"], "rotation_count": live_service.get_live_state()["rotation_count"],
        "card_count": live_service.get_card_count(),
        "preferences": p,
        "current_top5": live_service.get_current_top5(),
        "baseline_top5": live_service.get_baseline_top5(),
        "peak_moment": peak,
        "history": live_service.get_audience_history()[-20:],
    }

@router.post("/start")
async def live_start(interval: float = Query(15, ge=0.1, le=60)):
    return await live_service.start_live(_users_loader(), interval)

@router.post("/stop")
async def live_stop():
    return await live_service.stop_live()

@router.post("/force-reset")
async def force_reset():
    live_service.get_live_state()["is_live"] = False
    live_service.get_live_state()["online_user_ids"] = []
    live_service.get_card_event().set()
    live_service.get_live_event().set()
    live_service.get_cold_event().set()
    return {"ok": True}


