# -*- coding: utf-8 -*-
"""视频相关路由"""
import time
from fastapi import APIRouter, HTTPException, Query
from models import VideoMeta, TagResult, BatchTagReq, BatchTagRes
from agents.video_tagger import VideoTaggingAgent

router = APIRouter(prefix="/api/videos", tags=["videos"])

# ---- 依赖注入接口 ----
_videos_loader = None
_tags_cache = {}


def setup(loader, cache):
    global _videos_loader, _tags_cache
    _videos_loader = loader
    _tags_cache = cache


# ---- 端点 ----

@router.get("")
def list_videos(limit: int = Query(100, ge=1, le=100),
                offset: int = Query(0, ge=0)):
    all_v = _videos_loader()
    page = all_v[offset:offset + limit]
    return {
        "total": len(all_v), "offset": offset, "limit": limit,
        "items": [v.model_dump() for v in page],
    }


@router.get("/{video_id}")
def get_video(video_id: str):
    for v in _videos_loader():
        if v.video_id == video_id:
            return v.model_dump()
    raise HTTPException(404, f"视频 {video_id} 不存在")


@router.post("/tag", response_model=TagResult)
async def tag_video(video: VideoMeta, llm_mode: str = Query("mock")):
    agent = VideoTaggingAgent(llm_mode)
    r = await agent.tag(video)
    _tags_cache[r.video_id] = r
    return r


@router.post("/tag/batch", response_model=BatchTagRes)
async def tag_batch(req: BatchTagReq):
    t0 = time.perf_counter()
    vmap = {v.video_id: v for v in _videos_loader()}
    targets = [vmap[vid] for vid in req.video_ids if vid in vmap]
    if not targets:
        raise HTTPException(400, "无有效视频ID")
    agent = VideoTaggingAgent(req.llm_mode)
    results = await agent.tag_batch(targets)
    for r in results:
        _tags_cache[r.video_id] = r
    return BatchTagRes(
        results=results, total=len(req.video_ids),
        success=len(targets),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    )


@router.get("/{video_id}/tags")
def get_video_tags(video_id: str):
    if video_id in _tags_cache:
        return _tags_cache[video_id].model_dump()
    raise HTTPException(404, f"视频 {video_id} 尚未打标")
