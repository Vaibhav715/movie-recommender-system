import streamlit as st
import pickle
import pandas as pd
import requests
import os
import gdown
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------------------------------------------------
# 0. Secure Config
# ------------------------------------------------------
TMDB_API = os.getenv("TMDB_API")  # set in environment

if not TMDB_API:
    st.error("TMDB_API key not found. Set environment variable.")
    st.stop()

st.set_page_config(page_title="Movie Hub Pro", layout="wide")

# ------------------------------------------------------
# 1. Download similarity.pkl safely
# ------------------------------------------------------
file_id = "1C95mqxDDUNMVb0LAsgI_ReInIyd5qSBv"
output = "similarity.pkl"

if not os.path.exists(output):
    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, output, quiet=False)

# ------------------------------------------------------
# 2. Session State
# ------------------------------------------------------
if "wishlist" not in st.session_state:
    st.session_state.wishlist = []

if "last_recommendations" not in st.session_state:
    st.session_state.last_recommendations = []

# ------------------------------------------------------
# 3. API Session (retry enabled)
# ------------------------------------------------------
@st.cache_resource
def get_api_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

api_session = get_api_session()

# ------------------------------------------------------
# 4. CSS
# ------------------------------------------------------
st.markdown("""
<style>
body { background-color: #0d1117; }
h1, h2, h3 { color: #ffffff !important; }

.movie-container {
    background-color: #161b22;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #30363d;
    margin-bottom: 25px;
}

.genre-badge {
    background-color: #238636;
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    margin-right: 5px;
}

.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #ff4b1f, #ff9068);
    color: white;
    border-radius: 10px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------
# 5. Helpers
# ------------------------------------------------------
def fetch_json(url):
    try:
        r = api_session.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return {}

def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API}"
    data = fetch_json(url)

    return {
        "id": movie_id,
        "title": data.get("title", "Unknown"),
        "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" 
                  if data.get("poster_path") else "https://via.placeholder.com/500x750",
        "genres": [g["name"] for g in data.get("genres", [])],
        "overview": data.get("overview", "No overview available."),
        "rating": round(data.get("vote_average", 0), 1),
        "date": (data.get("release_date", "N/A")[:4]),
        "runtime": data.get("runtime", 0)
    }

def fetch_cast(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API}"
    data = fetch_json(url)

    return [
        (
            c.get("name"),
            f"https://image.tmdb.org/t/p/w185{c.get('profile_path')}"
            if c.get("profile_path") else "https://via.placeholder.com/185"
        )
        for c in data.get("cast", [])[:5]
    ]

def fetch_trailer_id(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API}"
    data = fetch_json(url)

    for v in data.get("results", []):
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            return v.get("key")
    return None

# ------------------------------------------------------
# 6. Load Dataset
# ------------------------------------------------------
@st.cache_data
def load_data():
    try:
        movies = pickle.load(open("movie_dict.pkl", "rb"))
        sim = pickle.load(open("similarity.pkl", "rb"))
        return pd.DataFrame(movies), sim
    except:
        return pd.DataFrame(columns=["title", "movie_id"]), None

movies_df, similarity = load_data()

# ------------------------------------------------------
# 7. Guard Clause (IMPORTANT FIX)
# ------------------------------------------------------
if similarity is None or movies_df.empty:
    st.error("Dataset or similarity matrix missing.")
    st.stop()

# ------------------------------------------------------
# 8. Sidebar
# ------------------------------------------------------
st.sidebar.title("🎬 Navigation")
page = st.sidebar.radio("Go to", ["Recommend Movies", "My Wishlist", "Trending Today"])

st.sidebar.write(f"📁 Wishlist: {len(st.session_state.wishlist)}")

# ------------------------------------------------------
# 9. RECOMMENDER PAGE
# ------------------------------------------------------
if page == "Recommend Movies":

    st.title("🎬 Movie Hub Pro")

    selected_movie = st.selectbox("Choose a movie", movies_df["title"].values)

    if st.button("✨ Recommend"):
        idx = movies_df[movies_df["title"] == selected_movie].index[0]

        distances = sorted(
            list(enumerate(similarity[idx])),
            reverse=True,
            key=lambda x: x[1]
        )[1:6]

        st.session_state.last_recommendations = []

        for i, _ in distances:
            m_id = movies_df.iloc[i].movie_id

            m = fetch_movie_details(m_id)
            m["cast"] = fetch_cast(m_id)
            m["trailer"] = fetch_trailer_id(m_id)

            st.session_state.last_recommendations.append(m)

    for m in st.session_state.last_recommendations:
        with st.container():
            st.markdown("<div class='movie-container'>", unsafe_allow_html=True)

            col1, col2 = st.columns([1, 2])

            with col1:
                st.image(m["poster"])

                if m["title"] not in st.session_state.wishlist:
                    if st.button("➕ Wishlist", key=m["id"]):
                        st.session_state.wishlist.append(m["title"])
                        st.rerun()
                else:
                    st.button("✅ Added", disabled=True)

            with col2:
                st.markdown(f"## {m['title']} ({m['date']})")
                st.markdown(f"⭐ {m['rating']} | ⏱ {m['runtime']} min")

                st.write(m["overview"])

                st.markdown("**Genres:** " +
                            ", ".join(m["genres"]))

            st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------
# 10. WISHLIST
# ------------------------------------------------------
elif page == "My Wishlist":

    st.title("📁 Wishlist")

    if not st.session_state.wishlist:
        st.info("No movies saved yet.")
    else:
        for title in st.session_state.wishlist:
            try:
                m_id = movies_df[movies_df["title"] == title].iloc[0].movie_id
                m = fetch_movie_details(m_id)

                st.markdown("---")
                st.image(m["poster"], width=150)
                st.write(f"### {m['title']} ({m['date']})")

                if st.button(f"❌ Remove {title}"):
                    st.session_state.wishlist.remove(title)
                    st.rerun()

            except:
                continue

# ------------------------------------------------------
# 11. TRENDING
# ------------------------------------------------------
elif page == "Trending Today":

    st.title("🔥 Trending Movies")

    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API}"
    data = fetch_json(url).get("results", [])[:10]

    for m in data:
        info = fetch_movie_details(m["id"])

        st.markdown(f"## {info['title']}")
        st.image(info["poster"])

        st.write(info["overview"])
        st.write(f"⭐ {info['rating']}")
        st.divider()
