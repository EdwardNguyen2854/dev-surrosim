## What changed

<!-- One paragraph, plain language. What behaviour is different now? -->

## Why

<!-- The problem this solves, with a link to the issue if there is one. -->

## Evidence

<!-- Required for any claim about accuracy, speed, or a fixed bug. -->
- [ ] Test added or updated (fails before, passes after)
- [ ] `python -m pytest -q -m "not solver"` passes
- [ ] `python -m pytest -q -m "solver"` passes, or a reason it could not run
- [ ] `npm run build` passes in `apps/web`, if the web app changed
- [ ] Report or table added under `reports/` for numerical claims
- [ ] CHANGELOG entry under `Unreleased`

## Provenance impact

<!-- Dataset schema, model registry hashes, or trained artefacts changed? Say so. -->
- [ ] No committed dataset or model artefact changed
- [ ] Dataset or model artefacts changed, and the registry metadata plus hashes were updated

## Checklist

- [ ] Commits are signed off (`git commit -s`), per CONTRIBUTING.md
- [ ] No secrets, absolute local paths, or new large binaries committed
- [ ] Documentation updated if user-facing behaviour changed
