import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

# --- Logic ---
def get_recipe(url, target_servings, status_container):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        status_container.update(label="Mapping and calculating units...", state="running")
        
        # Combined pass with strict schema for units
        prompt = f"""
        Extract recipe for {target_servings} servings.
        For every ingredient, provide 'name' and 'amount_options' (a list of strings with different units).
        Return JSON exactly:
        {{
          "steps": [
            {{
              "title": "...", "text": "...",
              "ingredients": [ {{"name": "Chicken", "amount_options": ["700g", "1.5 lbs"]}} ]
            }}
          ]
        }}
        Text: {text[:8000]}
        """
        res = model.generate_content(prompt)
        return json.loads(res.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if not st.session_state.recipe_data:
    url = st.text_input("Paste Recipe URL:")
    servings = st.number_input("Servings:", min_value=1, value=2)
    if st.button("Generate"):
        with st.status("Fetching...", expanded=True) as status:
            data = get_recipe(url, servings, status)
            if "error" in data: st.error(data["error"])
            else: st.session_state.recipe_data = data; st.rerun()
else:
    # Sidebar
    with st.sidebar:
        st.header("Recipe Ingredients")
        for step in st.session_state.recipe_data["steps"]:
            for ing in step["ingredients"]:
                st.write(f"• {ing['name']}")
        if st.button("Reset"): st.session_state.recipe_data = None; st.rerun()

    # Main Step Display
    step = st.session_state.recipe_data["steps"][st.session_state.current_step]
    st.subheader(step["title"])
    st.info(step["text"])
    
    # Checkbox + Unit Selector
    for j, ing in enumerate(step["ingredients"]):
        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            st.checkbox(ing["name"], key=f"chk_{st.session_state.current_step}_{j}")
        with col2:
            st.selectbox("Units", ing["amount_options"], key=f"sel_{st.session_state.current_step}_{j}", label_visibility="collapsed")

    # Navigation
    c1, c2, c3 = st.columns([1, 4, 1])
    if c1.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if c3.button("Next") and st.session_state.current_step < len(st.session_state.recipe_data["steps"])-1:
        st.session_state.current_step += 1; st.rerun()
