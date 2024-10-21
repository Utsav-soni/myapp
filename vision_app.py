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
import time

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

# Initialize session state variables
if 'last_response' not in st.session_state:
    st.session_state.last_response = None
if 'last_processed_image' not in st.session_state:
    st.session_state.last_processed_image = None
if 'description_visible' not in st.session_state:
    st.session_state.description_visible = False
if 'needs_audio_playback' not in st.session_state:
    st.session_state.needs_audio_playback = False

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        return base64.b64encode(f.read()).decode()

logo_left_b64 = get_base64_of_bin_file('mark2.svg')
logo_right_b64 = get_base64_of_bin_file('mark1.svg')

# [Your existing CSS styling code remains the same]
st.markdown(f"""
    <style>
        .svg-left {{
            position: absolute;
            top: 10px;
            left: 10px;
        }}
        .svg-right {{
            position: absolute;
            top: 10px;
            right: 10px;
        }}
        .svg-right img {{
            height: 60px;
            width: 187px;
            object-fit: contain;
            padding-top: 0px;
            padding-right: 0px;
            padding-bottom: 25px;
            padding-left: 0px;
        }}
        .svg-left img {{
            height: 69px;
            width: 93px;
            object-fit: contain;
            padding-top: 0px;
            padding-right: 0px;
            padding-bottom: 33px;
            padding-left: 0px;
        }}
    </style>
     <div style="text-align: center;">
        <img src="data:image/svg+xml;base64,{logo_left_b64}" style="height: 69px; width: 93px; object-fit: contain; padding: 10px 0;">
    </div>
    <div style="text-align: center;">
    <img src="data:image/svg+xml;base64,{logo_right_b64}" style="height: 60px; width: 187px; object-fit: contain; padding: 10px 0;">
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        body {
            background-color: #ffffff;
            color: #333333;
        }
        
        .st-emotion-cache-13ln4jf  {
            width: auto !important;
            padding: 0 !important;
            box-sizing: border-box;
        }
        
        .camera-permission-info {
            background-color: #f9f9f9;
            color: #333333;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            border: 1px solid #ccc;
        }
        .camera-container {
            width: 400px;
            margin: 0 auto;
        }
        input[type="file"] {
            width: 100%;
            height: auto;
        }
        button {
            background-color: #007BFF;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 10px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .st-emotion-cache-12fmjuu {
            display:none;
        }
        
        #smart-image-describer{
            padding-top: 1.25rem;
            padding-right: 0rem;
            padding-bottom: 2rem;
            padding-left: 0rem;
        }
        .st-emotion-cache-khjqke{
            padding:2.375rem 0.75rem;
        }
    </style>
""", unsafe_allow_html=True)

class TTSManager:
    def __init__(self):
        self.is_speaking = False
        self.current_audio = None

    def stop_current_audio(self):
        """Stop any currently playing audio."""
        if self.current_audio:
            st.markdown("""
                <script>
                    var audios = document.getElementsByTagName('audio');
                    for(var i = 0; i < audios.length; i++){
                        audios[i].pause();
                        audios[i].currentTime = 0;
                    }
                </script>
            """, unsafe_allow_html=True)
            time.sleep(0.3)  # Small delay to ensure audio stops

    def generate_audio(self, text, filename="output.mp3"):
        """Generate audio file from text using gTTS."""
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(filename)
            return True
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
            return False

    def create_audio_element(self, text, priority=False):
        """Create an audio element with the generated audio."""
        self.stop_current_audio()
        if self.generate_audio(text):
            try:
                with open("output.mp3", "rb") as audio_file:
                    audio_bytes = audio_file.read()
                    audio_base64 = base64.b64encode(audio_bytes).decode()
                    
                    volume = "1.0" if not priority else "1.5"
                    
                    audio_html = f"""
                    <audio id="autoAudio" autoplay>
                        <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                    </audio>
                    <script>
                        var audio = document.getElementById('autoAudio');
                        audio.volume = {volume};
                        audio.play();
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
                time.sleep(0.5)  # Wait for sound to complete
                return True
        except Exception as e:
            st.error(f"Error playing sound: {str(e)}")
            return False

# Initialize TTS manager in session state
if 'tts_manager' not in st.session_state:
    st.session_state.tts_manager = TTSManager()

def capture_image():
    """Capture an image from the webcam and encode it as Base64."""
    with st.container():
        img_file = st.camera_input("Take a picture", help="Click to take a photo")

    if img_file:
        st.session_state.tts_manager.play_sound("camera.mp3")
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

def main():
    st.markdown("<h1 style='text-align: center;'>Smart Vision 𓆩👁️𓆪</h1>", unsafe_allow_html=True)
    st.markdown("""📸 Take a picture and get an instant audio description!""")

    # Capture image
    base64_image = capture_image()

    # Clear previous description when a new image is captured
    if base64_image and base64_image != st.session_state.last_processed_image:
        # Reset session variables for new description
        st.session_state.last_processed_image = base64_image
        st.session_state.description_visible = False
        st.session_state.last_response = None
        
        prompt = "Describe this image smartly in 4-5 lines to the person who is completely unaware of the surroundings in a descriptive way."

        with st.spinner("Generating description..."):
            response = image_to_text(client, llama_3_2, base64_image, prompt)
            
            if response:
                st.session_state.last_response = response
                st.session_state.description_visible = True
                time.sleep(0.5)  # Small delay before playing audio
                st.session_state.tts_manager.create_audio_element(response, priority=True)

    # Display only the latest description
    if st.session_state.description_visible and st.session_state.last_response:
        st.markdown("### Image Description:", unsafe_allow_html=True)
        st.write(st.session_state.last_response)

    # Buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📸 Regenerate Picture Description", use_container_width=True):
            st.session_state.tts_manager.play_sound("button1.mp3")
            time.sleep(0.5)
            st.session_state.tts_manager.stop_current_audio()
            st.session_state.last_processed_image = None
            st.session_state.needs_audio_playback = True
            st.rerun()
    
    with col2:
        if st.button("🔊 Replay Audio", use_container_width=True):
            if st.session_state.last_response:
                st.session_state.tts_manager.play_sound("button2.mp3")
                time.sleep(0.3)
                st.session_state.tts_manager.create_audio_element(st.session_state.last_response)

if __name__ == "__main__":
    main()
