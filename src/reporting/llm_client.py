"""LLM API 客户端封装。使用 litellm 调用 DeepSeek API。

模型策略：
  - deepseek-v4-flash：轻量任务（异常备注标准化、关键词分类）
  - deepseek-v4-pro：复杂任务（IE 周报、CAPA、5Why 生成）
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.config.settings import settings


def call_llm(messages: list[dict], temperature: float = 0.2, model_tier: str | None = None) -> str:
    """调用 LLM API。

    Args:
        messages: OpenAI 格式的消息列表 [{"role": "system/user", "content": "..."}]
        temperature: 生成温度
        model_tier: 模型级别 ("flash" | "pro" | None)
            - flash: 使用 deepseek-v4-flash（轻量任务）
            - pro: 使用 deepseek-v4-pro（复杂任务）
            - None: 使用 .env 中 LLM_MODEL 指定的默认模型

    Returns:
        LLM 响应文本
    """
    from litellm import completion

    model = _resolve_model(model_tier)

    response = completion(
        model=model,
        api_key=settings.llm.api_key,
        api_base=settings.llm.base_url,
        messages=messages,
        temperature=temperature,
    )

    content = response["choices"][0]["message"]["content"]

    # 保存日志
    _save_llm_log(messages, content, model)

    return content


def call_llm_flash(messages: list[dict], temperature: float = 0.2) -> str:
    """使用 deepseek-v4-flash 调用 LLM（适合轻量任务）。"""
    return call_llm(messages, temperature=temperature, model_tier="flash")


def call_llm_pro(messages: list[dict], temperature: float = 0.2) -> str:
    """使用 deepseek-v4-pro 调用 LLM（适合复杂任务）。"""
    return call_llm(messages, temperature=temperature, model_tier="pro")


def _resolve_model(model_tier: str | None) -> str:
    """根据 model_tier 解析实际模型名称。"""
    if model_tier == "flash":
        return settings.llm.model_flash
    elif model_tier == "pro":
        return settings.llm.model_pro
    return settings.llm.model


def _save_llm_log(messages: list[dict], response: str, model: str):
    """保存 LLM 输入输出日志。"""
    log_dir = settings.llm_logs_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_file = log_dir / f"llm_log_{timestamp}.json"

    log_data = {
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "messages": messages,
        "response": response,
    }

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)


def check_llm_available(model_tier: str | None = None) -> bool:
    """检查 LLM API 是否可用。"""
    if not settings.llm.api_key:
        return False
    try:
        from litellm import completion
        model = _resolve_model(model_tier)
        completion(
            model=model,
            api_key=settings.llm.api_key,
            api_base=settings.llm.base_url,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=5,
        )
        return True
    except Exception:
        return False
