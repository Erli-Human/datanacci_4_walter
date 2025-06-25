# Datanacci 4 Walter

A Python application for automated Kijiji posting with Gradio UI interface.

## Project Structure

```
datanacci_4_walter/
├─ app/                    # Python modules
│  ├─ ui.py                # Gradio code
│  ├─ kijiji_bot.py        # Selenium routines
│  ├─ data_io.py           # Spreadsheet & image helpers
│  ├─ validators.py        # Data-quality checks
│  └─ logger.py            # Loguru wrapper
├─ assets/images/          # Bucket-truck photos
├─ inventory.xlsx          # Sample sheet
├─ main.py                 # Launches gradio
├─ activate_env.ps1        # PowerShell activation script
└─ README.md               # This file
```

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Windows with PowerShell

### Virtual Environment Setup

The virtual environment `datanacci_4_walter_env` has been created in the parent directory with all required packages installed:

- gradio
- selenium
- pandas
- openpyxl
- pillow
- loguru
- webdriver-manager

### Activation

#### Method 1: Using the activation script
```powershell
cd datanacci_4_walter
.\activate_env.ps1
```

#### Method 2: Manual activation
```powershell
# From the parent directory
.\datanacci_4_walter_env\Scripts\python.exe -m pip list  # to verify packages
```

### Running the Application

Once the virtual environment is activated:
```powershell
python main.py
```

## Development Notes

- All packages are installed from PyPI for self-contained solution
- Uses webdriver-manager for automatic WebDriver management
- Loguru is configured for comprehensive logging
- Gradio provides the web-based user interface
- Selenium handles Kijiji automation
- Pandas and openpyxl manage Excel data processing
- Pillow handles image processing

## File Descriptions

- **main.py**: Entry point that launches the Gradio interface
- **app/ui.py**: Contains Gradio UI components and layout
- **app/kijiji_bot.py**: Selenium-based automation for Kijiji interactions
- **app/data_io.py**: Utilities for reading/writing Excel files and handling images
- **app/validators.py**: Data validation and quality checks
- **app/logger.py**: Centralized logging configuration using loguru
- **inventory.xlsx**: Sample/template Excel file for inventory data
- **assets/images/**: Directory for storing bucket truck photos
