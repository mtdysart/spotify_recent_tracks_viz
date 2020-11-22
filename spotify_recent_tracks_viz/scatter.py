from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Select, TextInput, DateRangeSlider, HoverTool, CheckboxGroup, Label
from bokeh.layouts import row, column
import pandas as pd
import datetime
from datetime import date
import statsmodels.api as sm
import numpy as np
import html

class Scatter:

    # X axis choices
    AXIS_MAP = {
        "Tempo": "tempo",
        "Duration (sec)": "duration_s",
        "Danceability": "danceability",
        "Energy": "energy",
        "Loudness": "loudness",
        "Speechiness": "speechiness",
        "Acousticness": "acousticness",
        "Instrumentalness": "instrumentalness",
        "Liveness": "liveness",
        "Valence": "valence"
    }

    # Tooltips for circle glyphs
    CIRC_TOOLTIPS = [
        ("Track", "@track_name"),
        ("Artist", "@artist_name"),
        ("Times Played", "@count")
    ]

    def __init__(self, df: pd.DataFrame):
        # Initialize data sources for scatter plot and regression line
        self.backing_df = df
        self.circ_source = ColumnDataSource({'x': [], 'y': [], 'track_name': [], 'artist_name': [], 'count': [], 'circle_size': []})
        self.line_source = ColumnDataSource({'x': [], 'y_pred': []})

        # Initialize widgets
        self.x_axis = Select(title="X Axis", options=list(self.AXIS_MAP.keys()), value="Tempo")
        self.y_axis = Select(title="Y Axis", options=list(self.AXIS_MAP.keys()), value="Duration (sec)")

        time_start = datetime.datetime(1970, 1, 1, hour=0, minute=0, second=0)
        time_end = datetime.datetime(1970, 1, 1, hour=23, minute=59, second=59)

        start_date = min(self.backing_df['date_played'])
        start_dt = datetime.datetime(year=start_date.year, month=start_date.month, day=start_date.day, hour=0, minute=0, second=0)
        end_date = max(self.backing_df['date_played'])
        end_dt = datetime.datetime(year=end_date.year, month=end_date.month, day=end_date.day, hour=23, minute=59, second=59) 

        date_step_size = 1000*60*60*24 # Step size of 1 day in ms
        self.date_slider = DateRangeSlider(title="Date Range", start=start_dt, end=end_dt, value=(start_dt, end_dt), format="%d %b %Y", step=date_step_size)
        time_step_size = 1000*60*30 # 30 minues in ms
        self.time_slider = DateRangeSlider(title="Time Range", value=(time_start, time_end), start=time_start, end=time_end, format="%X", step=time_step_size)

        self.track_name = TextInput(title="Song name includes")
        self.artist_name = TextInput(title="Artist name includes")
        self.reg_line_check = CheckboxGroup(labels=["Add Regression Line"], active=[])

        # Create the hover tools
        self.points_hover = HoverTool(tooltips=self.CIRC_TOOLTIPS, names=["circles"])
        self.line_hover = HoverTool(tooltips=[], names=["reg_line"])

        # Create the scatter plot and regression line
        self.plot = figure(title="Scatter", plot_height=450, plot_width=800, tools=[self.points_hover, self.line_hover])
        self.plot.circle(x="x", y="y", source=self.circ_source, size="circle_size", fill_alpha=0.6, name="circles")
        self.reg_line = self.plot.line(x='x', y='y_pred', source=self.line_source, color='#FFAF87', name="reg_line")

        self.layout = row(column(self.x_axis, self.y_axis, self.date_slider, self.time_slider, self.track_name, self.artist_name, self.reg_line_check), 
                        self.plot)
        
        # Fill data and create events for on change
        self.update()
        self.on_change()

    def on_change(self):
        """
        Creates on change events for all widgets in the scatter plot.
        """

        widgets = [self.x_axis, self.y_axis, self.date_slider, self.time_slider, self.track_name, self.artist_name]
        for control in widgets:
            control.on_change("value", lambda attr, old, new : self.update())

        self.reg_line_check.on_change("active", lambda attr, old, new : self.update())
    
    def update(self):
        """
        Updates the data source and regression line based on current values of all widgets.
        """

        new_df = self.get_selected()

        # Get number of individual plays and then remove duplicate tracks for plotting
        num_plays = len(new_df)
        new_df.drop_duplicates(subset='track_id', inplace=True)

        # Choose the x and y axis
        x_name = self.AXIS_MAP[self.x_axis.value]
        y_name = self.AXIS_MAP[self.y_axis.value]
        self.plot.xaxis.axis_label = self.x_axis.value
        self.plot.yaxis.axis_label = self.y_axis.value

        # Calculate correlation coefficient between x and y axis
        corr = np.corrcoef(new_df[x_name], new_df[y_name])[0, 1] if not new_df.empty else 0
        self.plot.title.text = f"{num_plays} track plays selected, correlation: {round(corr, 2)}"
        
        # Provide the new selected data to the Data Source
        data_dict = {
            'x': new_df[x_name],
            'y': new_df[y_name],
            'track_name': new_df['song_name'],
            'artist_name': new_df['artist_name'],
            'count': new_df['counts'],
            'circle_size': new_df['circle_size']
        }
        
        self.circ_source.data = data_dict

        # Update the regression line if more than one track is selected
        if len(new_df) <= 1:
            self.reg_line.visible = False

        else:
            x = sm.add_constant(new_df[x_name])
            reg_model = sm.OLS(new_df[y_name], x)
            results = reg_model.fit()
            y_pred = list(map(lambda x : results.params.iloc[1] * x + results.params.iloc[0], new_df[x_name]))

            reg_data_dict = {
                'x': new_df[x_name],
                'y_pred': y_pred
            }

            self.line_source.data = reg_data_dict

            # Update hover tool for regression line
            self.line_hover.tooltips = [
                ("Y=", f"{round(results.params.iloc[1], 2)}x + {round(results.params.iloc[0], 2)}"),
                ("R\u00b2", str(round(results.rsquared, 2)))
            ]

            self.reg_line.visible = (len(self.reg_line_check.active) > 0)

    def get_selected(self):
        """
        Filter data based on widget values. Returns filtered DataFrame
        """
        df = self.backing_df
        
        if not self.track_name.value.isspace():
            df = df[df['song_name'].str.lower().str.contains(self.track_name.value.strip().lower())]
        
        if not self.artist_name.value.isspace():
            df = df[df['artist_name'].str.lower().str.contains(self.artist_name.value.strip().lower())]
            
        # Filter by date played
        date_begin = pd.to_datetime(self.date_slider.value[0], unit='ms')
        date_end = pd.to_datetime(self.date_slider.value[1], unit='ms')
        df = df[(date_begin <= df['date_played']) & (df['date_played'] <= date_end)]

        # Filter by time played
        time_begin = pd.to_datetime(self.time_slider.value[0], unit='ms').time()
        time_end = pd.to_datetime(self.time_slider.value[1], unit='ms').time()
        df = df[(time_begin <= df['time_played']) & (df['time_played'] <= time_end)]

        # Join the counts and circle size columns to the df
        df = self.get_selected_counts(df)
        
        return df

    def get_selected_counts(self, df):
        """
        If no tracks are selected, simply join empty columns for counts and circle_size.
        Otherwise, compute the counts and circle sizes, and join those columns to the df.

        Arguemnts:
            -df : filtered DataFrame

        Returns filtered DataFrame with additional columns for counts and circle_size.
        """
        
        if df.empty:
            df['counts'] = pd.Series([])
            df['circle_size'] = pd.Series([])
            return df

        df_counts = df.groupby(['song_name', 'artist_name']).size().reset_index(name='counts')
        df_counts = df_counts.apply(self.apply_circle_sizes, axis=1)
        return pd.merge(df, df_counts, on=['song_name', 'artist_name'], how='left')

    def apply_circle_sizes(self, row):
        """
        Determines the size of each circle based on the number of times that track has been played.
        """

        if row['counts'] == 1:
            row['circle_size'] = 5
        elif 1 < row['counts'] <= 5:
            row['circle_size'] = 7
        elif row['counts'] > 5:
            row['circle_size'] = 10

        return row

        


