#!/usr/bin/env python3
"""
Launch script for the Kijiji Posting Assistant Gradio UI.

This script provides an easy way to launch the web-based interface.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from app.ui import launch_ui
    import logging
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('kijiji_ui.log')
        ]
    )
    
    def main():
        """Main launcher function."""
        print("🚛 Kijiji Posting Assistant")
        print("=" * 50)
        print()
        
        # Check dependencies
        missing_deps = []
        
        try:
            import gradio
        except ImportError:
            missing_deps.append("gradio")
        
        try:
            import pandas
        except ImportError:
            missing_deps.append("pandas")
        
        try:
            import selenium
        except ImportError:
            missing_deps.append("selenium")
        
        try:
            import openpyxl
        except ImportError:
            missing_deps.append("openpyxl")
        
        if missing_deps:
            print("❌ Missing required dependencies:")
            for dep in missing_deps:
                print(f"   - {dep}")
            print()
            print("Please install them using:")
            print(f"   pip install {' '.join(missing_deps)}")
            sys.exit(1)
        
        print("✅ All dependencies found!")
        print()
        
        # Launch the UI
        try:
            launch_ui(
                server_name="127.0.0.1",
                server_port=7860,
                share=False
            )
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Error launching UI: {e}")
            sys.exit(1)

    if __name__ == "__main__":
        main()

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure you're running this from the project root directory.")
    sys.exit(1)
