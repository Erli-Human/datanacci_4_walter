"""
Gradio UI for the Datanacci Walter Kijiji automation system.

This module provides a web-based interface with:
- Textboxes for Kijiji email & password
- FileUpload for spreadsheet (or path input)
- Directory input for images (text)
- Radio: Mode (Single / Batch-New / Batch-All)
- If Single → dropdown populated with bucket_truck_id values
- Run button → triggers processing
- gr.Dataframe or gr.JSON live log window
- gr.Progress for batch bar

All callbacks call routines above, return real-time logs & updated sheet for download.
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

def get_progress_info() -> Tuple[float, str]:
    """
    Get current progress information for the UI.
    
    Returns:
        Tuple of (progress_percentage, current_message)
    """
    return processing_state['progress'], processing_state['current_message']

def create_ui() -> gr.Blocks:
    """
    Create the main Gradio interface.
    
    Returns:
        Gradio Blocks interface
    """
    with gr.Blocks(title="Kijiji Posting Assistant", theme=gr.themes.Soft()) as interface:
        gr.Markdown("""
        # 🚛 Kijiji Posting Assistant
        
        Automate posting of bucket truck listings to Kijiji with support for single posting and batch processing.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### 🔐 Credentials")
                email_input = gr.Textbox(
                    label="Kijiji Email",
                    placeholder="your.email@example.com",
                    type="email"
                )
                password_input = gr.Textbox(
                    label="Kijiji Password",
                    placeholder="Your password",
                    type="password"
                )
                
                gr.Markdown("### 📁 Files & Directories")
                spreadsheet_input = gr.File(
                    label="Upload Spreadsheet (.xlsx)",
                    file_types=[".xlsx", ".xls"]
                )
                images_dir_input = gr.Textbox(
                    label="Images Directory Path",
                    placeholder="/path/to/images",
                    value="assets/images"
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


if __name__ == "__main__":
    # Launch the UI
    launch_ui()
