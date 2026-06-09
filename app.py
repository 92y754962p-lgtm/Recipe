import streamlit as st
import streamlit.components.v1 as components
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
def fetch_and_parse(url):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:]
        
        prompt = f"""Return ONLY a JSON object: {{"steps": [ {{"action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [] }} ] }}. 
        Source: {text[:1500]}"""
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        res = model.generate_content(prompt)
        raw = json.loads(res.text.strip().replace("```json", "").replace("```", ""))
        
        if isinstance(raw, list): raw = {"steps": raw}
        return raw
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

js_paste = """
<button id="pasteBtn" style="width:100%; padding: 10px; background-color: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer;">📋 Paste URL & Start Cooking</button>
<script>
    const btn = document.getElementById('pasteBtn');
    btn.onclick = async () => {
        const text = await navigator.clipboard.readText();
        window.parent.postMessage({type: 'streamlit:setComponentValue', value: text}, '*');
    };
</script>
"""

if st.session_state.recipe_data is None:
    val = components.html(js_paste, height=60)
    url = st.text_input("Or paste manually:", key="url_in")
    target_url = val if val and isinstance(val, str) else url
    
    if target_url: 
        with st.spinner("Parsing..."):
            st.session_state.recipe_data = fetch_and_parse(target_url)
            st.session_state.current_step = 0
            st.rerun()
else:
    if st.sidebar.button("Clear / New Recipe"):
        st.session_state.recipe_data = None
        st.rerun()

    recipe = st.session_state.recipe_data
    steps = recipe.get('steps', [])
    
    # CRITICAL FIX: Check if steps exist before accessing
    if not steps:
        st.error("No steps found. Please try a different URL.")
        if st.button("Retry"): 
            st.session_state.recipe_data = None
            st.rerun()
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
