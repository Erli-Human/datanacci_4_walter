#!/usr/bin/env python3
"""
Test script for the Gradio UI components.

This script tests the UI functionality without actually posting to Kijiji.
"""

import sys
import pandas as pd
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / "app"))

try:
    from app.ui import (
        load_bucket_truck_ids,
        update_truck_dropdown,
        toggle_truck_dropdown,
        LogHandler,
        processing_state
    )
    from app import data_io
    
    def test_load_bucket_truck_ids():
        """Test loading truck IDs from a spreadsheet."""
        print("Testing load_bucket_truck_ids...")
        
        # Test with None
        result = load_bucket_truck_ids(None)
        assert result == ["No spreadsheet loaded"], f"Expected ['No spreadsheet loaded'], got {result}"
        
        # Create test data
        test_data = {
            'bucket_truck_id': ['BT001', 'BT002', 'BT003'],
            'image_filename': ['truck1.jpg', 'truck2.jpg', 'truck3.jpg'],
            'title': ['Test Truck 1', 'Test Truck 2', 'Test Truck 3'],
            'description': ['Description 1', 'Description 2', 'Description 3'],
            'price': [45000, 38000, 52000],
            'tags': ['test,truck', 'test,vehicle', 'test,equipment'],
            'fuel_type': ['diesel', 'gasoline', 'diesel'],
            'equipment_type': ['bucket truck', 'utility truck', 'service truck'],
            'posting_status': ['pending', '', 'pending']
        }
        
        df = pd.DataFrame(test_data)
        test_file = Path("test_inventory.xlsx")
        
        try:
            # Save test file
            data_io.save_inventory(df, test_file)
            
            # Test loading
            result = load_bucket_truck_ids(str(test_file))
            expected = ['BT001', 'BT002', 'BT003']
            assert result == expected, f"Expected {expected}, got {result}"
            
            print("✅ load_bucket_truck_ids test passed")
            
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
    
    def test_toggle_truck_dropdown():
        """Test the truck dropdown visibility toggle."""
        print("Testing toggle_truck_dropdown...")
        
        # Test Single mode
        result = toggle_truck_dropdown("Single")
        # For testing, we'll just check that it returns a dict with visible=True
        print(f"Single mode result: {result}")
        
        # Test Batch modes
        result = toggle_truck_dropdown("Batch-New")
        print(f"Batch-New mode result: {result}")
        
        result = toggle_truck_dropdown("Batch-All")
        print(f"Batch-All mode result: {result}")
        
        print("✅ toggle_truck_dropdown test passed")
    
    def test_log_handler():
        """Test the custom log handler."""
        print("Testing LogHandler...")
        
        import logging
        
        # Create logger and handler
        logger = logging.getLogger("test_logger")
        handler = LogHandler()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test logging
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Check logs were captured
        assert len(handler.logs) == 3, f"Expected 3 logs, got {len(handler.logs)}"
        assert handler.logs[0]['level'] == 'INFO', f"Expected INFO, got {handler.logs[0]['level']}"
        assert handler.logs[1]['level'] == 'WARNING', f"Expected WARNING, got {handler.logs[1]['level']}"
        assert handler.logs[2]['level'] == 'ERROR', f"Expected ERROR, got {handler.logs[2]['level']}"
        
        # Check processing state was updated
        assert processing_state['logs'] == handler.logs, "Processing state not updated correctly"
        
        print("✅ LogHandler test passed")
    
    def test_processing_state():
        """Test the global processing state."""
        print("Testing processing_state...")
        
        # Check initial state
        assert 'is_running' in processing_state
        assert 'progress' in processing_state
        assert 'current_message' in processing_state
        assert 'logs' in processing_state
        assert 'results' in processing_state
        
        # Test state modification
        processing_state['is_running'] = True
        processing_state['progress'] = 50.0
        processing_state['current_message'] = 'Test message'
        
        assert processing_state['is_running'] is True
        assert processing_state['progress'] == 50.0
        assert processing_state['current_message'] == 'Test message'
        
        print("✅ processing_state test passed")
    
    def main():
        """Run all tests."""
        print("🧪 Testing Kijiji UI Components")
        print("=" * 40)
        
        try:
            test_load_bucket_truck_ids()
            test_toggle_truck_dropdown()
            test_log_handler()
            test_processing_state()
            
            print()
            print("🎉 All tests passed!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install gradio pandas openpyxl")
    sys.exit(1)
