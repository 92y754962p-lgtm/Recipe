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
        
        # PASS 1: Strict Verbatim Extraction
        status_container.update(label="Scanning ingredients...", state="running")
        p1 = f"Extract a JSON dictionary of ALL ingredients/amounts. Copy the measurement strings EXACTLY as they appear in this text: {text[:8000]}"
        r1 = model.generate_content(p1)
        gt = json.loads(r1.text.replace("```json", "").replace("```", ""))
        
        # PASS 2: Layout-Oriented Mapping
        status_container.update(label="Mapping steps...", state="running")
        p2 = f"""Using ONLY this ground truth: {json.dumps(gt)}.
        Write steps for {target_servings} servings.
        Map each ingredient from the ground truth to its respective step.
        Return JSON: {{"steps": [{{"title": "...", "text": "...", "items": ["exact measurement string"]}}]}}"""
        r2 = model.generate_content(p2)
        return json.loads(r2.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI (Visual Layout as requested) ---
st.title("Interactive AI Kitchen")

if not st.session_state.recipe_data:
    url = st.text_input("Paste Recipe URL:")
    servings = st.number_input("Servings:", min_value=1, value=2)
    if st.button("Generate Recipe"):
        with st.status("Fetching...", expanded=True) as status:
            data = get_recipe(url, servings, status)
            if "error" in data: st.error(data["error"])
            else: st.session_state.recipe_data = data; st.rerun()
else:
    # Sidebar for Recipe Info (Layout per Image 6)
    with st.sidebar:
        st.header("Recipe Ingredients")
        for step in st.session_state.recipe_data["steps"]:
            for item in step["items"]:
                st.write(f"- {item}")
        if st.button("Reset"): st.session_state.recipe_data = None; st.rerun()

    # Main Step Display
    step = st.session_state.recipe_data["steps"][st.session_state.current_step]
    st.subheader(step["title"])
    st.info(step["text"])
    
    for j, item in enumerate(step["items"]):
        st.checkbox(item, key=f"c_{st.session_state.current_step}_{j}")

    # Navigation bar
    c1, c2, c3 = st.columns([1, 4, 1])
    if c1.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if c3.button("Next") and st.session_state.current_step < len(st.session_state.recipe_data["steps"])-1:
        st.session_state.current_step += 1; st.rerun()
