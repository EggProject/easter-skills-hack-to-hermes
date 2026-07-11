# 📦 Operations

[Magyar verzio](operations.hu.md) | [Docs](README.md)

This page is for maintainers preparing a handoff or release. It uses the
development environment from [Development](development.md). End users should
start with [User install](getting-started.md), which uses release wrappers and
does not require `uv`.

## Verify Before Handoff

Run the local gate before pushing documentation or code changes:

```bash
uv run --locked pytest -q
uv run --locked pre-commit run --all-files --show-diff-on-failure
```

For patch compatibility, validate the supported Hermes checkout:

```bash
uv run --locked easter-hermes-sorry-skills-patch-hermes \
  --dry-run
```

## Build Release Artifacts

```bash
scripts/build-release.sh
```

The build writes:

| Artifact | Purpose |
| --- | --- |
| `dist/easter-hermes-sorry-skills.pyz` | Single-file Python zipapp. |
| `dist/easter-hermes-sorry-skills-v0.1.0.tar.gz` | Release bundle with wrappers, plugin payload, skill payload, and READMEs. |

`dist/` should contain the latest release artifact after release-facing files
change.

## Wrapper Scripts

The release bundle includes:

```text
plugin/easter-hermes-sorry-skills-plugin/
skills/skill-creator/
scripts/easter-hermes-sorry-skills-patch-hermes.sh
scripts/easter-hermes-sorry-skills-report.sh
```

The plugin and skill directories are copied into Hermes by the operator. The
wrappers find the `.pyz` in nearby `dist/` locations and execute the matching
entry point. This is the user-facing execution path after the bundle is built.

## CI Shape

The GitHub workflow separates the work into parallel jobs:

| Job | Purpose |
| --- | --- |
| `lint` | Sync deps, build `.pyz` for wrapper smoke tests, run pre-commit. |
| `test-python` | Run pytest with 100% coverage gate. |
| `test-bats` | Run shell wrapper smoke tests. |
| `static-safety` | Check source for real silencer comments. |
| `build-package` | Build release zipapp as packaging smoke test. |

## Release Checklist

1. Run tests and pre-commit.
2. Run Hermes patcher dry-run.
3. Rebuild `dist/` when release-facing files changed.
4. Push the feature branch and wait for green PR checks.
