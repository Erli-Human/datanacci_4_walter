"""
Example usage of the post_single function for Kijiji automation.

This script demonstrates how to use the post_single function to post
individual inventory records to Kijiji.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add the app directory to the path for imports
sys.path.append(str(Path(__file__).parent / "app"))

try:
    from app.posting import post_single, post_single_with_df_update
    from app.kijiji_bot import KijijiBot
    from app import data_io
    import pandas as pd
    
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False


def demo_post_single_validation():
    """
    Demonstrate the validation aspects of post_single without requiring a bot.
    """
    print("=== post_single Validation Demo ===")
    
    # Example of a valid record
    valid_record = {
        'bucket_truck_id': 'BT001',
        'image_filename': 'truck1.jpg',
        'title': 'Ford F-550 Bucket Truck - Excellent Condition',
        'description': 'Well-maintained 2018 Ford F-550 bucket truck with 45ft reach. Perfect for utility work, tree service, or electrical maintenance. Low hours, recent service.',
        'price': 45000,
        'tags': 'ford,bucket,truck,utility,aerial',
        'fuel_type': 'diesel',
        'equipment_type': 'bucket truck',
        'posting_status': 'pending'
    }
    
    # Example of an invalid record (missing required fields)
    invalid_record = {
        'bucket_truck_id': 'BT002',
        'image_filename': '',  # Empty image filename
        'title': 'Test',  # Too short title
        'description': 'Short',  # Too short description  
        'price': -1000,  # Invalid price
        'tags': '',
        'fuel_type': 'invalid_fuel',  # Invalid fuel type
        'equipment_type': 'invalid_equipment',  # Invalid equipment type
        'posting_status': 'pending'
    }
    
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available - skipping validation demo")
        return
    
    # Create a mock bot for testing validation (won't actually post)
    class MockBot:
        def post_ad(self, record):
            return {
                'success': True,
                'message': 'Mock posting successful',
                'ad_url': 'https://www.kijiji.ca/v-mock-ad/12345'
            }
    
    mock_bot = MockBot()
    
    # Test valid record
    print("\n1. Testing valid record:")
    print(f"   Record ID: {valid_record['bucket_truck_id']}")
    print(f"   Title: {valid_record['title']}")
    
    try:
        result = post_single(valid_record, mock_bot)
        print(f"   Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"   Message: {result['message']}")
        print(f"   Status Update: {result['status_update']}")
        if result['ad_url']:
            print(f"   Ad URL: {result['ad_url']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test invalid record
    print("\n2. Testing invalid record:")
    print(f"   Record ID: {invalid_record['bucket_truck_id']}")
    print(f"   Title: {invalid_record['title']}")
    
    try:
        result = post_single(invalid_record, mock_bot)
        print(f"   Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"   Message: {result['message']}")
        print(f"   Status Update: {result['status_update']}")
    except Exception as e:
        print(f"   Error: {e}")


def demo_dataframe_workflow():
    """
    Demonstrate how to use post_single with a DataFrame workflow.
    """
    print("\n=== DataFrame Workflow Demo ===")
    
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available - skipping DataFrame demo")
        return
    
    # Create sample DataFrame
    sample_data = {
        'bucket_truck_id': ['BT001', 'BT002', 'BT003'],
        'image_filename': ['truck1.jpg', 'truck2.jpg', 'truck3.jpg'],
        'title': [
            'Ford F-550 Bucket Truck - Excellent Condition',
            'Chevrolet Silverado Utility Truck',
            'GMC C7500 Bucket Truck with Recent Service'
        ],
        'description': [
            'Well-maintained 2018 Ford F-550 bucket truck with 45ft reach.',
            'Reliable utility truck perfect for service calls and maintenance work.',
            'Heavy-duty bucket truck with extensive service history and recent maintenance.'
        ],
        'price': [45000, 38000, 52000],
        'tags': ['ford,bucket,utility', 'chevrolet,utility,service', 'gmc,bucket,heavy-duty'],
        'fuel_type': ['diesel', 'gasoline', 'diesel'],
        'equipment_type': ['bucket truck', 'utility truck', 'bucket truck'],
        'posting_status': ['pending', 'pending', 'pending']
    }
    
    df = pd.DataFrame(sample_data)
    print(f"Created sample DataFrame with {len(df)} records")
    
    # Mock bot for demonstration
    class MockBot:
        def __init__(self):
            self.post_count = 0
            
        def post_ad(self, record):
            self.post_count += 1
            # Simulate different outcomes
            if self.post_count == 1:
                return {
                    'success': True,
                    'message': 'Ad posted successfully',
                    'ad_url': f'https://www.kijiji.ca/v-{record["bucket_truck_id"].lower()}/12345'
                }
            elif self.post_count == 2:
                return {
                    'success': False,
                    'message': 'Posting failed: Network timeout',
                    'ad_url': None
                }
            else:
                return {
                    'success': True,
                    'message': 'Ad posted successfully',
                    'ad_url': f'https://www.kijiji.ca/v-{record["bucket_truck_id"].lower()}/67890'
                }
    
    mock_bot = MockBot()
    
    # Process each record
    print("\nProcessing records:")
    for index in range(len(df)):
        print(f"\n--- Processing Record {index + 1} ---")
        
        try:
            result = post_single_with_df_update(df, index, mock_bot)
            
            print(f"Record ID: {result['record_id']}")
            print(f"Result: {'SUCCESS' if result['success'] else 'FAILED'}")
            print(f"Message: {result['message']}")
            print(f"Status Update: {result['status_update']}")
            
            if result['ad_url']:
                print(f"Ad URL: {result['ad_url']}")
            
        except Exception as e:
            print(f"Error processing record {index}: {e}")
    
    # Show updated DataFrame
    print("\n--- Updated DataFrame Status Column ---")
    for index, row in df.iterrows():
        print(f"{row['bucket_truck_id']}: {row['posting_status']}")


def demo_error_handling():
    """
    Demonstrate error handling in various scenarios.
    """
    print("\n=== Error Handling Demo ===")
    
    if not DEPENDENCIES_AVAILABLE:
        print("Dependencies not available - skipping error handling demo")
        return
    
    # Mock bot that always fails
    class FailingBot:
        def post_ad(self, record):
            return {
                'success': False,
                'message': 'Bot authentication failed: Invalid credentials',
                'ad_url': None
            }
    
    # Mock bot that raises exceptions
    class ExceptionBot:
        def post_ad(self, record):
            raise Exception("Network connection lost during posting")
    
    failing_bot = FailingBot()
    exception_bot = ExceptionBot()
    
    test_record = {
        'bucket_truck_id': 'TEST001',
        'image_filename': 'test.jpg',
        'title': 'Test Record for Error Handling',
        'description': 'This record is used to test error handling scenarios.',
        'price': 25000,
        'tags': 'test,error,handling',
        'fuel_type': 'diesel',
        'equipment_type': 'bucket truck',
        'posting_status': 'pending'
    }
    
    print("\n1. Testing bot failure scenario:")
    try:
        result = post_single(test_record, failing_bot)
        print(f"   Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"   Message: {result['message']}")
        print(f"   Status Update: {result['status_update']}")
    except Exception as e:
        print(f"   Unexpected error: {e}")
    
    print("\n2. Testing bot exception scenario:")
    try:
        result = post_single(test_record, exception_bot)
        print(f"   Result: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"   Message: {result['message']}")
        print(f"   Status Update: {result['status_update']}")
    except Exception as e:
        print(f"   Unexpected error: {e}")


def main():
    """
    Main demo function.
    """
    print("Kijiji Automation - post_single Function Demo")
    print("=" * 50)
    
    demo_post_single_validation()
    demo_dataframe_workflow()
    demo_error_handling()
    
    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nTo use post_single in production:")
    print("1. Initialize a real KijijiBot with valid credentials")
    print("2. Load your inventory DataFrame using data_io.load_inventory()")
    print("3. Call post_single() or post_single_with_df_update() for each record")
    print("4. Save the updated DataFrame using data_io.save_inventory()")


if __name__ == "__main__":
    main()
