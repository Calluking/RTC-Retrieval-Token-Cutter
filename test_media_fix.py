#!/usr/bin/env python
"""Test script to verify the media ordering fix."""
import os
import sys
import django
from django.conf import settings

# Configure Django settings
if not settings.configured:
    settings.configure(
        DEBUG=True,
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        STATIC_URL='/static/',
    )
    django.setup()

from django.forms import Form, CharField
from django.forms.widgets import Widget
import warnings

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
print("Testing the form media...")
print("=" * 60)

# Catch warnings
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    form = MyForm()
    media_js = form.media._js
    print(f"Media JS order: {media_js}")
    print(f"Expected: ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']")
    print(f"Match: {media_js == ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']}")

    # Check if any warnings were emitted
    print(f"\nWarnings emitted: {len(w)}")
    for warning in w:
        print(f"  - {warning.category.__name__}: {warning.message}")

print("=" * 60)

# Test individual merges
from django.forms.widgets import Media

print("\nTesting individual merges:")
print("=" * 60)

# Step 1: ColorPicker + SimpleTextWidget
step1 = Media(js=['color-picker.js']) + Media(js=['text-editor.js'])
print(f"Step 1 (ColorPicker + SimpleTextWidget): {step1._js}")
print(f"  Expected: ['color-picker.js', 'text-editor.js']")

# Step 2: Result + FancyTextWidget
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    step2 = step1 + Media(js=['text-editor.js', 'text-editor-extras.js', 'color-picker.js'])
    print(f"\nStep 2 (Result + FancyTextWidget): {step2._js}")
    print(f"  Expected: ['text-editor.js', 'text-editor-extras.js', 'color-picker.js']")
    print(f"  Warnings: {len(w)}")
    for warning in w:
        print(f"    - {warning.message}")

print("=" * 60)

# Test the test_merge_css_three_way scenario
print("\nTesting merge scenarios from test suite:")
print("=" * 60)

# Test case from test_merge_css_three_way
widget1 = Media(css={'screen': ['a.css']})
widget2 = Media(css={'screen': ['b.css']})
widget3 = Media(css={'all': ['c.css']})
form1 = widget1 + widget2
form2 = widget2 + widget1

print(f"form1: {form1._css}")
print(f"form2: {form2._css}")

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    merged = widget3 + form1 + form2
    print(f"merged: {merged._css}")
    print(f"Expected: {{'screen': ['a.css', 'b.css'], 'all': ['c.css']}}")
    print(f"Warnings: {len(w)}")
    for warning in w:
        print(f"  - {warning.message}")
