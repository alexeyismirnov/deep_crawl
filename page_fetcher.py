import asyncio
import aiohttp
import ssl
import chardet
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

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
                    
                    # Try common Chinese encodings as fallback
                    fallback_encodings = ['gb2312', 'gbk', 'gb18030', 'utf-8', 'latin-1']
                    
                    for fallback_encoding in fallback_encodings:
                        try:
                            html_content = raw_content.decode(fallback_encoding)
                            print(f"✅ Successfully decoded with {fallback_encoding} ({len(html_content)} chars)")
                            return html_content, fallback_encoding
                        except UnicodeDecodeError:
                            continue
                    
                    print(f"❌ Could not decode content with any encoding")
            else:
                print(f"❌ {url} returned status {response.status}")
    except Exception as e:
        print(f"❌ Error with {url}: {str(e)}")
    
    return None, None

async def fetch_main_page(urls_to_try):
    """
    Fetch the main page using aiohttp
    
    Args:
        urls_to_try (list): List of URLs to try
        
    Returns:
        tuple: (html_content, base_url, encoding) or (None, None, None) if failed
    """
    # Set up SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
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
                    main_html = html_content
                    base_url = url.rstrip('/')
                    return main_html, base_url, encoding
                
            except Exception as e:
                print(f"❌ Error with {url}: {str(e)}")
        
        print("❌ Could not retrieve main page")
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
        
        # Check if the page has frames
        soup = BeautifulSoup(html_content, 'html.parser')
        frames = soup.find_all(['frame', 'iframe'])
        
        if frames:
            print(f"🔍 Found {len(frames)} frames in {url}")
            
            # Create a crawler to handle frames
            async with await create_crawler(config) as crawler:
                frame_contents = []
                
                for i, frame in enumerate(frames):
                    src = frame.get('src', '')
                    if src and not src.startswith('javascript:') and src != 'about:blank':
                        # Build absolute URL
                        if src.startswith('/'):
                            frame_url = f"{base_url}{src}"
                        elif src.startswith('http'):
                            frame_url = src
                        else:
                            # Get the directory of the current URL
                            url_dir = '/'.join(url.split('/')[:-1])
                            frame_url = f"{url_dir}/{src}"
                        
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