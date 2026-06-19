"""LLM-based Design Parameter Parser"""

import hashlib
import json
from typing import Optional
from functools import lru_cache

import httpx
from pydantic import BaseModel

from app.core.config import settings


class DesignParams(BaseModel):
    """Structured design parameters extracted from user input"""
    shape: str
    glaze_color: str
    size: str
    style: str
    emotion: str
    material: str
    usage: str


PROMPT_TEMPLATE = """你是一个专业的陶瓷设计师助手。请分析用户的描述，提取以下设计参数：

- shape: 主体造型描述（如：兔子、花瓶、茶杯等）
- glaze_color: 釉色（如：冷白釉、青瓷釉、哑光黑等）
- size: 建议尺寸（如：18-22cm，或根据用途推断）
- style: 风格（如：新中式、极简、侘寂等）
- emotion: 情感意象（如：温馨、庄重、治愈等）
- material: 材质（如：白瓷、紫砂、粗陶等）
- usage: 用途（如：玄关摆件、花瓶、茶宠等）

请以JSON格式输出，每个字段都要有值。

用户输入：{user_input}
"""

# Keyword blacklist for input validation
BLACKLIST = [
    "毒品", "赌博", "武器", "色情", "暴力",
    "政治", "邪教", "自杀"
]


class LLMParseError(Exception):
    """Error during LLM parsing"""
    pass


class InputValidationError(Exception):
    """Input validation failed"""
    pass


def validate_input(text: str) -> None:
    """Validate input text for prohibited content"""
    if len(text) > 200:
        raise InputValidationError("输入过长，请控制在200字以内")

    for keyword in BLACKLIST:
        if keyword in text:
            raise InputValidationError(f"输入包含不当内容，请重新描述")


def hash_prompt(text: str, model: str) -> str:
    """Generate cache key for prompt"""
    return hashlib.sha256(f"{text}:{model}".encode()).hexdigest()


@lru_cache(maxsize=100)
def _cached_result(cache_key: str) -> Optional[dict]:
    """Dummy cache for typing"""
    return None


async def parse_design_params(user_input: str, use_cache: bool = True) -> DesignParams:
    """
    Parse user input into structured design parameters using LLM.

    Args:
        user_input: Natural language input from user
        use_cache: Whether to use cached results

    Returns:
        DesignParams with extracted fields

    Raises:
        InputValidationError: If input is invalid
        LLMParseError: If LLM parsing fails
    """
    # Validate input
    validate_input(user_input)

    cache_key = hash_prompt(user_input, settings.LLM_PROVIDER)

    if use_cache:
        cached = _cached_result(cache_key)
        if cached:
            return DesignParams(**cached)

    # Call LLM API
    if settings.LLM_PROVIDER == "tongyi":
        result = await _call_tongyi(user_input)
    elif settings.LLM_PROVIDER == "openai":
        result = await _call_openai(user_input)
    else:
        # Fallback to mock
        result = _mock_parse(user_input)

    return DesignParams(**result)


async def _call_tongyi(user_input: str) -> dict:
    """Call Tongyi API for parsing"""
    if not settings.TONGYI_API_KEY:
        return _mock_parse(user_input)

    prompt = PROMPT_TEMPLATE.format(user_input=user_input)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {settings.TONGYI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-turbo",
                    "input": {"prompt": prompt},
                    "parameters": {"response_format": {"type": "json_object"}}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return json.loads(data["output"]["text"])
        except Exception as e:
            raise LLMParseError(f"Tongyi API error: {e}")


async def _call_openai(user_input: str) -> dict:
    """Call OpenAI API for parsing"""
    if not settings.OPENAI_API_KEY:
        return _mock_parse(user_input)

    prompt = PROMPT_TEMPLATE.format(user_input=user_input)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            raise LLMParseError(f"OpenAI API error: {e}")


def _mock_parse(user_input: str) -> dict:
    """Mock parsing for development without API keys"""
    return {
        "shape": "兔子",
        "glaze_color": "冷白釉",
        "size": "15-20cm",
        "style": "可爱",
        "emotion": "治愈",
        "material": "白瓷",
        "usage": "摆件"
    }
