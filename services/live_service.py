# -*- coding: utf-8 -*-
import asyncio, math, time
from typing import Any, Dict, List, Optional
from config import LATENT_DIM, DIM_LABELS, MIN_ONLINE_USERS, MAX_ONLINE_USERS, RNG
from config import DRIFT_EUCLIDEAN_THRESHOLD, DRIFT_TOP1_CHANGE
from models import UserProfile
from utils import logger

_lock: asyncio.Lock = asyncio.Lock()

_live_room: Dict[str, Any] = {
    "is_live": False,
    "room_id": "room_001",
    "online_user_ids": [],
    "started_at": 0,
    "rotation_count": 0,
    "rotation_interval": 15,
    "preferences": {},
    "baseline_vector": None,
    "current_vector": None,
    "baseline_top5": [],
    "current_top5": [],
    "card_count": 0,
    "last_card_time": 0,
    "audience_history": [],
    "peak_moment": None,
    "pending_card_type": "",
}

_rotation_task: Optional[asyncio.Task] = None
_live_event: asyncio.Event = asyncio.Event()
_card_event: asyncio.Event = asyncio.Event()
_cold_event: asyncio.Event = asyncio.Event()


def _euclidean(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def aggregate_online_users(users: List[UserProfile]) -> dict:
    online = [u for u in users if u.user_id in _live_room["online_user_ids"]]
    if not online:
        return {"count": 0, "preferences": [], "avg_vector": [0.0] * LATENT_DIM}

    n = len(online)
    # 直接用主导维度计数 (而非向量平均) → Top5 更容易超出70%
    dom_counts = [0] * LATENT_DIM
    for u in online:
        mi = max(range(LATENT_DIM), key=lambda i: u.persona_vector[i])
        dom_counts[mi] += 1

    labeled = [(DIM_LABELS[i], dom_counts[i]) for i in range(LATENT_DIM)]
    labeled.sort(key=lambda x: x[1], reverse=True)
    prefs = [{"dim": d, "score": round(cnt / n, 4), "count": cnt, "pct": round(cnt / n * 100, 1)} for d, cnt in labeled]

    # avg_vector 保留原有语义(用于漂移检测)
    agg = [0.0] * LATENT_DIM
    for u in online:
        for i in range(LATENT_DIM):
            agg[i] += u.persona_vector[i]
    avg = [round(v / n, 4) for v in agg]
    _live_room["preferences"] = {p["dim"]: p["count"] for p in prefs}
    return {"count": n, "preferences": prefs, "avg_vector": avg}


def detect_drift(users: List[UserProfile]) -> dict:
    stats = aggregate_online_users(users)
    current_vec = stats["avg_vector"]
    current_top5 = [p["dim"] for p in stats["preferences"][:5]]
    current_count = stats["count"]

    _live_room["current_vector"] = current_vec
    _live_room["current_top5"] = current_top5
    _live_room["preferences"] = {p["dim"]: p["count"] for p in stats["preferences"]}
    _live_room["audience_history"].append((time.time(), current_count, current_top5[:]))
    if len(_live_room["audience_history"]) > 100:
        _live_room["audience_history"] = _live_room["audience_history"][-100:]

    if _live_room["peak_moment"] is None or current_count >= _live_room["peak_moment"].get("count", 0):
        _live_room["peak_moment"] = {
            "time": time.time(), "count": current_count,
            "top5": current_top5[:], "rotation": _live_room["rotation_count"],
        }

    baseline = _live_room["baseline_vector"]
    baseline_top5 = _live_room.get("baseline_top5", [])

    if baseline is None:
        _live_room["baseline_vector"] = current_vec
        _live_room["baseline_top5"] = current_top5
        return {"drifted": True, "distance": 0.0, "reason": "首次初始化",
                "baseline_top5": [], "current_top5": current_top5}

    dist = _euclidean(baseline, current_vec)
    top5_changed = set(current_top5) != set(baseline_top5)
    drifted = dist >= DRIFT_EUCLIDEAN_THRESHOLD or top5_changed

    reason = ""
    if drifted:
        parts = []
        if dist >= DRIFT_EUCLIDEAN_THRESHOLD:
            parts.append(f"向量偏移 {dist:.3f}")
        if top5_changed:
            new_labels = set(current_top5) - set(baseline_top5)
            old_labels = set(baseline_top5) - set(current_top5)
            msg = "Top5变更"
            if new_labels: msg += f" 新上榜:{','.join(new_labels)}"
            if old_labels: msg += f" 退出:{','.join(old_labels)}"
            parts.append(msg)
        reason = "; ".join(parts)
        _live_room["baseline_vector"] = current_vec
        _live_room["baseline_top5"] = current_top5

    return {"drifted": drifted, "distance": round(dist, 4), "reason": reason,
            "baseline_top5": baseline_top5, "current_top5": current_top5}


def get_top5() -> List[str]:
    """获取当前 Top5 偏好维度"""
    return list(_live_room.get("preferences", {}).keys())[:5]

def get_current_top5() -> List[str]:
    """获取当前 Top5"""
    return _live_room.get("current_top5", [])

def get_baseline_top5() -> List[str]:
    """获取基线 Top5"""
    return _live_room.get("baseline_top5", [])

def get_card_count() -> int:
    """获取已生成卡片数量"""
    return _live_room.get("card_count", 0)

def inc_card_count() -> None:
    """递增卡片计数器"""
    _live_room["card_count"] = _live_room.get("card_count", 0) + 1
    _live_room["last_card_time"] = time.time()

def get_last_card_time() -> float:
    """获取上次卡片生成时间"""
    return _live_room.get("last_card_time", 0)

def get_live_state() -> Dict[str, Any]:
    """获取完整直播状态字典"""
    return _live_room

def get_pending_card_type() -> str:
    """获取待处理的卡片类型"""
    return _live_room.get("pending_card_type", "")

def clear_pending_card() -> None:
    """清除待处理卡片标记"""
    _live_room["pending_card_type"] = ""

def get_card_event() -> asyncio.Event:
    """获取卡片事件"""
    return _card_event

def get_cold_event() -> asyncio.Event:
    """获取冷场事件"""
    return _cold_event

def get_peak_moment() -> Optional[Dict]:
    """获取人气峰值时刻"""
    return _live_room.get("peak_moment")

def get_audience_history() -> List:
    """获取观众历史记录"""
    return _live_room.get("audience_history", [])


async def _rotation_loop(users: List[UserProfile]) -> None:
    """观众轮转循环：定时刷新在线用户并检测漂移"""
    while _live_room["is_live"]:
        await asyncio.sleep(_live_room["rotation_interval"])
        if not _live_room["is_live"]:
            break
        n = RNG.randint(MIN_ONLINE_USERS, MAX_ONLINE_USERS)
        all_ids = [u.user_id for u in users]
        RNG.shuffle(all_ids)
        online_ids = all_ids[:min(n, len(all_ids))]
        for u in users:
            if u.user_id in online_ids:
                v = list(u.persona_vector)
                noise = [max(0.001, x + RNG.gauss(0, 0.05)) for x in v]
                total = sum(noise) or 1.0
                u.persona_vector = [round(x / total, 4) for x in noise]
        _live_room["online_user_ids"] = online_ids
        _live_room["rotation_count"] += 1

        result = detect_drift(users)
        if result["drifted"] and _live_room["rotation_count"] >= 1:
            _live_room["pending_card_type"] = "drift"
        logger.info("[直播] #%d: %d在线, Top1=%s, drift=%s",
                     _live_room['rotation_count'], n,
                     _live_room.get('current_top5', [None])[0] or '?',
                     result['drifted'])

        _live_event.set()


async def start_live(users, interval=15):
    global _rotation_task
    if _live_room["is_live"]:
        return {"ok": False, "msg": "直播已在进行中"}

    n = RNG.randint(MIN_ONLINE_USERS, MAX_ONLINE_USERS)
    all_ids = [u.user_id for u in users]
    RNG.shuffle(all_ids)
    _live_room["online_user_ids"] = all_ids[:min(n, len(all_ids))]
    _live_room["is_live"] = True
    _live_room["started_at"] = time.time()
    _live_room["rotation_count"] = 0
    _live_room["rotation_interval"] = interval
    _live_room["baseline_vector"] = None
    _live_room["baseline_top5"] = []
    _live_room["card_count"] = 0
    _live_room["last_card_time"] = 0
    _live_room["audience_history"] = []
    _live_room["peak_moment"] = None
    _live_event.clear(); _card_event.clear(); _cold_event.clear()

    drift = detect_drift(users)
    _rotation_task = asyncio.create_task(_rotation_loop(users))

    return {"ok": True, "online_count": len(_live_room["online_user_ids"]), "interval_sec": interval,
            "top5": drift["current_top5"], "drifted": drift["drifted"]}


async def stop_live():
    _live_room["is_live"] = False; _live_room["online_user_ids"] = []
    _live_event.set(); _card_event.set(); _cold_event.set()
    if _rotation_task: _rotation_task.cancel()
    return {"ok": True, "peak_moment": _live_room.get("peak_moment"),
            "audience_history": _live_room.get("audience_history", [])[-10:]}
