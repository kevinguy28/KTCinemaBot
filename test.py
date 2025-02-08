import requests
import os
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore


cred = credentials.Certificate("C:/Users/mudKI/Downloads/ktcinemabot-2ef82-firebase-adminsdk-fbsvc-5449434d99.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


load_dotenv()
TMDB = os.getenv('TMDB')
BASE_URL = "https://api.themoviedb.org/3"

def getMovie(title: str, year: str = ""):
    movie_name = title if 0 <= len(title) <= 100 else title[:100]
    
    params = {
        'query': movie_name,  # Use 'query' for TMDb API to search by title
        'year': year,
        "api_key": TMDB,  # TMDB API Key, not OMDB
    }

    response = requests.get(f"{BASE_URL}/search/movie", params=params)
    data = response.json()

    if data.get("results"):
        movie = data["results"][0]
        print(f"Title: {movie['title']}")
        print(f"Release Date: {movie['release_date']}")
        print(f"Overview: {movie['overview']}")
        print(f"Poster URL: https://image.tmdb.org/t/p/w500{movie['poster_path']}")
    else:
        print("Movie not found.")

def addMovie(movie_name:str, year: str=""):
        
    movie_name = movie_name if 0 <= len(movie_name) <= 100 else movie_name[:100]
   
    params = {
        'query': movie_name,  # Use 'query' for TMDb API to search by title
        'year': year,
        "api_key": TMDB,  # TMDB API Key, not OMDB
    }

    response = requests.get(f"{BASE_URL}/search/movie", params=params)
    data = response.json()

    print(data)

    try:
        movie = data["results"][0]
        print(movie)
        movie_data = {'title': movie['title'], 'release_date': movie['release_date'], 'backdrop_path': movie['backdrop_path']}
        movie_ref = db.collection("movies").document(movie['title'])
        movie_ref.set(movie_data)
        watchlist_ref = db.collection("watchlist").document(movie['title']).set({'movie_ref': movie_ref.path})
    except Exception as E:
        print(f"❌ {movie_name} could not be added!")

    print(f"🎬 '{movie_name}' has been added!")

addMovie("Spiderman homecoming")