import streamlit as st
import google.generativeai as genai
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if "recipe_data" not in st.session_state: st.session_state.recipe_data = None
if "current_step" not in st.session_state: st.session_state.current_step = 0

# --- Logic ---
def process_recipe_text(text):
    try:
        prompt = f"""Extract recipe into this exact JSON structure: {{"steps": [ {{"action_header": "...", "description": "...", "timer_minutes": 0, "ingredients": [] }} ] }}. 
        Source: {text}"""
        
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
    st.info("Since recipe sites are blocking automation, paste the **raw recipe text** below to get started.")
    raw_text = st.text_area("Paste recipe text here:", height=200)
    
    if st.button("Generate Steps"):
        if not raw_text:
            st.warning("Please paste the recipe text.")
        else:
            with st.spinner("Processing..."):
                result = process_recipe_text(raw_text)
                if "error" in result:
                    st.error(f"Error: {result['error']}")
                else:
                    st.session_state.recipe_data = result
                    st.session_state.current_step = 0
                    st.rerun()
else:
    if st.sidebar.button("Clear / New Recipe"):
        st.session_state.recipe_data = None
        st.rerun()

    recipe = st.session_state.recipe_data
    steps = recipe.get('steps', [])
    
    if not steps:
        st.error("No steps found.")
    else:
        if st.session_state.current_step >= len(steps): st.session_state.current_step = 0
        
        step = steps[st.session_state.current_step]
        st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
        st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
        st.info(step.get('description', ''))
        
        if step.get('timer_minutes', 0) > 0:
            st.error(f"⏰ Timer: {step['timer_minutes']} minutes")
        
        for i, ing in enumerate(step.get('ingredients', [])):
            st.checkbox(f"{ing.get('name', 'Item')} ({ing.get('amount', 0)} {ing.get('unit', '')})")
        
        c1, c2 = st.columns(2)
        if c1.button("Back") and st.session_state.current_step > 0:
            st.session_state.current_step -= 1; st.rerun()
        if c2.button("Next") and st.session_state.current_step < len(steps)-1:
            st.session_state.current_step += 1; st.rerun()
