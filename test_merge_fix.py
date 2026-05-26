#!/usr/bin/env python
"""Test the merge fix directly."""
import warnings
import sys
import os

# Set up the path to import Django
sys.path.insert(0, os.path.dirname(__file__))

# Import Media class
from django.forms.widgets import Media, MediaOrderConflictWarning

print("Testing Media.merge() fix")
print("=" * 60)

# Test 1: merge([1, 2], [2, 1]) - should warn
print("\nTest 1: merge([1, 2], [2, 1]) - should warn")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    result = Media.merge([1, 2], [2, 1])
    media_warnings = [warning for warning in w if issubclass(warning.category, MediaOrderConflictWarning)]

    print(f"  Result: {result}")
    print(f"  Expected: [1, 2]")
    print(f"  Warnings emitted: {len(media_warnings)}")
    if media_warnings:
        print("  ✓ Warning emitted as expected")
    else:
        print("  ✗ Expected a warning")

# Test 2: Three-way merge that was causing false warnings
print("\nTest 2: Three-way merge scenario")
# First: merge(['color-picker.js'], ['text-editor.js'])
result1 = Media.merge(['color-picker.js'], ['text-editor.js'])
print(f"  Step 1: merge(['color-picker.js'], ['text-editor.js'])")
print(f"    Result: {result1}")

# Then: merge result with ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    result2 = Media.merge(result1, ['text-editor.js', 'text-editor-extras.js', 'color-picker.js'])
    media_warnings = [warning for warning in w if issubclass(warning.category, MediaOrderConflictWarning)]

    print(f"  Step 2: merge({result1}, ['text-editor.js', 'text-editor-extras.js', 'color-picker.js'])")
    print(f"    Result: {result2}")
    print(f"    Warnings emitted: {len(media_warnings)}")
    if len(media_warnings) == 0:
        print("    ✓ No false warnings!")
    else:
        print(f"    ✗ Unexpected warning")
        for warning in media_warnings:
            print(f"      {warning.message}")

# Test 3: test_merge test cases
print("\nTest 3: Test cases from test_merge")
test_cases = [
    (([1, 2], [3, 4]), [1, 2, 3, 4]),
    (([1, 2], [2, 3]), [1, 2, 3]),
    (([2, 3], [1, 2]), [1, 2, 3]),
    (([1, 3], [2, 3]), [1, 2, 3]),
    (([1, 2], [1, 3]), [1, 2, 3]),
    (([1, 2], [3, 2]), [1, 3, 2]),
]

all_pass = True
for (list1, list2), expected in test_cases:
    result = Media.merge(list1, list2)
    matches = result == expected
    all_pass = all_pass and matches
    status = "✓" if matches else "✗"
    print(f"  {status} merge({list1}, {list2}) = {result} (expected {expected})")

print("\n" + "=" * 60)
if all_pass:
    print("All tests passed!")
else:
    print("Some tests failed!")
