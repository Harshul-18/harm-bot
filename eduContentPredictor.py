from youtube_transcript_api import YouTubeTranscriptApi
from pathlib import Path

from categoryPredictor import load_model
from youtube_service import VideoData, extract_video_id


EDUCATION_MODEL = Path(__file__).resolve().parent / "models" / "educated_model.pkl"


def _metadata_fallback(video: VideoData) -> str:
    education_model = load_model(str(EDUCATION_MODEL))
    prediction = education_model.predict([video.prediction_text])[0]
    if prediction == 0:
        return (
            "A transcript was not available, but this video appears to be "
            "educational based on its title and description."
        )
    return (
        "A transcript was not available, and this video does not appear to be "
        "educational based on its title and description."
    )

def eduContentPrediction(url, video=None, progress_callback=None):
    """
    Predict the educational content percentage in a YouTube video.
    
    Args:
        url: YouTube video URL
        
    Returns:
        String describing the educational content percentage
    """
    try:
        video_id = extract_video_id(url)
        segments = YouTubeTranscriptApi().fetch(video_id, languages=["en"])
        E = 0
        NonE = 0
        education_model = load_model(str(EDUCATION_MODEL))

        texts = [segment.text for segment in segments]
        batch_size = 100
        for start in range(0, len(texts), batch_size):
            predictions = education_model.predict(texts[start : start + batch_size])
            E += sum(int(prediction == 0) for prediction in predictions)
            NonE += sum(int(prediction != 0) for prediction in predictions)
            if progress_callback:
                progress_callback(min((start + batch_size) / len(texts), 1.0))

        # Avoid division by zero
        if E + NonE == 0:
            return "Could not analyze the educational content of this video."
            
        return "The {:.2f}% portion of this video is educational.".format(E*100/(E+NonE))
    except Exception:
        if video is None:
            raise RuntimeError("The transcript for this video is not available.")
        return _metadata_fallback(video)

# print(eduContentPrediction("https://www.youtube.com/watch?v=OTuph9pJWU4"))
