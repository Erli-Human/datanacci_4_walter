"""
Datanacci DAO - All rights reserved
HelixEncoder(Kijiji) automation Agent

"""
Gradio UI for the Kijiji automation system.

This module provides a web-based interface with:
- Textboxes for Kijiji email & password
- FileUpload for spreadsheet (or path input)
- Directory input for images (text)
- Radio: Mode (Single / Batch-New / Batch-All)
- If Single → dropdown populated with bucket_truck_id values
- Run button → triggers processing
- gr.Dataframe or gr.JSON live log window
- Progress is shown via a gr.Number field (Gradio 4.x+)
"""

import gradio as gr
import pandas as pd
import threading
import time
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Import the app modules
try:
    from . import data_io, posting, kijiji_bot
except ImportError:
    import data_io
    import posting
    from kijiji_bot import KijijiBot

# Set up logging
logger = logging.getLogger(__name__)

# Global state for tracking processing
processing_state = {
    'is_running': False,
    'progress': 0.0,
    'current_message': 'Ready',
    'logs': []
}

def update_truck_dropdown(file):
    """
    Update the truck dropdown based on the uploaded spreadsheet.
    Returns a list of truck IDs or a placeholder if none.
    """
    if file is None:
        return gr.Dropdown.update(choices=["Upload spreadsheet first"], value=None)
    try:
        # Support all common spreadsheet formats
        filename = file.name if hasattr(file, "name") else str(file)
        ext = Path(filename).suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(filename)
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(filename)
        elif ext == ".ods":
            df = pd.read_excel(filename, engine="odf")
        else:
            return gr.Dropdown.update(choices=["Unsupported spreadsheet format"], value=None)
        if "bucket_truck_id" in df.columns:
            ids = [str(i) for i in df["bucket_truck_id"].dropna().unique()]
            return gr.Dropdown.update(choices=ids, value=ids[0] if ids else None)
        else:
            return gr.Dropdown.update(choices=["No 'bucket_truck_id' column"], value=None)
    except Exception as e:
        return gr.Dropdown.update(choices=[f"Error: {e}"], value=None)

def toggle_truck_dropdown(mode):
    """
    Show truck dropdown only if mode is 'Single', otherwise hide.
    """
    visible = mode == "Single"
    return gr.Dropdown.update(visible=visible)

def get_progress_info() -> Tuple[float, str]:
    """
    Get current progress information for the UI.
    Returns:
        Tuple of (progress_percentage, current_message)
    """
    return processing_state['progress'], processing_state['current_message']

def process_ads(email: str, password: str, file_obj: Optional[str], images_dir: str, 
               mode: str, selected_truck_id: Optional[str], progress=gr.Progress(track_tqdm=True)):
    """
    Main processing function called by the UI.
    Args:
        email: Kijiji email
        password: Kijiji password
        file_obj: Uploaded file object or path
        images_dir: Directory containing images
        mode: Processing mode (Single/Batch-New/Batch-All)
        selected_truck_id: Selected truck ID for single mode
    Returns:
        Tuple of (status_message, logs_dict, download_file_path, progress_percent)
    """
    # Reset processing state
    processing_state['is_running'] = True
    processing_state['progress'] = 0.0
    processing_state['current_message'] = 'Starting...'
    processing_state['logs'] = []

    # Set up logging
    log_handler = logging.StreamHandler()
    logger.addHandler(log_handler)

    try:
        # Validate inputs
        if not email or not password:
            return "Error: Email and password are required", {"error": "Missing credentials"}, "", 0
        
        if not file_obj:
            return "Error: Please upload a spreadsheet", {"error": "Missing spreadsheet"}, "", 0
        
        if not images_dir:
            return "Error: Please specify images directory", {"error": "Missing images directory"}, "", 0
        
        file_path = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)
        # Dummy progress simulation for this example
        for pct in range(0, 101, 10):
            time.sleep(0.1)
            processing_state['progress'] = pct
            processing_state['current_message'] = f"Processing... {pct}%"
            progress(pct / 100.0, desc=processing_state['current_message'])
        
        # Insert your actual processing here.
        # For now, we'll just simulate a successful run.
        status_msg = "✅ Processing completed successfully!"
        logs_dict = {"logs": ["Processing completed successfully!"]}
        download_path = ""  # Implement actual file logic if needed

        return status_msg, logs_dict, download_path, 100

    except Exception as e:
        logger.exception(f"Unexpected error in process_ads: {e}")
        return f"❌ Unexpected error: {str(e)}", {"error": str(e)}, "", processing_state['progress']
    
    finally:
        # Clean up
        processing_state['is_running'] = False
        logger.removeHandler(log_handler)

def create_ui() -> gr.Blocks:
    """
    Create the main Gradio interface.
    Returns:
        Gradio Blocks interface
    """
    with gr.Blocks(title="CaveSheepCollective Kijiji Agent Config", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🚛 CaveSheepCollective Kijiji Agent Config

        Automate posting of bucket truck listings to Kijiji with support for single posting and batch processing.
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🔐 Credentials")
                email_input = gr.Textbox(
                    label="Kijiji Email",
                    placeholder="walter@example.com",
                    type="email"
                )
                password_input = gr.Textbox(
                    label="Kijiji Password",
                    placeholder="Your password",
                    type="password"
                )

                gr.Markdown("### 📁 Files & Directories")
                spreadsheet_input = gr.File(
                    label="Upload Spreadsheet (CSV, XLS, XLSX, ODS)",
                    file_types=[".csv", ".xls", ".xlsx", ".ods"]
                )
                images_dir_input = gr.Textbox(
                    label="Images Directory Path",
                    placeholder="/path/to/images",
                    value="assets/images",
                    info="Supported image types: JPG, PNG, GIF, WEBP"
                )

                gr.Markdown("### ⚙️ Processing Mode")
                mode_input = gr.Radio(
                    choices=["Single", "Batch-New", "Batch-All"],
                    label="Mode",
                    value="Single",
                    info="Single: Post one record | Batch-New: Post pending/failed only | Batch-All: Post everything"
                )

                truck_id_input = gr.Dropdown(
                    label="Select Truck ID",
                    choices=["Upload spreadsheet first"],
                    visible=True,
                    info="Available when Single mode is selected"
                )

                with gr.Row():
                    run_button = gr.Button(
                        "🚀 Run Processing",
                        variant="primary",
                        size="lg"
                    )
                    stop_button = gr.Button(
                        "⏹️ Stop",
                        variant="stop",
                        size="lg",
                        visible=False
                    )

            with gr.Column(scale=2):
                gr.Markdown("### 📊 Progress & Logs")

                status_output = gr.Textbox(
                    label="Status",
                    value="Ready to process",
                    interactive=False
                )

                progress_output = gr.Number(
                    label="Progress (%)",
                    value=0,
                    interactive=False
                )

                logs_output = gr.JSON(
                    label="Live Logs",
                    value={"logs": []}
                )

                gr.Markdown("### 📥 Download Updated Spreadsheet")
                download_file = gr.File(
                    label="Download Updated Spreadsheet",
                    visible=False
                )

        # Event handlers

        # Update truck dropdown when spreadsheet is uploaded
        spreadsheet_input.change(
            fn=update_truck_dropdown,
            inputs=[spreadsheet_input],
            outputs=[truck_id_input]
        )

        # Show/hide truck dropdown based on mode
        mode_input.change(
            fn=toggle_truck_dropdown,
            inputs=[mode_input],
            outputs=[truck_id_input]
        )

        # Main processing function
        run_button.click(
            fn=process_ads,
            inputs=[
                email_input,
                password_input,
                spreadsheet_input,
                images_dir_input,
                mode_input,
                truck_id_input
            ],
            outputs=[
                status_output,
                logs_output,
                download_file,
                progress_output
            ]
        )

    return interface

def launch_ui(server_name: str = "127.0.0.1", server_port: int = 7860, share: bool = False) -> None:
    """
    Launch the Gradio interface.
    Args:
        server_name: Server host
        server_port: Server port
        share: Whether to create public link
    """
    interface = create_ui()
    print(f"🚀 Launching Kijiji Posting Assistant...")
    print(f"📍 URL: http://{server_name}:{server_port}")
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True
    )
