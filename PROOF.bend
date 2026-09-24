# =============================================================================
# PROOF.bend -- live evidence manifest for azureml-agent-sdk (companion to LAWS.bend)
# Date     : 2026-09-24
# Method   : each law re-checked against source at HEAD (cat -n line numbers),
#            grep, test-file inspection, and a real `uv run pytest -q` run
#            (121 passed in 10.23s).
# Laws     : 32 (one proof per LAW_ID in LAWS.bend)
# SUMMARY  : (proven, holds, partial, violated) = (2, 7, 10, 13)   total = 32
#   PROVEN    2  structural argument + tests
#   HOLDS     7  source inspection + passing tests
#   PARTIAL  10  law holds for part of its scope
#   VIOLATED 13  source does not enforce the law (missing piece is stated)
# NOTE     : several line references in LAWS.bend are stale (e.g. agent.run is
#            agent.py:74-87, not 59-71; AgentConfig is config.py:31, not 22;
#            trigger timeout is batch_trigger.py:84-88, not 65-69). The
#            EVIDENCE lines below use the current, re-verified line numbers.
#            Verdicts agree with LAWS.bend statuses for all 32 laws.
# =============================================================================

type Verdict:
  Proven
  Holds
  Partial
  Violated

# PROOF_AGENT_1: unique agent identity
# LAW_REF: LAW-AGENT-1
# EVIDENCE: src/azureml_agent_sdk/pipeline.py:57-61 only checks `not agents`; no name-uniqueness check. src/azureml_agent_sdk/yaml_loader.py:56 `agents: list[YamlAgentConfig] = Field(min_length=1)` has no uniqueness validator. Missing: duplicate-name rejection (registry or model_validator) + test.
# VERDICT: VIOLATED
def proof_agent_1() -> Verdict:
  return Verdict/Violated

# PROOF_AGENT_2: idempotent activation
# LAW_REF: LAW-AGENT-2
# EVIDENCE: src/azureml_agent_sdk/agent.py:40-48 `client` property builds only when `self._client is None` and caches. tests/test_agent.py:107 test_client_factory_called_once_and_cached passes (uv run pytest: 121 passed).
# VERDICT: HOLDS
def proof_agent_2() -> Verdict:
  return Verdict/Holds

# PROOF_AGENT_3: deactivation releases client
# LAW_REF: LAW-AGENT-3
# EVIDENCE: src/azureml_agent_sdk/agent.py:26-87 defines only __init__/client/_build_default_client/run; grep for close|deactivate|__exit__ finds nothing. Missing: close() that drops self._client (agent.py:38) and makes run() (agent.py:74) raise.
# VERDICT: VIOLATED
def proof_agent_3() -> Verdict:
  return Verdict/Violated

# PROOF_AGENT_4: identity non-blank and immutable
# LAW_REF: LAW-AGENT-4
# EVIDENCE: Blank rejected: src/azureml_agent_sdk/config.py:42-45 field_validator on name/system_prompt/model. Not immutable: AgentConfig (config.py:31) has no model_config; grep for frozen|validate_assignment in src/ hits only aml_client.py:16 (an unrelated dataclass). agent.config.name = '' is accepted.
# VERDICT: PARTIAL
def proof_agent_4() -> Verdict:
  return Verdict/Partial

# PROOF_PIPE_1: acyclic execution graph
# LAW_REF: LAW-PIPE-1
# EVIDENCE: src/azureml_agent_sdk/pipeline.py:53,61 agents is a flat list; pipeline.py:97 single `for agent in self.agents` loop. _Agent protocol (pipeline.py:22-25) has run(user_message) so an AgentPipeline (run() takes no args) cannot be nested as an agent. A flat list has no back-edges by construction; LAWS.bend chain_len spec reduces as expected.
# VERDICT: PROVEN
def proof_pipe_1() -> Verdict:
  return Verdict/Proven

# PROOF_PIPE_2: declared execution order
# LAW_REF: LAW-PIPE-2
# EVIDENCE: src/azureml_agent_sdk/pipeline.py:97 iterates in list order; pipeline.py:120 appends AgentRunResult in the same order. tests/test_pipeline.py:76 test_result_contains_per_agent_responses_in_agent_order; tests/test_parallel.py:70 test_result_ordering_matches_agent_order_regardless_of_delay.
# VERDICT: HOLDS
def proof_pipe_2() -> Verdict:
  return Verdict/Holds

# PROOF_PIPE_3: batch completes before agents
# LAW_REF: LAW-PIPE-3
# EVIDENCE: src/azureml_agent_sdk/pipeline.py:78 job = self.trigger.run() precedes the agent loop at pipeline.py:97; src/azureml_agent_sdk/batch_trigger.py:83-95 loops to a terminal state, raises BatchJobFailedError on Failed/Canceled (91-92), returns only for Completed. tests/test_pipeline.py:51 asserts trigger-then-agents.
# VERDICT: HOLDS
def proof_pipe_3() -> Verdict:
  return Verdict/Holds

# PROOF_PIPE_4: deterministic run
# LAW_REF: LAW-PIPE-4
# EVIDENCE: Stable: src/azureml_agent_sdk/results.py:47 json.dumps(sort_keys=True); fixed agent order. Not pinned: src/azureml_agent_sdk/config.py:37 temperature default 0.7; src/azureml_agent_sdk/agent.py:80-85 chat.completions.create passes no seed. grep -rn seed src/ -> no hits.
# VERDICT: PARTIAL
def proof_pipe_4() -> Verdict:
  return Verdict/Partial

# PROOF_COMP_1: compute quota enforced
# LAW_REF: LAW-COMP-1
# EVIDENCE: No compute abstraction in src/. Only limiter src/azureml_agent_sdk/parallel.py:27 max_concurrency defaults to None; parallel.py:44 None -> no semaphore (unbounded). Missing: quota check before dispatch.
# VERDICT: VIOLATED
def proof_comp_1() -> Verdict:
  return Verdict/Violated

# PROOF_COMP_2: bounded scale
# LAW_REF: LAW-COMP-2
# EVIDENCE: src/azureml_agent_sdk/config.py:13-23 BatchEndpointConfig has no min/max instance fields; src/azureml_agent_sdk/parallel.py:28 only validates max_concurrency >= 1, no upper bound. Missing: min<=configured<=max validation.
# VERDICT: VIOLATED
def proof_comp_2() -> Verdict:
  return Verdict/Violated

# PROOF_COMP_3: idle compute reclaimed
# LAW_REF: LAW-COMP-3
# EVIDENCE: grep -rniE 'idle|scale_down' src/ -> no hits. src/azureml_agent_sdk/config.py:23 timeout_seconds only bounds job polling (batch_trigger.py:84). Missing: idle-timeout config/verification, or declared out-of-scope.
# VERDICT: VIOLATED
def proof_comp_3() -> Verdict:
  return Verdict/Violated

# PROOF_COMP_4: submitted jobs tagged
# LAW_REF: LAW-COMP-4
# EVIDENCE: src/azureml_agent_sdk/batch_trigger.py:57-61 batch_endpoints.invoke(endpoint_name, deployment_name, input) passes no tags/properties; grep -rn tags src/ -> no hits.
# VERDICT: VIOLATED
def proof_comp_4() -> Verdict:
  return Verdict/Violated

# PROOF_MODEL_1: monotonic model versions
# LAW_REF: LAW-MODEL-1
# EVIDENCE: No model registry in src/. Only version-like value src/azureml_agent_sdk/config.py:40 api_version: str = '2024-02-15-preview', a free-form string with no ordering.
# VERDICT: VIOLATED
def proof_model_1() -> Verdict:
  return Verdict/Violated

# PROOF_MODEL_2: immutable model schema
# LAW_REF: LAW-MODEL-2
# EVIDENCE: src/azureml_agent_sdk/config.py:13,31,48 BatchEndpointConfig/AgentConfig/PipelineConfig are plain BaseModel with no frozen=True; grep frozen src/ finds no pydantic config.
# VERDICT: VIOLATED
def proof_model_2() -> Verdict:
  return Verdict/Violated

# PROOF_MODEL_3: complete lineage
# LAW_REF: LAW-MODEL-3
# EVIDENCE: src/azureml_agent_sdk/pipeline.py:37-42 PipelineResult links job, rows, agent_runs. src/azureml_agent_sdk/pipeline.py:28-33 AgentRunResult holds only agent_name and responses; no model/deployment/api_version, so the result cannot name the model that produced a response.
# VERDICT: PARTIAL
def proof_model_3() -> Verdict:
  return Verdict/Partial

# PROOF_MODEL_4: artifact integrity check
# LAW_REF: LAW-MODEL-4
# EVIDENCE: src/azureml_agent_sdk/results.py:33-42 parse_batch_output reads and parses the file with no checksum, size, or row-count verification.
# VERDICT: VIOLATED
def proof_model_4() -> Verdict:
  return Verdict/Violated

# PROOF_RETRY_1: attempts bounded by max_retries+1
# LAW_REF: LAW-RETRY-1
# EVIDENCE: src/azureml_agent_sdk/retry.py:62-70: attempt += 1 per retryable failure, `if attempt > self.max_retries: raise`, so calls == max_retries+1 exactly; non-retryable errors propagate at once. tests/test_retry.py:71 test_gives_up_after_max_retries_exhausted, :141 test_zero_max_retries_means_no_retrying. Model retry_calls(3)=4 in LAWS.bend.
# VERDICT: PROVEN
def proof_retry_1() -> Verdict:
  return Verdict/Proven

# PROOF_RETRY_2: delay capped at max_delay
# LAW_REF: LAW-RETRY-2
# EVIDENCE: src/azureml_agent_sdk/retry.py:57 caps the exponential term; retry.py:58 then adds delay*jitter*random(), so delay can reach max_delay*(1+jitter). retry.py:41-46 does not validate jitter (negative or >1 accepted). tests/test_retry.py:113 covers the cap only with jitter=0.
# VERDICT: PARTIAL
def proof_retry_2() -> Verdict:
  return Verdict/Partial

# PROOF_RETRY_3: retry idempotence
# LAW_REF: LAW-RETRY-3
# EVIDENCE: src/azureml_agent_sdk/agent.py:74-87 run() has no side effects and is safe to retry. src/azureml_agent_sdk/batch_trigger.py:53-62 submit() creates a new job per call with no idempotency key; src/azureml_agent_sdk/retry.py:60 call() has no non-retryable opt-out.
# VERDICT: PARTIAL
def proof_retry_3() -> Verdict:
  return Verdict/Partial

# PROOF_RETRY_4: timeout cancels remote job
# LAW_REF: LAW-RETRY-4
# EVIDENCE: src/azureml_agent_sdk/batch_trigger.py:84-88 raises BatchJobTimeoutError without cancelling; grep -rniE 'cancel' src/ hits only the 'Canceled' state name (batch_trigger.py:17,22). No jobs.begin_cancel call. Missing: cancel-on-timeout + test.
# VERDICT: VIOLATED
def proof_retry_4() -> Verdict:
  return Verdict/Violated

# PROOF_SCHEMA_1: inputs validated before execution
# LAW_REF: LAW-SCHEMA-1
# EVIDENCE: Config validated by Pydantic (src/azureml_agent_sdk/config.py:25-28,42-45,55-65; src/azureml_agent_sdk/yaml_loader.py:63 model_validate). Parsed rows go from pipeline.py:93 straight to agents (pipeline.py:94,101) with no row-schema check.
# VERDICT: PARTIAL
def proof_schema_1() -> Verdict:
  return Verdict/Partial

# PROOF_SCHEMA_2: outputs verified against schema
# LAW_REF: LAW-SCHEMA-2
# EVIDENCE: src/azureml_agent_sdk/agent.py:18-23 AgentResponse.content is a bare str; src/azureml_agent_sdk/pipeline.py:122 builds PipelineResult with no output validation. Missing: optional output schema/validator.
# VERDICT: VIOLATED
def proof_schema_2() -> Verdict:
  return Verdict/Violated

# PROOF_SCHEMA_3: breaking changes rejected
# LAW_REF: LAW-SCHEMA-3
# EVIDENCE: Unknown agent type rejected: src/azureml_agent_sdk/yaml_loader.py:37 Literal['azure_openai']. But no extra='forbid' anywhere (grep 'extra=' src/ -> none), so misspelled keys are silently dropped; no schema_version field.
# VERDICT: PARTIAL
def proof_schema_3() -> Verdict:
  return Verdict/Partial

# PROOF_SCHEMA_4: nullability contract
# LAW_REF: LAW-SCHEMA-4
# EVIDENCE: src/azureml_agent_sdk/agent.py:22 content: str, assigned at agent.py:86 from completion.choices[0].message.content, which the OpenAI SDK types Optional[str] (None for tool-call/filtered replies). src/azureml_agent_sdk/results.py:27-30 parse_csv yields None values for short rows via csv.DictReader.
# VERDICT: VIOLATED
def proof_schema_4() -> Verdict:
  return Verdict/Violated

# PROOF_AUTH_1: single-workspace scoping
# LAW_REF: LAW-AUTH-1
# EVIDENCE: src/azureml_agent_sdk/aml_client.py:35-37 binds subscription_id/resource_group/workspace_name at construction; aml_client.py:51-56 builds MLClient from them. src/azureml_agent_sdk/yaml_loader.py:76-84 requires all three (MissingCredentialError otherwise). tests/test_aml_client.py exists.
# VERDICT: HOLDS
def proof_auth_1() -> Verdict:
  return Verdict/Holds

# PROOF_AUTH_2: least-privilege roles
# LAW_REF: LAW-AUTH-2
# EVIDENCE: grep -rniE 'role|least.privilege|Data Scientist' docs README.md src -> no hits; docs/ contains only README.md. Missing: documented minimal roles and/or startup check.
# VERDICT: VIOLATED
def proof_auth_2() -> Verdict:
  return Verdict/Violated

# PROOF_AUTH_3: expired tokens never used
# LAW_REF: LAW-AUTH-3
# EVIDENCE: src/azureml_agent_sdk/agent.py:62-67 uses azure.identity.get_bearer_token_provider (per-request refresh); src/azureml_agent_sdk/credentials.py:25-34 caches only the credential object, never a token. Static API-key path (agent.py:56-60) has no expiry by nature.
# VERDICT: HOLDS
def proof_auth_3() -> Verdict:
  return Verdict/Holds

# PROOF_AUTH_4: complete redacted audit log
# LAW_REF: LAW-AUTH-4
# EVIDENCE: Success paths logged: src/azureml_agent_sdk/pipeline.py:68,82,98,107. Failure paths pipeline.py:79-81 and 102-106 only emit_sync('error'), no log_step. src/azureml_agent_sdk/logging_utils.py:18-21 _redact matches keys exactly against a fixed set (line 15), so 'api-key' or 'authorization' would leak; no caller identity in the log.
# VERDICT: PARTIAL
def proof_auth_4() -> Verdict:
  return Verdict/Partial

# PROOF_TST_1: no bare skip/xfail
# LAW_REF: LAW-TST-1
# EVIDENCE: grep -rnE 'skip|xfail' tests/ -> single hit tests/test_results.py:23 `test_skips_blank_lines` (a test name, not a marker).
# VERDICT: HOLDS
def proof_tst_1() -> Verdict:
  return Verdict/Holds

# PROOF_TST_2: agent state transitions tested
# LAW_REF: LAW-TST-2
# EVIDENCE: Lazy activation/caching tested (tests/test_agent.py:107). No tests for uniqueness or deactivation transitions because that code does not exist (see PROOF_AGENT_1, PROOF_AGENT_3).
# VERDICT: PARTIAL
def proof_tst_2() -> Verdict:
  return Verdict/Partial

# PROOF_TST_3: adversarial retry tests
# LAW_REF: LAW-TST-3
# EVIDENCE: tests/test_retry.py covers exhaustion (:71), non-retryable propagation (:88), cap (:113), constructor validation (:126-136). Absent: negative/>1 jitter, cap-with-jitter, non-idempotent submit retry; grep -n jitter tests/test_retry.py shows only the bounded case at :119.
# VERDICT: PARTIAL
def proof_tst_3() -> Verdict:
  return Verdict/Partial

# PROOF_TST_4: suite under 90 seconds
# LAW_REF: LAW-TST-4
# EVIDENCE: Measured 2026-09-24: `uv run pytest -q` -> 121 passed in 10.23s (13.5s wall incl. uv).
# VERDICT: HOLDS
def proof_tst_4() -> Verdict:
  return Verdict/Holds

# Self-check: reduces to Verdict/Proven.
def main():
  return proof_pipe_1()
