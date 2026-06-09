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
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # --- PASS 1 ---
        status_container.update(label="Pass 1: Extracting...", state="running")
        extract_prompt = f"Extract recipe as JSON with keys 'original_servings' and 'steps' (each step with 'action_header', 'description', 'ingredients' containing 'name' and 'original_amount'). Source: {text}"
        res1 = model.generate_content(extract_prompt)
        
        # CRASH FIX: Log and handle bad JSON
        raw_json1 = res1.text.strip().replace("```json", "").replace("```", "")
        try:
            extracted_data = json.loads(raw_json1)
        except json.JSONDecodeError:
            return {"error": f"AI returned invalid JSON: {raw_json1[:100]}..."}
            
        original_servings = extracted_data.get("original_servings", 1)
        
        # --- PASS 2 ---
        status_container.update(label="Pass 2: Scaling...", state="running")
        scale_prompt = f"Scale this JSON to {target_servings} servings. Provide 'amount_options' list for each ingredient. JSON: {json.dumps(extracted_data)}"
        res2 = model.generate_content(scale_prompt)
        
        raw_json2 = res2.text.strip().replace("```json", "").replace("```", "")
        try:
            final_data = json.loads(raw_json2)
        except json.JSONDecodeError:
            return {"error": f"AI returned invalid JSON in Pass 2: {raw_json2[:100]}..."}
        
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
            st.rerun()
else:
    # ... (Keep existing UI code from previous version here) ...
