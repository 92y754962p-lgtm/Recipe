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
    with st.status("Structuring recipe...", expanded=True) as status:
        try:
            # 1. Scrape (Deterministic)
            scraper = scrape_me(url)
            status.update(label="Analyzing steps and tools...")
            
            # 2. Structure (LLM only adds labels/mapping)
            model = genai.GenerativeModel("gemini-3.5-flash")
            prompt = f"""
            Organize these instructions into steps. For each step, add a 'vessel' (e.g., Mixing Bowl, Skillet).
            Map only the necessary ingredients to each step.
            Instructions: {json.dumps(scraper.instructions_list())}
            Ingredients: {json.dumps(scraper.ingredients())}
            Return JSON: {{"steps": [{{"vessel": "...", "text": "...", "ingredients": ["..."]}}]}}
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
    
    # Step Display
    curr = r["steps"][st.session_state.step]
    st.subheader(f"Step {st.session_state.step + 1}: {curr['vessel']}")
    st.info(curr["text"])
    
    # Ingredients in this step
    for ing in curr["ingredients"]:
        c1, c2 = st.columns([0.7, 0.3])
        c1.checkbox(ing)
        c2.selectbox("Unit", ["Original", "Metric", "Imperial"], key=f"s_{ing}", label_visibility="collapsed")
    
    # Nav
    c1, c2 = st.columns(2)
    if c1.button("Back") and st.session_state.step > 0: st.session_state.step -= 1; st.rerun()
    if c2.button("Next") and st.session_state.step < len(r["steps"])-1: st.session_state.step += 1; st.rerun()
