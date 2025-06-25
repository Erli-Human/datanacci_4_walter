"""
Spreadsheet & image helpers for the Kijiji automation system.

This module provides functionality for:
- Loading and saving inventory data from/to Excel files
- Converting DataFrame rows to dictionaries for bot processing
- Image file lookup and validation
- Record validation using the validators module
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple, Union
import logging

# Import validators module (will be in same package)
try:
    from . import validators
except ImportError:
    import validators

# Set up logging
logger = logging.getLogger(__name__)

# Required columns for the inventory spreadsheet
REQUIRED_COLUMNS = [
    'bucket_truck_id',
    'image_filename', 
    'title',
    'description',
    'price',
    'tags',
    'fuel_type',
    'equipment_type',
    'posting_status'
]

# Default images directory path
DEFAULT_IMAGES_DIR = Path(__file__).parent.parent / "assets" / "images"


def load_inventory(path: Union[str, Path]) -> pd.DataFrame:
    """
    Load inventory data from Excel file and enforce schema.
    
    Args:
        path: Path to the Excel file
        
    Returns:
        pd.DataFrame: Loaded inventory data with enforced schema
        
    Raises:
        FileNotFoundError: If the Excel file doesn't exist
        ValueError: If required columns are missing
        Exception: If file cannot be read
    """
    path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")
    
    try:
        # Load the Excel file
        df = pd.read_excel(path)
        logger.info(f"Loaded inventory file: {path} ({len(df)} rows)")
        
        # Check for required columns
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Ensure all required columns are present and in correct order
        # Add any missing columns with default values
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        
        # Reorder columns to match required schema
        df = df[REQUIRED_COLUMNS + [col for col in df.columns if col not in REQUIRED_COLUMNS]]
        
        # Clean up data types
        df['bucket_truck_id'] = df['bucket_truck_id'].astype(str)
        df['image_filename'] = df['image_filename'].astype(str)
        df['title'] = df['title'].astype(str)
        df['description'] = df['description'].fillna('').astype(str)
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['tags'] = df['tags'].fillna('').astype(str)
        df['fuel_type'] = df['fuel_type'].astype(str)
        df['equipment_type'] = df['equipment_type'].astype(str)
        df['posting_status'] = df['posting_status'].fillna('pending').astype(str)
        
        logger.info(f"Schema enforced successfully. Columns: {list(df.columns)}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading inventory file {path}: {str(e)}")
        raise


def save_inventory(df: pd.DataFrame, path: Union[str, Path]) -> None:
    """
    Save inventory data to Excel file to persist status updates.
    
    Args:
        df: DataFrame containing inventory data
        path: Path where to save the Excel file
        
    Raises:
        Exception: If file cannot be written
    """
    path = Path(path)
    
    try:
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to Excel with formatting
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Inventory', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Inventory']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"Inventory saved successfully to: {path}")
        
    except Exception as e:
        logger.error(f"Error saving inventory file {path}: {str(e)}")
        raise


def get_record(row: pd.Series) -> Dict[str, Any]:
    """
    Convert a DataFrame row into a dictionary used by the bot.
    
    Args:
        row: A pandas Series representing a single row from the inventory DataFrame
        
    Returns:
        Dict[str, Any]: Dictionary with all the required fields for bot processing
    """
    record = {
        'bucket_truck_id': str(row.get('bucket_truck_id', '')),
        'image_filename': str(row.get('image_filename', '')),
        'title': str(row.get('title', '')),
        'description': str(row.get('description', '')),
        'price': float(row.get('price', 0)) if pd.notna(row.get('price')) else 0.0,
        'tags': str(row.get('tags', '')),
        'fuel_type': str(row.get('fuel_type', '')),
        'equipment_type': str(row.get('equipment_type', '')),
        'posting_status': str(row.get('posting_status', 'pending'))
    }
    
    # Add any additional columns that might be present
    for col in row.index:
        if col not in record:
            record[col] = row[col]
    
    return record


def get_image_path(row: Union[pd.Series, Dict[str, Any]], images_dir: Union[str, Path] = None) -> Path:
    """
    Get the full path to an image file and assert its existence.
    
    Args:
        row: DataFrame row or dictionary containing image_filename
        images_dir: Directory containing images (defaults to assets/images)
        
    Returns:
        Path: Full path to the image file
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
        ValueError: If image_filename is missing or empty
    """
    if images_dir is None:
        images_dir = DEFAULT_IMAGES_DIR
    else:
        images_dir = Path(images_dir)
    
    # Extract image filename
    if isinstance(row, pd.Series):
        image_filename = row.get('image_filename', '')
    elif isinstance(row, dict):
        image_filename = row.get('image_filename', '')
    else:
        raise ValueError("Row must be a pandas Series or dictionary")
    
    if not image_filename or pd.isna(image_filename):
        raise ValueError("image_filename is missing or empty")
    
    image_filename = str(image_filename).strip()
    if not image_filename:
        raise ValueError("image_filename is empty after stripping whitespace")
    
    # Construct full path
    image_path = images_dir / image_filename
    
    # Assert existence
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Additional validation - check if it's actually a file
    if not image_path.is_file():
        raise FileNotFoundError(f"Path exists but is not a file: {image_path}")
    
    logger.debug(f"Image found: {image_path}")
    return image_path


def validate_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a record using the validators module.
    
    Args:
        record: Dictionary containing record data to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
                         If valid: (True, "")
                         If invalid: (False, "Error description")
    """
    try:
        # Call the validators module
        validation_result = validators.validate_inventory_record(record)
        
        if validation_result is True:
            return True, ""
        elif validation_result is False:
            return False, "Record validation failed"
        elif isinstance(validation_result, tuple):
            # If validators returns a tuple, use it directly
            return validation_result
        elif isinstance(validation_result, str):
            # If validators returns a string, treat it as an error message
            return False, validation_result
        else:
            # Unknown return type, assume it's valid
            return True, ""
            
    except AttributeError:
        # validators module doesn't have validate_inventory_record function
        logger.warning("validators.validate_inventory_record not found, performing basic validation")
        return _basic_validation(record)
    except Exception as e:
        logger.error(f"Error during record validation: {str(e)}")
        return False, f"Validation error: {str(e)}"


def _basic_validation(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Perform basic validation when validators module is not available.
    
    Args:
        record: Dictionary containing record data to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    errors = []
    
    # Check required fields
    required_fields = ['bucket_truck_id', 'image_filename', 'title', 'price']
    for field in required_fields:
        if not record.get(field):
            errors.append(f"Missing or empty required field: {field}")
    
    # Validate price
    try:
        price = float(record.get('price', 0))
        if price <= 0:
            errors.append("Price must be greater than 0")
    except (ValueError, TypeError):
        errors.append("Price must be a valid number")
    
    # Validate image filename
    image_filename = record.get('image_filename', '')
    if image_filename:
        try:
            # Try to get the image path to validate it exists
            get_image_path(record)
        except (FileNotFoundError, ValueError) as e:
            errors.append(f"Image validation failed: {str(e)}")
    
    if errors:
        return False, "; ".join(errors)
    else:
        return True, ""


# Utility function to create a sample inventory file
def create_sample_inventory(path: Union[str, Path]) -> None:
    """
    Create a sample inventory Excel file with the required schema.
    
    Args:
        path: Path where to create the sample file
    """
    sample_data = {
        'bucket_truck_id': ['BT001', 'BT002', 'BT003'],
        'image_filename': ['truck1.jpg', 'truck2.jpg', 'truck3.jpg'],
        'title': ['2018 Ford Bucket Truck', '2020 Chevrolet Bucket Truck', '2019 GMC Bucket Truck'],
        'description': [
            'Excellent condition bucket truck with 45ft reach',
            'Low mileage bucket truck, perfect for utility work',
            'Well-maintained bucket truck with recent service'
        ],
        'price': [45000, 52000, 48000],
        'tags': ['ford,bucket,utility', 'chevrolet,bucket,utility', 'gmc,bucket,utility'],
        'fuel_type': ['Diesel', 'Gasoline', 'Diesel'],
        'equipment_type': ['Bucket Truck', 'Bucket Truck', 'Bucket Truck'],
        'posting_status': ['pending', 'pending', 'pending']
    }
    
    df = pd.DataFrame(sample_data)
    save_inventory(df, path)
    logger.info(f"Sample inventory created at: {path}")


if __name__ == "__main__":
    # Test the module
    import sys
    import os
    
    # Add parent directory to path for imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Create sample inventory if it doesn't exist
    sample_path = Path("../inventory.xlsx")
    if not sample_path.exists():
        create_sample_inventory(sample_path)
    
    # Test loading
    try:
        df = load_inventory(sample_path)
        print(f"Loaded {len(df)} records")
        print(f"Columns: {list(df.columns)}")
        
        # Test getting a record
        if len(df) > 0:
            record = get_record(df.iloc[0])
            print(f"Sample record: {record}")
            
            # Test validation
            is_valid, message = validate_record(record)
            print(f"Validation result: {is_valid}, {message}")
        
    except Exception as e:
        print(f"Error testing module: {e}")
