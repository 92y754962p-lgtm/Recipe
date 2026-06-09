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
def get_recipe(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if response.status_code != 200:
            return {"error": f"Site returned status {response.status_code}"}
        
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:4000]
        
        prompt = f"""Extract recipe into a JSON object: {{"steps": [ {{"action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [] }} ] }}. 
        Source: {text}"""
        
        # Using the current latest stable model
        model = genai.GenerativeModel("gemini-3.5-flash")
        res = model.generate_content(prompt)
        
        clean_res = res.text.strip().replace("```json", "").replace("```", "")
        raw = json.loads(clean_res)
        
        if isinstance(raw, list): raw = {"steps": raw}
        return raw
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    url = st.text_input("Paste Recipe URL:")
    if st.button("Go"):
        if not url:
            st.warning("Please paste a URL.")
        else:
            with st.spinner("Loading recipe..."):
                result = get_recipe(url)
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.session_state.recipe_data = result
                    st.session_state.current_step = 0
                    st.rerun()
else:
    if st.sidebar.button("Clear / New Recipe"):
        st.session_state.recipe_data = None
        st.rerun()

    recipe = st.session_state.recipe_data
    steps = recipe.get('steps', [])
    
    if not steps:
        st.error("No recipe steps found.")
        if st.button("Back"): st.session_state.recipe_data = None; st.rerun()
    else:
        if st.session_state.current_step >= len(steps): st.session_state.current_step = 0
        
        step = steps[st.session_state.current_step]
        
        st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
        st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
        st.info(step.get('description', ''))
        
        if step.get('timer_minutes', 0) > 0:
            st.error(f"⏰ Timer: {step['timer_minutes']} minutes")
        
        for i, ing in enumerate(step.get('ingredients', [])):
            st.checkbox(f"{ing.get('name', 'Item')} ({ing.get('amount', 0)} {ing.get('unit', '')})")
        
        c1, c2 = st.columns(2)
        if c1.button("Back") and st.session_state.current_step > 0:
            st.session_state.current_step -= 1; st.rerun()
        if c2.button("Next") and st.session_state.current_step < len(steps)-1:
            st.session_state.current_step += 1; st.rerun()
