import streamlit as st
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- Config ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def extract_schema_recipe(url):
    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Locate the JSON-LD script block containing 'recipeIngredient'
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        data = json.loads(script.string)
        # Handle cases where it's a list of schemas or a single dict
        if isinstance(data, list):
            for item in data:
                if item.get('@type') == 'Recipe': return item
        elif data.get('@type') == 'Recipe':
            return data
    return None

# --- UI ---
st.title("Interactive Kitchen")

url = st.text_input("URL:")
if st.button("Fetch"):
    recipe = extract_schema_recipe(url)
    if recipe:
        st.session_state.recipe = {
            "title": recipe.get("name"),
            "ingredients": recipe.get("recipeIngredient"),
            "instructions": [step['text'] if isinstance(step, dict) else step 
                           for step in recipe.get("recipeInstructions", [])]
        }
        st.session_state.step = 0
        st.rerun()
    else:
        st.error("Could not find schema data on this page.")

if "recipe" in st.session_state:
    r = st.session_state.recipe
    
    # Sidebar: Raw ingredients from database (100% accurate)
    with st.sidebar:
        st.header(r["title"])
        for ing in r["ingredients"]:
            st.write(f"• {ing}")
            
    # Main: Instructions (Untouched raw text)
    st.info(r["instructions"][st.session_state.step])
    
    if st.button("Next") and st.session_state.step < len(r["instructions"])-1:
        st.session_state.step += 1; st.rerun()
