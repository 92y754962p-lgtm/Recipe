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
        
        JSON Schema Requirements:
        1. "title": String name of recipe.
        2. "steps": List of object steps containing:
            - "step_number": Integer
            - "text": String instruction. Ensure all measurements needed are explicitly embedded inline in this text sentence.
            - "timer_minutes": Integer (cooking duration, 0 if none).
            - "ingredients_in_step": List of strings for ingredients used in this step.
            - "measurements": List of objects for each measurement found in the step text:
                - "label": String name of ingredient/item being measured.
                - "options": List of strings containing converted values (e.g., ["2 cups", "240 grams", "8.4 oz"]).
        
        Recipe Source Text:
        {text_content[:8000]}
        
        Return ONLY raw valid JSON matching the schema. No markdown wrapping blocks.
        """
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        
        cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned_text)
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
        st.info(step.get("text", ""))
        
        # Inline Measurement Unit Toggles
        measurements = step.get("measurements", [])
        if measurements:
            st.write("**Unit Conversions:**")
            cols = st.columns(len(measurements))
            for i, meas in enumerate(measurements):
                with cols[i % len(cols)]:
                    st.selectbox(
                        label=meas.get("label", f"Unit {i+1}"),
                        options=meas.get("options", []),
                        key=f"meas_{idx}_{i}"
                    )
        
        # Step Ingredient Multi-Checklist
        ingredients = step.get("ingredients_in_step", [])
        if len(ingredients) > 1:
            st.write("**Ingredient Tracker:**")
            for ing in ingredients:
                st.checkbox(ing, key=f"check_{idx}_{ing}")
        elif len(ingredients) == 1:
            st.write(f"**Ingredient Active:** {ingredients[0]}")
            
        # Contextual Step Timer
        timer_mins = step.get("timer_minutes", 0)
        if timer_mins > 0:
            st.write("**Active Step Timer:**")
            timer_display = st.empty()
            if st.button("Start Countdown", key=f"timer_start_{idx}"):
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
