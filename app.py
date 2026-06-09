def get_recipe(url, target_servings, status_container):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"error": f"Site returned status {response.status_code}."}
        
        soup = BeautifulSoup(response.text, "html.parser")
        text = "\n".join([t.get_text() for t in soup.find_all(['h1', 'h2', 'li', 'p']) if len(t.get_text()) > 10])[1000:6000]
        
        model = genai.GenerativeModel("gemini-3.5-flash")
        
        # --- PASS 1: Strict Extraction with Forced Context Injection ---
        status_container.update(label="Pass 1: Mapping steps to master ingredient list...", state="running")
        extract_prompt = f"""
        You are a data extraction bot. 
        Step 1: First, list all ingredients and their exact measurements from the 'Ingredients' section of the provided text.
        Step 2: Now, process the 'Steps' section. For every ingredient mentioned in a step, assign the exact measurement you found in Step 1.
        
        CRITICAL: If a step mentions 'garlic powder' but not the amount, you MUST insert the amount found in the master list. Do not use 'Not specified'.
        
        Source text: {text}
        
        Return JSON only:
        {{
          "original_servings": 2,
          "steps": [
            {{
              "action_header": "Title",
              "description": "Exact instruction text",
              "timer_minutes": 0,
              "ingredients": [ {{"name": "ingredient name", "original_amount": "full measurement from master list"}} ]
            }}
          ]
        }}
        """
        
        res1 = model.generate_content(extract_prompt)
        clean_res1 = res1.text.strip().replace("```json", "").replace("```", "")
        extracted_data = json.loads(clean_res1)
        original_servings = extracted_data.get("original_servings", 1)
        
        # --- PASS 2: Scaling (same as before) ---
        status_container.update(label=f"Pass 2: Scaling from {original_servings} to {target_servings} servings...", state="running")
        scale_prompt = f"""
        Take this JSON and scale ingredients from {original_servings} to {target_servings} servings.
        Multiply amounts by ({target_servings}/{original_servings}). Provide metric and imperial conversions in 'amount_options'.
        
        JSON: {json.dumps(extracted_data)}
        """
        
        res2 = model.generate_content(scale_prompt)
        clean_res2 = res2.text.strip().replace("```json", "").replace("```", "")
        final_data = json.loads(clean_res2)
        
        status_container.update(label="Complete!", state="complete")
        return final_data
        
    except Exception as e:
        return {"error": str(e)}
