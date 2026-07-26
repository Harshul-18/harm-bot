import os
import pickle
import warnings
from functools import lru_cache
from pathlib import Path

from huggingface_hub import hf_hub_download

from colors import dataset

warnings.filterwarnings("ignore")

HF_MODEL_REPO = os.getenv("HF_MODEL_REPO", "dragTheDungeon/harm-models")
LOCAL_MODELS_DIR = Path(__file__).resolve().parent / "models"


def get_model_path(filename: str) -> str:
    """Resolve a model artifact from the local models/ folder or Hugging Face Hub."""
    local_path = LOCAL_MODELS_DIR / filename
    if local_path.exists():
        return str(local_path)
    return hf_hub_download(
        repo_id=HF_MODEL_REPO,
        filename=filename,
        repo_type="model",
    )


@lru_cache(maxsize=3)
def load_model(filename: str):
    """Load a model while keeping at most three classifiers resident.

    A prediction needs the education model, category model, and one subcategory
    model. An unbounded cache eventually retained the complete model set and
    exceeded Streamlit Community Cloud's memory limit. Hugging Face also caches
    downloaded files on disk, so unchanged artifacts are not re-fetched.
    """
    path = get_model_path(filename)
    try:
        with open(path, "rb") as model_file:
            return pickle.load(model_file)
    except Exception as e:
        raise Exception(f"Error loading model {filename} from {path}: {str(e)}")


def predictCategoryFor(url=None, text=None):
    """
    Predict the educational category for a YouTube video.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Tuple of (educational status, category, subcategories, subcategory probabilities)
    """
    try:
        if text is None:
            if not url:
                raise ValueError("A video URL or prediction text is required.")
            from youtube_service import YouTubeService
            import streamlit as st

            video = YouTubeService(st.secrets["YOUTUBE_API_KEY"]).get_video(url)
            text = video.prediction_text

        samples = [text]
        categories = sorted(list(dataset.keys()))
        
        # Load and apply education model
        education_model = load_model("educated_model.pkl")
        education_prediction = education_model.predict(samples)[0]

        if education_prediction == 0:
            # Educational content - get category
            category_classifier = load_model("cat_model.pkl")
            
            category_idx = category_classifier.predict(samples)[0]
            category_prediction = categories[category_idx]
            
            # Get subcategory probabilities
            sub_cat_filename = (
                f"{category_prediction.lower().replace(' ', '_')}_model.pkl"
            )
            sub_cat_clf = load_model(sub_cat_filename)
            
            sub_cat_pred = sub_cat_clf.predict_proba(samples)[0]
            sub_cat_pred *= 100
            subs = sorted(dataset[category_prediction])

            return ("Educational", category_prediction, subs, sub_cat_pred)
        else:
            return ("Non Educational", "", [], [])
    
    except Exception as exc:
        raise RuntimeError(f"Could not classify this video: {exc}") from exc


# print(predictCategoryFor(url="https://www.youtube.com/watch?v=bdCX8Nb_2Mg"))
