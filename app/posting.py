"""
Single-record posting module for the Kijiji automation system.

This module provides the post_single function for processing individual 
inventory records through the bot posting pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Import modules from the same package
try:
    from . import validators, data_io
    from .kijiji_bot import KijijiBot
except ImportError:
    try:
        import validators
        import data_io
        from kijiji_bot import KijijiBot
    except ImportError as e:
        # Handle case where dependencies are not available
        import sys
        print(f"Warning: Some dependencies not available: {e}")
        # For testing, we'll define minimal stubs
        if 'pandas' in str(e):
            print("Pandas not installed - some functionality will be limited")
        validators = None
        data_io = None
        KijijiBot = None

# Set up logging
logger = logging.getLogger(__name__)


def post_single(record: Dict[str, Any], bot: KijijiBot, images_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Post a single inventory record using the provided bot.
    
    This function:
    1. Validates the record → aborts on errors
    2. Calls bot.post_ad(record)
    3. Updates the record's status with 'Posted YYYY-MM-DD' or error reason
    4. Returns status for UI display
    
    Args:
        record: Dictionary containing inventory record data
        bot: Initialized KijijiBot instance
        images_dir: Optional directory path for images (defaults to assets/images)
        
    Returns:
        Dict with the following structure:
        {
            'success': bool,           # True if posting successful
            'message': str,            # Human-readable status message
            'status_update': str,      # Status string to update DataFrame
            'ad_url': str,            # URL of posted ad (if successful)
            'record_id': str,         # bucket_truck_id for reference
            'timestamp': str          # ISO timestamp of attempt
        }
    """
    timestamp = datetime.now()
    record_id = record.get('bucket_truck_id', 'Unknown')
    
    logger.info(f"Starting post_single for record: {record_id}")
    
    try:
        # Step 1: Validate record → abort on errors
        logger.debug(f"Validating record: {record_id}")
        
        # Check if validators module is available
        if validators is None:
            error_message = "Validation module not available"
            status_update = "Error: System error - validation unavailable"
            
            logger.error(f"Record {record_id} validation failed: validators module not available")
            
            return {
                'success': False,
                'message': error_message,
                'status_update': status_update,
                'ad_url': None,
                'record_id': record_id,
                'timestamp': timestamp.isoformat()
            }
        
        is_valid, validation_error = validators.validate_inventory_record(record)
        
        if not is_valid:
            error_message = f"Validation failed: {validation_error}"
            status_update = f"Error: {validation_error}"
            
            logger.error(f"Record {record_id} validation failed: {validation_error}")
            
            return {
                'success': False,
                'message': error_message,
                'status_update': status_update,
                'ad_url': None,
                'record_id': record_id,
                'timestamp': timestamp.isoformat()
            }
        
        logger.info(f"Record {record_id} validation passed")
        
        # Step 2: Validate image file exists (if specified)
        if record.get('image_filename'):
            try:
                # Check if data_io module is available
                if data_io is None:
                    logger.warning(f"Record {record_id}: data_io module not available, skipping image validation")
                else:
                    # Verify image file exists using data_io helper
                    image_path = data_io.get_image_path(record, images_dir)
                    logger.debug(f"Image validated: {image_path}")
            except (FileNotFoundError, ValueError) as e:
                error_message = f"Image validation failed: {str(e)}"
                status_update = f"Error: Image not found"
                
                logger.error(f"Record {record_id} image validation failed: {str(e)}")
                
                return {
                    'success': False,
                    'message': error_message,
                    'status_update': status_update,
                    'ad_url': None,
                    'record_id': record_id,
                    'timestamp': timestamp.isoformat()
                }
        
        # Step 3: Call bot.post_ad(record)
        logger.info(f"Posting ad for record: {record_id}")
        post_result = bot.post_ad(record)
        
        # Step 4: Process the result and update status
        if post_result.get('success', False):
            # Successful posting
            date_str = timestamp.strftime('%Y-%m-%d')
            status_update = f"Posted {date_str}"
            
            ad_url = post_result.get('ad_url')
            if ad_url:
                message = f"Ad posted successfully: {ad_url}"
            else:
                message = "Ad posted successfully (URL not available)"
            
            logger.info(f"Record {record_id} posted successfully. Status: {status_update}")
            
            return {
                'success': True,
                'message': message,
                'status_update': status_update,
                'ad_url': ad_url,
                'record_id': record_id,
                'timestamp': timestamp.isoformat()
            }
            
        else:
            # Failed posting
            error_reason = post_result.get('message', 'Unknown error')
            # Truncate error message for status column (keep it concise)
            truncated_error = error_reason[:100] + '...' if len(error_reason) > 100 else error_reason
            status_update = f"Error: {truncated_error}"
            
            logger.error(f"Record {record_id} posting failed: {error_reason}")
            
            return {
                'success': False,
                'message': f"Posting failed: {error_reason}",
                'status_update': status_update,
                'ad_url': None,
                'record_id': record_id,
                'timestamp': timestamp.isoformat()
            }
    
    except Exception as e:
        # Unexpected error during posting process
        error_message = f"Unexpected error: {str(e)}"
        status_update = f"Error: System error"
        
        logger.exception(f"Unexpected error posting record {record_id}: {str(e)}")
        
        return {
            'success': False,
            'message': error_message,
            'status_update': status_update,
            'ad_url': None,
            'record_id': record_id,
            'timestamp': timestamp.isoformat()
        }


def update_record_status(df, record_index: int, status_update: str) -> None:
    """
    Update the posting_status column for a specific record in the DataFrame.
    
    Args:
        df: Pandas DataFrame containing inventory data
        record_index: Index of the record to update
        status_update: New status string to set
    """
    try:
        df.at[record_index, 'posting_status'] = status_update
        logger.debug(f"Updated record {record_index} status to: {status_update}")
    except Exception as e:
        logger.error(f"Failed to update record {record_index} status: {str(e)}")


def post_single_with_df_update(df, record_index: int, bot: KijijiBot, 
                              images_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Post a single record and automatically update the DataFrame status column.
    
    This is a convenience function that combines post_single with automatic
    DataFrame status updates.
    
    Args:
        df: Pandas DataFrame containing inventory data
        record_index: Index of the record to post
        bot: Initialized KijijiBot instance
        images_dir: Optional directory path for images
        
    Returns:
        Dict: Same structure as post_single return value
    """
    try:
        # Get the record from DataFrame
        row = df.iloc[record_index]
        record = data_io.get_record(row)
        
        # Post the record
        result = post_single(record, bot, images_dir)
        
        # Update DataFrame status column
        update_record_status(df, record_index, result['status_update'])
        
        return result
        
    except Exception as e:
        error_message = f"Error processing record at index {record_index}: {str(e)}"
        logger.exception(error_message)
        
        # Try to update status with error
        try:
            update_record_status(df, record_index, "Error: System error")
        except:
            pass
        
        return {
            'success': False,
            'message': error_message,
            'status_update': "Error: System error",
            'ad_url': None,
            'record_id': f"Index-{record_index}",
            'timestamp': datetime.now().isoformat()
        }


# Example usage and testing
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Test the posting function with sample data
    sample_record = {
        'bucket_truck_id': 'TEST001',
        'image_filename': 'test.jpg',
        'title': 'Test Bucket Truck for Post Single',
        'description': 'This is a test description for the post_single function.',
        'price': 45000,
        'tags': 'test,bucket,truck',
        'fuel_type': 'diesel',
        'equipment_type': 'bucket truck',
        'posting_status': 'pending'
    }
    
    print("Testing post_single function...")
    
    # Test validation (without bot)
    if validators is not None:
        try:
            is_valid, validation_error = validators.validate_inventory_record(sample_record)
            print(f"Validation result: {is_valid}")
            if not is_valid:
                print(f"Validation errors: {validation_error}")
            else:
                print("Sample record passed validation!")
        except Exception as e:
            print(f"Validation test failed: {e}")
    else:
        print("Validators module not available - cannot test validation")
    
    print("\nNote: Full testing requires a KijijiBot instance and valid credentials.")
    print("Use this module in conjunction with the main application for full testing.")
