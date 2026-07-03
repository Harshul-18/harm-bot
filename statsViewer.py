"""Streamlit channel-analysis page support."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from categoryPredictor import predictCategoryFor
from youtube_service import YouTubeService


@st.cache_data
def convert_df(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def generate_channel_video_data(
    of_channel: str,
    with_number_of_videos: int,
    youtube: YouTubeService,
) -> None:
    with st.spinner("Fetching channel videos..."):
        videos = youtube.get_channel_videos(of_channel, with_number_of_videos)

    if not videos:
        st.warning("No public videos were found for this channel.")
        return

    data = {
        "Title": [],
        "URL": [],
        "Category": [],
        "Is Educational?": [],
        "HARM Bot Category": [],
    }
    progress = st.progress(0, text="Analyzing videos...")
    for index, video in enumerate(videos):
        status, category, _, _ = predictCategoryFor(text=video.prediction_text)
        data["Title"].append(video.title)
        data["URL"].append(video.url)
        data["Category"].append(video.category)
        data["Is Educational?"].append(status)
        data["HARM Bot Category"].append(category)
        progress.progress(
            (index + 1) / len(videos),
            text=f"Analyzing videos... {index + 1}/{len(videos)}",
        )
    progress.empty()

    frame = pd.DataFrame(data)
    st.dataframe(
        frame,
        column_config={"URL": st.column_config.LinkColumn("URL")},
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download this dataframe",
        convert_df(frame),
        "channel_analysis.csv",
        "text/csv",
    )

    st.subheader("Channel Summary")
    total_videos = len(frame)
    educational_videos = int((frame["Is Educational?"] == "Educational").sum())
    left, right = st.columns(2)
    left.metric("Total Videos Analyzed", total_videos)
    percentage = int(educational_videos / total_videos * 100)
    right.metric("Educational Videos", f"{educational_videos} ({percentage}%)")

    if educational_videos:
        st.subheader("Category Distribution")
        counts = frame.loc[
            frame["Is Educational?"] == "Educational", "HARM Bot Category"
        ].value_counts()
        st.bar_chart(counts, color="#E11D48")
