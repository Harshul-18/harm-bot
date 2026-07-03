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
- Replaced broken YouTube scraping packages with the official YouTube Data API.
- Replaced the old transcript integration with `youtube-transcript-api`.
- Updated Streamlit and reduced the dependency list from 34 entries to 7.
- Added caching, clearer errors, reliable URL parsing, tests, and CSV export.
- Removed old hosting metadata, team references, and unrelated external links.

## Architecture

```text
app.py                  Streamlit UI and five page workflows
youtube_service.py      YouTube Data API client and URL parsing
categoryPredictor.py    Educational, category, and subcategory inference
eduContentPredictor.py  Transcript analysis with metadata fallback
statsViewer.py          Channel table, summary, chart, and CSV export
colors.py               Model label taxonomy
models/                 16 trained scikit-learn pipelines (Git LFS)
tests/                  API, model-inventory, and Streamlit smoke tests
```

## Local setup

The trained models require Python 3.11 and `scikit-learn==1.1.3` because that is
the compatible release for the original serialized estimators.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

Create a free YouTube Data API v3 key in Google Cloud Console, enable the
YouTube Data API v3, and place the key in `.streamlit/secrets.toml`:

```toml
YOUTUBE_API_KEY = "your-key"
```

The API key file is ignored by Git and must never be committed.

## Test

```bash
python -m unittest discover -s tests -v
```

The model test loads every retained classifier and verifies that each category
has the expected number of trained output classes.

## GitHub setup

The trained models are larger than GitHub's normal file limit, so Git LFS is
required.

```bash
git lfs install
git add .
git commit -m "Modernize HARM Bot"
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
4. Add the following secret in the app settings:

   ```toml
   YOUTUBE_API_KEY = "your-key"
   ```

5. Deploy and test all five pages from the public app URL.

## Free-service boundaries

The YouTube Data API has a free daily quota, which is suitable for a portfolio
app but not unlimited public traffic. Transcript retrieval uses YouTube's public
caption interface; YouTube may block cloud-provider IPs or a video may have no
captions. When that happens, HARM Bot still returns a metadata-based educational
assessment instead of failing the page.

## License

Released under the [MIT License](LICENSE).
