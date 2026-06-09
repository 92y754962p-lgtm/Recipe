import streamlit as st
import json
from recipe_scrapers import scrape_me
import google.generativeai as genai

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize State
if "raw_data" not in st.session_state: st.session_state.raw_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

# --- Scaling Logic ---
def scale_ingredients(ingredients, factor):
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = f"""
    Scale these ingredients by a factor of {factor}.
    For each ingredient, provide the name and a list of alternative units (e.g. ['700g', '1.5 lbs']).
    Return JSON: {{"ingredients": [{{"name": "Ingredient Name", "units": ["700g", "1.5 lbs"]}}]}}
    Ingredients: {json.dumps(ingredients)}
    """
    res = model.generate_content(prompt)
    raw = res.text.replace("```json", "").replace("```", "")
    return json.loads(raw).get("ingredients", [])

# --- UI ---
st.title("Interactive AI Kitchen")

# 1. Fetching
col1, col2 = st.columns([0.8, 0.2])
url = col1.text_input("Recipe URL:")
if col2.button("Fetch"):
    try:
        scraper = scrape_me(url)
        st.session_state.raw_data = {
            "title": scraper.title(),
            "ingredients": scraper.ingredients(),
            "instructions": scraper.instructions_list(),
            "servings": 2 # Default fallback
        }
        st.session_state.current_step = 0
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

# 2. Display
if st.session_state.raw_data:
    st.divider()
    # Scaling
    servings = st.number_input("Servings:", value=st.session_state.raw_data["servings"])
    factor = servings / st.session_state.raw_data["servings"]
    scaled = scale_ingredients(st.session_state.raw_data["ingredients"], factor)
    
    # Sidebar: Ingredients
    with st.sidebar:
        st.header("Ingredients")
        for ing in scaled:
            st.write(f"• {ing['name']}")
    
    # Main: Directions (Raw text, no LLM interference)
    instructions = st.session_state.raw_data["instructions"]
    st.info(instructions[st.session_state.current_step])
    
    # Checkbox + Unit Selection (for ingredients in current step)
    for j, ing in enumerate(scaled):
        c1, c2 = st.columns([0.7, 0.3])
        c1.checkbox(ing["name"], key=f"ch_{j}")
        c2.selectbox("Unit", ing["units"], key=f"sl_{j}", label_visibility="collapsed")
        
    # Navigation
    c1, c2, c3 = st.columns([1, 4, 1])
    if c1.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if c3.button("Next") and st.session_state.current_step < len(instructions)-1:
        st.session_state.current_step += 1; st.rerun()
