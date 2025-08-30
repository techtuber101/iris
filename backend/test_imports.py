#!/usr/bin/env python3
"""
Quick test script to verify imports work correctly after renaming api.py to app_main.py
"""

def test_imports():
    """Test that the api.share_routes module can be imported correctly."""
    try:
        from api.share_routes import router as share_routes
        print("✓ Successfully imported api.share_routes")
        print(f"✓ Router type: {type(share_routes)}")
        return True
    except Exception as e:
        print(f"✗ Failed to import api.share_routes: {e}")
        return False

if __name__ == "__main__":
    print("Testing imports after api.py -> app_main.py rename...")
    success = test_imports()
    if success:
        print("\n✅ All imports successful!")
    else:
        print("\n❌ Import test failed!")
        exit(1)
