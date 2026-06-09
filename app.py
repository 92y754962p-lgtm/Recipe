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
        
        # We pass the full text and let the AI find the ingredients section itself
        prompt = f"""
        You are a recipe parser. 
        1. Identify the 'Ingredients' list and the 'Steps' in this text.
        2. Create a JSON where every step uses the exact ingredient measurements from the list.
        3. Scale all amounts for {target_servings} servings.
        
        Output format (JSON only):
        {{
            "steps": [
                {{
                    "action_header": "Step Title",
                    "description": "Instruction",
                    "ingredients": [ {{"name": "Ingredient Name", "amount_options": ["100g", "3.5oz"]}} ]
                }}
            ]
        }}
        
        Recipe text: {full_text[:10000]}
        """
        
        res = model.generate_content(prompt)
        raw_json = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw_json)
        
        return data
    except Exception as e:
        return {"error": str(e)}

# --- UI (Same as before) ---
st.title("Interactive AI Kitchen")
# ... (Keep your existing UI code)
