from flask import Flask, render_template, request
from google import genai
from google.genai import types
from PIL import Image
import os
from io import BytesIO
import base64
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# set api key from os environment variable
apiKey = os.environ.get("GOOGLE_API_KEY")

if not apiKey:
    raise ValueError("No GOOGLE_API_KEY set for Flask application. Did you set it in .env?")
# setup the flask app

app = Flask(__name__)

# configure the google genai client

client = genai.Client(api_key=apiKey)

textModel = "gemini-2.0-flash"
imageModel = "gemini-2.0-flash-preview-image-generation"

# In-memory store for recent haikus. For a production app, consider a database.
recent_haikus_store = []
MAX_RECENT_HAIKUS = 6

# run the flask app
@app.route('/', methods=['GET', 'POST'])
def index():
    haikuText = None
    haikuImageRequest = None
    current_image_url = None

    if request.method == 'POST':
        haiku_topic = request.form.get('haiku_topic')
        haikuRequest= client.models.generate_content(
            model="gemini-2.0-flash",
            contents = [f"Write a haiku about {haiku_topic}."]
        )
        haikuText = haikuRequest.text        

        haikuImageRequest = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[f"Generate an image that visually captures the essence and mood of the following haiku: '{haikuText}'. Important: The image must not contain any form of text, words, letters, or writing."],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
                )
            )

        for part in haikuImageRequest.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                unique_id = str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for brevity
                image_filename = f"haiku_image_{unique_id}.png"
                
                # Open the image data
                haikuImage = Image.open(BytesIO(part.inline_data.data))
                
                # Ensure the images directory exists
                images_dir = os.path.join(os.path.dirname(__file__), 'static')
                os.makedirs(images_dir, exist_ok=True)
                
                # Save the image
                image_path = os.path.join(images_dir, image_filename)
                haikuImage.save(image_path)
                
                # Create URL path for the current image
                current_image_url = f'/static/{image_filename}'

                # Add to recent haikus store
                if haikuText and current_image_url:
                    recent_haikus_store.append({
                        "text": haikuText,
                        "image_url": current_image_url
                    })
                    # Keep only the last MAX_RECENT_HAIKUS items
                    while len(recent_haikus_store) > MAX_RECENT_HAIKUS:
                        recent_haikus_store.pop(0)

    return render_template('index.html', haikuText=haikuText, image_url=current_image_url, recent_haikus=list(reversed(recent_haikus_store)))

if __name__ == '__main__':
    app.run(debug=False)