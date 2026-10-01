# docs/PROOF.bend — proofs of every law in docs/LAWS.bend (Bend 2.0.20).
#
#   BEND_NO_TELEMETRY=1 /home/luuk/universe/.claude/tools/bend/bin/bend docs/PROOF.bend
#
# prints "All terms check." and exits 0 only when every `law` in
# docs/LAWS.bend has a `def Laws.<name>` here that the checker accepts. The
# proofs are about the Bend model in docs/LAWS.bend, not the Python code
# directly; see that file's header and per-law comments for the source
# symbol each model mirrors.
# No `main` on purpose: a value-returning main would replace this line with
# a value instead of proving the 21 laws below.

import Base
import ./LAWS.bend as Laws

# ---------------------------------------------------------------------------
# I. CONFIG NUMERIC BOUNDS — all closed reductions: Nat.add(1n, n) always
# reduces to a `1n+_` shape regardless of n's shape, which is already
# enough for Nat.is_lt/Nat.is_le to conclude without induction.
# ---------------------------------------------------------------------------

def Laws.poll_interval_seconds_positive(n):
  {==}

def Laws.timeout_seconds_positive(n):
  {==}

# temperature_lower_bound_nonneg: n is compared directly (not wrapped in a
# fresh 1n+_), so Nat.cmp(n, 0n) must case-split on n to reach a
# constructor -- both branches give the same answer.
def Laws.temperature_lower_bound_nonneg(n):
  match n:
    case 0n:
      {==}
    case 1n+p:
      {==}

# default_temperature_within_upper_bound: closed literal comparison, 7 <= 20.
def Laws.default_temperature_within_upper_bound():
  {==}

def Laws.max_tokens_positive_when_set(n):
  {==}

def Laws.pipeline_requires_at_least_one_agent(n):
  {==}

# ---------------------------------------------------------------------------
# II. RETRY POLICY
# ---------------------------------------------------------------------------

def Laws.max_retries_nonneg(n):
  match n:
    case 0n:
      {==}
    case 1n+p:
      {==}

def Laws.base_delay_positive(n):
  {==}

# max_delay_at_least_base_delay: base <= base + extra. Nat.is_le compares
# via Nat.cmp, which recurses on both arguments together; case-split on
# base to reach a constructor on each side (Nat.add(0n, extra) = extra,
# Nat.add(1n+p, extra) = 1n+Nat.add(p, extra), so the recursion lines up
# with the split on base without needing a separate lemma).
def Laws.max_delay_at_least_base_delay(base, extra):
  match base:
    case 0n:
      match extra:
        case 0n:
          {==}
        case 1n+q:
          {==}
    case 1n+p:
      Laws.max_delay_at_least_base_delay(p, extra)

# retry_attempts_eq_max_retries_plus_one: retry_attempts(1n+p) unfolds to
# 1n+retry_attempts(p); the induction hypothesis at p rewrites that to
# 1n+(1n+p), which is exactly Nat.add(1n, 1n+p). Same shape as the guide's
# `add_zero` example.
def Laws.retry_attempts_eq_max_retries_plus_one(m):
  match m:
    case 0n:
      {==}
    case 1n+p:
      %Laws.retry_attempts_eq_max_retries_plus_one(p) : {1n+Laws.retry_attempts(p) == 1n+_ : Nat}
      {==}

# ---------------------------------------------------------------------------
# III. BATCH ENDPOINT TRIGGER — exhaustive case splits over the 4
# JobStatus constructors (and, for Running, the 2 Bool values of
# timed_out); every branch is a closed reduction.
# ---------------------------------------------------------------------------

def Laws.run_returns_result_iff_completed(status, timed_out):
  match status:
    case Laws.Completed{}:
      {==}
    case Laws.Failed{}:
      {==}
    case Laws.Canceled{}:
      {==}
    case Laws.Running{}:
      match timed_out:
        case True{}:
          {==}
        case False{}:
          {==}

def Laws.timeout_raised_iff_running_and_timed_out(status, timed_out):
  match status:
    case Laws.Completed{}:
      {==}
    case Laws.Failed{}:
      {==}
    case Laws.Canceled{}:
      {==}
    case Laws.Running{}:
      match timed_out:
        case True{}:
          {==}
        case False{}:
          {==}

# ---------------------------------------------------------------------------
# IV. PARALLEL AGENT GROUP
# ---------------------------------------------------------------------------

def Laws.max_concurrency_positive_when_set(n):
  {==}

def Laws.parallel_group_requires_at_least_one_agent(n):
  {==}

# run_batch_preserves_message_count: run_batch_model prepends one element
# per input element (0n <> ...), so its length tracks the input length by
# structural induction -- same shape as add_zero.
def Laws.run_batch_preserves_message_count(messages):
  match messages:
    case Nil{}:
      {==}
    case Con{h, t}:
      %Laws.run_batch_preserves_message_count(t) : {1n+Laws.length(Laws.run_batch_model(t)) == 1n+_ : Nat}
      {==}

# ---------------------------------------------------------------------------
# V. AGENT MEMORY
# ---------------------------------------------------------------------------

def Laws.memory_max_tokens_at_least_one(n):
  {==}

# newest_message_survives_eviction: messages_after_worst_case_eviction
# ignores its argument and always returns 1n, so 0 < 1 holds for every
# prior_count without case-splitting on it.
def Laws.newest_message_survives_eviction(prior_count):
  {==}

# ---------------------------------------------------------------------------
# VI. AGENT ROUTER
# ---------------------------------------------------------------------------

# router_raises_only_when_no_match_and_no_default: induction on the match
# list. Con{True, t}: select -> Matched, raises -> False, and
# Bool.and(False{}, has_default) reduces directly (Bool.and matches on its
# first argument, which is already the closed value False{}) regardless of
# has_default's shape. Con{False, t}: select recurses on t, so the goal at
# this list is literally the induction hypothesis at the shorter list.
# Nil: has_default is case-split to reach the two SelectOutcome branches.
def Laws.router_raises_only_when_no_match_and_no_default(matches, has_default):
  match matches:
    case Nil{}:
      match has_default:
        case True{}:
          {==}
        case False{}:
          {==}
    case Con{True{}, t}:
      {==}
    case Con{False{}, t}:
      Laws.router_raises_only_when_no_match_and_no_default(t, has_default)

# ---------------------------------------------------------------------------
# VII. STRUCTURED LOGGING / REDACTION
# ---------------------------------------------------------------------------

# known_secret_keys_always_masked: exhaustive over the 6 SecretKey
# constructors; is_masked returns True{} in every case by definition.
def Laws.known_secret_keys_always_masked(key):
  match key:
    case Laws.SK_ApiKey{}:
      {==}
    case Laws.SK_AzureOpenAIApiKey{}:
      {==}
    case Laws.SK_Key{}:
      {==}
    case Laws.SK_Secret{}:
      {==}
    case Laws.SK_Token{}:
      {==}
    case Laws.SK_Password{}:
      {==}

# ---------------------------------------------------------------------------
# VIII. CLI
# ---------------------------------------------------------------------------

# exit_code_zero_iff_succeeded: exhaustive over the 2 CliOutcome
# constructors; each side is a closed literal comparison (0 == 0, 1 == 0).
def Laws.exit_code_zero_iff_succeeded(outcome):
  match outcome:
    case Laws.Succeeded{}:
      {==}
    case Laws.RunFailed{}:
      {==}

# ---------------------------------------------------------------------------
# IX. AZURE ML CLIENT (WORKSPACE SCOPING)
# ---------------------------------------------------------------------------

# nat_eq_refl: every Nat equals itself under Nat.is_eq -- needed because
# Nat.cmp recurses on both arguments together, so a bare `sub == sub` does
# not close without induction on the shared variable.
law nat_eq_refl:
  for n: Nat
  {Nat.is_eq(n, n) == True{} : Bool}

def nat_eq_refl(n):
  match n:
    case 0n:
      {==}
    case 1n+p:
      nat_eq_refl(p)

# workspace_scope_is_exactly_the_constructor_triple: make_scope stores its
# three arguments unchanged into a Scope record, so scope_fields_match
# reads back exactly sub/rg/ws; each Nat.is_eq(x, x) closes via
# nat_eq_refl, then Bool.and(True{}, _) collapses one conjunct at a time.
def Laws.workspace_scope_is_exactly_the_constructor_triple(sub, rg, ws):
  %Equal.sym(Bool, Nat.is_eq(sub, sub), True{}, nat_eq_refl(sub)) : {Bool.and(_, Bool.and(Nat.is_eq(rg, rg), Nat.is_eq(ws, ws))) == True{} : Bool}
  %Equal.sym(Bool, Nat.is_eq(rg, rg), True{}, nat_eq_refl(rg)) : {Bool.and(_, Nat.is_eq(ws, ws)) == True{} : Bool}
  %Equal.sym(Bool, Nat.is_eq(ws, ws), True{}, nat_eq_refl(ws)) : {_ == True{} : Bool}
  {==}
