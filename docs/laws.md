# laws.md — inventory of `docs/LAWS.bend` / `docs/PROOF.bend`

This documents every law in `docs/LAWS.bend` (Bend 2.0.20 — the real `law` /
`for` / dependent-proof dialect). It is a separate, self-contained pair from
the repository's root `LAWS.bend` / `PROOF.bend` (an older, hand-audited
bend-lang 0.2.38 ledger that intentionally records several violated/partial
invariants). This `docs/` pair is fully proven:

```bash
BEND_NO_TELEMETRY=1 /home/luuk/universe/.claude/tools/bend/bin/bend docs/PROOF.bend
```

Output: `All terms check.`

**Law count**: 21, across 9 domains: config numeric bounds, retry policy,
batch endpoint job status/timeout, parallel agent group, agent memory,
agent router, structured logging/redaction, CLI exit codes, and Azure ML
client workspace scoping.

**How these are proven.** Each law is a universally quantified statement
(the `for x: T` binders) over one exact Bend model of a real guard, branch,
or invariant in `src/azureml_agent_sdk/`. `docs/PROOF.bend` discharges each
one with a total Bend function — a closed computation (the statement
reduces to `True == True` regardless of the quantified variables' shape), an
exhaustive case split over a small finite `Data` type, or a structural
induction. `bend docs/LAWS.bend` on its own reports every law as an open
claim (`21 TODOs found`) by design — that file only *states* the laws;
`docs/PROOF.bend` is what proves them.

**What is and isn't proven.** Bend never reads the Python source itself —
each law is about a small Bend model of one piece of real logic, named next
to a comment citing the source symbol it mirrors. Numeric constants
(temperature bounds, the redact-key set, job status names, exit codes) are
copied verbatim from the source; a law becoming stale (source changed
without updating the model) is a documentation-drift risk this file does
not, by itself, detect.

| Law | Domain | Type / constraint | Source symbol | Witness / proof |
|---|---|---|---|---|
| `poll_interval_seconds_positive` | Config | `poll_interval_seconds > 0` for all `n` | `config.py:22` `BatchEndpointConfig.poll_interval_seconds` (`Field(default=10.0, gt=0)`) | Closed reduction: `1+n` is always `> 0` |
| `timeout_seconds_positive` | Config | `timeout_seconds > 0` for all `n` | `config.py:23` `BatchEndpointConfig.timeout_seconds` (`Field(default=3600.0, gt=0)`) | Closed reduction: `1+n` is always `> 0` |
| `temperature_lower_bound_nonneg` | Config | `temperature >= 0` for all `n` | `config.py:37` `AgentConfig.temperature` (`Field(default=0.7, ge=0.0, le=2.0)`) | Case split on `n`; every `Nat` is `>= 0` |
| `default_temperature_within_upper_bound` | Config | shipped default `<= 2.0` | `config.py:37` default `0.7`, ceiling `2.0` (modelled as tenths: `7 <= 20`) | Closed literal comparison |
| `max_tokens_positive_when_set` | Config | `max_tokens > 0` when set, for all `n` | `config.py:38` `AgentConfig.max_tokens` (`Field(default=None, gt=0)`) | `Maybe<Nat>`; `Some{1+n}` closed `> 0` |
| `pipeline_requires_at_least_one_agent` | Config | `len(agents) >= 1` for all `n` | `config.py:60-65` `PipelineConfig._validate_at_least_one_agent`; `pipeline.py:57-58` `AgentPipeline.__init__` | Closed reduction: list length `1+n > 0` |
| `max_retries_nonneg` | Retry | `max_retries >= 0` for all `n` | `retry.py:41-42` `RetryPolicy.__init__` (`if max_retries < 0: raise`) | Case split on `n` |
| `base_delay_positive` | Retry | `base_delay > 0` for all `n` | `retry.py:43-44` `RetryPolicy.__init__` (`if base_delay <= 0: raise`) | Closed reduction: `1+n > 0` |
| `max_delay_at_least_base_delay` | Retry | `max_delay >= base_delay` for all `base, extra` | `retry.py:45-46` `RetryPolicy.__init__` (`if max_delay < base_delay: raise`) | Induction on `base` (`max_delay` modelled as `base + extra`) |
| `retry_attempts_eq_max_retries_plus_one` | Retry | attempts made `== max_retries + 1` | `retry.py:60-70` `RetryPolicy.call` (`attempt` loop, re-raises once `attempt > max_retries`) | Structural induction on `max_retries` |
| `run_returns_result_iff_completed` | Batch trigger | returns a result **iff** status is `Completed` | `batch_trigger.py:16-18,78-95` `_SUCCESS_STATES`/`_FAILURE_STATES`/`BatchEndpointTrigger.run` | Exhaustive case split (4 `JobStatus` × 2 `Bool`) |
| `timeout_raised_iff_running_and_timed_out` | Batch trigger | timeout raised **iff** status non-terminal and elapsed `> timeout_seconds` | `batch_trigger.py:83-88` polling loop | Exhaustive case split (4 `JobStatus` × 2 `Bool`) |
| `max_concurrency_positive_when_set` | Parallel | `max_concurrency > 0` when set, for all `n` | `parallel.py:28-29` `ParallelAgentGroup.__init__` (`if max_concurrency is not None and max_concurrency < 1: raise`) | `Maybe<Nat>`; `Some{1+n}` closed `> 0` |
| `parallel_group_requires_at_least_one_agent` | Parallel | `len(agents) >= 1` for all `n` | `parallel.py:41-42` `ParallelAgentGroup.run` (`if not self.agents: raise`) | Closed reduction: `1+n > 0` |
| `run_batch_preserves_message_count` | Parallel | `len(run_batch(messages)) == len(messages)` | `parallel.py:54-62` `ParallelAgentGroup.run_batch` (list comprehension over `messages`) | Structural induction on the message list |
| `memory_max_tokens_at_least_one` | Memory | `max_tokens >= 1` for all `n` | `memory.py:27-28` `AgentMemory.__init__` (`if max_tokens < 1: raise`) | Closed reduction: `1+n > 0` |
| `newest_message_survives_eviction` | Memory | post-eviction window is never empty, for all `prior_count` | `memory.py:33-37` `AgentMemory.add` (`while len(...) > 1 and ...: pop(0)`) | Closed: worst-case eviction always leaves exactly `1` |
| `router_raises_only_when_no_match_and_no_default` | Router | `raises => not has_default`, for all rule-match lists and `has_default` | `router.py:48-55` `AgentRouter.select_agent` | Structural induction on the rule-match list |
| `known_secret_keys_always_masked` | Logging | every key in the redact set is masked, for all 6 keys | `logging_utils.py:15,18-21` `_REDACT_KEYS`, `_redact` | Exhaustive case split (6 `SecretKey` constructors) |
| `exit_code_zero_iff_succeeded` | CLI | exit code `== 0` **iff** the run succeeded, for both outcomes | `cli.py:42-51` `run` (`raise typer.Exit(code=1)` on exception) | Exhaustive case split (2 `CliOutcome` constructors) |
| `workspace_scope_is_exactly_the_constructor_triple` | AML client | scope `== (subscription, resource_group, workspace)` for all `sub, rg, ws` | `aml_client.py:27-37,42-57` `AzureMLClientWrapper.__init__`/`.client` | `Nat` reflexivity (`nat_eq_refl`) composed over the 3-field record |
