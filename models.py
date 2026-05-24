# -*- coding: utf-8 -*-
"""Pydantic 数据模型"""
import time
from typing import List
from pydantic import BaseModel, Field
from config import LATENT_DIM

# -------------------------------------------------------
# 视频
# -------------------------------------------------------
class VideoMeta(BaseModel):
    video_id: str
    frame_descriptions: List[str]
    author_tags: List[str]
    duration_sec: int = 60

class TagResult(BaseModel):
    video_id: str
    tags: List[str]
    latent_vector: List[float]
    confidence: float = 0.85
    reasoning: str = ""
    llm_mode: str = "mock"
    elapsed_ms: float = 0.0

class BatchTagReq(BaseModel):
    video_ids: List[str]
    llm_mode: str = "mock"

class BatchTagRes(BaseModel):
    results: List[TagResult]
    total: int
    success: int
    elapsed_ms: float

# -------------------------------------------------------
# 用户
# -------------------------------------------------------
class UserProfile(BaseModel):
    user_id: str
    username: str
    persona_vector: List[float] = Field(default_factory=lambda: [round(1.0 / LATENT_DIM, 4)] * LATENT_DIM)
    last_update_time: float = Field(default_factory=time.time)

class UserBehavior(BaseModel):
    user_id: str
    video_id: str
    is_visited: bool = False
    watch_ratio: int = 0
    is_liked: bool = False
    is_favorited: bool = False
    is_followed: bool = False
    is_commented: bool = False
    comment_text: str = ""

class PersonaUpdateResult(BaseModel):
    user_id: str
    username: str
    old_vector: List[float]
    new_vector: List[float]
    interaction_count: int
    avg_weight: float
    shift_l2: float
    dominant_dim: str
    dominant_score: float

# -------------------------------------------------------
# 直播间
# -------------------------------------------------------
class LivePreferences(BaseModel):
    dim: str
    score: float
    count: int
    pct: float

class LiveStats(BaseModel):
    room_id: str
    is_live: bool
    online_count: int
    rotation_count: int
    avg_vector: List[float]
    preferences: List[LivePreferences]
