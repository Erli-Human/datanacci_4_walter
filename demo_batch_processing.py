#!/usr/bin/env python3
"""
Demo script for testing the run_batch function.

This script demonstrates the batch processing functionality with:
- Mock bot for testing
- Progress callback demonstration
- Different processing modes ('new' vs 'all')
- File persistence simulation
"""

import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add the app directory to the path for imports
sys.path.append(str(Path(__file__).parent / "app"))

try:
    from app.posting import run_batch, post_single, persist_dataframe
    from app import data_io
    import logging
    
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockKijijiBot:
    """Mock bot for testing batch processing without actual Kijiji posting."""
    
    def __init__(self, success_rate=0.7, delay_range=(0.5, 2.0)):
        """
        Initialize mock bot.
        
        Args:
            success_rate: Percentage of posts that should succeed (0.0 to 1.0)
            delay_range: Tuple of (min_delay, max_delay) to simulate posting time
        """
        self.success_rate = success_rate
        self.delay_range = delay_range
        self.post_count = 0
        
    def post_ad(self, record):
        """Simulate posting an ad with configurable success rate and delay."""
        import random
        
        self.post_count += 1
        
        # Simulate posting delay
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
        
        # Determine if this post should succeed
        success = random.random() < self.success_rate
        
        if success:
            return {
                'success': True,
                'message': f'Mock ad posted successfully (Post #{self.post_count})',
                'ad_url': f'https://www.kijiji.ca/v-mock-{record.get("bucket_truck_id", "unknown").lower()}/{random.randint(10000, 99999)}'
            }
        else:
            # Generate various failure scenarios
            failures = [
                'Network timeout during posting',
                'Authentication failed',
                'Rate limit exceeded',
                'Invalid category selection',
                'Image upload failed'
            ]
            error_msg = random.choice(failures)
            
            return {
                'success': False,
                'message': f'Mock posting failed: {error_msg}',
                'ad_url': None
            }


def create_sample_dataframe():
    """Create a sample DataFrame for testing batch processing."""
    sample_data = {
        'bucket_truck_id': [f'BT{i:03d}' for i in range(1, 11)],
        'image_filename': [f'truck{i}.jpg' for i in range(1, 11)],
        'title': [
            'Ford F-550 Bucket Truck - Excellent Condition',
            'Chevrolet Silverado Utility Truck',
            'GMC C7500 Bucket Truck with Recent Service',
            'International 4300 Bucket Truck - Low Miles',
            'Freightliner M2 Utility Vehicle',
            'Ford E-350 Service Truck with Tools',
            'Isuzu NPR Bucket Truck - Diesel',
            'Kenworth T270 Utility Truck',
            'Peterbilt 337 Bucket Truck - Clean Title',
            'Volvo VNL Service Vehicle'
        ],
        'description': [
            'Well-maintained 2018 Ford F-550 bucket truck with 45ft reach.',
            'Reliable utility truck perfect for service calls and maintenance work.',
            'Heavy-duty bucket truck with extensive service history.',
            'Low mileage International with recent hydraulic service.',
            'Commercial-grade Freightliner for heavy utility work.',
            'Ford service truck comes with full tool complement.',
            'Fuel-efficient Isuzu with excellent maintenance records.',
            'Heavy-duty Kenworth built for demanding utility work.',
            'Clean title Peterbilt with comprehensive service history.',
            'European engineering meets American utility needs.'
        ],
        'price': [45000, 38000, 52000, 41000, 35000, 28000, 39000, 48000, 55000, 46000],
        'tags': [
            'ford,bucket,utility,45ft',
            'chevrolet,utility,service,reliable',
            'gmc,bucket,heavy-duty,service',
            'international,bucket,low-miles',
            'freightliner,utility,commercial',
            'ford,service,tools,complete',
            'isuzu,bucket,diesel,efficient',
            'kenworth,utility,heavy-duty',
            'peterbilt,bucket,clean-title',
            'volvo,service,european,utility'
        ],
        'fuel_type': ['diesel'] * 7 + ['gasoline'] * 3,
        'equipment_type': ['bucket truck'] * 10,
        'posting_status': ['pending', '', 'Error: Failed upload', 'pending', 'Posted 2024-01-15', 
                          '', 'pending', 'Error: Validation failed', '', 'pending']
    }
    
    return pd.DataFrame(sample_data)


class ProgressTracker:
    """Demo progress callback handler."""
    
    def __init__(self, show_detailed=True):
        self.show_detailed = show_detailed
        self.last_percentage = 0
        
    def __call__(self, percentage, message):
        """Progress callback function."""
        # Round to nearest 5% for cleaner output
        rounded_percentage = round(percentage / 5) * 5
        
        if self.show_detailed or rounded_percentage != self.last_percentage:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {percentage:5.1f}% - {message}")
            self.last_percentage = rounded_percentage


def demo_batch_new_mode():
    """Demonstrate batch processing with 'new' mode."""
    print("\n" + "="*60)
    print("DEMO: Batch Processing - 'new' mode")
    print("="*60)
    print("This mode only processes records with blank or failed posting_status")
    
    # Create sample data
    df = create_sample_dataframe()
    
    print(f"\nInitial DataFrame status:")
    for idx, row in df.iterrows():
        status = row['posting_status'] if row['posting_status'] else "[blank]"
        print(f"  {row['bucket_truck_id']}: {status}")
    
    # Set up mock bot and progress tracker
    mock_bot = MockKijijiBot(success_rate=0.8, delay_range=(0.1, 0.3))
    progress_tracker = ProgressTracker(show_detailed=True)
    
    print(f"\nStarting batch processing in 'new' mode...")
    print("Expected to process records with blank, 'pending', or 'Error:' status\n")
    
    # Run batch processing
    result = run_batch(
        df=df,
        mode='new',
        bot=mock_bot,
        progress_cb=progress_tracker,
        file_path="demo_batch_output.xlsx"  # For persistence demo
    )
    
    # Display results
    print(f"\n" + "-"*40)
    print("BATCH PROCESSING RESULTS:")
    print("-"*40)
    print(f"Success: {result['success']}")
    print(f"Total records processed: {result['total_records']}")
    print(f"Successful posts: {result['successful_posts']}")
    print(f"Failed posts: {result['failed_posts']}")
    print(f"Skipped records: {result['skipped_records']}")
    print(f"Summary: {result['message']}")
    
    print(f"\nFinal DataFrame status:")
    for idx, row in df.iterrows():
        status = row['posting_status'] if row['posting_status'] else "[blank]"
        print(f"  {row['bucket_truck_id']}: {status}")


def demo_batch_all_mode():
    """Demonstrate batch processing with 'all' mode."""
    print("\n" + "="*60)
    print("DEMO: Batch Processing - 'all' mode")
    print("="*60)
    print("This mode processes ALL records in the DataFrame")
    
    # Create smaller sample for 'all' mode demo
    sample_data = {
        'bucket_truck_id': ['BT001', 'BT002', 'BT003'],
        'image_filename': ['truck1.jpg', 'truck2.jpg', 'truck3.jpg'],
        'title': [
            'Ford F-550 Bucket Truck',
            'Chevrolet Utility Truck', 
            'GMC Service Vehicle'
        ],
        'description': [
            'Excellent condition Ford bucket truck.',
            'Reliable Chevrolet utility vehicle.',
            'Well-maintained GMC service truck.'
        ],
        'price': [45000, 38000, 52000],
        'tags': ['ford,bucket', 'chevrolet,utility', 'gmc,service'],
        'fuel_type': ['diesel', 'gasoline', 'diesel'],
        'equipment_type': ['bucket truck', 'utility truck', 'service truck'],
        'posting_status': ['Posted 2024-01-10', 'pending', '']
    }
    
    df = pd.DataFrame(sample_data)
    
    print(f"\nInitial DataFrame status:")
    for idx, row in df.iterrows():
        status = row['posting_status'] if row['posting_status'] else "[blank]"
        print(f"  {row['bucket_truck_id']}: {status}")
    
    # Set up mock bot and progress tracker
    mock_bot = MockKijijiBot(success_rate=0.6, delay_range=(0.2, 0.5))
    progress_tracker = ProgressTracker(show_detailed=True)
    
    print(f"\nStarting batch processing in 'all' mode...")
    print("Expected to process ALL records regardless of current status\n")
    
    # Run batch processing
    result = run_batch(
        df=df,
        mode='all',
        bot=mock_bot,
        progress_cb=progress_tracker
    )
    
    # Display results
    print(f"\n" + "-"*40)
    print("BATCH PROCESSING RESULTS:")
    print("-"*40)
    print(f"Success: {result['success']}")
    print(f"Total records processed: {result['total_records']}")
    print(f"Successful posts: {result['successful_posts']}")
    print(f"Failed posts: {result['failed_posts']}")
    print(f"Summary: {result['message']}")
    
    print(f"\nFinal DataFrame status:")
    for idx, row in df.iterrows():
        status = row['posting_status'] if row['posting_status'] else "[blank]"
        print(f"  {row['bucket_truck_id']}: {status}")


def demo_error_handling():
    """Demonstrate error handling in batch processing."""
    print("\n" + "="*60)
    print("DEMO: Error Handling")
    print("="*60)
    print("Testing batch processing with various error scenarios")
    
    # Test invalid mode
    print("\n1. Testing invalid mode:")
    df = create_sample_dataframe()
    mock_bot = MockKijijiBot()
    
    result = run_batch(df, mode='invalid', bot=mock_bot)
    print(f"   Result: {result['success']}")
    print(f"   Message: {result['message']}")
    
    # Test with failing bot
    print("\n2. Testing with high failure rate bot:")
    failing_bot = MockKijijiBot(success_rate=0.1, delay_range=(0.05, 0.1))
    
    # Use small dataset
    small_df = df.head(3).copy()
    small_df['posting_status'] = ['pending', '', 'pending']
    
    result = run_batch(small_df, mode='new', bot=failing_bot)
    print(f"   Total processed: {result['total_records']}")
    print(f"   Successful: {result['successful_posts']}")
    print(f"   Failed: {result['failed_posts']}")
    print(f"   Summary: {result['message']}")


def demo_persistence():
    """Demonstrate file persistence functionality."""
    print("\n" + "="*60)
    print("DEMO: File Persistence")
    print("="*60)
    print("Testing spreadsheet persistence during batch processing")
    
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available - skipping persistence demo")
        return
    
    # Create test file path
    test_file = Path("demo_batch_persistence.xlsx")
    
    try:
        # Create sample data
        df = create_sample_dataframe().head(5)  # Smaller dataset for demo
        df['posting_status'] = ['pending'] * 5  # All pending for processing
        
        print(f"\nCreating test file: {test_file}")
        
        # Save initial state
        if data_io:
            data_io.save_inventory(df, test_file)
            print(f"Initial spreadsheet saved with {len(df)} records")
        
        # Mock bot with medium success rate
        mock_bot = MockKijijiBot(success_rate=0.6, delay_range=(0.1, 0.2))
        
        # Progress callback that shows persistence points
        def persistence_progress(percentage, message):
            if "Persisting spreadsheet" in message or percentage == 100.0:
                print(f"[PERSISTENCE] {percentage:5.1f}% - {message}")
            elif int(percentage) % 20 == 0:  # Show every 20%
                print(f"[PROGRESS] {percentage:5.1f}% - {message}")
        
        print(f"\nRunning batch processing with file persistence...")
        
        # Run batch with persistence
        result = run_batch(
            df=df,
            mode='all',
            bot=mock_bot,
            progress_cb=persistence_progress,
            file_path=test_file
        )
        
        print(f"\nBatch processing completed:")
        print(f"  File: {test_file}")
        print(f"  Exists: {test_file.exists()}")
        if test_file.exists():
            print(f"  Size: {test_file.stat().st_size} bytes")
        
        print(f"  Results: {result['successful_posts']} successful, {result['failed_posts']} failed")
        
    except Exception as e:
        print(f"Persistence demo failed: {e}")
    
    finally:
        # Clean up test file
        if test_file.exists():
            try:
                test_file.unlink()
                print(f"\nCleaned up test file: {test_file}")
            except:
                print(f"\nNote: Please manually delete {test_file}")


def main():
    """Main demo function."""
    print("Kijiji Automation - Batch Processing Demo")
    print("=" * 60)
    
    if not DEPENDENCIES_AVAILABLE:
        print("WARNING: Some dependencies not available.")
        print("Demo may have limited functionality.")
        print()
    
    try:
        # Run all demos
        demo_batch_new_mode()
        demo_batch_all_mode()
        demo_error_handling()
        demo_persistence()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED!")
        print("="*60)
        print("\nKey features demonstrated:")
        print("✓ Batch processing with 'new' and 'all' modes")
        print("✓ Progress tracking with callbacks")
        print("✓ Error handling and recovery")
        print("✓ File persistence during processing")
        print("✓ Status tracking and updates")
        
        print(f"\nTo use run_batch in production:")
        print("1. Initialize a real KijijiBot with valid credentials")
        print("2. Load your inventory DataFrame using data_io.load_inventory()")
        print("3. Define a progress callback for UI updates")
        print("4. Call run_batch() with appropriate mode and file path")
        print("5. Handle the returned results for user feedback")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
