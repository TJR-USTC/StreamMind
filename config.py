# -*- coding: utf-8 -*-
"""全局配置常量 — 12维扩展版"""
import os, random

LATENT_DIM = 12
DIM_LABELS = [
    "知识干货", "游戏娱乐", "美食探店", "科技数码",
    "户外旅行", "萌宠日常", "情感心理", "穿搭美妆",
    "运动健身", "影视八卦", "职场提升", "家居生活",
]

# 每维独立标称向量 (单位阵 + 微扰避免全零)
DOMAIN_VECTOR_MAP = {}
for idx, label in enumerate(DIM_LABELS):
    vec = [0.01] * LATENT_DIM
    vec[idx] = 0.88
    DOMAIN_VECTOR_MAP[label] = vec

CATEGORIES = DIM_LABELS

# 请设置您自己的 LLM API Key，支持 DeepSeek / OpenAI 等兼容接口
# 方式一: 设置环境变量 export LLM_API_KEY="sk-xxxx"
# 方式二: 在项目根目录创建 .env 文件，写入 LLM_API_KEY=sk-xxxx
LLM_API_KEY = os.environ.get("LLM_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
DEFAULT_LLM_MODE = "openai"  # 默认使用真实大模型

# ---- 向量漂移检测阈值 ----
DRIFT_EUCLIDEAN_THRESHOLD = 0.05   # 欧氏距离阈值 (降低以更容易触发飘移)
DRIFT_TOP1_CHANGE = True           # Top1标签变化也算触发

DEFAULT_ROTATION_INTERVAL = 5
MAX_ONLINE_USERS = 50
MIN_ONLINE_USERS = 10

EMA_ALPHA = 0.6  # 提高新信息权重 (原来0.3太慢)
EMA_BETA = 0.4

RNG = random.Random(42)
