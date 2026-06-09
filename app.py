import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import time

# Configure Gemini API using Streamlit Secrets securely
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please configure GEMINI_API_KEY within your Streamlit Secrets setting.")

if "recipe_data" not in st.session_state:
    st.session_state.recipe_data = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

st.title("Interactive AI Kitchen Interface")

url_input = st.text_input("Paste Recipe URL:")

# Density database (grams per 1 cup)
INGREDIENT_DENSITIES = {
    "flour": 120.0, "sugar": 200.0, "butter": 227.0,
    "water": 236.6, "milk": 240.0, "oil": 218.0,
    "salt": 270.0, "baking powder": 192.0, "baking soda": 288.0
}

def convert_units(amount, unit, ingredient_name):
    """Dynamically provides Volume (cups/tsp) AND Weight (g/oz) for all ingredients."""
    unit = unit.lower().strip()
    name = ingredient_name.lower().strip()
    
    # 1. Convert everything to "Base Cups" first
    if unit in ["cup", "cups", "c"]: base_cups = amount
    elif unit in ["tablespoon", "tablespoons", "tbsp", "tbs"]: base_cups = amount / 16.0
    elif unit in ["teaspoon", "teaspoons", "tsp"]: base_cups = amount / 48.0
    elif unit in ["ounce", "ounces", "oz"]: base_cups = amount / 8.0 # Rough conversion for liquid
    elif unit in ["gram", "grams", "g"]: base_cups = amount / INGREDIENT_DENSITIES.get(name, 200.0)
    else: base_cups = amount
    
    # 2. Build the output list
    options = []
    # Volume
    if base_cups >= 1: options.append(f"{base_cups:.1f} Cups")
    elif base_cups * 16 >= 1: options.append(f"{base_cups * 16:.1f} Tbsp")
    else: options.append(f"{base_cups * 48:.1f} Tsp")
    
    # Weight
    grams = base_cups * INGREDIENT_DENSITIES.get(name, 236.6)
    options.append(f"{grams:.1f} Grams")
    options.append(f"{grams / 28.35:.1f} Ounces")
    
    return options

def fetch_and_parse_recipe(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Priority 1: Extract JSON-LD (Skipping blog)
        recipe_schema = None
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get("@type") == "Recipe": recipe_schema = data
            except: continue
        
        # Priority 2: Fallback to Recipe-specific HTML classes if schema empty
        text_content = json.dumps(recipe_schema) if recipe_schema else " ".join([p.get_text() for p in soup.find_all(["p", "li"])])
        
        prompt = f"""
        Extract recipe steps from this JSON-LD schema/text. 
        MIX RULE: If a step uses a previously made mixture, list it as a "Batch". Do not relist raw ingredients.
        Return raw JSON.
        Schema: {{"title": "...", "steps": [{{"step_number": 1, "action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [{{"name": "...", "amount": 0.0, "unit": "..."}}]}}]}}
        Source: {text_content[:8000]}
        """
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"Failed: {e}")
        return None

if st.button("Process Recipe"):
    if url_input:
        with st.spinner("Analyzing recipe..."):
            recipe = fetch_and_parse_recipe(url_input)
            if recipe:
                st.session_state.recipe_data = recipe
                st.session_state.current_step = 0
                st.rerun()

if st.session_state.recipe_data:
    recipe = st.session_state.recipe_data
    step = recipe['steps'][st.session_state.current_step]
    
    st.markdown(f"### 🥣 {step['action_header']}")
    st.info(step['description'])
    
    for i, ing in enumerate(step['ingredients']):
        col1, col2 = st.columns([1, 2])
        col1.checkbox(ing['name'], key=f"c_{i}")
        col2.selectbox(ing['name'], options=convert_units(ing['amount'], ing['unit'], ing['name']), label_visibility="collapsed")
    
    # Navigation
    cols = st.columns(2)
    if cols[0].button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if cols[1].button("Next") and st.session_state.current_step < len(recipe['steps'])-1:
        st.session_state.current_step += 1; st.rerun()
