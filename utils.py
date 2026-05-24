# -*- coding: utf-8 -*-
import json
import logging

logger = logging.getLogger("streammind")


def extract_json(content: str) -> dict:
    """从 LLM 返回内容中提取 JSON，支持 markdown 代码块包裹"""
    raw = content
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    return json.loads(raw.strip())
