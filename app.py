import streamlit as st
from recipe_scrapers import scrape_me

# --- Initialize State ---
if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0

st.title("Interactive Kitchen")

# --- Fetching ---
url = st.text_input("Paste Recipe URL:")
if st.button("Fetch and Build"):
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

# --- Display Section ---
if st.session_state.recipe:
    r = st.session_state.recipe
    
    # 1. Sidebar (Master Ingredient List)
    with st.sidebar:
        st.header("Ingredients")
        for ing in r["ingredients"]:
            st.write(f"• {ing}")
        if st.button("Clear / New Recipe"):
            st.session_state.recipe = None
            st.rerun()

    # 2. Main Step Display (Untouched text)
    st.subheader(r["title"])
    st.caption(f"Step {st.session_state.step + 1} of {len(r['instructions'])}")
    
    # Raw Step Text (No LLM)
    step_text = r["instructions"][st.session_state.step]
    st.info(step_text)
    
    # 3. Interactive Row for each Ingredient
    # Note: We display all ingredients in the sidebar; 
    # for the interactive row, we show them here as requested.
    st.write("---")
    st.subheader("Items in this step:")
    for ing in r["ingredients"]:
        c1, c2 = st.columns([0.7, 0.3])
        c1.checkbox(ing)
        c2.selectbox("Unit", ["Original", "Metric", "Imperial"], key=f"sel_{ing}", label_visibility="collapsed")
    
    # 4. Navigation
    c1, c2, c3 = st.columns([1, 4, 1])
    if c1.button("Back") and st.session_state.step > 0:
        st.session_state.step -= 1; st.rerun()
    if c3.button("Next") and st.session_state.step < len(r["instructions"])-1:
        st.session_state.step += 1; st.rerun()
