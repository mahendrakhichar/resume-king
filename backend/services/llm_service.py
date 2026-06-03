"""LLM service abstraction layer with OpenRouter integration, task-based routing, and fallback chain."""

import asyncio
import time
from typing import Optional

from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential, retry_if_exception

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# ─── Task-to-Model Routing Table ────────────────────────────────────────
# Maps agent task types to the optimal model tier for cost/quality balance.
TASK_MODEL_MAP: dict[str, str] = {
    # Heavy tier: deep reasoning, rewrites, optimizations
    "resume_rewriting": "heavy",
    "project_optimization": "heavy",
    "recruiter_outreach": "heavy",
    "resume_parsing": "heavy",

    # Main tier: structured analysis, comparisons
    "jd_analysis": "main",
    "ats_matching": "main",
    "interview_prep": "main",

    # Fast tier: validation, small checks
    "validation": "fast",
    "quick_summary": "fast",
}

# ─── Fallback Routing Hierarchy (Direct Keys Prioritized) ───────────────
LLM_FALLBACKS: dict[str, list[str]] = {
    "heavy": [
        "nvidia/deepseek-ai/deepseek-v4-pro",
        "nvidia/meta/llama-3.3-70b-instruct",
        "openrouter/openai/gpt-oss-120b:free",
        "groq/llama-3.3-70b-versatile",
        "nvidia/nvidia/nemotron-3-super-120b-a12b",
    ],
    "main": [
        "nvidia/deepseek-ai/deepseek-v4-flash",
        "nvidia/stepfun-ai/step-3.5-flash",
        "nvidia/minimaxai/minimax-m2.7",
        "gemini/gemini-3.1-flash-lite",
    ],
    "fast": [
        "groq/llama-3.1-8b-instant",
        "gemini/gemini-2.5-flash-lite",
        "nvidia/nvidia/llama-3.1-nemotron-nano-8b-v1",
        "nvidia/nvidia/nemotron-mini-4b-instruct",
        "openrouter/moonshotai/kimi-k2.6:free",
    ]
}

# ─── Error Categories ───────────────────────────────────────────────────
ERROR_CATEGORY_RATE_LIMIT = "rate_limit"
ERROR_CATEGORY_TIMEOUT = "timeout"
ERROR_CATEGORY_NETWORK = "network"
ERROR_CATEGORY_AUTH = "auth"
ERROR_CATEGORY_UNKNOWN = "unknown"


def _categorize_error(error: Exception) -> str:
    """Classify an LLM error into a user-friendly category."""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    # Rate limit / quota / credits exhausted (includes 402 "Insufficient credits")
    if any(kw in error_str for kw in ["429", "rate", "quota", "credit", "insufficient", "402"]):
        return ERROR_CATEGORY_RATE_LIMIT
    if isinstance(error, asyncio.TimeoutError) or "timeout" in error_str:
        return ERROR_CATEGORY_TIMEOUT
    if "connect" in error_str or "network" in error_str or "dns" in error_str:
        return ERROR_CATEGORY_NETWORK
    # Auth errors - be specific to avoid matching "key" in unrelated messages
    if "401" in error_str or "403" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
        return ERROR_CATEGORY_AUTH
    return ERROR_CATEGORY_UNKNOWN


def _is_transient_error(e: Exception) -> bool:
    """Check if an exception is a rate limit or timeout error suitable for retries."""
    category = _categorize_error(e)
    return category in [ERROR_CATEGORY_RATE_LIMIT, ERROR_CATEGORY_TIMEOUT]


class LLMServiceError(Exception):
    """Structured error with category information for frontend display."""

    def __init__(self, message: str, category: str, original_error: Exception = None):
        super().__init__(message)
        self.category = category
        self.original_error = original_error


class LLMService:
    """
    Abstraction over multiple LLM providers with task-based model routing
    and automatic fallback through OpenRouter.

    Provider priority:
    1. OpenRouter (unified — routes to MAIN/FAST/FALLBACK models)
    2. Gemini (direct Google key fallback)
    3. Groq (direct Groq key fallback)
    4. OpenAI (direct OpenAI key fallback)
    """

    _instances: dict[str, BaseChatModel] = {}
    
    # Rate limit cooldown tracking (maps "provider/model" to expiry timestamp)
    _rate_limits: dict[str, float] = {}

    @classmethod
    def _is_model_rate_limited(cls, provider: str, model: str) -> bool:
        """Check if a specific provider model is cooling down from a rate limit (429/402)."""
        key = f"{provider}/{model or 'default'}"
        if key in cls._rate_limits:
            expiry = cls._rate_limits[key]
            if time.time() < expiry:
                return True
            else:
                cls._rate_limits.pop(key, None)
        return False

    @classmethod
    def _mark_model_rate_limited(cls, provider: str, model: str, duration: float = 300.0):
        """Mark a provider model as rate limited, cooling down for `duration` seconds."""
        key = f"{provider}/{model or 'default'}"
        cls._rate_limits[key] = time.time() + duration
        logger.warning(f"Model {key} is rate-limited / out of credits. Adding to cooldown list for {duration}s.")

    @classmethod
    def _resolve_model_name(cls, tier: str) -> str:
        """Resolve a tier label ('heavy', 'main', 'fast', 'fallback') to an actual model name."""
        if tier == "heavy":
            return settings.heavy_model
        elif tier == "main":
            return settings.main_model
        elif tier == "fast":
            return settings.fast_model
        elif tier == "fallback":
            return settings.fallback_model
        # If it's already a full model name, return as-is
        return tier

    @classmethod
    def get_model_for_task(cls, task_type: str) -> str:
        """
        Get the optimal model name for a given task type.

        Usage:
            model = LLMService.get_model_for_task("resume_rewriting")
            # Returns "qwen/qwen3-coder" (MAIN_MODEL)
        """
        tier = TASK_MODEL_MAP.get(task_type, "fast")  # Default to fast model
        model_name = cls._resolve_model_name(tier)
        logger.debug(f"Task '{task_type}' -> tier '{tier}' -> model '{model_name}'")
        return model_name

    @classmethod
    def get_model(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> BaseChatModel:
        """
        Get an LLM instance for the specified provider.

        Args:
            provider: "openrouter", "gemini", "groq", or "openai". Defaults to settings.
            model: Specific model name. Defaults based on provider.
            temperature: Override default temperature.
        """
        provider = provider or settings.default_llm_provider
        temp = temperature if temperature is not None else settings.default_temperature

        cache_key = f"{provider}:{model}:{temp}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        llm = cls._create_model(provider, model, temp)
        cls._instances[cache_key] = llm
        return llm

    @classmethod
    def _create_model(cls, provider: str, model: Optional[str], temperature: float) -> BaseChatModel:
        """Create a new LLM instance for the given provider."""

        if provider == "openrouter":
            from langchain_openai import ChatOpenAI

            model_name = model or settings.default_llm_model
            logger.info(f"Initializing OpenRouter model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=settings.openrouter_api_key,
                openai_api_base=settings.openrouter_base_url,
                default_headers={
                    "HTTP-Referer": settings.frontend_url,
                    "X-Title": settings.app_name,
                },
                # OpenRouter-specific: don't send org headers
                max_retries=1,
            )

        elif provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            model_name = model or "gemini-2.5-flash"
            logger.info(f"Initializing Gemini model: {model_name}")
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                google_api_key=settings.google_api_key,
                convert_system_message_to_human=True,
            )

        elif provider == "groq":
            from langchain_groq import ChatGroq

            model_name = model or "llama-3.3-70b-versatile"
            logger.info(f"Initializing Groq model: {model_name}")
            return ChatGroq(
                model=model_name,
                temperature=temperature,
                groq_api_key=settings.groq_api_key,
            )

        elif provider == "openai":
            from langchain_openai import ChatOpenAI

            model_name = model or "gpt-4o-mini"
            logger.info(f"Initializing OpenAI model: {model_name}")
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=settings.openai_api_key,
            )

        elif provider == "nvidia":
            from langchain_openai import ChatOpenAI

            model_name = model or "meta/llama-3.3-70b-instruct"
            logger.info(f"Initializing NVIDIA model: {model_name}")
            
            extra_body = {}
            if model_name in ["nvidia/nemotron-3-super-120b-a12b", "google/gemma-4-31b-it"]:
                extra_body = {"chat_template_kwargs": {"enable_thinking": True}}
                
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                openai_api_key=settings.nvidia_api_key,
                openai_api_base="https://integrate.api.nvidia.com/v1",
                max_retries=1,
                extra_body=extra_body if extra_body else None,
            )

        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    @classmethod
    async def invoke_with_fallback(
        cls,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        task_type: Optional[str] = None,
        providers: Optional[list[str]] = None,
    ) -> str:
        """
        Invoke an LLM with automatic fallback through provider chain.

        When task_type is specified, uses the task-based routing table to select
        the optimal model, then falls back through the tier chain:
        assigned_model → fast_model → fallback_model → main_model

        When providers is specified (legacy), tries each provider in order.
        """
        timeout = settings.llm_call_timeout

        # Build the model/provider chain to try
        attempts = cls._build_attempt_chain(task_type, providers)

        last_error = None
        last_category = ERROR_CATEGORY_UNKNOWN

        for provider, model_name in attempts:
            try:
                llm = cls.get_model(provider=provider, model=model_name, temperature=temperature)
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]

                # Use tenacity retry logic inside the provider loop for transient errors
                # Retries up to 4 times, with exponential backoff multiplier 1.5, starting at 8s, capped at 40s
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(4),
                    wait=wait_exponential(multiplier=1.5, min=8, max=40),
                    retry=retry_if_exception(_is_transient_error),
                    reraise=True,
                ):
                    with attempt:
                        # Enforce per-call timeout
                        response = await asyncio.wait_for(
                            llm.ainvoke(messages),
                            timeout=timeout,
                        )

                content = response.content
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, str):
                            text_parts.append(part)
                        elif isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                        elif hasattr(part, "text"):
                            text_parts.append(getattr(part, "text"))
                        else:
                            text_parts.append(str(part))
                    content = "".join(text_parts)
                else:
                    content = str(content)

                logger.info(
                    f"LLM response from {provider}/{model_name} "
                    f"({len(content)} chars)"
                )
                return content

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(
                    f"LLM call to {provider}/{model_name} timed out after {timeout}s"
                )
                last_category = ERROR_CATEGORY_TIMEOUT
                logger.warning(f"LLM call timed out: {provider}/{model_name} after {timeout}s")
                continue

            except Exception as e:
                last_error = e
                last_category = _categorize_error(e)
                logger.warning(
                    f"LLM provider {provider}/{model_name} failed "
                    f"[{last_category}]: {e}"
                )
                if last_category == ERROR_CATEGORY_RATE_LIMIT:
                    cls._mark_model_rate_limited(provider, model_name)
                continue

        raise LLMServiceError(
            f"All LLM providers failed. Last error: {last_error}",
            category=last_category,
            original_error=last_error,
        )

    @classmethod
    def _build_attempt_chain(
        cls,
        task_type: Optional[str],
        providers: Optional[list[str]],
    ) -> list[tuple[str, str]]:
        """
        Build an ordered list of (provider, model) tuples to attempt.
        Uses LLM_FALLBACKS priority lists for 'heavy', 'main', and 'fast' model tiers.
        Skips models that are currently marked as rate-limited.
        """
        attempts: list[tuple[str, str]] = []
        seen_keys = set()

        if providers:
            # Explicit providers list specified (legacy / fallback)
            for provider in providers:
                if provider == "gemini" and settings.google_api_key:
                    if not cls._is_model_rate_limited("gemini", "gemini-2.5-flash"):
                        attempts.append(("gemini", "gemini-2.5-flash"))
                        seen_keys.add("gemini/gemini-2.5-flash")
                elif provider == "groq" and settings.groq_api_key:
                    model = "llama-3.3-70b-versatile" if task_type in ["resume_rewriting", "project_optimization", "recruiter_outreach", "heavy_reasoning", "ats_matching", "interview_prep"] else "llama-3.1-8b-instant"
                    if not cls._is_model_rate_limited("groq", model):
                        attempts.append(("groq", model))
                        seen_keys.add(f"groq/{model}")
                elif provider == "openrouter" and settings.openrouter_api_key:
                    model = cls.get_model_for_task(task_type) if task_type else settings.default_llm_model
                    if not cls._is_model_rate_limited("openrouter", model):
                        attempts.append(("openrouter", model))
                        seen_keys.add(f"openrouter/{model}")
                elif provider == "openai" and settings.openai_api_key:
                    if not cls._is_model_rate_limited("openai", "gpt-4o-mini"):
                        attempts.append(("openai", "gpt-4o-mini"))
                        seen_keys.add("openai/gpt-4o-mini")
            return attempts

        # Look up model tier ('heavy', 'main', or 'fast') based on task type
        tier = "fast"
        if task_type:
            tier = TASK_MODEL_MAP.get(task_type, "fast")
            if tier == "fallback":
                tier = "fast"

        # 0. Add primary model from settings first
        primary_model_str = None
        if tier == "heavy" and hasattr(settings, "heavy_model"):
            primary_model_str = settings.heavy_model
        elif tier == "main" and hasattr(settings, "main_model"):
            primary_model_str = settings.main_model
        elif tier == "fast" and hasattr(settings, "fast_model"):
            primary_model_str = settings.fast_model

        if primary_model_str:
            parts = primary_model_str.split("/", 1)
            if len(parts) == 2:
                parsed_provider, model_name = parts
                provider = "gemini" if parsed_provider == "google" else parsed_provider
                # Ensure we only try direct Google/Groq/OpenAPI/NVIDIA models if they don't have :free tags, or route via openrouter
                is_valid = True
                if provider == "nvidia" and not settings.nvidia_api_key:
                    is_valid = False
                elif model_name.endswith(":free") and provider != "openrouter":
                    is_valid = False
                if is_valid and not cls._is_model_rate_limited(provider, model_name):
                    attempts.append((provider, model_name))
                    seen_keys.add(f"{provider}/{model_name}")

        # Get fallback models list for the tier
        fallback_models = LLM_FALLBACKS.get(tier, LLM_FALLBACKS["fast"])

        # 1. Prioritize direct fallbacks in order (Groq / Gemini / OpenAI)
        for model_str in fallback_models:
            parts = model_str.split("/", 1)
            if len(parts) != 2:
                continue
            parsed_provider, model_name = parts
            
            # Normalize provider name
            provider = parsed_provider
            if provider == "google":
                provider = "gemini"

            # Check if key is available in settings and if it can be called directly
            has_key = False
            if provider == "gemini" and settings.google_api_key:
                # Direct Gemini API only supports standard gemini models (no OpenRouter :free tags)
                if model_name.startswith("gemini-") and not model_name.endswith(":free"):
                    has_key = True
            elif provider == "groq" and settings.groq_api_key:
                # Direct Groq key supports standard llama models (no OpenRouter :free tags)
                if "llama" in model_name and not model_name.endswith(":free"):
                    has_key = True
            elif provider == "openai" and settings.openai_api_key:
                if not model_name.endswith(":free"):
                    has_key = True
            elif provider == "nvidia" and settings.nvidia_api_key:
                if not model_name.endswith(":free"):
                    has_key = True

            if has_key:
                # Check if model is rate limited
                if not cls._is_model_rate_limited(provider, model_name):
                    attempts.append((provider, model_name))
                    seen_keys.add(f"{provider}/{model_name}")

        # 2. Append OpenRouter as a final safeguard if configured
        if settings.openrouter_api_key:
            # Add the fallback models themselves via OpenRouter if not already added directly
            for model_str in fallback_models:
                key = f"openrouter/{model_str}"
                if key not in seen_keys:
                    if not cls._is_model_rate_limited("openrouter", model_str):
                        attempts.append(("openrouter", model_str))
                        seen_keys.add(key)

            # Also add predefined tier defaults from settings
            openrouter_defaults = []
            if tier == "heavy" and hasattr(settings, "heavy_model"):
                openrouter_defaults.append(settings.heavy_model)
            openrouter_defaults.extend([
                settings.main_model,
                settings.fast_model,
                settings.fallback_model,
            ])

            for model_name in openrouter_defaults:
                key = f"openrouter/{model_name}"
                if key not in seen_keys:
                    if not cls._is_model_rate_limited("openrouter", model_name):
                        attempts.append(("openrouter", model_name))
                        seen_keys.add(key)

        # 3. If everything is rate limited, try them anyway as a last resort
        if not attempts:
            logger.warning("All configured LLM models are currently rate-limited. Trying them anyway as a last resort.")
            for model_str in fallback_models:
                parts = model_str.split("/", 1)
                if len(parts) == 2:
                    parsed_provider, model_name = parts
                    provider = "gemini" if parsed_provider == "google" else parsed_provider
                    
                    # Direct check
                    if provider == "gemini" and settings.google_api_key and model_name.startswith("gemini-"):
                        attempts.append((provider, model_name))
                    elif provider == "groq" and settings.groq_api_key and "llama" in model_name:
                        attempts.append((provider, model_name))
                    elif provider == "openai" and settings.openai_api_key:
                        attempts.append((provider, model_name))
                    elif provider == "nvidia" and settings.nvidia_api_key:
                        attempts.append((provider, model_name))

            if settings.openrouter_api_key:
                for model_str in fallback_models:
                    attempts.append(("openrouter", model_str))

        if not attempts:
            raise LLMServiceError(
                "No LLM providers configured. Set provider keys in .env",
                category=ERROR_CATEGORY_AUTH,
            )

        return attempts

    @classmethod
    def clear_cache(cls):
        """Clear cached LLM instances (useful for testing)."""
        cls._instances.clear()


# Convenience singleton
llm_service = LLMService()
