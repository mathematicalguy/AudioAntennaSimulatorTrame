import os
from pathlib import Path
from trame.widgets import vuetify, html
import base64

class AudioUploaderComponent:
    def __init__(self, server):
        self.server = server
        self.upload_dir = Path(__file__).parent.parent.parent / 'uploads'
        self.upload_dir.mkdir(exist_ok=True)
        
        # Initialize state
        self.server.state.uploaded_file = None
        self.server.state.upload_status = ""
        
        # Setup controllers
        self.setup_controllers()
    
    def setup_controllers(self):
        @self.server.controller.set("handle_file_upload")
        def handle_file_upload(file_content, file_name):
            try:
                if not file_name.lower().endswith('.mp3'):
                    self.server.state.upload_status = "Error: Only MP3 files are allowed"
                    return
                
                # Decode base64 content
                content = base64.b64decode(file_content.split(',')[1])
                
                # Save file
                file_path = self.upload_dir / file_name
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                self.server.state.uploaded_file = str(file_path)
                self.server.state.upload_status = f"Successfully uploaded {file_name}"
                
            except Exception as e:
                self.server.state.upload_status = f"Error uploading file: {str(e)}"
    
    def get_upload_widget(self):
        with vuetify.VCard(classes="pa-4") as card:
            html.Div("Audio File Upload", classes="text-h6 mb-4")
            
            vuetify.VFileInput(
                v_model=("files", None),
                label="Upload MP3 File",
                accept=".mp3",
                show_size=True,
                truncate_length=25,
                append_icon="mdi-upload",
                classes="mb-2",
            )
            
            with vuetify.VRow(classes="mb-2"):
                with vuetify.VCol(cols=12):
                    vuetify.VBtn(
                        "Upload",
                        block=True,
                        color="primary",
                        click="""
                        if (files) {
                            const reader = new FileReader();
                            reader.onload = (e) => {
                                handle_file_upload(e.target.result, files.name);
                            };
                            reader.readAsDataURL(files);
                        }
                        """,
                    )
            
            html.Div("{{ upload_status }}", classes="text-body-2")