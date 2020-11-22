from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Select, DateRangeSlider, HoverTool, FactorRange
from bokeh.transform import dodge
from bokeh.layouts import row, column
import pandas as pd
import datetime
from datetime import date

class BarChart:

    # X axis choices
    AXIS_MAP = {
        "Key": "key",
        "Time Signature": "time_signature"
    }

    # Unicode for sharp and flat symbols
    SHARP = 9839
    FLAT = 9837

    # Map to standard pitch notation
    PITCH_CLASS_MAP = {
        0: 'C',
        1: 'D' + chr(FLAT),
        2: 'D',
        3: 'E' + chr(FLAT),
        4: 'E',
        5: 'F',
        6: 'F' + chr(SHARP),
        7: 'G',
        8: 'A' + chr(FLAT),
        9: 'A',
        10: 'B' + chr(FLAT),
        11: 'B'
    }

    # Map major/minor
    MODE_MAP = {
        0: 'Minor',
        1: 'Major'
    }

    # Bar chart colors
    MAJOR_COLOR = "#e84d60"
    MINOR_COLOR = "#718dbf"

    # Tooltip style for time signature bar chart
    TIME_SIG_TOOLTIPS = [("Count", "@counts")]

    # Tooltip styles for major/minor bar chart
    MAJOR_TOOLTIPS = """
        <div>
            <span style="font-size: 12px; color: #e84d60;">Count: </span>
            <span styel="font-size: 10px;">@major</span>
        </div>    
    """
 
    MINOR_TOOLTIPS = """
        <div>
            <span style="font-size: 12px; color: #718dbf;">Count: </span>
            <span styel="font-size: 10px;">@minor</span>
        </div>    
    """

    def __init__(self, df: pd.DataFrame):
        # Initialize data sources
        self.backing_df = df
        self.bar_source = ColumnDataSource({'x': [], 'counts': []})
        self.dbl_bar_source = ColumnDataSource({'key': [], 'major': [], 'minor': []})

        # Initialize widgets
        self.x_axis = Select(title="X Axis", options=list(self.AXIS_MAP.keys()), value="Key")

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

        # Create the hover tools
        major_hover = HoverTool(tooltips=self.MAJOR_TOOLTIPS, names=['major_bar'])
        minor_hover = HoverTool(tooltips=self.MINOR_TOOLTIPS, names=['minor_bar'])
        time_sig_hover = HoverTool(tooltips=self.TIME_SIG_TOOLTIPS, names=['time_sig_bar'])

        # Create the bar charts
        self.bar_plot = figure(x_range=FactorRange(factors=['2', '3', '4', '5', '6', '7', '8', '9']), title="Bar Chart", plot_height=300, plot_width=800, y_axis_label="Number of Plays", tools=[major_hover, minor_hover, time_sig_hover])

        self.major_bar = self.bar_plot.vbar(x=dodge('key', -0.125, range=self.bar_plot.x_range), top='major', source=self.dbl_bar_source, width=0.2, color=self.MAJOR_COLOR, legend_label="Major", visible=False, name="major_bar")
        self.minor_bar = self.bar_plot.vbar(x=dodge('key', 0.125, range=self.bar_plot.x_range), top='minor', source=self.dbl_bar_source, width=0.2, color=self.MINOR_COLOR, legend_label="Minor", visible=False, name="minor_bar")
        
        self.time_sig_bar = self.bar_plot.vbar(x='x', top='counts', source=self.bar_source, width =0.5, color=self.MINOR_COLOR, visible=True, name="time_sig_bar")

        self.layout = row(column(self.x_axis, self.date_slider, self.time_slider), self.bar_plot)

        # Fill data and create events for on change
        self.update()
        self.on_change()

    def on_change(self):
        """
        Creates on change events for all widgets in the bar chart.
        """

        widgets = [self.x_axis, self.date_slider, self.time_slider]
        for control in widgets:
            control.on_change("value", lambda attr, old, new : self.update())

    def update(self):
        """
        Updates the data source and bar chart type based on current values of all widgets.
        """

        # Get the selected data
        new_df = self.get_selected()
        self.bar_plot.title.text = f"{len(new_df)} track plays selected"

        # Choose the x axis
        x_name = self.AXIS_MAP[self.x_axis.value]
        self.bar_plot.xaxis.axis_label = self.x_axis.value

        # Get counts grouped by selected x axis
        agg_df = self.get_bar_counts(new_df, x_name)

        # Provide the new selected data to the Data Source
        if x_name == 'key':
            # Change x range to key bar chart
            keys = list(self.PITCH_CLASS_MAP.values())
            modes = list(self.MODE_MAP.values())
            self.bar_plot.x_range.factors = keys
            
            # Fill in missing data rows with counts of 0
            for key in keys:
                if not key in agg_df['key'].values:
                    agg_df = agg_df.append(pd.DataFrame({'key': [key, key], 'mode': ['Major', 'Minor'], 'counts': [0, 0]}), ignore_index=True)
                
                else:
                    for mode in modes:
                        if not mode in agg_df[agg_df['key'] == key]['mode'].values:
                            agg_df = agg_df.append({'key': key, 'mode': mode, 'counts': 0}, ignore_index=True)
            
            agg_df.sort_values(by=['key', 'mode'], inplace=True)

            data_dict = {
                'key': agg_df['key'].drop_duplicates(),
                'major': agg_df[agg_df['mode'] == 'Major']['counts'],
                'minor': agg_df[agg_df['mode'] == 'Minor']['counts']
            }

            # Update data source and change to display key bar chart
            self.dbl_bar_source.data = data_dict

            self.time_sig_bar.visible = False
            self.bar_plot.legend.visible = True
            self.major_bar.visible = True
            self.minor_bar.visible = True

        else:
            # Add zeros for missing time signatures
            for num in range(2, 10):
                if not num in agg_df['time_signature'].values:
                    agg_df = agg_df.append({'time_signature': num, 'counts': 0}, ignore_index=True)
                
            agg_df.sort_values(by='time_signature', inplace=True)
            self.bar_plot.x_range.factors = list(map(str, range(2, 10)))

            data_dict = {
                'x': agg_df[x_name].astype(str),
                'counts': agg_df['counts'],
            }

            self.bar_source.data = data_dict

            self.major_bar.visible = False
            self.minor_bar.visible = False
            self.bar_plot.legend.visible = False
            self.time_sig_bar.visible = True


    def get_selected(self):
        """
        Filters dataset by date/time ranges. Returns the filtered DataFrame.
        """
        df = self.backing_df

        # Filter by date played
        date_begin = pd.to_datetime(self.date_slider.value[0], unit='ms')
        date_end = pd.to_datetime(self.date_slider.value[1], unit='ms')
        df = df[(date_begin <= df['date_played']) & (df['date_played'] <= date_end)]

        # Filter by time played
        time_begin = pd.to_datetime(self.time_slider.value[0], unit='ms').time()
        time_end = pd.to_datetime(self.time_slider.value[1], unit='ms').time()
        df = df[(time_begin <= df['time_played']) & (df['time_played'] <= time_end)]

        return df

    def get_bar_counts(self, df, x_name):
        """
        Aggregates counts based on either key or time signature.

        Arguments:
            - df: date/time filtered DataFrame
            - x_name: name of column to group by ('key' or 'time_signature')

        Returns DataFrame with counts grouped by x_name (grouped by key and mode if x_name == 'key').
        """

        if x_name == 'key':
            df_counts = df.groupby(['key', 'mode']).size().reset_index(name='counts')
            df_counts = df_counts.apply(self.map_keys_and_modes, axis=1)
        
        elif x_name == 'time_signature':
            df_counts = df.groupby('time_signature').size().reset_index(name='counts')

        return df_counts

    def map_keys_and_modes(self, row):
        """
        Function to map integer values of keys and modes to typical names.

        Arguments:
            - row: row of counts dataframe (Pandas Series object).

        Returns updated row.
        """

        row['mode'] = self.MODE_MAP[row['mode']]

        if 'key' in row.index:
            row['key'] = self.PITCH_CLASS_MAP[row['key']]

        return row