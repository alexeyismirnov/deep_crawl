import asyncio
import aiohttp
import ssl
import chardet
import os
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from link_extractor import is_same_domain
from language_detector import is_target_language, detect_chinese_content_patterns

def _validate_decoded_content(html_content, used_encoding, original_encoding):
    """
    Validate that decoded content is reasonable and not corrupted

    Args:
        html_content (str): Decoded HTML content
        used_encoding (str): Encoding used for decoding
        original_encoding (str): Originally detected encoding

    Returns:
        bool: True if content appears valid, False if likely corrupted
    """
    # Basic sanity checks
    if len(html_content) < 100:
        return False

    # Check for reasonable HTML structure
    if not any(tag in html_content.lower() for tag in ['<html', '<head', '<body', '<div', '<p', '<title']):
        return False

    # Check if this appears to be Chinese content based on HTML patterns
    if detect_chinese_content_patterns(html_content):
        # If HTML suggests Chinese content but we're using Russian encoding, it's likely corrupted
        if used_encoding.lower() in ['koi8-r', 'windows-1251', 'cp1251']:
            print(f"⚠️ HTML patterns suggest Chinese content but decoded with {used_encoding} - likely corrupted")
            return False

    # Check for encoding mismatch indicators
    # If original was Chinese but we're using Russian encoding, look for corruption signs
    if (original_encoding and original_encoding.lower().startswith(('gb', 'big5')) and
        used_encoding.lower() in ['koi8-r', 'windows-1251', 'cp1251']):

        # Look for patterns that suggest Chinese content decoded with wrong encoding
        # Chinese characters decoded with Russian encodings often produce specific patterns
        corruption_patterns = [
            r'[А-Я]{10,}',  # Long sequences of uppercase Cyrillic (unusual in normal text)
            r'[а-я]{1}[А-Я]{1}[а-я]{1}[А-Я]{1}',  # Alternating case (corruption indicator)
            r'[Ё-я]{20,}',  # Very long sequences of Cyrillic characters
        ]

        for pattern in corruption_patterns:
            if re.search(pattern, html_content):
                print(f"⚠️ Detected corruption pattern when Chinese content decoded with {used_encoding}")
                return False

    # Check character distribution - normal text shouldn't have too many control characters
    control_chars = sum(1 for c in html_content if ord(c) < 32 and c not in '\n\r\t')
    if control_chars > len(html_content) * 0.01:  # More than 1% control characters is suspicious
        return False

    return True

def get_base_url(url):
    """
    Extract the base URL (domain with path up to the last /) from a URL
    
    Args:
        url (str): URL to extract base from
        
    Returns:
        str: Base URL
    """
    parsed = urlparse(url)
    # Get the domain
    domain = f"{parsed.scheme}://{parsed.netloc}"
    
    # If the URL ends with a filename (has a dot in the last part), 
    # remove the filename to get the directory
    path = parsed.path
    if '.' in os.path.basename(path):
        path = os.path.dirname(path)
    
    # Ensure path ends with a slash
    if path and not path.endswith('/'):
        path += '/'
        
    return domain + path

async def fetch_page_with_encoding_detection(url, session):
    """
    Fetch a page with encoding detection
    
    Args:
        url (str): URL to fetch
        session (aiohttp.ClientSession): Session to use for fetching
        
    Returns:
        tuple: (html_content, encoding) or (None, None) if failed
    """
    try:
        async with session.get(url) as response:
            if response.status == 200:
                # Get raw bytes first
                raw_content = await response.read()
                
                # Detect encoding
                detected = chardet.detect(raw_content)
                encoding = detected['encoding']
                confidence = detected['confidence']
                
                print(f"📊 Detected encoding: {encoding} (confidence: {confidence:.2f})")
                
                # Try to decode with detected encoding
                try:
                    html_content = raw_content.decode(encoding)
                    print(f"✅ Retrieved page ({len(html_content)} chars)")
                    return html_content, encoding
                except UnicodeDecodeError as decode_error:
                    print(f"⚠️ Failed to decode with {encoding}, trying fallback encodings...")

                    # Determine appropriate fallback encodings based on initial detection
                    if encoding and encoding.lower().startswith(('gb', 'big5', 'hz')):
                        # For Chinese encodings, try other Chinese encodings first
                        fallback_encodings = ['gbk', 'gb18030', 'big5', 'hz-gb-2312', 'utf-8', 'latin-1']
                    elif encoding and encoding.lower() in ['koi8-r', 'windows-1251', 'cp1251']:
                        # For Russian encodings, try other Russian encodings first
                        fallback_encodings = ['windows-1251', 'koi8-r', 'cp1251', 'utf-8', 'latin-1']
                    else:
                        # General fallback order - prioritize UTF-8 and common encodings
                        fallback_encodings = ['utf-8', 'windows-1251', 'koi8-r', 'gb2312', 'gbk', 'gb18030', 'latin-1']

                    for fallback_encoding in fallback_encodings:
                        if fallback_encoding == encoding:
                            continue  # Skip the encoding that already failed
                        try:
                            html_content = raw_content.decode(fallback_encoding)
                            print(f"✅ Successfully decoded with {fallback_encoding} ({len(html_content)} chars)")

                            # Additional validation: check if the decoded content makes sense
                            # by looking for common HTML patterns and reasonable character distribution
                            if _validate_decoded_content(html_content, fallback_encoding, encoding):
                                return html_content, fallback_encoding
                            else:
                                print(f"⚠️ Decoded content with {fallback_encoding} appears corrupted, trying next encoding...")
                                continue

                        except UnicodeDecodeError:
                            continue
                    
                    print(f"❌ Could not decode content with any encoding")
            else:
                print(f"❌ {url} returned status {response.status}")
    except Exception as e:
        print(f"❌ Error with {url}: {str(e)}")
    
    return None, None

async def fetch_main_page(urls_to_try, config):
    """
    Fetch the main page using aiohttp
    
    Args:
        urls_to_try (list): List of URLs to try
        config (dict): Configuration dictionary
        
    Returns:
        tuple: (html_content, base_url, encoding) or (None, None, None) if failed
    """
    # Set up SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': config['user_agent']
    }
    
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
        timeout=aiohttp.ClientTimeout(total=20),
        headers=headers
    ) as session:
        
        main_html = None
        base_url = None
        encoding = None
        
        for url in urls_to_try:
            try:
                print(f"🔍 Analyzing page structure: {url}")
                html_content, encoding = await fetch_page_with_encoding_detection(url, session)
                
                if html_content:
                    # Check if the page is in the target language
                    if config.get('language') and not is_target_language(html_content, config['language']):
                        print(f"⏭️ Skipping main page: not in target language ({config['language']})")
                        continue
                    
                    main_html = html_content
                    # Extract the base URL correctly
                    base_url = get_base_url(url)
                    print(f"📌 Using base URL: {base_url}")
                    return main_html, base_url, encoding
                
            except Exception as e:
                print(f"❌ Error with {url}: {str(e)}")
        
        print("❌ Could not retrieve main page in target language")
        return None, None, None

async def create_crawler(config):
    """
    Create and configure a web crawler
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        AsyncWebCrawler: Configured web crawler
    """
    browser_config = BrowserConfig(
        headless=config['headless'],
        user_agent=config['user_agent']
    )
    
    crawler = AsyncWebCrawler(config=browser_config)
    return crawler

async def crawl_page(crawler, url, config):
    """
    Crawl a single page using the crawler
    
    Args:
        crawler (AsyncWebCrawler): Configured web crawler
        url (str): URL to crawl
        config (dict): Configuration dictionary
        
    Returns:
        dict: Page result or None if failed
    """
    crawler_config = CrawlerRunConfig(
        delay_before_return_html=config['delay_before_return'],
        page_timeout=config['page_timeout']
    )
    
    try:
        result = await crawler.arun(
            url=url,
            config=crawler_config
        )
        
        if result.success:
            # Check if the page is in the target language
            # Use more lenient language detection for frames (they often have minimal text)
            is_frame_url = 'frame' in url.lower() or any(frame_indicator in url.lower() for frame_indicator in ['nav', 'menu', 'title'])
            min_text_length = 20 if is_frame_url else 50
            if config.get('language') and not is_target_language(result.html, config['language'], min_text_length, is_frame=is_frame_url):
                print(f"⏭️ Skipping page: not in target language ({config['language']})")
                return None

            return {
                'url': url,
                'html': result.html,
                'cleaned_html': result.cleaned_html,
                'title': result.metadata.get('title', 'No title'),
                'success': True
            }
        else:
            print(f"❌ Failed to crawl {url}: {result.error_message}")
            return None
    except Exception as e:
        print(f"❌ Exception while crawling {url}: {str(e)}")
        return None

async def fetch_page_with_frames(url, base_url, config):
    """
    Fetch a page and handle frames if present
    
    Args:
        url (str): URL to fetch
        base_url (str): Base URL of the site
        config (dict): Configuration dictionary
        
    Returns:
        dict: Page result with frames or None if failed
    """
    # Set up SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': config['user_agent']
    }
    
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
        timeout=aiohttp.ClientTimeout(total=20),
        headers=headers
    ) as session:
        
        # First try to fetch the page directly
        html_content, encoding = await fetch_page_with_encoding_detection(url, session)
        
        if not html_content:
            return None
        
        # Check if the page is in the target language
        # Use more lenient language detection for frames (they often have minimal text)
        is_frame_url = 'frame' in url.lower() or any(frame_indicator in url.lower() for frame_indicator in ['nav', 'menu', 'title'])
        min_text_length = 20 if is_frame_url else 50
        if config.get('language') and not is_target_language(html_content, config['language'], min_text_length, is_frame=is_frame_url):
            print(f"⏭️ Skipping page: not in target language ({config['language']})")
            return None
        
        # Check if the page has frames
        soup = BeautifulSoup(html_content, 'html.parser')
        frames = soup.find_all(['frame', 'iframe'])
        
        if frames:
            print(f"🔍 Found {len(frames)} frames in {url}")
            
            # Create a crawler to handle frames
            async with await create_crawler(config) as crawler:
                frame_contents = []
                
                # Get the correct base URL for this page
                page_base_url = get_base_url(url)
                print(f"📌 Using page base URL for frames: {page_base_url}")
                
                for i, frame in enumerate(frames):
                    src = frame.get('src', '')
                    if src and not src.startswith('javascript:') and src != 'about:blank':
                        # Build absolute URL correctly using urljoin
                        frame_url = urljoin(page_base_url, src)
                        print(f"🔗 Frame source: {src} -> {frame_url}")
                        
                        # Skip external domains
                        if not is_same_domain(frame_url, base_url):
                            print(f"⏭️ Skipping external frame: {frame_url}")
                            continue
                        
                        print(f"🔄 Accessing frame {i+1} in {url}: {frame_url}")
                        
                        # Crawl the frame
                        frame_result = await crawl_page(crawler, frame_url, config)
                        
                        if frame_result:
                            frame_name = frame.get('name', f'frame_{i+1}')
                            frame_contents.append({
                                'number': i+1,
                                'name': frame_name,
                                'url': frame_url,
                                'content': frame_result['cleaned_html'],
                                'html': frame_result['html'],
                                'title': frame_result['title']
                            })
                
                # Combine frame contents
                combined_content = f"<h1>Page with {len(frames)} frames</h1>\n\n"
                for frame in frame_contents:
                    combined_content += f"<h2>Frame {frame['number']}: {frame['name']}</h2>\n"
                    combined_content += f"<div class='frame-content'>{frame['content']}</div>\n\n"
                
                # Get title from the main page or first frame
                title = soup.find('title')
                title_text = title.get_text().strip() if title else (
                    frame_contents[0]['title'] if frame_contents else "No title"
                )
                
                return {
                    'url': url,
                    'html': html_content,
                    'cleaned_html': combined_content,
                    'title': title_text,
                    'has_frames': True,
                    'frames': frame_contents,
                    'encoding': encoding,
                    'success': True
                }
        else:
            # No frames, return the page as is
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"
            
            return {
                'url': url,
                'html': html_content,
                'cleaned_html': html_content,  # No cleaning for now
                'title': title_text,
                'has_frames': False,
                'encoding': encoding,
                'success': True
            }

def extract_frames(html):
    """
    Extract frames from HTML
    
    Args:
        html (str): HTML content
        
    Returns:
        list: List of frame elements
    """
    soup = BeautifulSoup(html, 'html.parser')
    frames = soup.find_all(['frame', 'iframe'])
    
    print(f"\n🔍 Frame structure analysis:")
    print(f"Total frames found: {len(frames)}")
    
    return frames