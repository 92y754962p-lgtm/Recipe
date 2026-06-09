import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import time

# Configure Gemini API
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
    # Simple logic to handle batch vs raw units
    if unit in ["batch", "mixture"]: return [f"{amount} {unit.capitalize()}"]
    
    # Base normalization
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
        
        # Bypass blog: Extract JSON-LD or just p/li tags
        recipe_schema = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Recipe": recipe_schema = data
            except: continue
        
        text_content = json.dumps(recipe_schema) if recipe_schema else " ".join([p.get_text() for p in soup.find_all(["p", "li"])])
        
        prompt = f"""
        Extract recipe steps from the provided source.
        
        STRICT RULES:
        1. ATOMIC STEPS: Break instructions into the smallest logical actions. If a recipe says "mix X and Y, then add to Z", create separate steps for each.
        2. MIX RULE: If a step uses a previously made mixture, list it as a "Batch". Do not relist raw ingredients.
        3. FORMAT: Output ONLY raw JSON. No markdown.
        
        Schema: {{"title": "...", "steps": [{{"step_number": 1, "action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [{{"name": "...", "amount": 0.0, "unit": "..."}}]}}]}}
        Source: {text_content[:8000]}
        """
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Error: {e}")
        return None

if st.button("Process Recipe"):
    with st.spinner("Parsing atomic steps..."):
        recipe = fetch_and_parse_recipe(url_input)
        if recipe:
            st.session_state.recipe_data = recipe
            st.session_state.current_step = 0
            st.rerun()

if st.session_state.recipe_data:
    recipe = st.session_state.recipe_data
    step = recipe['steps'][st.session_state.current_step]
    
    # Progress UI
    progress_val = (st.session_state.current_step + 1) / len(recipe['steps'])
    st.progress(progress_val)
    st.caption(f"Step {st.session_state.current_step + 1} of {len(recipe['steps'])}")
    
    st.markdown(f"### 🥣 {step['action_header']}")
    st.info(step['description'])
    
    for i, ing in enumerate(step['ingredients']):
        c1, c2 = st.columns([1, 2])
        c1.checkbox(ing['name'], key=f"c_{st.session_state.current_step}_{i}")
        c2.selectbox(ing['name'], options=convert_units(ing['amount'], ing['unit'], ing['name']), label_visibility="collapsed")
    
    # Navigation
    cols = st.columns(2)
    if cols[0].button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if cols[1].button("Next") and st.session_state.current_step < len(recipe['steps'])-1:
        st.session_state.current_step += 1; st.rerun()
