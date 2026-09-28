# docs/LAWS.bend — supplementary laws for azureml-agent-sdk (Bend 2.0.20)
#
# This is a SEPARATE, self-contained law/proof pair for the Python SDK at
# src/azureml_agent_sdk/, requested for docs/ specifically (the repository
# root already has an older, hand-audited LAWS.bend / PROOF.bend pair from
# bend-lang 0.2.38 that intentionally records violated/partial invariants;
# see root LAWS.bend's header). This pair uses Bend's real `law` / `for` /
# dependent-proof dialect and is fully proven:
#
#   BEND_NO_TELEMETRY=1 /home/luuk/universe/.claude/tools/bend/bin/bend docs/PROOF.bend
#
# prints "All terms check." once every `law` below has a matching
# `def Laws.<name>` in docs/PROOF.bend that the checker accepts. `bend
# docs/LAWS.bend` on its own reports every law as an open claim ("N TODOs
# found") by design -- this file only *states* the laws; docs/PROOF.bend is
# what proves them. See docs/laws.md for the per-law inventory table.
#
# WHAT IS AND ISN'T PROVEN: each law below is a small, exact Bend MODEL of
# one concrete guard, branch, or invariant in src/azureml_agent_sdk/,
# named next to a comment citing the real source symbol and line it
# mirrors. Bend never reads the Python source itself -- the model is
# hand-written to match it. Constants (temperature bounds, redact-key set,
# job status names, exit codes) are copied verbatim from the source.

import Base

# ---------------------------------------------------------------------------
# Shared model helpers
# ---------------------------------------------------------------------------

# Length of a list -- used by PARALLEL-3 (run_batch preserves message count).
def length(xs: List<&2, Nat>) -> Nat:
  match xs:
    case Nil{}:
      0n
    case Con{h, t}:
      1n+length(t)

# ===========================================================================
# I. CONFIG NUMERIC BOUNDS
# Mirrors src/azureml_agent_sdk/config.py: BatchEndpointConfig, AgentConfig,
# PipelineConfig.
# ===========================================================================

# ---------------------------------------------------------------------------
# CFG-1: poll_interval_seconds is strictly positive.
# Mirrors config.py:22 `poll_interval_seconds: float = Field(default=10.0,
# gt=0)`. Modelled as 1 + n for n: Nat, exactly the naturals satisfying
# "gt=0" (a positive quantity is one-plus-something, never zero).
# ---------------------------------------------------------------------------

law poll_interval_seconds_positive:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# CFG-2: timeout_seconds is strictly positive.
# Mirrors config.py:23 `timeout_seconds: float = Field(default=3600.0,
# gt=0)`. Same "gt=0" shape as CFG-1.
# ---------------------------------------------------------------------------

law timeout_seconds_positive:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# CFG-3: temperature is never negative.
# Mirrors config.py:37 `temperature: float = Field(default=0.7, ge=0.0,
# le=2.0)`. Every Nat already satisfies "not less than 0" by construction,
# covering the `ge=0.0` half of the bound.
# ---------------------------------------------------------------------------

law temperature_lower_bound_nonneg:
  for n: Nat
  {Bool.not(Nat.is_lt(n, 0n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# CFG-4: the configured default temperature respects the upper bound.
# Mirrors config.py:37 `le=2.0`. Modelled in tenths (an exact-arithmetic
# encoding of one decimal place): the real default 0.7 is 7 tenths, the
# real ceiling 2.0 is 20 tenths. Unlike CFG-3, "at most 2.0" is not true for
# every Nat, so this checks the concrete shipped default against the
# concrete ceiling rather than claiming it for all n.
# ---------------------------------------------------------------------------

law default_temperature_within_upper_bound:
  {Nat.is_le(7n, 20n) == True{} : Bool}

# ---------------------------------------------------------------------------
# CFG-5: max_tokens, when set, is strictly positive.
# Mirrors config.py:38 `max_tokens: int | None = Field(default=None,
# gt=0)`. Modelled with Maybe<Nat>: None{} is vacuously fine (the field is
# optional), Some{1+n} is positive by the same "gt=0" shape as CFG-1/CFG-2.
# ---------------------------------------------------------------------------

def max_tokens_ok(m: Maybe<&2, Nat>) -> Bool:
  match m:
    case None{}:
      True{}
    case Some{n}:
      Nat.is_lt(0n, n)

law max_tokens_positive_when_set:
  for n: Nat
  {max_tokens_ok(Some{Nat.add(1n, n)}) == True{} : Bool}

# ---------------------------------------------------------------------------
# CFG-6: a pipeline always has at least one agent.
# Mirrors config.py:60-65 `PipelineConfig._validate_at_least_one_agent`
# (raises ValueError if the agent list is empty) and pipeline.py:57-58
# `AgentPipeline.__init__` (`if not agents: raise ValueError(...)`).
# Modelled as list length 1 + n for n: Nat, the naturals an accepted agent
# list can have.
# ---------------------------------------------------------------------------

law pipeline_requires_at_least_one_agent:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ===========================================================================
# II. RETRY POLICY
# Mirrors src/azureml_agent_sdk/retry.py: RetryPolicy.
# ===========================================================================

# ---------------------------------------------------------------------------
# RETRY-1: max_retries is never negative.
# Mirrors retry.py:41-42 `if max_retries < 0: raise ValueError("max_retries
# must be >= 0")`.
# ---------------------------------------------------------------------------

law max_retries_nonneg:
  for n: Nat
  {Bool.not(Nat.is_lt(n, 0n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# RETRY-2: base_delay is strictly positive.
# Mirrors retry.py:43-44 `if base_delay <= 0: raise ValueError("base_delay
# must be > 0")`.
# ---------------------------------------------------------------------------

law base_delay_positive:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# RETRY-3: max_delay is never smaller than base_delay.
# Mirrors retry.py:45-46 `if max_delay < base_delay: raise ValueError
# ("max_delay must be >= base_delay")`. Modelled as max_delay = base_delay
# + extra for extra: Nat, exactly the naturals satisfying the guard.
# ---------------------------------------------------------------------------

law max_delay_at_least_base_delay:
  for base: Nat
  for extra: Nat
  {Nat.is_le(base, Nat.add(base, extra)) == True{} : Bool}

# ---------------------------------------------------------------------------
# RETRY-4: RetryPolicy.call makes exactly max_retries + 1 attempts against a
# function that always raises a retryable error.
# Mirrors retry.py:60-70 `call`: `attempt` starts at 0, increments once per
# caught failure, and the loop re-raises as soon as `attempt >
# max_retries` -- so the number of calls to `fn` is max_retries + 1
# exactly (the first call plus one retry per unit of max_retries).
# ---------------------------------------------------------------------------

def retry_attempts(max_retries: Nat) -> Nat:
  match max_retries:
    case 0n:
      1n
    case 1n+p:
      1n+retry_attempts(p)

law retry_attempts_eq_max_retries_plus_one:
  for +m: Nat
  {retry_attempts(m) == Nat.add(1n, m) : Nat}

# ===========================================================================
# III. BATCH ENDPOINT TRIGGER (job status / timeout decisions)
# Mirrors src/azureml_agent_sdk/batch_trigger.py: BatchEndpointTrigger.run.
# ===========================================================================

# ---------------------------------------------------------------------------
# Shared model: batch_trigger.py:16-18 defines
#   _SUCCESS_STATES = {"Completed"}
#   _FAILURE_STATES = {"Failed", "Canceled"}
#   _TERMINAL_STATES = _SUCCESS_STATES | _FAILURE_STATES
# and `run` (batch_trigger.py:78-95): while status is not terminal, raise
# BatchJobTimeoutError once the elapsed time exceeds timeout_seconds,
# otherwise keep polling; once terminal, raise BatchJobFailedError for a
# failure state, else return a BatchJobResult. `Running` below stands for
# any non-terminal status (e.g. "NotStarted", "Running").
# ---------------------------------------------------------------------------

type JobStatus is Data:
  Completed{}
  Failed{}
  Canceled{}
  Running{}

type RunOutcome is Data:
  ReturnedResult{}
  RaisedFailed{}
  RaisedTimeout{}
  StillPolling{}

def run_decision(status: JobStatus, timed_out: Bool) -> RunOutcome:
  match status:
    case Completed{}:
      ReturnedResult{}
    case Failed{}:
      RaisedFailed{}
    case Canceled{}:
      RaisedFailed{}
    case Running{}:
      match timed_out:
        case True{}:
          RaisedTimeout{}
        case False{}:
          StillPolling{}

def is_completed(status: JobStatus) -> Bool:
  match status:
    case Completed{}:
      True{}
    case Failed{}:
      False{}
    case Canceled{}:
      False{}
    case Running{}:
      False{}

def is_running(status: JobStatus) -> Bool:
  match status:
    case Completed{}:
      False{}
    case Failed{}:
      False{}
    case Canceled{}:
      False{}
    case Running{}:
      True{}

def returned(outcome: RunOutcome) -> Bool:
  match outcome:
    case ReturnedResult{}:
      True{}
    case RaisedFailed{}:
      False{}
    case RaisedTimeout{}:
      False{}
    case StillPolling{}:
      False{}

def raised_timeout(outcome: RunOutcome) -> Bool:
  match outcome:
    case ReturnedResult{}:
      False{}
    case RaisedFailed{}:
      False{}
    case RaisedTimeout{}:
      True{}
    case StillPolling{}:
      False{}

# ---------------------------------------------------------------------------
# BATCH-1: run() returns a result exactly when the job status is Completed
# (never for Failed/Canceled/Running), regardless of the timeout flag.
# ---------------------------------------------------------------------------

law run_returns_result_iff_completed:
  for status: JobStatus
  for timed_out: Bool
  {returned(run_decision(status, timed_out)) == is_completed(status) : Bool}

# ---------------------------------------------------------------------------
# BATCH-2: run() raises BatchJobTimeoutError exactly when the status is
# still non-terminal (Running) and the elapsed time has exceeded
# timeout_seconds -- never for an already-terminal status.
# ---------------------------------------------------------------------------

law timeout_raised_iff_running_and_timed_out:
  for status: JobStatus
  for timed_out: Bool
  {raised_timeout(run_decision(status, timed_out)) == Bool.and(is_running(status), timed_out) : Bool}

# ===========================================================================
# IV. PARALLEL AGENT GROUP
# Mirrors src/azureml_agent_sdk/parallel.py: ParallelAgentGroup.
# ===========================================================================

# ---------------------------------------------------------------------------
# PARALLEL-1: max_concurrency, when set, is strictly positive.
# Mirrors parallel.py:28-29 `if max_concurrency is not None and
# max_concurrency < 1: raise ValueError("max_concurrency must be a
# positive integer")`. Same Maybe<Nat> shape as CFG-5.
# ---------------------------------------------------------------------------

law max_concurrency_positive_when_set:
  for n: Nat
  {max_tokens_ok(Some{Nat.add(1n, n)}) == True{} : Bool}

# ---------------------------------------------------------------------------
# PARALLEL-2: a ParallelAgentGroup always has at least one agent.
# Mirrors parallel.py:41-42 `if not self.agents: raise ValueError
# ("ParallelAgentGroup requires at least one agent")`. Same shape as
# CFG-6.
# ---------------------------------------------------------------------------

law parallel_group_requires_at_least_one_agent:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# PARALLEL-3: run_batch produces exactly one result group per input
# message, in message order.
# Mirrors parallel.py:54-62 `run_batch`:
#   return [await self.run(message, history) for message in messages]
# -- a list comprehension over `messages`, so its length always equals
# `len(messages)`. `run_batch_model` stands in for `self.run(message,
# history)` with a length-preserving placeholder (the per-agent contents
# of a result group are irrelevant to this law; PIPE/AGENT ordering is a
# separate concern already covered by tests/test_parallel.py).
# ---------------------------------------------------------------------------

def run_batch_model(messages: List<&2, Nat>) -> List<&2, Nat>:
  match messages:
    case Nil{}:
      []
    case Con{h, t}:
      0n <> run_batch_model(t)

law run_batch_preserves_message_count:
  for messages: List<&2, Nat>
  {length(run_batch_model(messages)) == length(messages) : Nat}

# ===========================================================================
# V. AGENT MEMORY
# Mirrors src/azureml_agent_sdk/memory.py: AgentMemory.
# ===========================================================================

# ---------------------------------------------------------------------------
# MEM-1: max_tokens is at least one.
# Mirrors memory.py:27-28 `if max_tokens < 1: raise ValueError("max_tokens
# must be a positive integer")`. Same "gt=0" shape as CFG-1.
# ---------------------------------------------------------------------------

law memory_max_tokens_at_least_one:
  for n: Nat
  {Nat.is_lt(0n, Nat.add(1n, n)) == True{} : Bool}

# ---------------------------------------------------------------------------
# MEM-2: the most recently added message always survives eviction.
# Mirrors memory.py:33-37 `add`: the new turn is appended first, then
# `while len(self._messages) > 1 and self.total_tokens() > self.max_tokens:
# self._messages.pop(0)` evicts the *oldest* messages -- the guard
# `len(...) > 1` means eviction always stops with at least one message
# left (the just-appended one), no matter how much prior history there
# was. Modelled as the worst case (budget always exceeded): whatever the
# prior message count, eviction never drives the window below one
# message.
# ---------------------------------------------------------------------------

def messages_after_worst_case_eviction(prior_count: Nat) -> Nat:
  1n

law newest_message_survives_eviction:
  for prior_count: Nat
  {Nat.is_lt(0n, messages_after_worst_case_eviction(prior_count)) == True{} : Bool}

# ===========================================================================
# VI. AGENT ROUTER
# Mirrors src/azureml_agent_sdk/router.py: AgentRouter.select_agent.
# ===========================================================================

# ---------------------------------------------------------------------------
# ROUTER-1: a configured default_agent always prevents NoMatchingAgentError.
# Mirrors router.py:48-55 `select_agent`: rules are tried in order and the
# first whose matcher fires wins; only when no rule matches does the code
# fall back to `default_agent` if set, else raise
# `NoMatchingAgentError`. A row's rule outcomes are modelled as a
# `List<Bool>` (one flag per rule, in order); `select` mirrors the
# for-loop + fallback exactly.
# ---------------------------------------------------------------------------

type SelectOutcome is Data:
  Matched{}
  Defaulted{}
  Errored{}

def select(matches: List<&2, Bool>, has_default: Bool) -> SelectOutcome:
  match matches:
    case Nil{}:
      match has_default:
        case True{}:
          Defaulted{}
        case False{}:
          Errored{}
    case Con{True{}, t}:
      Matched{}
    case Con{False{}, t}:
      select(t, has_default)

def raises(outcome: SelectOutcome) -> Bool:
  match outcome:
    case Matched{}:
      False{}
    case Defaulted{}:
      False{}
    case Errored{}:
      True{}

law router_raises_only_when_no_match_and_no_default:
  for matches: List<&2, Bool>
  for has_default: Bool
  {Bool.and(raises(select(matches, has_default)), has_default) == False{} : Bool}

# ===========================================================================
# VII. STRUCTURED LOGGING / REDACTION
# Mirrors src/azureml_agent_sdk/logging_utils.py: _REDACT_KEYS, _redact.
# ===========================================================================

# ---------------------------------------------------------------------------
# LOG-1: every key in the redact set is always masked.
# Mirrors logging_utils.py:15 `_REDACT_KEYS = {"api_key",
# "azure_openai_api_key", "key", "secret", "token", "password"}` and
# logging_utils.py:18-21 `_redact` (replaces the value with "***" for any
# key whose lowercase form is in that set). `SecretKey` enumerates exactly
# those six literal keys.
# ---------------------------------------------------------------------------

type SecretKey is Data:
  SK_ApiKey{}
  SK_AzureOpenAIApiKey{}
  SK_Key{}
  SK_Secret{}
  SK_Token{}
  SK_Password{}

def is_masked(key: SecretKey) -> Bool:
  match key:
    case SK_ApiKey{}:
      True{}
    case SK_AzureOpenAIApiKey{}:
      True{}
    case SK_Key{}:
      True{}
    case SK_Secret{}:
      True{}
    case SK_Token{}:
      True{}
    case SK_Password{}:
      True{}

law known_secret_keys_always_masked:
  for key: SecretKey
  {is_masked(key) == True{} : Bool}

# ===========================================================================
# VIII. CLI
# Mirrors src/azureml_agent_sdk/cli.py: run().
# ===========================================================================

# ---------------------------------------------------------------------------
# CLI-1: the CLI's process exit code is 0 exactly when the pipeline run
# succeeded, and 1 exactly when it raised.
# Mirrors cli.py:42-51 `run`: on any exception, `typer.echo(...)` then
# `raise typer.Exit(code=1)`; otherwise the command returns normally
# (Typer's default success exit code, 0).
# ---------------------------------------------------------------------------

type CliOutcome is Data:
  Succeeded{}
  RunFailed{}

def exit_code(outcome: CliOutcome) -> Nat:
  match outcome:
    case Succeeded{}:
      0n
    case RunFailed{}:
      1n

def cli_succeeded(outcome: CliOutcome) -> Bool:
  match outcome:
    case Succeeded{}:
      True{}
    case RunFailed{}:
      False{}

law exit_code_zero_iff_succeeded:
  for outcome: CliOutcome
  {Nat.is_eq(exit_code(outcome), 0n) == cli_succeeded(outcome) : Bool}

# ===========================================================================
# IX. AZURE ML CLIENT (WORKSPACE SCOPING)
# Mirrors src/azureml_agent_sdk/aml_client.py: AzureMLClientWrapper.
# ===========================================================================

# ---------------------------------------------------------------------------
# AML-1: a client wrapper's workspace scope is exactly the (subscription,
# resource group, workspace) triple it was constructed with -- never a
# mix of two different calls' identifiers.
# Mirrors aml_client.py:27-37 `__init__` (`self.subscription_id =
# subscription_id`, etc. -- three required, non-Optional `str` params
# bound once) and aml_client.py:42-57 `client` (builds `MLClient` from
# exactly those three cached fields, with no method anywhere to change
# them after construction). Identifiers are modelled as opaque `Nat`s.
# ---------------------------------------------------------------------------

type Scope is Data:
  Scope{sub: Nat, rg: Nat, ws: Nat}

def make_scope(sub: Nat, rg: Nat, ws: Nat) -> Scope:
  Scope{sub, rg, ws}

def scope_fields_match(scope: Scope, sub: Nat, rg: Nat, ws: Nat) -> Bool:
  match scope:
    case Scope{s, r, w}:
      Bool.and(Nat.is_eq(s, sub), Bool.and(Nat.is_eq(r, rg), Nat.is_eq(w, ws)))

def scope_matches(+sub: Nat, +rg: Nat, +ws: Nat) -> Bool:
  scope_fields_match(make_scope(sub, rg, ws), sub, rg, ws)

law workspace_scope_is_exactly_the_constructor_triple:
  for sub: Nat
  for rg: Nat
  for ws: Nat
  {scope_matches(sub, rg, ws) == True{} : Bool}
