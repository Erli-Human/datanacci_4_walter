"""
Data validation module for the Kijiji automation system.

This module provides validation functions for inventory records.
"""

import re
from typing import Dict, Any, Tuple, Union, List
from pathlib import Path


def validate_inventory_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate an inventory record for completeness and correctness.
    
    Args:
        record: Dictionary containing inventory record data
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
                         If valid: (True, "")
                         If invalid: (False, "Error description")
    """
    errors = []
    
    # Required fields validation
    required_fields = {
        'bucket_truck_id': str,
        'image_filename': str,
        'title': str,
        'description': str,
        'price': (int, float),
        'tags': str,
        'fuel_type': str,
        'equipment_type': str,
        'posting_status': str
    }
    
    # Check if all required fields are present and non-empty
    for field, expected_type in required_fields.items():
        if field not in record:
            errors.append(f"Missing required field: {field}")
            continue
            
        value = record[field]
        
        # Check if field is empty (but allow 0 for numeric fields)
        if field == 'price':
            if value is None or (isinstance(value, str) and value.strip() == ''):
                errors.append(f"Field '{field}' cannot be empty")
        else:
            if not value or (isinstance(value, str) and value.strip() == ''):
                errors.append(f"Field '{field}' cannot be empty")
                continue
        
        # Type validation
        if not isinstance(value, expected_type):
            if field == 'price':
                try:
                    float(value)
                except (ValueError, TypeError):
                    errors.append(f"Field '{field}' must be a number, got: {type(value).__name__}")
            else:
                errors.append(f"Field '{field}' must be {expected_type.__name__}, got: {type(value).__name__}")
    
    # Specific field validations
    if 'bucket_truck_id' in record:
        bucket_truck_id = str(record['bucket_truck_id']).strip()
        if not re.match(r'^[A-Z0-9_-]+$', bucket_truck_id, re.IGNORECASE):
            errors.append("bucket_truck_id must contain only letters, numbers, underscore, or dash")
    
    if 'price' in record:
        try:
            price = float(record['price'])
            if price <= 0:
                errors.append("Price must be greater than 0")
            elif price > 1000000:  # Reasonable upper limit
                errors.append("Price seems unreasonably high (over $1,000,000)")
        except (ValueError, TypeError):
            errors.append("Price must be a valid number")
    
    if 'image_filename' in record:
        image_filename = str(record['image_filename']).strip()
        if not image_filename:
            errors.append("image_filename cannot be empty")
        else:
            # Validate file extension
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
            file_ext = Path(image_filename).suffix.lower()
            if file_ext not in valid_extensions:
                errors.append(f"Invalid image file extension: {file_ext}. Must be one of: {', '.join(valid_extensions)}")
            
            # Check for invalid characters in filename
            if re.search(r'[<>:"/\\|?*]', image_filename):
                errors.append("image_filename contains invalid characters")
    
    if 'title' in record:
        title = str(record['title']).strip()
        if len(title) < 5:
            errors.append("Title must be at least 5 characters long")
        elif len(title) > 200:
            errors.append("Title must be 200 characters or less")
    
    if 'description' in record:
        description = str(record['description']).strip()
        if len(description) < 10:
            errors.append("Description must be at least 10 characters long")
        elif len(description) > 5000:
            errors.append("Description must be 5000 characters or less")
    
    if 'fuel_type' in record:
        fuel_type = str(record['fuel_type']).strip().lower()
        valid_fuel_types = {'diesel', 'gasoline', 'gas', 'electric', 'hybrid', 'propane', 'cng'}
        if fuel_type not in valid_fuel_types:
            errors.append(f"Invalid fuel_type: {fuel_type}. Must be one of: {', '.join(valid_fuel_types)}")
    
    if 'equipment_type' in record:
        equipment_type = str(record['equipment_type']).strip().lower()
        valid_equipment_types = {'bucket truck', 'utility truck', 'crane truck', 'service truck', 'aerial lift'}
        if equipment_type not in valid_equipment_types:
            errors.append(f"Invalid equipment_type: {equipment_type}. Must be one of: {', '.join(valid_equipment_types)}")
    
    if 'posting_status' in record:
        posting_status = str(record['posting_status']).strip().lower()
        valid_statuses = {'pending', 'posted', 'sold', 'inactive', 'draft'}
        if posting_status not in valid_statuses:
            errors.append(f"Invalid posting_status: {posting_status}. Must be one of: {', '.join(valid_statuses)}")
    
    # Tags validation
    if 'tags' in record:
        tags = str(record['tags']).strip()
        if tags:
            # Split tags and validate each one
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            for tag in tag_list:
                if len(tag) < 2:
                    errors.append(f"Tag '{tag}' is too short (minimum 2 characters)")
                elif len(tag) > 50:
                    errors.append(f"Tag '{tag}' is too long (maximum 50 characters)")
                elif not re.match(r'^[a-zA-Z0-9\s_-]+$', tag):
                    errors.append(f"Tag '{tag}' contains invalid characters")
    
    # Return result
    if errors:
        return False, "; ".join(errors)
    else:
        return True, ""


def validate_price(price: Union[str, int, float]) -> Tuple[bool, str]:
    """
    Validate a price value.
    
    Args:
        price: Price value to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        price_float = float(price)
        if price_float <= 0:
            return False, "Price must be greater than 0"
        elif price_float > 1000000:
            return False, "Price seems unreasonably high (over $1,000,000)"
        return True, ""
    except (ValueError, TypeError):
        return False, "Price must be a valid number"


def validate_image_filename(filename: str) -> Tuple[bool, str]:
    """
    Validate an image filename.
    
    Args:
        filename: Image filename to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not filename or not filename.strip():
        return False, "Image filename cannot be empty"
    
    filename = filename.strip()
    
    # Check file extension
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in valid_extensions:
        return False, f"Invalid image file extension: {file_ext}. Must be one of: {', '.join(valid_extensions)}"
    
    # Check for invalid characters
    if re.search(r'[<>:"/\\|?*]', filename):
        return False, "Image filename contains invalid characters"
    
    return True, ""


def validate_bucket_truck_id(truck_id: str) -> Tuple[bool, str]:
    """
    Validate a bucket truck ID.
    
    Args:
        truck_id: Truck ID to validate
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not truck_id or not truck_id.strip():
        return False, "Bucket truck ID cannot be empty"
    
    truck_id = truck_id.strip()
    
    if not re.match(r'^[A-Z0-9_-]+$', truck_id, re.IGNORECASE):
        return False, "Bucket truck ID must contain only letters, numbers, underscore, or dash"
    
    if len(truck_id) < 3:
        return False, "Bucket truck ID must be at least 3 characters long"
    
    if len(truck_id) > 20:
        return False, "Bucket truck ID must be 20 characters or less"
    
    return True, ""


def validate_tags(tags: str) -> Tuple[bool, str]:
    """
    Validate tags string.
    
    Args:
        tags: Comma-separated tags string
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not tags:
        return True, ""  # Tags are optional
    
    tags = tags.strip()
    if not tags:
        return True, ""
    
    # Split tags and validate each one
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
    
    if len(tag_list) > 20:
        return False, "Too many tags (maximum 20 allowed)"
    
    for tag in tag_list:
        if len(tag) < 2:
            return False, f"Tag '{tag}' is too short (minimum 2 characters)"
        elif len(tag) > 50:
            return False, f"Tag '{tag}' is too long (maximum 50 characters)"
        elif not re.match(r'^[a-zA-Z0-9\s_-]+$', tag):
            return False, f"Tag '{tag}' contains invalid characters"
    
    return True, ""


if __name__ == "__main__":
    # Test the validators
    test_record = {
        'bucket_truck_id': 'BT001',
        'image_filename': 'truck1.jpg',
        'title': 'Test Bucket Truck',
        'description': 'This is a test description for the bucket truck.',
        'price': 45000,
        'tags': 'bucket,truck,utility',
        'fuel_type': 'diesel',
        'equipment_type': 'bucket truck',
        'posting_status': 'pending'
    }
    
    is_valid, message = validate_inventory_record(test_record)
    print(f"Test record validation: {is_valid}")
    if not is_valid:
        print(f"Errors: {message}")
    else:
        print("Record is valid!")
