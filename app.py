import streamlit as st
from recipe_scrapers import scrape_me
import google.generativeai as genai
import json

if "recipe" not in st.session_state: st.session_state.recipe = None
if "step" not in st.session_state: st.session_state.step = 0

st.title("Interactive Kitchen")

url = st.text_input("URL:")
if st.button("Fetch"):
    scraper = scrape_me(url)
    model = genai.GenerativeModel("gemini-3.5-flash")
    
    # Map ingredients to steps and generate conversions
    prompt = f"""
    Map these ingredients to these instructions. 
    Ingredients: {json.dumps(scraper.ingredients())}
    Instructions: {json.dumps(scraper.instructions_list())}
    
    For each step, identify ONLY the ingredients used in that step. 
    Provide 3 conversion options for each ingredient (e.g., ['700g', '25oz', '1.5lbs']).
    Return JSON: {{"steps": [{{"text": "...", "ingredients": [{{"name": "...", "conversions": ["700g", "25oz"]}}]}}]}}
    """
    res = model.generate_content(prompt)
    data = json.loads(res.text.replace("```json", "").replace("```", ""))
    
    st.session_state.recipe = {"title": scraper.title(), "all_ing": scraper.ingredients(), **data}
    st.session_state.step = 0
    st.rerun()

if st.session_state.recipe:
    r = st.session_state.recipe
    with st.sidebar:
        st.header("Master Ingredients")
        for ing in r["all_ing"]: st.write(f"• {ing}")
    
    step_data = r["steps"][st.session_state.step]
    st.info(step_data["text"])
    
    for ing in step_data["ingredients"]:
        c1, c2 = st.columns([0.6, 0.4])
        c1.checkbox(ing["name"])
        c2.selectbox("Amount", ing["conversions"], key=f"sel_{ing['name']}", label_visibility="collapsed")
        
    c1, c2 = st.columns(2)
    if c1.button("Back") and st.session_state.step > 0: st.session_state.step -= 1; st.rerun()
    if c2.button("Next") and st.session_state.step < len(r["steps"])-1: st.session_state.step += 1; st.rerun()
