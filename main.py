# -*- coding: utf-8 -*-
"""
============================================================================
多智能体直播运营系统 — 工程化重构版
启动: python main.py   或   uvicorn main:app --reload --port 8000
============================================================================
"""
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import LATENT_DIM, CATEGORIES, DOMAIN_VECTOR_MAP
from data_generator import MockDataGenerator, video_category
from models import VideoMeta, UserProfile, UserBehavior
from typing import Dict, List


# ---- 自定义UTF-8 JSON响应 ----
class UTF8JSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False, default=str).encode("utf-8")


# ---- FastAPI 应用 ----
app = FastAPI(title="多智能体直播运营系统", version="4.0.0", default_response_class=UTF8JSONResponse)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# =========================================================================
# 全局数据层 (懒加载 + 缓存)
# =========================================================================
_generator = MockDataGenerator()

_videos: List[VideoMeta] = []
_users: List[UserProfile] = []
_behaviors: Dict[str, List[UserBehavior]] = {}
_tags_cache: dict = {}
_vec_map: Dict[str, List[float]] = {}


def _load_videos() -> List[VideoMeta]:
    global _videos
    if not _videos:
        _videos = _generator.make_videos(100)
    return _videos


def _load_users() -> List[UserProfile]:
    global _users
    if not _users:
        _users = _generator.make_users(100)
    return _users


def _load_behaviors() -> Dict[str, List[UserBehavior]]:
    global _behaviors
    if not _behaviors:
        _behaviors = _generator.make_behaviors(_load_users(), len(_load_videos()))
    return _behaviors


def _load_vec_map() -> Dict[str, List[float]]:
    global _vec_map
    if not _vec_map:
        for v in _load_videos():
            vid = v.video_id
            if vid in _tags_cache:
                _vec_map[vid] = _tags_cache[vid].latent_vector
            else:
                cat = video_category(vid)
                _vec_map[vid] = DOMAIN_VECTOR_MAP.get(cat, [0.2] * LATENT_DIM)
    return _vec_map

# =========================================================================
# 注册路由
# =========================================================================
from routes import video_routes, user_routes, live_routes

video_routes.setup(_load_videos, _tags_cache)
user_routes.setup(_load_users, _load_behaviors, _load_vec_map)
live_routes.setup(_load_users)

app.include_router(video_routes.router)
app.include_router(user_routes.router)
app.include_router(live_routes.router)


# =========================================================================
# 根路由
# =========================================================================
@app.get("/")
def root():
    return {
        "service": "多智能体直播运营系统",
        "version": "4.0.0",
        "videos": len(_load_videos()),
        "users": len(_load_users()),
        "tags_cached": len(_tags_cache),
    }


@app.get("/api/health")
def health():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/stats")
def stats():
    dc = {}
    for v in _load_videos():
        cat = video_category(v.video_id)
        dc[cat] = dc.get(cat, 0) + 1
    return {
        "total_videos": len(_load_videos()),
        "domain_distribution": dc,
        "tagged_count": len(_tags_cache),
        "user_count": len(_load_users()),
        "behavior_count": sum(len(bl) for bl in _load_behaviors().values()),
    }


@app.get("/api/behavior/stats")
def behavior_stats():
    bm = _load_behaviors()
    all_b = [b for bl in bm.values() for b in bl]
    total = len(all_b)
    visited = sum(1 for b in all_b if b.is_visited)
    liked = sum(1 for b in all_b if b.is_liked)
    fav = sum(1 for b in all_b if b.is_favorited)
    fol = sum(1 for b in all_b if b.is_followed)
    com = sum(1 for b in all_b if b.is_commented)
    bins = {"0~20%": 0, "20~40%": 0, "40~60%": 0, "60~80%": 0, "80~100%": 0}
    for b in all_b:
        if not b.is_visited:
            continue
        if b.watch_ratio <= 20: bins["0~20%"] += 1
        elif b.watch_ratio <= 40: bins["20~40%"] += 1
        elif b.watch_ratio <= 60: bins["40~60%"] += 1
        elif b.watch_ratio <= 80: bins["60~80%"] += 1
        else: bins["80~100%"] += 1
    return {
        "total_records": total, "visited": visited,
        "visit_rate": round(visited / total * 100, 1) if total else 0,
        "like_rate": round(liked / visited * 100, 1) if visited else 0,
        "favorite_rate": round(fav / visited * 100, 1) if visited else 0,
        "follow_rate": round(fol / visited * 100, 1) if visited else 0,
        "comment_rate": round(com / visited * 100, 1) if visited else 0,
        "watch_distribution": bins,
    }


# =========================================================================
# 启动入口
# =========================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
