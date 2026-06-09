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
        if response.status_code != 200:
            return {"error": f"Site returned status {response.status_code}."}
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # PRE-PROCESS: Extract the specific ingredient list block
        ing_section = soup.find(lambda t: "ingredient" in t.get_text().lower() and t.name in ['h2', 'h3', 'div'])
        ing_list = ing_section.find_next('ul').get_text() if ing_section else "Manual extraction needed"
        
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p'])])
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # --- PASS 1: Extraction with Context Injection ---
        status_container.update(label="Pass 1: Extracting with context...", state="running")
        extract_prompt = f"""
        Master Ingredient List (Ground Truth):
        {ing_list}
        
        Extract the recipe steps into JSON.
        CRITICAL: For every ingredient used in a step, map it to the Master List above. 
        Example: If a step says 'add chicken', find the weight in the list. Do not use count (e.g., '2').
        
        Output JSON only:
        {{
          "original_servings": 2,
          "steps": [
            {{
              "action_header": "Title",
              "description": "Exact text",
              "ingredients": [ {{"name": "name", "original_amount": "exact measurement from list"}} ]
            }}
          ]
        }}
        Source text: {text}
        """
        res1 = model.generate_content(extract_prompt)
        raw_json1 = res1.text.strip().replace("```json", "").replace("```", "")
        extracted_data = json.loads(raw_json1)
        original_servings = extracted_data.get("original_servings", 1)
        
        # --- PASS 2: Scaling ---
        status_container.update(label="Pass 2: Scaling...", state="running")
        scale_prompt = f"""
        Scale this JSON to {target_servings} servings. 
        Multiplier: {target_servings}/{original_servings}.
        For each ingredient, output 'name' and 'amount_options' (list of metric/imperial strings).
        JSON: {json.dumps(extracted_data)}
        """
        res2 = model.generate_content(scale_prompt)
        raw_json2 = res2.text.strip().replace("```json", "").replace("```", "")
        final_data = json.loads(raw_json2)
        
        status_container.update(label="Complete!", state="complete")
        return final_data
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    col1, col2 = st.columns([0.8, 0.2])
    url = col1.text_input("Paste Recipe URL:")
    servings = col2.number_input("Servings:", min_value=1, value=2, step=1)
    
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
            st.selectbox(label="amount", options=ing.get('amount_options', ["N/A"]), key=f"select_{i}", label_visibility="collapsed")
        
        col_space, col_back, col_next = st.columns([6, 1, 1])
        with col_space: st.empty() 
        with col_back:
            if st.button("Back", use_container_width=True) and st.session_state.current_step > 0:
                st.session_state.current_step -= 1; st.rerun()
        with col_next:
            if st.button("Next", use_container_width=True) and st.session_state.current_step < len(steps)-1:
                st.session_state.current_step += 1; st.rerun()
