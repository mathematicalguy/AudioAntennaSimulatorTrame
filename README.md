# Audio Antenna Simulator

A web-based application that simulates magnetic field vectors based on uploaded audio files.

## Features

- Upload MP3 audio files
- Visualize magnetic field vectors based on audio data
- Interactive 3D visualization with PyVista
- Adjustable antenna parameters

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/AudioAntennaSimulatorTrame.git
   cd AudioAntennaSimulatorTrame
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the application:
   ```bash
   cd antenna-simulation-web/src
   python main.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:8080
   ```

3. Use the interface to:
   - Upload MP3 files
   - Adjust antenna parameters
   - View the simulation

## File Upload

The application accepts MP3 files and processes them to extract frequency information that drives the simulation. Follow these steps:

1. Click on the "Upload MP3 File" button
2. Select an MP3 file from your computer
3. Click "Upload"

The simulation will automatically adjust based on the dominant frequencies in the audio file.

## Troubleshooting

If you encounter issues with file uploads:

- Ensure the file is in MP3 format
- Check terminal output for error messages
- Verify that the `uploads` directory exists and is writable

## Dependencies

- trame
- PyVista
- VTK
- librosa
- NumPy
