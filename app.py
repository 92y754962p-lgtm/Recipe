import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state
if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

# --- Agentic Parsing Logic ---
def get_recipe(url, target_servings, status_container):
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # PASS 1: Create immutable Ground Truth
        status_container.update(label="Phase 1: Creating Ground Truth...", state="running")
        p1 = f"Extract a JSON dictionary of ALL ingredients and their EXACT amounts from this text: {text[:8000]}"
        r1 = model.generate_content(p1)
        ground_truth = json.loads(r1.text.replace("```json", "").replace("```", ""))
        
        # PASS 2: Map to layout (Strict Mode)
        status_container.update(label="Phase 2: Mapping to layout...", state="running")
        p2 = f"""Using ONLY this ingredient list: {json.dumps(ground_truth)}
        Write recipe steps for {target_servings} servings. 
        MAPPING RULE: For every ingredient in a step, replace the name with the value from the ingredient list.
        Return JSON schema: {{"steps": [{{"title": "...", "text": "...", "ingredients": [{{"name": "...", "amount_options": ["700g", "1.5 lbs"]}}]}}]}}
        Text: {text[:8000]}"""
        r2 = model.generate_content(p2)
        return json.loads(r2.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI (Visual Layout per your request) ---
st.title("Interactive AI Kitchen")

if not st.session_state.recipe_data:
    url = st.text_input("Recipe URL:")
    servings = st.number_input("Servings:", min_value=1, value=2)
    if st.button("Generate", type="primary"):
        with st.status("Initializing...", expanded=True) as status:
            data = get_recipe(url, servings, status)
            if "error" in data: st.error(data["error"])
            else: st.session_state.recipe_data = data; st.rerun()
else:
    # Sidebar
    with st.sidebar:
        st.header("Master Ingredients")
        for step in st.session_state.recipe_data["steps"]:
            for ing in step["ingredients"]:
                st.write(f"• {ing['name']}")
        if st.button("Reset"): st.session_state.recipe_data = None; st.rerun()

    # Main Area
    step = st.session_state.recipe_data["steps"][st.session_state.current_step]
    st.subheader(step["title"])
    st.info(step["text"])
    
    # Checkbox + Unit Selection
    for j, ing in enumerate(step["ingredients"]):
        c1, c2 = st.columns([0.7, 0.3])
        with c1: st.checkbox(ing["name"], key=f"c_{st.session_state.current_step}_{j}")
        with c2: st.selectbox("Units", ing["amount_options"], key=f"s_{st.session_state.current_step}_{j}", label_visibility="collapsed")
    
    # Navigation
    col1, col2, col3 = st.columns([1, 4, 1])
    if col1.button("Back") and st.session_state.current_step > 0:
        st.session_state.current_step -= 1; st.rerun()
    if col3.button("Next") and st.session_state.current_step < len(st.session_state.recipe_data["steps"])-1:
        st.session_state.current_step += 1; st.rerun()
