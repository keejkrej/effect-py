"""effect — a Python port of Effect-TS."""

from effect import cause, context, data, effect, either, exit, layer, option, ref, runtime, scope
from effect.cause import Cause
from effect.context import Context, GenericTag, Tag, empty, make, merge
from effect.data import TaggedError, tagged_class, tagged_error
from effect.effect import (
    AsyncFiberException,
    Effect,
    async_,
    catch_all,
    catch_if,
    catch_tag,
    fail,
    flat_map,
    gen,
    map,
    match_effect,
    on_exit,
    pipe,
    provide,
    provide_context,
    provide_service,
    run_async,
    run_async_exit,
    run_sync,
    run_sync_exit,
    succeed,
    sync,
    tag,
    tap,
    try_,
)
from effect.effect import (
    context as context_effect,
)
from effect.exit import Exit
from effect.layer import Layer, build, provide_to
from effect.layer import merge as merge_layers
from effect.layer import succeed as layer_succeed
from effect.option import Option
from effect.ref import Ref
from effect.ref import make as ref_make
from effect.runtime import Runtime, default_runtime
from effect.runtime import run_async as runtime_run_async
from effect.scope import (
    CloseableScope,
    Scope,
    acquire_release,
    add_finalizer,
    scoped,
    scoped_with,
)
from effect.scope import make as scope_make

__all__ = [
    "AsyncFiberException",
    "CloseableScope",
    "Scope",
    "acquire_release",
    "add_finalizer",
    "Cause",
    "Context",
    "Effect",
    "Exit",
    "GenericTag",
    "Layer",
    "Option",
    "Ref",
    "Runtime",
    "Tag",
    "TaggedError",
    "async_",
    "build",
    "catch_all",
    "catch_if",
    "catch_tag",
    "cause",
    "context",
    "context_effect",
    "data",
    "default_runtime",
    "either",
    "effect",
    "empty",
    "exit",
    "fail",
    "flat_map",
    "gen",
    "layer",
    "layer_succeed",
    "make",
    "map",
    "match_effect",
    "merge",
    "merge_layers",
    "on_exit",
    "option",
    "pipe",
    "provide",
    "provide_context",
    "provide_service",
    "provide_to",
    "ref",
    "ref_make",
    "run_async",
    "run_async_exit",
    "runtime",
    "runtime_run_async",
    "run_sync",
    "run_sync_exit",
    "scope",
    "scope_make",
    "scoped",
    "scoped_with",
    "succeed",
    "sync",
    "tag",
    "tap",
    "tagged_class",
    "tagged_error",
    "try_",
]
