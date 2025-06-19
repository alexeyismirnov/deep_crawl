import asyncio
import aiohttp
import ssl
import chardet
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

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
                            main_html = raw_content.decode(encoding)
                            base_url = url.rstrip('/')
                            print(f"✅ Retrieved main page ({len(main_html)} chars)")
                            return main_html, base_url, encoding
                        except UnicodeDecodeError as decode_error:
                            print(f"⚠️ Failed to decode with {encoding}, trying fallback encodings...")
                            
                            # Try common Chinese encodings as fallback
                            fallback_encodings = ['gb2312', 'gbk', 'gb18030', 'utf-8', 'latin-1']
                            
                            for fallback_encoding in fallback_encodings:
                                try:
                                    main_html = raw_content.decode(fallback_encoding)
                                    base_url = url.rstrip('/')
                                    print(f"✅ Successfully decoded with {fallback_encoding} ({len(main_html)} chars)")
                                    return main_html, base_url, fallback_encoding
                                except UnicodeDecodeError:
                                    continue
                            
                            print(f"❌ Could not decode content with any encoding")
                    else:
                        print(f"❌ {url} returned status {response.status}")
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