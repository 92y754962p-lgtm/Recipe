import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_recipe(url, target_servings):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(separator="\n")
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # PASS 1: Extract the "Ground Truth" dictionary
        prompt1 = f"Extract a JSON dictionary of ALL ingredients and their exact amounts from this text: {text[:8000]}"
        res1 = model.generate_content(prompt1)
        ground_truth = json.loads(res1.text.replace("```json", "").replace("```", ""))
        
        # PASS 2: Write steps using ONLY the ground truth
        prompt2 = f"""
        Using ONLY this ingredient list: {json.dumps(ground_truth)}
        Write the recipe steps for {target_servings} servings.
        For every ingredient in a step, replace the ingredient name with the measurement from the list. 
        Return JSON: {{"steps": [{{"title": "...", "text": "...", "items": ["700g chicken"]}}]}}
        Text: {text[:8000]}
        """
        res2 = model.generate_content(prompt2)
        return json.loads(res2.text.replace("```json", "").replace("```", ""))
        
    except Exception as e:
        return {"error": str(e)}

# --- UI ---
st.title("Interactive Kitchen")
url = st.text_input("URL:")
servings = st.number_input("Servings:", value=2)

if st.button("Go"):
    with st.spinner("Processing..."):
        data = get_recipe(url, servings)
        if "error" in data: st.error(data["error"])
        else: 
            st.session_state.data = data
            st.rerun()

if "data" in st.session_state:
    for step in st.session_state.data["steps"]:
        st.subheader(step["title"])
        st.write(step["text"])
        for item in step["items"]:
            st.checkbox(item)
