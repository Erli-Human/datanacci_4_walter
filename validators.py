import os
from typing import List, Dict, Any


def check_required_fields(record: Dict[str, Any]) -> List[str]:
    """
    Check if all required fields are present and not empty.
    
    Args:
        record: Dictionary containing record data
        
    Returns:
        List of error messages for missing required fields
    """
    errors = []
    required_fields = ['title', 'description', 'price', 'image']
    
    for field in required_fields:
        if field not in record:
            errors.append(f"Missing required field: {field}")
        elif not record[field] or str(record[field]).strip() == "":
            errors.append(f"Required field '{field}' is empty")
    
    return errors


def check_image_exists(record: Dict[str, Any], images_dir: str) -> List[str]:
    """
    Check if the image file specified in the record exists in the images directory.
    
    Args:
        record: Dictionary containing record data
        images_dir: Path to the directory containing images
        
    Returns:
        List of error messages if image file doesn't exist
    """
    errors = []
    
    if 'image' not in record or not record['image']:
        return errors  # This will be caught by check_required_fields
    
    image_filename = record['image']
    image_path = os.path.join(images_dir, image_filename)
    
    if not os.path.exists(image_path):
        errors.append(f"Image file not found: {image_filename}")
    elif not os.path.isfile(image_path):
        errors.append(f"Image path is not a file: {image_filename}")
    
    return errors


def check_price_format(record: Dict[str, Any]) -> List[str]:
    """
    Check if price is a positive numeric value <= 999999.
    
    Args:
        record: Dictionary containing record data
        
    Returns:
        List of error messages for invalid price format
    """
    errors = []
    
    if 'price' not in record:
        return errors  # This will be caught by check_required_fields
    
    price = record['price']
    
    try:
        # Convert to float to handle both int and float inputs
        price_value = float(price)
        
        if price_value <= 0:
            errors.append("Price must be positive")
        elif price_value > 999999:
            errors.append("Price must be <= 999999")
            
    except (ValueError, TypeError):
        errors.append("Price must be a valid number")
    
    return errors


def check_length(text: str, max_length: int, field_name: str) -> List[str]:
    """
    Check if text length is within the specified limit.
    
    Args:
        text: Text to check
        max_length: Maximum allowed length
        field_name: Name of the field being checked (for error messages)
        
    Returns:
        List of error messages for length violations
    """
    errors = []
    
    if text is None:
        text = ""
    
    text_str = str(text).strip()
    
    if len(text_str) > max_length:
        errors.append(f"{field_name} exceeds maximum length of {max_length} characters (current: {len(text_str)})")
    
    return errors


def check_title_length(record: Dict[str, Any]) -> List[str]:
    """
    Check if title length is <= 60 characters.
    
    Args:
        record: Dictionary containing record data
        
    Returns:
        List of error messages for title length violations
    """
    if 'title' not in record:
        return []  # This will be caught by check_required_fields
    
    return check_length(record['title'], 60, 'Title')


def check_description_length(record: Dict[str, Any]) -> List[str]:
    """
    Check if description length is reasonable (between 10 and 1000 characters).
    
    Args:
        record: Dictionary containing record data
        
    Returns:
        List of error messages for description length violations
    """
    errors = []
    
    if 'description' not in record:
        return errors  # This will be caught by check_required_fields
    
    description = str(record['description']).strip() if record['description'] else ""
    
    if len(description) < 10:
        errors.append("Description is too short (minimum 10 characters)")
    elif len(description) > 1000:
        errors.append(f"Description exceeds maximum length of 1000 characters (current: {len(description)})")
    
    return errors


def validate_record(record: Dict[str, Any], images_dir: str = "images") -> List[str]:
    """
    Validate a record against all data quality rules.
    
    Args:
        record: Dictionary containing record data to validate
        images_dir: Path to the directory containing images (default: "images")
        
    Returns:
        List of error messages. Empty list means validation passed.
    """
    all_errors = []
    
    # Check required fields first
    all_errors.extend(check_required_fields(record))
    
    # Only proceed with other checks if required fields are present
    if not all_errors:
        # Check image exists
        all_errors.extend(check_image_exists(record, images_dir))
        
        # Check price format
        all_errors.extend(check_price_format(record))
        
        # Check title length
        all_errors.extend(check_title_length(record))
        
        # Check description length
        all_errors.extend(check_description_length(record))
    
    return all_errors


# Example usage and testing
if __name__ == "__main__":
    # Test cases
    valid_record = {
        'title': 'Sample Product',
        'description': 'This is a sample product description that meets the minimum length requirement.',
        'price': 29.99,
        'image': 'sample.jpg'
    }
    
    invalid_record = {
        'title': 'This is a very long title that exceeds the maximum allowed length of sixty characters',
        'description': 'Short',
        'price': -10,
        'image': 'nonexistent.jpg'
    }
    
    print("Valid record errors:", validate_record(valid_record))
    print("Invalid record errors:", validate_record(invalid_record))
