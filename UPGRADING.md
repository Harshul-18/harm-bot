# Reproducibility and upgrades

This repository deliberately separates human-reviewed requirements from the
machine-generated environment lock:

- `.python-version` pins Python 3.11.15.
- `requirements.in` lists the direct dependencies chosen for the app.
- `requirements.lock` pins every transitive dependency and its package hashes.
- `requirements.txt` points Streamlit Community Cloud at that lock.
- Git preserves every known-good lock so an upgrade can be reverted exactly.

## Recreate the known-good environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements.lock
python -m pip check
python -m unittest discover -s tests -v
```

The model files were created with an older scikit-learn estimator format.
Do not upgrade Python, `scikit-learn`, or `numpy` casually: retrain or migrate
the models first and re-run every model test.

## Upgrade a YouTube provider

When YouTube changes its site, update the primary provider first. If only the
fallback is broken, update PyTubeFix independently.

1. Create a branch and change only the intended versions in `requirements.in`.
2. Regenerate the complete lock with the same Python target:

   ```bash
   uv pip compile requirements.in \
     --output-file requirements.lock \
     --generate-hashes \
     --universal \
     --python-version 3.11
   ```

3. Recreate a clean virtual environment from the lock.
4. Run the deterministic suite and both live provider checks:

   ```bash
   python -m unittest discover -s tests -v
   python scripts/smoke_youtube.py --full
   python scripts/smoke_youtube.py --fallback
   ```

5. Start Streamlit and click through all five workflows before merging.
6. Commit `requirements.in` and `requirements.lock` together. If production
   regresses, revert that commit to restore the last complete environment.

Dependabot checks monthly for ordinary Python updates but intentionally ignores
`scikit-learn` and `numpy`; those are compatibility constraints for the trained
model artifacts, not forgotten dependencies.

## Operational notes

`yt-dlp` is primary because it is actively maintained and supports search,
videos, playlists, and channels. PyTubeFix follows a different extraction path
and is used automatically after a primary failure. Captions use
`youtube-transcript-api` and already have an in-app metadata fallback.

Both metadata providers use public YouTube web interfaces. A new YouTube
anti-bot or player change may require a provider update, a supported token
configuration, or a different host IP. Never hide that condition with static
hard-coded video results: the live smoke test should fail loudly so the lock can
be upgraded deliberately.
