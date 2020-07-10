import json
import os

# APIs
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import requests
import youtube_dl

from exception import ResponseException
from private_token import spotify_user_id, spotify_token

class gen_playlist:
    def __init__(self):
        self.yt_client = self.get_yt_client()
        self.song_info = {}

    def get_yt_client(self):
        # copied from yt data api
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # get credentials and create an api client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()

        # from the youtube data api
        yt_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)
        return yt_client

    def get_liked_vids(self):
        # create dictionary of song info from yt liked videos
        request = self.yt_client.videos().list(
            part="snippet, details, statistics",
            my_rating="like"
        )
        response = request.execute()

        # obtain video info (song name, artist)
        for i in response["items"]:
            vid_title =  item["snippet"]["title"]
            yt_url = "https://www.youtube.com/watch?v={}".format(item["id"])

            # song title and artist name, from youtube_dl
            vid = youtube_dl.YoutubeDL({}).extract_info(yt_url, download=False)
            song = vid["track"]
            artist = vid["artist"]

            if song is not None and artist is not None:
                self.song_info[vid_title] = {
                    "yt_url": yt_url,
                    "song": song,
                    "artist": artist,
                    "spotify_uri": self.get_spotify_uri(song, artist)
                }

    def get_spotify_uri(self, song, artist):
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song,
            artist
        )
        response = requests.get(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]
        uri = songs[0]["uri"]
        return uri

    def create_playlist(self):
        request_body = json.dumps({
            "name": "YT Liked"
            "description": "liked music on youtube"
            "public": False
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format(spotify_user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        return response_json["id"]

    def add_song(self):
        self.get_liked_vids()
        # colelct all of uri
        uris = [info["spotify_uri"] for song, info in self.song_info.items()]
        # create new playlist and add all songs
        playlist_id = self.create_playlist()
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)
        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )

        # check valid response
        if response.status_code != 200:
            raise ResponseException(response.status_code)

        response_json = response.json()
        return response_json

if __name__ == '__main__':
    hi = create_playlist()
    hi.add_song()
