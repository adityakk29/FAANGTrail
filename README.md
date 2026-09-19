# FAANGTrail

FAANGTrail is a local-first programming practice app built on the FAANGTrail roadmap. The first milestone is a Python CLI that discovers roadmap challenges and executes submitted Python code with the user's local interpreter.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev]'
faangtrail list
faangtrail run two-sum --code "print('skeleton ready')"
python -m pytest
```

The CLI never sends source code to a remote service. Challenge metadata is kept in `src/faangtrail/data/roadmap.json`; future milestones can add the interactive desktop UI without changing the runner contract.

## Packaging

Install the optional build dependency and run the platform script:

```bash
python -m pip install -e '.[build]'
# Windows PowerShell
./scripts/build_windows.ps1
# macOS
./scripts/build_macos.sh
```

The Windows script produces `dist/FAANGTrail.exe`. The macOS script creates `dist/FAANGTrail-macos.zip`.

Pushing a version tag such as `v0.1.0` runs the GitHub Actions release workflow. It builds native Windows, macOS, and Linux packages and attaches them to the generated GitHub Release. Pull requests and pushes to `main` run the same builds as validation without publishing a release.

## Roadmap source

This project is initialized from the repository's existing FAANG prep roadmap: [adityakk29/FAANGTrail](https://github.com/adityakk29/FAANGTrail). The app layer is intentionally separate from the roadmap data so that upstream content can evolve independently.