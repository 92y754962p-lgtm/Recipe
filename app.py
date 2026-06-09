import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state variables
if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

INGREDIENT_DENSITIES = {"flour": 120.0, "sugar": 200.0, "butter": 227.0, "water": 236.6, "milk": 240.0, "oil": 218.0, "salt": 270.0, "baking powder": 192.0, "baking soda": 288.0}

# --- Helpers ---
def convert_units(amount, unit, name):
    unit, name = unit.lower().strip(), name.lower().strip()
    base_cups = amount if unit in ["cup", "cups"] else (amount/16.0 if unit == "tbsp" else (amount/48.0 if unit == "tsp" else amount))
    grams = base_cups * INGREDIENT_DENSITIES.get(name, 236.6)
    return [f"{amount} {unit.capitalize()}", f"{grams:.1f} Grams", f"{grams/28.35:.1f} Ounces"]

def fetch_and_parse(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:]
        
        prompt = f"""Convert to JSON with this structure: 
        {{"preheat": "350F", "steps": [ {{"action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [ {{"name": "...", "amount": 0.0, "unit": "..."}} ] }} ] }}. 
        If no timer, set timer_minutes to 0. Source: {text[:1500]}"""
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        res = model.generate_content(prompt)
        raw = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
        
        final_steps = []
        for step in raw.get('steps', []):
            sentences = [s.strip() for s in step.get('description', '').replace(';', '.').split('.') if s.strip()]
            for i, sub in enumerate(sentences):
                final_steps.append({
                    'action_header': step.get('action_header', 'Step'), 
                    'description': sub, 
                    'timer_minutes': step.get('timer_minutes', 0) if i == len(sentences)-1 else 0,
                    'ingredients': step.get('ingredients', []) if i == 0 else []
                })
        raw['steps'] = final_steps
        return raw
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- UI ---
st.title("Interactive AI Kitchen")

# Only show input if no data is loaded
if st.session_state.recipe_data is None:
    url = st.text_input("Paste Recipe URL:")
    if st.button("Start Cooking"):
        with st.spinner("Parsing recipe..."):
            st.session_state.recipe_data = fetch_and_parse(url)
            st.session_state.current_step = 0
            st.rerun()
else:
    # Sidebar for control
    if st.sidebar.button("Clear / New Recipe"):
        st.session_state.recipe_data = None
        st.session_state.current_step = 0
        st.rerun()

    # Recipe Display
    recipe = st.session_state.recipe_data
    if st.session_state.current_step == 0 and recipe.get("preheat"):
        st.warning(f"🔥 Preheat oven to: {recipe['preheat']}")
    
    step = recipe['steps'][st.session_state.current_step]
    st.caption(f"Step {st.session_state.current_step + 1} of {len(recipe['steps'])}")
    st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
    st.info(step.get('description', ''))
    
    if step.get('timer_minutes', 0) > 0:
        st.error(f"⏰ Timer: {step['timer_minutes']} minutes")
    
    for i, ing in enumerate(step.get('ingredients', [])):
        c1, c2 = st.columns([1, 2])
        c1.checkbox(ing.get('name', 'Item'), key=f"c_{st.session_state.current_step}_{i}")
        c2.selectbox(ing.get('name', 'Item'), options=convert_units(ing.get('amount', 0), ing.get('unit', ''), ing.get('name', '')), label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    if c1.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if c2.button("Next") and st.session_state.current_step < len(recipe['steps'])-1:
        st.session_state.current_step += 1; st.rerun()
