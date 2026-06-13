from __future__ import annotations

from dataclasses import dataclass

import pytest

import effect as Effect
from effect import pipe, run_sync, run_sync_exit, succeed
from effect.cause import die, interrupt, is_failure, is_interrupted, parallel, pretty, sequential
from effect.cause import fail as cause_fail
from effect.data import TaggedError, tagged_error
from effect.either import from_nullable, is_left, is_right, left, right
from effect.exit import Failure, Success, is_success
from effect.option import get_or_else, is_none, is_some, none, some


class TestOption:
    def test_some_and_none(self) -> None:
        assert is_some(some(1))
        assert is_none(none())
        assert get_or_else(some(42), 0) == 42
        assert get_or_else(none(), 0) == 0


class TestEither:
    def test_constructors(self) -> None:
        assert is_right(right(1))
        assert is_left(left("err"))
        assert from_nullable(1, "missing") == right(1)
        assert from_nullable(None, "missing") == left("missing")


class TestData:
    def test_tagged_error(self) -> None:
        @dataclass
        class NotFound(TaggedError):
            _tag = "NotFound"
            message: str

        err = NotFound(message="missing")
        assert err._tag == "NotFound"
        assert "missing" in str(err)

    def test_tagged_error_factory(self) -> None:
        NotFound = tagged_error("NotFound")
        err = NotFound()
        assert err._tag == "NotFound"


class TestCause:
    def test_fail_and_sequential(self) -> None:
        c = sequential(cause_fail("a"), cause_fail("b"))
        assert is_failure(cause_fail("x"))
        assert "Fail('a')" in pretty(c)
        assert is_interrupted(interrupt(1))

    def test_parallel(self) -> None:
        c = parallel(cause_fail(1), die(ValueError("boom")))
        assert is_failure(c)


class TestExit:
    def test_success_and_failure(self) -> None:
        ok = Success(value=1)
        bad = Failure(cause=cause_fail("err"))
        assert is_success(ok)
        assert isinstance(bad, Failure)
        assert ok.value == 1


class TestEffectSync:
    def test_succeed(self) -> None:
        assert run_sync(succeed(42)) == 42

    def test_fail(self) -> None:
        @dataclass
        class Boom(TaggedError):
            _tag = "Boom"

        err = Boom()
        with pytest.raises(Boom):
            run_sync(Effect.fail(err))

    def test_map_and_flat_map(self) -> None:
        program = pipe(
            succeed(2),
            Effect.map(lambda n: n + 1),
            Effect.flat_map(lambda n: succeed(n * 3)),
        )
        assert run_sync(program) == 9

    def test_sync_and_try(self) -> None:
        assert run_sync(Effect.sync(lambda: 7)) == 7
        result = run_sync_exit(Effect.try_(lambda: 1 // 0))
        assert isinstance(result, Failure)

    def test_gen(self) -> None:
        @Effect.gen
        def program():
            x = yield succeed(1)
            y = yield succeed(2)
            return x + y

        assert run_sync(program()) == 3

    def test_catch_tag(self) -> None:
        @dataclass
        class NotFound(TaggedError):
            _tag = "NotFound"

        @Effect.gen
        def program():
            result = yield pipe(
                Effect.fail(NotFound()),
                Effect.catch_tag("NotFound", lambda _: succeed("recovered")),
            )
            return result

        assert run_sync(program()) == "recovered"

    def test_run_sync_exit(self) -> None:
        result = run_sync_exit(succeed("ok"))
        assert isinstance(result, Success)
        assert result.value == "ok"
