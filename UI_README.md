# 🚛 Kijiji Posting Assistant - Gradio UI

A web-based interface for automated posting of bucket truck listings to Kijiji with support for single posting and batch processing.

## Features

### UI Components

- **🔐 Credentials Section**
  - Email textbox for Kijiji account
  - Password textbox (hidden input)

- **📁 Files & Directories**
  - File upload for inventory spreadsheet (.xlsx/.xls)
  - Text input for images directory path

- **⚙️ Processing Modes**
  - **Single**: Post one specific record by truck ID
  - **Batch-New**: Process only pending/failed records
  - **Batch-All**: Process all records in the spreadsheet

- **🎛️ Dynamic Controls**
  - Truck ID dropdown (populated from spreadsheet when Single mode is selected)
  - Run button to trigger processing

- **📊 Live Monitoring**
  - Real-time status updates
  - Progress bar for batch operations
  - Live JSON log window showing processing details
  - Download link for updated spreadsheet

## Installation

### Prerequisites

```bash
pip install gradio pandas selenium openpyxl webdriver-manager
```

### Launch the UI

```bash
# From the project root directory
python launch_ui.py
```

Or directly:

```bash
# From the app directory
python -m app.ui
```

The interface will be available at: `http://127.0.0.1:7860`

## Usage

### 1. Setup Credentials
- Enter your Kijiji email address
- Enter your Kijiji password
- These credentials are used to authenticate with Kijiji

### 2. Upload Data
- **Spreadsheet**: Upload your inventory Excel file (.xlsx or .xls)
  - Must contain required columns: `bucket_truck_id`, `image_filename`, `title`, `description`, `price`, `tags`, `fuel_type`, `equipment_type`, `posting_status`
- **Images Directory**: Specify the path to your images folder
  - Example: `assets/images` or `/path/to/your/images`

### 3. Select Processing Mode

#### Single Mode
- Select "Single" from the mode radio buttons
- Choose a specific truck ID from the dropdown (populated after uploading spreadsheet)
- Posts only the selected record

#### Batch-New Mode
- Select "Batch-New" from the mode radio buttons
- Processes only records with:
  - Blank `posting_status`
  - Status = "pending"
  - Status starting with "Error:"

#### Batch-All Mode
- Select "Batch-All" from the mode radio buttons
- Processes ALL records in the spreadsheet regardless of current status

### 4. Run Processing
- Click "🚀 Run Processing" button
- Monitor progress in real-time:
  - Status messages show current operation
  - Progress bar updates during batch processing
  - Live logs display detailed processing information

### 5. Download Results
- Updated spreadsheet becomes available for download after processing
- Contains updated `posting_status` column with results:
  - `Posted YYYY-MM-DD` for successful posts
  - `Error: <description>` for failed posts

## Spreadsheet Format

Your inventory spreadsheet must include these columns:

| Column | Description | Example |
|--------|-------------|---------|
| `bucket_truck_id` | Unique identifier | BT001 |
| `image_filename` | Image file name | truck1.jpg |
| `title` | Ad title | 2018 Ford Bucket Truck |
| `description` | Ad description | Excellent condition... |
| `price` | Price in dollars | 45000 |
| `tags` | Comma-separated tags | ford,bucket,utility |
| `fuel_type` | Fuel type | diesel |
| `equipment_type` | Equipment category | bucket truck |
| `posting_status` | Current status | pending |

## Error Handling

The UI provides comprehensive error handling:

- **Validation Errors**: Missing credentials, files, or invalid data
- **Login Errors**: Kijiji authentication failures
- **Processing Errors**: Individual record posting failures
- **System Errors**: Unexpected exceptions during processing

All errors are logged and displayed in the live logs window.

## Logging

- Real-time logs appear in the JSON log window
- Detailed logs are also saved to `kijiji_ui.log`
- Logs include timestamps, levels, and detailed messages

## File Persistence

- During batch processing, the spreadsheet is periodically saved
- Final updated spreadsheet is always available for download
- Original file is never modified directly

## Tips

1. **Test First**: Start with Single mode to test your setup
2. **Monitor Logs**: Watch the live logs for detailed progress
3. **Images Directory**: Ensure your images directory path is correct and accessible
4. **Spreadsheet Backup**: Keep a backup of your original spreadsheet
5. **Rate Limiting**: Kijiji may have rate limits; batch processing includes delays

## Troubleshooting

### Common Issues

1. **"Upload spreadsheet first"**: Upload your inventory file before selecting truck ID
2. **"No truck IDs found"**: Check that your spreadsheet has the correct column names
3. **"Login failed"**: Verify your Kijiji credentials
4. **"Image not found"**: Check that images directory path is correct and contains the referenced files

### Dependencies

If you get import errors, install missing packages:

```bash
pip install gradio pandas selenium openpyxl webdriver-manager
```

### Chrome Driver

The system automatically downloads the appropriate Chrome driver using `webdriver-manager`. Ensure you have Chrome browser installed.

## Development

### File Structure

```
app/
├── ui.py              # Main Gradio interface
├── data_io.py         # Spreadsheet and data handling
├── posting.py         # Single and batch posting logic
├── kijiji_bot.py      # Selenium automation for Kijiji
├── validators.py      # Data validation
└── logger.py          # Logging configuration
```

### Extending the UI

The UI is built with Gradio Blocks for maximum flexibility. Key extension points:

- Add new input validation in `process_ads()`
- Enhance progress tracking in `progress_callback()`
- Extend logging in `LogHandler` class
- Add new UI components in `create_ui()`

## Security Notes

- Credentials are not stored permanently
- Processing runs in headless Chrome for security
- All file operations use temporary directories when possible
- Logs may contain sensitive information - handle carefully

## Support

For issues or questions:
1. Check the live logs for detailed error messages
2. Review the `kijiji_ui.log` file
3. Ensure all dependencies are installed correctly
4. Verify your spreadsheet format matches requirements
