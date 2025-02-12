// script.js
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('recipeForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        const ingredients = document.getElementById('ingredients').value;
        const diet = document.getElementById('diet').value;

        try {
            const response = await fetch('/suggest_recipes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ingredients: ingredients.split(',').map(item => item.trim()),
                    diet: diet
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`); //Improved error handling
            }

            const result = await response.json();

            // Improved display logic
            const outputDiv = document.getElementById('output');
            outputDiv.innerHTML = ""; // Clear previous results

            if (result.original_recipes && result.original_recipes.length > 0) {
                result.original_recipes.forEach(recipe => {
                    const recipeDiv = document.createElement('div');
                    recipeDiv.innerHTML = `<h3>${recipe.title}</h3>`;

                    if (recipe.image) {
                        recipeDiv.innerHTML += `<img src="${recipe.image}" alt="${recipe.title}">`;
                    }

                    if (recipe.extendedIngredients) {
                      recipeDiv.innerHTML += "<h4>Ingredients:</h4><ul>";
                      recipe.extendedIngredients.forEach(ingredient => {
                        recipeDiv.innerHTML += `<li>${ingredient.original}</li>`;
                      });
                      recipeDiv.innerHTML += "</ul>";
                    }

                    if(recipe.analyzedInstructions && recipe.analyzedInstructions.length > 0 && recipe.analyzedInstructions.steps){
                        recipeDiv.innerHTML += "<h4>Instructions:</h4><ol>";
                        recipe.analyzedInstructions.steps.forEach(step => {
                            recipeDiv.innerHTML += `<li>${step.step}</li>`;
                        });
                        recipeDiv.innerHTML += "</ol>";
                    }
                    outputDiv.appendChild(recipeDiv);
                });
            } else {
                outputDiv.innerHTML = "<p>No recipes found.</p>";
            }

            if (result.refined_suggestions) {
                const refinedDiv = document.createElement('div');
                refinedDiv.innerHTML = "<h2>Refined Suggestions:</h2><p>" + result.refined_suggestions + "</p>";
                outputDiv.appendChild(refinedDiv);
            }


        } catch (error) {
            document.getElementById('output').innerText = `Error: ${error.message}`; //Improved error handling
            console.error("Error fetching recipes:", error); // Log the error to the console for debugging
        }
    });
});