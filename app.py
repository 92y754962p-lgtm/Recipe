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
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # Pass 1: Extraction
        p1 = f"Extract a JSON dictionary of all ingredients and their exact amounts from: {text[:8000]}"
        r1 = model.generate_content(p1)
        gt = json.loads(r1.text.replace("```json", "").replace("```", ""))
        
        # Pass 2: Mapping
        p2 = f"""Using ONLY this ingredient list: {json.dumps(gt)}
        Write steps for {target_servings} servings. 
        For every ingredient in a step, replace the name with the value from the list.
        Return JSON: {{"steps": [{{"title": "Step", "text": "Instruction", "items": ["700g chicken"]}}]}}
        Text: {text[:8000]}"""
        r2 = model.generate_content(p2)
        return json.loads(r2.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive Kitchen")

col1, col2 = st.columns([0.8, 0.2])
url = col1.text_input("Paste Recipe URL:")
servings = col2.number_input("Servings:", min_value=1, value=2)

if st.button("Go", type="primary"):
    with st.spinner("Processing..."):
        data = get_recipe(url, servings)
        if "error" in data: st.error(data["error"])
        else: 
            st.session_state.recipe_data = data
            st.session_state.current_step = 0
            st.rerun()

if st.session_state.recipe_data:
    steps = st.session_state.recipe_data["steps"]
    step = steps[st.session_state.current_step]
    
    st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
    st.subheader(step["title"])
    st.write(step["text"])
    
    for j, item in enumerate(step["items"]):
        # Unique keys fix the crash
        st.checkbox(item, key=f"chk_{st.session_state.current_step}_{j}")
    
    col_back, col_next = st.columns(2)
    if col_back.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1
        st.rerun()
    if col_next.button("Next") and st.session_state.current_step < len(steps)-1:
        st.session_state.current_step += 1
        st.rerun()
