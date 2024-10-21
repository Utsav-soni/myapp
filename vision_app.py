import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
import base64
import json
from PIL import Image
from gtts import gTTS
import io

# Load environment variables from .env file
load_dotenv()

# Set up the API key for Groq
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("API key not found. Please set GROQ_API_KEY environment variable.")

# Initialize the Groq client
client = Groq(api_key=api_key)
llama_3_2 = 'llama-3.2-90b-vision-preview'

# Inject custom JavaScript for requesting camera and audio permissions
st.markdown("""
    <script>
        function requestPermissions() {
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                .then(function(stream) {
                    console.log('Permissions granted');
                })
                .catch(function(error) {
                    console.error('Permissions denied', error);
                });
        }
        requestPermissions();
    </script>
    """, unsafe_allow_html=True)

# Add custom CSS for mobile optimization
st.markdown("""
    <style>
        .stButton>button {
            width: 100%;
            margin-top: 10px;
        }
        .camera-permission-info {
            padding: 10px;
            background-color: #f0f2f6;
            border-radius: 5px;
            margin: 10px 0;
        }
        @media (max-width: 768px) {
            .stCamera {
                width: 100% !important;
            }
            .stCamera>div {
                min-height: 300px;
            }
        }
    </style>
    """, unsafe_allow_html=True)


def show_permission_instructions():
    """Show instructions for enabling permissions on mobile devices."""
    st.markdown("""
    <div class="camera-permission-info">
        <h4>📱 Mobile Device Instructions:</h4>
        <p>This app needs camera and audio permissions to work:</p>
        <ol>
            <li>When prompted, tap "Allow" for camera and audio access</li>
            <li>If permissions are blocked, enable them in your browser settings:
                <ul>
                    <li>Tap the lock icon (🔒) in your address bar</li>
                    <li>Enable camera and audio permissions</li>
                    <li>Refresh the page</li>
                </ul>
            </li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

def capture_image():
    """Capture an image from the webcam and encode it as Base64."""
    show_permission_instructions()
    
    img_file = st.camera_input("Take a picture", help="Click to take a photo")
    if img_file:
        try:
            img = Image.open(img_file)
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
            base64_image = base64.b64encode(img_bytes).decode('utf-8')
            save_base64_image(base64_image)
            return base64_image
        except Exception as e:
            st.error(f"Error capturing image: {str(e)}")
            return None
    return None

def save_base64_image(base64_image):
    """Save the Base64 image string to a text file."""
    try:
        json_data = json.dumps({"image": base64_image})
        filename = 'output.txt'
        
        with open(filename, 'w') as file:
            json.dump(json_data, file, indent=4)
    except Exception as e:
        st.error(f"Error saving image data: {str(e)}")

def image_to_text(client, model, base64_image, prompt):
    """Convert an image to text using the Groq client."""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                    ]
                }
            ],
            model=model
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating description: {str(e)}")
        return None
        
def play_audio(text):
    """Generate audio using gTTS and save it to a file."""
    tts = gTTS(text, lang='en')
    audio_file_path = "response.mp3"
    tts.save(audio_file_path)
    return audio_file_path

def main():
    st.title("Smart Image Describer")
    
    # Add a brief introduction
    st.markdown("""📸 Take a picture and get an instant audio description!""")

    # Initialize session state
    if 'last_processed_image' not in st.session_state:
        st.session_state.last_processed_image = None
    
    # Capture image
    base64_image = capture_image()

    # Only process if we have a new image
    if base64_image and base64_image != st.session_state.last_processed_image:
        st.session_state.last_processed_image = base64_image
        
        prompt = "Describe this image smartly in 4-5 lines to the person who is completely unaware of the surroundings in a descriptive way."
        
        with st.spinner("Generating description..."):
            response = image_to_text(client, llama_3_2, base64_image, prompt)
            
            if response:
                st.markdown("### Image Description:")
                st.write(response)
                
                # Automatically play audio description
                st.info("🔊 Playing audio description... Please ensure your volume is turned on.")
                
                # Generate and play audio description
                audio_file_path = play_audio(response)
                st.audio(audio_file_path, format='audio/mp3', start_time=0)  # Start audio playback

    # Retry option
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📸 Take Another Picture", use_container_width=True):
            st.session_state.last_processed_image = None
            st.rerun()
    with col2:
        if st.button("🔊 Replay Audio", use_container_width=True):
            if hasattr(st.session_state, 'last_response'):
                audio_file_path = play_audio(st.session_state.last_response)
                st.audio(audio_file_path, format='audio/mp3', start_time=0)


if __name__ == "__main__":
    main()
