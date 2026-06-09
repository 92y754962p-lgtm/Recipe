import streamlit as st
from recipe_scrapers import scrape_me

# --- Master Code ---
if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0

st.title("Interactive Kitchen")

# Fetch Input
url = st.text_input("Paste Recipe URL:")

# Full-width Fetch button
if st.button("Fetch", use_container_width=True):
    try:
        scraper = scrape_me(url)
        st.session_state.recipe = {
            "title": scraper.title(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions_list()
        }
        st.session_state.step = 0
        st.rerun()
    except Exception as e:
        st.error(f"Scraper error: {e}")

# Data Display
if st.session_state.recipe:
    r = st.session_state.recipe
    
    with st.sidebar:
        st.header("Master Ingredient List")
        for ing in r["ingredients"]:
            st.write(f"• {ing}")
            
    st.subheader(r["title"])
    st.info(r["instructions"][st.session_state.step])
    
    st.checkbox("Step Done")
    
    # Full-width Navigation
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True) and st.session_state.step > 0:
        st.session_state.step -= 1; st.rerun()
    if c2.button("Next", use_container_width=True) and st.session_state.step < len(r["instructions"])-1:
        st.session_state.step += 1; st.rerun()
