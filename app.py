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
def get_recipe(url, servings):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"Site returned status {response.status_code}."}
        
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:6000]
        
        prompt = f"""
        Extract the recipe into this exact JSON format. 
        CRITICAL: Scale all ingredient amounts to yield exactly {servings} servings. If the original text makes a different amount, calculate the new scaled amounts.
        For every ingredient, provide the scaled amount in both metric and imperial units as a list of strings in the 'amount_options' array.
        {{
          "steps": [
            {{
              "action_header": "Title",
              "description": "Short instruction",
              "timer_minutes": 0,
              "ingredients": [ 
                {{
                    "name": "ingredient name", 
                    "amount_options": ["500 g", "1.1 lbs", "17.6 oz"] 
                }} 
              ]
            }}
          ]
        }}
        Source text: {text}
        """
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        res = model.generate_content(prompt)
        
        clean_res = res.text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_res)
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive AI Kitchen")

if st.session_state.recipe_data is None:
    col1, col2 = st.columns([0.8, 0.2])
    url = col1.text_input("Paste Recipe URL:")
    servings = col2.number_input("Servings:", min_value=1, value=2, step=1)
    
    if st.button("Go"):
        with st.spinner("Loading..."):
            result = get_recipe(url, servings)
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
    
    if steps:
        if st.session_state.current_step >= len(steps): st.session_state.current_step = 0
        step = steps[st.session_state.current_step]
        
        st.caption(f"Step {st.session_state.current_step + 1} of {len(steps)}")
        st.markdown(f"### 🥣 {step.get('action_header', 'Step')}")
        st.info(step.get('description', ''))
        
        if step.get('timer_minutes', 0) > 0:
            st.error(f"⏰ Timer: {step['timer_minutes']} minutes")
        
        for i, ing in enumerate(step.get('ingredients', [])):
            ing_name = ing.get('name', 'Ingredient')
            options = ing.get('amount_options', ["Amount not specified"])
            
            # FIXED: Completed the broken f-string here
            st.checkbox(ing_name, key=f"check_{st.session_state.current_step}_{i}")
            
            st.selectbox(
                label=f"amount_{st.session_state.current_step}_{i}",
                options=options,
                key=f"select_{st.session_state.current_step}_{i}",
                label_visibility="collapsed"
            )
        
        # Spacer column pushes buttons to the right
        col_space, col_back, col_next = st.columns([0.7, 0.15, 0.15])
        
        with col_back:
            if st.button("Back") and st.session_state.current_step > 0:
                st.session_state.current_step -= 1
                st.rerun()
                
        with col_next:
            if st.button("Next") and st.session_state.current_step < len(steps)-1:
                st.session_state.current_step += 1
                st.rerun()
