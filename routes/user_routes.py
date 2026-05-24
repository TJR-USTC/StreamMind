# -*- coding: utf-8 -*-
"""用户相关路由"""
import time
from fastapi import APIRouter, HTTPException, Query
from models import PersonaUpdateResult
from agents.user_persona import UserPersonaAgent

router = APIRouter(prefix="/api/users", tags=["users"])

_users_loader = None
_behaviors_loader = None
_vec_map_loader = None


def setup(users_loader, behaviors_loader, vec_map_loader):
    global _users_loader, _behaviors_loader, _vec_map_loader
    _users_loader = users_loader
    _behaviors_loader = behaviors_loader
    _vec_map_loader = vec_map_loader


@router.get("")
def list_users(limit: int = Query(20, ge=1, le=100),
               offset: int = Query(0, ge=0)):
    all_u = _users_loader()
    page = all_u[offset:offset + limit]
    return {
        "total": len(all_u), "offset": offset, "limit": limit,
        "items": [u.model_dump() for u in page],
    }


@router.get("/stats/all")
def get_all_user_stats():
    """返回所有用户画像 + 行为特征汇总"""
    users = _users_loader()
    bm = _behaviors_loader()
    results = []
    for u in users:
        blist = bm.get(u.user_id, [])
        total = len(blist)
        visited = [b for b in blist if b.is_visited]
        vc = len(visited)
        if vc > 0:
            avg_watch = sum(b.watch_ratio for b in visited) / vc
            like_rate = sum(1 for b in visited if b.is_liked) / vc
            fav_rate = sum(1 for b in visited if b.is_favorited) / vc
            com_rate = sum(1 for b in visited if b.is_commented) / vc
            fol_rate = sum(1 for b in visited if b.is_followed) / vc
        else:
            avg_watch = like_rate = fav_rate = com_rate = fol_rate = 0
        dom_idx = max(range(len(u.persona_vector)), key=lambda i: u.persona_vector[i])
        results.append({
            "user_id": u.user_id,
            "username": u.username,
            "persona_vector": u.persona_vector,
            "dominant_dim": dom_idx,
            "total_behaviors": total,
            "visited_count": vc,
            "avg_watch_ratio": round(avg_watch, 1),
            "like_rate": round(like_rate * 100, 1),
            "favorite_rate": round(fav_rate * 100, 1),
            "comment_rate": round(com_rate * 100, 1),
            "follow_rate": round(fol_rate * 100, 1),
        })
    return {"total": len(results), "users": results}
    for u in _users_loader():
        if u.user_id == user_id:
            return u.model_dump()
    raise HTTPException(404, f"用户 {user_id} 不存在")


@router.get("/{user_id}/behaviors")
def get_user_behaviors(user_id: str, limit: int = Query(50, ge=1, le=200),
                       offset: int = Query(0, ge=0)):
    bm = _behaviors_loader()
    if user_id not in bm:
        raise HTTPException(404, f"用户 {user_id} 不存在")
    all_b = bm[user_id]
    page = all_b[offset:offset + limit]
    visited = sum(1 for b in page if b.is_visited)
    return {
        "user_id": user_id, "total_behaviors": len(all_b),
        "visited_count": visited, "offset": offset, "limit": limit,
        "items": [b.model_dump() for b in page],
    }


@router.post("/{user_id}/update-persona", response_model=PersonaUpdateResult)
def update_user_persona(user_id: str):
    u = next((x for x in _users_loader() if x.user_id == user_id), None)
    if not u:
        raise HTTPException(404, f"用户 {user_id} 不存在")
    bm = _behaviors_loader()
    if user_id not in bm:
        raise HTTPException(404, "无行为数据")
    agent = UserPersonaAgent()
    return agent.batch_update(u, bm[user_id], _vec_map_loader())


@router.post("/update-all-personas")
def update_all_personas():
    t0 = time.perf_counter()
    vm = _vec_map_loader()
    agent = UserPersonaAgent()
    users = _users_loader()
    results = [
        agent.batch_update(u, _behaviors_loader().get(u.user_id, []), vm)
        for u in users
    ]
    dom = {}
    for r in results:
        dom[r.dominant_dim] = dom.get(r.dominant_dim, 0) + 1
    return {
        "total_users": len(users),
        "updated": len(results),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "avg_shift_l2": round(sum(r.shift_l2 for r in results) / len(results), 4),
        "dominant_distribution": dom,
        "results": [r.model_dump() for r in results[:5]],
    }
