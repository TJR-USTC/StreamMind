# -*- coding: utf-8 -*-
"""直播路由 — 卡片流 + 控制"""
import asyncio, json, time
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
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

@router.get("/cards/stream")
async def card_stream(llm_mode: str = Query("openai")):
    if not live_service.get_live_state()["is_live"]:
        async def _e():
            yield f"data: {json.dumps({'type':'error'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(_e(), media_type="text/event-stream")

    agent = LiveHostAgent(llm_mode=llm_mode)

    async def _gen():
        # 清除任何残留的 pending_card_type, 确保只生成1张开场卡片
        live_service.clear_pending_card()
        bl5 = live_service.get_baseline_top5()
        cr5 = live_service.get_current_top5()
        on = len(live_service.get_live_state()["online_user_ids"])
        stats = live_service.aggregate_online_users(_users_loader())
        top5_list = [p["dim"] for p in stats["preferences"][:5]]
        top5_scores = [p["score"] for p in stats["preferences"][:5]]
        card = await agent.generate_card("initial", bl5, cr5, on, 0, top5_list, top5_scores)
        live_service.inc_card_count()
        yield f"data: {json.dumps({'type':'card','card':card,'card_number':live_service.get_card_count(),'card_type':'initial','baseline':bl5,'current':cr5,'online':on}, ensure_ascii=False)}\n\n"

        while live_service.get_live_state()["is_live"]:
            await asyncio.sleep(1)
            if not live_service.get_live_state()["is_live"]: break

            ct = live_service.get_pending_card_type()
            if not ct:
                yield f"data: {json.dumps({'type':'heartbeat','online':len(live_service.get_live_state()['online_user_ids'])}, ensure_ascii=False)}\n\n"
                continue

            live_service.clear_pending_card()
            bl5 = live_service.get_baseline_top5()
            cr5 = live_service.get_current_top5()
            on = len(live_service.get_live_state()["online_user_ids"])
            idle = int(time.time()-live_service.get_last_card_time()) if live_service.get_last_card_time() else 0
            stats2 = live_service.aggregate_online_users(_users_loader())
            top5_l = [p["dim"] for p in stats2["preferences"][:5]]
            top5_s = [p["score"] for p in stats2["preferences"][:5]]

            card = await agent.generate_card(ct, bl5, cr5, on, idle, top5_l, top5_s)
            live_service.inc_card_count()
            yield f"data: {json.dumps({'type':'card','card':card,'card_number':live_service.get_card_count(),'card_type':ct,'baseline':bl5,'current':cr5,'online':on}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type':'stopped'})}\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control":"no-cache","Connection":"keep-alive"})

@router.get("/users/online")
def get_online_users():
    users = _users_loader()
    online_ids = live_service.get_live_state()["online_user_ids"]
    online = [u for u in users if u.user_id in online_ids]
    return {
        "count": len(online),
        "online": [{"user_id":u.user_id,"username":u.username,"persona_vector":u.persona_vector,
                     "dominant_dim":max(range(len(u.persona_vector)),key=lambda i:u.persona_vector[i]),
                     "top3":sorted([(i,v) for i,v in enumerate(u.persona_vector)],key=lambda x:x[1],reverse=True)[:3]} for u in online],
        "labels": DIM_LABELS}

@router.get("/clips")
def get_clips():
    peak = live_service.get_peak_moment()
    return {"peak_moment":peak}

@router.post("/cold-field")
async def trigger_cold_field(source:str="mic"):
    if not live_service.get_live_state()["is_live"]: return {"ok":False}
    live_service.get_live_state()["pending_card_type"] = "cold"
    return {"ok":True}

from config import DIM_LABELS
