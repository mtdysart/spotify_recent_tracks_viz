#!/usr/bin/env python
# coding: utf-8
from bokeh.plotting import figure, curdoc
from bokeh.layouts import row, column
import sqlalchemy
import pandas as pd
import datetime
import numpy as np
from datetime import date
from scatter import Scatter
from barchart import BarChart


played_tracks_df = pd.read_csv("spotify_recent_tracks_viz/data/track_plays.csv")
audio_features_df = pd.read_csv("spotify_recent_tracks_viz/data/audio_features.csv")

# Convert duration_ms to duration in seconds
audio_features_df['duration_ms'] = np.round(audio_features_df['duration_ms'] / 1000)
audio_features_df = audio_features_df.rename({'duration_ms': 'duration_s'}, axis=1)

# Join both dataframes and clean up date/time data
merged_df = pd.merge(played_tracks_df, audio_features_df, how="left", on="track_id")

def create_date_and_time(row):
    row['played_at'] = pd.to_datetime(row['played_at'])
    row['date_played'] = pd.to_datetime(row['played_at'].date())
    row = row.rename({"played_at": "time_played"})
    row['time_played'] = row['time_played'].time()
    return row
    
merged_df = merged_df.apply(create_date_and_time, axis=1)

# Create application layout
bok_scatter = Scatter(merged_df)
bok_bar = BarChart(merged_df.drop(['danceability', 'energy', 'loudness', 'speechiness', 'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo', 'duration_s'], axis=1))
layout = column(bok_scatter.layout, bok_bar.layout)

curdoc().add_root(layout)



