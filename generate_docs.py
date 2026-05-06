readme_md = """# 🎬 Movie Hub — Smart Recommender & Trending Dashboard

A high-performance **Movie Recommendation System** built with **Python** and **Streamlit**[cite: 1, 8].

## 🚀 Features
- **Smart Recommendations**: Powered by Cosine Similarity[cite: 8].
- **Real-Time Trending**: Integrated with TMDB API[cite: 1].
- **Immersive Visuals**: High-resolution posters and trailers[cite: 8].

## 🛠️ Technical Stack
- **Frontend**: Streamlit[cite: 8]
- **Data Analysis**: Pandas[cite: 3, 8]
- **API**: TMDB[cite: 1, 8]
"""

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme_md)
print("README.md created successfully!")