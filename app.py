import streamlit as st
import json
from recipe_scrapers import scrape_me
import google.generativeai as genai

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

# --- Engine ---
def prepare_recipe_structure(scraper):
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = f"""
    Organize this recipe into a structured JSON format. 
    Keep instructions exactly as provided by the scraper (verbatim).
    Map ingredients to the steps they are used in.
    
    Recipe Title: {scraper.title()}
    Ingredients: {json.dumps(scraper.ingredients())}
    Instructions: {json.dumps(scraper.instructions_list())}
    
    Return JSON: 
    {{"steps": [ {{"text": "instruction text", "ingredients": ["ingredient A", "ingredient B"]}} ]}}
    """
    res = model.generate_content(prompt)
    return json.loads(res.text.replace("```json", "").replace("```", ""))

# --- UI ---
st.title("Interactive AI Kitchen")

# Stage 1: Fetch
url = st.text_input("Recipe URL:")
if st.button("Fetch and Build Recipe"):
    with st.spinner("Building structure..."):
        try:
            scraper = scrape_me(url)
            # Gather everything first
            st.session_state.recipe_data = prepare_recipe_structure(scraper)
            st.session_state.base_servings = 2 # Most sites default to 2
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# Stage 2: Scaling & Display
if st.session_state.recipe_data:
    st.divider()
    # Now introduce the math
    servings = st.number_input("Servings:", min_value=1, value=st.session_state.base_servings)
    factor = servings / st.session_state.base_servings
    
    # Sidebar
    with st.sidebar:
        st.header("Ingredients")
        # Here you could add a function to multiply ingredient strings if needed
        st.write(f"Multiplier: {factor}x")
    
    # Display Directions
    step = st.session_state.recipe_data["steps"][st.session_state.current_step]
    st.info(step["text"])
    
    for ing in step["ingredients"]:
        c1, c2 = st.columns([0.7, 0.3])
        c1.checkbox(ing)
        c2.selectbox("Unit", ["Original", "Metric"], key=f"sel_{ing}")
        
    # Nav
    if st.button("Next") and st.session_state.current_step < len(st.session_state.recipe_data["steps"])-1:
        st.session_state.current_step += 1; st.rerun()
