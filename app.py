import streamlit as st
from recipe_scrapers import scrape_me

# --- Master Code ---
# Base state initialization
if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0

st.title("Interactive Kitchen")

# Fetch Input
url = st.text_input("Paste Recipe URL:")

if st.button("Fetch"):
    try:
        # 1. Deterministic Data Extraction (No LLM)
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
    
    # Sidebar: Master Ingredient List
    with st.sidebar:
        st.header("Master Ingredient List")
        for ing in r["ingredients"]:
            st.write(f"• {ing}")
            
    # Main: Verbatim Instructions
    st.subheader(r["title"])
    st.info(r["instructions"][st.session_state.step])
    
    # Step Control
    st.checkbox("Step Done")
    
    c1, c2 = st.columns(2)
    if c1.button("Back") and st.session_state.step > 0:
        st.session_state.step -= 1; st.rerun()
    if c2.button("Next") and st.session_state.step < len(r["instructions"])-1:
        st.session_state.step += 1; st.rerun()
