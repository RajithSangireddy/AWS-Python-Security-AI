# Cloud Security Automation Platform — Project Plan & Status

**Last updated:** 2026-11-12  
**Strategy:** AWS-first end-to-end platform; GCP deferred to Phase 2.  
**Evidence policy:** "Passed" means reported local test success, not an independently audited production release.

## 1. Mission

Build a portfolio-quality, cost-conscious, read-only AWS security automation platform. Collect IAM/security data, detect and explain risks, report findings, automate tests and deployment, and add a grounded AI assistant. Develop independent Python and software-design skills by implementing features with review rather than receiving full solutions.

**Phase 1 ends only after an AWS end-to-end demonstration with GitHub Actions, AppSec scanners, Docker, Kubernetes, Argo CD, and AI integration. No GCP development until then.**

## 2. Engineering and learning principles

- Least privilege: assume an AWS audit role; never embed credentials or perform remediation without human approval.
- Local-first and cost-conscious: prefer temporary infrastructure and teardown.
- Fail closed: collection errors propagate; do not present partial inventories as complete scans.
- Separate authentication, collectors, normalization, inventory orchestration, rules, reporting, and deployment.
- Keep AWS-specific models until cross-cloud requirements justify abstraction.
- Test critical success paths and failures; explicitly track missing coverage.
- User writes production Python; mentor provides design prompts, pseudocode, review, and targeted hints. AI may generate pytest/mock scaffolding to avoid spending disproportionate time on mocking syntax.
- Periodically assess **independent implementation**, not just whether guided code runs.

## 3. Current status snapshot

| Area | Status | Evidence / remaining work |
|---|---|---|
| Module 00 — Plan | Updated | Roadmap and learning progress revised after Module 04. |
| Module 01 — AWS Authentication | Complete (core) | `src/auth.py`, `security-audit` named profile, AssumeRole/STS verification. |
| Module 02 — Users / Access Keys | Implemented; additional coverage deferred | Paginated collection, usage, normalization, API/SDK errors; original 3 user-collector tests passed; other edge cases remain. |
| Module 03 — IAM Inventory Orchestration | Complete (core) | `src/aws_inventory.py`; raw users/keys and normalized keys; copied key enriched with usage; mocked orchestration tests reported passing. |
| Module 04 — IAM Roles & Trust Policies | Complete (module scope) | `list_iam_roles`, trust-statement normalization, inventory integration; live result 34 roles; 7/7 role-focused tests reported passed. |
| Module 05 — IAM Permissions & Policies | **Next** | Define policy/attachment scope and implement in small independent steps. |
| Security analyzer / findings schema / reporting | Planned | Existing placeholder/scaffolding files do not establish completed functionality. |
| AppSec, CI/CD, Docker, Terraform, Kubernetes, Argo CD | Planned | No deployment completion claimed. |
| AI findings assistant | Planned | Grounded explanations, correlation, prioritization, no autonomous remediation. |
| Phase 2 — GCP | Deferred | Only after AWS end-to-end milestone. |

**Scope caution:** The 7 passing tests are Module 04-focused. They do not prove all older Module 02 cases, every IAM trust-policy shape, or production readiness. No precise overall completion percentage is asserted without an effort baseline.

## 4. Phase 1 — Revised module roadmap

The **2026-11-09 draft** assigned Module 04 to analysis, Module 05 to reporting, and Module 06 to broader IAM inventory. Actual implementation changed that order. The following numbering supersedes the earlier proposal and keeps already-used chat/module IDs stable.

| Module | Deliverable | Definition of done | Status |
|---|---|---|---|
| 01 — Authentication | Reusable Boto3 session | STS verified; auth failures handled | Complete (core) |
| 02 — IAM Users & Keys | Users, keys, last-used, normalization | Paginated collectors and tests | Implemented; coverage follow-up |
| 03 — Inventory Orchestration | `collect_aws_iam_inventory(iam)` | Thin `main.py`, coherent raw/normalized inventory, mock tests | Complete (core) |
| 04 — IAM Roles & Trust Policies | Paginated roles, extracted trust statements | Real-account validation; focused tests; journal | Code/tests complete; journal produced with this update |
| 05 — IAM Permissions & Policies | Role-attached managed policies, inline policies and selected permission relationships | Define scope, collect with pagination, normalize, integrate, test | Next |
| 06 — Security Analyzer | IAM security rules including key and trust/permission risks | Deterministic, explainable findings with evidence/tests | Planned |
| 07 — Findings Schema & Reporting | JSON and human-readable reports | Stable schema, severity/evidence, samples, tests | Planned |
| 08 — AppSec Integration | Semgrep, Checkov, pip-audit, Gitleaks, Trivy | Repeatable local/CI scans; normalized results | Planned |
| 09 — CI/CD & Containerization | GitHub Actions, Docker | Lint/test/scan/build; protected secrets | Planned |
| 10 — Infrastructure & GitOps | Terraform, Kubernetes, Argo CD | Ephemeral deploy, sync, observability, teardown | Planned |
| 11 — AI Findings Assistant | Evidence-grounded analysis and correlation | Explicit uncertainty and prompt-injection controls | Planned |
| 12 — AWS End-to-End Release | Full demo and portfolio documentation | Tested collection → findings → report → deployment → AI | Planned |

## 5. Verified design and implementation through Module 04

### Module 03 inventory contract

```python
{
    "users": [...],
    "access_keys": [...],
    "normalized_keys": [...],
    "roles": [...],
    "normalized_roles": [...],
}
```

- `main.py` creates the session/client and delegates to `collect_aws_iam_inventory(iam)`.
- Access-key usage is merged into `key.copy()` with `.update(...)`, preserving raw records.
- Empty categories remain empty lists rather than missing keys.
- Roles are **lists of dictionaries**, not keyed only by RoleName, so future cross-account identity does not depend on globally unique role names.
- Normalized roles currently contain `role_name`, `role_arn`, and `trust_statements`; the last is always a list. This is extraction and shape normalization, **not** full principal/action/condition normalization.
- Live role collector returned 34 role dictionaries after correcting an `extend()` mistake; role-specific suite reported **7/7 passed** on 2026-11-12.

### Test status and deferred coverage

- Module 02: original user collector success/empty/two-page tests passed; broader key/usage/network/access-denied tests were deferred.
- Module 03: user shared updated `test_aws_inventory.py` with mocked roles, empty inventory, multiple users/keys, no keys, and propagation tests; user reported tests passing. Its parametrized failures did not originally include `list_iam_roles`.
- Module 04: separate role-focused suite reported 7 passing tests, covering role behavior and integration. Treat this as focused regression evidence, not exhaustive IAM validation.
- Before production claims: review error propagation in all collectors, response shape assumptions, permission-boundary handling, and full-suite results.

## 6. Phase 2 — GCP expansion (after AWS end-to-end milestone)

1. Evaluate which Phase 1 AWS contracts are genuinely reusable.
2. Add GCP authentication and read-only project/service-account/IAM collectors.
3. Normalize GCP findings into the established findings schema.
4. Add provider-specific orchestration and only then a lightweight multicloud coordinator if needed.
5. Extend tests, deployment configuration, AI correlation, and reports to GCP.

## 7. Module 01 and 02 learning record

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

## 8. Python skill-development checkpoint (2026-11-12)

**Observed strengths:** AWS/IAM domain knowledge; understanding and reviewing existing Python; Boto3 API usage; growing familiarity with list/dict nesting, pagination, function boundaries, raw vs normalized data, and debugging with `type()`/`pprint()`.

**Still developing:** implementing a feature from a blank file without a template; anticipating unusual input structures and failure modes; choosing data structures without extended prompting; independently identifying meaningful test scenarios. Test mocking syntax is deliberately not the main learning goal.

**Specific evidence:** Changing `append(role)` to `extend(role)` when `role` was a dictionary produced 260 dictionary-key strings rather than 34 role dictionaries. Corrected to `extend(page["Roles"])`. Implemented `isinstance(statements, dict)` then `[statements]` to keep a consistent trust-statement list. Questioned why normalized records should duplicate raw data, leading to a lean role record with ARN identity.

**Teaching adjustment for Module 05:** User first states function contract, input/output examples, algorithm and failure behavior; user writes production implementation; mentor reviews and hints; AI supplies most pytest/mock scaffolding. Include one small independent exercise and compare performance against this checkpoint. No numeric proficiency score should be treated as a formal assessment.

## 9. Immediate checklist

- [x] Module 03 inventory orchestration implemented and tested at core level.
- [x] Module 04 roles/trust-policy code integrated into inventory.
- [x] Live role collection validated: 34 roles.
- [x] Module 04 focused tests: 7/7 reported passing.
- [x] Prepare Module 04 learning journal and Module 05 handoff.
- [ ] Place generated Markdown files in repository and verify relative README links.
- [ ] Run full test suite: `python -m pytest -v`; investigate any regressions.
- [ ] Review `git status`, `git diff --check`, `.gitignore` and stage intended files only.
- [ ] Commit/push Module 04 code, tests, journal, and updated plan.
- [ ] Start Module 05 in a new chat using its starter context.
- [ ] Revisit deferred Module 02 coverage before calling the platform production-ready.

## 10. GitHub workflow

From repository root (adjust paths to your actual layout):

```powershell
python -m pytest -v
git status
git diff --check
git add 00-PROJECT-PLAN-AND-STATUS.md docs/04-iam-roles-trust-policies.md docs/05-module-starter.md
git status
git commit -m "docs: close IAM roles module and update AWS roadmap"
git push origin HEAD
```

Stage source and test changes separately if they have not already been committed. Never commit `.venv`, AWS credentials, secrets, or real access keys.

## 11. Suggested README documentation links

```markdown
## Project documentation
- [Project plan and status](00-PROJECT-PLAN-AND-STATUS.md)
- [Module 01 — Authentication](docs/01-authentication.md)
- [Module 02 — IAM Collector](docs/02-IAM-Collector-Learning-Journal.md)
- [Module 03 — AWS IAM Inventory](docs/03-aws-inventory.md)
- [Module 04 — IAM Roles & Trust Policies](docs/04-iam-roles-trust-policies.md)
- [Module 05 — Starter Context](docs/05-module-starter.md)
```

**Check actual repository filenames before committing these links.**
