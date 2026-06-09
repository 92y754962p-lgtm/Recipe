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
def get_recipe_from_url(url):
    try:
        # Standard request. If this triggers a 403, the app handles it in the UI.
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": f"Site returned {response.status_code}. Paste text instead."}
        
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:6000]
        return process_recipe_text(text)
    except Exception as e:
        return {"error": str(e)}

def process_recipe_text(text):
    try:
        prompt = f"""
        Extract recipe from the provided text into this exact JSON structure.
        Ingredient format MUST be: {{"name": "item", "amount": 0, "unit": "unit"}}.
        
        Source text: {text}
        
        Return JSON ONLY:
        {{"steps": [ {{"action_header": "Header", "description": "Description", "timer_minutes": 0, "ingredients": [ {{"name": "item", "amount": 0, "unit": "unit"}} ] }} ] }}
        """
        model = genai.GenerativeModel("gemini-3.5-flash")
        res = model.generate_content(prompt)
        clean_res = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(clean_res)
        if isinstance(data, list): data = {"steps": data}
        if "steps" not in data: data = {"steps": [data]}
        return data
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    # URL input with fallback text area
    url = st.text_input("Paste Recipe URL:")
    raw_text = st.text_area("OR Paste recipe text here (if URL is blocked):")
    
    if st.button("Go"):
        with st.spinner("Processing..."):
            if url:
                result = get_recipe_from_url(url)
            elif raw_text:
                result = process_recipe_text(raw_text)
            else:
                st.warning("Please provide a URL or paste recipe text.")
                result = None
            
            if result and "error" not in result:
                st.session_state.recipe_data = result
                st.session_state.current_step = 0
                st.rerun()
            elif result and "error" in result:
                st.error(f"Error: {result['error']}")
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
        
        if step.get('timer_minutes', 0) > 0:
            st.error(f"⏰ Timer: {step['timer_minutes']} minutes")
        
        # Robust ingredient display
        for ing in step.get('ingredients', []):
            if isinstance(ing, dict):
                st.checkbox(f"{ing.get('name', 'Item')} ({ing.get('amount', 0)} {ing.get('unit', '')})")
            else:
                st.checkbox(str(ing))
        
        c1, c2 = st.columns(2)
        if c1.button("Back") and st.session_state.current_step > 0:
            st.session_state.current_step -= 1; st.rerun()
        if c2.button("Next") and st.session_state.current_step < len(steps)-1:
            st.session_state.current_step += 1; st.rerun()
