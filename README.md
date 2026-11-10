# Cloud Security Automation Platform

An AWS-first cloud security automation platform built with Python, Boto3, Terraform, Kubernetes, GitHub Actions, Argo CD, and AI.

## Project Objective

Build an end-to-end security automation platform to collect cloud security data, identify risks, automate security checks, and use AI to explain and prioritize findings.

This is also a hands-on software engineering project focused on improving independent Python programming, architecture, testing, and DevSecOps skills.

## Project Scope

**Phase 1 — AWS**

- AWS IAM inventory collection and normalization
- IAM security analysis and reporting
- Application security scanning
- CI/CD automation using GitHub Actions
- Docker and Kubernetes deployment
- Infrastructure management using Terraform
- GitOps deployment using Argo CD
- AI-powered security findings analysis

**Phase 2 — GCP**

Expand the completed AWS platform to support GCP and multicloud security analysis.

GCP development is intentionally deferred until Phase 1 is operational end to end.

## Current Progress

| Module | Description | Status |
|---|---|---|
| 01 | AWS Authentication | Core completed |
| 02 | IAM Collector and initial unit tests | Core completed; additional tests deferred |
| 03 | AWS IAM Inventory Orchestration | Next |
| 04+ | Analysis, reporting, DevSecOps, deployment and AI | Planned |

## Architecture

```text
AWS IAM
   |
   v
Python / Boto3 Collectors
   |
   v
AWS Inventory Orchestration
   |
   v
Security Analysis
   |
   v
Reporting and Findings
   |
   v
AI Security Assistant

GitHub Actions → Security Scanning → Docker
                                      |
                                      v
                               Kubernetes / Argo CD
```

The diagram represents the target architecture. Not all components are implemented yet.

## Implemented Features

- AWS authentication using named profiles and assumed IAM roles
- AWS STS identity verification
- IAM user enumeration with pagination
- IAM access-key enumeration
- Access-key last-used data collection
- Normalization of access-key metadata
- AWS API and SDK error handling
- Initial pytest unit tests using Botocore Stubber

## Technology Stack

Python, Boto3, AWS IAM, pytest, Terraform, GitHub Actions, Docker, Kubernetes, Argo CD, Semgrep, Checkov, Trivy, Gitleaks, pip-audit, and AI/LLM integration.

Some technologies are planned and not yet integrated.

## Documentation

- [Project Plan and Status](00-PROJECT-PLAN-AND-STATUS.md)
- [Module 01 — Authentication](docs/01-authentication.md)
- [Module 02 — IAM Collector](docs/02-IAM-Collector.md)

## Development Principles

- AWS-first development
- Read-only security collection
- Least-privilege IAM permissions
- No hardcoded AWS credentials or secrets
- Modular, testable Python functions
- Human approval before security remediation
- Incremental development and testing

## Next Milestone

**Module 03 — AWS IAM Inventory Orchestration**

Move IAM collection coordination out of `main.py` into a dedicated orchestration function, while keeping the implementation simple and testable.

## Project Status

Active development — AWS Phase 1.

See the [Project Plan](00-PROJECT-PLAN-AND-STATUS.md) for the detailed roadmap, progress estimates, and outstanding tasks.
