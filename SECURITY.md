# Security Policy

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Report it privately, one of two ways:

1. **GitHub Private Vulnerability Reporting** (preferred) — on this repo, go to
   the **Security** tab → **Report a vulnerability**. This keeps the report and
   discussion private until a fix ships.
2. **Email** — **hello@quantumbyte.ai**. Put `SECURITY` in the subject.

Please include:

- what the issue is and the impact you think it has,
- steps to reproduce (or a proof of concept),
- affected app/component (`web`, `orchestrator`, `worker`) and commit/branch,
- any suggested fix or mitigation.

## What to expect

QuantumByte is a **young open-source project** — treat these as targets, not a
contractual SLA:

- **Acknowledgement:** within 3 business days.
- **Assessment + severity:** within 10 business days.
- **Fix / mitigation:** timeline shared after triage, prioritized by severity.

We'll keep you updated through the process and credit you in the release notes
once a fix is public, unless you ask us not to. Please give us reasonable time to
ship a fix before any public disclosure.

## Scope

In scope — this repository (the open core):

- `apps/web`, `apps/orchestrator`, `apps/worker` source
- the generation/spec/harness pipeline
- build, dev, and deploy tooling in this repo (`Makefile`, `docker-compose.yml`)

Out of scope:

- the hosted QuantumByte platform (operations, tenant management, billing,
  deployment infra) — it is not in this repo; report platform issues via the same
  email and we'll route them.
- vulnerabilities in third-party dependencies with no QuantumByte-specific
  exploit path — report those upstream (tell us too if we should pin/patch).
- findings that require a compromised host, a malicious local `.env`, or physical
  access.

## Handling secrets

This repo tracks only `.env.example` files with **placeholder** values. If you
ever find a real credential committed (a live `sk-ant-…`, `ghp_…`,
`github_pat_…`, S3 key, or database password), treat it as a vulnerability and
report it privately per above — do not open a public issue, and do not use the
credential.
