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

# Ingredient density database (grams per 1 cup) for Python-side conversions
INGREDIENT_DENSITIES = {
    "flour": 120.0,
    "sugar": 200.0,
    "granulated sugar": 200.0,
    "brown sugar": 200.0,
    "powdered sugar": 120.0,
    "butter": 227.0,
    "water": 236.6,
    "milk": 242.0,
    "almond milk": 240.0,
    "oil": 218.0,
    "vegetable oil": 218.0,
    "salt": 300.0,  # 1 cup of salt is roughly 300g (though usually measured in tsp)
    "baking powder": 240.0,
    "baking soda": 288.0,
}

def convert_units(amount, unit, ingredient_name):
    """Calculates metric and imperial variations locally to save LLM compute time."""
    normalized_ing = ingredient_name.lower().strip()
    unit = unit.lower().strip()
    
    # Standardize common unit strings
    if unit in ["cup", "cups", "c"]:
        base_cups = amount
    elif unit in ["tablespoon", "tablespoons", "tbsp", "tbs"]:
        base_cups = amount / 16.0
    elif unit in ["teaspoon", "teaspoons", "tsp"]:
        base_cups = amount / 48.0
    elif unit in ["fluid ounce", "fluid ounces", "fl oz"]:
        base_cups = amount / 8.0
    else:
        # Fallback if unit is already a weight or unhandled
        if unit in ["gram", "grams", "g"]:
            return [f"{amount} Grams", f"{amount/28.35:.2f} Ounces"]
        if unit in ["ounce", "ounces", "oz"]:
            return [f"{amount} Ounces", f"{amount*28.35:.1f} Grams"]
        return [f"{amount} {unit}"]

    # Determine density factors
    density = INGREDIENT_DENSITIES.get(normalized_ing, 236.6) # Default to water density
    
    grams = base_cups * density
    ounces = grams / 28.35
    
    # Generate cleaner strings depending on scale
    options = [f"{amount} {unit}"]
    if grams >= 1:
        options.append(f"{grams:.1f} Grams")
    if ounces >= 0.05:
        options.append(f"{ounces:.2f} Ounces")
        
    return options

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
        4. Isolate the numerical quantity and unit name into separate fields. Do not perform math conversions here.
        
        JSON Schema Requirements:
        1. "title": String name of recipe.
        2. "steps": List of object steps containing:
            - "step_number": Integer
            - "action_header": String (e.g., "Whisk Dry Ingredients (Medium Bowl)")
            - "description": String (Brief 1-2 sentence instruction of what to do with the items).
            - "timer_minutes": Integer (cooking duration, 0 if none).
            - "ingredients": List of objects for each item used in this step:
                - "name": String (e.g., "Flour")
                - "amount": Float (The numerical value only, e.g., 1.5)
                - "unit": String (The unit label only, e.g., "Cups")
        
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
        
        # Display Ingredients with Inline Unit Toggles calculated via Python
        ingredients = step.get("ingredients", [])
        if ingredients:
            st.write("**Ingredients:**")
            for i, ing in enumerate(ingredients):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.checkbox(f"**{ing.get('name', 'Ingredient')}**", key=f"check_{idx}_{i}")
                with col2:
                    # Calculate unit drop-down arrays dynamically in local memory
                    amt = ing.get("amount", 0.0)
                    unt = ing.get("unit", "")
                    name = ing.get("name", "")
                    
                    calculated_options = convert_units(amt, unt, name)
                    
                    st.selectbox(
                        label=f"Amount for {name}", 
                        options=calculated_options, 
                        key=f"amount_{idx}_{i}",
                        label_visibility="collapsed"
                    )
            
        # Contextual Step Timer with an animated progress bar
        timer_mins = step.get("timer_minutes", 0)
        if timer_mins > 0:
            st.write("---")
            st.write("**Active Step Timer:**")
            timer_display = st.empty()
            timer_bar = st.progress(1.0)
            
            if st.button(f"Start Countdown ({timer_mins} mins)", key=f"timer_start_{idx}"):
                total_seconds = timer_mins * 60
                initial_seconds = total_seconds
                while total_seconds > 0:
                    m, s = divmod(total_seconds, 60)
                    timer_display.metric("Time Remaining", f"{m:02d}:{s:02d}")
                    timer_bar.progress(total_seconds / initial_seconds)
                    time.sleep(1)
                    total_seconds -= 1
                timer_bar.progress(0.0)
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
