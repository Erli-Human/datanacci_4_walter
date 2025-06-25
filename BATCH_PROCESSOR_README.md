# Batch Processor - `run_batch()` Function

## Overview

The `run_batch()` function has been successfully implemented in `app/posting.py`. This function provides automated batch processing for posting multiple inventory records to Kijiji with comprehensive progress tracking, error handling, and file persistence.

## Function Signature

```python
def run_batch(df, mode: str, bot, images_dir: Optional[Path] = None, 
              progress_cb=None, file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]
```

## Parameters

- **`df`**: Pandas DataFrame containing inventory data with required columns
- **`mode`**: Processing mode
  - `'new'` - Only process records where `posting_status` is blank, 'pending', or starts with 'Error'
  - `'all'` - Process entire sheet regardless of current status
- **`bot`**: Initialized KijijiBot instance for posting ads
- **`images_dir`**: Optional directory path for images (defaults to assets/images)
- **`progress_cb`**: Optional callback function for progress updates - `function(percentage: float, message: str)`
- **`file_path`**: Optional file path for periodic spreadsheet persistence

## Return Value

Returns a dictionary with comprehensive batch processing results:

```python
{
    'success': bool,           # True if batch completed without critical errors
    'total_records': int,      # Total number of records processed
    'successful_posts': int,   # Number of successful posts
    'failed_posts': int,       # Number of failed posts
    'skipped_records': int,    # Number of records skipped
    'results': List[Dict],     # Individual results for each processed record
    'message': str             # Summary message
}
```

## Key Features

### ✅ Mode Selection

- **'new' mode**: Only processes records that need posting (blank, pending, or failed status)
- **'all' mode**: Processes every record in the DataFrame regardless of status

### ✅ Progress Tracking

- Real-time progress callbacks with percentage and descriptive messages
- Suitable for UI integration with progress bars
- Example: `[45.2%] Processing record 5/11: BT005`

### ✅ Error Handling

- Individual record errors don't stop the entire batch
- Comprehensive error logging and recovery
- Keyboard interrupt handling (Ctrl+C)
- Critical error detection and reporting

### ✅ Status Updates

- Automatic updating of `posting_status` column in DataFrame
- Success status: `"Posted YYYY-MM-DD"`
- Error status: `"Error: [error description]"`

### ✅ File Persistence

- Periodic saving of spreadsheet during processing
- Configurable persistence interval (every 10% of records)
- Final save at completion
- Error handling for file operations

### ✅ Comprehensive Logging

- Detailed logging of all operations
- Progress tracking in logs
- Error reporting with context

## Usage Examples

### Basic Usage

```python
from app.posting import run_batch
from app.kijiji_bot import KijijiBot
from app import data_io

# Load inventory data
df = data_io.load_inventory("inventory.xlsx")

# Initialize bot
bot = KijijiBot(username="user", password="pass")

# Run batch processing for new records only
result = run_batch(df, mode='new', bot=bot)

print(f"Processed {result['total_records']} records")
print(f"Success: {result['successful_posts']}, Failed: {result['failed_posts']}")
```

### With Progress Tracking

```python
def progress_handler(percentage, message):
    print(f"[{percentage:5.1f}%] {message}")
    # Update your UI progress bar here

result = run_batch(
    df=df,
    mode='new', 
    bot=bot,
    progress_cb=progress_handler
)
```

### With File Persistence

```python
result = run_batch(
    df=df,
    mode='all',
    bot=bot,
    file_path="inventory_updated.xlsx",
    progress_cb=progress_handler
)
```

### Complete Example

```python
import logging
from pathlib import Path
from app.posting import run_batch
from app.kijiji_bot import KijijiBot
from app import data_io

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load data
inventory_file = Path("inventory.xlsx")
df = data_io.load_inventory(inventory_file)

# Initialize bot
bot = KijijiBot(username="your_username", password="your_password")
if not bot.login():
    print("Failed to login to Kijiji")
    exit(1)

# Define progress callback
def update_progress(percentage, message):
    print(f"Progress: {percentage:5.1f}% - {message}")

# Run batch processing
try:
    result = run_batch(
        df=df,
        mode='new',                    # Only process new/failed records
        bot=bot,
        images_dir=Path("assets/images"),
        progress_cb=update_progress,
        file_path=inventory_file       # Save progress periodically
    )
    
    # Handle results
    if result['success']:
        print(f"✅ Batch completed successfully!")
        print(f"   📊 Summary: {result['message']}")
    else:
        print(f"❌ Batch failed: {result['message']}")
        
    # Save final state
    data_io.save_inventory(df, inventory_file)
    
except KeyboardInterrupt:
    print("🛑 Batch processing cancelled by user")
except Exception as e:
    print(f"💥 Unexpected error: {e}")
finally:
    bot.logout()
```

## Record Status Flow

The `posting_status` column follows this flow:

1. **Initial States** (processed by 'new' mode):
   - `""` (blank)
   - `"pending"`
   - `"Error: [description]"`

2. **Success State**:
   - `"Posted YYYY-MM-DD"`

3. **Failure States**:
   - `"Error: [specific error message]"`
   - `"Error: System error"` (for unexpected exceptions)

## Integration Notes

### For UI Integration

```python
class BatchProgressHandler:
    def __init__(self, progress_bar, status_label):
        self.progress_bar = progress_bar
        self.status_label = status_label
    
    def __call__(self, percentage, message):
        self.progress_bar.value = percentage
        self.status_label.text = message
        # Force UI update if needed
        app.process_events()

# Use with your UI framework
progress_handler = BatchProgressHandler(my_progress_bar, my_status_label)
result = run_batch(df, 'new', bot, progress_cb=progress_handler)
```

### Error Handling Best Practices

```python
result = run_batch(df, mode, bot, progress_cb=progress_callback)

if not result['success']:
    # Handle critical errors
    show_error_dialog(f"Batch processing failed: {result['message']}")
else:
    # Check individual record results
    failed_records = [r for r in result['results'] if not r['success']]
    if failed_records:
        show_warning_dialog(f"{len(failed_records)} records failed to post")
```

## Testing

The implementation includes comprehensive testing:

- **`demo_batch_processing.py`**: Full-featured demo with mock data and pandas
- **`test_batch_simple.py`**: Simplified test without external dependencies

Run tests:
```bash
python test_batch_simple.py       # Basic functionality test
python demo_batch_processing.py   # Full demo (requires pandas)
```

## Files Modified/Created

1. **`app/posting.py`**: Added `run_batch()` function and helper functions
2. **`demo_batch_processing.py`**: Comprehensive demo with multiple test scenarios
3. **`test_batch_simple.py`**: Simple test without external dependencies
4. **`BATCH_PROCESSOR_README.md`**: This documentation

## Performance Considerations

- **Persistence Interval**: Currently set to every 10% of records (minimum 1)
- **Memory Usage**: Maintains all results in memory until completion
- **Processing Speed**: Limited by bot posting speed and network delays
- **Interruption Safety**: Can be safely interrupted; progress is preserved

## Future Enhancements

Potential improvements for future versions:

1. **Configurable persistence interval**
2. **Resume functionality** from interrupted batches
3. **Parallel processing** for multiple records (with rate limiting)
4. **Detailed statistics** and reporting
5. **Retry mechanisms** for failed records
6. **Email notifications** for batch completion

---

**Status**: ✅ **COMPLETED** - Ready for production use

The `run_batch()` function is fully implemented and tested, providing robust batch processing capabilities for the Kijiji automation system.
