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
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:6000]
        
        # Using the current production-standard model: gemini-3.5-flash
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # --- PASS 1: Extraction ---
        status_container.update(label="Pass 1: Extracting...", state="running")
        extract_prompt = f"""
        Extract the recipe into a JSON object with 'original_servings' and 'steps' (list).
        Each step must have 'action_header', 'description', and 'ingredients' (list).
        Each ingredient must have 'name' and 'original_amount'.
        
        CRITICAL: For every ingredient found in the 'Ingredients' list, use that exact amount in all steps. Do not infer or invent measurements.
        
        Source text: {text}
        """
        res1 = model.generate_content(extract_prompt)
        raw_json1 = res1.text.strip().replace("```json", "").replace("```", "")
        
        try:
            extracted_data = json.loads(raw_json1)
        except:
            return {"error": "AI returned invalid JSON in Pass 1."}
            
        original_servings = extracted_data.get("original_servings", 1)
        
        # --- PASS 2: Scaling ---
        status_container.update(label="Pass 2: Scaling...", state="running")
        scale_prompt = f"""
        Scale this recipe to {target_servings} servings (multiplier: {target_servings}/{original_servings}).
        Keep 'action_header', 'description' identical.
        For each ingredient, output 'name' and 'amount_options' (list of strings with metric/imperial).
        
        JSON: {json.dumps(extracted_data)}
        """
        res2 = model.generate_content(scale_prompt)
        raw_json2 = res2.text.strip().replace("```json", "").replace("```", "")
        
        try:
            final_data = json.loads(raw_json2)
        except:
            return {"error": "AI returned invalid JSON in Pass 2."}
        
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
            
        if "error" in result:
            st.error(result['error'])
        else:
            st.session_state.recipe_data = result
            st.session_state.current_step = 0
            st.rerun()
else:
    # ... (UI Rendering remains exactly as before)
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
            ing_name = ing.get('name', 'Ingredient')
            options = ing.get('amount_options', ["Amount not specified"])
            
            st.checkbox(ing_name, key=f"check_{st.session_state.current_step}_{i}")
            st.selectbox(label=f"amount_{st.session_state.current_step}_{i}", options=options, key=f"select_{st.session_state.current_step}_{i}", label_visibility="collapsed")
        
        col_space, col_back, col_next = st.columns([6, 1, 1])
        with col_space: st.empty() 
        with col_back:
            if st.button("Back", use_container_width=True) and st.session_state.current_step > 0:
                st.session_state.current_step -= 1; st.rerun()
        with col_next:
            if st.button("Next", use_container_width=True) and st.session_state.current_step < len(steps)-1:
                st.session_state.current_step += 1; st.rerun()
