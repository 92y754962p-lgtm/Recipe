import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json

# Configuration
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe_data" not in st.session_state:
    st.session_state.recipe_data = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

st.title("Interactive AI Kitchen Interface")
url_input = st.text_input("Paste Recipe URL:")

INGREDIENT_DENSITIES = {
    "flour": 120.0, "sugar": 200.0, "butter": 227.0,
    "water": 236.6, "milk": 240.0, "oil": 218.0,
    "salt": 270.0, "baking powder": 192.0, "baking soda": 288.0
}

def convert_units(amount, unit, ingredient_name):
    unit, name = unit.lower().strip(), ingredient_name.lower().strip()
    if unit in ["batch", "mixture"]: return [f"{amount} {unit.capitalize()}"]
    if unit in ["cup", "cups"]: base_cups = amount
    elif unit in ["tbsp"]: base_cups = amount / 16.0
    elif unit in ["tsp"]: base_cups = amount / 48.0
    else: base_cups = amount
    grams = base_cups * INGREDIENT_DENSITIES.get(name, 236.6)
    return [f"{amount} {unit.capitalize()}", f"{grams:.1f} Grams", f"{grams/28.35:.1f} Ounces"]

def fetch_and_parse_recipe(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        # Aggressive filtering: Only grab likely instruction/ingredient tags
        recipe_text = ""
        for tag in soup.find_all(['h1', 'h2', 'li', 'p']):
            text = tag.get_text().strip()
            if len(text) > 10: recipe_text += text + "\n"
        
        prompt = f"Convert to JSON (title, steps: [{{\"action_header\": \"...\", \"description\": \"...\", \"ingredients\": [{{\"name\": \"...\", \"amount\": 0.0, \"unit\": \"...\"}}]}}]). No commentary. Source: {recipe_text[:1500]}"
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Processing Error: {e}")
        return None

if st.button("Process Recipe"):
    with st.spinner("Analyzing recipe..."):
        recipe = fetch_and_parse_recipe(url_input)
        if recipe:
            st.session_state.recipe_data = recipe
            st.session_state.current_step = 0
            st.rerun()

if st.session_state.recipe_data:
    recipe = st.session_state.recipe_data
    step = recipe['steps'][st.session_state.current_step]
    
    st.progress((st.session_state.current_step + 1) / len(recipe['steps']))
    st.caption(f"Step {st.session_state.current_step + 1} of {len(recipe['steps'])}")
    
    st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
    st.info(step.get('description', ''))
    
    for i, ing in enumerate(step.get('ingredients', [])):
        c1, c2 = st.columns([1, 2])
        c1.checkbox(ing.get('name', 'Item'), key=f"c_{st.session_state.current_step}_{i}")
        c2.selectbox(ing.get('name', 'Item'), options=convert_units(ing.get('amount', 0), ing.get('unit', ''), ing.get('name', '')), label_visibility="collapsed")
    
    cols = st.columns(2)
    if cols[0].button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if cols[1].button("Next") and st.session_state.current_step < len(recipe['steps'])-1:
        st.session_state.current_step += 1; st.rerun()
