from flask import Flask, request, jsonify, render_template
import os
import requests
import asyncio
import httpx
import google.generativeai as genai
from google.generativeai import GenerativeModel

# Load API keys from environment variables
SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# Ensure API keys are set
if not SPOONACULAR_API_KEY:
    raise ValueError("SPOONACULAR_API_KEY environment variable not set")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = GenerativeModel(GEMINI_MODEL_NAME)

# Initialize Flask app
app = Flask(__name__)

BASE_URL = "https://api.spoonacular.com/recipes"

async def fetch_recipes(ingredients, dietary_restrictions):
    """Fetch recipes from Spoonacular and get full details."""
    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "ingredients": ",".join(ingredients),
        "number": 5,  # Or whatever number you want
        "diet": dietary_restrictions,
        "ranking": 2
    }

    async with httpx.AsyncClient() as client: #Keep the client open for all the requests
        response = await client.get(f"{BASE_URL}/findByIngredients", params=params)

        if response.status_code != 200:
            return {"error": f"Failed to fetch initial recipes: {response.status_code}", "details": response.text}

        initial_recipes = response.json()
        detailed_recipes = []

        for recipe in initial_recipes:
            recipe_id = recipe["id"]
            info_response = await client.get(f"{BASE_URL}/{recipe_id}/information", params={"apiKey": SPOONACULAR_API_KEY, "includeNutrition": True})
            if info_response.status_code == 200:
                detailed_recipes.append(info_response.json())
            else:
                print(f"Error fetching details for recipe {recipe_id}: {info_response.status_code} - {info_response.text}")
                recipe['error'] = f"Failed to fetch recipe details: {info_response.status_code}"
                detailed_recipes.append(recipe)

        return detailed_recipes

async def generate_gemini_suggestions(ingredients, dietary_restrictions, spoonacular_recipes):
    recipes_string = ""
    for recipe in spoonacular_recipes:
        ingredients_list = ", ".join([ing["name"] for ing in recipe.get("extendedIngredients",)])  # Corrected key
        instructions_snippet = ""
        if recipe.get("analyzedInstructions"):
            for step in recipe["analyzedInstructions"].get("steps",)[:3]:  # Corrected key and access
                instructions_snippet += f"{step['number']}. {step['step']}\n"

        recipes_string += f"""
        Recipe: {recipe.get('title', 'N/A')}
        Ingredients: {ingredients_list}
        Instructions:
        {instructions_snippet}

        """
    content = f"""
    Here are some recipes based on these ingredients: {ingredients}.
    Dietary restriction: {dietary_restrictions}.
    Given these Spoonacular suggestions: {recipes_string}, refine the results and suggest the best ones.
    """
    try:
        gemini_response = await asyncio.to_thread(model.generate_content, contents=[content])
        return gemini_response.text if gemini_response else "No refined suggestions available."
    except Exception as e:
        return f"Error generating Gemini suggestions: {e}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/suggest_recipes', methods=['POST'])
async def suggest_recipes():
    data = request.json
    ingredients = data.get("ingredients", [])
    dietary_restrictions = data.get("diet", "")

    if not ingredients or not isinstance(ingredients, list):
        return jsonify({"error": "Invalid ingredients format. Provide a list of ingredients."}), 400

    try:
        spoonacular_recipes = await fetch_recipes(ingredients, dietary_restrictions)
        if "error" in spoonacular_recipes and isinstance(spoonacular_recipes, dict):
            return jsonify(spoonacular_recipes), 400

        refined_suggestions = await generate_gemini_suggestions(ingredients, dietary_restrictions, spoonacular_recipes) # Corrected line!
        return jsonify({
            "original_recipes": spoonacular_recipes,
            "refined_suggestions": refined_suggestions
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_meal_plan', methods=['POST'])
async def generate_meal_plan():
    """Handle meal plan generation."""
    data = request.json
    dietary_restrictions = data.get("diet", "")
    target_calories = data.get("target_calories", 2000)

    params = {
        "apiKey": SPOONACULAR_API_KEY,
        "timeFrame": "week",
        "targetCalories": target_calories,
        "diet": dietary_restrictions
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/mealplanner/generate", params=params)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({"error": f"Failed to generate meal plan: {response.status_code}", "details": response.text}), response.status_code

if __name__ == '__main__':
    app.run(debug=True)
