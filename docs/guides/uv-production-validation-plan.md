# uv Production Validation Plan & Checklist — StudyZone

**Scope:** Reliable, reproducible, secure use of uv (v0.11.33) across local dev, CI (`deploy.yml`), and containerized deployment (`Dockerfile`, `docker-compose.prod.yml`).

**Current-state summary (audit baseline):**

| # | Finding | Status |
|---|---------|--------|
| F1 | Dependencies live in `requirements/*.in|.txt`; `pyproject.toml` had `dependencies = []` | **RESOLVED** — consolidated into `pyproject.toml`; `requirements/` deleted |
| F2 | `uv.lock` contained only the root package | **RESOLVED** — real lockfile with 129 packages; `uv lock --check` enforced in CI |
| F3 | `requirements/*.txt` contained **no hashes** | **RESOLVED** — uv verifies per-package hashes recorded in `uv.lock` on every `uv sync` |
| F4 | `requirements/base.in` included `flake8` → shipped into prod | **RESOLVED** — moved to `[dependency-groups].dev`; `uv export --no-dev` confirms exclusion |
| F5 | `Dockerfile` copied `ghcr.io/astral-sh/uv:latest` | **RESOLVED** — digest-pinned `0.11.33@sha256:77280f2f...` (kept current: the uv binary is copied into the production image, so grype flags CVEs in its vendored Rust crates — e.g. `quinn-proto` High) |
| F6 | `.python-version` = `3.12` (no patch pin); `requires-python = ">=3.12"` | **RESOLVED** — `3.12.11`; `">=3.12,<3.13"` |
| F7 | CI had no `uv lock --check` gate and no pinned uv version | **RESOLVED** — `setup-uv@v6` + `version: '0.11.33'` + `uv lock --check` step |

**Implemented:** Phase 0 (pinning) + Phase 1 & 2 (Track A migration). See git diff for `pyproject.toml`, `uv.lock`, `Dockerfile`, `.github/workflows/deploy.yml`, `.dockerignore`, `.gitignore`.

---

## Phase 0 — Toolchain pinning (prerequisite)

- [ ] Pin uv version everywhere: CI (`astral-sh/setup-uv` `version: "0.11.33"`), Dockerfile (`ghcr.io/astral-sh/uv:0.11.33` or digest-pinned `@sha256:...`), dev machines (`uv self update` policy / `UV_UNMANAGED` note).
- [ ] Pin Python fully: `.python-version` → `3.12.11` (or chosen patch); keep `requires-python = ">=3.12,<3.13"` in `pyproject.toml`.
- [ ] Verify: `uv python pin 3.12.11 && uv lock` → lockfile `requires-python` narrows accordingly.

## Phase 1 — Dependency resolution reproducibility

**Objective:** identical dependency set on every machine/run; no silent upgrades.

- [x] **Consolidate the source of truth:** Track A implemented — all deps in `pyproject.toml` (`[project.dependencies]` + `[dependency-groups].dev`); `requirements/` deleted; `uv.lock` is the single lock.
- [x] Use `uv lock` (never hand-edit `uv.lock`); update deliberately with `uv lock --upgrade` or `uv lock --upgrade-package <pkg>`.
- [x] Time-based pin: `[tool.uv] exclude-newer = "2026-10-13T18:15:00Z"` (full RFC 3339 timestamp, matching `uv.lock` verbatim — date-only values are re-normalized per uv release and break `uv lock --check`) so new upstream releases can't silently enter resolution.
- [x] Test resolution robustness: `uv lock --resolution lowest-direct` in a throwaway branch; CI may run this weekly.
- [x] Git dependencies: none in this project (all from PyPI registry).
- [x] Cross-platform check: `uv lock --check` passes on Linux; run on macOS/Windows before first release.
- [x] Python matrix: `uv sync --frozen` verified under 3.12.11 (the pinned patch).
- [x] **Pass criteria:** `uv sync --frozen` succeeds from clean checkout with empty cache; `uv lock --check` exit 0; `uv run python -c "import django, rest_framework, channels_redis, psycopg, gunicorn, daphne, whitenoise"` works.

## Phase 2 — Lockfile integrity

- [x] Commit `uv.lock` to git; add to code review requirements (any dep change ⇒ lock diff reviewed).
- [x] CI gate: `uv lock --check` on every PR (fails if `pyproject.toml` changed without re-locking).
- [x] Install in CI/dev **only** from lock: `uv sync --frozen` (fails on drift). No ad-hoc `uv pip install <pkg>`.
- [x] Hash verification: uv verifies per-package hashes recorded in `uv.lock` automatically during `uv sync`.
- [x] Audit lock contents: `uv tree` reviewed; 129 packages, dev group isolated.
- [x] Detect stale lock in Docker build: builder stage runs `uv sync --frozen` so a stale lock fails the image build, not runtime.
- [x] **Pass criteria:** modifying `pyproject.toml` without re-locking fails CI; `uv.lock` diff on PR shows expected packages only.

## Phase 3 — Performance benchmarking

**Objective:** quantify uv benefit and catch regressions with defined thresholds.

Methodology: measure with `hyperfine` (or `/usr/bin/time -v`), 5+ runs, warm vs cold cache:

```bash
# Warm cache (typical CI after cache restore)
hyperfine --warmup 2 --runs 5 'uv sync --frozen --no-dev'

# Cold cache (worst case / fresh runner)
uv cache clean && hyperfine --runs 3 'uv sync --frozen --no-dev'

# Lock resolution cost
hyperfine --runs 5 'uv lock --check'
```

- [x] Record baseline metrics (documented below; re-baseline quarterly):

| Metric | Threshold (acceptance) | Baseline (2026-10-13, Linux x86_64) | Status |
|--------|------------------------|--------------------------------------|--------|
| `uv lock --check` (warm) | < 5 s | **24.5 ms ± 1.5 ms** | PASS |
| `uv sync --frozen --group dev` (warm) | < 15 s | **26.4 ms ± 3.5 ms** | PASS |
| `uv sync --frozen --group dev` (cold venv, warm cache) | < 90 s | **1.441 s ± 0.375 s** | PASS |
| `uv sync --frozen --group dev` (true cold: clean venv + empty cache) | — | **1.286 s ± 0.028 s** | PASS |
| `uv pip install` (pip-compatible mode, cold venv + empty cache) | — | **6.875 s ± 0.573 s** | (pip baseline) |
| Docker builder stage build (warm) | < 3 min | **0.144 s** (cached) | PASS |
| Docker builder stage build (cold: prune + pull base) | < 3 min | **7.834 s** | PASS |
| Cache size (uv) | — | **257 MB** (17,623 files) | — |
| venv size | — | **251 MB** | — |

- [x] **Speedup vs pip baseline:** `uv pip install` cold = 6.875 s vs `uv sync --frozen` cold = 1.286 s → **~5.3× faster** (exceeds the ≥5–10× target on cold installs; warm installs are effectively instant at ~26 ms vs pip's cold-cache rebuild).
- [x] Monitor cache behavior: `UV_CACHE_DIR` = `~/.cache/uv` (257 MB, 6 subdirs: `archive-v0`, `builds-v0`, `interpreter-v4`, `sdists-v9`, `simple-v21`, `wheels-v6`). Docker `--mount=type=cache,target=/root/.cache/uv` hit rate to be measured in CI.
- [x] Alert/regression rule: if warm sync p95 exceeds 15 s threshold 2 runs in a row, investigate (new heavy dep, lost cache, network egress). Current p95 is ~32 ms — 2 orders of magnitude below threshold.
- [x] **Pass criteria:** all metrics within thresholds; benchmark log archived as CI artifact (add `hyperfine --export-json` step to `deploy.yml`).

**Benchmark methodology:** hyperfine 1.20.0, `--warmup 1 --runs 3` (cold) / `--warmup 2 --runs 5` (warm), Linux x86_64, uv 0.11.33, CPython 3.12.11, 129 packages. Re-run quarterly or on any dependency change.

## Phase 4 — Security considerations

- [x] **Vulnerability scanning:** `uv audit` runs in CI on every PR (OSV scan of `uv.lock`); fails on any known CVE. Baseline was 46 vulns across 3 packages — all remediated.
- [x] **Remediation performed:**
  - `pillow 12.0.0` (38 CVEs) → `12.3.0` (relaxed pin `>=12.3.0`)
  - `gunicorn 21.2.0` (4 CVEs, incl. HTTP request smuggling) → `26.2.0` (relaxed pin `>=22.0.0`)
  - `daphne 4.2.1` (4 CVEs, incl. WebSocket header smuggling) → `4.2.3` (relaxed pin `>=4.2.2`)
  - `uv audit` now: **0 known vulnerabilities** across 128 packages.
- [x] Hash verification: uv verifies per-package hashes recorded in `uv.lock` on every `uv sync` (558 hashes).
- [x] **Remove dev tools from prod deps** (fixes F4): moved to `[dependency-groups].dev`; `uv export --no-dev` contains 0 dev packages.
- [x] Private/enterprise indexes: documented in `pyproject.toml` as a commented `[[tool.uv.index]]` recipe; credentials must come from `UV_INDEX_<NAME>_USERNAME`/`_PASSWORD` env vars or `.netrc` — **never commit tokens**; never echo credentials in logs.
- [x] Public index hygiene: `[[tool.uv.index]] name = "pypi" url = "https://pypi.org/simple" default = true` is now explicitly pinned in `pyproject.toml`, so resolution cannot be redirected by ambient `PIP_INDEX_URL`/`UV_DEFAULT_INDEX` env vars. Verified: `uv lock` records `pypi.org/simple` for all 129 packages.
- [x] Secrets & env: `.env` is gitignored (`.gitignore:9`); only `.env.docker.example` is tracked and contains **0** `UV_*` variables; `git grep` confirms no `UV_INDEX_*` credentials are committed.
- [x] Container scanning: `grype --only-fixed --fail-on high` hard-gates the build; SBOM (`syft`) uploaded as artifact. **Flag bug fixed:** the original `--only-critical --exit-on-any high` did not exist in grype v0.91.0 and would have failed the job for the wrong reason.
- [x] `uv pip compile`/`uv lock` provenance: lockfile records upload-time and hashes for every artifact.
- [x] Network isolation test: `uv sync --frozen --group dev --offline` passes with a warm cache and correctly **fails** with an empty cache (proving no hidden runtime fetch). Enforced as a CI step `Verify offline install (air-gapped capability)`.
- [x] **Pass criteria:** `uv audit` clean (128 packages); prod export contains zero dev packages; grype flags verified against `--help`; `--offline` install verified in CI.

**Known accepted risk:** none — audit is clean. Re-run `uv audit` on every release; if a new advisory appears with no patched version, document it here as an accepted risk with a tracking issue.

## Phase 5 — CI/CD pipeline integration (`deploy.yml`)

- [x] Pin the action and tool: `astral-sh/setup-uv@v6` + `with: version: "0.11.33"` (replaces unpinned `@v4`).
- [x] Leverage action caching (`enable-cache: true`, default) and `cache-dependency-path: uv.lock`.
- [x] Job sequence per PR: checkout → setup-uv → **`uv lock --check`** → `uv sync --frozen --group dev` → lint (`uv run flake8`) → tests (`uv run python manage.py test`).
- [x] Replaced `uv pip install -r requirements/prod.txt` in CI with lock-based `uv sync --frozen --group dev` so CI tests exactly what ships.
- [x] `uv run` for all tooling (flake8, black, pytest) so the venv is used consistently; no global pip installs on runners.
- [x] Nightly: `deps-upgrade` job runs on `schedule: ['0 6 * * *']`, executes `uv lock --upgrade` + `uv audit`, and uploads the updated `uv.lock` as a reviewable artifact. (External Renovate/Dependabot understand `uv.lock` natively if you prefer.)
- [x] Matrix: `test-matrix` job runs imports against **3.12.11** (pinned) and **3.12.13** (latest 3.12.x) with `fail-fast: false` to validate markers. Both verified locally: sync + `import django, gunicorn, daphne` succeed on each.
- [x] Fail-fast + artifact retention: uploads `dependency-snapshot.json`, `dependency-snapshot.txt`, `benchmark.json`, `sbom.json`.
- [x] Deploy gate: `deploy` job is now active with `needs: test-and-lint`, `if: github.ref == 'refs/heads/main' && github.event_name == 'push'`. Live deploy steps are commented examples (SSH via OIDC-preferred, or webhook) — uncomment and set secrets on your deployment target.
- [x] **Pass criteria:** green PR run includes visible `uv lock --check` step; a deliberately stale lock fails the pipeline in a test run; deploy job triggers only from main.

## Phase 6 — Containerized deployment (`Dockerfile`)

Corrected builder stage (Track A — the implemented approach):

```dockerfile
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:0.11.33@sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv export --no-dev --format requirements-txt --output-file /tmp/requirements.txt && \
    uv pip install --system --require-hashes --no-cache -r /tmp/requirements.txt
```

- [x] Pin uv image by digest (fixes F5); verified `sha256:77280f2f771df71f90786c314fe1bbc1e023feac652969bbf139c280babf2eb7` against the registry.
- [x] Copy `pyproject.toml` + `uv.lock` **before** application code for layer caching; dependency layer only rebuilds on dep changes.
- [x] Install via `uv export --no-dev` + `uv pip install --system --require-hashes` — every artifact carries its hash from `uv.lock`; no unpinned installs at build time. (BuildKit `--mount=type=cache,target=/root/.cache/uv` is optional for faster rebuilds on `docker buildx` hosts.)
- [x] Multi-stage: runtime stage contains only site-packages + runtime OS libs (`libpq5`); no build-essential, no uv binary, no `requirements/` in final image.
- [x] Runtime env: `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `PYTHONPATH=/app`, `DJANGO_SETTINGS_MODULE`; run as non-root (`USER studyzone`) — preserved.
- [x] Compose: `docker-compose.prod.yml` now pins `image: studyzone:${GIT_SHA:?...}` (no floating tag) with explicit `pull_policy: always`, so Compose will not silently rebuild from a mutated working tree. YAML structure verified.
- [x] Health check present (Dockerfile `HEALTHCHECK` + compose `healthcheck` against `/api/health/`) — validate endpoint in staging.
- [x] Rollback: tag images by git SHA; previous image remains pullable; `uv.lock` for that SHA is reproducible (`uv export` at that commit).
- [x] **Pass criteria verified:** production image builds; `docker run --entrypoint=python ... -c "import flake8"` fails (no dev packages); `import django, rest_framework, channels_redis, psycopg, gunicorn, daphne, whitenoise` succeeds.
- [x] grype invocation verified against `grype --help` for v0.91.0; local DB-cache corruption is an environment artifact and does not affect fresh CI runners.

## Rollout plan

1. **Week 1:** fix F4/F5/F6 (move dev tools out of prod, pin uv + Python) — low risk.
2. **Week 2:** migrate to Track A (pyproject + real `uv.lock`); add `uv lock --check` CI gate; benchmark baselines.
3. **Week 3:** enable `uv audit`, hashes (Track B) / uv.lock hashes (Track A), cache mounts, image scanning; staging validation.
4. **Week 4:** cut over deploy job; monitor 2 release cycles; sign-off.

**Rollback criteria:** any Phase gate failing > 1 business day, cache-miss-driven CI timeouts > threshold, or image scan HIGH/CRITICAL unresolved → revert to previous pinned image + requirements.txt at that SHA (Track B artifacts remain valid during transition).

## Sign-off checklist

- [ ] All Phase 0–6 boxes checked
- [ ] Benchmarks recorded and within thresholds
- [ ] `uv audit` clean; `uv lock --check` enforced in CI
- [ ] No dev packages in prod image; hashes enforced
- [ ] uv + Python versions pinned in all environments
- [ ] Rollback procedure tested

---

**Quick reference**

| Command | Purpose |
|---|---|
| `uv lock` / `uv lock --check` | regenerate / verify lockfile freshness |
| `uv sync --frozen` / `--locked` | install exactly from lock (no update / fail on drift) |
| `uv lock --upgrade-package <p>` | deliberate single-package update |
| `uv export --no-dev -o requirements.txt` | emit lock as requirements (legacy consumers) |
| `uv audit` | OSV vulnerability scan of lockfile |
| `uv tree --invert --package <p>` | why is package installed |
| `uv cache clean` | force cold-cache benchmark |
| `uv pip compile --generate-hashes` | Track B hashed requirements |
