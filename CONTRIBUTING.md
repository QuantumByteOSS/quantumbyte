# Contributing to QuantumByte

QuantumByte is the **open core** of an app-builder engine: intent → spec → generated,
validated app. This guide covers how to get a working checkout, the conventions we
hold to, and how changes land.

> **Founding phase.** The contributor group is intentionally small right now
> (see the [README](README.md)). If you're not yet in it and want to be, say hi on
> [Discord](https://discord.gg/zFD35kwHmU) or DM
> [@kevin.pantasdo](https://www.threads.com/@kevin.pantasdo), and open a discussion
> before starting large work — we'd rather talk first than have you build against
> a design we're about to change.

## Ground rules from the design principles

These aren't style preferences — they're what the project *is* (see the
[README](README.md) design principles):

- **Spec-first.** A change to generation behavior is a change to a spec
  (AppSpec, SlideSpec) and its validators — not an ad-hoc tweak to the LLM prompt.
  If your change makes generated output differ, the spec and its validators move
  with it.
- **Harness before features.** Anything generated must stay reproducible and
  evaluable. New generation capability ships **with** the eval that proves it, in
  the same PR — not "tests later."
- **Pluggable boundaries.** Model providers, target stacks, and deploy targets are
  adapters behind stable interfaces. Don't hard-wire a specific provider into core.

## Development setup

Monorepo, three apps: `apps/web` (Next.js, npm), `apps/orchestrator` and
`apps/worker` (Python, pip venvs). Everything is driven by the `Makefile` — run
`make help` for the full list.

```bash
make setup     # one-shot: env + deps (web npm, orch/worker venvs) + Postgres + migrations
make dev       # run web + orchestrator + worker together (Ctrl-C stops all)
```

Or per-app in separate terminals: `make web` (http://localhost:3000),
`make orchestrator`, `make worker` (start several for a fleet).

Copy the `.env.example` in each app dir to `.env` and fill in secrets — `make env`
seeds all three. Never commit a real `.env` — only `.env.example` is tracked,
and it must hold placeholders only.

## Checks

`make check` runs everything CI runs: ESLint + `tsc --noEmit` + vitest for the web
app, and `ruff check` for the Python apps. Run it before pushing — CI
(`.github/workflows/ci.yml`) enforces the same checks on every PR.

## Branching and PRs

- Branch off `main`. Keep branches focused — one logical change per PR.
- Open a PR against `main`. Describe *what changed and why*; link the issue.
- A PR that changes generation behavior must include the eval/spec change that
  covers it. A reviewer will bounce "code now, tests later."
- Keep the diff reviewable. Large mechanical changes (renames, reformatting) go in
  their own commit, separate from behavior changes.

## Commit messages — Conventional Commits

The history uses [Conventional Commits](https://www.conventionalcommits.org/).
Match it:

```
feat: user-locked harness requirements survive auto-derivation
fix(web): re-check spinner is additive, not a verdict-icon swap
refactor(worker): single-agent PARTNER — remove all subagents
```

Type is one of `feat`, `fix`, `refactor`, `docs`, `chore`, `test`. Scope
(`web`, `worker`, `orchestrator`) is optional but preferred. Subject is imperative,
lower-case, no trailing period.

## Code style

- **Web (`apps/web`):** Prettier + ESLint. Run `npx prettier --write .` from
  `apps/web`, and `make lint` before pushing. `.editorconfig` covers whitespace.
  Note `apps/web/AGENTS.md`: this Next.js has breaking changes from upstream — read
  the guide in `node_modules/next/dist/docs/` before touching framework code.
- **Python (`apps/worker`, `apps/orchestrator`):** `ruff check` is enforced in CI
  (config in `ruff.toml`; `make lint` runs it locally). No enforced formatter yet —
  match the surrounding file: 4-space indent, type hints on public functions,
  docstrings where the existing code has them.

## Bigger changes — design discussion first

Architecture-level changes start as a design issue (or a
[Discord](https://discord.gg/zFD35kwHmU) thread) before code. Open one when a
change:

- alters a spec schema or a stable adapter interface,
- picks a new dependency, stack, or deploy target,
- changes the agent execution model or the harness contract.

Small, local changes don't need one — just a good PR description.

## Licensing of contributions

The project is licensed under [Apache-2.0](LICENSE). By opening a PR you agree your
contribution is licensed under the same terms (Apache-2.0 §5). No CLA is required.

## Reporting bugs and security issues

- **Bugs / features:** open a GitHub issue with repro steps, expected vs. actual.
- **Security vulnerabilities:** do **not** open a public issue. Follow
  [SECURITY.md](SECURITY.md).
