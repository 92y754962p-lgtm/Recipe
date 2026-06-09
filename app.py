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
        
        # ANCHOR 1 & 2: Extract blocks manually
        ing_header = soup.find(lambda t: t.name in ['h2', 'h3'] and 'ingredient' in t.get_text().lower())
        ing_list = ing_header.find_next(['ul', 'ol']).get_text(separator="|") if ing_header else "No list found"
        
        step_header = soup.find(lambda t: t.name in ['h2', 'h3'] and 'step' in t.get_text().lower())
        steps_list = step_header.find_next(['ol', 'ul']).get_text(separator="|") if step_header else "No steps found"

        model = genai.GenerativeModel("gemini-3.5-flash")
        status_container.update(label="Mapping and scaling data...", state="running")
        
        prompt = f"""
        Map these ingredients to these steps. 
        Ingredients: {ing_list}
        Steps: {steps_list}
        
        CRITICAL: For every ingredient in a step, use the PRECISE measurement from the Ingredients list. Do not infer. If the list says '700g', use '700g'. Do not use count (e.g., '2').
        Scale all amounts to {target_servings} servings.
        
        Output JSON only:
        {{
          "steps": [
            {{
              "action_header": "Title",
              "description": "Instruction",
              "ingredients": [ {{"name": "...", "amount_options": ["700g (scaled)", "1.5 lbs (scaled)"]}} ]
            }}
          ]
        }}
        """
        res = model.generate_content(prompt)
        return json.loads(res.text.replace("```json", "").replace("```", ""))
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    col1, col2 = st.columns([0.8, 0.2])
    url = col1.text_input("Paste Recipe URL:")
    servings = col2.number_input("Servings:", min_value=1, value=2, step=1)
    
    st.write("") 
    _, col_center, _ = st.columns([1, 2, 1])
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
            st.checkbox(ing.get('name'), key=f"c_{i}")
            st.selectbox(label="amount", options=ing.get('amount_options', ["N/A"]), key=f"s_{i}", label_visibility="collapsed")
        
        col_space, col_back, col_next = st.columns([6, 1, 1])
        with col_space: st.empty()
        with col_back:
            if st.button("Back", use_container_width=True) and st.session_state.current_step > 0:
                st.session_state.current_step -= 1; st.rerun()
        with col_next:
            if st.button("Next", use_container_width=True) and st.session_state.current_step < len(steps)-1:
                st.session_state.current_step += 1; st.rerun()
