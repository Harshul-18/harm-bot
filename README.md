# HARM Bot

HARM Bot is a Streamlit application that analyzes educational content on
YouTube. It was originally created as a hackathon project and has been updated
as a standalone portfolio project by Harshul Nanda.

The app retains its original five workflows:

1. Predict whether a video is educational and classify its subject.
2. Analyze recent videos from a channel and export the results as CSV.
3. Search YouTube and classify the returned videos.
4. Analyze every public video in a playlist.
5. Estimate the educational portion of a video from its transcript, with a
   title-and-description fallback when captions are unavailable.

## What changed

- Preserved all 16 trained models that are used by the application.
- Removed three unused model artifacts and the obsolete model downloader.
- Replaced the broken YouTube integration with keyless `yt-dlp` extraction and
  an independent PyTubeFix fallback. No developer key or quota is required.
- Replaced the old transcript integration with `youtube-transcript-api`.
- Updated Streamlit while retaining the original pages, branding, and behavior.
- Added bounded caches, retries, clearer errors, reliable URL parsing, tests,
  CSV export, and a visible sidebar reopen control.
- Locked Python and every direct/transitive package version with integrity
  hashes, with a documented upgrade and rollback workflow.
- Removed old hosting metadata, team references, and unrelated external links.

## Architecture

```text
app.py                  Streamlit UI and five page workflows
youtube_service.py      Keyless yt-dlp client with PyTubeFix fallback
categoryPredictor.py    Educational, category, and subcategory inference
eduContentPredictor.py  Transcript analysis with metadata fallback
statsViewer.py          Channel table, summary, chart, and CSV export
colors.py               Model label taxonomy
models/                 16 trained scikit-learn pipelines (Git LFS)
scripts/                Live integration smoke test
tests/                  Provider, model, and Streamlit regression tests
```

## Local setup

The trained models require the pinned Python and scikit-learn runtime because
they are serialized estimators. The `.python-version` file records Python
`3.11.15`.

To keep the environment inside this project, create it with the name
`harm-keyless-env` from the repository root. A virtual environment should be
recreated from the lock on each computer rather than copied between computers:

```bash
python3.11 -m venv harm-keyless-env
source harm-keyless-env/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements.lock
streamlit run app.py
```

Open `http://localhost:8501` if it does not open automatically. On later runs,
only activate the existing environment and start Streamlit:

```bash
source harm-keyless-env/bin/activate
streamlit run app.py
```

Use `deactivate` when finished. The environment directory is local-only and is
excluded from Git; the small lock files are what make it reproducible. No API
key, account, or Streamlit secret is needed.

## Test

Run the deterministic regression suite:

```bash
python -m unittest discover -s tests -v
```

Optionally verify YouTube's current public interfaces over the network:

```bash
python scripts/smoke_youtube.py --full
python scripts/smoke_youtube.py --fallback
```

The first command checks video metadata, search, playlist, channel, and
captions. The second deliberately disables the primary extractor and verifies
PyTubeFix. See [UPGRADING.md](UPGRADING.md) before changing dependencies.

## GitHub setup

The trained models are larger than GitHub's normal file limit, so Git LFS is
required.

```bash
git lfs install
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/harm-bot.git
git push -u origin main
```

The included `.gitattributes` already tracks every `models/*.pkl` file with
Git LFS.

## Deploy on Streamlit Community Cloud

1. Push this repository, including all Git LFS objects, to GitHub.
2. Open [Streamlit Community Cloud](https://share.streamlit.io/) and create an
   app from the repository.
3. Select `app.py` as the entrypoint and Python 3.11 in Advanced settings.
4. Deploy and test all five pages from the public app URL.

`requirements.txt` delegates to the hash-locked `requirements.lock`, so cloud
and local installations resolve to the same package set. There are no secrets
to configure.

## Free-service boundaries

This design has no YouTube Data API quota and all application libraries are
free/open source. It reads YouTube's public web interfaces, which are not a
permanent API contract: YouTube can change them or block automated requests
from a cloud IP. The dual-provider design, pinned runtime, live smoke test, and
Git history make those changes quicker to detect, upgrade, and roll back, but
no keyless YouTube library can honestly guarantee lifetime availability.

If captions are absent or blocked, HARM Bot falls back to a metadata-based
educational assessment instead of failing the page.

## License

Released under the [MIT License](LICENSE).
