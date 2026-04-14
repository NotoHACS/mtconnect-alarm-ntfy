#!/usr/bin/env python3
"""
Update script for MTConnect Alarm Monitor.
Called by update.bat. Downloads latest from GitHub and updates files.
"""

import urllib.request
import zipfile
import os
import shutil
import sys
import argparse


def download_zip(url, output_path):
    """Download ZIP from GitHub."""
    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"Download successful: {url}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def extract_zip(zip_path, extract_path):
    """Extract ZIP file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Extraction successful to {extract_path}")
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def update_files(source_dir):
    """Copy updated files from source to current directory."""
    files_to_update = [
        'main.py',
        'poller.py',
        'models.py',
        'notifier.py',
        'config.py',
        'config_defaults.py',
        'SPEC.md',
        'alarm_db.json',
        'requirements.txt',
        'update.bat',
        'update_helper.py',  # Also update this script
    ]
    
    updated_count = 0
    for file in files_to_update:
        src = os.path.join(source_dir, file)
        if os.path.exists(src):
            try:
                shutil.copy2(src, file)
                print(f"Updated: {file}")
                updated_count += 1
            except Exception as e:
                print(f"Failed to update {file}: {e}")
        else:
            print(f"Not found in update: {file} (skipped)")
    
    return updated_count


def main():
    parser = argparse.ArgumentParser(description='Update MTConnect Alarm Monitor')
    parser.add_argument('branch', nargs='?', default='master', help='Git branch to update from')
    args = parser.parse_args()
    
    branch = args.branch
    zip_url = f"https://github.com/NotoHACS/mtconnect-alarm-monitor-classic/archive/refs/heads/{branch}.zip"
    temp_zip = "update_temp.zip"
    extract_path = "update_temp"
    
    print(f"Updating from branch: {branch}")
    print(f"URL: {zip_url}")
    
    # Clean up any old files
    if os.path.exists(temp_zip):
        os.remove(temp_zip)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    
    # Download
    print("\nDownloading...")
    if not download_zip(zip_url, temp_zip):
        return 1
    
    # Extract
    print("\nExtracting...")
    if not extract_zip(temp_zip, extract_path):
        return 1
    
    # Find extracted folder
    extracted_dirs = [d for d in os.listdir(extract_path) if os.path.isdir(os.path.join(extract_path, d))]
    if not extracted_dirs:
        print("No extracted directory found!")
        return 1
    
    source_dir = os.path.join(extract_path, extracted_dirs[0])
    
    # Update files
    print("\nUpdating files...")
    updated_count = update_files(source_dir)
    print(f"\nUpdated {updated_count} files")
    
    # Cleanup
    print("\nCleaning up...")
    shutil.rmtree(extract_path)
    os.remove(temp_zip)
    
    print("Update complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
