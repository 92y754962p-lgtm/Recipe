import streamlit as st
import google.generativeai as genai
import json

# --- Config ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- Logic ---
def get_structured_recipe(url, target_servings):
    try:
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # We instruct the model to specifically locate the JSON-LD schema
        prompt = f"""
        Go to this URL: {url}.
        Find the JSON-LD schema (structured recipe data).
        Extract it and scale the ingredient amounts to {target_servings} servings.
        
        Return JSON exactly in this format:
        {{
          "steps": [
            {{
              "title": "Step",
              "text": "Instruction text",
              "items": ["700g chicken", "1 tbsp oil"]
            }}
          ]
        }}
        """
        res = model.generate_content(prompt)
        raw = res.text.replace("```json", "").replace("```", "")
        return json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive Kitchen (Schema-Based)")

url = st.text_input("Recipe URL:")
servings = st.number_input("Servings:", min_value=1, value=2)

if st.button("Go"):
    with st.spinner("Fetching structured data..."):
        data = get_structured_recipe(url, servings)
        if "error" in data: 
            st.error(data["error"])
        else: 
            st.session_state.data = data
            st.rerun()

if "data" in st.session_state:
    for step in st.session_state.data["steps"]:
        st.subheader(step.get("title", "Step"))
        st.write(step.get("text", ""))
        for item in step.get("items", []):
            st.checkbox(item)
