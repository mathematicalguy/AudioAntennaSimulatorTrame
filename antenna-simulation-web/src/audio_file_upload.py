import os
from pathlib import Path
from trame.widgets import vuetify, html
import base64
import shutil
import sys

# Add parent directory to path so we can import audiograph_maker
sys.path.append(str(Path(__file__).parent.parent))
from audiograph_maker import generate_graph_for_audio

class AudioUploaderComponent:
    def __init__(self, server):
        self.server = server
        
        # Create the upload directory if it doesn't exist
        self.upload_dir = Path(__file__).parent.parent.parent / 'uploads'
        try:
            self.upload_dir.mkdir(exist_ok=True, parents=True)
            
            # Test write permissions by creating a test file
            test_file = self.upload_dir / '.test_write'
            test_file.touch()
            test_file.unlink()
            
            print(f"Upload directory ready: {self.upload_dir}")
        except Exception as e:
            print(f"Warning: Could not create or access upload directory: {str(e)}")
            # Fall back to temp directory
            self.upload_dir = Path(os.path.join(os.path.expanduser('~'), 'temp_uploads'))
            self.upload_dir.mkdir(exist_ok=True, parents=True)
            print(f"Using fallback directory: {self.upload_dir}")
        
        # Initialize state
        self.server.state.uploaded_file = None
        self.server.state.upload_status = ""
        self.server.state.should_process = False
        self.server.state.audio_graph = None
        
        # Watch for the trigger variable
        @self.server.state.change("should_process")
        def on_should_process(should_process, **kwargs):
            if should_process:
                # Reset the trigger immediately
                self.server.state.should_process = False
                
                # Process the file upload
                self.process_file_upload()
        
        # Register direct method to handle file uploads
        @self.server.controller.set("process_file")
        def process_file():
            """Process a file upload that's been stored in the window global variable"""
            self.process_file_upload()
    
    def process_file_upload(self):
        """Process a file upload using the temp state variables"""
        print("\n===== PROCESSING AUDIO FILE (SERVER DIRECT) =====")
        filename = self.server.state.temp_filename
        base64_data = self.server.state.temp_base64data
        
        print(f"Received filename: {filename}")
        if base64_data:
            print(f"Received base64 data length: {len(base64_data)}")
        else:
            print("No base64 data received")
            
        if not filename or not base64_data:
            self.server.state.upload_status = "Error: Missing file data"
            return
        
        if not filename.lower().endswith('.mp3'):
            self.server.state.upload_status = "Error: Only MP3 files are allowed"
            return
        
        try:
            # Decode base64 content
            content = base64.b64decode(base64_data.split(',')[1])
            print(f"Successfully decoded base64 content, size: {len(content)} bytes")
            
            # Save file
            file_path = self.upload_dir / filename
            with open(file_path, 'wb') as f:
                f.write(content)
            
            print(f"File saved to {file_path}")
            
            # Update state
            self.server.state.uploaded_file = str(file_path)
            self.server.state.upload_status = f"Successfully uploaded {filename}"
            
            # Generate audio graph after successful upload
            try:
                graph_path = generate_graph_for_audio(file_path)
                if graph_path:
                    self.server.state.audio_graph = str(graph_path)
                    self.server.state.upload_status += f" and created audio graph"
                    print(f"Generated audio graph: {graph_path}")
            except Exception as e:
                print(f"Error generating audio graph: {str(e)}")
                # Don't fail the whole upload if graph generation fails
                
        except Exception as e:
            self.server.state.upload_status = f"Error processing file: {str(e)}"
            print(f"Error: {str(e)}")
    
    def get_upload_widget(self):
        with vuetify.VCard(classes="pa-4") as card:
            html.Div("Audio File Upload", classes="text-h6 mb-4")
            
            # State variables to store file data
            vuetify.VTextField(
                v_model=("temp_filename", ""),
                style="display: none;"
            )
            
            vuetify.VTextField(
                v_model=("temp_base64data", ""),
                style="display: none;"
            )
            
            vuetify.VTextField(
                v_model=("should_process", False),
                style="display: none;"
            )
            
            # Use a standard Vuetify file input
            vuetify.VFileInput(
                v_model=("file_input", None),
                label="Select MP3 File",
                accept=".mp3",
                truncate_length=25,
                show_size=True,
                persistent_hint=True,
                hint="Select an MP3 file to upload",
                classes="mb-4",
            )
            
            # Upload button
            vuetify.VBtn(
                "Upload File",
                color="primary",
                block=True,
                classes="mb-4",
                click="""
                if (!file_input) {
                    // Show an error message if no file is selected
                    upload_status = 'Error: Please select a file first';
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    temp_filename = file_input.name;
                    temp_base64data = e.target.result;
                    should_process = true;
                };
                reader.readAsDataURL(file_input);
                """
            )
            
            # Status display
            vuetify.VAlert(
                "{{ upload_status }}",
                classes="text-body-2",
                v_if="upload_status",
                type=("upload_status.includes('Error') ? 'error' : 'success'"),
                dense=True,
                outlined=True
            )
            
            # Show audio graph if available
            html.Div(
                v_if="audio_graph",
                classes="mt-4 text-center"
            ).add_child(
                html.Img("{{ audio_graph }}", 
                         style="max-width: 100%; height: auto;",
                         v_if="audio_graph")
            )
        
        return card