# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| `0.1.x` (current public release) | Yes |
| Pre-publication builds | No |

## Reporting a vulnerability

Please **do not** open a public issue for a security problem.

Report it privately through GitHub's
[security advisory](https://github.com/EdwardNguyen2854/surrosim/security/advisories/new)
form. That keeps the details private until a fix is ready.

Please include:

- What is affected (API endpoint, CLI command, desktop shell, dataset or model
  loader).
- Steps to reproduce, or the smallest input that triggers the problem.
- What an attacker could achieve.
- The version or commit you tested.

You can expect an acknowledgement within a few days and an assessment within
about two weeks. Once a fix is released, the report will be credited unless you
ask to stay anonymous.

## Scope

SurroSim runs locally by default and has no authentication layer, so the
service is intended for a trusted machine or a trusted network. Relevant
reports include:

- Remote code execution, path traversal, or command injection through the API,
  job runner, or dataset/model loaders.
- Untrusted model artefacts (for example a `.pt` or `.joblib` file) escaping
  the expected load path.
- Leaked secrets, credentials, or private paths in committed files.
- Dependency vulnerabilities that are actually reachable through this code.

Out of scope:

- A local user with full filesystem access doing whatever they can already do.
- The service being reachable on a network because it was deployed without a
  reverse proxy or authentication. Deploy it behind one.
- Numerical inaccuracy of predictions. That is an engineering-trust issue, not
  a security vulnerability: see
  [limitations and out of scope](docs/limitations_and_out_of_scope.md).

## Handling data and models

- Treat an untrusted `.pt`, `.joblib`, or dataset file like an untrusted
  program. Python model formats can execute code when loaded.
- The bundled CalculiX path (`tools/calculix/ccx.exe`) is git-ignored and
  Windows-only; Docker images do not include it.
- Never commit access tokens, `.env` files, or absolute paths from your own
  machine. `dataset run` writes absolute paths into manifests — rewrite them
  before publishing a new committed dataset.

## Attribution

This policy does not change the terms of the [Apache License 2.0](LICENSE).
