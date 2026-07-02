# Python 3.11 Standardization (All Social Automation Skills)

## Rule
All scripts MUST use `python3` (Python 3.11). **Never** hardcode machine-specific paths like `/Users/.../venv/bin/python3`.

```bash
PYTHON=python3  # Python 3.11 — pyenv shim or venv, both point to 3.11
```

## Why
- Portability: other agents run on different machines
- Consistency: `python3` is guaranteed 3.11 via pyenv or venv
- Maintenance: one standard, not N machine-specific paths

## Shebangs
All `.py` scripts use `#!/usr/bin/env python3`. If you find a machine-specific shebang (e.g., `#!/Users/maochundong/.../bin/python3`), replace it immediately.

## Applies To
- `xiaohongshu-creator` skill scripts
- `wx-pub` skill scripts
- Future social automation skills (抖音, etc.)
- All SKILL.md examples and documentation

## Migration
If you encounter hardcoded paths, replace ALL occurrences with `python3`. Search for `/hermes-agent/venv/bin/python3` to find leftovers.