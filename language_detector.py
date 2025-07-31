"""
Language detection module for the crawler
"""
import re
from langdetect import detect, LangDetectException
from bs4 import BeautifulSoup

def clean_text_for_detection(html_content):
    """
    Clean HTML content for language detection by:
    1. Removing HTML tags
    2. Removing scripts and style content
    3. Removing special characters and numbers
    4. Keeping only text that's likely to be in a natural language
    
    Args:
        html_content (str): HTML content to clean
        
    Returns:
        str: Cleaned text suitable for language detection
    """
    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.extract()
    
    # Get text
    text = soup.get_text()
    
    # Remove URLs, email addresses, and numbers
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'\d+', '', text)
    
    # Remove special characters and extra whitespace
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def detect_language(html_content, min_text_length=50):
    """
    Detect the language of HTML content
    
    Args:
        html_content (str): HTML content to detect language from
        min_text_length (int): Minimum text length required for reliable detection
        
    Returns:
        str or None: ISO 639-1 language code (e.g., 'en', 'zh', 'ru') or None if detection failed
    """
    try:
        # Clean the text for better detection
        clean_text = clean_text_for_detection(html_content)
        
        # Skip if not enough text
        if len(clean_text) < min_text_length:
            print(f"⚠️ Not enough text for reliable language detection ({len(clean_text)} chars)")
            return None
        
        # Detect language
        language = detect(clean_text)
        print(f"🔍 Detected language: {language}")
        return language
    
    except LangDetectException as e:
        print(f"❌ Language detection failed: {str(e)}")
        return None

def is_target_language(html_content, target_language, min_text_length=50):
    """
    Check if HTML content is in the target language
    
    Args:
        html_content (str): HTML content to check
        target_language (str): Target language code (ISO 639-1)
        min_text_length (int): Minimum text length required for reliable detection
        
    Returns:
        bool: True if content is in target language or if target_language is empty, False otherwise
    """
    # If no target language specified, accept all languages
    if not target_language:
        return True
    
    # Detect the language
    detected_language = detect_language(html_content, min_text_length)
    
    # If detection failed, give benefit of the doubt
    if not detected_language:
        print("⚠️ Language detection failed, including page by default")
        return True
    
    # For Chinese, handle different variants (zh-cn, zh-tw, etc.)
    if target_language.startswith('zh') and detected_language.startswith('zh'):
        return True
    
    # Check if the detected language matches the target
    return detected_language == target_language