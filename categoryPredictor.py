import pickle
import warnings
import os
from functools import lru_cache

from colors import dataset

warnings.filterwarnings("ignore")

@lru_cache(maxsize=3)
def load_model(model_path):
    """Load a model while keeping at most three classifiers resident.

    A prediction needs the education model, category model, and one subcategory
    model. An unbounded cache eventually retained the complete 1.9 GB model set
    and exceeded Streamlit Community Cloud's memory limit.
    """
    try:
        with open(model_path, "rb") as model_file:
            return pickle.load(model_file)
    except Exception as e:
        raise Exception(f"Error loading model from {model_path}: {str(e)}")

def predictCategoryFor(url=None, text=None):
    """
    Predict the educational category for a YouTube video.
    
    Args:
        url: YouTube video URL
        
    Returns:
        Tuple of (educational status, category, subcategories, subcategory probabilities)
    """
    try:
        # Get the absolute path to the models directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(current_dir, "models")
        
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
        education_model_path = os.path.join(models_dir, "educated_model.pkl")
        education_model = load_model(education_model_path)
        education_prediction = education_model.predict(samples)[0]

        if education_prediction == 0:
            # Educational content - get category
            category_model_path = os.path.join(models_dir, "cat_model.pkl")
            category_classifier = load_model(category_model_path)
            
            category_idx = category_classifier.predict(samples)[0]
            category_prediction = categories[category_idx]
            
            # Get subcategory probabilities
            sub_cat_model_path = os.path.join(models_dir, f"{category_prediction.lower().replace(' ', '_')}_model.pkl")
            sub_cat_clf = load_model(sub_cat_model_path)
            
            sub_cat_pred = sub_cat_clf.predict_proba(samples)[0]
            sub_cat_pred *= 100
            subs = sorted(dataset[category_prediction])

            return ("Educational", category_prediction, subs, sub_cat_pred)
        else:
            return ("Non Educational", "", [], [])
    
    except Exception as exc:
        raise RuntimeError(f"Could not classify this video: {exc}") from exc


# print(predictCategoryFor(url="https://www.youtube.com/watch?v=bdCX8Nb_2Mg"))
