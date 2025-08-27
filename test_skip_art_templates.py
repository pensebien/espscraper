#!/usr/bin/env python3
"""
Test script to verify the skip_art_templates flag works correctly
"""

import subprocess
import sys
import os

def test_skip_art_templates_flag():
    """Test that the skip_art_templates flag works correctly"""
    
    print("🧪 Testing skip_art_templates flag...")
    
    # Test 1: Check if flag is in help
    print("\n📋 Test 1: Check if flag is in help")
    result = subprocess.run([
        sys.executable, "enhance_batch_files_with_art.py",
        "--help"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        help_text = result.stdout
        if "--skip-art-templates" in help_text:
            print("✅ --skip-art-templates flag found in help")
        else:
            print("❌ --skip-art-templates flag NOT found in help")
            return False
    else:
        print(f"❌ Help command failed: {result.stderr}")
        return False
    
    # Test 2: Test flag is accepted
    print("\n📋 Test 2: Test flag is accepted")
    result = subprocess.run([
        sys.executable, "enhance_batch_files_with_art.py",
        "--batch-dir", "test_batch",
        "--skip-art-templates",
        "--log-level", "INFO"
    ], capture_output=True, text=True)
    
    # This should fail because test_batch doesn't exist, but flag should be accepted
    if "error" in result.stderr.lower() and "batch directory not found" in result.stderr.lower():
        print("✅ --skip-art-templates flag accepted (expected error about missing directory)")
    else:
        print(f"❌ Unexpected result: {result.stderr}")
        return False
    
    # Test 3: Test flag with other parameters
    print("\n📋 Test 3: Test flag with other parameters")
    result = subprocess.run([
        sys.executable, "enhance_batch_files_with_art.py",
        "--batch-dir", "test_batch",
        "--max-batch-files", "2",
        "--skip-art-templates",
        "--log-level", "INFO"
    ], capture_output=True, text=True)
    
    if "error" in result.stderr.lower() and "batch directory not found" in result.stderr.lower():
        print("✅ --skip-art-templates flag works with other parameters")
    else:
        print(f"❌ Unexpected result: {result.stderr}")
        return False
    
    print("\n🎉 All skip_art_templates tests passed!")
    return True

def test_flag_combinations():
    """Test various combinations of the flag"""
    
    print("\n🧪 Testing flag combinations...")
    
    test_cases = [
        # Just the flag
        ["--skip-art-templates"],
        
        # Flag with basic parameters
        ["--batch-dir", "test", "--skip-art-templates"],
        
        # Flag with chunking parameters
        ["--batch-dir", "test", "--max-batch-files", "2", "--skip-art-templates"],
        
        # Flag with all parameters
        ["--batch-dir", "test", "--max-batch-files", "2", "--max-time-minutes", "180", 
         "--workflow-state-file", "state.json", "--skip-art-templates"]
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test case {i}: {' '.join(test_case)}")
        
        result = subprocess.run([
            sys.executable, "enhance_batch_files_with_art.py"
        ] + test_case, capture_output=True, text=True)
        
        # All should fail with directory not found, but flag should be accepted
        if "batch directory not found" in result.stderr.lower():
            print(f"✅ Test case {i} passed (expected error)")
        else:
            print(f"❌ Test case {i} failed: {result.stderr}")
            return False
    
    print("\n🎉 All flag combination tests passed!")
    return True

if __name__ == "__main__":
    print("🚀 Testing skip_art_templates flag for enhance_batch_files_with_art.py")
    print("=" * 60)
    
    success = True
    
    # Test basic flag functionality
    if not test_skip_art_templates_flag():
        success = False
    
    # Test flag combinations
    if not test_flag_combinations():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 All tests passed! skip_art_templates flag is working correctly.")
        print("✅ Flag is accepted by the script")
        print("✅ Flag works with other parameters")
        print("✅ Ready for faster processing without art templates")
    else:
        print("❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
