import streamlit as st
import os
import hashlib
import sqlite3
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai

# Load all the environment variables
load_dotenv()

# Configure the Generative AI API with the API key
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize the new model with the correct name
new_model = genai.GenerativeModel('models/gemini-1.5-flash-latest')

# Function to load Google Gemini Pro Vision API and get a response
def get_gemini_response(input_text, image_data, prompt):
    response = new_model.generate_content([input_text, image_data[0], prompt])
    return response.text

# Function to set up the input image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
                "data": bytes_data
            }
        ]
        return bytes_data, image_parts
    else:
        raise FileNotFoundError("No file uploaded")

# Initialize the Streamlit app
st.set_page_config(page_title="Gemini Health App")

st.header("Gemini Health App")

# Create or connect to the SQLite database
conn = sqlite3.connect("image_data.db")
c = conn.cursor()

# Create the table with the new schema if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS images (
    hash TEXT,
    prompt TEXT,
    description TEXT,
    PRIMARY KEY (hash, prompt)
)
''')
conn.commit()

# Input prompt from the user
input_text = st.text_input("Input Prompt: ", key="input")

# File uploader for the user to upload an image
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# Display the uploaded image
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.", use_column_width=True)

# Submit button
submit = st.button("Tell me the total calories")

# Input prompt for the nutrition expert
input_prompt = """
You are an expert in nutrition analysis. You have been provided an image of a food plate or bowl meal. Your task is to identify all the food items in the image and provide a detailed nutritional breakdown. Ensure to be accurate and thorough in your analysis. Each food item should be described clearly, including the quantity (e.g., 4 pieces of tofu), and accompanied by an estimate of its protein, carbohydrates, and calorie content. Additionally, provide recommendations for gym or cardio exercises to burn the total number of calories in the meal.

Always respond in the following fixed format and avoid providing incorrect information. If exact details are not available, provide an educated approximation but do not state that you need more information or that it is impossible to provide the analysis:

1. Item 1 - Description: [quantity and description], Protein: [protein content]g, Carbohydrates: [carbohydrate content]g, Calories: [calorie content] kcal
2. Item 2 - Description: [quantity and description], Protein: [protein content]g, Carbohydrates: [carbohydrate content]g, Calories: [calorie content] kcal
3. ...

----
Total Protein: [total protein]g
Total Carbohydrates: [total carbohydrates]g
Total Calories: [total calories] kcal

Recommended Exercises to Burn Total Calories:
1. [Exercise 1] - [description], [duration]
2. [Exercise 2] - [description], [duration]
3. ...

Analyze the items in the image very carefully and provide an estimate of their protein, carbohydrates, and calorie content. DO NOT miss any item from the picture and be as detailed and specific as you can. Provide an approximation if exact details are not available. DO NOT say you need more information or that it is impossible to provide the analysis.
"""

# If submit button is clicked
if submit:
    if uploaded_file is not None:
        bytes_data, image_data = input_image_setup(uploaded_file)
        
        # Compute the hash of the image
        image_hash = hashlib.md5(bytes_data).hexdigest()
        st.write(f"Image hash: {image_hash}")
        
        # Check if the image and prompt combination has been processed before
        c.execute("SELECT description FROM images WHERE hash = ? AND prompt = ?", (image_hash, input_text))
        result = c.fetchone()
        
        if result:
            description = result[0]
            st.write("Retrieved from database.")
        else:
            description = get_gemini_response(input_text, image_data, input_prompt)
            # Filter out any negative remarks (basic example, refine as needed)
            positive_description = "\n".join([line for line in description.split('\n') if "cannot" not in line.lower() and "sorry" not in line.lower()])
            # Store the result in the database
            c.execute("INSERT INTO images (hash, prompt, description) VALUES (?, ?, ?)", (image_hash, input_text, positive_description))
            conn.commit()
            st.write("Generated new response and saved to database.")
        
        st.subheader("The Response is:")
        st.write(description)
    else:
        st.error("Please upload an image to proceed.")

# Close the database connection
conn.close()
