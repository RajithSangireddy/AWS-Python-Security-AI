# Cloud Security Automation Platform

An **AWS-first, read-only cloud security automation platform** built incrementally with Python and Boto3. The goal is to collect and normalize cloud security data, identify and explain risks, and ultimately deliver a tested DevSecOps pipeline and AI-assisted security analysis.

This is also a hands-on software engineering project to develop independent Python programming, architecture, debugging, and testing skills.

> **Project status:** Active development — AWS Phase 1. IAM authentication, user/access-key collection, inventory orchestration, and role/trust-policy collection are implemented. Security analysis, deployment, and AI integration remain planned.

## Table of Contents

- [Project Objective](#project-objective)
- [Project Scope](#project-scope)
- [Current Progress](#current-progress)
- [Architecture](#architecture)
- [Implemented Features](#implemented-features)
- [Technology Stack](#technology-stack)
- [Repository Documentation](#repository-documentation)
- [Development Principles](#development-principles)
- [Running the Tests](#running-the-tests)
- [Next Milestone](#next-milestone)

## Project Objective

Build a portfolio-quality, cost-conscious security automation platform that collects cloud identity and security data, analyzes risks, produces findings and reports, automates testing and deployment, and uses AI to help explain and prioritize evidence-based findings.

## Project Scope

**Phase 1 — AWS:** IAM inventory collection and normalization; IAM risk analysis and reporting; AppSec scanning; GitHub Actions CI/CD; Docker; Terraform; Kubernetes and Argo CD; AI-assisted security findings analysis.

**Phase 2 — GCP:** Extend the proven AWS approach to GCP and, where useful, introduce shared security findings models. GCP implementation is deferred until the AWS platform works end to end, including CI/CD, Argo CD, and AI integration.

## Current Progress

| Module | Deliverable | Status |
|---|---|---|
| 01 | AWS authentication and STS identity verification | Core complete |
| 02 | IAM users, access keys, last-used metadata, normalization | Core implemented; additional collector tests deferred |
| 03 | AWS IAM inventory orchestration | Core complete; focused tests passed |
| 04 | IAM roles and trust-policy collection/normalization | Complete for agreed scope; **7/7 module-specific tests passed** |
| 05 | IAM permissions and policy collection | **Next** |
| Later | Findings analysis, reporting, AppSec, CI/CD, infrastructure, GitOps, AI | Planned |
| Phase 2 | GCP support | Deferred |

The seven passing tests refer to the Module 04 test suite, not a claim of complete coverage for every collector or the overall application. See the [project plan and status](docs/00-PROJECT-PLAN-AND-STATUS.md) for detailed milestones and deferred work.

## Architecture

```text
AWS IAM (read-only APIs)
       |
       v
Python / Boto3 collectors
  - Users and access keys
  - Access-key last-used data
  - Roles and trust policies
       |
       v
AWS IAM inventory orchestration
  - Raw inventory
  - Normalized records
       |
       v
Security analysis / findings (planned)
       |
       v
Reporting and AI assistant (planned)

GitHub Actions + AppSec scanning (planned)
       |
       v
Docker + Terraform + Kubernetes + Argo CD (planned)
```

The diagram separates the current collection foundation from future components; it does not imply that the full pipeline has been deployed.

## Implemented Features

- AWS authentication through a named profile and assumed audit role, with STS identity verification.
- IAM user and access-key enumeration with pagination.
- Access-key last-used metadata retrieval and normalization.
- AWS IAM inventory orchestration that keeps raw and normalized records separate.
- IAM role enumeration with pagination and SDK/API error handling.
- Role trust-policy extraction with role name and ARN; normalize a single `Statement` dictionary into a list for consistent downstream processing.
- Unit tests for inventory orchestration and role/trust-policy behavior, including the seven passing Module 04 tests.
- Error propagation rather than silently returning incomplete inventories.

## Technology Stack

**In use:** Python, Boto3, AWS IAM/STS, pytest, Botocore Stubber, `unittest.mock`, Git/GitHub.

**Planned:** Terraform, GitHub Actions, Docker, Kubernetes, Argo CD, Semgrep, Checkov, Trivy, Gitleaks, pip-audit, and AI/LLM integration.

## Repository Documentation

The following paths match the filenames shown in the repository's `docs/` directory:

| Document | Link |
|---|---|
| Master project plan and status | [00 — Project Plan and Status](docs/00-PROJECT-PLAN-AND-STATUS.md) |
| Module 01 — Authentication | [01 — Authentication](docs/01-authentication.md) |
| Module 02 — IAM Collector | [02 — IAM Collector Learning Journal](docs/02-IAM-Collector-Learning-Journal.md) |
| Module 03 — AWS Inventory | [03 — AWS Inventory](docs/03-aws-inventory.md) |
| Module 04 — IAM Roles and Trust Policies | [04 — IAM Roles & Policy Collection](docs/04-IAM-roles-policy-collection.md) |

**Module 05:** IAM permissions and policy collection is next. Its starter context can be added to `docs/` when ready; no link is included until the file is committed.

## Development Principles

- AWS-first and read-only collection; least-privilege IAM access.
- Never hardcode or commit credentials or secrets.
- Keep authentication, collection, orchestration, analysis, and reporting separate.
- Prefer small, testable functions and explicit data structures.
- Propagate errors rather than silently accepting incomplete inventory results.
- Human review before any future remediation; no autonomous AI changes.
- Learn by designing and writing production code independently, with focused review and generated test scaffolding when useful.

## Running the Tests

From the repository root, with the project's Python environment activated:

```powershell
python -m pytest tests/ -v
```

To run only the IAM roles tests (if saved at this path):

```powershell
python -m pytest tests/test_iam_roles.py -v
```

## Next Milestone

**Module 05 — IAM Permissions and Policies.** Design and implement read-only collection of relevant role policies and relationships, then extend the inventory and focused tests. The learning emphasis is on independently planning function inputs/outputs, choosing data structures, implementing code, and reviewing edge cases.

For the full roadmap and tracked status, see [docs/00-PROJECT-PLAN-AND-STATUS.md](docs/00-PROJECT-PLAN-AND-STATUS.md).
