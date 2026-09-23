// =============================================================================
// LAWS.bend -- formal laws for azureml-agent-sdk
// Project : azureml-agent-sdk (Azure ML batch endpoint -> Azure OpenAI agent pipelines)
// Date    : 2026-09-23
// Laws    : 32 (8 domains x 4)
// Summary : (proven, hold, partial, violated, total) = (2, 7, 10, 13, 32)
//
// HOW TO READ THIS FILE
//   Bend has no dependent-type proof checker. A `type Proof_<D>_<N>` encodes the
//   evidence a law needs and a `proof_<d>_<n>` term is a witness whose fields are
//   computed by executable specs in this file (run: `bend run-rs LAWS.bend`).
//   Comment syntax: this file uses `//` comments as the LAWS format requires; stock Bend
//   only accepts `#`. To compile: sed 's#^\(\s*\)//#\1\##' LAWS.bend > /tmp/l.bend && bend run-rs /tmp/l.bend
//   (verified 2026-09-23: reduces to (1, (3, 4))).
//   STATUS meaning:
//     proven   - witness built from a spec that models the source, plus a written
//                structural argument tied to source lines
//     hold     - witness/annotation backed by source inspection + existing tests
//     partial  - law holds only for part of its scope (see MANIFEST)
//     violated - the source does not enforce the law; no witness can be built, so the
//                proof term is intentionally omitted and a PROOF annotation names the
//                evidence a fix must supply
//   Domains with no SDK feature (COMP, MODEL) are marked violated rather than
//   vacuously true: the law is required, the code does not provide it.
// =============================================================================

// ---- Shared executable specs -------------------------------------------------

// Number of activations that actually build a client: lazy + cached (agent.py:41-48).
def activate_count(built, remaining):
  if remaining == 0:
    return built
  else:
    return activate_count(1, remaining - 1)

// A pipeline is a cons-list of agents; there is no constructor that can point back.
type Chain:
  Nil
  Link { next }

def build_chain(n):
  if n == 0:
    return Chain/Nil
  else:
    return Chain/Link { next: build_chain(n - 1) }

// Length of a chain terminates by structural recursion on Chain (no cycles possible).
def chain_len_of(c):
  match c:
    case Chain/Nil:
      return 0
    case Chain/Link:
      return 1 + chain_len_of(c.next)

def chain_len(n):
  return chain_len_of(build_chain(n))

// Calls made by RetryPolicy.call for a function that always fails (retry.py:62-70):
// attempt goes 1..max_retries+1; the call at attempt > max_retries re-raises.
def retry_calls(max_retries):
  return retry_loop(0, max_retries)

def retry_loop(attempt, max_retries):
  // one call has just failed; attempt counts failures so far
  if attempt + 1 > max_retries:
    return attempt + 1
  else:
    return retry_loop(attempt + 1, max_retries)

// ---------------------------------------------------------------------------
// LAW-AGENT-1: Every agent in a pipeline has a unique identity (AgentConfig.name).
type Proof_AGENT_1:
  NamesDistinct { names_checked }
// PROOF: unit-test  (no witness proof_agent_1 can be constructed: the invariant is not enforced)
// STATUS: violated -- AgentPipeline.__init__ (src/azureml_agent_sdk/pipeline.py:57-64) and YamlPipelineConfig.agents (yaml_loader.py:56) accept duplicate agent names; there is no registry.

// ---------------------------------------------------------------------------
// LAW-AGENT-2: Activation is idempotent: the AOAI client is built at most once per agent and then reused.
type Proof_AGENT_2:
  ClientBuiltOnce { builds }
def proof_agent_2() -> Proof_AGENT_2:
  return Proof_AGENT_2/ClientBuiltOnce { builds: activate_count(0, 5) }
// STATUS: hold -- AzureOpenAIAgent.client (agent.py:41-48) caches self._client; exercised in tests/test_agent.py.

// ---------------------------------------------------------------------------
// LAW-AGENT-3: Deactivation releases the agent's client and blocks further runs.
type Proof_AGENT_3:
  Deactivated { released }
// PROOF: unit-test  (no witness proof_agent_3 can be constructed: the invariant is not enforced)
// STATUS: violated -- AzureOpenAIAgent (agent.py:26-87) has no close()/deactivate(); the cached client (agent.py:38) lives for the object's lifetime and run() (agent.py:59) is always callable.

// ---------------------------------------------------------------------------
// LAW-AGENT-4: An agent's identity fields are non-blank and immutable after construction.
type Proof_AGENT_4:
  IdentityFrozen { blank_rejected, assignment_rejected }
// PROOF: unit-test  (no witness proof_agent_4 can be constructed: the invariant is not enforced)
// STATUS: partial -- Blank name/system_prompt/model are rejected (config.py:31-34) but AgentConfig (config.py:22) is not frozen and has no validate_assignment, so agent.config.name can be reassigned to '' or a duplicate.

// ---------------------------------------------------------------------------
// LAW-PIPE-1: The pipeline execution graph is acyclic.
type Proof_PIPE_1:
  LinearChain { length, back_edges }
def proof_pipe_1() -> Proof_PIPE_1:
  return Proof_PIPE_1/LinearChain { length: chain_len(3), back_edges: 0 }
// STATUS: proven -- AgentPipeline.agents is a flat list run by one for-loop (pipeline.py:97); a list has no back-edges by construction, see the structural argument and chain_len below.

// ---------------------------------------------------------------------------
// LAW-PIPE-2: Agents execute in exactly the order they were declared (topological order of a chain).
type Proof_PIPE_2:
  DeclaredOrder { positions_monotone }
def proof_pipe_2() -> Proof_PIPE_2:
  return Proof_PIPE_2/DeclaredOrder { positions_monotone: 1 }
// STATUS: hold -- pipeline.py:97 iterates self.agents in order; tests/test_pipeline.py:76 and tests/test_parallel.py:70 assert ordering.

// ---------------------------------------------------------------------------
// LAW-PIPE-3: No agent starts before the batch job has reached the Completed state (dependency completeness).
type Proof_PIPE_3:
  BatchBeforeAgents { batch_done_first }
def proof_pipe_3() -> Proof_PIPE_3:
  return Proof_PIPE_3/BatchBeforeAgents { batch_done_first: 1 }
// STATUS: hold -- trigger.run() (pipeline.py:78) either returns a Completed BatchJobResult or raises (batch_trigger.py:72-73); only then does the agent loop (pipeline.py:97) run.

// ---------------------------------------------------------------------------
// LAW-PIPE-4: Given identical batch output and agent responses, a pipeline run is deterministic.
type Proof_PIPE_4:
  Deterministic { rows_sorted, temp_pinned }
// PROOF: property-test  (no witness proof_pipe_4 can be constructed: the invariant is not enforced)
// STATUS: partial -- Row serialisation is stable (results.py:47 sort_keys=True) and order is fixed, but AgentConfig.temperature defaults to 0.7 (config.py:27) and no seed is passed to chat.completions.create (agent.py:64-69).

// ---------------------------------------------------------------------------
// LAW-COMP-1: Compute quota is enforced before any work is dispatched.
type Proof_COMP_1:
  QuotaEnforced { limit_checked }
// PROOF: unit-test  (no witness proof_comp_1 can be constructed: the invariant is not enforced)
// STATUS: violated -- The SDK has no compute abstraction. The only limiter is ParallelAgentGroup.max_concurrency (parallel.py:27), which defaults to None = unbounded (parallel.py:44).

// ---------------------------------------------------------------------------
// LAW-COMP-2: Scale is bounded: min <= configured <= max for every compute target.
type Proof_COMP_2:
  ScaleBounded { min_nodes, max_nodes }
// PROOF: unit-test  (no witness proof_comp_2 can be constructed: the invariant is not enforced)
// STATUS: violated -- No min/max instance settings exist in BatchEndpointConfig (config.py:8-20); max_concurrency is validated >= 1 (parallel.py:28) but has no upper bound.

// ---------------------------------------------------------------------------
// LAW-COMP-3: Idle compute is reclaimed after a bounded idle timeout.
type Proof_COMP_3:
  IdleReclaimed { timeout_s }
// PROOF: static-analysis  (no witness proof_comp_3 can be constructed: the invariant is not enforced)
// STATUS: violated -- No cluster idle-timeout is configured or verified anywhere in src/; timeout_seconds (config.py:17) only bounds job polling.

// ---------------------------------------------------------------------------
// LAW-COMP-4: Every submitted compute resource/job carries identifying tags.
type Proof_COMP_4:
  Tagged { tags_present }
// PROOF: unit-test  (no witness proof_comp_4 can be constructed: the invariant is not enforced)
// STATUS: violated -- BatchEndpointTrigger.submit (batch_trigger.py:41-45) calls batch_endpoints.invoke without tags/properties.

// ---------------------------------------------------------------------------
// LAW-MODEL-1: Registered model versions increase monotonically.
type Proof_MODEL_1:
  VersionMonotone { prev, next }
// PROOF: unit-test  (no witness proof_model_1 can be constructed: the invariant is not enforced)
// STATUS: violated -- There is no model registry; the only version-like value is AgentConfig.api_version (config.py:30), a free-form string with no ordering.

// ---------------------------------------------------------------------------
// LAW-MODEL-2: A registered model's schema is immutable after registration.
type Proof_MODEL_2:
  SchemaFrozen { frozen }
// PROOF: unit-test  (no witness proof_model_2 can be constructed: the invariant is not enforced)
// STATUS: violated -- AgentConfig/BatchEndpointConfig/PipelineConfig (config.py:8,22,35) are mutable Pydantic models (no model_config frozen=True).

// ---------------------------------------------------------------------------
// LAW-MODEL-3: Every pipeline result carries complete lineage: job -> rows -> agent runs -> model.
type Proof_MODEL_3:
  LineageComplete { job, rows, runs, model }
// PROOF: unit-test  (no witness proof_model_3 can be constructed: the invariant is not enforced)
// STATUS: partial -- PipelineResult (pipeline.py:37-42) links job, rows and agent_runs, but AgentRunResult (pipeline.py:29-33) records only agent_name, not model/deployment/api_version.

// ---------------------------------------------------------------------------
// LAW-MODEL-4: Artifacts read from a batch output are integrity-checked before use.
type Proof_MODEL_4:
  ArtifactVerified { digest_ok }
// PROOF: unit-test  (no witness proof_model_4 can be constructed: the invariant is not enforced)
// STATUS: violated -- parse_batch_output (results.py:33-42) reads the file and parses it with no checksum/size/row-count verification.

// ---------------------------------------------------------------------------
// LAW-RETRY-1: RetryPolicy.call invokes the function at most max_retries + 1 times.
type Proof_RETRY_1:
  AttemptsBounded { max_retries, calls }
def proof_retry_1() -> Proof_RETRY_1:
  return Proof_RETRY_1/AttemptsBounded { max_retries: 3, calls: retry_calls(3) }
// STATUS: proven -- retry.py:62-70: attempt increments per failure and re-raises when attempt > max_retries, so calls == max_retries + 1 exactly; retry_calls below checks the model, tests/test_retry.py:71,141 check the code.

// ---------------------------------------------------------------------------
// LAW-RETRY-2: Each backoff delay is <= max_delay (exponential growth is capped).
type Proof_RETRY_2:
  DelayCapped { cap, worst_case }
// PROOF: property-test  (no witness proof_retry_2 can be constructed: the invariant is not enforced)
// STATUS: partial -- compute_delay (retry.py:55-58) caps the exponential term, then adds jitter afterwards, so delay can reach max_delay*(1+jitter); jitter is not validated (retry.py:41-46), so it may be negative or > 1.

// ---------------------------------------------------------------------------
// LAW-RETRY-3: Retrying a call is idempotent: a retried operation has no duplicated side effects.
type Proof_RETRY_3:
  IdempotentRetry { dedupe_key }
// PROOF: unit-test  (no witness proof_retry_3 can be constructed: the invariant is not enforced)
// STATUS: partial -- AzureOpenAIAgent.run (agent.py:59-71) is side-effect free and safe to retry, but BatchEndpointTrigger.submit (batch_trigger.py:38-46) creates a new job on every call with no idempotency key, and RetryPolicy.call (retry.py:60) gives no way to mark a callable non-retryable.

// ---------------------------------------------------------------------------
// LAW-RETRY-4: After a timeout, no partial writes remain: the remote job is cancelled.
type Proof_RETRY_4:
  TimeoutCancels { cancelled }
// PROOF: unit-test  (no witness proof_retry_4 can be constructed: the invariant is not enforced)
// STATUS: violated -- BatchEndpointTrigger.run raises BatchJobTimeoutError (batch_trigger.py:65-69) without cancelling the job, so the remote batch keeps running and can still write its output.

// ---------------------------------------------------------------------------
// LAW-SCHEMA-1: Input schemas are validated before execution begins.
type Proof_SCHEMA_1:
  InputsValidated { config_ok, rows_ok }
// PROOF: unit-test  (no witness proof_schema_1 can be constructed: the invariant is not enforced)
// STATUS: partial -- Config and YAML are validated by Pydantic before any run (config.py, yaml_loader.py:63), but parsed batch rows go straight to agents (pipeline.py:93-101) with no row schema check.

// ---------------------------------------------------------------------------
// LAW-SCHEMA-2: Agent/pipeline outputs are verified against a schema after the run.
type Proof_SCHEMA_2:
  OutputsVerified { schema_ok }
// PROOF: unit-test  (no witness proof_schema_2 can be constructed: the invariant is not enforced)
// STATUS: violated -- AgentResponse.content (agent.py:19-24) is an unvalidated string; PipelineResult (pipeline.py:37-42) is built at pipeline.py:122 with no output validation.

// ---------------------------------------------------------------------------
// LAW-SCHEMA-3: Breaking schema changes are rejected instead of silently accepted.
type Proof_SCHEMA_3:
  BreakingRejected { unknown_type_rejected, unknown_key_rejected }
// PROOF: unit-test  (no witness proof_schema_3 can be constructed: the invariant is not enforced)
// STATUS: partial -- Unknown agent type is rejected (Literal at yaml_loader.py:37), but Pydantic's default extra='ignore' silently drops unknown/misspelled keys (config.py:8-49, yaml_loader.py:51-56) and there is no schema version field.

// ---------------------------------------------------------------------------
// LAW-SCHEMA-4: The nullability contract holds: a field typed non-null is never None at runtime.
type Proof_SCHEMA_4:
  NonNullHolds { content_non_null }
// PROOF: unit-test  (no witness proof_schema_4 can be constructed: the invariant is not enforced)
// STATUS: violated -- AgentResponse.content is typed str (agent.py:22) but is assigned completion.choices[0].message.content (agent.py:70), which is None for tool-call/filtered replies; parse_csv (results.py:27-30) also yields None for short rows.

// ---------------------------------------------------------------------------
// LAW-AUTH-1: Every AML call is scoped to exactly one (subscription, resource group, workspace).
type Proof_AUTH_1:
  WorkspaceScoped { scope_fixed }
def proof_auth_1() -> Proof_AUTH_1:
  return Proof_AUTH_1/WorkspaceScoped { scope_fixed: 1 }
// STATUS: hold -- AzureMLClientWrapper binds all three identifiers at construction (aml_client.py:26-28) and builds MLClient from them (aml_client.py:40-45); build_pipeline requires them (yaml_loader.py:76-84).

// ---------------------------------------------------------------------------
// LAW-AUTH-2: Roles are minimal: the SDK declares and needs no more than the least-privilege roles.
type Proof_AUTH_2:
  RolesMinimal { roles_declared }
// PROOF: static-analysis  (no witness proof_auth_2 can be constructed: the invariant is not enforced)
// STATUS: violated -- No least-privilege role list (e.g. AzureML Data Scientist / Cognitive Services OpenAI User) is declared in code or docs/README.md; nothing verifies the credential's roles.

// ---------------------------------------------------------------------------
// LAW-AUTH-3: Expired tokens are never used: token lifetime is enforced by the credential layer.
type Proof_AUTH_3:
  ExpiryEnforced { delegated }
def proof_auth_3() -> Proof_AUTH_3:
  return Proof_AUTH_3/ExpiryEnforced { delegated: 1 }
// STATUS: hold -- agent.py:49-53 uses get_bearer_token_provider (refreshes per call) and credentials.py:25-34 caches only the credential object, not a token; the static API-key path (agent.py:44) has no expiry by nature.

// ---------------------------------------------------------------------------
// LAW-AUTH-4: The audit log is complete: every step, including failures, is logged with redaction.
type Proof_AUTH_4:
  AuditComplete { success_logged, failure_logged }
// PROOF: unit-test  (no witness proof_auth_4 can be constructed: the invariant is not enforced)
// STATUS: partial -- log_step is called for batch/agent start and complete (pipeline.py:68,82,98,107) but the failure paths (pipeline.py:79-81, 102-106) only emit events, not log_step; the log has no caller identity, and _redact (logging_utils.py:18-21) matches keys exactly (e.g. 'api-key' would leak).

// ---------------------------------------------------------------------------
// LAW-TST-1: No test is skipped or xfailed without an issue ID.
type Proof_TST_1:
  NoBareSkips { bare_skips }
def proof_tst_1() -> Proof_TST_1:
  return Proof_TST_1/NoBareSkips { bare_skips: 0 }
// STATUS: hold -- grep -rnE 'skip|xfail' tests/ finds only the test name test_skips_blank_lines (tests/test_results.py:23); no skip/xfail markers exist.

// ---------------------------------------------------------------------------
// LAW-TST-2: Every AGENT state transition is covered by a test.
type Proof_TST_2:
  TransitionsCovered { covered, total }
// PROOF: unit-test  (no witness proof_tst_2 can be constructed: the invariant is not enforced)
// STATUS: partial -- Lazy activation is tested (tests/test_agent.py) but registration-uniqueness and deactivation transitions have no tests because no such code exists (see LAW-AGENT-1, LAW-AGENT-3).

// ---------------------------------------------------------------------------
// LAW-TST-3: RETRY has adversarial tests (hostile inputs, not just the happy path).
type Proof_TST_3:
  RetryAdversarial { cases }
// PROOF: property-test  (no witness proof_tst_3 can be constructed: the invariant is not enforced)
// STATUS: partial -- tests/test_retry.py covers exhaustion, non-retryable errors and caps, but nothing tests jitter > 1 / negative jitter (retry.py:41-46), delay-over-cap with jitter (retry.py:58), or retry of a non-idempotent submit.

// ---------------------------------------------------------------------------
// LAW-TST-4: The full regression suite runs in under 90 seconds.
type Proof_TST_4:
  FastSuite { seconds, budget }
def proof_tst_4() -> Proof_TST_4:
  return Proof_TST_4/FastSuite { seconds: 11, budget: 90 }
// STATUS: hold -- Measured 2026-09-23: `uv run pytest -q` -> 121 passed in 10.29s (13.8s wall incl. uv).

// =============================================================================
// Self-check: evaluating these terms must reduce without error.
def main():
  a = activate_count(0, 5)
  b = chain_len(3)
  c = retry_calls(3)
  return (a, b, c)   // expected (1, 3, 4)

// =============================================================================
// MANIFEST -- violated / partial laws, exact source location, remediation
// =============================================================================
// LAW-AGENT-1 [violated]
//   at    : src/azureml_agent_sdk/pipeline.py:57-64
//   fix   : Reject duplicate names in AgentPipeline.__init__ and YamlPipelineConfig (model_validator); add a test.
// LAW-AGENT-3 [violated]
//   at    : src/azureml_agent_sdk/agent.py:26-87
//   fix   : Add AzureOpenAIAgent.close() that drops the client and makes run() raise; support context-manager use.
// LAW-AGENT-4 [partial]
//   at    : src/azureml_agent_sdk/config.py:31-34
//   fix   : Set model_config = ConfigDict(frozen=True) on AgentConfig (or validate_assignment=True).
// LAW-PIPE-4 [partial]
//   at    : src/azureml_agent_sdk/results.py:47
//   fix   : Pass a seed and document that temperature=0 + seed gives best-effort determinism; add a fake-client property test.
// LAW-COMP-1 [violated]
//   at    : src/azureml_agent_sdk/parallel.py:27
//   fix   : Introduce a ComputeQuota check (or document out-of-scope); default max_concurrency to a finite value.
// LAW-COMP-2 [violated]
//   at    : src/azureml_agent_sdk/config.py:8-20
//   fix   : Add min/max bounds to config and validate min <= max <= quota; cap max_concurrency.
// LAW-COMP-3 [violated]
//   at    : src/azureml_agent_sdk/config.py:17
//   fix   : Expose/verify cluster idle-timeout via MLClient compute settings, or declare compute out of scope in docs.
// LAW-COMP-4 [violated]
//   at    : src/azureml_agent_sdk/batch_trigger.py:41-45
//   fix   : Pass tags/properties (pipeline name, SDK version) to batch_endpoints.invoke.
// LAW-MODEL-1 [violated]
//   at    : src/azureml_agent_sdk/config.py:30
//   fix   : Add a model registry with a monotonic integer version, or declare it out of scope and drop the law.
// LAW-MODEL-2 [violated]
//   at    : src/azureml_agent_sdk/config.py:8,22,35
//   fix   : Set frozen=True on config models; hash the config at registration.
// LAW-MODEL-3 [partial]
//   at    : src/azureml_agent_sdk/pipeline.py:37-42
//   fix   : Add model, deployment and api_version to AgentRunResult; assert non-empty in PipelineResult.
// LAW-MODEL-4 [violated]
//   at    : src/azureml_agent_sdk/results.py:33-42
//   fix   : Verify a digest/row-count of the batch output before parsing; fail closed.
// LAW-RETRY-2 [partial]
//   at    : src/azureml_agent_sdk/retry.py:55-58
//   fix   : Apply the max_delay cap after adding jitter and validate 0 <= jitter <= 1 in __init__.
// LAW-RETRY-3 [partial]
//   at    : src/azureml_agent_sdk/agent.py:59-71
//   fix   : Add an idempotency key/dedupe lookup to submit() and a `retryable` opt-out in RetryPolicy.call.
// LAW-RETRY-4 [violated]
//   at    : src/azureml_agent_sdk/batch_trigger.py:65-69
//   fix   : On timeout, cancel the job (jobs.begin_cancel) before raising BatchJobTimeoutError; test it.
// LAW-SCHEMA-1 [partial]
//   at    : src/azureml_agent_sdk/yaml_loader.py:63
//   fix   : Add an optional row schema (Pydantic model) applied after parse_batch_output.
// LAW-SCHEMA-2 [violated]
//   at    : src/azureml_agent_sdk/agent.py:19-24
//   fix   : Add an optional output schema/validator to AgentConfig and check it in AzureOpenAIAgent.run.
// LAW-SCHEMA-3 [partial]
//   at    : src/azureml_agent_sdk/yaml_loader.py:37
//   fix   : Set extra='forbid' on config models; add a schema_version field and reject mismatches.
// LAW-SCHEMA-4 [violated]
//   at    : src/azureml_agent_sdk/agent.py:22
//   fix   : Coerce None content to '' or raise a typed error in agent.py:70; make AgentResponse.content Optional if intended.
// LAW-AUTH-2 [violated]
//   at    : src/azureml_agent_sdk/
//   fix   : Document least-privilege roles in docs/README.md and add a startup role check or doctor command.
// LAW-AUTH-4 [partial]
//   at    : src/azureml_agent_sdk/pipeline.py:68,82,98,107
//   fix   : log_step on failure paths (pipeline.py:79-81, 102-106); include caller identity; normalise keys in _redact.
// LAW-TST-2 [partial]
//   at    : src/azureml_agent_sdk/
//   fix   : After fixing AGENT-1/AGENT-3, add transition tests for register/duplicate/deactivate.
// LAW-TST-3 [partial]
//   at    : src/azureml_agent_sdk/retry.py:41-46
//   fix   : Add hypothesis property tests for jitter, cap, and non-idempotent retry after RETRY-2/RETRY-3 fixes.
