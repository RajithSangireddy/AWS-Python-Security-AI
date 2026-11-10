# Module 01 — AWS Authentication (`src/auth.py`)

**Project:** Cloud Security Automation Platform  
**Session record:** October 17–19, 2026  
**Status:** Role-based authentication verified; error handling and deployment portability require follow-up.  
**Record type:** Detailed reconstruction of our technical discussion, not a verbatim transcript. Questions are paraphrased where exact wording is unavailable.

---

## 1. Why this module exists

The platform will collect read-only cloud security metadata (starting with AWS IAM users, access keys, roles and trust policies). Before collecting anything, it needs a reliable way to obtain an AWS SDK session, verify which identity is in use, and report authentication failures intelligibly.

We separated authentication from collection:

- `src/auth.py` owns session creation and identity validation.
- `src/collector.py` will receive an authenticated session rather than building a new one.
- `main.py` coordinates these modules.

**Learning preference:** Write the implementation independently, in small increments; use discussion, review and targeted examples rather than receiving a complete codebase.

## 2. Local setup and identity design

Development environment: Windows PowerShell, VS Code, Python 3.12, Boto3. The working project was referred to as `AWS-Python-Security-AI`.

The local AWS CLI `default` profile uses an IAM user with permission to assume an audit role. A named profile, `security-audit`, uses the `default` profile as its credential source:

```ini
[profile security-audit]
role_arn = arn:aws:iam::<ACCOUNT_ID>:role/security-audit
source_profile = default
region = us-east-1
```

`<ACCOUNT_ID>` is a placeholder; do not put real credentials in the repository. The role name is **`security-audit`** (not `SecurityAuditRole`). The role trust policy permits the intended IAM principal, not a wildcard principal. The role also needs appropriate read-only IAM permissions to support subsequent collector calls.

### Identity flow

```text
Local Python application
        |
        v
boto3.Session(profile_name="security-audit")
        |
        v
AWS shared config: role_arn + source_profile=default
        |
        v
Credentials for local IAM user
        |
        v
AWS STS AssumeRole (trust + caller permissions both required)
        |
        v
Temporary role credentials
        |
        v
STS GetCallerIdentity / IAM read APIs
```

**Verified:** `aws sts get-caller-identity --profile security-audit` succeeded, and the Python code also successfully returned an assumed-role ARN resembling `arn:aws:sts::<ACCOUNT_ID>:assumed-role/security-audit/botocore-session-...`.

**Not yet verified:** credential refresh during a long-running collector, or all permissions needed by future IAM API calls.

## 3. Questions and reasoning from the discussion

### Q1. Why create a Boto3 session instead of calling AWS CLI commands?

The earlier shell approach used AWS CLI commands such as `aws iam list-users`. Boto3 gives Python objects and dictionaries that the collector and analyzer can process directly. A `Session` carries AWS configuration and credential-provider behavior; service clients such as STS or IAM are created from it.

```python
session = boto3.Session(profile_name="security-audit")
sts = session.client("sts")
identity = sts.get_caller_identity()
```

A Boto3 `Session` object is not itself proof of valid credentials. Making an AWS request, such as `get_caller_identity()`, validates that a request can be signed and accepted at that moment.

### Q2. What exactly does `get_caller_identity()` return?

A dictionary containing fields such as `Account`, `Arn` and `UserId`. Python dictionary keys are case-sensitive: `identity["Account"]` is different from `identity["account"]`.

```python
print(identity["Account"])
print(identity.get("Arn"))
```

`[]` requires the key to exist; `.get()` returns `None` by default if the key is absent. `Account` and `Arn` are expected in a successful STS identity response.

### Q3. Why does the AWS profile have a `source_profile`?

The named role profile does not store a separate long-lived access key. It tells the SDK which existing credentials to use to request `AssumeRole`. In this local setup, the source is `default`.

An earlier `source_profile = bootstrap` caused `InvalidConfigError` because that source profile was not configured. Changing it to `default` resolved the configuration problem.

**Key distinction:** `source_profile` is a *local credential source*, not an AWS role permission or trust policy.

### Q4. Why did STS return `AccessDenied` even though the profile existed?

A configured profile does not grant permission. Role assumption depends on both the caller being allowed to call `sts:AssumeRole` and the target role's trust policy allowing that principal. The earlier STS `AccessDenied` was resolved by correcting the IAM trust/permissions setup. Do not use `"Principal": "*"` as a shortcut.

### Q5. What happens when temporary credentials expire?

When Boto3/Botocore uses the standard assume-role credential provider, it can obtain and refresh temporary role credentials using the configured source credentials. The application normally should **not** implement its own STS refresh loop. Refresh still depends on the source credentials and role permissions remaining valid.

An expired or invalid credential is **not always** an `InvalidConfigError`. `InvalidConfigError` concerns malformed/incomplete credential configuration; AWS service rejections such as expired tokens commonly surface as `ClientError` with an AWS error code. Missing credentials can surface as `NoCredentialsError`. Exact behavior depends on the credential provider and failure point.

### Q6. Does the deployed application need `source_profile`?

Not necessarily. A local named profile is useful for development, but a workload running on EC2 can use its instance role via the default credential chain. A GKE workload or CI job can use an appropriate federated identity flow rather than embedding IAM user keys. The intended future interface is an optional profile:

```python
def create_aws_session(profile_name: str | None = None):
    ...
```

With `None`, Boto3 can use the standard credential provider chain. This is a **planned refactor**, not yet verified in the current code.

### Q7. Why import a function from `auth.py` into `main.py`?

Python modules have separate namespaces. Defining `create_aws_session()` in `src/auth.py` does not automatically make the name available in `main.py`. Import it using the appropriate package layout, then call it. This was relevant to a `NameError` encountered while developing the project.

### Q8. Why does AWS return `ClientError` if the failure happens on the server?

`ClientError` is the name of the **Botocore exception class raised in the Python client** when an AWS service returns an error response. It does not mean the user's Python client necessarily caused the failure. AWS sends a structured error response; Botocore translates that response into `ClientError`.

Examples of service error codes include `AccessDenied`, `ExpiredToken` and `ValidationError` (depending on the API). The structured AWS code can be read from:

```python
error_code = error.response["Error"]["Code"]
```

### Q9. What is the difference between `ProfileNotFound`, `InvalidConfigError`, `NoCredentialsError` and `ClientError`?

| Exception | Typical meaning | Example |
|---|---|---|
| `ProfileNotFound` | Requested named profile cannot be found | Typo in `security-audit` |
| `InvalidConfigError` | Credential/profile configuration is invalid | `source_profile` points to missing configuration |
| `NoCredentialsError` | No usable credentials found | No provider supplies credentials |
| `ClientError` | AWS service returned an error response | STS denies `AssumeRole` |

These are useful categories, but the same underlying operational problem can surface differently depending on when credential resolution or a request fails.

### Q10. What does `raise` do, and why can't we write `raise error_code`?

`raise` requires an exception instance or exception class, not a plain string. In an earlier draft:

```python
error_code = error.response["Error"]["Code"]
raise error_code  # Incorrect: error_code is a string
```

The corrected approach creates an exception:

```python
raise RuntimeError(f"AWS API request failed: {error_code}") from error
```

`RuntimeError` here is an application-level wrapper, not the original AWS exception.

### Q11. Does “preserve the original exception” mean `RuntimeError` is the original?

No. The original is the exception caught in the `except` clause, for example Botocore's `ClientError`. The new `RuntimeError` becomes the exception propagated to the caller. `from error` explicitly links them through the new exception's `__cause__` attribute.

```python
try:
    int("abc")
except ValueError as original:
    raise RuntimeError("Conversion failed") from original
```

If a caller catches the new exception as `error`:

```python
print(type(error).__name__)            # RuntimeError
print(type(error.__cause__).__name__)  # ValueError
```

The user's reasoning was that the original `ValueError` must still be present somewhere. **That is correct**: it remains accessible as `__cause__`, but it does not change the type of the new exception into `ValueError`.

### Q12. Is `raise error` the same as `raise RuntimeError(...) from error`?

No:

- `raise` inside an `except` block re-raises the current exception and is usually preferred when simply propagating it.
- `raise error` raises that exception object again, but can add a traceback frame.
- `raise RuntimeError("...")` creates a new exception; while handling another exception, Python may retain implicit context.
- `raise RuntimeError("...") from error` creates a new exception with an **explicit cause**.

Wrapping is a design choice: it simplifies the application's public error interface but callers that need to handle AWS error codes specifically may prefer the original `ClientError` or a custom application exception.

## 4. Code evolution

### Initial behavior

The first implementation created a Boto3 session, called STS, printed the account and ARN, and returned the session. Exceptions were then added to make failures more understandable.

### Representative code at the stopping point

This is a reconstructed version of the code discussed; compare it against the actual local `src/auth.py` before treating it as the source of truth.

```python
import boto3
from botocore.exceptions import (
    ProfileNotFound,
    NoCredentialsError,
    InvalidConfigError,
    ClientError,
)


def create_aws_session(name_of_profile: str):
    try:
        session = boto3.Session(profile_name=name_of_profile)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        print(f"AWS Account : {identity['Account']}")
        print(f"Role ARN is : {identity.get('Arn')}")
    except ProfileNotFound as error:
        raise RuntimeError("AWS profile not found") from error
    except InvalidConfigError as error:
        raise RuntimeError("AWS profile or role configuration is invalid") from error
    except NoCredentialsError as error:
        raise RuntimeError("AWS credentials not available") from error
    except ClientError as error:
        error_code = error.response["Error"]["Code"]
        raise RuntimeError(f"AWS API request failed: {error_code}") from error
    return session
```

**Important:** The last exception-handling line was recommended after a screenshot showed `raise error_code`; it has not been independently confirmed in the final local file. The successful role assumption occurred earlier.

### Design observations

1. `session` is returned only after the STS identity check succeeds.
2. The role ARN is printed for local verification; production code should use structured logging and consider whether identity information is appropriate for its log audience.
3. All four exception categories are wrapped in `RuntimeError`, which gives callers a consistent type but can obscure granular handling unless `__cause__` is inspected.
4. This code does not yet validate that the account or role is the **expected** account/role.
5. `profile_name` is currently required; workload-identity-friendly optional configuration remains future work.

## 5. Troubleshooting chronology

| Problem or question | What we learned / action taken | Outcome |
|---|---|---|
| Boto3 import/environment issue | Install or select Boto3 in the Python environment actually running the script | Development continued |
| Function name not found in `main.py` | Modules require explicit imports | Development continued |
| `source_profile = bootstrap` | Referenced source profile was not configured | Corrected to `default` |
| STS `AccessDenied` on `AssumeRole` | Review caller permissions and target role trust | Resolved; role assumption verified |
| Profile works in CLI; does it work in Python? | Use Boto3 session and STS identity call | Verified assumed-role identity |
| Expiring temporary credentials | Understand Botocore credential-provider refresh behavior | Discussed, not load-tested |
| `ClientError` naming confusion | Exception is raised by the Python SDK for an AWS service error response | Concept clarified |
| `raise error_code` | Cannot raise a string | Recommended `RuntimeError(...) from error` |
| Original versus wrapped exception | `__cause__` holds explicitly chained original | Concept clarified with `ValueError` example |

## 6. What is complete, and what is not

### Confirmed

- Local named role profile successfully assumes `security-audit`.
- AWS CLI and Python STS identity checks succeeded.
- Basic session creation and module separation were implemented.
- Core Python exception concepts were discussed in detail.

### Still to implement or test

- Confirm the final corrected exception line exists in local code.
- Make `profile_name` optional and test default credential-chain behavior.
- Validate expected AWS account and role before scanning.
- Add unit tests using mocks/stubs; avoid requiring live AWS credentials for unit tests.
- Test handling of missing profile, malformed profile, missing credentials and AWS `AccessDenied`.
- Consider whether to preserve `ClientError` directly, define a custom `AuthenticationError`, or keep `RuntimeError`.
- Add structured logging without exposing secrets.
- Verify role permissions for `iam:ListUsers`, `iam:ListAccessKeys`, `iam:GetAccessKeyLastUsed`, role enumeration and trust-policy inspection.
- Verify automatic credential refresh if a long-running workload needs it.

## 7. Next module handoff: `02 — IAM Collector`

**Goal:** Implement a read-only AWS IAM user collector using the authenticated session.

**First exercise:** In `src/collector.py`, define a function that accepts `session`, creates an IAM client, obtains the `list_users` paginator, and iterates its pages. Only after that works, extract user fields and choose a normalized return structure.

Reference APIs:

```python
iam = session.client("iam")
paginator = iam.get_paginator("list_users")
for page in paginator.paginate():
    users = page["Users"]
    # Design the next small step yourself.
```

**Architecture decision:** `main.py` creates the session once and passes it to the collector. The collector does not call `create_aws_session()` internally. This improves separation of concerns, testing and reuse.

**Learning method:** Ask one focused design question at a time; let the learner write the next few lines and review them before moving on. Avoid full-file code dumps.

## 8. Keeping the notes up to date

Store this file at `docs/sessions/01-authentication.md`. After revisiting this module, append a dated subsection with:

1. The exact question or issue.
2. The reasoning and resolution.
3. Code changes and test evidence.
4. Any decision that affects other modules.

For cross-module decisions, add a short entry to `docs/decisions.md` and link back here. Never include access keys, session tokens, private profile contents, or other secrets in notes or screenshots committed to Git.

### Suggested Git commands (once the repository is initialized)

```powershell
git add docs/sessions/01-authentication.md
git diff --cached
git commit -m "docs: capture detailed AWS authentication learning notes"
git push
```

---

*This record is designed to preserve the learning trail while keeping the new `02 — IAM Collector` conversation focused. For exact code state, the local source file and Git history remain authoritative.*
