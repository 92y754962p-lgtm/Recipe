import streamlit as st
from recipe_scrapers import scrape_me
import google.generativeai as genai
import json

# --- Config ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0

st.title("Interactive Kitchen")

url = st.text_input("Paste Recipe URL:")

if st.button("Fetch and Build"):
    with st.status("Building structure...", expanded=True) as status:
        try:
            # 1. Scrape (Deterministic)
            scraper = scrape_me(url)
            status.update(label="Calculating conversions and mapping...")
            
            # 2. Structure + Math (LLM calculates conversions)
            model = genai.GenerativeModel("gemini-3.5-flash")
            prompt = f"""
            Analyze these ingredients: {json.dumps(scraper.ingredients())}
            Analyze these steps: {json.dumps(scraper.instructions_list())}
            
            Task:
            1. Map ingredients to steps (only include ingredients needed for that step).
            2. For every ingredient, calculate 3 actual conversion values (e.g., if input is '1 cup', provide ['1 cup', '240ml', '8oz']).
            3. Assign a vessel (e.g., 'Mixing Bowl') to each step.
            
            Return ONLY JSON: {{"steps": [{{"vessel": "...", "text": "...", "ingredients": [{{"name": "...", "values": ["1 cup", "240ml", "8oz"]}}]}}]}}
            """
            res = model.generate_content(prompt)
            data = json.loads(res.text.replace("```json", "").replace("```", ""))
            
            st.session_state.recipe = {"title": scraper.title(), "all_ing": scraper.ingredients(), **data}
            st.session_state.step = 0
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- Display ---
if st.session_state.recipe:
    r = st.session_state.recipe
    
    with st.sidebar:
        st.header("Master List")
        for ing in r["all_ing"]: st.write(f"• {ing}")
    
    curr = r["steps"][st.session_state.step]
    st.subheader(f"Step {st.session_state.step + 1}: {curr['vessel']}")
    st.info(curr["text"])
    
    # Checkbox + Unit Selector with Calculated Values
    for ing in curr["ingredients"]:
        c1, c2 = st.columns([0.7, 0.3])
        c1.checkbox(ing["name"])
        # The dropdown now uses the 'values' calculated by the LLM
        c2.selectbox("Unit", ing["values"], key=f"sel_{ing['name']}", label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    if c1.button("Back") and st.session_state.step > 0: st.session_state.step -= 1; st.rerun()
    if c2.button("Next") and st.session_state.step < len(r["steps"])-1: st.session_state.step += 1; st.rerun()
