# Spotify Data Visualization Web App
* Deployed on Heroku. Link: https://spotify-recent-tracks-viz.herokuapp.com/
* Interactive data visualization of my personal listening history on Spotify between Nov 8, 2020 and Nov 21, 2020 using Bokeh library in Python
* Can be used to discover trends in my own listening habits as well as relationships between different track audio features 

## Packages Used
* Python version: 3.7.2
* Packages: Bokeh, Pandas, Statsmodels, requests, SQLAlchemy, Spotipy
* To install dependencies: pip install -r requirements.txt

## Data collection
All raw data is directly provided by Spotify using the Spotify web API. Both the Spotipy and requests libraries in Python were used in conjunction to extract the data. Data
integrity was then verified before inserting into a Postgres database. Since Spotify only stores the last 50 recently played tracks, the spotify_etl.py script was run (almost)
every day for nearly two weeks to create the full dataset. The tables were then exported to csv files to be used in the app.

## How To Use
The interactive visualization was created using the [Bokeh](https://bokeh.org/) library. It contains a scatter plot and bar chart, and several user input controls for each. 

* X and Y Axes
  * The axes for each can be changed by changing the axis label in the respective dropdowns
  * The correlation coefficient between the x and y fields will be updated in the scatter plot title
* Date/Time Range
  * The user can choose to examine only tracks played during a certain date range or certain time of day
  * Date/Time range can be chosen independently for both charts
  * The number of individual track plays selected will update in the title of both charts 
* Track/Artist Name
  * The user can also filter the data by track or artist name
  * Type the name of the track(s) or artist(s) you want to filter by (or only a part of the name) and press enter to filter
  * To remove the filter, clear the field and press enter
* Regression Line
  * The user can choose to add a regression line to the scatter plot or not by selecting the Add Regression Line checkbox
  * To see the regression equation and the R squared value, simply hover the mouse over the line
* Hover
  * The user can see additional info for each track plotted on the scatter plot by hovering over the circle. Circle size is larger for tracks that were played multiple times
  * The user can see the exact count for each category in the bar chart by hovering over the corresponding bar
  
