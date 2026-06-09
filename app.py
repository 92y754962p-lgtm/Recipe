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
def get_recipe(url, target_servings):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        prompt = f"""
        Extract recipe as JSON for {target_servings} servings.
        Structure MUST be: {{ "steps": [ {{"action_header": "...", "description": "...", "ingredients": [{{"name": "...", "amount": "..."}}]}} ] }}
        Text: {text[:8000]}
        """
        
        res = model.generate_content(prompt)
        raw = res.text.replace("```json", "").replace("```", "")
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

col1, col2 = st.columns([0.8, 0.2])
url = col1.text_input("Paste Recipe URL:")
servings = col2.number_input("Servings:", min_value=1, value=2)

if st.button("Go"):
    with st.spinner("Processing..."):
        result = get_recipe(url, servings)
        if "error" in result: 
            st.error(result['error'])
        else:
            st.session_state.recipe_data = result
            st.session_state.current_step = 0
            st.rerun()

# SAFE ACCESS: Check if recipe_data exists AND has the 'steps' key
if st.session_state.recipe_data and 'steps' in st.session_state.recipe_data:
    steps = st.session_state.recipe_data['steps']
    if 0 <= st.session_state.current_step < len(steps):
        step = steps[st.session_state.current_step]
        st.subheader(step.get('action_header', 'Step'))
        st.write(step.get('description', ''))
        for ing in step.get('ingredients', []):
            st.checkbox(f"{ing.get('name', 'Item')} ({ing.get('amount', 'N/A')})")
        
        col1, col2 = st.columns(2)
        if col1.button("Back") and st.session_state.current_step > 0:
            st.session_state.current_step -= 1; st.rerun()
        if col2.button("Next") and st.session_state.current_step < len(steps)-1:
            st.session_state.current_step += 1; st.rerun()
    else:
        st.error("Error: Current step is invalid.")
