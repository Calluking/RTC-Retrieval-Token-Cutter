#!/usr/bin/env python
"""Test that the false warning issue is fixed."""
import os
import sys
import django
from django.conf import settings
import warnings

# Configure Django
if not settings.configured:
    settings.configure(
        DEBUG=True,
        INSTALLED_APPS=[],
        DATABASES={},
        STATIC_URL='/static/',
    )

from django.forms import Form, CharField
from django.forms.widgets import Widget

class ColorPicker(Widget):
    class Media:
        js = ['color-picker.js']

class SimpleTextWidget(Widget):
    class Media:
        js = ['text-editor.js']

class FancyTextWidget(Widget):
    class Media:
        js = ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']

class MyForm(Form):
    background_color = CharField(widget=ColorPicker())
    intro = CharField(widget=SimpleTextWidget())
    body = CharField(widget=FancyTextWidget())

# Test the form media
print("Testing the original issue scenario...")
print("=" * 60)

# Catch warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    form = MyForm()
    media_js = form.media._js

    # Check if MediaOrderConflictWarning was emitted
    from django.forms.widgets import MediaOrderConflictWarning
    media_warnings = [warning for warning in w if issubclass(warning.category, MediaOrderConflictWarning)]

    print(f"Media JS: {media_js}")
    print(f"Expected: ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']")
    print(f"        or similar respecting dependencies")
    print()
    print(f"MediaOrderConflictWarning emitted: {len(media_warnings) > 0}")

    if media_warnings:
        for warning in media_warnings:
            print(f"  Warning: {warning.message}")
    else:
        print("  ✓ No false warnings!")

print("=" * 60)

# Test merge([1, 2], [2, 1]) which SHOULD warn
print("\nTesting merge([1, 2], [2, 1]) - should warn...")
from django.forms.widgets import Media

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    result = Media.merge([1, 2], [2, 1])
    media_warnings = [warning for warning in w if issubclass(warning.category, MediaOrderConflictWarning)]

    print(f"Result: {result}")
    print(f"Expected: [1, 2]")
    print(f"MediaOrderConflictWarning emitted: {len(media_warnings) > 0}")

    if media_warnings:
        print(f"  ✓ Warning emitted as expected:")
        for warning in media_warnings:
            print(f"    {warning.message}")
    else:
        print("  ✗ Expected a warning but got none!")
