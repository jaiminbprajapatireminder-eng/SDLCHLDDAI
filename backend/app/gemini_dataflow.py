"""
Google Gemini Dataflow Pipeline

Multi-stage processing pipeline that improves response precision by:
1. Analyzing the user question and HLDD context
2. Reasoning step-by-step about the best response
3. Generating a structured, precise final response

Each stage uses tuned generation config for its purpose.
"""

import json
import os
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

MODEL_FAST = "gemini-2.0-flash"
MODEL_PRECISE = "gemini-2.5-flash"

STAGE_CONFIGS = {
    "analyze": {
        "temperature": 0.1,
        "top_p": 0.95,
        "top_k": 20,
        "max_output_tokens": 1024,
    },
    "reason": {
        "temperature": 0.2,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    "generate": {
        "temperature": 0.15,
        "top_p": 0.90,
        "top_k": 30,
        "max_output_tokens": 4096,
    },
}

SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

SYSTEM_INSTRUCTION_GENERATE = (
    "You are a precise delivery planning assistant for HLDD (High Level Design Document) "
    "analysis and software project planning.\n\n"
    "Your responses must be:\n"
    "- Grounded in the provided HLDD context — never invent tech stack details\n"
    "- Structured with clear sections (Summary, Details, Recommendation, Next Steps)\n"
    "- Practical and actionable with specific recommendations\n"
    "- Specific to the project's technology stack and requirements\n"
    "- Concise but comprehensive\n\n"
    "When the user asks about:\n"
    "- **Costs/pricing**: Include specific numbers, instance types, and provider comparisons\n"
    "- **Alternatives**: Compare 2-3 options with pros, cons, and use cases\n"
    "- **Architecture**: Reference the specific tech stack and suggest improvements\n"
    "- **Planning**: Provide actionable next steps with priorities and timelines\n"
    "- **General**: Summarize key project aspects and offer relevant guidance"
)


def _fetch_gemini(
    model: str,
    system_instruction: str,
    user_prompt: str,
    stage: str = "generate",
) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    config = STAGE_CONFIGS.get(stage, STAGE_CONFIGS["generate"])

    body = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generation_config": {
            "temperature": config["temperature"],
            "top_p": config["top_p"],
            "top_k": config["top_k"],
            "max_output_tokens": config["max_output_tokens"],
        },
        "safety_settings": SAFETY_SETTINGS,
    }

    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    request = Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _extract_text(response: Dict[str, Any]) -> str:
    try:
        return response["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Invalid Gemini response format: {e}")


def _build_analysis_prompt(context: str, prompt: str, priority: str) -> str:
    return (
        f"Analyze this HLDD project context and user question. Be concise.\n\n"
        f"HLDD Context:\n{context}\n\n"
        f"User Question: {prompt}\n"
        f"Priority: {priority}\n\n"
        "Respond in exactly this format:\n"
        "TOPIC: [cost|alternatives|architecture|planning|general|specific]\n"
        "SCOPE: [project|general]\n"
        "KEY_TERMS: [comma-separated list]\n"
        "INTENT: [1-2 sentences about what the user really needs]\n"
        "RELEVANT_CONTEXT: [specific HLDD details relevant to this question]"
    )


def _build_reasoning_prompt(analysis: str, context: str, prompt: str, priority: str) -> str:
    return (
        f"Based on the analysis below, reason step by step.\n\n"
        f"Analysis:\n{analysis}\n\n"
        f"HLDD Context:\n{context}\n\n"
        f"User Question: {prompt}\n"
        f"Priority: {priority}\n\n"
        "Walk through your reasoning:\n"
        "1. What exactly is being asked?\n"
        "2. What from the HLDD is relevant?\n"
        "3. What are the possible options/approaches?\n"
        f"4. What tradeoffs exist given the selected priority ({priority})?\n"
        "5. What is the best recommendation?\n\n"
        "Then provide your final reasoning summary."
    )


def _build_generation_prompt(
    reasoning: str,
    context: str,
    prompt: str,
    priority: str,
) -> str:
    return (
        f"Using the reasoning below, generate the final structured response.\n\n"
        f"Reasoning:\n{reasoning}\n\n"
        f"HLDD Context:\n{context}\n\n"
        f"User Question: {prompt}\n"
        f"Priority: {priority}\n\n"
        "Generate a response with these sections:\n"
        "- **Summary**: Direct answer in 2-3 sentences\n"
        "- **Details**: Specific information, options, comparisons grounded in the HLDD\n"
        f"- **Recommendation**: Best option given the {priority} priority\n"
        "- **Next Steps**: Actionable items"
    )


def call_gemini_dataflow(
    context: str,
    prompt: str,
    priority: str = "balanced",
) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Run the Gemini dataflow pipeline for precise responses.

    Pipeline stages:
      1. Analyze — classify question topic, scope, intent against HLDD context
      2. Reason  — step-by-step reasoning about the best answer
      3. Generate — produce structured final response with tuned precision config

    Falls back to a single-stage call if the multi-stage pipeline fails.
    """
    llm = {
        "provider": "Google Gemini",
        "model": f"{MODEL_FAST} → {MODEL_PRECISE}",
        "reason": (
            "Gemini Dataflow pipeline: analysis → reasoning → generation "
            "for maximum output precision."
        ),
    }

    try:
        analysis_resp = _fetch_gemini(
            MODEL_FAST,
            "You analyze software project questions against HLDD context. Be concise.",
            _build_analysis_prompt(context, prompt, priority),
            stage="analyze",
        )
        analysis = _extract_text(analysis_resp)

        reasoning_resp = _fetch_gemini(
            MODEL_FAST,
            "You reason step-by-step about software delivery decisions.",
            _build_reasoning_prompt(analysis, context, prompt, priority),
            stage="reason",
        )
        reasoning = _extract_text(reasoning_resp)

        final_resp = _fetch_gemini(
            MODEL_PRECISE,
            SYSTEM_INSTRUCTION_GENERATE,
            _build_generation_prompt(reasoning, context, prompt, priority),
            stage="generate",
        )
        response_text = _extract_text(final_resp)

        return response_text, llm

    except (HTTPError, URLError, KeyError, ValueError, json.JSONDecodeError):
        try:
            fallback = _fetch_gemini(
                MODEL_PRECISE,
                SYSTEM_INSTRUCTION_GENERATE,
                (
                    f"HLDD Context:\n{context}\n\n"
                    f"Priority: {priority}\n\n"
                    f"Question: {prompt}"
                ),
            )
            return _extract_text(fallback), llm
        except (HTTPError, URLError, KeyError, ValueError, json.JSONDecodeError):
            return None, llm
