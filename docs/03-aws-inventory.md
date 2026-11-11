# Module 03 — AWS IAM Inventory Orchestration

**Project:** Cloud Security Automation Platform  
**Module:** 03  
**Status:** Application logic implemented and live AWS integration checked; automated tests supplied for local execution  
**Next module:** 04 — IAM roles and trust policies

> This journal consolidates the Module 03 design and learning discussions available in our project conversation, including representative code, questions, mistakes, corrections, and testing explanations. It is a detailed reconstruction, not a verbatim transcript. The tests included with this journal have not been executed against your local repository here.

## 1. Why this module exists

Modules 01 and 02 established the AWS session and individual IAM collection functions. Originally, `main.py` was responsible for the loops that fetched users, fetched their keys, enriched keys with usage, and normalized records. Module 03 moves that coordination into a dedicated orchestration function, so `main.py` becomes a simple entry point.

**Separation of responsibilities:**

| File | Responsibility |
| --- | --- |
| `src/auth.py` | Create a Boto3 session using the configured AWS profile; validate caller identity |
| `src/collector.py` | Make individual IAM API calls, paginate, and normalize access-key records |
| `src/error_handler.py` | Translate AWS/network errors into application-level failures |
| `src/aws_inventory.py` | Coordinate collectors and assemble a consistent inventory |
| `main.py` | Initialize the session and IAM client, then call the orchestrator |
| `tests/test_aws_inventory.py` | Verify orchestration behavior without calling AWS |

The AWS session is reused rather than creating a new session in each collector. The `security-audit` profile assumes a read-only audit role.

## 2. Design requirements and decisions

### 2.1 Inventory contract

We chose a **dictionary containing three lists**, even if some lists are empty:

```python
{
    "users": [...],
    "access_keys": [...],
    "normalized_keys": [...],
}
```

- `users`: original IAM user dictionaries.
- `access_keys`: original IAM access-key metadata dictionaries.
- `normalized_keys`: access keys enriched with usage and transformed to a consistent field schema.

**Discussion:** Why keep both raw and normalized keys? The user preferred preserving raw AWS records for future workflows and troubleshooting, while normalized records are suitable for a later `analyzer.py`. This duplicates some data but makes both uses explicit. We accepted that trade-off for the initial project.

**Discussion:** Why return all three keys even if the account has no users? A predictable return contract makes downstream consumers simpler: they can iterate `inventory["normalized_keys"]` without first checking whether the key exists.

### 2.2 Collection order

1. Fetch all IAM users once.
2. For each user, fetch their access keys.
3. Combine all returned access-key lists into one flat list.
4. For each key, fetch usage information.
5. Copy the raw key dictionary, merge usage into the copy, normalize it, and append the result.
6. Return all three collections.

### 2.3 Failure policy

If a collector raises an exception, the orchestration function currently **propagates the error**. It does not silently return a partially completed inventory. This is a deliberate first-version policy: callers should not mistake incomplete results for a complete audit.

## 3. Current implementation — representative code

The following matches the orchestration design discussed in this module; compare against your current repository before replacing any code.

```python
from src.collector import (
    list_iam_users,
    list_user_access_keys,
    get_access_key_usage,
    normalize_access_key,
)


def collect_aws_iam_inventory(iam):
    iam_inventory = {}
    iam_users = list_iam_users(iam)

    iam_access_keys = []
    for user in iam_users:
        username = user["UserName"]
        iam_access_keys.extend(list_user_access_keys(iam, username))

    normalized_keys = []
    for key in iam_access_keys:
        access_key_id = key["AccessKeyId"]
        key_with_usage = key.copy()
        key_with_usage.update(get_access_key_usage(iam, access_key_id))
        normalized_keys.append(normalize_access_key(key_with_usage))

    iam_inventory["users"] = iam_users
    iam_inventory["access_keys"] = iam_access_keys
    iam_inventory["normalized_keys"] = normalized_keys
    return iam_inventory
```

**`main.py` integration:**

```python
from src.auth import create_aws_session
from src.aws_inventory import collect_aws_iam_inventory

session = create_aws_session("security-audit")
iam = session.client("iam")
iam_inventory = collect_aws_iam_inventory(iam)
```

Remove any unused imports or temporary debugging output once the integration is verified.

## 4. Python learning discussions and examples

### 4.1 `append()` versus `extend()`

**Question:** When a collector returns a list of keys for each user, how do we create one flat collection?

```python
all_keys = []
new_keys = [{"AccessKeyId": "KEY1"}, {"AccessKeyId": "KEY2"}]

all_keys.append(new_keys)
# [[{"AccessKeyId": "KEY1"}, {"AccessKeyId": "KEY2"}]]

all_keys = []
all_keys.extend(new_keys)
# [{"AccessKeyId": "KEY1"}, {"AccessKeyId": "KEY2"}]
```

`append()` adds one object, even if that object is a list. `extend()` iterates the supplied iterable and adds each element. For a flat IAM key inventory, use `extend()`.

### 4.2 `copy()` and `update()` — enriching access-key data

**Question:** How can we combine AWS access-key metadata with last-used details without changing the original metadata?

`list_user_access_keys()` provides `UserName`, `AccessKeyId`, `Status`, and `CreateDate`. The `get_access_key_usage()` function supplies `last_used_at`, `last_used_service`, and `last_used_region`. We want those usage fields in the **same enriched dictionary** while retaining the original record in `iam_inventory["access_keys"]`.

**Before enrichment — access-key metadata:**

```python
{
    "UserName": "alice",
    "AccessKeyId": "AKIAEXAMPLE00000001",
    "Status": "Active",
    "CreateDate": datetime.datetime(2023, 3, 22, 20, 1, 3, tzinfo=tzutc()),
}
```

**Our orchestration code:**

```python
access_key_id = key["AccessKeyId"]
key_with_usage = key.copy()
key_with_usage.update(get_access_key_usage(iam, access_key_id))
normalized_keys.append(normalize_access_key(key_with_usage))
```

**After `update()` — metadata plus usage fields:**

```python
{
    "UserName": "alice",
    "AccessKeyId": "AKIAEXAMPLE00000001",
    "Status": "Active",
    "CreateDate": datetime.datetime(2023, 3, 22, 20, 1, 3, tzinfo=tzutc()),
    "last_used_at": None,
    "last_used_service": None,
    "last_used_region": None,
}
```

The same example access-key ID is used before and after to show that **one record was enriched**, not replaced by another record. The `None` values illustrate missing last-used information in our normalized usage fields.

**What we learned:**

- `key.copy()` makes a **shallow copy** of the original dictionary. Updating the copy does not add fields to the original outer dictionary. Nested mutable objects would still be shared.
- `key_with_usage.update(usage)` adds the usage key-value pairs **in place**; if a field name already exists, the incoming value overwrites it.
- `dict.update()` returns `None`, not the updated dictionary. Do not write `key_with_usage = key_with_usage.update(usage)`.
- `update()` does **not** save to disk or a database. It changes the dictionary in memory.
- We retain raw AWS metadata in `iam_inventory["access_keys"]` and send the enriched copy through `normalize_access_key()` for `iam_inventory["normalized_keys"]`.

This copy-and-enrich pattern will also be useful when combining IAM roles, trust policies, and future security findings.

### 4.3 Fixing a naming/call mistake

An early draft accidentally used a list as if it were a function:

```python
normalized_keys.append(normalized_keys(key))  # incorrect
```

The intended operation was:

```python
normalized_keys.append(normalize_access_key(key_with_usage))
```

`normalized_keys` is the output **list**; `normalize_access_key` is the transformation **function**. Python names must clearly distinguish collections from callables.

### 4.4 Consistent schemas and downstream analysis

The normalized record uses consistent snake_case keys such as `access_key_id`. A basic check is:

```python
assert all("access_key_id" in key for key in inventory["normalized_keys"])
```

This validates presence of a field, not the full correctness of the record. More precise tests should check the exact expected fields and values.

### 4.5 What an assertion does — and does not do

An earlier validation included:

```python
assert len(inventory["users"]) >= 0
```

This is always true for any list and therefore provides no meaningful verification. Better checks include a known expected count, the existence of the three keys, or equality between raw and normalized key counts **when the current design requires one normalized record per raw key**.

Production code should not rely on temporary development assertions as its main validation strategy. Put stable expectations in tests; use explicit runtime checks for genuine input or invariant failures.

## 5. Live AWS integration results

A live AWS run using `collect_aws_iam_inventory(iam)` returned:

| Resource | Count |
| --- | ---: |
| IAM users | 4 |
| Raw access keys | 5 |
| Normalized access keys | 5 |

The terminal also printed individual usernames and an assumed-role ARN. Those details are intentionally omitted from this journal; the important facts are that role assumption worked and the orchestration produced the expected collection counts. Avoid committing account identifiers, real access-key IDs, or unnecessary identity output to GitHub.

**Interpretation:** This is a successful smoke/integration run, not proof of every edge case. The pytest suite addresses cases that are inconvenient to reproduce against a real AWS account.

## 6. Testing discussions — Stubber versus mock

### 6.1 Why the two tools felt different

In Module 02, `botocore.stub.Stubber` was used to simulate responses from a Boto3 IAM client. That is well suited to testing individual collector functions and their AWS API interactions.

In Module 03, the question changes: **does the orchestration function call the right collector functions and combine their outputs correctly?** For this, `unittest.mock.patch` replaces the imported collector functions with test-controlled substitutes.

| Tool | What it replaces | Good fit |
| --- | --- | --- |
| `Stubber` | AWS client responses | Individual Boto3 collectors |
| `patch` / `MagicMock` | Python functions or objects | Orchestration and function-to-function interactions |

### 6.2 The first mock-only exercise

```python
from unittest.mock import patch


def test_mock_iam_users():
    with patch("src.aws_inventory.list_iam_users") as mock_users:
        mock_users.return_value = [
            {"UserName": "alice"},
            {"UserName": "bob"},
        ]
        users = mock_users()
        assert len(users) == 2
        mock_users.assert_called_once()
```

**Important:** This proves the mock configuration works; it does **not** test `collect_aws_iam_inventory()`. The generated tests in `test_aws_inventory.py` actually invoke the orchestrator.

**Mistake discussed:** `mock_users.assert_called_once(list_iam_users(iam))` is not how the assertion works. Use `assert_called_once()` with no arguments, or `assert_called_once_with(iam)` when checking arguments. Do not call the original collector inside a mock assertion.

**Mistake discussed:** `from src.aws_inventory import all` is not a wildcard import. It is valid Python syntax but attempts to import a name literally called `all`, which is not the intended function. For the real test, use:

```python
from src.aws_inventory import collect_aws_iam_inventory
```

### 6.3 Python scope: `with` versus function

**Question:** Is `users = mock_users()` accessible outside the `with` block but inside the test function?

**Answer:** Yes. Python `with`, `if`, and `for` blocks do not create their own local scope. A function does.

```python
def example():
    with open("example.txt", "w") as handle:
        count = 5
    print(count)  # 5
```

`mock_users` also remains bound after its `with` block. However, **the patch is no longer active** after the block exits; the original function reference is restored.

**Jupyter/VS Code confusion:** Running `users = mock_users()` separately in an Interactive Window does not put that line inside the test function's scope. Local variables created during a test invocation are not global notebook variables. Run tests from the terminal with pytest.

### 6.4 Default mock return values

**Question:** If no `return_value` is configured, does `mock_users()` return `[]` or `None`?

**Answer:** Neither. A `MagicMock` normally returns another `MagicMock` when called.

```python
from unittest.mock import MagicMock

mock_users = MagicMock()
users = mock_users()
print(type(users))  # unittest.mock.MagicMock
```

| Configuration | Result |
| --- | --- |
| No explicit return value | Another `MagicMock` |
| `mock_users.return_value = []` | Empty list |
| `mock_users.return_value = None` | `None` |

An unconfigured `MagicMock` may iterate as if empty, causing an orchestration test to pass without exercising its loops. Explicit return values and call assertions prevent this false confidence.

### 6.5 Call counts and object identity

**Question:** If a mock is called twice with one configured list as its `return_value`, are there two calls and two separate lists?

```python
mock_users.return_value = [{"UserName": "alice"}, {"UserName": "bob"}]
users1 = mock_users()
users2 = mock_users()
```

There are **two calls** (`call_count == 2`), but both results reference **the same list**:

```python
assert users1 == users2
assert users1 is users2
assert id(users1) == id(users2)
```

`==` checks value equality; `is` checks object identity. A fixed `return_value` does not automatically create a fresh copy on every call.

### 6.6 `side_effect` for successive collector results

Our representative orchestration scenario has two IAM users: Alice owns two keys, Bob owns none. We expect:

| Function | Expected calls |
| --- | ---: |
| `list_iam_users` | 1 |
| `list_user_access_keys` | 2 |
| `get_access_key_usage` | 2 |
| `normalize_access_key` | 2 |

A `side_effect` list can return different results for consecutive calls:

```python
mock_keys.side_effect = [alice_keys, []]
```

First invocation returns Alice's keys; second returns Bob's empty list. The mock records calls so the test can verify that usernames were passed in the expected order.

### 6.7 Patching the name where it is used

Because `aws_inventory.py` imports functions directly:

```python
from src.collector import list_iam_users
```

The orchestrator looks up `list_iam_users` in **`src.aws_inventory`**. Therefore tests patch:

```python
patch("src.aws_inventory.list_iam_users")
```

Patching `src.collector.list_iam_users` after `aws_inventory` has imported it may not replace the reference that the orchestrator uses.

### 6.8 Test-import troubleshooting

The user encountered `ModuleNotFoundError: No module named 'src'` when invoking pytest, plus an incorrect `from src.aws_inventory import all` line.

From the **repository root**, prefer:

```powershell
python -m pytest tests/test_aws_inventory.py -v
```

This uses the selected Python interpreter and places the current working directory on Python's import path. If it still fails, verify the terminal's working directory, the active virtual environment, and whether `src/aws_inventory.py` is importable.

### 6.9 Testing ownership and our revised learning strategy

**User concern:** Mocking was consuming too much learning time; the main goal is independent Python development, not becoming a QA specialist.

**Agreed approach:**

- The user designs and implements the production Python code.
- AI may generate test scaffolding, fixtures, and mock syntax.
- The user should still understand what each test scenario means, run the tests, read failures, and validate important behavior.
- Advanced mocking, fixture machinery, and exhaustive framework details can wait.
- Developers own the correctness of their code even when QA or AI assists with tests.

This prioritizes practical software design, debugging, data structures, and API integration without abandoning engineering quality.

## 7. Generated orchestration test suite

The companion file `tests/test_aws_inventory.py` includes:

1. **Empty inventory:** all three keys exist with empty lists; no key-related collectors run.
2. **Two users / two keys:** Alice has two keys, Bob none; checks counts, call arguments, usage merge, normalized output, and preservation of raw records.
3. **User with no keys:** one IAM user with an empty access-key collection.
4. **Failure propagation:** parameterized tests for failures in each of the four collector/normalizer functions.

These tests deliberately mock the individual collector functions; they do not contact AWS. Module 02's `Stubber` tests cover a different layer.

### Run locally

Place the supplied test file at `tests/test_aws_inventory.py`, then run:

```powershell
python -m pytest tests/test_aws_inventory.py -v
```

The generated suite contains **7 pytest cases**: 3 normal scenarios plus 4 parameterized failure scenarios. A passing run is expected if the current implementation matches the representative code in Section 3; actual execution in your repository remains to be verified.

## 8. Suggested cleanup before committing

- Keep `main.py` focused on session/client initialization and one orchestrator call.
- Remove unused imports and temporary `print()` statements from `main.py` and `aws_inventory.py` once no longer needed.
- Do not log raw access-key identifiers or account-specific details unnecessarily.
- Confirm `tests/test_aws_inventory.py` passes locally.
- Retain existing Module 02 `Stubber` tests; these test different responsibilities.
- Commit the implementation, tests, and this learning journal together.

Suggested Git commands (review your changes before committing):

```powershell
git status
git add src/aws_inventory.py main.py tests/test_aws_inventory.py docs/03-aws-inventory.md
git commit -m "Complete IAM inventory orchestration and tests"
git push
```

## 9. Module boundary and what comes next

**Module 03 scope:** Orchestrate existing IAM user/access-key collectors and return a consistent inventory.  
**Module 04 scope:** Add IAM role collection and trust-policy inspection, then integrate new records into the inventory.  
**Module 05 scope:** IAM permissions and policy collection.  
**Later:** security findings model/analyzer, reporting, CI/CD and scanners, deployment/GitOps, AI-assisted analysis, and finally GCP collection.

### Module 04 design questions to begin with

- Which Boto3 IAM operation lists roles, and does it require pagination?
- What fields belong in the raw role record versus a normalized role record?
- How should `AssumeRolePolicyDocument` be represented for later trust-policy analysis?
- How can we extend the existing inventory without breaking consumers expecting the original three keys?

**Completion criteria for Module 03:** `main.py` calls the orchestrator; live AWS collection succeeds; the generated orchestration tests pass locally; the repository contains this journal. The integration run was successful; test execution should be confirmed locally.
