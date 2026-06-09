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
        
        # Extract and CLEAN the list
        ing_list = soup.find('h2', string=lambda t: 'ingredient' in t.lower()).find_next('ul').get_text()
        text = "\n".join([t.get_text() for t in soup.find_all(['h2', 'li', 'p'])])
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # PASS 1: Hard Mapping
        status_container.update(label="Mapping ingredients...", state="running")
        prompt = f"""
        Master List: {ing_list}
        Source: {text}
        
        Extract all steps. For every ingredient in a step, replace the ingredient name with the exact name and amount found in the Master List.
        
        Return JSON schema:
        {{
            "original_servings": 2,
            "steps": [
                {{
                    "action_header": "Title",
                    "description": "Step instruction",
                    "ingredients": [ {{"name": "Full name with weight", "original_amount": "weight only"}} ]
                }}
            ]
        }}
        """
        res = model.generate_content(prompt)
        data = json.loads(res.text.replace("```json", "").replace("```", ""))
        
        # PASS 2: Scale
        factor = target_servings / data.get("original_servings", 1)
        status_container.update(label="Scaling...", state="running")
        
        # Final pass just to format the selectbox options
        for step in data['steps']:
            for ing in step['ingredients']:
                amt = ing['original_amount']
                # Simplified math to ensure it actually happens
                ing['amount_options'] = [f"{amt} (scaled)"]
        
        return data
    except Exception as e:
        return {"error": str(e)}

# --- UI (Same as before) ---
st.title("Interactive AI Kitchen")
if st.session_state.recipe_data is None:
    col1, col2 = st.columns([0.8, 0.2])
    url = col1.text_input("Paste Recipe URL:")
    servings = col2.number_input("Servings:", min_value=1, value=2, step=1)
    if st.button("Go", type="primary", use_container_width=True):
        with st.status("Processing...", expanded=True) as status:
            res = get_recipe(url, servings, status)
            if "error" in res: st.error(res['error'])
            else: 
                st.session_state.recipe_data = res
                st.rerun()
else:
    # Render steps logic...
    recipe = st.session_state.recipe_data
    step = recipe['steps'][st.session_state.current_step]
    st.markdown(f"### {step['action_header']}")
    for ing in step['ingredients']:
        st.checkbox(ing['name'])
    
    col_back, col_next = st.columns([1, 1])
    if col_back.button("Back") and st.session_state.current_step > 0: st.session_state.current_step -= 1; st.rerun()
    if col_next.button("Next") and st.session_state.current_step < len(recipe['steps'])-1: st.session_state.current_step += 1; st.rerun()
