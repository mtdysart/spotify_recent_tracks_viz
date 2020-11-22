import sqlalchemy
import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import requests
import json
import datetime
import spotipy.util as util

# password omitted
DB_CONN_STRING = "postgresql+psycopg2://user:pass@localhost:5432/spotify"

# Spotify authorization 
USERNAME = "(username)"
CLIENT_ID = ""
CLIENT_SECRET = ""
REDIRECT_URI = "http://localhost:7777/callback"
SCOPE = "user-read-recently-played"

def get_audio_features(track_ids, token):
    """
    Get audio features data for all collected recently played tracks.

    Arguments:
        - tracks_ids: pandas Series object containing all track_id's from track_plays DataFrame
        - token: access token provided by spotify

    Returns audio_features DataFrame containing the following columns (all measures created by Spotify):
        - track_id: id for specific track
        - danceability, energy, loudness, acousticness, liveness, instrumentalness, speechiness, valence (each seperate column)
        - tempo: in bpm
        - duration_ms: duration of track in milliseconds
        - key: key of track encoded as an integer following standard pitch class mapping: https://en.wikipedia.org/wiki/Pitch_class#Other_ways_to_label_pitch_classes
        - mode: major/minor key: 0 -> minor, 1 -> major
        - time_signature: approximate number of beats per measure/bar (ie both time signatures 3/4 and 3/8 would be encoded as 3)

    Throws exception if bad response for any track_id.
    """

    ids = set(track_ids)

    data = []
    headers = {"Authorization": f"Bearer {token}"}

    # Loop over unique track ID's
    for id in ids:
        r = requests.get(f"https://api.spotify.com/v1/audio-features/{id}", headers=headers)

        if r.status_code in range(200, 299):
            track_data = r.json()
            data.append(track_data)

        else:
            print(f"Error {r.status_code}")
            raise Exception(f"No response for audio features for track id {id}")

    df = pd.DataFrame(data)

    # Remove columns we don't need
    df = df.drop(['type', 'uri', 'track_href', 'analysis_url'], axis=1)
    return df.rename({'id': 'track_id'}, axis=1) # rename track_id column for easier merging

def create_df(data):
    """
    Creates track plays DataFrame.
    Arguments:
        - data: json-type data received from Spotify get recently played

    Returns pandas DataFrame with following columns:
        - track_id: id for specific track
        - song_name: song title
        - artist_name: artist(s) names
        - played_at: datetime when song was played (format: YYYY-MM-DD HH:MM:SS)
    """

    track_id = []
    song_name = []
    artist_name = []
    played_at = []
    timestamps = []

    for item in data['items']:
        track_id.append(item['track']['id'])
        song_name.append(item['track']['name'])
        artist_name.append(item['track']['album']['artists'][0]['name'])
        played_at.append(item['played_at'])
        timestamps.append(item['played_at'][0:10])

    song_dict = {
        "track_id": track_id, 
        "song_name": song_name,
        "artist_name": artist_name,
        "played_at": played_at,
        "timestamp": timestamps
    }

    return pd.DataFrame(song_dict)

def data_is_valid(df):
    """
    Checks if data is valid before attempting to insert into database.
    Arguments:
        - df: DataFrame for either track plays or audio features

    Returns True if data is valid, False if the dataset is empty (no tracks played in last day).

    Throws Exception if data contains any null or duplicate values. Also throws exception if time_played data contains dates
    not in past 24 hours.
    """
    if df.empty:
        return False

    if df.isnull().values.any():
        raise Exception("Data contains missing values.")

    # If track_plays DataFrame
    if "played_at" in df.columns:
        if not pd.Series(df['played_at']).is_unique:
            raise Exception("Data contains duplicate 'played at' times.")

        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        timestamps = df['timestamp'].tolist()

        for i, ts in enumerate(timestamps):
            if datetime.datetime.strptime(ts, "%Y-%m-%d") < yesterday:
                raise Exception(f"Contains data not from yesterday.")

    # If audio_features DataFrame
    elif "key" in df.columns:
        if not pd.Series(df['track_id']).is_unique:
            raise Exception("Audio features data contains duplicate track ID's.")

    return True

def create_track_plays(engine):
    """
    Creates track_plays table in postgres database if it does not already exist.

    Arguments:
        - engine: SQLAlchemy engine connected to database.
    """

    create_tb_qry = """CREATE TABLE IF NOT EXISTS track_plays (
            track_id VARCHAR(255),
            song_name VARCHAR(255),
            artist_name VARCHAR(255),
            played_at VARCHAR(255),
            timestamp DATE,
            PRIMARY KEY (played_at)
    );
    """
    engine.execute(create_tb_qry)

def create_audio_features(engine):
    """
    Creates audio_features table in postgres database if it does not already exist.

    Arguments:
        - engine: SQLAlchemy engine connected to database.
    """

    create_tb_qry = """CREATE TABLE IF NOT EXISTS audio_features (
            danceability DECIMAL,
            energy DECIMAL,
            key INTEGER,
            mode INTEGER,
            loudness DECIMAL,
            speechiness DECIMAL,
            acousticness DECIMAL,
            instrumentalness DECIMAL,
            liveness DECIMAL,
            valence DECIMAL,
            tempo DECIMAL,
            track_id VARCHAR(255),
            duration_ms INTEGER,
            time_signature INTEGER,
            PRIMARY KEY (track_id)
    );
    """
    engine.execute(create_tb_qry)

def load(engine, recently_played_df, audio_features_df):
    """
    Loads data into two seperate tables after validation.

    Arguments:
        - engine: SQLAlchemy database connection
        - recently_played_df: DataFrame containing recent track plays data
        - audio_features_df: DataFrame containing audio features for each track
    """

    recently_played_df.to_sql("track_plays", engine, index=False, if_exists='append')

    # Need to check integrity errors
    audio_features_df.to_sql("temp_audio_features", engine, index=False, if_exists='replace')
    engine.execute("INSERT INTO audio_features (SELECT * FROM temp_audio_features) ON CONFLICT ON CONSTRAINT audio_features_pkey DO NOTHING;")
    engine.execute("DROP TABLE temp_audio_features;")
    
            

if __name__ == "__main__":
    
    # Request access token from Spotify API
    token = util.prompt_for_user_token(username=USERNAME, scope=SCOPE,
                client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                redirect_uri=REDIRECT_URI)

    print("Access token created sucessfully.")

    get_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer {token}".format(token=token)
    }

    # Select time frame
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    yesterday_unix_timestamp = int(yesterday.timestamp()) * 1000
    max_limit = 50

    # Request data last (max 50) tracks played in past day
    response = requests.get(f"https://api.spotify.com/v1/me/player/recently-played?limit={max_limit}&after={yesterday_unix_timestamp}", headers=get_headers)

    if response.status_code in range(200, 299):
        data = response.json()
        recently_played_df = create_df(data)

        # Get audio features for the tracks that were played
        audio_features_df = get_audio_features(recently_played_df['track_id'], token)

        # Check if data is valid for entry into the database
        if data_is_valid(recently_played_df) and data_is_valid(audio_features_df):
            engine = sqlalchemy.create_engine(DB_CONN_STRING)
            with engine.connect() as conn:
                create_track_plays(conn)
                create_audio_features(conn)

                # Load new data
                load(conn, recently_played_df, audio_features_df)

            print("Load completed.")

    else:
        print(f"Error {response.status_code} from GET request")
        print(response.json()['error'])
