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
    'current_message': '',
    'logs': [],
    'results': None
}


class LogHandler(logging.Handler):
    """Custom logging handler to capture logs for UI display."""
    
    def __init__(self):
        super().__init__()
        self.logs = []
    
    def emit(self, record):
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage()
        }
        self.logs.append(log_entry)
        processing_state['logs'] = self.logs[-50:]  # Keep last 50 logs


def load_bucket_truck_ids(file_path: Optional[str]) -> List[str]:
    """
    Load bucket_truck_id values from the uploaded spreadsheet.
    
    Args:
        file_path: Path to the uploaded Excel file
        
    Returns:
        List of bucket_truck_id values
    """
    if not file_path:
        return ["No spreadsheet loaded"]
    
    try:
        df = data_io.load_inventory(file_path)
        truck_ids = df['bucket_truck_id'].astype(str).tolist()
        return truck_ids if truck_ids else ["No truck IDs found"]
    except Exception as e:
        logger.error(f"Error loading truck IDs: {e}")
        return [f"Error: {str(e)}"]


def update_truck_dropdown(file_path: Optional[str]) -> gr.Dropdown:
    """
    Update the truck ID dropdown when a new spreadsheet is uploaded.
    """
    truck_ids = load_bucket_truck_ids(file_path)
    return gr.Dropdown.update(choices=truck_ids, value=truck_ids[0] if truck_ids else None)


def toggle_truck_dropdown(mode: str) -> gr.Dropdown:
    """
    Show/hide the truck ID dropdown based on selected mode.
    """
    if mode == "Single":
        return gr.Dropdown.update(visible=True)
    else:
        return gr.Dropdown.update(visible=False)


def progress_callback(percentage: float, message: str) -> None:
    """
    Progress callback function for batch processing.
    """
    processing_state['progress'] = percentage
    processing_state['current_message'] = message
    logger.info(f"Progress: {percentage:.1f}% - {message}")


def post_single_record(email: str, password: str, file_path: str, images_dir: str, 
                      selected_truck_id: str) -> Dict[str, Any]:
    """
    Post a single record based on selected truck ID.
    
    Args:
        email: Kijiji email
        password: Kijiji password
        file_path: Path to spreadsheet
        images_dir: Directory containing images
        selected_truck_id: Selected bucket_truck_id to post
        
    Returns:
        Dict with processing results
    """
    try:
        # Load data
        df = data_io.load_inventory(file_path)
        
        # Find the record with matching truck ID
        record_row = df[df['bucket_truck_id'] == selected_truck_id]
        if record_row.empty:
            return {
                'success': False,
                'message': f'No record found with truck ID: {selected_truck_id}',
                'logs': processing_state['logs']
            }
        
        # Get the record data
        record_index = record_row.index[0]
        record = data_io.get_record(record_row.iloc[0])
        
        # Initialize bot
        bot = KijijiBot(email, password, headless=True)
        
        # Login
        login_result = bot.login()
        if not login_result['success']:
            bot.close()
            return {
                'success': False,
                'message': f'Login failed: {login_result["message"]}',
                'logs': processing_state['logs']
            }
        
        # Post single record
        result = posting.post_single_with_df_update(df, record_index, bot, Path(images_dir))
        
        # Close bot
        bot.close()
        
        # Save updated spreadsheet
        output_path = file_path.replace('.xlsx', '_updated.xlsx')
        data_io.save_inventory(df, output_path)
        
        return {
            'success': result['success'],
            'message': result['message'],
            'logs': processing_state['logs'],
            'updated_file': output_path
        }
        
    except Exception as e:
        logger.exception(f"Error in single record posting: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'logs': processing_state['logs']
        }


def run_batch_processing(email: str, password: str, file_path: str, images_dir: str, 
                        mode: str) -> Dict[str, Any]:
    """
    Run batch processing for multiple records.
    
    Args:
        email: Kijiji email
        password: Kijiji password
        file_path: Path to spreadsheet
        images_dir: Directory containing images
        mode: 'Batch-New' or 'Batch-All'
        
    Returns:
        Dict with processing results
    """
    try:
        # Load data
        df = data_io.load_inventory(file_path)
        
        # Initialize bot
        bot = KijijiBot(email, password, headless=True)
        
        # Login
        login_result = bot.login()
        if not login_result['success']:
            bot.close()
            return {
                'success': False,
                'message': f'Login failed: {login_result["message"]}',
                'logs': processing_state['logs']
            }
        
        # Determine batch mode
        batch_mode = 'new' if mode == 'Batch-New' else 'all'
        
        # Run batch processing
        result = posting.run_batch(
            df=df,
            mode=batch_mode,
            bot=bot,
            images_dir=Path(images_dir),
            progress_cb=progress_callback,
            file_path=file_path
        )
        
        # Close bot
        bot.close()
        
        # Save final updated spreadsheet
        output_path = file_path.replace('.xlsx', '_batch_updated.xlsx')
        data_io.save_inventory(df, output_path)
        
        return {
            'success': result['success'],
            'message': result['message'],
            'total_records': result['total_records'],
            'successful_posts': result['successful_posts'],
            'failed_posts': result['failed_posts'],
            'logs': processing_state['logs'],
            'updated_file': output_path
        }
        
    except Exception as e:
        logger.exception(f"Error in batch processing: {e}")
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'logs': processing_state['logs']
        }


def process_ads(email: str, password: str, file_obj: Optional[str], images_dir: str, 
               mode: str, selected_truck_id: Optional[str]) -> Tuple[str, Dict, str]:
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
        Tuple of (status_message, logs_dict, download_file_path)
    """
    # Reset processing state
    processing_state['is_running'] = True
    processing_state['progress'] = 0.0
    processing_state['current_message'] = 'Starting...'
    processing_state['logs'] = []
    
    # Set up logging
    log_handler = LogHandler()
    logger.addHandler(log_handler)
    
    try:
        # Validate inputs
        if not email or not password:
            return "Error: Email and password are required", {"error": "Missing credentials"}, ""
        
        if not file_obj:
            return "Error: Please upload a spreadsheet", {"error": "Missing spreadsheet"}, ""
        
        if not images_dir:
            return "Error: Please specify images directory", {"error": "Missing images directory"}, ""
        
        file_path = file_obj.name if hasattr(file_obj, 'name') else str(file_obj)
        
        # Process based on mode
        if mode == "Single":
            if not selected_truck_id:
                return "Error: Please select a truck ID", {"error": "Missing truck ID"}, ""
            
            result = post_single_record(email, password, file_path, images_dir, selected_truck_id)
        else:
            result = run_batch_processing(email, password, file_path, images_dir, mode)
        
        # Prepare response
        if result['success']:
            status_msg = f"✅ {result['message']}"
            if 'updated_file' in result:
                download_path = result['updated_file']
            else:
                download_path = ""
        else:
            status_msg = f"❌ {result['message']}"
            download_path = ""
        
        logs_dict = {"logs": result.get('logs', [])}
        
        return status_msg, logs_dict, download_path
        
    except Exception as e:
        logger.exception(f"Unexpected error in process_ads: {e}")
        return f"❌ Unexpected error: {str(e)}", {"error": str(e)}, ""
    
    finally:
        # Clean up
        processing_state['is_running'] = False
        logger.removeHandler(log_handler)


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
                
                progress_bar = gr.Progress(label="Processing Progress")
                
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
                download_file
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

 
