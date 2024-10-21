import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
import base64
import json
from PIL import Image
import io
from gtts import gTTS
from langsmith import traceable

# Load environment variables from .env file
load_dotenv()

# Set up the API key for Groq
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("API key not found. Please set GROQ_API_KEY environment variable.")

# Initialize the Groq client
client = Groq(api_key=api_key)
llama_3_2 = 'llama-3.2-90b-vision-preview'

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "vision_app"
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

# Inject custom JavaScript for requesting camera and audio permissions
st.markdown("""
    <script>
        function requestPermissions() {
            navigator.mediaDevices.getUserMedia({ video: true, audio: true })
                .then(function(stream) {
                    console.log("Permissions granted");
                })
                .catch(function(err) {
                    console.error("Permissions denied:", err);
                });
        }
        requestPermissions();
    </script>
""", unsafe_allow_html=True)

# Add custom CSS for mobile optimization and to adjust camera input size
st.markdown("""
    <style>
        .camera-permission-info {
            background-color: #f9f9f9;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .camera-container {
            width: 400px;  /* Adjust width */
            margin: 0 auto; /* Center the camera input */
        }
        input[type="file"] {
            width: 100%; /* Makes the camera input full width */
            height: auto; /* Adjust height automatically */
        }
    </style>
""", unsafe_allow_html=True)

class TTSManager:
    def __init__(self):
        self.is_speaking = False

    def generate_audio(self, text, filename="output.mp3"):
        """Generate audio file from text using gTTS."""
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(filename)
            return True
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
        return False

    def create_audio_element(self, text):
        """Create an audio element with the generated audio."""
        if self.generate_audio(text):
            try:
                with open("output.mp3", "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    
                    audio_html = f"""
                    <audio id="autoAudio" autoplay>
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    </audio>
                    <script>
                        document.getElementById('autoAudio').play();
                    </script>
                    """
                    st.markdown(audio_html, unsafe_allow_html=True)
                    return True
            except Exception as e:
                st.error(f"Error creating audio element: {str(e)}")
        return False

    def play_sound(self, filename):
        """Play a specific sound file."""
        try:
            with open(filename, "rb") as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
                
                sound_html = f"""
                <audio id="soundEffect" autoplay>
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
                <script>
                    document.getElementById('soundEffect').play();
                </script>
                """
                st.markdown(sound_html, unsafe_allow_html=True)
                return True
        except Exception as e:
            st.error(f"Error playing sound: {str(e)}")
        return False

# Initialize TTS manager in session state
if 'tts_manager' not in st.session_state:
    st.session_state.tts_manager = TTSManager()

def show_permission_instructions():
    """Show instructions for enabling permissions on mobile devices."""
    st.markdown("""<div class="camera-permission-info">Please allow camera and microphone permissions to use this feature.</div>""", unsafe_allow_html=True)

def capture_image():
    """Capture an image from the webcam and encode it as Base64."""
    show_permission_instructions()
    
    with st.container():  # Use a container to apply CSS
        img_file = st.camera_input("Take a picture", help="Click to take a photo")
    
    if img_file:
        st.session_state.tts_manager.play_sound("camera.mp3")  # Play camera sound
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

@traceable
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
response=""
def main():
    st.title("Smart Image Describer")
    
    # Add a brief introduction
    st.markdown("""📸 Take a picture and get an instant audio description!""")

    # Initialize session state
    if 'last_processed_image' not in st.session_state:
        st.session_state.last_processed_image = None
        
    if 'last_response' not in st.session_state:
        st.session_state.last_response = None
    
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
                st.session_state.last_response = response
                
                # Auto-generate and play audio
                st.session_state.tts_manager.create_audio_element(response)

    # Retry option
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📸 Regenerate Picture Description", use_container_width=True):
            st.session_state.last_processed_image = None
            st.session_state.tts_manager.play_sound("button1.mp3")  # Play sound on click
            st.rerun()
    
    
    with col2:
        if st.button("🔊 Replay Audio", use_container_width=True):
            if st.session_state.last_response:
               st.session_state.tts_manager.create_audio_element(st.session_state.last_response)
               st.session_state.tts_manager.play_sound("button2.mp3")  # Different sound for replay

if __name__ == "__main__":
    main()

