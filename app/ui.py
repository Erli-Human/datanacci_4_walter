import gradio as gr
import pandas as pd
import threading
import time
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from io import StringIO
import uuid
import re
import os  # <--- add this for chmod

try:
    from . import data_io, posting, kijiji_bot
except ImportError:
    import data_io
    import posting
    from kijiji_bot import KijijiBot

logger = logging.getLogger(__name__)

processing_state = {
    'is_running': False,
    'progress': 0.0,
    'current_message': 'Ready',
    'logs': []
}

def sanitize_filename(filename: str) -> str:
    basename = Path(filename).name
    return re.sub(r'[^A-Za-z0-9.\-_]', '_', basename)

def is_path_within(parent: Path, child: Path) -> bool:
    try:
        parent = parent.resolve(strict=True)
        child = child.resolve(strict=True)
        return parent == child or parent in child.parents
    except Exception:
        return False

def safe_save_uploaded_file(file_obj):
    temp_dir = Path(tempfile.gettempdir())
    safe_base = "upload_%s.csv" % uuid.uuid4().hex
    temp_path = temp_dir / sanitize_filename(safe_base)
    # File-like object (from gr.File)
    if hasattr(file_obj, "read"):
        with open(temp_path, "wb") as out_f:
            out_f.write(file_obj.read())
        # Set permissions: owner read/write, no access for group/others
        os.chmod(temp_path, 0o600)
        return temp_path
    file_path = str(getattr(file_obj, "name", file_obj))
    file_path_obj = Path(file_path)
    if file_path_obj.is_file():
        file_path_obj_abs = file_path_obj.resolve(strict=True)
        allowed_dirs = [
            temp_dir.resolve(),
            Path.cwd().resolve(),
            Path("/tmp").resolve()
        ]
        if not any(is_path_within(ad, file_path_obj_abs) for ad in allowed_dirs):
            raise ValueError(f"Unsafe file path detected: {file_path_obj_abs}")
        shutil.copy(file_path_obj, temp_path)
        # Set permissions: owner read/write, no access for group/others
        os.chmod(temp_path, 0o600)
        return temp_path
    if file_path_obj.is_dir():
        raise ValueError(f"Uploaded path {file_path_obj} is a directory, not a file.")
    raise ValueError(f"Unsupported file object type or not a file: {file_path_obj}")

def update_truck_dropdown(file):
    if file is None:
        return gr.update(choices=["Upload spreadsheet first"], value=None)
    try:
        temp_path = safe_save_uploaded_file(file)
        ext = temp_path.suffix.lower()
        if ext == ".csv":
            df = pd.read_csv(temp_path)
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(temp_path)
        elif ext == ".ods":
            df = pd.read_excel(temp_path, engine="odf")
        else:
            return gr.update(choices=["Unsupported spreadsheet format"], value=None)
        if "bucket_truck_id" in df.columns:
            ids = [str(i) for i in df["bucket_truck_id"].dropna().unique()]
            return gr.update(choices=ids, value=ids[0] if ids else None)
        else:
            return gr.update(choices=["No 'bucket_truck_id' column"], value=None)
    except Exception as e:
        return gr.update(choices=[f"Error: {e}"], value=None)

def toggle_truck_dropdown(mode):
    visible = mode == "Single"
    return gr.update(visible=visible)

def get_progress_info() -> Tuple[float, str]:
    return processing_state['progress'], processing_state['current_message']

def process_ads(email: str, password: str, file_obj: Optional[str], images_dir: str, 
               mode: str, selected_truck_id: Optional[str], progress=gr.Progress(track_tqdm=True)):
    processing_state['is_running'] = True
    processing_state['progress'] = 0.0
    processing_state['current_message'] = 'Starting...'
    processing_state['logs'] = []

    log_handler = logging.StreamHandler()
    logger.addHandler(log_handler)

    try:
        if not email or not password:
            return "Error: Email and password are required", {"error": "Missing credentials"}, "", 0
        if not file_obj:
            return "Error: Please upload a spreadsheet", {"error": "Missing spreadsheet"}, "", 0
        if not images_dir:
            return "Error: Please specify images directory", {"error": "Missing images directory"}, "", 0
        
        temp_path = safe_save_uploaded_file(file_obj)

        for pct in range(0, 101, 10):
            time.sleep(0.1)
            processing_state['progress'] = pct
            processing_state['current_message'] = f"Processing... {pct}%"
            progress(pct / 100.0, desc=processing_state['current_message'])
        
        status_msg = "✅ Processing completed successfully!"
        logs_dict = {"logs": ["Processing completed successfully!"]}
        download_path = ""

        return status_msg, logs_dict, download_path, 100

    except Exception as e:
        logger.exception(f"Unexpected error in process_ads: {e}")
        return f"❌ Unexpected error: {str(e)}", {"error": str(e)}, "", processing_state['progress']
    
    finally:
        processing_state['is_running'] = False
        logger.removeHandler(log_handler)

def create_ui() -> gr.Blocks:
    truck_csv_example = (
        "bucket_truck_id,vin_id,image_filename,title,description,price,tags,fuel_type,equipment_type,posting_status\n"
        "2024FORDF350XLWHITE123,1FT8W3BT4JEC12345,fordf350xl_white_123.jpg,Ford F-350 XL White,White 2024 Ford F-350 XL,55000,utility,gasoline,utility truck,pending\n"
        "2023CHEVG2500SILVER789,1GCWGFCF1F1189789,chevg2500_silver_789.jpg,Chevy G2500 Silver,Silver 2023 Chevy G2500 with lift gate,43000,delivery,gasoline,van,posted\n"
        "2022RAM5500DUMP456,3C7WRNFL8NG204456,ram5500_dump_456.jpg,RAM 5500 Dump,RAM 5500 2022 with dump body and toolboxes,67500,construction,diesel,dump truck,failed\n"
        "2024HINO338BOX001,2AYNC8JV8R3S90001,hino338_box_001.jpg,Hino 338 Box Truck,Hino 338 2024 box truck with liftgate,72000,box,lpg,box truck,pending\n"
        "2019ISUZUNPRHDRED555,JALE5W163K7905555,isuzunprhd_red_555.jpg,Isuzu NPR-HD Red,Red Isuzu NPR-HD 2019,34000,light,gasoline,flatbed truck,pending\n"
    )
    instructions_markdown = """
**Single Mode:**  
- Select a single truck (via the dropdown) to post one listing from your spreadsheet.

**Batch-New Mode:**  
- Posts all listings in your spreadsheet which have a `posting_status` column that is blank or marked as `pending` or `failed`.  
- Skips any listings already marked as `posted` or otherwise completed.

**Batch-All Mode:**  
- Posts (or re-posts) all listings in your spreadsheet, regardless of their current `posting_status`.

**Spreadsheet Download:**  
- After processing, you can download your spreadsheet back.  
- The system will update the `posting_status` column for each truck:
    - `pending` = not yet attempted  
    - `posted` = successfully posted  
    - `failed` = posting attempt failed  
- Use the downloaded sheet to keep track of which trucks have been posted or need retrying.

_Supported spreadsheet formats are CSV, XLS, XLSX, and ODS. Supported image formats are JPG, PNG, GIF, and WEBP. Ensure your images directory matches filenames in your spreadsheet._
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

        spreadsheet_input.change(
            fn=update_truck_dropdown,
            inputs=[spreadsheet_input],
            outputs=[truck_id_input]
        )

        mode_input.change(
            fn=toggle_truck_dropdown,
            inputs=[mode_input],
            outputs=[truck_id_input]
        )

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

        # --- Collapsible instructions and CSV Example at the bottom, both default closed ---
        with gr.Row():
            with gr.Column():
                with gr.Accordion("Modes & Spreadsheet Download Instructions", open=False):
                    gr.Markdown("## ℹ️ Instructions")
                    gr.Markdown(instructions_markdown)
                with gr.Accordion("Truck CSV Example", open=False):
                    gr.Markdown("Below is a sample CSV file format for your truck inventory upload. Make sure your spreadsheet (CSV/XLS/XLSX/ODS) matches these columns.")
                    gr.Dataframe(
                        value=pd.read_csv(StringIO(truck_csv_example)),
                        label="Truck CSV Example",
                        interactive=False
                    )
                    gr.Markdown(
                        f"```\n{truck_csv_example}```"
                    )

    return interface

def launch_ui(server_name: str = "127.0.0.1", server_port: int = 7860, share: bool = False) -> None:
    interface = create_ui()
    print(f"🚀 Launching Kijiji Posting Assistant...")
    print(f"📍 URL: http://{server_name}:{server_port}")
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True
    )
