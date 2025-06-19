import os
import re
import urllib.parse
from datetime import datetime

def create_output_directory(output_dir):
    """
    Create the output directory if it doesn't exist
    
    Args:
        output_dir (str): Path to the output directory
        
    Returns:
        str: Absolute path to the output directory
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    else:
        print(f"📁 Using existing output directory: {output_dir}")
    
    return os.path.abspath(output_dir)

def create_safe_filename(url, prefix='', max_length=50):
    """
    Create a safe filename from a URL
    
    Args:
        url (str): URL to convert to a filename
        prefix (str): Prefix to add to the filename
        max_length (int): Maximum length of the filename
        
    Returns:
        str: Safe filename
    """
    # Parse the URL and get the path
    parsed_url = urllib.parse.urlparse(url)
    path_part = parsed_url.path.rstrip('/')
    
    # Use 'index' if the path is empty
    if not path_part:
        path_part = 'index'
    
    # Get the last part of the path
    filename = path_part.split('/')[-1]
    
    # Replace non-alphanumeric characters with underscores
    safe_name = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Add prefix if provided
    if prefix:
        safe_name = f"{prefix}_{safe_name}"
    
    # Limit the length
    if len(safe_name) > max_length:
        extension = os.path.splitext(safe_name)[1]
        safe_name = safe_name[:max_length-len(extension)] + extension
    
    return safe_name

def get_timestamp():
    """
    Get the current timestamp in a format suitable for filenames
    
    Returns:
        str: Current timestamp
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_formatted_datetime():
    """
    Get the current datetime in a human-readable format
    
    Returns:
        str: Formatted datetime
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")