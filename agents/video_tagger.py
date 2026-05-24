# -*- coding: utf-8 -*-
"""Agent 1: 视频打标智能体 — 12维版"""
import asyncio, json, time
from typing import List
from config import LATENT_DIM, CATEGORIES, DOMAIN_VECTOR_MAP, RNG, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from models import VideoMeta, TagResult

TAG_MAP = {
    "知识干货": {"tags": ["知识科普", "硬核干货", "学习"], "vec": DOMAIN_VECTOR_MAP["知识干货"]},
    "游戏娱乐": {"tags": ["游戏实况", "电竞", "主机游戏"], "vec": DOMAIN_VECTOR_MAP["游戏娱乐"]},
    "美食探店": {"tags": ["美食教程", "探店打卡", "家常菜"], "vec": DOMAIN_VECTOR_MAP["美食探店"]},
    "科技数码": {"tags": ["数码测评", "开箱", "黑科技"], "vec": DOMAIN_VECTOR_MAP["科技数码"]},
    "户外旅行": {"tags": ["旅行风景", "航拍", "户外"], "vec": DOMAIN_VECTOR_MAP["户外旅行"]},
    "萌宠日常": {"tags": ["萌宠日常", "猫咪", "狗狗"], "vec": DOMAIN_VECTOR_MAP["萌宠日常"]},
    "情感心理": {"tags": ["情感共鸣", "心理治愈", "人生感悟"], "vec": DOMAIN_VECTOR_MAP["情感心理"]},
    "穿搭美妆": {"tags": ["穿搭分享", "美妆教程", "OOTD"], "vec": DOMAIN_VECTOR_MAP["穿搭美妆"]},
    "运动健身": {"tags": ["健身打卡", "减脂增肌", "运动教程"], "vec": DOMAIN_VECTOR_MAP["运动健身"]},
    "影视八卦": {"tags": ["影视解说", "娱乐八卦", "追剧"], "vec": DOMAIN_VECTOR_MAP["影视八卦"]},
    "职场提升": {"tags": ["职场干货", "面试技巧", "效率提升"], "vec": DOMAIN_VECTOR_MAP["职场提升"]},
    "家居生活": {"tags": ["家居好物", "收纳整理", "生活美学"], "vec": DOMAIN_VECTOR_MAP["家居生活"]},
}


class VideoTaggingAgent:
    def __init__(self, llm_mode: str = "mock"):
        self.mode = llm_mode

    async def tag(self, video: VideoMeta) -> TagResult:
        t0 = time.perf_counter()
        if self.mode == "mock":
            r = self._mock(video)
        elif self.mode == "openai":
            r = await self._llm(video)
        else:
            r = self._mock(video)
        r.elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        r.llm_mode = self.mode
        return r

    async def tag_batch(self, videos: List[VideoMeta], concurrency: int = 8) -> List[TagResult]:
        sem = asyncio.Semaphore(concurrency)
        async def _one(v):
            async with sem: return await self.tag(v)
        return await asyncio.gather(*[_one(v) for v in videos])

    def _mock(self, video: VideoMeta) -> TagResult:
        txt = " ".join(video.frame_descriptions) + " " + " ".join(video.author_tags)
        best, best_score = CATEGORIES[-1], 0
        for cat in CATEGORIES:
            s = sum(1 for w in [cat, cat + "博主", cat + "达人"] if w in txt)
            if s > best_score: best_score, best = s, cat
        info = TAG_MAP.get(best, TAG_MAP[CATEGORIES[-1]])
        base = info["vec"]
        noisy = [max(0.005, v + RNG.gauss(0, 0.04)) for v in base]
        t = sum(noisy)
        vec = [round(v / t, 4) for v in noisy]
        return TagResult(
            video_id=video.video_id, tags=info["tags"][:3],
            latent_vector=vec, confidence=round(RNG.uniform(0.80, 0.97), 2),
            reasoning=f"关键词匹配 -> 领域={best}",
        )

    async def _llm(self, video: VideoMeta) -> TagResult:
        try:
            import openai
        except ImportError:
            return self._mock(video)
        client = openai.AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        frames = "\n  - ".join(video.frame_descriptions)
        prompt = (
            f"帧描述:\n  - {frames}\n\n"
            f"作者标签: {', '.join(video.author_tags)}\n"
            f"请返回JSON: {{\"tags\":[...],\"vector\":[v1..v{LATENT_DIM}],\"reasoning\":\"...\"}}"
        )
        try:
            resp = await client.chat.completions.create(
                model=LLM_MODEL, messages=[{"role": "user", "content": prompt}],
                temperature=0.3, max_tokens=500,
            )
            content = resp.choices[0].message.content or ""
            raw = content
            if "```json" in content: raw = content.split("```json")[1].split("```")[0]
            elif "```" in content: raw = content.split("```")[1].split("```")[0]
            data = json.loads(raw.strip())
            v = data.get("vector", [0.1] * LATENT_DIM)
            s = sum(v) or 1
            return TagResult(
                video_id=video.video_id, tags=data.get("tags", ["通用"])[:3],
                latent_vector=[round(x / s, 4) for x in v],
                confidence=float(data.get("confidence", 0.8)),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            r = self._mock(video)
            r.llm_mode = "mock(fallback)"
            r.reasoning = f"LLM调用失败: {e}"
            return r
