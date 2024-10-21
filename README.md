# A visionary companion for the new world by Utsav Soni.
# Smart Vision 𓆩👁️𓆪

This Streamlit application allows users to capture images via webcam and get a detailed, real-time audio description using a combination of the Groq AI API and Google Text-to-Speech (gTTS). It is designed to assist visually impaired users or those who need instant descriptions of their surroundings.

## Features

- **Webcam Image Capture**: Users can capture images using the built-in camera functionality of their device.
- **Image-to-Text Conversion**: Images are processed through the Groq API using the LLaMA 3.2 Vision model to generate a descriptive text response.
- **Audio Description**: The generated description is converted to speech using the Google Text-to-Speech (gTTS) API and played back automatically.
- **Interactive Controls**: Users can regenerate descriptions for the captured image and replay the audio at any time.
- **Responsive UI**: The UI includes a clean layout with logos, buttons for user interaction, and sound effects for actions like capturing images and regenerating descriptions.

## Prerequisites

Before running the application, ensure you have the following:

1. **API Keys**:
   - `GROQ_API_KEY`: Groq API key for image-to-text generation.
   - `LANGSMITH_API_KEY`: Langsmith API key for tracing.
   
   Store these keys in a `.env` file in the project directory.

2. **Python Dependencies**:
   - `streamlit`
   - `groq`
   - `gTTS`
   - `PIL` (Pillow)
   - `dotenv`
   - `langsmith`

   Install the dependencies using:

   ```bash
   pip install -r requirements.txt

# **Installation**
Clone this repository:

## bash
git clone https://github.com/your-username/smart-vision.git
cd smart-vision
Create a .env file in the project root:

## .env
GROQ_API_KEY=your_groq_api_key
LANGSMITH_API_KEY=your_langsmith_api_key
Install the required Python packages:

## bash
pip install -r requirements.txt
Ensure the sound files (camera.mp3, button1.mp3, and button2.mp3) are placed in the project directory.

## Usage
Run the Streamlit app bash:
streamlit run vision_app.py
Open the browser link provided by Streamlit.

# Instructions:

Use the "Take a picture" button to capture an image using your webcam.
A description of the image will be generated and read aloud automatically.
Use the buttons to regenerate the description or replay the audio.
Project Structure
vision_app.py: Main application code.
.env: Contains environment variables (API keys).
camera.mp3, button1.mp3, button2.mp3: Sound effect files.
requirements.txt: Python dependencies.
