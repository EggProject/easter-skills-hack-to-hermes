# easter-hermes-sorry-skills

[Magyar leírás](README.hu.md) | [Detailed documentation](docs/README.md) | [License](LICENSE)

This project improves how Hermes Agent works with skills. It adds clearer skill
guidance to Hermes, reminds the agent when an installed skill is relevant, and
includes a simple report about enabled skills.

It provides:

- a patcher for the supported Hermes version;
- a Hermes plugin that suggests relevant skills before an LLM call;
- a Hermes-compatible `skill-creator`;
- a read-only skill report.

Supported Hermes commit: `a4973c3f11d9cc92da986cbe150d1e79d094626f`.

## Requirements

- Python 3.14 or newer
- Hermes Agent
- Git

You do not need `uv` for normal use.

## Install

Clone the repository:

```bash
git clone https://github.com/EggProject/easter-skills-hack-to-hermes.git
cd easter-skills-hack-to-hermes
```

Copy the plugin and the `skill-creator` skill into Hermes:

```bash
mkdir -p "$HOME/.hermes/plugins" "$HOME/.hermes/skills"
cp -R plugin/easter-hermes-sorry-skills-plugin "$HOME/.hermes/plugins/"
cp -R skills/skill-creator "$HOME/.hermes/skills/"
```

If either destination already exists, remove it or back it up before copying.
The [detailed install guide](docs/getting-started.md) includes safe upgrade
steps.

Enable the plugin in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - easter-hermes-sorry-skills-plugin
```

Check the Hermes patch without changing files:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh --dry-run
```

If the plan looks correct, apply it:

```bash
bash scripts/easter-hermes-sorry-skills-patch-hermes.sh
```

## Skill Report

```bash
bash scripts/easter-hermes-sorry-skills-report.sh
```

The reporter only reads Hermes data unless you explicitly request a JSON output
file.

## More Documentation

- [Installation and upgrades](docs/getting-started.md)
- [Commands and options](docs/commands.md)
- [Plugin configuration](docs/plugin.md)
- [Development](docs/development.md)
- [Release process](docs/operations.md)

## License

The project is distributed under the [MIT License](LICENSE). The migrated
`skill-creator` retains its own license in
[`skills/skill-creator/LICENSE.txt`](skills/skill-creator/LICENSE.txt).
