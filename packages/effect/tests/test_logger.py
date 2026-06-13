from __future__ import annotations

import pytest

import effect as Effect
from effect import GenericTag, pipe, run_async
from effect.logger import LoggerTag, MockLogger, log_error, log_info


@pytest.mark.asyncio
async def test_structured_logging() -> None:
    logger = MockLogger()
    RequestId = GenericTag("request_id")

    @Effect.gen
    def program():
        yield log_info("handling request", extra="data")
        yield log_error("something failed")
        return None

    ctx_program = pipe(
        program(),
        Effect.provide_service(LoggerTag, logger),
        Effect.provide_service(RequestId, "req-123"),
    )
    await run_async(ctx_program)

    assert len(logger.logs) == 2
    assert logger.logs[0] == (
        "info",
        "handling request",
        {"request_id": "req-123", "extra": "data"},
    )
    assert logger.logs[1] == ("error", "something failed", {"request_id": "req-123"})
