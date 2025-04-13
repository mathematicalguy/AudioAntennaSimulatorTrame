from pathlib import Path
from trame.app import get_server
from trame.widgets import vuetify3, html
import base64

def decode_base64_data(data_url):
    if "," in data_url:
        _, b64_data = data_url.split(",", 1)
        return base64.b64decode(b64_data)
    return base64.b64decode(data_url)

class AudioUploaderComponent:
    def __init__(self, server):
        self.server = server
        self.state = server.state
        self.ctrl = server.controller

        # Initialize state variables
        self.state.uploadedFile = None
        self.state.is_uploading = False
        self.state.message = ""
        self.state.show_message = False
        self.state.message_color = "success"

        # Create uploads directory
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)

        self.setup_controllers()

    def setup_controllers(self):
        @self.ctrl.add("uploadFile")
        async def upload_file():
            self.state.is_uploading = True
            try:
                file_data = self.state.uploadedFile
                if not file_data:
                    self.state.message = "No file selected"
                    self.state.message_color = "error"
                    return

                filename = file_data.get("name", "")
                content = file_data.get("content", "")

                if not filename.lower().endswith(".mp3"):
                    self.state.message = "Only .mp3 files are allowed"
                    self.state.message_color = "error"
                    return

                filepath = self.upload_dir / filename
                with open(filepath, "wb") as f:
                    f.write(decode_base64_data(content))

                self.state.message = f"Uploaded '{filename}'"
                self.state.message_color = "success"
            except Exception as e:
                self.state.message = f"Upload failed: {e}"
                self.state.message_color = "error"
            finally:
                self.state.uploadedFile = None
                self.state.show_message = True
                self.state.is_uploading = False

    def get_upload_widget(self):
        return html.Div(
            style="position: fixed; bottom: 20px; right: 20px; z-index: 100;",
            children=[
                vuetify3.VCard(
                    elevation=4,
                    width=300,
                    children=[
                        vuetify3.VFileInput(
                            v_model=("uploadedFile", None),
                            label="Select MP3 File",
                            accept=".mp3",
                            show_size=True,
                            density="compact",
                        ),
                        vuetify3.VBtn(
                            "Upload",
                            color="primary",
                            class_="ma-2",
                            on_click="uploadFile",
                            loading=("is_uploading", False),
                            disabled=("is_uploading", False),
                        ),
                    ]
                ),
                vuetify3.VSnackbar(
                    v_model=("show_message", False),
                    text=("message", ""),
                    timeout=3000,
                    color=("message_color", "success"),
                    location="top",
                ),
            ]
        )

if __name__ == "__main__":
    server = get_server(client_type="vue3", port=8080)
    uploader = AudioUploaderComponent(server)
    server.ui.add(uploader.get_upload_widget())
    server.start()
