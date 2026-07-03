# HARM Bot

HARM Bot is a Streamlit application that analyzes educational content on
YouTube. It was originally created as a hackathon project and has been updated
as a standalone project.

The app provides six workflows:

1. Predict whether a video is educational and classify its subject.
2. Analyze recent videos from a channel and export the results as CSV.
3. Search YouTube and classify the returned videos.
4. Analyze every public video in a playlist.
5. Estimate the educational portion of a video from its transcript, with a
   title-and-description fallback when captions are unavailable.
6. Turn a playlist or channel into a downloadable learning path: filter
   non-educational videos, group them by topic, order introductory material
   before advanced material, estimate known study time, and suggest preparation.

## Learning Path Generator

Choose **Learning Path Generator** in the sidebar and provide either a YouTube
playlist URL or a channel URL/handle. For channels, choose how many recent
videos to consider. The generator uses the existing HARM Bot models locally;
it does not require a paid AI service or API key.

The resulting table explains each video's predicted topic, confidence, learning
level, duration when YouTube exposes it, and suggested preparation. The complete
plan can be downloaded as CSV for analysis or Markdown for notes and portfolios.
The beginner/intermediate/advanced order is based on transparent wording in the
title and description, so users can review and adjust it for their background.

## Architecture

```text
app.py                  Streamlit UI and six page workflows
youtube_service.py      Keyless yt-dlp client with PyTubeFix fallback
categoryPredictor.py    Educational, category, and subcategory inference
eduContentPredictor.py  Transcript analysis with metadata fallback
learning_path.py        Educational filtering, grouping, ordering, and export
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
`harm-env` from the repository root. A virtual environment should be
recreated from the lock on each computer rather than copied between computers:

```bash
python3.11 -m venv harm-env
source harm-env/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements.lock
streamlit run app.py
```

Open `http://localhost:8501` if it does not open automatically. On later runs,
only activate the existing environment and start Streamlit:

```bash
source harm-env/bin/activate
streamlit run app.py
```

Use `deactivate` when finished. The environment directory is local-only and is
excluded from Git; the small lock files are what make it reproducible. No API
key, account, or Streamlit secret is needed.

## GitHub setup

The trained models are larger than GitHub's normal file limit, so Git LFS is
required.

```bash
git lfs install
git branch -M main
git remote add origin https://github.com/Harshul-18/harm-bot.git
git push -u origin main
```

The included `.gitattributes` already tracks every `models/*.pkl` file with
Git LFS.

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
