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
        
        # Remove scripts/styles to clean text
        for s in soup(["script", "style"]): s.decompose()
        full_text = soup.get_text(separator='\n')
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        status_container.update(label="Analyzing recipe...", state="running")
        
        prompt = f"""
        Extract recipe as JSON.
        Target Servings: {target_servings}.
        Identify the 'Ingredients' list and 'Steps'.
        For every ingredient in a step, find the exact amount from the 'Ingredients' list. Scale that amount for {target_servings} servings.
        
        Output JSON only:
        {{
            "steps": [
                {{
                    "action_header": "Title",
                    "description": "Step instruction",
                    "ingredients": [ {{"name": "Name", "amount_options": ["100g", "3.5oz"]}} ]
                }}
            ]
        }}
        
        Recipe text: {full_text[:10000]}
        """
        
        res = model.generate_content(prompt)
        raw_json = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_json)
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    col1, col2 = st.columns([0.8, 0.2])
    url = col1.text_input("Paste Recipe URL:")
    servings = col2.number_input("Servings:", min_value=1, value=2, step=1)
    
    st.write("") 
    col_l, col_center, col_r = st.columns([1, 2, 1])
    if col_center.button("Go", type="primary", use_container_width=True):
        with st.status("Initializing...", expanded=True) as status:
            result = get_recipe(url, servings, status)
            if "error" in result: st.error(result['error'])
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
    
    if steps:
        if st.session_state.current_step >= len(steps): st.session_state.current_step = 0
        step = steps[st.session_state.current_step]
        
        st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
        st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
        st.info(step.get('description', ''))
        
        for i, ing in enumerate(step.get('ingredients', [])):
            st.checkbox(ing.get('name'), key=f"check_{i}")
            st.selectbox(label="amount", options=ing.get('amount_options', ["Amount not specified"]), key=f"select_{i}", label_visibility="collapsed")
        
        col_space, col_back, col_next = st.columns([6, 1, 1])
        with col_space: st.empty() 
        with col_back:
            if st.button("Back", use_container_width=True) and st.session_state.current_step > 0:
                st.session_state.current_step -= 1; st.rerun()
        with col_next:
            if st.button("Next", use_container_width=True) and st.session_state.current_step < len(steps)-1:
                st.session_state.current_step += 1; st.rerun()
