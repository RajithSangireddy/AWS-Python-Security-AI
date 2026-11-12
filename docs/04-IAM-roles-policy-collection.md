# Module 04 — AWS IAM Roles & Trust Policies: Learning Journal

**Date closed:** 2026-11-12  
**Project:** Cloud Security Automation Platform (AWS-first)  
**Status:** Core implementation working; live collection returned 34 roles; 7/7 module-specific tests reported passed.

## 1. Objectives and boundaries

Module 04 extends the IAM collector and AWS inventory to include roles and their trust policies. Scope: list roles using IAM pagination; extract role identity and trust statements; keep a predictable data shape; integrate raw and normalized roles; test normal, empty, paginated and failure paths. **Out of scope:** full IAM permission/managed-policy collection (Module 05), evaluating whether a trust policy is risky (security analyzer), cross-account/GCP collectors, deployment and AI.

### Existing architecture

- `src/auth.py`: `create_aws_session(profile_name)` and STS verification.
- `src/collector.py`: user/key/usage collectors and normalizers; now role collector and trust-policy normalizer.
- `src/error_handler.py`: translates service failures; BotoCoreError handling remains explicit.
- `src/aws_inventory.py`: `collect_aws_iam_inventory(iam)` coordinates collection and normalization.
- `main.py`: obtains session/client and calls inventory orchestrator; printing/debugging kept separate from collectors.

## 2. Design decision: list of role dictionaries

**Question:** Should `list_iam_roles(iam)` return `{RoleName: role}` or `[role, role, ...]`?

The initial idea was a dictionary indexed by `RoleName` for convenient lookup. After considering users/keys, future multiple accounts and duplicate role names across accounts, the decision was to return a **list of role dictionaries**. This keeps the raw collector consistent and preserves all role records. A later analyzer may create an index keyed by `(account_id, role_name)` or role ARN if lookup performance warrants it. A list is not inherently faster for name lookups; the decision is about a consistent raw inventory contract.

Illustrative response:

```python
[
    {"RoleName": "ExampleAuditRole", "Arn": "arn:aws:iam::111122223333:role/ExampleAuditRole", "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "sts:AssumeRole", "Principal": {"Service": "ec2.amazonaws.com"}}]}},
    {"RoleName": "ExampleApplicationRole", "Arn": "arn:aws:iam::111122223333:role/ExampleApplicationRole", "AssumeRolePolicyDocument": {"Statement": []}},
]
```

The examples use invented non-secret names and IDs for illustration, not actual collected credentials.

## 3. IAM paginator and role collection

Boto3 `iam.get_paginator("list_roles")` returns a paginator; `.paginate()` produces page dictionaries; each page has a `Roles` list. The collector accumulates role dictionaries across all pages and returns one list.

Core loop (illustrative excerpt):

```python
iam_roles = []
paginator = iam.get_paginator("list_roles")
for page in paginator.paginate():
    iam_roles.extend(page["Roles"])
return iam_roles
```

A `ClientError` is an AWS service response error; a `BotoCoreError` is an SDK-side failure category and should not be mislabeled as always a network problem. Collection errors must propagate rather than yielding a partial inventory. A paginator simplifies marker handling, but does not remove the need for tests.

## 4. Major debugging lesson: `append()` versus `extend()`

Original nested loop was correct:

```python
for page in pages:
    for role in page["Roles"]:
        iam_roles.append(role)
```

Then `append(role)` was replaced by `extend(role)` while the nested loop remained:

```python
for page in pages:
    for role in page["Roles"]:
        iam_roles.extend(role)  # WRONG: role is a dict
```

**Observed symptom:** `len(iam_roles)` became **260**, while `type(iam_roles[0])` was `str`. This was not 260 IAM roles. `list.extend(iterable)` iterates the supplied iterable; iterating a dictionary yields its **keys**, so the list contained strings such as `"RoleName"` and `"Arn"` rather than whole role dictionaries.

Correct forms:

```python
# One dictionary at a time
for page in pages:
    for role in page["Roles"]:
        iam_roles.append(role)

# Or the shorter equivalent for a list of dictionaries
for page in pages:
    iam_roles.extend(page["Roles"])
```

The second version returned **34** roles on the user's AWS account, and `type(iam_roles[0])` was `dict`.

| Expression | Input | Result |
|---|---|---|
| `result.append(role)` | dict | Adds one dict as one element |
| `result.extend([role])` | one-element list containing dict | Adds one dict; equivalent result to `append(role)` |
| `result.extend(role)` | dict | Adds the dict's **keys** (strings): incorrect for role collection |
| `result.extend(page["Roles"])` | list of dicts | Adds each role dict as one element |
| `result.append(page["Roles"])` | list of dicts | Adds a nested list; different structure |

**Broader debugging habit:** Inspect both `len(collection)` and `type(collection[0])`, then sample the first element with `pprint()`. A plausible count does not prove a correct data shape.

## 5. Inspecting IAM trust policies

`from pprint import pprint` was used to display nested role dictionaries more readably. It affects **presentation only**, not the data structure.

Example trust policy observed in the learning exercise (simplified):

```python
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Principal": {"Service": "ec2.amazonaws.com"},
        }
    ],
}
```

The extraction path is:

```python
role["AssumeRolePolicyDocument"]["Statement"]
```

- `role` is a dictionary describing one IAM role.
- `AssumeRolePolicyDocument` is a nested dictionary.
- `Statement` may be a list of statements or a single statement dictionary.
- Each statement may have `Effect`, `Action`, `Principal` and optional `Condition` (and other policy fields).
- `statements[0]` accesses only the first statement, so analysis must eventually iterate all statements.
- **Trust policy**: who can assume the role and under what conditions. **Permission policies**: what actions the role can perform. These are different security questions.

Do not assume `Principal` is always a dictionary or that `Action` is always a string; future analysis should handle AWS policy variants without dropping conditions.

## 6. Extraction versus normalization

First implementation:

```python
normalized_roles = {}
normalized_roles["role_name"] = role["RoleName"]
normalized_roles["trust_statements"] = role["AssumeRolePolicyDocument"]["Statement"]
return normalized_roles
```

This extracts selected fields but does **not** fully normalize actions, principals or conditions. The user questioned why to duplicate all fields when raw roles are already retained. Decision: keep normalized output **lean** and add the role ARN as a stable identity useful for later correlation.

Current design pattern:

```python
def normalize_role_trust_policy(role):
    normalized_role = {}
    normalized_role["role_name"] = role["RoleName"]
    normalized_role["role_arn"] = role["Arn"]
    statements = role["AssumeRolePolicyDocument"]["Statement"]
    if isinstance(statements, dict):
        statements = [statements]
    normalized_role["trust_statements"] = statements
    return normalized_role
```

Why `isinstance(statements, dict)`? When a single statement is represented as a dictionary, wrap it in `[statements]`. When already a list, preserve it. **Contract:** `trust_statements` is always a list for supported input shapes. That simplifies later iteration and avoids two separate code paths in analyzers.

**Mutability caveat:** In the list case, `normalized_role["trust_statements"]` refers to the same list object as the raw role's `Statement`; this is not a deep copy. If later code mutates a statement, it could change both representations. The current module reads this data; if transformations start mutating it, consider copying or constructing new records.

**Missing-key caveat:** Direct `[...]` indexing raises `KeyError` if the required field is absent. The module has not implemented a comprehensive schema-validation layer. Tests and future collectors should distinguish required fields from genuinely optional ones.

## 7. Orchestration: raw and normalized roles

Existing `collect_aws_iam_inventory(iam)` was extended with:

```python
iam_roles = list_iam_roles(iam)
normalized_roles = []
for role in iam_roles:
    normalized_roles.append(normalize_role_trust_policy(role))
iam_inventory["roles"] = iam_roles
iam_inventory["normalized_roles"] = normalized_roles
```

The user originally wrote `normalized_roles.extend([normalize_role_trust_policy(role)])`, which works because it extends by a one-element list, but `append(normalize_role_trust_policy(role))` is simpler and expresses the intention: one normalized dict per role.

Final inventory contract:

```python
{
    "users": [...],
    "access_keys": [...],
    "normalized_keys": [...],
    "roles": [...],
    "normalized_roles": [...],
}
```

The raw/normalized separation makes it possible to retain AWS response context while providing smaller records for downstream analysis. Empty lists are valid outcomes. An exception must propagate rather than returning a falsely complete inventory.

## 8. Tests and evidence

The user updated the Module 03 inventory tests to mock `list_iam_roles` and expect the two new keys, preserving previous user/key scenarios. The uploaded `test_aws_inventory.py` included tests for empty inventory, multiple users and keys, users with no keys, and parametrized failures for the older collectors. It did not originally include `list_iam_roles` in that parametrized failure list.

A separate `test_iam_roles.py` was supplied for Module 04-specific coverage. **User reported all seven tests passed** on 2026-11-12. The planned cases included role pagination, empty responses, trust-statement shapes, failure propagation, and integration. This journal records the reported result; it does not claim an independent audit of the entire codebase or exhaustive coverage.

Useful regression commands:

```powershell
python -m pytest tests/test_iam_roles.py -v
python -m pytest tests/test_aws_inventory.py -v
python -m pytest -v
```

Follow-up tests before production readiness: unusual/malformed trust-policy shapes, missing fields, IAM permissions errors, multi-account identity, and all previously deferred Module 02 collector failures. Validate actual full-suite results rather than assuming all suites passed because one suite did.

## 9. Questions answered and engineering reasoning

1. **Why use a list rather than a dictionary keyed by role name?** Consistency with collectors and preservation of future multi-account role identity; index only when needed.
2. **Why did 260 appear when only 34 roles exist?** `extend(dict)` adds keys; the list's element type revealed the bug.
3. **Why can we remove the inner `for role` loop?** `extend(page["Roles"])` itself iterates the list of role dictionaries.
4. **Are `append(role)` and `extend([role])` equivalent?** They produce the same one-element addition, but `append` communicates intent more clearly.
5. **What does `pprint` do?** Formats nested structures for inspection without modifying values.
6. **Why not just use `statements[0]`?** It ignores additional statements; policy evaluation must consider all.
7. **Why normalize if raw roles exist?** Provide a lean, predictable contract while retaining the full source record.
8. **Why add ARN?** Distinguish resources and support future correlation; RoleName alone is not a cross-account identifier.
9. **Why wrap dict statements in a list?** One downstream iteration path regardless of source shape.
10. **Does wrapping statements mean complete trust-policy normalization?** No: principal/action/condition semantics remain unparsed.
11. **Why keep error propagation?** A partial scan should not be mistaken for a successful full inventory.
12. **What do passing tests establish?** Evidence for tested cases, not all edge cases or production readiness.

## 10. Learning assessment at module close

**Improved:** Boto3 pagination; list-of-dictionaries reasoning; recognizing nested dictionary structures; using `type`, `len`, and `pprint` to debug; choosing raw vs normalized contracts; function boundaries; awareness of consistent schema and mutability.

**Needs more independent practice:** writing a new collector from requirements without a near-identical template; predicting `append`/`extend` behavior immediately; identifying malformed input and error scenarios; designing meaningful test cases independently. AWS security domain understanding is stronger than independent Python implementation skill, so next module should convert existing domain knowledge into code.

**Mentoring change for Module 05:** user proposes function contract and pseudocode, writes first production implementation, then receives targeted review. AI may write test scaffolding. Do not prematurely generate a complete collector.

## 11. Deferred tasks and next module

- Module 05: IAM permission relationships (attached role policies, inline role policies, relevant managed-policy documents/versions). Agree on the minimum scope before coding.
- Later analyzer: distinguish trust (who can assume) from permissions (what can be done), then evaluate risks with evidence.
- Deferred: GCP, multicloud model, remediation, AI, CI/CD, deployment.
- Commit this journal and updated plan, verify full suite, and link documentation from README.

**Next file:** `docs/05-module-starter.md`.
