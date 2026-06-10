import streamlit as st
from recipe_scrapers import scrape_me
import google.generativeai as genai
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0
if "is_loaded" not in st.session_state: st.session_state.is_loaded = False
if "checked_ingredients" not in st.session_state: st.session_state.checked_ingredients = {}

# Define a realistic browser identity to bypass 403 errors
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- Page Logic ---
if not st.session_state.is_loaded:
    st.title("Interactive Kitchen")
    url = st.text_input("Paste Recipe URL:")
    
    if st.button("Fetch and Build", use_container_width=True):
        with st.status("Structuring recipe...", expanded=True) as status:
            try:
                # Pass the headers to the scraper
                scraper = scrape_me(url, headers=headers)
                
                model = genai.GenerativeModel("gemini-3.5-flash")
                prompt = f"""
                Map these ingredients to these steps.
                Ingredients: {json.dumps(scraper.ingredients())}
                Steps: {json.dumps(scraper.instructions_list())}
                
                For each step, provide:
                1. The original text (verbatim).
                2. The specific ingredients used in that step.
                3. A list of 3 conversion options (e.g., ['700g', '25oz', '1.5lbs']) for each ingredient.
                
                Return JSON: {{"steps": [{{"text": "...", "ingredients": [{{"name": "...", "conversions": ["..."]}}]}}]}}
                """
                res = model.generate_content(prompt)
                data = json.loads(res.text.replace("```json", "").replace("```", ""))
                
                st.session_state.recipe = {"title": scraper.title(), "all_ing": scraper.ingredients(), **data}
                st.session_state.is_loaded = True
                st.session_state.step = 0
                st.session_state.checked_ingredients = {} # Reset checkboxes
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

# --- Recipe View ---
if st.session_state.is_loaded:
    r = st.session_state.recipe
    
    with st.sidebar:
        st.header("Master List")
        for ing in r["all_ing"]: 
            st.write(f"• {ing}")
            
        if st.button("New Recipe", use_container_width=True):
            st.session_state.is_loaded = False
            st.session_state.recipe = None
            st.rerun()
    
    curr = r["steps"][st.session_state.step]
    st.subheader(f"Step {st.session_state.step + 1}")
    st.info(curr["text"])
    
    # Functional Checkboxes + Dropdowns
    for ing in curr["ingredients"]:
        c1, c2 = st.columns([0.6, 0.4])
        
        checkbox_key = f"chk_{st.session_state.step}_{ing['name']}"
        c1.checkbox(ing["name"], key=checkbox_key)
        
        c2.selectbox("Unit", ing["conversions"], key=f"sel_{ing['name']}", label_visibility="collapsed")
    
    # Navigation
    c1, c2 = st.columns(2)
    if c1.button("Back", use_container_width=True) and st.session_state.step > 0:
        st.session_state.step -= 1
        st.rerun()
    if c2.button("Next", use_container_width=True) and st.session_state.step < len(r["steps"])-1:
        st.session_state.step += 1
        st.rerun()
