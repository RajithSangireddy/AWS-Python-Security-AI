# Module 02 — AWS IAM Collector

**Project:** Cloud Security Automation Platform  
**Module:** 02 — IAM Collector  
**Status:** Core implementation completed; initial tests passing; additional failure-path tests deferred  
**Updated:** November 10, 2026

> This is a learning journal as well as a technical record. Code fragments illustrate concepts and may not exactly match the latest local repository. The repository source remains authoritative.

## 1. Goals and scope

Build a read-only Python/Boto3 AWS IAM collector that retrieves IAM users, their access keys, and last-used metadata; normalizes results; handles AWS errors without silently returning incomplete inventory; and provides a foundation for later security analysis. Reuse the authenticated IAM client from Module 01 rather than creating new sessions inside each collector function.

### Learning objectives
- Work with Boto3 clients, paginators, API response shapes, lists and dictionaries.
- Design small functions with clear inputs and return values.
- Understand exception propagation and distinguish AWS service errors from SDK/transport failures.
- Understand object references, copies, merging records, and dependency injection.
- Write pytest tests with Botocore `Stubber` without calling real AWS.
- Decide what belongs in collection, normalization, orchestration, analysis, and reporting layers.

## 2. Implementation and data flow

### Current workflow

```text
main.py
  |
  +-- create_aws_session("security-audit")  [Module 01]
  |     +-- session.client("iam")
  |
  +-- list_iam_users(iam)
  |     +-- paginator("list_users") -> list of user dictionaries
  |
  +-- for each user: list_user_access_keys(iam, username)
  |     +-- paginator("list_access_keys") -> list of access-key dictionaries
  |
  +-- for each access key: get_access_key_usage(iam, access_key_id)
  |     +-- get_access_key_last_used -> dictionary of usage attributes
  |
  +-- copy key metadata, update copy with usage, normalize_access_key(...)
  |     +-- normalized_keys: list of normalized dictionaries
  |
  +-- later: analyzer and reporter
```

The AWS profile `security-audit` assumes a read-only audit role. Authentication and client creation occur outside the collector. Each collector accepts `iam` as a parameter. The same function can therefore receive a real IAM client or a client intercepted by Stubber in tests.

### Representative orchestration (conceptual)

```python
session = create_aws_session("security-audit")
iam = session.client("iam")

users = list_iam_users(iam)
access_keys = []
normalized_keys = []

for user in users:
    access_keys.extend(list_user_access_keys(iam, user["UserName"]))

for key in access_keys:
    access_key_id = key["AccessKeyId"]
    enriched = key.copy()
    enriched.update(get_access_key_usage(iam, access_key_id))
    normalized_keys.append(normalize_access_key(enriched))
```

This code currently lives in `main.py`. We decided to move provider-specific orchestration into an `aws_inventory.py` function in the next module, keeping `main.py` a small entry point. Later a GCP inventory function and a multicloud coordinator can use a common inventory/findings model. **No restructuring is required to finish Module 02.**

## 3. Core collector functions

### `list_iam_users(iam)`
- Uses `iam.get_paginator("list_users")` and `.paginate()`.
- Each page is a **dictionary** with a `"Users"` field containing a **list** of user dictionaries.
- Appends or extends user records across pages into one list.
- Returns `[]` when no IAM users exist: a valid inventory result, not an exception.
- An API failure during pagination raises rather than returning a partial inventory.

```python
users = []
for page in iam.get_paginator("list_users").paginate():
    for user in page["Users"]:
        users.append(user)
return users
```

### `list_user_access_keys(iam, username)`
- Uses `iam.get_paginator("list_access_keys").paginate(UserName=username)`.
- Reads `page["AccessKeyMetadata"]` and accumulates access-key dictionaries.
- Returns `[]` if the user has no access keys.
- Do not log full access-key identifiers unnecessarily; never log secret access keys.

### `get_access_key_usage(iam, access_key_id)`
- Calls `iam.get_access_key_last_used(AccessKeyId=access_key_id)`.
- Reads `response["AccessKeyLastUsed"]`.
- Returns **one dictionary** with `last_used_at`, `last_used_service`, `last_used_region`.
- Converts AWS `"N/A"` values for service/region into Python `None`.
- A missing/unknown last-used timestamp does **not** prove a key is safe to delete.

```python
usage = response["AccessKeyLastUsed"]
service = usage.get("ServiceName")
normalized_service = None if service == "N/A" else service
```

### `normalize_access_key(key)`
- Takes a dictionary already enriched with usage details.
- Produces consistent field names: `username`, `access_key_id`, `status`, `created_at`, `last_used_at`, `last_used_service`, `last_used_region`.
- Should be a pure transformation; it does **not** need an IAM client or AWS API call.
- Keep `datetime` objects as dates/timestamps internally; serialize later at the reporting boundary.

## 4. Questions and design decisions: lists, dictionaries, and indexing

### Q: Why lists for IAM users and access keys, but a dictionary for last-used details?

**Answer:** A list holds **multiple records**; each record is a dictionary of named attributes. A usage lookup returns attributes for **one specified access key**, so a dictionary is natural.

```python
users = [
    {"UserName": "alice", "UserId": "A123"},
    {"UserName": "bob", "UserId": "B456"},
]
usage = {
    "last_used_at": None,
    "last_used_service": "ec2",
    "last_used_region": "us-east-1",
}
```

A list of positional usage values, e.g. `[None, "ec2", "us-east-1"]`, would require callers to remember what each index means. Named dictionary fields are easier to read and maintain.

### Q: Why not use dictionaries for all three?

You *can* use a dictionary keyed by a unique identifier when fast lookup matters:

```python
users_by_name = {
    "alice": {"UserName": "alice", "UserId": "A123"},
    "bob": {"UserName": "bob", "UserId": "B456"},
}
user = users_by_name["alice"]
```

But the current collector mostly iterates through all records, so `list[dict]` is simple and preserves each record. A dictionary index is useful for repeated lookup and enforces one value per key; duplicate keys overwrite unless explicitly handled. In future multicloud collection, names alone are not globally unique: account/provider/resource identifiers matter.

### Q: Does Python automatically use the first field, such as `UserName`, as the dictionary key?

**No.** You explicitly select the index key:

```python
users_by_name = {}
for user in users:
    users_by_name[user["UserName"]] = user
```

Contrast this with `.update()`:

```python
combined = {}
for user in users:
    combined.update(user)
```

That merges each user's **fields** into one dictionary, overwriting repeated field names (`UserName`, `UserId`) and losing separate user records. `append()` adds one item to a list; `extend()` adds each item from another iterable; `dict.update()` merges key-value pairs.

### Q: What about IAM roles?

For collecting 50 roles, use `list[dict]` by default. If repeated instant lookup by unique role name is needed, create a dictionary keyed by role name. Role names are unique within an AWS account, **not** across all accounts; use an account-aware identifier for aggregated inventory.

## 5. Questions and design decisions: correlating access-key usage

### Q: How does the last-used information map back to the correct access key?

The `get_access_key_usage()` function returns attributes, but does not independently return the access key ID. The caller knows the ID because it passed that ID into the API call. In `main.py`, the loop retrieves usage for the current key, copies that key's metadata, and merges the usage dictionary into that copy:

```python
for key in access_keys:
    key_id = key["AccessKeyId"]
    key_with_usage = key.copy()
    key_with_usage.update(get_access_key_usage(iam, key_id))
    normalized_keys.append(normalize_access_key(key_with_usage))
```

The resulting normalized list contains **self-contained access-key records**. If usage records were stored independently for later correlation, they would need to be keyed by `AccessKeyId` or include that ID explicitly.

### Q: Why `.copy()` before `.update()`?

`for key in access_keys` binds `key` to an existing dictionary object in the list. Mutating `key` directly would also change the dictionary held in the original list. `key.copy()` creates a shallow copy so top-level enrichment leaves the raw record unchanged. Shallow copies do not recursively copy nested mutable objects.

### Q: Should `main.py` handle correlation forever?

No. Current orchestration in `main.py` is acceptable for learning, but a separate provider inventory function will be easier to test and maintain. Proposed direction:

```text
main.py -> multicloud coordinator (eventually)
                   |-- AWS inventory orchestrator -> AWS collector functions
                   |-- GCP inventory orchestrator -> GCP collector functions
          -> common model -> analysis -> reporting
```

We chose a function first, not a class, until state or shared behavior justifies a class.

## 6. Questions and design decisions: exceptions and completeness

### Q: Why separate `ClientError` and `BotoCoreError`?

- `ClientError` generally represents an AWS service error response, such as `AccessDenied`.
- `BotoCoreError` covers client-side SDK failures, including certain endpoint/connection errors, **but is broader than network failure**.
- The common `error_handler.py` reads `error.response["Error"]["Code"]` and `["Message"]`, which is appropriate for `ClientError`, **not** generic `BotoCoreError`.
- Use a broader message such as `"AWS SDK error"` rather than asserting every `BotoCoreError` is a network failure.

```python
except ClientError as error:
    error_handler(error, "list_users")
except BotoCoreError as error:
    raise RuntimeError(f"AWS SDK error: {error}") from error
```

The `error_handler()` itself raises `RuntimeError`, chaining the original exception using `from error`; it does not need a `return` statement. An exception raised inside an `except ClientError` handler is not then caught by a sibling `except BotoCoreError` block. Other exceptions, including some credential/configuration errors, may require separate handling at the appropriate layer; avoid claiming all failures are covered without testing them.

### Q: Why initialize `users = []`, `iam_keys = []`, or `last_used_details = {}` before `try`?

This can make the function's structure and intended return value clearer. **It does not make collection transactional and is not required for correctness when every caught failure is re-raised.** Lists are populated immediately on `.append()` whether initialized inside or outside `try`.

### Q: If page 3 fails after pages 1 and 2 were appended, does the caller receive those records?

No. The local list has accumulated earlier records, but the raised exception prevents the function's normal `return` from executing. The caller receives the exception, **not an empty list or a partial list**. If the caller had previously stored some data elsewhere, that state is separate and may still exist.

### Q: What if collecting access keys for the 75th of 100 users fails?

Fail the **entire inventory operation** instead of presenting 74 users' keys as complete. A retry should begin a fresh collection. Do not assume stable ordering across independent scans or blindly merge partial snapshots; reconciliation and deduplication would require deliberate identifiers and completeness metadata. AWS paginator markers manage continuation *within* a scan; they are not a general cross-scan reconciliation mechanism.

### Q: What about zero users or zero access keys?

Valid empty results return `[]`; they are not AWS errors. The caller/reporting layer decides how to display a no-results message.

## 7. Python environment and Interactive Window troubleshooting

The VS Code Interactive Window initially ran with the working directory set to `.../AWS-Python-Security-AI/src`, while `main.py` and the package import root were in `.../AWS-Python-Security-AI`. The `.venv` interpreter itself was correct.

Diagnostic:

```python
import os, sys
print(os.getcwd())
print(sys.executable)
print(sys.path)
```

Fix: set the Jupyter notebook file root to the workspace root. The project uses a `.code-workspace` file, so put the setting there rather than changing it globally:

```json
{
  "folders": [{"path": "."}],
  "settings": {
    "jupyter.notebookFileRoot": "${workspaceFolder}"
  }
}
```

Merge this setting into the existing workspace JSON; do not overwrite unrelated settings. Restore the global user setting to its default. Select the project-local `.venv` interpreter independently. Restart the Interactive Window kernel after configuration changes. Avoid hardcoded `sys.path` hacks.

The user used `# %%` cells for interactive experimentation. Keep experiments in a scratchpad or dedicated cells; use `pytest` for reproducible automated tests. `.venv`, caches, and credentials should be excluded from Git.

## 8. Testing architecture: pytest and Botocore Stubber

### Q: Why create an IAM client with dummy credentials?

The collector accepts an IAM **client** parameter, not a session. Tests create a client without using the personal AWS profile:

```python
import boto3
from botocore.stub import Stubber
from src.collector import list_iam_users

iam = boto3.client(
    "iam",
    region_name="us-east-1",
    aws_access_key_id="testing",
    aws_secret_access_key="testing",
)
stubber = Stubber(iam)
```

Dummy credentials alone **do not** prevent network calls. Stubber intercepts calls on this **specific IAM client object** while active. In production, `main.py` passes the real IAM client; in tests, `test_collector.py` passes the test client. `collector.py` uses the argument supplied by its caller. This is **dependency injection** and ordinary Python parameter passing—not variable-name precedence.

### Q: What is the difference between `print`, `if`, and `assert` in a test?

`print(len(result))` displays a value but doesn't make pytest fail on mismatch. `assert len(result) == 2` raises `AssertionError` when false; pytest reports pass/fail. A test is typically a function named `test_...`, discovered automatically by pytest.

```python
assert len(result) == 2
assert result[0]["UserName"] == "alice"
```

### Q: Why is the fake response a dictionary with a `"Users"` list?

AWS `ListUsers` defines a response object with a `Users` member containing a list. The paginator returns each API page in that shape; the collector accesses `page["Users"]`. The paginator does not invent the `Users` field.

```python
from datetime import datetime, timezone
created_at = datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc)

fake_response = {
    "Users": [{
        "UserName": "alice",
        "UserId": "AIDA1234567890123456",
        "Arn": "arn:aws:iam::123456789012:user/alice",
        "Path": "/",
        "CreateDate": created_at,
    }],
    "IsTruncated": False,
}
```

Fixed timestamps are preferable to changing `today()` values in deterministic unit tests. A real `datetime` object is accepted for the modeled timestamp field. The initial test failed with `ParamValidationError` because fake `UserId` values such as `"1234"` were shorter than the AWS service model's minimum length of 16 characters; longer synthetic IDs fixed it. Stubber validates response shapes/types and request parameters.

### Q: How do `add_response`, the paginator, and Stubber interact?

```python
stubber.add_response("list_users", fake_response, {})
with stubber:
    result = list_iam_users(iam)
```

`list_iam_users` invokes the paginator; the paginator invokes the IAM API; Stubber intercepts that API call and supplies the queued response. The collector is unaware of Stubber. `add_response(operation, response, expected_params)` means: expect this operation and parameters, then return this fake response. `with stubber:` activates interception and deactivates it afterward.

### Q: For two pages, do we register one or two Stubber responses?

**Two.** The paginator makes a separate API call for each page; Stubber must be given one queued response per expected call.

```python
page1 = {"Users": [alice, bob], "IsTruncated": True, "Marker": "next-page-token"}
page2 = {"Users": [charlie, delta], "IsTruncated": False}

stubber.add_response("list_users", page1, {})
stubber.add_response("list_users", page2, {"Marker": "next-page-token"})

with stubber:
    result = list_iam_users(iam)

stubber.assert_no_pending_responses()
assert len(result) == 4
assert result[2]["UserName"] == "charlie"
```

Here `alice`, `bob`, `charlie`, and `delta` stand for complete, valid IAM user dictionaries (including the required modeled fields). The first page's response marker is sent as the second request's `Marker` parameter. Stubber validates exact request parameters.

### Experiment: deliberately mismatched markers

Changing the second expected request marker from `"next-page-token"` to `"next-token"` produced `StubAssertionError`: expected and actual request parameters did not match. This checks API request correctness, not the returned inventory count.

### Experiment: stop after Page 1

Changing Page 1 to `"IsTruncated": False` caused the paginator to stop after Alice and Bob. The second stubbed response remained unused, and `stubber.assert_no_pending_responses()` raised `AssertionError: 1 responses remaining in queue.` Restore Page 1 to `IsTruncated=True` afterward.

### Q: What do our test assertions verify?

- `assert len(result) == 4`: returned inventory contains all expected records.
- Stubber `expected_params`: each API call sends expected arguments (including continuation marker).
- `stubber.assert_no_pending_responses()`: every queued fake response was consumed; it does **not** independently prove inventory completeness.

### Q: How does a test verify expected `AccessDenied`?

Use `stubber.add_client_error(...)` rather than `add_response(...)` to simulate AWS `ClientError`. The collector should transform it into `RuntimeError`. A pytest test that **expects** this exception should pass when it occurs (e.g. via `pytest.raises(RuntimeError)`). **This test was discussed but not implemented in this module.**

## 9. Verified test results and deferred work

Three tests were run successfully in `tests/test_collector.py`:

| Test | Purpose | Verified result |
|---|---|---|
| `test_list_iam_users_success` | Two valid IAM users | PASS |
| `test_list_iam_users_empty` | Empty `Users` list | PASS |
| `test_list_iam_users_pagination` | Two pages, four users, continuation marker | PASS |

Command:

```powershell
python -m pytest tests/test_collector.py -v
```

The user also deliberately produced failing tests to observe Stubber's validation. After those experiments, restore the passing marker and `IsTruncated=True` settings and rerun before committing.

**Deferred tests / quality checks:**
- AWS `AccessDenied` / `ClientError` -> expected `RuntimeError`.
- SDK/endpoint failure handling (and exception coverage).
- No access keys for a user.
- Access-key pagination.
- Last-used response with missing fields / `"N/A"`.
- Multi-user aggregation, normalization, and full orchestration failure propagation.
- Cleanup of debug prints and review of logs/error messages.

Deferring these is an intentional learning-scope decision, **not** a claim that all error paths are tested.

## 10. Design principles to carry forward

1. **Choose data structures for usage patterns.** Lists for multiple records; dictionaries for named attributes and fast keyed lookup; sets later for membership/uniqueness.
2. **Keep raw collection separate from normalization and analysis.** Avoid making the collector determine security findings.
3. **Pass dependencies explicitly.** An IAM client parameter makes real and stubbed execution use the same function.
4. **Fail closed on incomplete inventories.** Raise on API errors; never silently present partial scans as complete.
5. **Keep records self-contained.** Correlate usage with metadata using the access key ID before normalization.
6. **Use deterministic tests.** Fixed timestamps, synthetic valid API data, no real credentials, no live AWS calls.
7. **Test observable behavior.** Verify output, expected API parameters, and consumed responses.
8. **Refactor after functionality works.** Next module: provider-specific AWS inventory orchestrator; later GCP and multicloud coordination.

## 11. Module boundary and next chat

**Module 02 stays in this conversation.** Start **Module 03 — AWS Inventory Orchestration** in a new chat. Begin by moving coordination from `main.py` into a function (tentative `collect_aws_iam_inventory(iam)`), choosing an extensible return shape for IAM users, normalized keys, and future roles/policies. Avoid a class unless needed. Keep learning incremental: design, pseudocode, small exercises, tests, and review of user-written code rather than full implementations by default.

## 12. Git checklist

Before committing:

```powershell
python -m pytest tests/test_collector.py -v
git status
git diff --check
git add src/collector.py src/error_handler.py tests/test_collector.py docs/02-IAM-Collector-Learning-Journal.md
git commit -m "Complete IAM collector and document Module 02 learning"
git push origin HEAD
```

Adjust the `git add` paths to include any other intentionally changed source, `.gitignore`, or `requirements.txt` files after reviewing `git status`. Do **not** commit `.venv`, secrets, AWS credentials, or unrelated scratch files. The Git push must be executed in the user's local repository; generating this journal does not push it automatically.

## 13. AWS API response samples and Python data-structure walkthroughs

> **All identities, dates, tokens, and key IDs below are synthetic learning examples, not real AWS data.** API responses are abbreviated to highlight their shape. Actual Boto3 responses may contain additional fields (such as `ResponseMetadata`); Stubber tests may require schema-valid values. These examples describe the data flow, not full implementations.

### Example A — `list_users`: outer dictionary, inner list of dictionaries

```python
page = {
    "Users": [
        {"UserName": "alice", "UserId": "AIDAEXAMPLE000001", "Arn": "arn:aws:iam::123456789012:user/alice"},
        {"UserName": "bob", "UserId": "AIDAEXAMPLE000002", "Arn": "arn:aws:iam::123456789012:user/bob"},
    ],
    "IsTruncated": False,
}

# Types: page -> dict; page["Users"] -> list; page["Users"][0] -> dict
users = []
for user in page["Users"]:
    users.append(user)

print(users[0]["UserName"])  # alice
```

**Why:** AWS returns a response dictionary with a `Users` collection. We accumulate user *records* in a list. `users.append(user)` adds a whole dictionary as one element; `users.extend(page["Users"])` is another valid way to add all users in the page. `users.update(...)` does not work because `list` has no `update` method. Using a single dictionary's `.update(user)` repeatedly would overwrite fields like `UserName` rather than retain separate users.

### Example B — Two paginator pages and the continuation marker

```python
page1 = {
    "Users": [{"UserName": "alice"}, {"UserName": "bob"}],
    "IsTruncated": True,
    "Marker": "next-page-token",
}
page2 = {
    "Users": [{"UserName": "charlie"}],
    "IsTruncated": False,
}

users = []
for page in (page1, page2):  # Illustration only: production uses Boto3 paginator
    users.extend(page["Users"])

print([u["UserName"] for u in users])  # ['alice', 'bob', 'charlie']
```

**Why:** Each page is a dictionary, each `Users` value is a list, and the final inventory is a single accumulated list. In a real paginator, Boto3 follows `IsTruncated`/`Marker` and makes the subsequent API request. The marker is not a user attribute. In Stubber, the second response must be registered with expected parameters `{"Marker": "next-page-token"}` when that is the first page's marker.

### Example C — `list_access_keys`: list of key metadata dictionaries

```python
response = {
    "AccessKeyMetadata": [
        {
            "UserName": "alice",
            "AccessKeyId": "AKIAEXAMPLE00000001",
            "Status": "Active",
            "CreateDate": "2026-01-15T10:30:00Z",  # Readable illustration; Boto3 uses datetime
        },
        {
            "UserName": "alice",
            "AccessKeyId": "AKIAEXAMPLE00000002",
            "Status": "Inactive",
            "CreateDate": "2025-06-10T08:00:00Z",
        },
    ],
    "IsTruncated": False,
}

keys = []
keys.extend(response["AccessKeyMetadata"])
print(len(keys))                   # 2
print(keys[1]["Status"])          # Inactive
```

**Why:** One IAM user can have multiple keys. A list keeps those as distinct records. Each key dictionary stores fields describing *that key*. The real Boto3 `CreateDate` is a `datetime` object, which must be serialized explicitly when writing JSON.

### Example D — `get_access_key_last_used`: nested AWS response to flat usage dictionary

```python
aws_response = {
    "UserName": "alice",
    "AccessKeyLastUsed": {
        "LastUsedDate": "2026-10-01T12:00:00Z",  # Boto3 normally returns datetime
        "ServiceName": "s3",
        "Region": "us-east-1",
    },
}

last_used = aws_response["AccessKeyLastUsed"]
usage = {
    "last_used_at": last_used.get("LastUsedDate"),
    "last_used_service": None if last_used.get("ServiceName") == "N/A" else last_used.get("ServiceName"),
    "last_used_region": None if last_used.get("Region") == "N/A" else last_used.get("Region"),
}
```

**Why:** The AWS API's nested `AccessKeyLastUsed` dictionary becomes a flat, application-defined dictionary with predictable names. For never-used keys, AWS may omit `LastUsedDate` and return `"N/A"` for service/region; our normalized values use `None`. This usage dictionary describes one requested key, not a collection of all keys.

### Example E — Merge metadata and usage without changing the original

```python
key = {
    "UserName": "alice",
    "AccessKeyId": "AKIAEXAMPLE00000001",
    "Status": "Active",
}
usage = {
    "last_used_at": None,
    "last_used_service": None,
    "last_used_region": None,
}

combined = key.copy()  # Shallow copy: new outer dictionary
combined.update(usage)

print(key)       # Still only the original three fields
print(combined)  # Original three fields plus three usage fields
```

**Why:** `.copy()` prevents adding usage fields directly to the original metadata dictionary. `.update()` is appropriate here because we want *one* record containing different named attributes. If both dictionaries contain the same key, the value from `usage` replaces the value in `combined`. A shallow copy does not recursively clone nested objects.

### Example F — Normalized access-key record: one dictionary; inventory: list of dictionaries

```python
normalized_key = {
    "username": "alice",
    "access_key_id": "AKIAEXAMPLE00000001",
    "status": "Active",
    "created_at": "2026-01-15T10:30:00Z",
    "last_used_at": None,
    "last_used_service": None,
    "last_used_region": None,
}

normalized_keys = []
normalized_keys.append(normalized_key)
print(normalized_keys[0]["access_key_id"])  # AKIAEXAMPLE00000001
```

**Why:** `normalize_access_key` transforms AWS field names such as `AccessKeyId` into our stable schema such as `access_key_id`. The function returns one dictionary for one key; the caller appends that record to a list of all normalized keys. Dates are strings in this *illustration* for readability; our current collector retains Boto3 date values unless explicitly serialized.

### Example G — Explicitly build a dictionary indexed by username

```python
users = [
    {"UserName": "alice", "UserId": "AIDAEXAMPLE000001"},
    {"UserName": "bob", "UserId": "AIDAEXAMPLE000002"},
]
users_by_name = {}
for user in users:
    users_by_name[user["UserName"]] = user

print(users_by_name["bob"]["UserId"])  # AIDAEXAMPLE000002
```

**Why:** A dictionary lookup by username is useful if we repeatedly search for a specific user. Python does **not** infer the key from the first field; we create the mapping ourselves. For future multi-account data, the same username can occur in different AWS accounts, so account ID must be considered in lookup keys.

### Example H — Stubber: fake response, request parameters, and pagination assertions

```python
# Abbreviated teaching example: schema-valid full user records are required in actual tests.
stubber.add_response("list_users", page1, {})
stubber.add_response("list_users", page2, {"Marker": "next-page-token"})
with stubber:
    result = list_iam_users(iam)
stubber.assert_no_pending_responses()
assert len(result) == 3
```

**Why:** Each `add_response` queues one fake service response for the *same* injected IAM client. The first paginator call has no marker; the second sends the marker from page 1. `assert_no_pending_responses()` confirms every queued response was consumed. If page 1 says `IsTruncated=False`, page 2 remains unused and the assertion fails. If the expected marker differs from the actual request, Stubber raises a parameter-mismatch error. This is a *conceptual* example: use the schema-valid response objects from `tests/test_collector.py` when running it.

### Example I — Expected AWS error: successful negative test

```python
# Example to implement later; not among the three verified passing tests.
stubber.add_client_error(
    "list_users",
    service_error_code="AccessDenied",
    service_message="Not authorized to call iam:ListUsers",
)
with stubber:
    with pytest.raises(RuntimeError, match="AccessDenied"):
        list_iam_users(iam)
```

**Why:** The simulated AWS API raises `ClientError`; the collector wraps it as `RuntimeError`. The test **passes** if the expected exception occurs, because rejecting an unauthorized operation is the intended behavior. `pytest` must be imported. This is a deferred test example, not a verified result.

### Example J — Incomplete pagination must not look like a complete inventory

```text
Page 1 -> 2 users collected locally
Page 2 -> 2 more users collected locally
Page 3 -> AWS ClientError
         -> error_handler raises RuntimeError
         -> list_iam_users does not return its local list
```

**Why:** `append` and `extend` modify the local list as each page arrives, but an uncaught propagated exception stops execution before the final `return users`. The caller does not receive a successful partial result. If a higher-level orchestration layer wants partial-results behavior later, it must define that explicitly, including how incompleteness is represented.

### Quick reference: which structure did we choose?

| Data | Python shape | Why |
|---|---|---|
| Single Boto3 API page | `dict` | Named response fields and metadata |
| Page's `Users` | `list[dict]` | Multiple user records |
| All collected users | `list[dict]` | Accumulated records across pages |
| One access-key metadata record | `dict` | Named fields for one key |
| All access keys | `list[dict]` | Multiple keys per user / across users |
| One key's usage details | `dict` | One set of named usage attributes |
| Combined/normalized key | `dict` | One cohesive key record |
| All normalized keys | `list[dict]` | Collection of normalized records |
| Optional username lookup index | `dict[str, dict]` | Explicit key-based lookup when needed |

**Review questions:** Why is `page["Users"]` a list? When would `.extend()` replace `.append()`? Why does `.update()` make sense for merging one key's metadata with usage but not for accumulating multiple users? What happens if page 3 fails? Why does the Stubber's second request include `Marker`?

