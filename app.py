import streamlit as st
import pickle
import pandas as pd
import requests
import os
import gdown
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------------------------------------------------
# 1. Configuration & Session State
# ------------------------------------------------------
# Priority: Streamlit Secrets (Cloud), then the hardcoded key
if "TMDB_API" in st.secrets:
    TMDB_API = st.secrets["TMDB_API"]
else:
    TMDB_API = "007d640d828e1f901db9a75caecd8656"

st.set_page_config(page_title="Movie Hub Pro", layout="wide")

# Download logic to ensure the app works on deployment
file_id = "1C95mqxDDUNMVb0LAsgI_ReInIyd5qSBv"
output = "similarity.pkl"

if not os.path.exists(output):
    try:
        # Using 'id' directly is the most stable way to bypass Google warnings
        gdown.download(id=file_id, output=output, quiet=False)
    except Exception as e:
        st.error(f"Failed to download similarity matrix: {e}")
        st.stop()

# Initialize Session States for Persistence
if 'wishlist' not in st.session_state:
    st.session_state.wishlist = []
if 'last_recommendations' not in st.session_state:
    st.session_state.last_recommendations = []

@st.cache_resource
def get_api_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

api_session = get_api_session()

# ------------------------------------------------------
# 2. Custom CSS (Re-Applied your exact styles)
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
    transition: 0.4s ease-in-out;
}
.movie-container:hover {
    border-color: #58a6ff;
    box-shadow: 0 4px 20px rgba(88, 166, 255, 0.15);
}

.trailer-section {
    position: relative;
    width: 100%;
    height: 200px;
    border-radius: 10px;
    overflow: hidden;
    background: #000;
}
.trailer-overlay {
    position: absolute;
    top: 0; left: 0; width: 100%; height: 100%;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.6);
    color: white; font-weight: bold; font-size: 18px;
    z-index: 2; transition: 0.3s;
}
.trailer-section:hover .trailer-overlay { opacity: 0; visibility: hidden; }

.genre-badge {
    background-color: #238636;
    color: white;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    margin-right: 5px;
    display: inline-block;
}

.cast-name { color: white; font-size: 13px; font-weight: 600; text-align: center; margin-top: 5px; }

.stButton>button {
    width: 100%;
    background: linear-gradient(90deg, #ff4b1f, #ff9068);
    color: white; border-radius: 10px; font-weight: bold; border: none;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------
# 3. Helper Functions
# ------------------------------------------------------
def fetch_json(url):
    try:
        response = api_session.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass 
    return {}

def fetch_movie_details(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API}&language=en-US"
    data = fetch_json(url)
    return {
        "id": movie_id,
        "title": data.get("title", "Unknown"),
        "poster": f"https://image.tmdb.org/t/p/w500{data.get('poster_path')}" if data.get('poster_path') else "https://via.placeholder.com/500x750",
        "genres": [g["name"] for g in data.get("genres", [])],
        "overview": data.get("overview", "No overview available."),
        "rating": round(data.get("vote_average", 0), 1),
        "date": data.get('release_date', 'N/A')[:4],
        "runtime": data.get('runtime', 0)
    }

def fetch_cast(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API}"
    data = fetch_json(url)
    return [(c.get("name"), f"https://image.tmdb.org/t/p/w185{c.get('profile_path')}" if c.get('profile_path') else "https://via.placeholder.com/185") for c in data.get("cast", [])[:5]]

def fetch_trailer_id(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API}"
    data = fetch_json(url)
    for v in data.get("results", []):
        if v.get("type") == "Trailer" and v.get("site") == "YouTube":
            return v.get("key")
    return None

@st.cache_data
def load_data():
    try:
        m_dict = pickle.load(open("movie_dict.pkl", "rb"))
        sim = pickle.load(open("similarity.pkl", "rb"))
        return pd.DataFrame(m_dict), sim
    except:
        return pd.DataFrame(), None

movies_df, similarity = load_data()

# ------------------------------------------------------
# 4. App Navigation
# ------------------------------------------------------
st.sidebar.title("🎬 Navigation")
page = st.sidebar.radio("Go to", ["Recommend Movies", "My Wishlist", "Trending Today"])
st.sidebar.divider()
st.sidebar.write(f"📁 Saved Movies: **{len(st.session_state.wishlist)}**")

# ------------------------------------------------------
# PAGE: RECOMMENDATIONS (UI Fully Restored)
# ------------------------------------------------------
if page == "Recommend Movies":
    st.title("🎬 Movie Hub — Smart Recommender")
    
    selected_movie_name = st.selectbox("Choose a movie", movies_df["title"].values)

    if st.button("✨ Get Recommendations"):
        idx = movies_df[movies_df["title"] == selected_movie_name].index[0]
        distances = sorted(list(enumerate(similarity[idx])), reverse=True, key=lambda x: x[1])[1:6]
        
        st.session_state.last_recommendations = []
        for i, score in distances:
            m_id = movies_df.iloc[i].movie_id
            m_info = fetch_movie_details(m_id)
            m_info['cast'] = fetch_cast(m_id)
            m_info['trailer_id'] = fetch_trailer_id(m_id)
            st.session_state.last_recommendations.append(m_info)

    for m in st.session_state.last_recommendations:
        with st.container():
            st.markdown(f"<div class='movie-container'>", unsafe_allow_html=True)
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(m['poster'])
                if m['title'] in st.session_state.wishlist:
                    st.button("✅ In Wishlist", key=f"in_rec_{m['id']}", disabled=True)
                else:
                    if st.button(f"➕ Wishlist", key=f"add_rec_{m['id']}"):
                        st.session_state.wishlist.append(m['title'])
                        st.rerun()
            with col2:
                st.markdown(f"## {m['title']} ({m['date']})")
                st.markdown(f"**⭐ Rating:** {m['rating']} | ⏱ {m['runtime']} min")
                genre_html = "".join([f"<span class='genre-badge'>{g}</span>" for g in m['genres']])
                st.markdown(genre_html, unsafe_allow_html=True)
                st.write(m['overview'])
                if m['trailer_id']:
                    st.markdown("#### 📺 Hover to Play Trailer")
                    t_url = f"https://www.youtube.com/embed/{m['trailer_id']}?autoplay=1&mute=1&loop=1"
                    st.markdown(f'<div class="trailer-section"><div class="trailer-overlay">HOVER TO START</div><iframe src="{t_url}" width="100%" height="200" frameborder="0" allow="autoplay; encrypted-media"></iframe></div>', unsafe_allow_html=True)
            
            st.markdown("#### Top Cast")
            cast_cols = st.columns(5)
            for i, (actor, pic) in enumerate(m['cast']):
                with cast_cols[i]:
                    st.image(pic)
                    st.markdown(f"<div class='cast-name'>{actor}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------------------------------
# PAGE: WISHLIST
# ------------------------------------------------------
elif page == "My Wishlist":
    st.title("📁 Your Saved Movies")
    if not st.session_state.wishlist:
        st.info("Your wishlist is empty. Add movies from the recommendations page!")
    else:
        for movie_name in st.session_state.wishlist:
            try:
                m_id = movies_df[movies_df['title'] == movie_name].iloc[0].movie_id
                m = fetch_movie_details(m_id)
                
                with st.container():
                    st.markdown(f"<div class='movie-container'>", unsafe_allow_html=True)
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.image(m['poster'])
                        if st.button(f"❌ Remove", key=f"rem_wish_{m_id}"):
                            st.session_state.wishlist.remove(movie_name)
                            st.rerun()
                    with c2:
                        st.markdown(f"## {m['title']} ({m['date']})")
                        st.markdown(f"**⭐ Rating:** {m['rating']} | ⏱ {m['runtime']} min")
                        genre_html = "".join([f"<span class='genre-badge'>{g}</span>" for g in m['genres']])
                        st.markdown(genre_html, unsafe_allow_html=True)
                        st.write(m['overview'])
                    st.markdown("</div>", unsafe_allow_html=True)
            except Exception:
                st.warning(f"Could not load details for {movie_name}")

# ------------------------------------------------------
# PAGE: TRENDING
# ------------------------------------------------------
elif page == "Trending Today":
    st.title("🔥 Trending Movies Today")
    url = f"https://api.themoviedb.org/3/trending/movie/day?api_key={TMDB_API}"
    data = fetch_json(url).get("results", [])[:10]
    for m in data:
        m_id = m.get("id")
        info = fetch_movie_details(m_id)
        cast = fetch_cast(m_id)
        t_id = fetch_trailer_id(m_id)
        st.markdown(f"## 🎞 {info['title']}")
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(info['poster'])
        with c2:
            st.markdown(f"**⭐ Rating:** {info['rating']}")
            st.markdown(f"**🎭 Genres:** {', '.join(info['genres'])}")
            st.markdown(f"**📝 Overview:** {info['overview']}")
            if t_id:
                st.video(f"https://www.youtube.com/watch?v={t_id}")
        st.markdown("### 👥 Top Cast")
        cast_cols = st.columns(5)
        for i, (actor, pic) in enumerate(cast):
            with cast_cols[i]:
                st.image(pic)
                st.markdown(f"<div class='cast-name'>{actor}</div>", unsafe_allow_html=True)
        st.divider()
