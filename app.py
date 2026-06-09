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
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        status_container.update(label="Analyzing...", state="running")
        # Pass 1
        p1 = f"Return JSON dictionary of ingredients and amounts from: {text[:8000]}"
        r1 = model.generate_content(p1)
        gt = json.loads(r1.text.replace("```json", "").replace("```", ""))
        
        # Pass 2
        p2 = f"""Use this list: {json.dumps(gt)}. 
        Write steps for {target_servings} servings. 
        Replace names with amounts from list.
        Return JSON: {{"steps": [{{"title": "...", "text": "...", "items": ["700g chicken"]}}]}}
        Text: {text[:8000]}"""
        r2 = model.generate_content(p2)
        return json.loads(r2.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

# Section 1: Inputs
col1, col2 = st.columns([0.8, 0.2])
url = col1.text_input("Paste Recipe URL:")
servings = col2.number_input("Servings:", min_value=1, value=2)

if st.button("Go", type="primary"):
    with st.status("Initializing...", expanded=True) as status:
        data = get_recipe(url, servings, status)
        if "error" in data: 
            st.error(data["error"])
        else:
            st.session_state.recipe_data = data
            st.session_state.current_step = 0
            st.rerun()

# Section 2: Display (Guard Clause)
if st.session_state.recipe_data:
    st.divider()
    if st.sidebar.button("Clear / New Recipe"):
        st.session_state.recipe_data = None
        st.rerun()
        
    steps = st.session_state.recipe_data.get("steps", [])
    if 0 <= st.session_state.current_step < len(steps):
        step = steps[st.session_state.current_step]
        st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
        st.subheader(step.get("title", "Step"))
        st.info(step.get("text", ""))
        
        for j, item in enumerate(step.get("items", [])):
            st.checkbox(item, key=f"chk_{st.session_state.current_step}_{j}")
        
        # Navigation
        c1, c2, c3 = st.columns([6, 1, 1])
        if c2.button("Back") and st.session_state.current_step > 0:
            st.session_state.current_step -= 1; st.rerun()
        if c3.button("Next") and st.session_state.current_step < len(steps)-1:
            st.session_state.current_step += 1; st.rerun()
