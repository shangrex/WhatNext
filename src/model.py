import os
import pickle
import re

import pandas as pd
import spotipy
import streamlit as st
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import openai


def playlist_model(url, model, max_gen=3, same_art=5):
    log = []
    Fresult = []
    try:
        log.append('Start logging')
        uri = url.split('/')[-1].split('?')[0]
        try:
            log.append('spotify local method')
            stream = open("Spotify/Spotify.yaml")
            spotify_details = yaml.safe_load(stream)
            auth_manager = SpotifyClientCredentials(client_id=spotify_details['Client_id'],
                                                    client_secret=spotify_details['client_secret'])
        except:
            log.append('spotify .streamlit method')
            try:
                Client_id = st.secrets["Client_ID"]
                client_secret = st.secrets["Client_secret"]
                auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
            except:
                log.append('spotify hug method')
                Client_id = os.environ['Client_ID']
                client_secret = os.environ['Client_secret']
                auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
        sp = spotipy.client.Spotify(auth_manager=auth_manager)

        # directly use spotify recommendation model
        if model == 'Spotify Model':
            def get_IDs(user, playlist_id):
                try:
                    log.append('start playlist extraction')
                    track_ids = []
                    playlist = sp.user_playlist(user, playlist_id)
                    for item in playlist['tracks']['items']:
                        track = item['track']
                        track_ids.append(track['id'])
                    return track_ids
                except Exception as e:
                    log.append('Failed to load the playlist')
                    log.append(e)

            track_ids = get_IDs('Ruby', uri)
            track_ids_uni = list(set(track_ids))
            log.append('Starting Spotify Model')
            Spotifyresult = pd.DataFrame()
            for i in range(len(track_ids_uni) - 5):
                if len(Spotifyresult) >= 50:
                    break
                try:
                    ff = sp.recommendations(seed_tracks=list(track_ids_uni[i:i + 5]), limit=5)
                except Exception as e:
                    log.append(e)
                    continue
                for z in range(5):
                    result = pd.DataFrame([z + (5 * i) + 1])
                    result['uri'] = ff['tracks'][z]['id']
                    Spotifyresult = pd.concat([Spotifyresult, result], axis=0)
                    Spotifyresult.drop_duplicates(subset=['uri'], inplace=True, keep='first')
                Fresult = Spotifyresult.uri[:50]

            log.append('Model run successfully')
            return Fresult, log

        lendf = len(pd.read_csv('Data/streamlit.csv', usecols=['track_uri']))
        dtypes = {'track_uri': 'object', 'artist_uri': 'object', 'album_uri': 'object', 'danceability': 'float16',
                  'energy': 'float16', 'key': 'float16',
                  'loudness': 'float16', 'mode': 'float16', 'speechiness': 'float16', 'acousticness': 'float16',
                  'instrumentalness': 'float16',
                  'liveness': 'float16', 'valence': 'float16', 'tempo': 'float16', 'duration_ms': 'float32',
                  'time_signature': 'float16',
                  'Track_release_date': 'int8', 'Track_pop': 'int8', 'Artist_pop': 'int8', 'Artist_genres': 'object'}
        col_name = ['track_uri', 'artist_uri', 'album_uri', 'danceability', 'energy', 'key',
                    'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo', 'duration_ms', 'time_signature',
                    'Track_release_date', 'Track_pop', 'Artist_pop', 'Artist_genres']

        try:
            def get_IDs(user, playlist_id):
                log.append('start playlist extraction')
                track_ids = []
                artist_id = []
                playlist = sp.user_playlist(user, playlist_id)
                for item in playlist['tracks']['items']:
                    track = item['track']
                    track_ids.append(track['id'])
                    artist = item['track']['artists']
                    artist_id.append(artist[0]['id'])
                return track_ids, artist_id
        except Exception as e:
            log.append('Failed to load the playlist')
            log.append(e)

        # get all tracks and artists id in the playlist
        track_ids, artist_id = get_IDs('Ruby', uri)
        log.append("Number of Track : {}".format(len(track_ids)))

        # take the set of all tracks and artists id in the playlist
        artist_id_uni = list(set(artist_id))
        track_ids_uni = list(set(track_ids))
        log.append("Number of unique Artists : {}".format(len(artist_id_uni)))
        log.append("Number of unique Tracks : {}".format(len(track_ids_uni)))

        def extract(track_ids_uni, artist_id_uni):
            err = []
            err.append('Start audio features extraction')
            audio_features = pd.DataFrame()
            for i in range(0, len(track_ids_uni), 25):
                try:
                    track_feature = sp.audio_features(track_ids_uni[i:i + 25])
                    track_df = pd.DataFrame(track_feature)
                    audio_features = pd.concat([audio_features, track_df], axis=0)
                except Exception as e:
                    err.append(e)
                    continue
            err.append('Start track features extraction')
            track_ = pd.DataFrame()
            for i in range(0, len(track_ids_uni), 25):
                try:
                    track_features = sp.tracks(track_ids_uni[i:i + 25])
                    for x in range(25):
                        track_pop = pd.DataFrame([track_ids_uni[i + x]], columns=['Track_uri'])
                        track_pop['Track_release_date'] = track_features['tracks'][x]['album']['release_date']
                        track_pop['Track_pop'] = track_features['tracks'][x]["popularity"]
                        track_pop['Artist_uri'] = track_features['tracks'][x]['artists'][0]['id']
                        track_pop['Album_uri'] = track_features['tracks'][x]['album']['id']
                        track_ = pd.concat([track_, track_pop], axis=0)
                except Exception as e:
                    err.append(e)
                    continue
            err.append('Start artist features extraction')
            artist_ = pd.DataFrame()
            for i in range(0, len(artist_id_uni), 25):
                try:
                    artist_features = sp.artists(artist_id_uni[i:i + 25])
                    for x in range(25):
                        artist_df = pd.DataFrame([artist_id_uni[i + x]], columns=['Artist_uri'])
                        artist_pop = artist_features['artists'][x]["popularity"]
                        artist_genres = artist_features['artists'][x]["genres"]
                        artist_df["Artist_pop"] = artist_pop
                        if artist_genres:
                            artist_df["genres"] = " ".join([re.sub(' ', '_', i) for i in artist_genres])
                        else:
                            artist_df["genres"] = "unknown"
                        artist_ = pd.concat([artist_, artist_df], axis=0)
                except Exception as e:
                    err.append(e)
                    continue
            try:
                test = pd.DataFrame(
                    track_, columns=['Track_uri', 'Artist_uri', 'Album_uri'])

                test.rename(columns={'Track_uri': 'track_uri',
                                     'Artist_uri': 'artist_uri', 'Album_uri': 'album_uri'}, inplace=True)

                audio_features.drop(
                    columns=['type', 'uri', 'track_href', 'analysis_url'], axis=1, inplace=True)

                test = pd.merge(test, audio_features,
                                left_on="track_uri", right_on="id", how='outer')
                test = pd.merge(test, track_, left_on="track_uri",
                                right_on="Track_uri", how='outer')
                test = pd.merge(test, artist_, left_on="artist_uri",
                                right_on="Artist_uri", how='outer')

                test.rename(columns={'genres': 'Artist_genres'}, inplace=True)

                test.drop(columns=['Track_uri', 'Artist_uri_x',
                                   'Artist_uri_y', 'Album_uri', 'id'], axis=1, inplace=True)

                test.dropna(axis=0, inplace=True)
                test['Track_pop'] = test['Track_pop'].apply(lambda x: int(x / 5))
                test['Artist_pop'] = test['Artist_pop'].apply(lambda x: int(x / 5))
                test['Track_release_date'] = test['Track_release_date'].apply(lambda x: x.split('-')[0])
                test['Track_release_date'] = test['Track_release_date'].astype('int16')
                test['Track_release_date'] = test['Track_release_date'].apply(lambda x: int(x / 50))

                test[['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
                      'instrumentalness', 'liveness', 'valence', 'tempo', 'time_signature']] = test[[
                    'danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness',
                    'instrumentalness', 'liveness', 'valence', 'tempo', 'time_signature']].astype('float16')
                test[['duration_ms']] = test[['duration_ms']].astype('float32')
                test[['Track_release_date', 'Track_pop', 'Artist_pop']] = test[[
                    'Track_release_date', 'Track_pop', 'Artist_pop']].astype('int8')
            except Exception as e:
                err.append(e)
            err.append('Finish extraction')
            return test, err

        # test contain all feature of user's provided playlist
        test, err = extract(track_ids_uni, artist_id_uni)

        for i in err:
            log.append(i)
        del err
        grow = test.copy()
        test['Artist_genres'] = test['Artist_genres'].apply(lambda x: x.split(" "))
        # build tf idf column for top mx_gen number of feature in the test
        tfidf = TfidfVectorizer(max_features=max_gen)
        tfidf_matrix = tfidf.fit_transform(test['Artist_genres'].apply(lambda x: " ".join(x)))
        genre_df = pd.DataFrame(tfidf_matrix.toarray())
        genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]
        genre_df = genre_df.astype('float16')
        test.drop(columns=['Artist_genres'], axis=1, inplace=True)
        test = pd.concat([test.reset_index(drop=True), genre_df.reset_index(drop=True)], axis=1)
        Fresult = pd.DataFrame()
        x = 1
        # streamlit.csv太大，分chunk去處理
        for i in range(int(lendf / 2), lendf + 1, int(lendf / 2)):
            try:
                df = pd.read_csv('Data/streamlit.csv', names=col_name, dtype=dtypes, skiprows=x, nrows=i)
                log.append('reading data frame chunks from {} to {}'.format(x, i))
            except Exception as e:
                log.append('Failed to load grow')
                log.append(e)
            # 從 grow 中移除那些 'track_uri' 存在於 df 的所有行,保留剩餘的行
            grow = grow[~grow['track_uri'].isin(df['track_uri'].values)]
            # 從 df 中移除那些 'track_uri' 存在於 test 的所有行,保留剩餘的行
            df = df[~df['track_uri'].isin(test['track_uri'].values)]
            df['Artist_genres'] = df['Artist_genres'].apply(lambda x: x.split(" "))
            tfidf_matrix = tfidf.transform(df['Artist_genres'].apply(lambda x: " ".join(x)))
            genre_df = pd.DataFrame(tfidf_matrix.toarray())
            genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]
            genre_df = genre_df.astype('float16')
            df.drop(columns=['Artist_genres'], axis=1, inplace=True)
            df = pd.concat([df.reset_index(drop=True),
                            genre_df.reset_index(drop=True)], axis=1)
            del genre_df
            try:
                df.drop(columns=['genre|unknown'], axis=1, inplace=True)
                test.drop(columns=['genre|unknown'], axis=1, inplace=True)
            except:
                log.append('genre|unknown not found')
            log.append('Scaling the data .....')
            if x == 1:
                # sc 是 tune完的minmaxscaler
                sc = pickle.load(open('Data/sc.sav', 'rb'))
                # 把 danceability ~ Artlist_pop之間的feature做minmaxscaling
                df.iloc[:, 3:19] = sc.transform(df.iloc[:, 3:19])
                test.iloc[:, 3:19] = sc.transform(test.iloc[:, 3:19])
                log.append("Creating playlist vector")
                # 把整張playlist 用 sum壓成一個vector
                playvec = pd.DataFrame(test.sum(axis=0)).T
            else:
                df.iloc[:, 3:19] = sc.transform(df.iloc[:, 3:19])
            x = i
            if model == 'Model 1':
                # 除了 track_uri, artist_uri, album_uri以外的cosine_similarity
                df['sim'] = cosine_similarity(df.drop(['track_uri', 'artist_uri', 'album_uri'], axis=1),
                                              playvec.drop(['track_uri', 'artist_uri', 'album_uri'], axis=1))
                # Track_release_date, Track_pop, Artlist_pop, 3種genre|feature的cosine_similarity
                df['sim2'] = cosine_similarity(df.iloc[:, 16:-1], playvec.iloc[:, 16:])
                # 3種genre|feature的cosine_similarity
                df['sim3'] = cosine_similarity(df.iloc[:, 19:-2], playvec.iloc[:, 19:])
                df = df.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable').groupby('artist_uri').head(
                    same_art).head(50)
                Fresult = pd.concat([Fresult, df], axis=0)
                Fresult = Fresult.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable')
                Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
                Fresult = Fresult.groupby('artist_uri').head(same_art).head(50)
            elif model == 'Model 2':
                df['sim'] = cosine_similarity(df.iloc[:, 3:16], playvec.iloc[:, 3:16])
                df['sim2'] = cosine_similarity(
                    df.loc[:, df.columns.str.startswith('T') | df.columns.str.startswith('A')],
                    playvec.loc[:, playvec.columns.str.startswith('T') | playvec.columns.str.startswith('A')])
                df['sim3'] = cosine_similarity(df.loc[:, df.columns.str.startswith('genre')],
                                               playvec.loc[:, playvec.columns.str.startswith('genre')])
                df['sim4'] = (df['sim'] + df['sim2'] + df['sim3']) / 3
                df = df.sort_values(['sim4'], ascending=False, kind='stable').groupby('artist_uri').head(same_art).head(
                    50)
                Fresult = pd.concat([Fresult, df], axis=0)
                Fresult = Fresult.sort_values(['sim4'], ascending=False, kind='stable')
                Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
                Fresult = Fresult.groupby('artist_uri').head(same_art).head(50)
        del test
        try:
            del df
            log.append('Getting Result')
        except:
            log.append('Getting Result')
        # model 1 sort based on sim3, sim2, sim
        if model == 'Model 1':
            Fresult = Fresult.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable')
            Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
            Fresult = Fresult.groupby('artist_uri').head(same_art).track_uri.head(50)
        # model 2 sort based on average of sim, sim2 and sim3
        elif model == 'Model 2':
            Fresult = Fresult.sort_values(['sim4'], ascending=False, kind='stable')
            Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
            Fresult = Fresult.groupby('artist_uri').head(same_art).track_uri.head(50)
        log.append('{} New Tracks Found'.format(len(grow)))
        if (len(grow) >= 1):
            try:
                new = pd.read_csv('Data/new_tracks.csv', dtype=dtypes)
                new = pd.concat([new, grow], axis=0)
                new = new[new.Track_pop > 0]
                new.drop_duplicates(subset=['track_uri'], inplace=True, keep='last')
                new.to_csv('Data/new_tracks.csv', index=False)
            except:
                grow.to_csv('Data/new_tracks.csv', index=False)
        log.append('Model run successfully')
    except Exception as e:
        log.append("Model Failed")
        log.append(e)

    return Fresult, log


def generate_trading_report(message):
    load_dotenv()
    openai_api_secret = os.getenv("OPENAI_API_SECRET")
    openai.api_key = openai_api_secret
    template = """
    Based on the provided financial data, here's today's trading report for the investor:

    Today's Trading Report
    Unrealized Profit and Loss (PnL) Details:

    Stock 1220: Shows a decline with an unrealized PnL of -$22,652, which is -2.31% of its net worth.
    Stock 2472: Experienced a significant drop, losing -$56,140, which is -6.22% of its net worth.
    Stock 6206: Minor decline with an unrealized PnL of -$12,387, equating to -1.67%.
    Stock 6261: On a positive note, this stock gained $33,612, about 3.76% of its net worth.
    Stock 8182: Also faced a heavy loss of -$62,302, marking -6.6% of its net worth.
    Stock 2109: Slightly positive with a gain of $497, which is 0.29%.
    Stock 2441: Similar to 8182, facing a loss of -$63,034, which is -6.58%.
    Stock 5356: Performed well with a gain of $40,420, or 4.56%.
    Stock 8150: Decreased by -$33,438, equating to -3.74%.
    Stock 1582: Dropped by -$35,129, or -3.9%.
    Total Unrealized PnL: -$210,553.
    Realized Profit and Loss (PnL) Details:

    Stock 6239: Had a significant realized loss of -$105,128, constituting -11.02% of its value.
    Total Realized PnL: -$105,128.
    Overall Financial Performance:

    Total PnL: -$315,681.
    Return on Investment (ROI) of Algorithm: -3.42%.
    ROI of All Funds: -3.48%.
    Remaining Cash: $1,007,206.
    Net Worth: $9,066,233.

    Summary
    Today's trading reflected a challenging market environment with significant losses in several stocks. Although some gains were noted, the overall financial performance resulted in a negative ROI for both the algorithm and the overall funds. Moving forward, a reassessment of the current investment strategy and risk management practices might be necessary to mitigate further losses and enhance returns.
    """

    prompt = f"Here is the template {template}, Please generate today\'s trading report for the investor on the data: {message}"

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )
    print(completion.choices[0].message.content)
    return completion.choices[0].message.content


def top_tracks(url, region):
    log = []
    Fresult = []
    uri = url.split('/')[-1].split('?')[0]
    try:
        log.append('spotify local method')
        stream = open("Spotify/Spotify.yaml")
        spotify_details = yaml.safe_load(stream)
        auth_manager = SpotifyClientCredentials(client_id=spotify_details['Client_id'],
                                                client_secret=spotify_details['client_secret'])
    except:
        log.append('spotify .streamlit method')
        try:
            Client_id = st.secrets["Client_ID"]
            client_secret = st.secrets["Client_secret"]
            auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
        except:
            log.append('spotify hug method')
            Client_id = os.environ['Client_ID']
            client_secret = os.environ['Client_secret']
            auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
    sp = spotipy.client.Spotify(auth_manager=auth_manager)
    try:
        log.append('Starting Spotify Model')
        top = sp.artist_top_tracks(uri, country=region)
        for i in range(10):
            Fresult.append(top['tracks'][i]['id'])
        log.append('Model run successfully')
    except Exception as e:
        log.append("Model Failed")
        log.append(e)
    return Fresult, log


def song_model(url, model, max_gen=3, same_art=5):
    log = []
    Fresult = []
    try:
        log.append('Start logging')
        uri = url.split('/')[-1].split('?')[0]
        try:
            log.append('spotify local method')
            stream = open("Spotify/Spotify.yaml")
            spotify_details = yaml.safe_load(stream)
            auth_manager = SpotifyClientCredentials(client_id=spotify_details['Client_id'],
                                                    client_secret=spotify_details['client_secret'])
        except:
            log.append('spotify .streamlit method')
            try:
                Client_id = st.secrets["Client_ID"]
                client_secret = st.secrets["Client_secret"]
                auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
            except:
                log.append('spotify hug method')
                Client_id = os.environ['Client_ID']
                client_secret = os.environ['Client_secret']
                auth_manager = SpotifyClientCredentials(client_id=Client_id, client_secret=client_secret)
        sp = spotipy.client.Spotify(auth_manager=auth_manager)

        if model == 'Spotify Model':
            log.append('Starting Spotify Model')
            aa = sp.recommendations(seed_tracks=[uri], limit=25)
            for i in range(25):
                Fresult.append(aa['tracks'][i]['id'])
            log.append('Model run successfully')
            return Fresult, log
        lendf = len(pd.read_csv('Data/streamlit.csv', usecols=['track_uri']))
        dtypes = {'track_uri': 'object', 'artist_uri': 'object', 'album_uri': 'object', 'danceability': 'float16',
                  'energy': 'float16', 'key': 'float16',
                  'loudness': 'float16', 'mode': 'float16', 'speechiness': 'float16', 'acousticness': 'float16',
                  'instrumentalness': 'float16',
                  'liveness': 'float16', 'valence': 'float16', 'tempo': 'float16', 'duration_ms': 'float32',
                  'time_signature': 'float16',
                  'Track_release_date': 'int8', 'Track_pop': 'int8', 'Artist_pop': 'int8', 'Artist_genres': 'object'}
        col_name = ['track_uri', 'artist_uri', 'album_uri', 'danceability', 'energy', 'key',
                    'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                    'liveness', 'valence', 'tempo', 'duration_ms', 'time_signature',
                    'Track_release_date', 'Track_pop', 'Artist_pop', 'Artist_genres']
        log.append('Start audio features extraction')
        audio_features = pd.DataFrame(sp.audio_features([uri]))
        log.append('Start track features extraction')
        track_ = pd.DataFrame()
        track_features = sp.tracks([uri])
        track_pop = pd.DataFrame([uri], columns=['Track_uri'])
        track_pop['Track_release_date'] = track_features['tracks'][0]['album']['release_date']
        track_pop['Track_pop'] = track_features['tracks'][0]["popularity"]
        track_pop['Artist_uri'] = track_features['tracks'][0]['artists'][0]['id']
        track_pop['Album_uri'] = track_features['tracks'][0]['album']['id']
        track_ = pd.concat([track_, track_pop], axis=0)
        log.append('Start artist features extraction')
        artist_id_uni = list(track_['Artist_uri'])
        artist_ = pd.DataFrame()
        artist_features = sp.artists(artist_id_uni)
        artist_df = pd.DataFrame(artist_id_uni, columns=['Artist_uri'])
        artist_pop = artist_features['artists'][0]["popularity"]
        artist_genres = artist_features['artists'][0]["genres"]
        artist_df["Artist_pop"] = artist_pop
        if artist_genres:
            artist_df["genres"] = " ".join([re.sub(' ', '_', i) for i in artist_genres])
        else:
            artist_df["genres"] = "unknown"
        artist_ = pd.concat([artist_, artist_df], axis=0)
        try:
            test = pd.DataFrame(track_, columns=['Track_uri', 'Artist_uri', 'Album_uri'])
            test.rename(columns={'Track_uri': 'track_uri', 'Artist_uri': 'artist_uri', 'Album_uri': 'album_uri'},
                        inplace=True)
            audio_features.drop(columns=['type', 'uri', 'track_href', 'analysis_url'], axis=1, inplace=True)
            test = pd.merge(test, audio_features, left_on="track_uri", right_on="id", how='outer')
            test = pd.merge(test, track_, left_on="track_uri", right_on="Track_uri", how='outer')
            test = pd.merge(test, artist_, left_on="artist_uri", right_on="Artist_uri", how='outer')
            test.rename(columns={'genres': 'Artist_genres'}, inplace=True)
            test.drop(columns=['Track_uri', 'Artist_uri_x', 'Artist_uri_y', 'Album_uri', 'id'], axis=1, inplace=True)
            test.dropna(axis=0, inplace=True)
            test['Track_pop'] = test['Track_pop'].apply(lambda x: int(x / 5))
            test['Artist_pop'] = test['Artist_pop'].apply(lambda x: int(x / 5))
            test['Track_release_date'] = test['Track_release_date'].apply(lambda x: x.split('-')[0])
            test['Track_release_date'] = test['Track_release_date'].astype('int16')
            test['Track_release_date'] = test['Track_release_date'].apply(lambda x: int(x / 50))
            test[
                ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                 'liveness', 'valence', 'tempo', 'time_signature']] = test[
                ['danceability', 'energy', 'key', 'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                 'liveness', 'valence', 'tempo', 'time_signature']].astype('float16')
            test[['duration_ms']] = test[['duration_ms']].astype('float32')
            test[['Track_release_date', 'Track_pop', 'Artist_pop']] = test[
                ['Track_release_date', 'Track_pop', 'Artist_pop']].astype('int8')
        except Exception as e:
            log.append(e)
        log.append('Finish extraction')
        grow = test.copy()
        test['Artist_genres'] = test['Artist_genres'].apply(lambda x: x.split(" "))
        tfidf = TfidfVectorizer(max_features=max_gen)
        tfidf_matrix = tfidf.fit_transform(test['Artist_genres'].apply(lambda x: " ".join(x)))
        genre_df = pd.DataFrame(tfidf_matrix.toarray())
        genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]
        genre_df = genre_df.astype('float16')
        test.drop(columns=['Artist_genres'], axis=1, inplace=True)
        test = pd.concat([test.reset_index(drop=True), genre_df.reset_index(drop=True)], axis=1)
        Fresult = pd.DataFrame()
        x = 1
        for i in range(int(lendf / 2), lendf + 1, int(lendf / 2)):
            try:
                df = pd.read_csv('Data/streamlit.csv', names=col_name, dtype=dtypes, skiprows=x, nrows=i)
                log.append('reading data frame chunks from {} to {}'.format(x, i))
            except Exception as e:
                log.append('Failed to load grow')
                log.append(e)
            grow = grow[~grow['track_uri'].isin(df['track_uri'].values)]
            df = df[~df['track_uri'].isin(test['track_uri'].values)]
            df['Artist_genres'] = df['Artist_genres'].apply(lambda x: x.split(" "))
            tfidf_matrix = tfidf.transform(df['Artist_genres'].apply(lambda x: " ".join(x)))
            genre_df = pd.DataFrame(tfidf_matrix.toarray())
            genre_df.columns = ['genre' + "|" + i for i in tfidf.get_feature_names_out()]
            genre_df = genre_df.astype('float16')
            df.drop(columns=['Artist_genres'], axis=1, inplace=True)
            df = pd.concat([df.reset_index(drop=True),
                            genre_df.reset_index(drop=True)], axis=1)
            del genre_df
            try:
                df.drop(columns=['genre|unknown'], axis=1, inplace=True)
                test.drop(columns=['genre|unknown'], axis=1, inplace=True)
            except:
                log.append('genre|unknown not found')
            log.append('Scaling the data .....')
            if x == 1:
                sc = pickle.load(open('Data/sc.sav', 'rb'))
                df.iloc[:, 3:19] = sc.transform(df.iloc[:, 3:19])
                test.iloc[:, 3:19] = sc.transform(test.iloc[:, 3:19])
                log.append("Creating playlist vector")
                playvec = pd.DataFrame(test.sum(axis=0)).T
            else:
                df.iloc[:, 3:19] = sc.transform(df.iloc[:, 3:19])
            x = i
            if model == 'Model 1':
                df['sim'] = cosine_similarity(df.drop(['track_uri', 'artist_uri', 'album_uri'], axis=1),
                                              playvec.drop(['track_uri', 'artist_uri', 'album_uri'], axis=1))
                df['sim2'] = cosine_similarity(df.iloc[:, 16:-1], playvec.iloc[:, 16:])
                df['sim3'] = cosine_similarity(df.iloc[:, 19:-2], playvec.iloc[:, 19:])
                df = df.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable').groupby('artist_uri').head(
                    same_art).head(50)
                Fresult = pd.concat([Fresult, df], axis=0)
                Fresult = Fresult.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable')
                Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
                Fresult = Fresult.groupby('artist_uri').head(same_art).head(50)
            elif model == 'Model 2':
                df['sim'] = cosine_similarity(df.iloc[:, 3:16], playvec.iloc[:, 3:16])
                df['sim2'] = cosine_similarity(
                    df.loc[:, df.columns.str.startswith('T') | df.columns.str.startswith('A')],
                    playvec.loc[:, playvec.columns.str.startswith('T') | playvec.columns.str.startswith('A')])
                df['sim3'] = cosine_similarity(df.loc[:, df.columns.str.startswith('genre')],
                                               playvec.loc[:, playvec.columns.str.startswith('genre')])
                df['sim4'] = (df['sim'] + df['sim2'] + df['sim3']) / 3
                df = df.sort_values(['sim4'], ascending=False, kind='stable').groupby('artist_uri').head(same_art).head(
                    50)
                Fresult = pd.concat([Fresult, df], axis=0)
                Fresult = Fresult.sort_values(['sim4'], ascending=False, kind='stable')
                Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
                Fresult = Fresult.groupby('artist_uri').head(same_art).head(50)
        del test
        try:
            del df
            log.append('Getting Result')
        except:
            log.append('Getting Result')
        if model == 'Model 1':
            Fresult = Fresult.sort_values(['sim3', 'sim2', 'sim'], ascending=False, kind='stable')
            Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
            Fresult = Fresult.groupby('artist_uri').head(same_art).track_uri.head(50)
        elif model == 'Model 2':
            Fresult = Fresult.sort_values(['sim4'], ascending=False, kind='stable')
            Fresult.drop_duplicates(subset=['track_uri'], inplace=True, keep='first')
            Fresult = Fresult.groupby('artist_uri').head(same_art).track_uri.head(50)
        log.append('{} New Tracks Found'.format(len(grow)))
        if (len(grow) >= 1):
            try:
                new = pd.read_csv('Data/new_tracks.csv', dtype=dtypes)
                new = pd.concat([new, grow], axis=0)
                new = new[new.Track_pop > 0]
                new.drop_duplicates(subset=['track_uri'], inplace=True, keep='last')
                new.to_csv('Data/new_tracks.csv', index=False)
            except:
                grow.to_csv('Data/new_tracks.csv', index=False)
        log.append('Model run successfully')
    except Exception as e:
        log.append("Model Failed")
        log.append(e)
    return Fresult, log


def update_dataset():
    col_name = ['track_uri', 'artist_uri', 'album_uri', 'danceability', 'energy', 'key',
                'loudness', 'mode', 'speechiness', 'acousticness', 'instrumentalness',
                'liveness', 'valence', 'tempo', 'duration_ms', 'time_signature',
                'Track_release_date', 'Track_pop', 'Artist_pop', 'Artist_genres']
    dtypes = {'track_uri': 'object', 'artist_uri': 'object', 'album_uri': 'object', 'danceability': 'float16',
              'energy': 'float16', 'key': 'float16',
              'loudness': 'float16', 'mode': 'float16', 'speechiness': 'float16', 'acousticness': 'float16',
              'instrumentalness': 'float16',
              'liveness': 'float16', 'valence': 'float16', 'tempo': 'float16', 'duration_ms': 'float32',
              'time_signature': 'float16',
              'Track_release_date': 'int8', 'Track_pop': 'int8', 'Artist_pop': 'int8', 'Artist_genres': 'object'}
    df = pd.read_csv('Data/streamlit.csv', dtype=dtypes)
    grow = pd.read_csv('Data/new_tracks.csv', dtype=dtypes)
    cur = len(df)
    df = pd.concat([df, grow], axis=0)
    grow = pd.DataFrame(columns=col_name)
    grow.to_csv('Data/new_tracks.csv', index=False)
    df = df[df.Track_pop > 0]
    df.drop_duplicates(subset=['track_uri'], inplace=True, keep='last')
    df.dropna(axis=0, inplace=True)
    df.to_csv('Data/streamlit.csv', index=False)
    return (len(df) - cur)


if __name__ == '__main__':
    song_model(url="https://open.spotify.com/track/4JHg4nNYUJQ5HULcCmI18R?si=2379b70cee0d4923", model="Model 1")