# Cloud Security Automation Platform — Project Plan & Status

**Last updated:** 2026-11-09  
**Project strategy:** AWS-first, end-to-end delivery. GCP is explicitly deferred to Phase 2.  
**Status legend:** Complete / Implemented (testing incomplete) / In progress / Planned / Deferred.

## 1. Mission

Build a portfolio-quality, cost-conscious, read-only AWS security automation platform. Collect cloud identity and security data, analyze and prioritize risks, produce reports, automate testing and deployment, and integrate AI to explain and correlate findings. Develop independent Python/software architecture skills by implementing small pieces with senior-engineer-style design reviews.

**Phase 1 must reach an end-to-end AWS demonstration including GitHub Actions, security scanners, Docker, Kubernetes, Argo CD, and AI integration before GCP work starts.** GCP is Phase 2, not part of Module 03.

## 2. Non-negotiable engineering principles

- Least privilege; assume an AWS audit role; prefer read-only APIs and never embed real credentials.
- Local-first development; temporary cloud infrastructure and teardown to control cost.
- Fail closed on incomplete inventories; propagate collection errors rather than silently returning partial scans.
- Separate authentication, resource collection, inventory orchestration, analysis, reporting, and deployment responsibilities.
- Normalize data for analysis, but do not prematurely build a generic multicloud abstraction.
- Automated tests for critical paths, with deferred coverage tracked explicitly.
- Human review and approval for any future remediation; AI suggestions are not autonomous changes.
- **Teaching approach:** The user writes code; mentor gives requirements, trade-offs, pseudocode, focused hints, and code review. No full implementations unless explicitly requested.

## 3. Current status snapshot

| Area | Status | Evidence / next action |
|---|---|---|
| Module 00 — Master plan | In progress | This document establishes the tracked roadmap. |
| Module 01 — AWS authentication | Complete (core) | `src/auth.py`; named `security-audit` profile; AssumeRole/STS verified. |
| Module 02 — IAM collector | Implemented (testing incomplete) | IAM users, keys, last-used details, normalization, pagination, API/SDK error handling. |
| Module 02 — pytest | In progress | Three tests passed: success, empty users, two-page pagination. Additional tests deferred. |
| Module 02 — learning journal | Complete | `02-IAM-Collector-Learning-Journal.md` exists; verify it is committed. |
| Module 03 — AWS inventory orchestration | Next | Move correlation/orchestration out of `main.py` into an AWS-specific function. |
| AWS IAM analysis and reporting | Planned / partial scaffolding | `analyzer.py` and `reporter.py` appear in repository; implementation not independently verified. |
| AppSec scanners and CI/CD | Planned | Checkov, Semgrep, pip-audit, Gitleaks, Trivy; GitHub Actions. |
| Docker, Terraform, Kubernetes, Argo CD | Planned | AWS-first end-to-end pipeline; choose affordable cluster/deployment target before provisioning. |
| AI security assistant | Planned | Correlate, explain, and prioritize AWS/AppSec findings with guardrails. |
| Phase 2 — GCP | Deferred | Begin only after AWS + Argo CD + AI milestone is achieved. |

**Progress reporting:** Do not treat placeholder files as finished functionality. Three passing collector tests do not imply full collector test coverage. Overall completion percentage is intentionally not asserted without a reviewed scope/effort baseline.

## 4. Phase 1 — AWS-first implementation roadmap

| Module | Deliverable | Definition of done | Current status |
|---|---|---|---|
| 01 — Authentication | Reusable Boto3 session using audit-role profile | STS identity verified; predictable auth errors | Complete (core) |
| 02 — IAM Collector | Users, access keys, last-used metadata, pagination, normalization | Functional collector; initial tests; documented deferred edge cases | Implemented; remaining tests deferred |
| 03 — AWS IAM Inventory Orchestration | `collect_aws_iam_inventory(iam)` or equivalent AWS-specific workflow | `main.py` delegates; users and normalized keys correlated; coherent return structure; focused tests | Next |
| 04 — AWS Security Analyzer | Findings for unused/old keys, statuses and selected IAM risks | Rules are configurable, explainable, deterministic and tested | Planned |
| 05 — Reporting & Findings Schema | Machine-readable JSON and human-readable summary | Stable schema, severity/evidence, sample output, tests | Planned |
| 06 — Broader AWS IAM Inventory | IAM roles, trust policies, attached/inline policies and relevant relationships | Paginated collection, normalization, errors, tests | Planned |
| 07 — AppSec Integration | Semgrep, Checkov, pip-audit, Gitleaks, Trivy | Repeatable local scans; ingest/normalize findings; safe CI behavior | Planned |
| 08 — CI/CD & Containerization | Docker image and GitHub Actions pipeline | Lint/test/scan/build; secrets protected; reproducible builds | Planned |
| 09 — Infrastructure & GitOps | Terraform, Kubernetes deployment, Argo CD | Ephemeral deployment; GitOps sync; observability; teardown and cost controls | Planned |
| 10 — AI Findings Assistant | AI explanation, deduplication/correlation, prioritization | Grounded evidence, explicit uncertainty, prompt-injection controls, no autonomous remediation | Planned |
| 11 — AWS End-to-End Release | Working AWS collection → findings → reports → pipeline → deployment → AI | Demonstration, documentation, tests, architecture diagram, cost/security review | Planned |

Module numbering is a planning proposal after Module 03 and may be revised as dependencies become clearer. **No GCP implementation in Phase 1.**

### Module 03 — precise scope

**Goal:** Refactor the IAM user/access-key/usage coordination currently in `main.py` into a testable AWS inventory orchestration function/module (e.g., `src/aws_inventory.py`).

**In scope:** choose function signature; return structure for users and normalized keys; preserve key-to-usage correlation; propagate errors; keep `main.py` thin; test orchestration using existing collector interfaces.

**Out of scope:** GCP collection, multicloud orchestrator, generic provider framework, AI, Kubernetes, Argo CD, broad IAM-role support. These are later modules.

**Suggested design discussion:** Should the function return `{"users": [...], "access_keys": [...]}` or another explicit structure? How should account metadata be represented? When does a class become justified? Have the user propose a design before code is written.

## 5. Phase 2 — GCP expansion (after AWS end-to-end milestone)

1. Evaluate which Phase 1 AWS contracts are genuinely reusable.
2. Add GCP authentication and read-only project/service-account/IAM collectors.
3. Normalize GCP findings into the established findings schema.
4. Add provider-specific orchestration and only then a lightweight multicloud coordinator if needed.
5. Extend tests, deployment configuration, AI correlation, and reports to GCP.

## 6. Module 01 and 02 learning record

### Module 01 — authentication

- Boto3 Session vs service client; AWS CLI named profile, source profile, AssumeRole, STS `get_caller_identity`.
- Role trust versus permissions; no hardcoded credentials; reusable session.
- `ProfileNotFound`, `InvalidConfigError`, `NoCredentialsError`, `ClientError`; exception chaining via `raise ... from error`.

### Module 02 — collection, data structures, architecture

- Why `list[dict]` for many IAM users/keys but `dict` for attributes of one key's last-used details.
- Explicit indexing: Python will not automatically key users by `UserName`; `users_by_name[user["UserName"]] = user` does that. `.update(user)` instead merges fields and may overwrite prior user values.
- `.append()` vs `.extend()` vs `.update()`; `.get()`; `.copy()`; mutability and references.
- Pagination returns page dictionaries with `Users` / `AccessKeyMetadata`; continuation markers; incomplete pages must not silently produce a successful inventory.
- `try` does not make list updates transactional; an exception prevents the function's normal `return`.
- AWS `ClientError` vs `BotoCoreError`; SDK errors are not exclusively network failures.
- Usage lookup by `AccessKeyId`, merging usage into a copied key record, then normalizing. The orchestration belongs in an AWS-specific layer, not permanently in `main.py`.
- Dependency injection: collector receives the IAM client supplied by production or tests; no implicit precedence of `main.py` over test clients.
- pytest + Stubber: dummy credentials do not alone block network calls; Stubber intercepts a specific client; `add_response` checks response schema and expected request parameters; `assert_no_pending_responses()` checks unconsumed responses.
- Successful tests: normal IAM user collection, empty list, two-page pagination. Deliberate failures explored: short UserId, marker mismatch, and unused queued response.
- Deferred tests: `AccessDenied`, network/SDK failure, key collection, usage, normalization, partial-failure handling.

**Detailed source:** `02-IAM-Collector-Learning-Journal.md` and Module 01 authentication notes. Keep these as separate, detailed learning journals; this plan is the project index.

## 7. Immediate checklist

- [ ] Restore pagination test to `IsTruncated=True` and confirm all three tests pass.
- [ ] Review `git status`, `.gitignore`, and pending source changes.
- [ ] Commit Module 02 collector, error handler, tests and learning journal.
- [ ] Add this project plan to repository and link it from `README.md`.
- [ ] Start a new chat: **03 — AWS IAM Inventory Orchestration**.
- [ ] In Module 03, begin with design/return-value choices, not a full implementation.
- [ ] Revisit deferred Module 02 tests before treating the AWS inventory as production-ready.

## 8. GitHub workflow

From repository root:

```powershell
python -m pytest tests/test_collector.py -v
git status
git diff --check
git add 00-PROJECT-PLAN-AND-STATUS.md
git commit -m "docs: add AWS-first project roadmap and status"
git push origin HEAD
```

If other intended Module 02 changes are still uncommitted, review and stage them separately or in a deliberate combined commit. Never commit `.venv`, secrets, real access keys, or local credential files.

## 9. Suggested README links

```markdown
## Project documentation
- [Project plan and status](00-PROJECT-PLAN-AND-STATUS.md)
- [Module 01 — Authentication](01-authentication.md)
- [Module 02 — IAM Collector](02-IAM-Collector-Learning-Journal.md)
```

Adjust the Module 01/02 link paths to their actual repository locations. Update this plan after each module, recording verified test results, decisions, blockers, and next actions.
