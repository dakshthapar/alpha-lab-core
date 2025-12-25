# External Libraries

This directory contains external dependencies included as git submodules.

## ABIDES (Agent-Based Interactive Discrete Event Simulator)

The `abides/` directory contains the full ABIDES market simulation framework from JPMorgan Chase & Co.

### Setup

If you cloned this repository and the `abides/` directory is empty, initialize the submodule:

```bash
git submodule update --init --recursive
```

### Updating ABIDES

To update to the latest version of ABIDES:

```bash
git submodule update --remote libs/abides
```

### Repository Information

- **Source**: https://github.com/jpmorganchase/abides-jpmc-public
- **License**: Apache 2.0
- **Current Commit**: Run `git submodule status` from project root to see the pinned version

### Troubleshooting

**Problem**: `libs/abides` directory is empty after cloning

**Solution**: Run `git submodule update --init --recursive` from the project root

**Problem**: Import errors when trying to use ABIDES

**Solution**: Make sure you've installed ABIDES in editable mode:
```bash
cd libs/abides/abides-core && pip install -e .
cd ../abides-markets && pip install -e .
```
