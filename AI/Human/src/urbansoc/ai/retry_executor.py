"""AI Request Retry Executor implementing strict 4-Attempt Retry Policy with 3-Second Interval.

Conforms to SOC-Grade Reliability:
- Maximum 4 retry attempts upon transient failure.
- 3.0 second fixed backoff interval between attempts.
- Explicit audit logging of each attempt and transparent fallback.
"""

import logging
import time
from typing import Any, Callable, List, Optional, Tuple, Type

logger = logging.getLogger("urbansoc.ai.retry_executor")


class AIRetryExhaustedError(Exception):
    """Raised when all retry attempts to the AI Inference Engine are exhausted."""
    def __init__(self, message: str, attempts: int, last_error: Exception) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def execute_ai_with_retry(
    operation: Callable[..., Any],
    *args: Any,
    max_retries: int = 4,
    retry_delay_seconds: float = 3.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    fallback_factory: Optional[Callable[[], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Execute an AI inference operation with up to `max_retries` attempts spaced by `retry_delay_seconds`.

    Parameters:
        operation: Callable to invoke.
        max_retries: Maximum number of attempts (default: 4).
        retry_delay_seconds: Delay in seconds between attempts (default: 3.0s).
        retry_exceptions: Tuple of exceptions triggering retry.
        on_retry: Optional callback invoked on each retry: (attempt, error, delay).
        fallback_factory: Optional callable generating fallback output if all retries fail.

    Returns:
        Result from successful operation or fallback_factory().

    Raises:
        AIRetryExhaustedError: If all retries fail and no fallback_factory is provided.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            return operation(*args, **kwargs)
        except retry_exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(
                    "⚠️ [AI RETRY %d/%d] Inference request failed: %s. Re-attempting in %.1fs...",
                    attempt,
                    max_retries,
                    e,
                    retry_delay_seconds,
                )
                if on_retry:
                    try:
                        on_retry(attempt, e, retry_delay_seconds)
                    except Exception as cb_err:
                        logger.debug("on_retry callback error: %s", cb_err)

                if retry_delay_seconds > 0:
                    time.sleep(retry_delay_seconds)
            else:
                logger.error(
                    "🚨 [AI RETRIES EXHAUSTED] Reached maximum %d attempts. Last error: %s",
                    max_retries,
                    e,
                )

    if fallback_factory is not None:
        logger.info("Executing safe local fallback engine following retry exhaustion.")
        return fallback_factory()

    raise AIRetryExhaustedError(
        f"AI Inference failed after {max_retries} attempts: {last_exception}",
        attempts=max_retries,
        last_error=last_exception,  # type: ignore
    )
