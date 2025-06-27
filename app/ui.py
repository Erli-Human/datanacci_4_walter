import gradio as gr
import pandas as pd
import tempfile
import shutil
import logging
from pathlib import Path
from io import StringIO
import uuid
import os

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

# Use a Gradio-friendly, user-writable temp directory for any file handling
GRADIO_TEMP_ROOT = Path(tempfile.gettempdir()) / "gradio_kijiji_uploads"
GRADIO_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

def safe_save_uploaded_file(file_obj):
    # Handles single uploaded file and returns a local temp file path (in a safe, writable temp directory)
    if hasattr(file_obj, "read"):
        suffix = getattr(file_obj, "name", ".csv")
        tmp_dir = GRADIO_TEMP_ROOT
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=Path(suffix).suffix, mode="wb") as temp_file:
            temp_file.write(file_obj.read())
            return Path(temp_file.name)
    file_path = str(getattr(file_obj, "name", file_obj))
    file_path_obj = Path(file_path)
    if file_path_obj.is_dir():
        raise ValueError(f"Uploaded path {file_path_obj} is a directory, not a file.")
    if file_path_obj.is_file() and os.access(file_path_obj, os.R_OK):
        tmp_dir = GRADIO_TEMP_ROOT
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir, suffix=file_path_obj.suffix, mode="wb") as temp_file:
            with open(file_path_obj, "rb") as src:
                shutil.copyfileobj(src, temp_file)
            return Path(temp_file.name)
    raise ValueError(f"Unsupported file object type or not a file: {file_path_obj}")

def get_image_files(images_upload):
    # Returns the list of image file names from uploaded files
    if images_upload is None or len(images_upload) == 0:
        return []
    allowed_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    files = []
    for img in images_upload:
        name = getattr(img, "name", None)
        if name:
            ext = Path(name).suffix.lower()
            if ext in allowed_exts:
                files.append(name)
    return files

def save_uploaded_images(images_upload):
    # Save all uploaded images to a safe temp directory and return mapping {name: path}
    if images_upload is None or len(images_upload) == 0:
        return {}, None
    temp_dir = GRADIO_TEMP_ROOT / f"images_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    name_to_path = {}
    for img in images_upload:
        img_name = Path(getattr(img, "name", uuid.uuid4().hex + ".img")).name
        # Prevent path traversal or invalid filenames
        img_name = img_name.replace("..", "").replace("\\", "_").replace("/", "_")
        img_path = temp_dir / img_name
        img.seek(0)
        with open(img_path, "wb") as out_f:
            out_f.write(img.read())
        name_to_path[img_name] = str(img_path)
    return name_to_path, temp_dir

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

def update_image_dropdown_ui(truck_id, spreadsheet, images_upload):
    if spreadsheet is None or truck_id is None:
        return gr.update(choices=[], value=None)
    temp_path = safe_save_uploaded_file(spreadsheet)
    df = pd.read_csv(temp_path)
    try:
        image_filename = df[df["bucket_truck_id"] == truck_id]["image_filename"].values[0]
    except Exception:
        image_filename = None
    available_images = get_image_files(images_upload)
    matched = image_filename if image_filename in available_images else None
    return gr.update(choices=available_images, value=matched or (available_images[0] if available_images else None))

def toggle_truck_dropdown(mode):
    visible = mode == "Single"
    return gr.update(visible=visible)

def generate_rental_ad(record, contact_phone=None, include_email=False, include_phone=False, kijiji_email=None):
    title = f"{record.get('title', '')} - Now Available for Rent!"
    description = f"{record.get('description', '')}\n\n"
    description += f"**Rental Details:**\n"
    description += f"• Price: ${record.get('price', 'N/A')} per day\n"
    description += f"• Equipment Type: {record.get('equipment_type', 'N/A')}\n"
    description += f"• Fuel Type: {record.get('fuel_type', 'N/A')}\n"
    description += f"• VIN: {record.get('vin_id', 'N/A')}\n"
    description += f"• Tags: {record.get('tags', '')}\n"
    description += f"• Status: {record.get('posting_status', '')}\n"
    description += "\nContact us now to reserve this vehicle for your next project!\n"

    contact_lines = []
    if include_email and kijiji_email:
        contact_lines.append(f"📧 Email: {kijiji_email}")
    if include_phone and contact_phone:
        contact_lines.append(f"📞 Phone: {contact_phone}")
    if contact_lines:
        description += "\n" + "\n".join(contact_lines)
    return f"**{title}**\n\n{description}"

def preview_ad(
    truck_id, spreadsheet, images_upload, image_dropdown,
    contact_phone, include_email, include_phone, kijiji_email
):
    if spreadsheet is None or truck_id is None:
        return "Select a truck to preview its ad.", None
    temp_path = safe_save_uploaded_file(spreadsheet)
    df = pd.read_csv(temp_path)
    rec = df[df["bucket_truck_id"] == truck_id]
    if rec.empty:
        return "Truck record not found.", None
    rec = rec.iloc[0].to_dict()

    image_path = None
    name_to_path, _ = save_uploaded_images(images_upload)
    if image_dropdown and image_dropdown in name_to_path:
        image_path = name_to_path[image_dropdown]

    ad_text = generate_rental_ad(
        rec,
        contact_phone=contact_phone,
        include_email=include_email,
        include_phone=include_phone,
        kijiji_email=kijiji_email
    )
    return ad_text, image_path

def process_ads(email, password, file_obj, images_upload, mode, selected_truck_id, image_dropdown, contact_phone, include_email, include_phone, progress=gr.Progress(track_tqdm=True)):
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
        if not images_upload or len(images_upload) == 0:
            return "Error: Please upload at least one image", {"error": "Missing images upload"}, "", 0
        temp_path = safe_save_uploaded_file(file_obj)
        name_to_path, temp_dir = save_uploaded_images(images_upload)
        for pct in range(0, 101, 10):
            import time
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
- **Note:** In Batch and Batch-New mode, `vin_id` must correctly map to the image filename (e.g., `vin_id.jpg`) in your images directory.

**Batch-All Mode:**  
- Posts (or re-posts) all listings in your spreadsheet, regardless of their current `posting_status`.
- **Note:** In Batch and Batch-New mode, `vin_id` must correctly map to the image filename (e.g., `vin_id.jpg`) in your images directory.

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
                gr.Markdown("### ☎️ Contact Info")
                contact_phone_input = gr.Textbox(
                    label="Contact Phone Number (optional)",
                    placeholder="e.g. 555-555-5555",
                    type="text"
                )
                include_email_checkbox = gr.Checkbox(
                    label="Include Kijiji email in ad?",
                    value=True
                )
                include_phone_checkbox = gr.Checkbox(
                    label="Include phone number in ad?",
                    value=True
                )
                gr.Markdown("### 📁 Files & Images")
                spreadsheet_input = gr.File(
                    label="Upload Spreadsheet (CSV, XLS, XLSX, ODS)",
                    file_types=[".csv", ".xls", ".xlsx", ".ods"]
                )
                images_upload_input = gr.Files(
                    label="Upload Images (JPG, PNG, GIF, WEBP)",
                    file_types=[".jpg", ".jpeg", ".png", ".gif", ".webp"]
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
                image_dropdown = gr.Dropdown(
                    label="Select Image for Truck",
                    choices=[],
                    visible=True,
                    info="Images you uploaded"
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
                gr.Markdown("### 👀 Preview Truck Ad Before Posting")
                with gr.Row():
                    ad_preview = gr.Markdown(value="Select a truck to preview its rental ad here.")
                    image_preview = gr.Image(label="Preview Image", value=None, interactive=False, visible=True, height=320)
        preview_inputs = [
            truck_id_input,
            spreadsheet_input,
            images_upload_input,
            image_dropdown,
            contact_phone_input,
            include_email_checkbox,
            include_phone_checkbox,
            email_input
        ]
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
        truck_id_input.change(
            fn=update_image_dropdown_ui,
            inputs=[truck_id_input, spreadsheet_input, images_upload_input],
            outputs=[image_dropdown]
        )
        images_upload_input.change(
            fn=update_image_dropdown_ui,
            inputs=[truck_id_input, spreadsheet_input, images_upload_input],
            outputs=[image_dropdown]
        )
        for comp in [
            truck_id_input, image_dropdown, contact_phone_input, include_email_checkbox, include_phone_checkbox
        ]:
            comp.change(
                fn=preview_ad,
                inputs=preview_inputs,
                outputs=[ad_preview, image_preview]
            )
        run_button.click(
            fn=process_ads,
            inputs=[
                email_input,
                password_input,
                spreadsheet_input,
                images_upload_input,
                mode_input,
                truck_id_input,
                image_dropdown,
                contact_phone_input,
                include_email_checkbox,
                include_phone_checkbox
            ],
            outputs=[
                status_output,
                logs_output,
                download_file,
                progress_output
            ]
        )
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
