# 🧭 Documentation

[Magyar verzio](README.hu.md) | [Project README](../README.md)

This documentation is organized around the work operators and maintainers do
most often. English is the default language; Hungarian translations live beside
each page as `.hu.md` files.

## Start Here

| Goal | Read |
| --- | --- |
| ⚡ Install and run the first dry-run | [Getting started](getting-started.md) |
| 🧰 Check command flags and examples | [Commands](commands.md) |
| 🧩 Configure the Hermes plugin hook | [Plugin and hooks](plugin.md) |
| 🩹 Validate or apply Hermes patches | [Patching Hermes](patching.md) |
| 🛠️ Use the migrated skill creator | [Skill creator](skill-creator.md) |
| 📦 Build, verify, and release | [Operations](operations.md) |
| 🧪 Work on the repository | [Development](development.md) |
| 🧾 Understand migration decisions | [Migration notes](migration-notes.md) |
| 🪝 Inspect hook decision flows | [WOW skill flowcharts](wow-skills-flowcharts.md) |

## Safety Model

- The supported Hermes source version is commit `30e947e0a`.
- Use `--dry-run --target /tmp/hermes-30e947e0a` to validate a pinned checkout.
- The patcher writes when `--dry-run` is omitted.
- The reporter is read-only unless the operator asks for a JSON output file.
- The plugin injects short runtime context; it does not mutate Hermes source.

## Documentation Style

- Commands, flags, paths, environment variables, and package names stay in
  English in both language versions.
- Examples prefer `uv run --locked` so `uv.lock` remains authoritative.
- Mermaid diagrams are kept in the flowchart pages and validated separately.

