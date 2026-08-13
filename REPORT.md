# 1. Architecture

The implementation is a small vertical slice with four boundaries: a target surface, a discovery controller, a capability artifact, and a deterministic replay engine. Playwright is the concrete browser surface. The discovery controller observes the page through a screenshot plus a compact control/visible-text representation, asks an LLM for exactly one next action, validates that action against policy, executes it, and records the decision. The successful action sequence is then compiled into a typed artifact.

The production path is deliberately different: replay loads the artifact and executes only its declared steps. There is no model call in the replay decision loop. This makes behavior auditable, cheap, and deterministic. The target app is a local synthetic member-servicing console because the assignment explicitly prohibits relying on real bank systems or credentials and asks for a concrete surface.

The architecture favors a clean seam over infrastructure breadth. `BrowserController` owns perception and browser mechanics; the artifact contains intent-neutral control descriptions; `ReplayEngine` owns deterministic execution; `policy.py` owns safety checks. This allows the same artifact model to sit above another surface adapter later.

# 2. Artifact schema

The artifact is a versioned Pydantic model with: capability identity/version, target origin, typed inputs, typed outputs, ordered action steps, locator strategy, retryability, risk classification, an explicit checkpoint, allowed actions, and metadata describing provenance.

A step stores the action type separately from its target. Locators prefer semantic strategies (`role`, `label`, visible `text`) and can carry fallbacks. Values are templates such as `{{member_id}}`, so the artifact is parameterized rather than tied to the discovery run's concrete member. Outputs have a declared name and type, and a checkpoint is required to prove that the desired state was reached.

This is intentionally not a raw transcript. The model may have reasoned about several possibilities during discovery, but the artifact records only the reusable contract and executable decisions.

# 3. Determinism & error handling

Replay never asks the LLM what to do next. It follows the artifact step-by-step, uses explicit locators, waits for page loads, applies bounded fallbacks where declared, and verifies a final checkpoint. The artifact is therefore the source of truth for the production execution path.

Runtime states are classified deliberately. `member_not_found` and `validation_error` are business outcomes, returned as structured results rather than exceptions. A slow load or known retryable action can be retried within its step timeout. Policy violations, missing controls, failed checkpoints, and unexpected application failures become hard failures with an error code, failed step, message, and screenshot evidence.

UI drift is secondary in this environment because the prompt says the applications are relatively stable. Nevertheless, semantic locators are preferred to brittle coordinates and the schema supports fallback locators. A future version would add locator health metrics and artifact approval/versioning.

# 4. Heterogeneity & multi-tenant

The artifact should not encode browser-specific implementation details beyond a generic surface/locator contract. For legacy web, the browser adapter can implement frame-aware locators, table-cell anchors, accessibility-tree queries, or screenshot/coordinate actions behind the same `ActionStep` interface. For desktop applications, a `desktop` surface adapter can translate the same action concepts to accessibility APIs or OS automation while preserving the capability contract.

For multi-tenant reuse, artifacts should be scoped to a canonical vendor application/version rather than a single institution. Tenant-specific configuration can be represented as a small overlay containing origin, known locator overrides, route patterns, and version metadata. Replay first resolves the base artifact and then applies a validated tenant overlay. If an overlay is incompatible, the system should fail closed and request re-recording rather than silently guessing.

Drift can be detected through checkpoint failures, locator fallback frequency, replay success rate, and application/version fingerprints. A healthy artifact can remain shared across tenants while only the minimum necessary locator or route override is specialized.

# 5. Escalation & handoff

The discovery agent can explicitly emit `escalate` when it is stuck or cannot safely determine the next action. The runner pauses rather than guessing, captures a screenshot and context, writes an intervention request, and waits for bounded operator commands.

The operator seam is intentionally minimal: the operator can fill a labeled control, click visible text, or resume. Commands are written to the waiting session's evidence directory and executed by the same discovery process against its still-live Playwright page/context. This preserves the live session rather than creating a fresh browser session. The intervention log records the handoff and operator command, after which control returns to automation.

A production implementation would replace the file-based seam with an authenticated operator service and a real co-browsing/remote-control channel, while preserving the same control-state model: `AUTOMATION`, `PAUSED_FOR_HUMAN`, `HUMAN`, and `AUTOMATION` again.

# 6. Safety

Safety is enforced before execution. The default origin allowlist contains only the local demo application, and only safe browser actions are allowed. Risky or irreversible actions are absent from the allowlist and therefore cannot be executed by the agent. This is a fail-closed design: the model cannot grant itself permissions.

Secrets are provided through environment variables and excluded by `.gitignore`. The target uses synthetic data. Evidence should contain only the minimum state needed for debugging; a production implementation would add field-level redaction before persistence and explicit retention policies.

The safety model is intentionally conservative. A future version could classify actions as safe, reversible, risky, or irreversible and require explicit human approval for the latter two classes.

# 7. Cuts

The implementation deliberately does not build production queues, a full multi-tenant control plane, a native desktop adapter, or a polished real-time operator console. These are breadth cuts rather than missing core capabilities. The important seams are present: surface abstraction, typed artifact, deterministic replay, policy enforcement, evidence, and same-session handoff.

With more time, the next additions would be: an authenticated operator web UI with live screenshots, artifact approval states and replay stability scoring, tenant/version overlays, stronger sensitive-data redaction, a legacy frameset fixture, and one desktop surface adapter. The first production hardening step would be to add replay metrics and fail-closed artifact compatibility checks before allowing unattended execution.
