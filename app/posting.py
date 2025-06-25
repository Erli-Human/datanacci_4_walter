"""
Single-record posting module for the Kijiji automation system.

This module provides the post_single function for processing individual 
inventory records through the bot posting pipeline.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
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


def run_batch(df, mode: str, bot, images_dir: Optional[Path] = None, 
              progress_cb=None, file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Batch processor for posting multiple inventory records.
    
    Args:
        df: Pandas DataFrame containing inventory data
        mode: Processing mode - 'new' (only blank/failed) or 'all' (entire sheet)
        bot: Initialized KijijiBot instance
        images_dir: Optional directory path for images
        progress_cb: Optional callback function for progress updates
                    Should accept (percentage: float, message: str)
    
    Returns:
        Dict with batch processing results:
        {
            'success': bool,           # True if batch completed without critical errors
            'total_records': int,      # Total number of records processed
            'successful_posts': int,   # Number of successful posts
            'failed_posts': int,       # Number of failed posts
            'skipped_records': int,    # Number of records skipped
            'results': List[Dict],     # Individual results for each processed record
            'message': str             # Summary message
        }
    """
    logger.info(f"Starting batch processing with mode: {mode}")
    
    # Initialize result tracking
    batch_result = {
        'success': True,
        'total_records': 0,
        'successful_posts': 0,
        'failed_posts': 0,
        'skipped_records': 0,
        'results': [],
        'message': ''
    }
    
    # Determine which records to process based on mode
    if mode == 'new':
        # Only process records where posting_status is blank, 'pending', or starts with 'Error'
        mask = (
            df['posting_status'].isna() | 
            (df['posting_status'] == '') | 
            (df['posting_status'] == 'pending') |
            df['posting_status'].str.startswith('Error', na=False)
        )
        records_to_process = df[mask].index.tolist()
        logger.info(f"Mode 'new': Found {len(records_to_process)} records to process")
    elif mode == 'all':
        # Process entire sheet
        records_to_process = df.index.tolist()
        logger.info(f"Mode 'all': Processing all {len(records_to_process)} records")
    else:
        error_msg = f"Invalid mode '{mode}'. Must be 'new' or 'all'"
        logger.error(error_msg)
        batch_result['success'] = False
        batch_result['message'] = error_msg
        return batch_result
    
    batch_result['total_records'] = len(records_to_process)
    
    if len(records_to_process) == 0:
        batch_result['message'] = "No records to process"
        logger.info("No records found to process")
        return batch_result
    
    # Process records with progress tracking
    persist_interval = max(1, len(records_to_process) // 10)  # Persist every 10% or at least every record
    processed_count = 0
    
    try:
        for i, record_index in enumerate(records_to_process):
            processed_count += 1
            
            # Calculate progress percentage
            progress_percentage = (processed_count / len(records_to_process)) * 100
            
            # Get record info for progress message
            try:
                record_id = df.at[record_index, 'bucket_truck_id']
            except:
                record_id = f"Index-{record_index}"
            
            progress_message = f"Processing record {processed_count}/{len(records_to_process)}: {record_id}"
            
            # Emit progress to UI if callback provided
            if progress_cb:
                try:
                    progress_cb(progress_percentage, progress_message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
            
            logger.info(progress_message)
            
            try:
                # Process the single record
                result = post_single_with_df_update(df, record_index, bot, images_dir)
                
                # Track results
                batch_result['results'].append(result)
                
                if result['success']:
                    batch_result['successful_posts'] += 1
                    logger.info(f"✓ Record {record_id} posted successfully")
                else:
                    batch_result['failed_posts'] += 1
                    logger.warning(f"✗ Record {record_id} failed: {result['message']}")
                    
            except Exception as e:
                # Handle individual record processing errors
                error_msg = f"Error processing record {record_id}: {str(e)}"
                logger.exception(error_msg)
                
                batch_result['failed_posts'] += 1
                batch_result['results'].append({
                    'success': False,
                    'message': error_msg,
                    'status_update': "Error: System error",
                    'ad_url': None,
                    'record_id': record_id,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Try to update the DataFrame status
                try:
                    update_record_status(df, record_index, "Error: System error")
                except:
                    pass
            
            # Persist spreadsheet periodically
            if processed_count % persist_interval == 0 or processed_count == len(records_to_process):
                if file_path and data_io is not None:
                    try:
                        logger.info(f"Persisting spreadsheet after {processed_count} records")
                        persist_dataframe(df, file_path)
                    except Exception as e:
                        logger.warning(f"Failed to persist spreadsheet: {e}")
                elif processed_count == len(records_to_process):
                    # Always log when we reach the end, even if no file path provided
                    logger.info("Batch processing completed - no file path provided for persistence")
    
    except KeyboardInterrupt:
        logger.info("Batch processing interrupted by user")
        batch_result['success'] = False
        batch_result['message'] = f"Batch processing interrupted after {processed_count} records"
        return batch_result
    
    except Exception as e:
        logger.exception(f"Critical error during batch processing: {e}")
        batch_result['success'] = False
        batch_result['message'] = f"Critical error: {str(e)}"
        return batch_result
    
    # Final progress update
    if progress_cb:
        try:
            progress_cb(100.0, "Batch processing completed")
        except Exception as e:
            logger.warning(f"Final progress callback failed: {e}")
    
    # Generate summary message
    summary = f"Batch processing completed: {batch_result['successful_posts']} successful, {batch_result['failed_posts']} failed"
    if batch_result['skipped_records'] > 0:
        summary += f", {batch_result['skipped_records']} skipped"
    
    batch_result['message'] = summary
    logger.info(summary)
    
    return batch_result


def persist_dataframe(df, file_path: Union[str, Path]) -> bool:
    """
    Helper function to persist the DataFrame to Excel file.
    
    Args:
        df: Pandas DataFrame to save
        file_path: Path to save the Excel file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if data_io is not None:
            data_io.save_inventory(df, file_path)
            logger.info(f"DataFrame persisted to {file_path}")
            return True
        else:
            logger.warning("data_io module not available - cannot persist DataFrame")
            return False
    except Exception as e:
        logger.error(f"Failed to persist DataFrame: {e}")
        return False


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
