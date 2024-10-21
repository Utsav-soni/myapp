import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
import base64
import json
from PIL import Image
import pyttsx3
import io
import threading
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

class TTSManager:
    def __init__(self):
        self.engine = None
        self.is_speaking = False
        self._lock = threading.Lock()

    def initialize_engine(self):
        """Initialize or reinitialize the TTS engine."""
        try:
            if self.engine is not None:
                self.engine.stop()
                self.engine = None
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
        except Exception as e:
            st.error(f"Failed to initialize TTS engine: {str(e)}")
            self.engine = None

    def speak(self, text):
        """Speak the given text in a thread-safe manner."""
        if self.is_speaking:
            return

        def speak_thread():
            with self._lock:
                try:
                    self.is_speaking = True
                    self.initialize_engine()
                    if self.engine is not None:
                        self.engine.say(text)
                        self.engine.runAndWait()
                except Exception as e:
                    st.error(f"TTS Error: {str(e)}")
                finally:
                    self.is_speaking = False
                    if self.engine is not None:
                        self.engine.stop()
                        self.engine = None

    def play_audio(self, text):
        """Play audio using JavaScript on mobile."""
        # Generate audio with pyttsx3 and save it to a WAV file
        audio_file = "output.wav"
        self.initialize_engine()
        if self.engine is not None:
            self.engine.save_to_file(text, audio_file)
            self.engine.runAndWait()

        # Read the WAV file and convert to base64 for browser playback
        with open(audio_file, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode()

        # Create an audio element in HTML
        st.markdown(f"<audio controls autoplay><source src='data:audio/wav;base64,{audio_base64}' type='audio/wav'></audio>", unsafe_allow_html=True)

# Initialize TTS manager in session state
if 'tts_manager' not in st.session_state:
    st.session_state.tts_manager = TTSManager()

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

def main():
    st.title("Smart Image Describer")
    
    # Add a brief introduction
    st.markdown("""
    📸 Take a picture and get an instant audio description!
    """)

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
                
                # Add audio playback notification
                st.info("🔊 Playing audio description... Please ensure your volume is turned on.")
                
                # Play audio description using the TTS manager
                st.session_state.tts_manager.play_audio(response)

    # Retry option
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📸 Take Another Picture", use_container_width=True):
            st.session_state.last_processed_image = None
            st.rerun()
    with col2:
        if st.button("🔊 Replay Audio", use_container_width=True):
            if hasattr(st.session_state, 'last_response'):
                st.session_state.tts_manager.speak(st.session_state.last_response)

if __name__ == "__main__":
    main()


# import streamlit as st
# from groq import Groq
# import os
# from dotenv import load_dotenv
# import base64
# import json
# from PIL import Image
# import pyttsx3
# import io
# import threading
# import time

# # Load environment variables from .env file
# load_dotenv()

# # Set up the API key for Groq
# api_key = os.getenv("GROQ_API_KEY")
# if not api_key:
#     raise ValueError("API key not found. Please set GROQ_API_KEY environment variable.")

# # Initialize the Groq client
# client = Groq(api_key=api_key)
# llama_3_2 = 'llama-3.2-90b-vision-preview'

# # Inject custom JavaScript for requesting camera permissions
# st.markdown("""
#     <script>
#         function requestCameraPermission() {
#             navigator.mediaDevices.getUserMedia({ video: true })
#                 .then(function(stream) {
#                     console.log('Camera access granted');
#                 })
#                 .catch(function(error) {
#                     console.error('Camera access denied', error);
#                 });
#         }
#         requestCameraPermission();
#     </script>
#     """, unsafe_allow_html=True)

# # Add custom CSS for mobile optimization
# st.markdown("""
#     <style>
#         .stButton>button {
#             width: 100%;
#             margin-top: 10px;
#         }
#         .camera-permission-info {
#             padding: 10px;
#             background-color: #f0f2f6;
#             border-radius: 5px;
#             margin: 10px 0;
#         }
#         @media (max-width: 768px) 
#             .stCamera {
#                 width: 100% !important;
#             }
#             .stCamera>div {
#                 min-height: 300px;
#             }
#         }
#     </style>
#     """, unsafe_allow_html=True)

# class TTSManager:
#     def __init__(self):
#         self.engine = None
#         self.is_speaking = False
#         self._lock = threading.Lock()

#     def initialize_engine(self):
#         """Initialize or reinitialize the TTS engine."""
#         try:
#             if self.engine is not None:
#                 self.engine.stop()
#                 self.engine = None
#             self.engine = pyttsx3.init()
#             self.engine.setProperty('rate', 150)
#             self.engine.setProperty('volume', 1.0)
#         except Exception as e:
#             st.error(f"Failed to initialize TTS engine: {str(e)}")
#             self.engine = None

#     def speak(self, text):
#         """Speak the given text in a thread-safe manner."""
#         if self.is_speaking:
#             return

#         def speak_thread():
#             with self._lock:
#                 try:
#                     self.is_speaking = True
#                     self.initialize_engine()
#                     if self.engine is not None:
#                         self.engine.say(text)
#                         self.engine.runAndWait()
#                 except Exception as e:
#                     st.error(f"TTS Error: {str(e)}")
#                 finally:
#                     self.is_speaking = False
#                     if self.engine is not None:
#                         self.engine.stop()
#                         self.engine = None

#         thread = threading.Thread(target=speak_thread)
#         thread.daemon = True
#         thread.start()

# # Initialize TTS manager in session state
# if 'tts_manager' not in st.session_state:
#     st.session_state.tts_manager = TTSManager()

# def show_permission_instructions():
#     """Show instructions for enabling permissions on mobile devices."""
#     st.markdown("""
#     <div class="camera-permission-info">
#         <h4>📱 Mobile Device Instructions:</h4>
#         <p>This app needs camera and audio permissions to work:</p>
#         <ol>
#             <li>When prompted, tap "Allow" for camera access</li>
#             <li>Allow audio permissions when prompted</li>
#             <li>If permissions are blocked, you can enable them in your browser settings:
#                 <ul>
#                     <li>Tap the lock icon (🔒) in your address bar</li>
#                     <li>Enable camera and audio permissions</li>
#                     <li>Refresh the page</li>
#                 </ul>
#             </li>
#         </ol>
#     </div>
#     """, unsafe_allow_html=True)

# def capture_image():
#     """Capture an image from the webcam and encode it as Base64."""
#     show_permission_instructions()
    
#     img_file = st.camera_input("Take a picture", help="Click to take a photo")
#     if img_file:
#         try:
#             img = Image.open(img_file)
#             img_bytes = io.BytesIO()
#             img.save(img_bytes, format='PNG')
#             img_bytes = img_bytes.getvalue()
#             base64_image = base64.b64encode(img_bytes).decode('utf-8')
#             save_base64_image(base64_image)
#             return base64_image
#         except Exception as e:
#             st.error(f"Error capturing image: {str(e)}")
#             return None
#     return None

# def save_base64_image(base64_image):
#     """Save the Base64 image string to a text file."""
#     try:
#         json_data = json.dumps({"image": base64_image})
#         filename = 'output.txt'
        
#         with open(filename, 'w') as file:
#             json.dump(json_data, file, indent=4)
#     except Exception as e:
#         st.error(f"Error saving image data: {str(e)}")

# def image_to_text(client, model, base64_image, prompt):
#     """Convert an image to text using the Groq client."""
#     try:
#         chat_completion = client.chat.completions.create(
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {"type": "text", "text": prompt},
#                         {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]
#                 }
#             ],
#             model=model
#         )
#         return chat_completion.choices[0].message.content
#     except Exception as e:
#         st.error(f"Error generating description: {str(e)}")
#         return None

# def main():
#     st.title("Smart Image Describer")
    
#     # Add a brief introduction
#     st.markdown("""
#     📸 Take a picture and get an instant audio description!
#     """)

#     # Initialize session state
#     if 'last_processed_image' not in st.session_state:
#         st.session_state.last_processed_image = None
    
#     # Capture image
#     base64_image = capture_image()

#     # Only process if we have a new image
#     if base64_image and base64_image != st.session_state.last_processed_image:
#         st.session_state.last_processed_image = base64_image
        
#         prompt = "Describe this image smartly in 4-5 lines to the person who is completely unaware of the surroundings in a descriptive way."
        
#         with st.spinner("Generating description..."):
#             response = image_to_text(client, llama_3_2, base64_image, prompt)
            
#             if response:
#                 st.markdown("### Image Description:")
#                 st.write(response)
                
#                 # Add audio playback notification
#                 st.info("🔊 Playing audio description... Please ensure your volume is turned on.")
                
#                 time.sleep(0.5)
#                 st.session_state.tts_manager.speak(response)

#     # Retry option with better mobile styling
#     col1, col2 = st.columns([1, 1])
#     with col1:
#         if st.button("📸 Take Another Picture", use_container_width=True):
#             st.session_state.last_processed_image = None
#             st.rerun()
#     with col2:
#         if st.button("🔊 Replay Audio", use_container_width=True):
#             if hasattr(st.session_state, 'last_response'):
#                 st.session_state.tts_manager.speak(st.session_state.last_response)

# if __name__ == "__main__":
#     main()





#============================ ENHANCED BY GPT WORKING SAME AS RAW ===============================

# from groq import Groq  # Importing the Groq class to interact with the LLaMA model
# import os  # Importing os to work with environment variables
# from dotenv import load_dotenv  # Importing load_dotenv to load environment variables from a .env file
# import cv2
# import tkinter as tk
# from tkinter import messagebox
# from PIL import Image as PILImage, ImageTk
# import base64
# import json
# import pyttsx3

# # Load environment variables from .env file
# load_dotenv()  

# # Set up the API key for Groq (LLaMA model)
# api_key = os.getenv("GROQ_API_KEY")
# if not api_key:  
#     raise ValueError("API key not found. Please set GROQ_API_KEY environment variable.")

# # Initialize the Groq client for LLaMA Vision
# client = Groq(api_key=api_key)
# llama_3_2 = 'llama-3.2-11b-vision-preview'  

# # Initialize the webcam
# cap = cv2.VideoCapture(0)

# # Initialize the text-to-speech engine
# engine = pyttsx3.init()

# # Declare base64_image as a global variable
# base64_image = ""

# def capture_image():
#     """Capture an image from the webcam and encode it as Base64."""
#     global base64_image  # Declare base64_image as global
#     ret, frame = cap.read()
#     if ret:
#         _, buffer = cv2.imencode('.png', frame)
#         img_bytes = buffer.tobytes()
#         base64_image = base64.b64encode(img_bytes).decode('utf-8')

#         messagebox.showinfo("Success", "Image captured and encoded in Base64.")
#         save_base64_image(base64_image)
#     else:
#         messagebox.showerror("Error", "Could not capture image.")

# def save_base64_image(base64_image):
#     """Save the Base64 image string to a text file."""
#     json_data = json.dumps({"image": base64_image})
#     filename = 'output.txt'
    
#     with open(filename, 'w') as file:
#         json.dump(json_data, file, indent=4)

#     print(f"Data written to {filename}")

# def update_frame():
#     """Update the frame shown in the Tkinter window."""
#     ret, frame = cap.read()
#     if ret:
#         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         img = PILImage.fromarray(frame)
#         imgtk = ImageTk.PhotoImage(image=img)
#         video_label.imgtk = imgtk
#         video_label.configure(image=imgtk)

#     video_label.after(10, update_frame)  # Schedule the next frame update

# def image_to_text(client, model, base64_image, prompt):
#     """Convert an image to text using the Groq client."""
#     chat_completion = client.chat.completions.create(
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": prompt},
#                     {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
#                 ],
#             }
#         ],
#         model=model
#     )
#     return chat_completion.choices[0].message.content

# def main():
#     """Main function to set up the GUI and process the image."""
#     global base64_image  # Declare base64_image as global

#     # Create the main window
#     root = tk.Tk()
#     root.title("Webcam Image Capture")

#     # Create a label to show the webcam preview
#     global video_label
#     video_label = tk.Label(root)
#     video_label.pack()

#     # Create a button to capture the image
#     capture_button = tk.Button(root, text="Capture Image", command=capture_image)
#     capture_button.pack(pady=20)

#     # Create a button to exit the application
#     exit_button = tk.Button(root, text="Exit", command=root.quit)
#     exit_button.pack(pady=20)

#     # Start updating the frames
#     update_frame()

#     # Start the GUI main loop
#     root.mainloop()

#     # Release the webcam when done
#     cap.release()

#     # Define prompt and get response
#     if base64_image:  # Check if the image was captured successfully
#         prompt = "Describe this image smartly in 4-5 lines to the person who is completely unaware of the surroundings."
#         response = image_to_text(client, llama_3_2, base64_image, prompt)
#         print(response)

#         # Convert the text to speech
#         engine.say(response)
#         engine.runAndWait()
#     else:
#         print("No image captured. Please try again.")

# if __name__ == "__main__":
#     main()





#===================== RAW VERSION =======================================================================


# from groq import Groq  # Importing the Groq class from the groq library to interact with the LLaMA model.
# import os  # Importing the os module to work with environment variables.
# from IPython.display import Image  # Importing Image to display images in Jupyter notebooks.
# from dotenv import load_dotenv  # Importing load_dotenv to load environment variables from a .env file.
# import requests
# from PIL import Image
# from io import BytesIO

# #======================
# import cv2
# import tkinter as tk
# from tkinter import messagebox
# from PIL import Image, ImageTk
# import base64
# import json
# import io
# #==================

# import pyttsx3


# engine = pyttsx3.init()











# # Load environment variables from .env file
# load_dotenv()  # This line loads environment variables defined in a .env file into the program.

# # Set up the API key for Groq (LLaMA model)
# api_key = os.getenv("GROQ_API_KEY")  # Retrieving the Groq API key from the environment variables.

# # Ensure the API key is retrieved
# if not api_key:  # Check if the API key was not found.
#     raise ValueError("API key not found. Please set GROQ_API_KEY environment variable.")  # Raise an error if the key is missing.

# # Initialize the Groq client for LLaMA Vision
# client = Groq(api_key=api_key)  # Creating a Groq client instance with the retrieved API key.

# llama_3_2 = 'llama-3.2-11b-vision-preview'  # Defining the model name for the LLaMA Vision preview.


# # Initialize the webcam
# cap = cv2.VideoCapture(0)

# # Variable to hold the Base64 encoded image
# base64_image = ""

# def capture_image():
#     global base64_image
#     ret, frame = cap.read()
#     if ret:
#         # Convert the image to a bytes buffer
#         _, buffer = cv2.imencode('.png', frame)
#         img_bytes = buffer.tobytes()

#         # Encode the bytes in Base64
#         base64_image = base64.b64encode(img_bytes).decode('utf-8')
        
#         # Show success message and optionally print the Base64 string
#         messagebox.showinfo("Success", "Image captured and encoded in Base64.")
        
#         # For demonstration, you can also save the Base64 string in a JSON object
#         json_data = json.dumps({"image": base64_image})
#         filename = 'output.txt'

#         # Write json_data to a text file
#         with open(filename, 'w') as file:
#             json.dump(json_data, file, indent=4)

#         print(f"Data written to {filename}")
#     else:
#         messagebox.showerror("Error", "Could not capture image.")

# def update_frame():
#     ret, frame = cap.read()
#     if ret:
#         # Convert the frame from BGR to RGB
#         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#         # Convert the frame to a PhotoImage
#         img = Image.fromarray(frame)
#         imgtk = ImageTk.PhotoImage(image=img)
        
#         # Update the label with the new image
#         video_label.imgtk = imgtk
#         video_label.configure(image=imgtk)

#     video_label.after(10, update_frame)  # Schedule the next frame update

# # Create the main window
# root = tk.Tk()
# root.title("Webcam Image Capture")

# # Create a label to show the webcam preview
# video_label = tk.Label(root)
# video_label.pack()

# # Create a button to capture the image
# capture_button = tk.Button(root, text="Capture Image", command=capture_image)
# capture_button.pack(pady=20)

# # Create a button to exit the application
# exit_button = tk.Button(root, text="Exit", command=root.quit)
# exit_button.pack(pady=20)

# # Start updating the frames
# update_frame()

# # Start the GUI main loop
# root.mainloop()

# # Release the webcam when done
# cap.release()




















# # # Use your direct URL
# # image_url = "https://img.freepik.com/premium-photo/cute-furry-animal-ai-generated_970779-17.jpg"
# # response = requests.get(image_url)
# # img = Image.open(BytesIO(response.content))
# # img.show()

# # Define image to text function
# def image_to_text(client, model, base64_image, prompt):  # Accepting image_url instead of base64_image
#     chat_completion = client.chat.completions.create(
#         messages=[
#             {
#                 "role": "user",  # Defining the role of the message sender.
#                 "content": [
#                     {"type": "text", "text": prompt},  # Adding the prompt as text.
#                     {
#                         "type": "image_url",  # Adding the image in URL format.
#                         "image_url": {
                            
#                             "url": f"data:image/png;base64,{base64_image}",
#                             # "url": image_url,  # Directly using the provided image URL
#                         },
#                     },
#                 ],
#             }
#         ],
#         model=model  # Specifying the model to be used for the request.
#     )

#     return chat_completion.choices[0].message.content  # Returning the text response from the model.

# prompt = "Describe this image smarly in 4-5 lines to the person who is completely unaware about surrounding."  # Defining the prompt for the model.
# response = image_to_text(client, llama_3_2, base64_image, prompt)  # Pass the URL instead of base64 image
# print(response)


# # Convert the text to speech
# engine.say(response)

# # Wait for the speech to finish
# engine.runAndWait()