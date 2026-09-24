# FAANGTrail

FAANGTrail is a local-first programming practice app built on the FAANGTrail roadmap. It provides a desktop GUI where you can browse challenges, write Python solutions, and run them with your local interpreter. A CLI is also included for automation.

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e '.[dev,ai]'
faangtrail-gui
faangtrail list
faangtrail run two-sum --code "print('skeleton ready')"
faangtrail fetch-testcases
python -m pytest
```

The GUI lets you select a roadmap challenge, edit its starter function, and click **Run tests**. Each challenge runs its bundled assertions in the local Python interpreter and displays stdout, tracebacks, pass/fail status, and timeouts. You can optionally configure an OpenAI API key through the **API key** button and request only the time and space complexity of the current solution. The key is stored in the system credential manager and code is sent to OpenAI only when you explicitly request analysis. Challenge metadata and tests are kept in `src/faangtrail/data/roadmap.json`. The full problem catalog is stored in `src/faangtrail/data/problems/`, including descriptions, examples, constraints, and language templates. The desktop app uses Tkinter from the Python standard library, so no web server or account is required.

## Packaging

Install the optional build dependency and run the platform script:

```bash
python -m pip install -e '.[build]'
# Windows PowerShell
./scripts/build_windows.ps1
# macOS
./scripts/build_macos.sh
```

The Windows script produces `dist/FAANGTrail.exe`. The macOS script creates `dist/FAANGTrail-macos.zip`. Both launch the desktop GUI.

Pushing a version tag such as `v0.1.0` runs the GitHub Actions release workflow. It builds native Windows, macOS, and Linux packages and attaches them to the generated GitHub Release. Pull requests and pushes to `main` run the same builds as validation without publishing a release.

## Roadmap source

This project is initialized from the repository's existing FAANG prep roadmap: [adityakk29/FAANGTrail](https://github.com/adityakk29/FAANGTrail). The app layer is intentionally separate from the roadmap data so that upstream content can evolve independently.