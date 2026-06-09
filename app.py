import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
import time

# Configure Gemini API using Streamlit Secrets securely
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Please configure GEMINI_API_KEY within your Streamlit Secrets setting.")

if "recipe_data" not in st.session_state:
    st.session_state.recipe_data = None
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

st.title("Interactive AI Kitchen Interface")

url_input = st.text_input("Paste Recipe URL:")

def fetch_and_parse_recipe(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        text_content = " ".join([p.get_text() for p in soup.find_all(["p", "li", "h1", "h2", "h3"])])
        
        prompt = f"""
        Analyze the following recipe web page text and convert it into a structured JSON object.
        
        CRITICAL DIRECTIVES:
        1. Break down steps by the specific vessel/bowl being used. 
        2. Do not use paragraph format for ingredients. Extract every ingredient mentioned in the step and list them individually.
        3. Cross-reference generic terms (e.g., "dry ingredients") with the master ingredient list. Explicitly list the exact ingredients and their measurements.
        4. For EVERY ingredient measurement, calculate and provide at least three unit variations in an array: Original, Metric (grams/ml), and Imperial (ounces/cups/lbs).
        
        JSON Schema Requirements:
        1. "title": String name of recipe.
        2. "steps": List of object steps containing:
            - "step_number": Integer
            - "action_header": String (e.g., "Whisk Dry Ingredients (Medium Bowl)")
            - "description": String (Brief 1-2 sentence instruction of what to do with the items).
            - "timer_minutes": Integer (cooking duration, 0 if none).
            - "ingredients": List of objects for each item used in this step:
                - "name": String (e.g., "Flour")
                - "options": List of strings containing converted values (e.g., ["1.5 Cups", "180 Grams", "6.3 Ounces"])
        
        Recipe Source Text:
        {text_content[:8000]}
        
        Return ONLY raw valid JSON matching the schema. No markdown wrapping blocks.
        """
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
                return json.loads(cleaned_text)
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2) 
                    continue
                else:
                    st.error(f"API Error after {max_retries} attempts: {e}")
                    return None
                    
    except Exception as e:
        st.error(f"Failed to process URL content: {e}")
        return None

if st.button("Process Recipe"):
    if url_input:
        with st.spinner("Gemini is parsing and converting recipe content..."):
            recipe = fetch_and_parse_recipe(url_input)
            if recipe:
                st.session_state.recipe_data = recipe
                st.session_state.current_step = 0
                st.rerun()
    else:
        st.warning("Please provide a valid URL string.")

if st.session_state.recipe_data:
    recipe = st.session_state.recipe_data
    steps = recipe.get("steps", [])
    idx = st.session_state.current_step
    
    st.header(recipe.get("title", "Parsed Recipe"))
    st.progress((idx + 1) / len(steps))
    st.subheader(f"Step {idx + 1} of {len(steps)}")
    
    if idx < len(steps):
        step = steps[idx]
        
        # Display the Vessel/Action Header and Description
        st.markdown(f"### 🥣 {step.get('action_header', 'Action Needed')}")
        st.info(step.get("description", ""))
        
        # Display Ingredients with Inline Unit Toggles
        ingredients = step.get("ingredients", [])
        if ingredients:
            st.write("**Ingredients:**")
            for i, ing in enumerate(ingredients):
                col1, col2 = st.columns([1, 2])
                with col1:
                    # Checkbox for the ingredient name
                    st.checkbox(f"**{ing.get('name', 'Ingredient')}**", key=f"check_{idx}_{i}")
                with col2:
                    # Dropdown acting as the inline amount display
                    options = ing.get("options", ["Amount not specified"])
                    st.selectbox(
                        label=f"Amount for {ing.get('name')}", 
                        options=options, 
                        key=f"amount_{idx}_{i}",
                        label_visibility="collapsed"
                    )
            
        # Contextual Step Timer
        timer_mins = step.get("timer_minutes", 0)
        if timer_mins > 0:
            st.write("---")
            st.write("**Active Step Timer:**")
            timer_display = st.empty()
            if st.button(f"Start Countdown ({timer_mins} mins)", key=f"timer_start_{idx}"):
                total_seconds = timer_mins * 60
                while total_seconds > 0:
                    m, s = divmod(total_seconds, 60)
                    timer_display.metric("Time Remaining", f"{m:02d}:{s:02d}")
                    time.sleep(1)
                    total_seconds -= 1
                timer_display.success("Timer Complete!")
        
        st.write("---")
        
        # Interface Navigation Buttons
        nav_cols = st.columns([1, 1, 4])
        with nav_cols[0]:
            if st.button("Back", disabled=(idx == 0)):
                st.session_state.current_step -= 1
                st.rerun()
        with nav_cols[1]:
            if st.button("Next", disabled=(idx == len(steps) - 1)):
                st.session_state.current_step += 1
                st.rerun()
