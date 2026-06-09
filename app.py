import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import threading

# Configuration
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe_data" not in st.session_state:
    st.session_state.recipe_data = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

def background_parse(url):
    """Parses full recipe in background, updates session_state when done."""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])
        
        # Parse only Step 1 first for immediate display
        prompt = f"Extract ONLY the first step of this recipe as JSON (action_header, description, ingredients: [{name, amount, unit}]). Source: {text[:1500]}"
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # Get Step 1
        res1 = model.generate_content(prompt)
        step1 = json.loads(res1.text.strip().replace("```json", "").replace("```", ""))
        st.session_state.recipe_data = {"title": "Recipe", "steps": [step1]}
        
        # Get Remaining Steps (Background)
        prompt_full = f"Extract all steps AFTER the first step as JSON. Source: {text[:1500]}"
        res2 = model.generate_content(prompt_full)
        rest = json.loads(res2.text.strip().replace("```json", "").replace("```", ""))
        st.session_state.recipe_data['steps'].extend(rest.get('steps', []))
        
    except Exception as e:
        st.error(f"Background Error: {e}")

st.title("Interactive AI Kitchen Interface")
url = st.text_input("Paste Recipe URL:")

if st.button("Start Cooking"):
    st.session_state.recipe_data = None
    threading.Thread(target=background_parse, args=(url,)).start()

if st.session_state.recipe_data:
    # Display UI immediately if step 1 is ready
    step = st.session_state.recipe_data['steps'][st.session_state.current_step]
    st.write(f"Step {st.session_state.current_step + 1}")
    st.markdown(f"### {step.get('action_header', 'Step')}")
    st.info(step.get('description', ''))
    
    if st.button("Next"):
        st.session_state.current_step += 1
        st.rerun()
