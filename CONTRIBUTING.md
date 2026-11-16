# Contributing to SurroSim

Thanks for taking the time to help. SurroSim is a small project with a strict
rule: **every number it reports must be reproducible and traceable.** That rule
shapes how contributions are reviewed.

## Ways to contribute

- Report a bug or an unclear document in
  [Issues](https://github.com/EdwardNguyen2854/surrosim/issues).
- Reproduce a result and tell us whether you matched it.
- Improve documentation, the plain-language manual, or the web app.
- Add a test, a shape family, a baseline model, or a solver improvement.
- Review an open pull request, especially its claims and evidence.

Small, focused pull requests are much easier to review than large ones. If you
plan something structural — a new shape family, a dataset schema change, a new
model architecture — open an issue first so we can agree on the contract.

## Development setup

Python 3.11 or newer, on Windows, macOS, or Linux.

```bash
python -m venv .venv
# Windows
.venv\Scripts\python.exe -m pip install -e ".[dev,mesh,ml,app,gnn]"
# macOS / Linux
.venv/bin/python -m pip install -e ".[dev,mesh,ml,app,gnn]"
```

The fast test lane is the one CI runs on every push:

```bash
python -m pytest -q -m "not solver"
```

Tests marked `solver` need a real Gmsh and CalculiX installation and skip
themselves when the binaries are missing. If you change geometry, meshing,
boundary conditions, or result parsing, run them:

```bash
python -m pytest -q -m "solver"
python -m surrosim reproduce --profile quick --jobs 4 --ccx ccx
```

The web application is checked by a type-check plus production build:

```bash
cd apps/web
npm ci
npm run build
```

## What a change must include

1. **A test that fails before the change and passes after it.** For solver
   behaviour, add the deterministic case to the `solver` marker.
2. **Evidence, not adjectives.** If a pull request claims an accuracy
   improvement, it must point to a report under `reports/`, a command that
   regenerates it, and the dataset hash it used.
3. **No silent changes to dataset or model artefacts.** Dataset and model
   files record the SHA-256 of their inputs and the git commit that built them.
   Retraining or rebuilding a dataset invalidates registry hash checks, so say
   so explicitly and update the registry metadata.
4. **No new committed binaries** unless they are small model weights that the
   application needs at runtime. Large solver binaries, run directories, meshes
   and scratch output stay out of git (see `.gitignore`).

## Coding conventions

- Python: 4-space indentation, type hints on public functions, no new runtime
  dependency without discussing it first.
- Web: follow `apps/web/DESIGN.md`. Design values live in
  `apps/web/src/tokens.css`, components use Tailwind role names rather than raw
  hex colours, and icons come from the vendored sprite through `Icon.tsx`.
- Documents and reports: plain language first, then the depth. Prefer a table
  of measured values over a claim.
- Commit messages: `type: short imperative summary` (`feat:`, `fix:`,
  `docs:`, `test:`, `refactor:`, `chore:`).

## Licensing of contributions

SurroSim is released under the [Apache License 2.0](LICENSE). By submitting a
pull request you agree that your contribution is licensed under the same terms
(section 5 of the license: inbound equals outbound), and that the project may
distribute it with the existing attribution notices.

Please sign off your commits to confirm you have the right to submit the work:

```bash
git commit -s -m "fix: correct FRD rotation parsing"
```

This adds a `Signed-off-by:` line. Contributions that cannot be signed off
(such as code copied from a project with an incompatible license) cannot be
merged.

## Review process

1. A maintainer checks the change against the rules above.
2. CI must pass: Python unit tests, the solver lane plus quick reproduction,
   and the web build.
3. Behavioural changes need a CHANGELOG entry under `Unreleased`.
4. Merged work is credited through git history and, for substantial
   contributions, in the release notes.

## Reporting security issues

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).
