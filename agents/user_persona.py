# -*- coding: utf-8 -*-
"""Agent 2: 用户画像更新智能体"""
import math
import time
from typing import Dict, List
from config import LATENT_DIM, DIM_LABELS, EMA_ALPHA, EMA_BETA
from models import UserProfile, UserBehavior, PersonaUpdateResult


class UserPersonaAgent:
    """基于EMA算法的用户画像更新Agent"""

    def __init__(self, alpha: float = EMA_ALPHA, beta: float = EMA_BETA):
        self.alpha = alpha
        self.beta = beta

    def update_one(self, user: UserProfile, bhv: UserBehavior,
                   vid_vec: List[float]) -> bool:
        """单次交互更新, 返回是否实际更新"""
        if not bhv.is_visited:
            return False

        c = (
            (bhv.watch_ratio / 100.0) * 0.40
            + (1 if bhv.is_liked else 0) * 0.20
            + (1 if bhv.is_favorited else 0) * 0.30
            + (1 if bhv.is_followed else 0) * 0.05
            + (1 if bhv.is_commented else 0) * 0.05
        )
        c = max(0.0, min(1.0, c))

        old = user.persona_vector
        nv = self._norm(vid_vec)
        new = [old[i] * self.beta + nv[i] * c * self.alpha for i in range(LATENT_DIM)]
        user.persona_vector = self._norm(new)
        user.last_update_time = time.time()
        return True

    def batch_update(self, user: UserProfile, behaviors: List[UserBehavior],
                     vec_map: Dict[str, List[float]]) -> PersonaUpdateResult:
        """批量处理一个用户的全部行为"""
        old_vec = list(user.persona_vector)
        cnt, total_w = 0, 0.0

        for b in behaviors:
            if not b.is_visited:
                continue
            vv = vec_map.get(b.video_id, [0.2] * LATENT_DIM)
            if self.update_one(user, b, vv):
                cnt += 1
                c = (
                    (b.watch_ratio / 100.0) * 0.40 + (1 if b.is_liked else 0) * 0.20
                    + (1 if b.is_favorited else 0) * 0.30
                    + (1 if b.is_followed else 0) * 0.05
                    + (1 if b.is_commented else 0) * 0.05
                )
                total_w += max(0.0, min(1.0, c))

        nv = user.persona_vector
        shift = math.sqrt(sum((a - b) ** 2 for a, b in zip(nv, old_vec)))
        mi = max(range(LATENT_DIM), key=lambda i: nv[i])

        return PersonaUpdateResult(
            user_id=user.user_id,
            username=user.username,
            old_vector=old_vec,
            new_vector=nv,
            interaction_count=cnt,
            avg_weight=round(total_w / max(cnt, 1), 4),
            shift_l2=round(shift, 4),
            dominant_dim=DIM_LABELS[mi],
            dominant_score=round(nv[mi], 4),
        )

    @staticmethod
    def _norm(v: List[float]) -> List[float]:
        s = sum(v) or 1.0
        return [round(x / s, 4) for x in v]

    @staticmethod
    def compute_weight(bhv: UserBehavior) -> float:
        if not bhv.is_visited:
            return 0.0
        c = (
            (bhv.watch_ratio / 100.0) * 0.40 + (1 if bhv.is_liked else 0) * 0.20
            + (1 if bhv.is_favorited else 0) * 0.30
            + (1 if bhv.is_followed else 0) * 0.05
            + (1 if bhv.is_commented else 0) * 0.05
        )
        return max(0.0, min(1.0, c))
