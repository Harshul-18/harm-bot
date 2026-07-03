"""HARM Bot — educational YouTube video analysis in Streamlit."""

from __future__ import annotations

import base64
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
from PIL import Image

from categoryPredictor import predictCategoryFor
from eduContentPredictor import eduContentPrediction
from statsViewer import generate_channel_video_data
from youtube_service import YouTubeService, YouTubeServiceError


BASE_DIR = Path(__file__).resolve().parent
ASSET_DIR = BASE_DIR / "assets"
MODEL_DIR = BASE_DIR / "models"
EXPECTED_MODELS = {
    "business_model.pkl",
    "cat_model.pkl",
    "coding_model.pkl",
    "competitive_exams_model.pkl",
    "design_model.pkl",
    "educated_model.pkl",
    "finance_and_accounting_model.pkl",
    "health_and_fitness_model.pkl",
    "it_and_software_model.pkl",
    "lifestyle_model.pkl",
    "marketing_model.pkl",
    "music_model.pkl",
    "office_productivity_model.pkl",
    "personal_development_model.pkl",
    "photography_and_video_model.pkl",
    "teaching_and_academics_model.pkl",
}
APP_BACKGROUND = "#160000"


st.set_page_config(
    page_title="HARM Bot",
    page_icon=Image.open(ASSET_DIR / "harmLogo.ico"),
)


def apply_styles() -> None:
    background = base64.b64encode(
        (ASSET_DIR / "sidebarBackground.jpg").read_bytes()
    ).decode("utf-8")
    st.markdown(
        f"""
        <style>
        #MainMenu, footer {{visibility: hidden;}}
        [data-testid="stHeader"] {{background: transparent;}}
        button[data-testid="stBaseButton-headerNoPadding"] {{
            visibility: visible !important;
        }}
        div.stButton > button:first-child,
        div.stLinkButton > a:first-child {{
            border: 1px solid #FFF;
            border-radius: 20px;
            background: none;
        }}
        div.stButton > button:first-child:hover,
        div.stLinkButton > a:first-child:hover {{
            background: #E11D48;
            color: white;
        }}
        [data-testid="stSidebar"] > div:first-child {{
            background-image: url("data:image/jpeg;base64,{background}");
            background-position: center;
            background-size: cover;
        }}
        .harm-footer {{
            width: 100%;
            padding: 2rem 0 0.5rem;
            text-align: center;
            color: white;
        }}
        .harm-footer a {{color: white; font-weight: bold; text-decoration: none;}}
        .harm-footer a:hover {{color: #E11D48;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def add_sidebar_menu() -> None:
    with st.sidebar:
        st.markdown(
            "**HARM Bot** is an educational YouTube analysis project created "
            "by Harshul Nanda."
        )
        st.markdown("### Project links")
        st.link_button("GitHub", "https://github.com/Harshul-18")
        st.link_button("LinkedIn", "https://www.linkedin.com/in/harshulnanda/")
        st.link_button("Buy me a coffee ☕", "https://www.buymeacoffee.com/HARMBOT")


def add_logo() -> None:
    data = base64.b64encode((ASSET_DIR / "harmLogo.gif").read_bytes()).decode("utf-8")
    st.markdown(
        f'<center><img src="data:image/gif;base64,{data}" '
        'alt="HARM Bot logo" width="300" height="125"></center>',
        unsafe_allow_html=True,
    )


def add_title_text() -> None:
    st.title("Hello, I am a YouTube API Bot!")
    st.text("I am a simple tool, just enter the URL and I will give the statistics.")


def add_footer() -> None:
    st.markdown(
        """
        <div class="harm-footer">
          <p>HARM Bot · Created and designed by
          <a href="https://harshul-18.github.io/Harshul-Site/" target="_blank">
          Harshul Nanda</a>.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def check_models() -> bool:
    missing = sorted(name for name in EXPECTED_MODELS if not (MODEL_DIR / name).exists())
    if missing:
        st.error("Required model files are missing: " + ", ".join(missing))
        return False
    return True


@st.cache_resource
def get_youtube_service() -> YouTubeService:
    return YouTubeService()


def render_prediction(text: str) -> None:
    status, category, subcategories, probabilities = predictCategoryFor(text=text)
    if status != "Educational":
        st.markdown("<h5>This is not an educational video.</h5>", unsafe_allow_html=True)
        return

    st.markdown(
        f"<h5>This video comes under the {category} category.</h5>",
        unsafe_allow_html=True,
    )
    figure, axis = plt.subplots(facecolor=APP_BACKGROUND)
    bars = axis.barh(subcategories, probabilities, color="#E11D48")
    axis.set_facecolor(APP_BACKGROUND)
    axis.tick_params(axis="x", colors="white")
    axis.tick_params(axis="y", colors="white", labelsize=8)
    for spine in axis.spines.values():
        spine.set_color("white")
    axis.bar_label(bars, fmt="%.1f%%", label_type="center", color="white", fontsize=7)
    figure.tight_layout()
    st.pyplot(figure)
    plt.close(figure)


def render_video(video) -> None:
    st.video(video.url)
    st.markdown(f"**Author of this video:** {video.channel_name}")
    st.markdown(f"**Title of video:** {video.title}")
    st.markdown("**Description of video:**")
    st.write(video.description or "No description is available.")


def body_of_page_1() -> None:
    value = st.text_input(
        "Enter the URL of the Youtube Video",
        help="Enter the URL of the YouTube video to analyze.",
    )
    if not value:
        return
    try:
        with st.spinner("Fetching video details..."):
            video = get_youtube_service().get_video(value)
        with st.expander("Prediction"):
            render_prediction(video.prediction_text)
        with st.expander("View Video"):
            render_video(video)
    except (YouTubeServiceError, RuntimeError) as exc:
        st.error(str(exc))


def body_of_page_2() -> None:
    channel = st.text_input(
        "Enter the Channel ID to get the stats of that channel",
        help="You can enter a channel ID, channel URL, handle, or video URL.",
    )
    number = st.number_input("How many videos to analyse?", min_value=5, step=5)
    if not channel:
        return
    try:
        with st.expander("View Statistics", expanded=True):
            generate_channel_video_data(channel, int(number), get_youtube_service())
    except (YouTubeServiceError, RuntimeError) as exc:
        st.error(str(exc))


def body_of_page_3() -> None:
    query = st.text_input("Search for videos")
    number = st.number_input("Show search results", min_value=1, max_value=50, step=1)
    if not query:
        return
    try:
        with st.spinner("Searching YouTube..."):
            videos = get_youtube_service().search_videos(query, int(number))
        if not videos:
            st.warning("No videos were found.")
        for video in videos:
            with st.container(border=True):
                render_video(video)
                with st.expander("Prediction"):
                    render_prediction(video.prediction_text)
    except (YouTubeServiceError, RuntimeError) as exc:
        st.error(str(exc))


def body_of_page_4() -> None:
    playlist = st.text_input("Enter a YouTube playlist url")
    if not playlist:
        return
    try:
        with st.spinner("Fetching playlist videos..."):
            videos = get_youtube_service().get_playlist_videos(playlist)
        progress = st.progress(0, text="Analyzing playlist...")
        for index, video in enumerate(videos):
            with st.container(border=True):
                st.video(video.url)
                with st.expander("Prediction"):
                    render_prediction(video.prediction_text)
            progress.progress((index + 1) / len(videos))
        progress.empty()
    except (YouTubeServiceError, RuntimeError) as exc:
        st.error(str(exc))


def body_of_page_5() -> None:
    value = st.text_input("Enter a Youtube Video URL")
    if not value:
        return
    try:
        with st.spinner("Fetching video details..."):
            video = get_youtube_service().get_video(value)
        progress = st.progress(0, text="Analyzing the transcript...")
        result = eduContentPrediction(
            value,
            video=video,
            progress_callback=lambda amount: progress.progress(amount),
        )
        progress.empty()
        st.markdown(f"### {result}")
    except (YouTubeServiceError, RuntimeError) as exc:
        st.error(str(exc))


def main() -> None:
    apply_styles()
    add_logo()
    add_title_text()
    if check_models():
        pages = {
            "Category Predictor": body_of_page_1,
            "Channel Stats Viewer": body_of_page_2,
            "Search Videos": body_of_page_3,
            "Playlist Videos Predictor": body_of_page_4,
            "Educational Content in a Video": body_of_page_5,
        }
        selected_page = st.sidebar.selectbox("Select the page", pages)
        add_sidebar_menu()
        pages[selected_page]()
    add_footer()


if __name__ == "__main__":
    main()
