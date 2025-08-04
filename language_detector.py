"""
Language detection module for the crawler
"""
import re
from langdetect import detect, LangDetectException
from bs4 import BeautifulSoup

def detect_chinese_content_patterns(html_content):
    """
    Detect patterns that suggest Chinese content, even if decoded with wrong encoding

    Args:
        html_content (str): HTML content to analyze

    Returns:
        bool: True if content appears to be Chinese, False otherwise
    """
    # Look for HTML lang attributes indicating Chinese
    if re.search(r'lang\s*=\s*["\']?(zh|chinese)', html_content, re.IGNORECASE):
        return True

    # Look for charset declarations for Chinese encodings
    if re.search(r'charset\s*=\s*["\']?(gb2312|gbk|gb18030|big5)', html_content, re.IGNORECASE):
        return True

    # Look for Chinese-specific HTML entities or Unicode ranges
    chinese_patterns = [
        r'&#x[4-9][0-9a-f]{3};',  # Chinese Unicode range (rough approximation)
        r'&#[2-4][0-9]{4};',      # Chinese decimal entities
        r'&[a-z]+;.*?&#x[4-9]',   # Mixed entities with Chinese
    ]

    for pattern in chinese_patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            return True

    return False

def clean_text_for_detection(html_content):
    """
    Clean HTML content for language detection by:
    1. Removing HTML tags
    2. Removing scripts and style content
    3. Removing special characters and numbers
    4. Keeping only text that's likely to be in a natural language
    5. Detecting potential encoding corruption

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

    # Check for potential encoding corruption patterns
    # These patterns suggest Chinese content decoded with wrong encoding
    corruption_indicators = [
        r'[А-Я]{15,}',  # Very long sequences of uppercase Cyrillic
        r'[Ё-я]{30,}',  # Very long sequences of Cyrillic characters
        r'([А-Я][а-я]){10,}',  # Repetitive alternating case patterns
    ]

    for pattern in corruption_indicators:
        if re.search(pattern, text):
            print(f"⚠️ Potential encoding corruption detected in text")
            # Return empty string to force language detection failure
            return ""

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
            print(f"⚠️ Not enough text for reliable language detection ({len(clean_text)} chars, need {min_text_length})")
            return None

        # Detect language
        language = detect(clean_text)
        print(f"🔍 Detected language: {language}")
        return language

    except LangDetectException as e:
        print(f"❌ Language detection failed: {str(e)}")
        return None

def is_target_language(html_content, target_language, min_text_length=50, is_frame=False):
    """
    Check if HTML content is in the target language

    Args:
        html_content (str): HTML content to check
        target_language (str): Target language code (ISO 639-1)
        min_text_length (int): Minimum text length required for reliable detection
        is_frame (bool): Whether this is a frame/navigation content (more lenient validation)

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
        return True

    # Additional validation for Russian target language
    if target_language == 'ru' and detected_language == 'ru':
        return True

    # For Chinese, handle different variants (zh-cn, zh-tw, etc.)
    if target_language.startswith('zh') and detected_language.startswith('zh'):
        return True

    # Check if the detected language matches the target
    return detected_language == target_language