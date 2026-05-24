# -*- coding: utf-8 -*-
"""Agent 3: 决策卡片生成器 — 支持开场卡片 + 冷场救援"""
import json, random
from typing import List
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from utils import extract_json

SYSTEM_PROMPT = """你是一个数据敏锐的主播操盘手。你需要给主播生成"决策卡片"。

严格返回 JSON 格式:
```json
{
  "topic": "建议话题",
  "reason": "一句话解释为何切换",
  "script": "自然口播过渡语(50字内)"
}
```"""

USER_PROMPT_DRIFT = """【画像漂移】
之前 Top3: {baseline}
当前 Top3: {current}
在线人数: {online}

分析突变原因，生成决策卡片。"""

USER_PROMPT_INITIAL = """【首次开播】
当前 Top3: {current}
在线人数: {online}

这是直播的第一张卡片。请根据当前观众画像，给出开场话题和第一波产品方向。"""

USER_PROMPT_COLD = """【冷场救援】
当前 Top3: {current}
在线人数: {online}
已沉默 {idle_sec} 秒，人气正在下降。

请生成一张"救场卡片"——提出一个能立刻拉回观众注意力的话题或互动游戏。"""

MOCK_CARDS = {
    "initial": [
        {"topic": "开场福利大放送", "reason": "首次开播, 用福利留住第一波观众",
         "script": "来了来了！今天直播正式开始——我先不说别的, 小黄车第一个福利先给大家安排上！"},
        {"topic": "今日主打星品", "reason": "当前观众画像匹配, 开局即推核心产品",
         "script": "好, 直播正式开始！今天要聊的东西, 我准备了很久——绝对不让你们失望！"},
    ],
    "drift": [
        {"topic": "{t}专场推荐", "reason": "检测到偏好从{o}转向{t}, 立即调整话术",
         "script": "说到这儿我突然发现, 今天直播间里好多朋友其实对{t}特别感兴趣——那我必须给你们安排一波！"},
        {"topic": "{t}深度解析", "reason": "Top1变为{t}, 涌入大量该领域观众",
         "script": "来咱们换个话题——我看弹幕里好多人在问{t}相关的东西, 今天不聊这个可说不过去！"},
    ],
    "cold": [
        {"topic": "互动抽奖时刻", "reason": "冷场{idle}秒, 用抽奖拉回注意力",
         "script": "等一下等一下——我看公屏有点安静啊！这样, 在线的朋友扣个1, 我抽3个人送福利！"},
        {"topic": "弹幕问答环节", "reason": "人气下滑, 互动问答激活观众",
         "script": "好, 咱们玩个游戏——你们随便问, 我能答的都答！关于{current}的问题优先！"},
        {"topic": "限时秒杀倒计时", "reason": "冷场中, 用紧迫感刺激下单",
         "script": "不跟你们开玩笑了——小黄车这个链接, 我再放最后3分钟！3分钟后准时下架, 没拍的抓紧！"},
    ],
}


class LiveHostAgent:
    def __init__(self, llm_mode: str = "openai"):
        self.mode = llm_mode

    async def generate_card(
        self,
        card_type: str,
        baseline_top3: List[str],
        current_top3: List[str],
        online_count: int,
        idle_sec: int = 0,
        top5_list: List[str] = None,
        top5_scores: List[float] = None,
    ) -> dict:
        """card_type: 'initial' | 'drift' | 'cold'"""
        if self.mode == "mock":
            return self._mock(card_type, baseline_top3, current_top3, online_count, idle_sec)

        try:
            import openai
        except ImportError:
            return self._mock(card_type, baseline_top3, current_top3, online_count, idle_sec)

        current_top1 = current_top3[0] if current_top3 else "通用"
        prev_top1 = baseline_top3[0] if baseline_top3 else "无"
        top5_str = ""
        if top5_list and top5_scores:
            items = [f"{d}({s*100:.0f}%)" for d, s in zip(top5_list[:5], top5_scores[:5])]
            top5_str = ", ".join(items)

        if card_type == "initial":
            user_msg = f"【首次开播】\n当前Top3: {', '.join(current_top3)}\n观众偏好分布: {top5_str}\n在线: {online_count}\n请生成开场卡片(话题/洞察/口播过渡)"
        elif card_type == "cold":
            user_msg = f"【冷场救援】\n当前Top3: {', '.join(current_top3)}\n分布: {top5_str}\n在线: {online_count}\n沉默{idle_sec}秒, 人气下降, 请生成救场卡片"
        else:
            user_msg = f"【画像漂移】\n之前Top1: {prev_top1}\n当前Top1: {current_top1}\n全部分布: {top5_str}\n在线: {online_count}\n请分析漂移原因, 生成决策卡片"

        client = openai.AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        try:
            resp = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": user_msg}],
                temperature=0.7, max_tokens=300,
            )
            return self._parse(resp.choices[0].message.content or "", card_type,
                               baseline_top3, current_top3, online_count, idle_sec)
        except Exception:
            return self._mock(card_type, baseline_top3, current_top3, online_count, idle_sec)

    def _parse(self, content: str, card_type: str, baseline: List[str],
               current: List[str], online: int, idle: int) -> dict:
        """解析 LLM 返回的 JSON 决策卡片"""
        try:
            data = extract_json(content)
            return {"topic": data.get("topic", ""), "reason": data.get("reason", ""), "script": data.get("script", "")}
        except json.JSONDecodeError:
            return self._mock(card_type, baseline, current, online, idle)

    def _mock(self, card_type: str, baseline: List[str], current: List[str],
              online: int, idle: int) -> dict:
        """mock 模式：从模板库随机选取并变量替换"""
        t = current[0] if current else "通用"
        o = baseline[0] if baseline else "之前"
        pool = MOCK_CARDS.get(card_type, MOCK_CARDS["drift"])
        card = random.choice(pool)
        return {
            "topic": card["topic"].replace("{t}", t).replace("{o}", o).replace("{current}", t).replace("{idle}", str(idle)),
            "reason": card["reason"].replace("{t}", t).replace("{o}", o).replace("{current}", t).replace("{idle}", str(idle)),
            "script": card["script"].replace("{t}", t).replace("{o}", o).replace("{current}", t).replace("{idle}", str(idle)),
        }
