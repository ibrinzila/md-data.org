

<!-- ci-capacity-fallback:start -->
## CI capacity and owned-runner fallback — standing owner instruction

- Use available included GitHub Actions minutes or an already authorised CI budget first. Do not increase budgets, purchase capacity, or wait for a reset when the owned-runner fallback can do the work.
- If hosted minutes, billing caps, queues, or service availability prevent execution, automatically use the repository's existing local/self-hosted runner or dedicated owned safe lane. This fallback is already authorised; do not return the CI budget decision to the owner.
- Missing runner registration, compatible runtime, workflow routing, or result storage is repository engineering/backlog work. Discover and reuse existing runners before creating anything. Record a concrete setup/repair item in the repository's existing backlog, and complete machine-remediable work within the active task's authority; do not classify it as an owner decision or substitute unrelated feature work.
- Preserve the actual verification: exact candidate identity, required tests, OS/runtime/browser coverage, security/isolation, retained logs and artifacts, and honest check results. Adapt the execution and evidence route rather than treating a historical requirement for GitHub-hosted compute as immutable. Never fabricate a green check, weaken tests, or bypass branch protection.
- A GitHub artifact-upload/storage failure is distinct from a failed build or test. Preserve evidence on an existing authorised durable local/owned store and repair the reporting path; do not repeatedly rerun unchanged tests or request spend merely to store their results.
- Escalate only a concrete action that truly requires human authority or unavailable access (for example protected runner registration, credentials, or an existing release approval), with the attempted machine recovery and smallest remaining action. Quota exhaustion by itself is not such an escalation.
- These instructions supersede older repo guidance that treats exhausted GitHub capacity as a reason to wait, seek more budget, or stop without attempting the fallback. Product, security, signing, sending, payment and deployment approval gates remain intact. A policy update does not resume a paused task.
<!-- ci-capacity-fallback:end -->
