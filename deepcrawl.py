import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import aiohttp
import ssl
from bs4 import BeautifulSoup
import chardet
import os
from datetime import datetime
import re
import configparser
import urllib.parse

async def crawl_orthodox_and_save():
    """
    Enhanced version that saves crawled content to markdown files
    with support for depth=1 crawling
    """
    print("🚀 Starting Orthodox website crawl with markdown export...")
    
    # Load configuration
    config = configparser.ConfigParser()
    config.read('crawler_config.ini')
    
    # Get settings from config
    max_depth = int(config.get('CRAWL_SETTINGS', 'MAX_DEPTH', fallback='1'))
    max_links_per_page = int(config.get('CRAWL_SETTINGS', 'MAX_LINKS_PER_PAGE', fallback='15'))
    output_dir = config.get('OUTPUT_SETTINGS', 'OUTPUT_DIR', fallback='output')
    skip_extensions = config.get('FILTERING', 'SKIP_EXTENSIONS', fallback='.pdf,.doc,.docx').split(',')
    skip_patterns = config.get('FILTERING', 'SKIP_PATTERNS', fallback='/admin/,/login/').split(',')
    
    print(f"📋 Configuration:")
    print(f"   - Max depth: {max_depth}")
    print(f"   - Max links per page: {max_links_per_page}")
    print(f"   - Output directory: {output_dir}")
    
    # Create output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"📁 Created output directory: {output_dir}")
    else:
        print(f"📁 Using existing output directory: {output_dir}")
    
    # First, get the page structure using aiohttp
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    urls_to_try = ["https://orthodox.cn/", "http://orthodox.cn/"]
    
    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
        timeout=aiohttp.ClientTimeout(total=20),
        headers=headers
    ) as session:
        
        main_html = None
        base_url = None
        
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
                            break
                        except UnicodeDecodeError as decode_error:
                            print(f"⚠️ Failed to decode with {encoding}, trying fallback encodings...")
                            
                            # Try common Chinese encodings as fallback
                            fallback_encodings = ['gb2312', 'gbk', 'gb18030', 'utf-8', 'latin-1']
                            decoded = False
                            
                            for fallback_encoding in fallback_encodings:
                                try:
                                    main_html = raw_content.decode(fallback_encoding)
                                    base_url = url.rstrip('/')
                                    print(f"✅ Successfully decoded with {fallback_encoding} ({len(main_html)} chars)")
                                    decoded = True
                                    break
                                except UnicodeDecodeError:
                                    continue
                            
                            if decoded:
                                break
                            else:
                                print(f"❌ Could not decode content with any encoding")
                    else:
                        print(f"❌ {url} returned status {response.status}")
            except Exception as e:
                print(f"❌ Error with {url}: {str(e)}")
        
        if not main_html:
            print("❌ Could not retrieve main page")
            return None
        
        # Parse frame structure
        soup = BeautifulSoup(main_html, 'html.parser')
        frames = soup.find_all(['frame', 'iframe'])
        
        print(f"\n🔍 Frame structure analysis:")
        print(f"Total frames found: {len(frames)}")
        
        # Save main page analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        main_md_path = os.path.join(output_dir, f"00_main_page_analysis_{timestamp}.md")
        
        with open(main_md_path, 'w', encoding='utf-8') as f:
            f.write(f"# Orthodox.cn Main Page Analysis\n\n")
            f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Base URL:** {base_url}\n")
            f.write(f"**Encoding:** {encoding} (confidence: {confidence:.2f})\n\n")
            
            # Extract title and meta info
            title = soup.find('title')
            if title:
                f.write(f"**Title:** {title.get_text().strip()}\n\n")
            
            # Extract keywords
            keywords_meta = soup.find('meta', {'name': 'keywords'})
            if keywords_meta:
                keywords = keywords_meta.get('content', '')
                f.write(f"**Keywords:** {keywords}\n\n")
            
            f.write(f"## Frame Structure\n\n")
            f.write(f"Total frames found: **{len(frames)}**\n\n")
            
            if frames:
                f.write(f"| Frame # | Name | Source | Attributes |\n")
                f.write(f"|---------|------|--------|-----------|\n")
                for i, frame in enumerate(frames):
                    src = frame.get('src', 'No source')
                    name = frame.get('name', f'unnamed_frame_{i}')
                    attrs = ', '.join([f"{k}={v}" for k, v in frame.attrs.items() if k not in ['src', 'name']])
                    f.write(f"| {i+1} | {name} | `{src}` | {attrs} |\n")
            
            f.write(f"\n## Raw HTML Structure\n\n")
            f.write(f"```html\n{main_html}\n```\n")
        
        print(f"💾 Saved main page analysis to: {main_md_path}")
        
        # Now crawl frames with Crawl4AI
        browser_config = BrowserConfig(
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        crawler_config = CrawlerRunConfig(
            delay_before_return_html=2.0,
            page_timeout=15000
        )
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            successful_frames = []
            all_crawled_pages = []  # Track all crawled pages
            all_links_to_crawl = []  # Links to crawl for depth=1
            
            # First, crawl the frames from the main page
            if frames:
                for i, frame in enumerate(frames):
                    src = frame.get('src', '')
                    if src and not src.startswith('javascript:') and src != 'about:blank':
                        # Build absolute URL
                        if src.startswith('/'):
                            frame_url = f"{base_url}{src}"
                        elif src.startswith('http'):
                            frame_url = src
                        else:
                            frame_url = f"{base_url}/{src}"
                        
                        print(f"\n🔄 Accessing frame {i+1}: {frame_url}")
                        
                        try:
                            frame_result = await crawler.arun(
                                url=frame_url,
                                config=crawler_config
                            )
                            
                            if frame_result.success:
                                print(f"✅ Frame {i+1} success!")
                                print(f"Content length: {len(frame_result.cleaned_html)}")
                                print(f"Title: {frame_result.metadata.get('title', 'No title')}")
                                
                                # Save frame content to markdown
                                frame_name = frame.get('name', f'frame_{i+1}')
                                safe_name = re.sub(r'[^\w\-_\.]', '_', frame_name)
                                frame_md_path = os.path.join(output_dir, f"{i+1:02d}_{safe_name}_{timestamp}.md")
                                
                                # Extract links from the frame HTML
                                frame_soup = BeautifulSoup(frame_result.html, 'html.parser')
                                frame_links = []
                                
                                # Find all <a> tags with href attributes
                                for a_tag in frame_soup.find_all('a', href=True):
                                    link_url = a_tag['href']
                                    link_text = a_tag.get_text().strip() or link_url
                                    
                                    # Skip javascript: and empty links
                                    if link_url.startswith('javascript:') or not link_url or link_url == '#':
                                        continue
                                    
                                    # Normalize the URL
                                    if not link_url.startswith(('http://', 'https://')):
                                        if link_url.startswith('/'):
                                            link_url = f"{base_url}{link_url}"
                                        else:
                                            # Get the directory of the current frame URL
                                            frame_dir = '/'.join(frame_url.split('/')[:-1])
                                            link_url = f"{frame_dir}/{link_url}"
                                    
                                    # Check if we should skip this URL
                                    should_skip = False
                                    
                                    # Check against skip extensions
                                    for ext in skip_extensions:
                                        if ext and link_url.lower().endswith(ext.lower()):
                                            should_skip = True
                                            break
                                    
                                    # Check against skip patterns
                                    for pattern in skip_patterns:
                                        if pattern and pattern in link_url:
                                            should_skip = True
                                            break
                                    
                                    if not should_skip:
                                        frame_links.append({
                                            'url': link_url,
                                            'text': link_text,
                                            'parent_frame': i+1,
                                            'parent_name': frame_name
                                        })
                                
                                # Find all <area> tags with href attributes (for image maps)
                                for area_tag in frame_soup.find_all('area', href=True):
                                    link_url = area_tag['href']
                                    link_text = area_tag.get('alt', '') or area_tag.get('title', '') or link_url
                                    
                                    # Skip javascript: and empty links
                                    if link_url.startswith('javascript:') or not link_url or link_url == '#' or link_url.lower() == 'nohref':
                                        continue
                                    
                                    # Normalize the URL
                                    if not link_url.startswith(('http://', 'https://')):
                                        if link_url.startswith('/'):
                                            link_url = f"{base_url}{link_url}"
                                        else:
                                            # Get the directory of the current frame URL
                                            frame_dir = '/'.join(frame_url.split('/')[:-1])
                                            link_url = f"{frame_dir}/{link_url}"
                                    
                                    # Check if we should skip this URL
                                    should_skip = False
                                    
                                    # Check against skip extensions
                                    for ext in skip_extensions:
                                        if ext and link_url.lower().endswith(ext.lower()):
                                            should_skip = True
                                            break
                                    
                                    # Check against skip patterns
                                    for pattern in skip_patterns:
                                        if pattern and pattern in link_url:
                                            should_skip = True
                                            break
                                    
                                    if not should_skip:
                                        frame_links.append({
                                            'url': link_url,
                                            'text': link_text,
                                            'parent_frame': i+1,
                                            'parent_name': frame_name
                                        })
                                
                                print(f"🔗 Found {len(frame_links)} links in frame {i+1}")
                                
                                with open(frame_md_path, 'w', encoding='utf-8') as f:
                                    f.write(f"# Frame {i+1}: {frame_name}\n\n")
                                    f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                    f.write(f"**Frame URL:** {frame_url}\n")
                                    f.write(f"**Frame Name:** {frame_name}\n")
                                    f.write(f"**Content Length:** {len(frame_result.cleaned_html)} characters\n")
                                    
                                    title = frame_result.metadata.get('title', '')
                                    if title:
                                        f.write(f"**Page Title:** {title}\n")
                                    
                                    f.write(f"\n## Content\n\n")
                                    f.write(frame_result.cleaned_html)
                                    
                                    # Add links section
                                    if frame_links:
                                        f.write(f"\n\n## Links Found ({len(frame_links)})\n\n")
                                        for link in frame_links:
                                            f.write(f"- [{link['text']}]({link['url']})\n")
                                    
                                    # Add raw HTML section
                                    f.write(f"\n\n## Raw HTML\n\n")
                                    f.write(f"```html\n{frame_result.html}\n```\n")
                                
                                print(f"💾 Saved frame {i+1} to: {frame_md_path}")
                                
                                frame_data = {
                                    'frame_number': i+1,
                                    'name': frame_name,
                                    'url': frame_url,
                                    'content': frame_result.cleaned_html,
                                    'title': frame_result.metadata.get('title', ''),
                                    'links': frame_links,
                                    'file_path': frame_md_path
                                }
                                
                                successful_frames.append(frame_data)
                                all_crawled_pages.append(frame_url)
                                
                                # Add links to our crawl list for depth=1
                                for link in frame_links:
                                    if link['url'] not in all_crawled_pages:
                                        all_links_to_crawl.append(link)
                            else:
                                print(f"❌ Frame {i+1} failed: {frame_result.error_message}")
                                
                        except Exception as e:
                            print(f"❌ Frame {i+1} exception: {str(e)}")
            else:
                # If no frames, extract links from the main page
                print("\n🔍 No frames found, extracting links from main page...")
                main_links = []
                main_soup = BeautifulSoup(main_html, 'html.parser')
                for a_tag in main_soup.find_all('a', href=True):
                    link_url = a_tag['href']
                    link_text = a_tag.get_text().strip() or link_url
                    
                    # Normalize the URL
                    if not link_url.startswith(('http://', 'https://')):
                        if link_url.startswith('/'):
                            link_url = f"{base_url}{link_url}"
                        else:
                            link_url = f"{base_url}/{link_url}"
                    
                    # Check if we should skip this URL
                    should_skip = False
                    for ext in skip_extensions:
                        if ext and link_url.lower().endswith(ext.lower()):
                            should_skip = True
                            break
                    
                    for pattern in skip_patterns:
                        if pattern and pattern in link_url:
                            should_skip = True
                            break
                    
                    if not should_skip and link_url not in all_crawled_pages:
                        main_links.append({
                            'url': link_url,
                            'text': link_text,
                            'parent_frame': 0,
                            'parent_name': 'main_page'
                        })
                
                print(f"Found {len(main_links)} links on main page")
                all_links_to_crawl.extend(main_links[:max_links_per_page])
            
            # Now crawl depth=1 links if max_depth > 0
            if max_depth > 0:
                if all_links_to_crawl:
                    print(f"\n🔄 Starting depth=1 crawl of {len(all_links_to_crawl)} links...")
                    print(f"🔍 First 5 links to crawl: {[link['url'] for link in all_links_to_crawl[:5]]}")
                    
                    # Limit the number of links to crawl if there are too many
                    if len(all_links_to_crawl) > max_links_per_page * 3:
                        print(f"⚠️ Too many links ({len(all_links_to_crawl)}), limiting to {max_links_per_page * 3}")
                        all_links_to_crawl = all_links_to_crawl[:max_links_per_page * 3]
                    
                    depth1_pages = []
                    
                    for i, link_data in enumerate(all_links_to_crawl):
                        link_url = link_data['url']
                        link_text = link_data['text']
                        parent_info = f"(from {link_data['parent_name']})"
                        
                        # Skip if already crawled
                        if link_url in all_crawled_pages:
                            print(f"⏭️ Skipping already crawled: {link_url}")
                            continue
                        
                        print(f"\n🔄 Crawling depth=1 link {i+1}/{len(all_links_to_crawl)}: {link_url} {parent_info}")
                        
                        try:
                            page_result = await crawler.arun(
                                url=link_url,
                                config=crawler_config
                            )
                            
                            if page_result.success:
                                print(f"✅ Link {i+1} success!")
                                print(f"Content length: {len(page_result.cleaned_html)}")
                                print(f"Title: {page_result.metadata.get('title', 'No title')}")
                                
                                # Create a safe filename from the URL
                                parsed_url = urllib.parse.urlparse(link_url)
                                path_part = parsed_url.path.rstrip('/')
                                if not path_part:
                                    path_part = 'index'
                                safe_name = re.sub(r'[^\w\-_\.]', '_', path_part.split('/')[-1])
                                
                                # Save page content to markdown
                                page_md_path = os.path.join(output_dir, f"depth1_{i+1:03d}_{safe_name}_{timestamp}.md")
                                
                                with open(page_md_path, 'w', encoding='utf-8') as f:
                                    title = page_result.metadata.get('title', 'No title')
                                    f.write(f"# {title}\n\n")
                                    f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                    f.write(f"**URL:** {link_url}\n")
                                    f.write(f"**Parent:** {link_data['parent_name']} (Frame {link_data['parent_frame']})\n")
                                    f.write(f"**Link Text:** {link_text}\n")
                                    f.write(f"**Content Length:** {len(page_result.cleaned_html)} characters\n")
                                    
                                    f.write(f"\n## Content\n\n")
                                    f.write(page_result.cleaned_html)
                                    
                                    # Extract links from this page
                                    page_soup = BeautifulSoup(page_result.html, 'html.parser')
                                    page_links = []
                                    
                                    for a_tag in page_soup.find_all('a', href=True):
                                        sub_link_url = a_tag['href']
                                        sub_link_text = a_tag.get_text().strip() or sub_link_url
                                        
                                        # Skip javascript: and empty links
                                        if sub_link_url.startswith('javascript:') or not sub_link_url or sub_link_url == '#':
                                            continue
                                            
                                        # Normalize the URL
                                        if not sub_link_url.startswith(('http://', 'https://')):
                                            if sub_link_url.startswith('/'):
                                                sub_link_url = f"{base_url}{sub_link_url}"
                                            else:
                                                # Get the directory of the current page URL
                                                page_dir = '/'.join(link_url.split('/')[:-1])
                                                sub_link_url = f"{page_dir}/{sub_link_url}"
                                        
                                        page_links.append({
                                            'url': sub_link_url,
                                            'text': sub_link_text
                                        })
                                    
                                    # Add links section if available
                                    if page_links:
                                        f.write(f"\n\n## Links Found ({len(page_links)})\n\n")
                                        for page_link in page_links[:20]:  # Limit to 20 links in the output
                                            f.write(f"- [{page_link['text']}]({page_link['url']})\n")
                                    
                                    # Add raw HTML section
                                    f.write(f"\n\n## Raw HTML\n\n")
                                    f.write(f"```html\n{page_result.html}\n```\n")
                                
                                print(f"💾 Saved depth=1 page to: {page_md_path}")
                                
                                depth1_pages.append({
                                    'number': i+1,
                                    'url': link_url,
                                    'text': link_text,
                                    'title': title,
                                    'content': page_result.cleaned_html,
                                    'parent_frame': link_data['parent_frame'],
                                    'parent_name': link_data['parent_name'],
                                    'file_path': page_md_path
                                })
                                
                                all_crawled_pages.append(link_url)
                            else:
                                print(f"❌ Link {i+1} failed: {page_result.error_message}")
                        
                        except Exception as e:
                            print(f"❌ Link {i+1} exception: {str(e)}")
                
                    # Update the summary with depth=1 pages
                    print(f"\n🎉 Successfully crawled {len(depth1_pages)} depth=1 pages")
                else:
                    depth1_pages = []
                    print("\n⚠️ No links found to crawl at depth=1")
            else:
                depth1_pages = []
                print("\nℹ️ Skipping depth=1 crawl (max_depth=0)")
            
            # Create summary file
            summary_path = os.path.join(output_dir, f"README_{timestamp}.md")
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(f"# Orthodox.cn Crawl Results\n\n")
                f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Base URL:** {base_url}\n")
                f.write(f"**Max Depth:** {max_depth}\n")
                f.write(f"**Total Frames:** {len(frames)}\n")
                f.write(f"**Successfully Crawled Frames:** {len(successful_frames)}\n")
                f.write(f"**Successfully Crawled Depth=1 Pages:** {len(depth1_pages)}\n")
                f.write(f"**Total Pages Crawled:** {len(successful_frames) + len(depth1_pages)}\n\n")
                
                f.write(f"## Files Generated\n\n")
                f.write(f"1. **Main Page Analysis:** `{os.path.basename(main_md_path)}`\n")
                
                # List frame files
                for frame_data in successful_frames:
                    f.write(f"{frame_data['frame_number']+1}. **Frame {frame_data['frame_number']} ({frame_data['name']}):** `{os.path.basename(frame_data['file_path'])}`\n")
                
                # List depth=1 files
                for i, page_data in enumerate(depth1_pages):
                    parent_info = f"from {page_data['parent_name']}"
                    f.write(f"{len(successful_frames)+i+2}. **Depth=1 Page {page_data['number']} ({parent_info}):** `{os.path.basename(page_data['file_path'])}`\n")
                
                f.write(f"\n## Site Structure\n\n")
                f.write(f"**Website:** 中国正教会 (Chinese Orthodox Church)\n\n")
                
                if successful_frames:
                    f.write(f"### Frame Contents\n\n")
                    for frame_data in successful_frames:
                        f.write(f"#### Frame {frame_data['frame_number']}: {frame_data['name']}\n")
                        f.write(f"- **URL:** {frame_data['url']}\n")
                        f.write(f"- **Content Length:** {len(frame_data['content'])} characters\n")
                        if frame_data['title']:
                            f.write(f"- **Title:** {frame_data['title']}\n")
                        f.write(f"- **File:** [{os.path.basename(frame_data['file_path'])}]({os.path.basename(frame_data['file_path'])})\n")
                        
                        # List links from this frame that were crawled
                        crawled_from_this = [p for p in depth1_pages if p['parent_frame'] == frame_data['frame_number']]
                        if crawled_from_this:
                            f.write(f"- **Links Crawled:** {len(crawled_from_this)}\n")
                            f.write(f"  - " + ", ".join([f"[{p['text']}]({os.path.basename(p['file_path'])})" for p in crawled_from_this]) + "\n\n")
                        else:
                            f.write("\n")
                
                if depth1_pages:
                    f.write(f"### Depth=1 Pages\n\n")
                    for page_data in depth1_pages:
                        f.write(f"#### Page {page_data['number']}: {page_data['title']}\n")
                        f.write(f"- **URL:** {page_data['url']}\n")
                        f.write(f"- **Content Length:** {len(page_data['content'])} characters\n")
                        f.write(f"- **Parent:** {page_data['parent_name']} (Frame {page_data['parent_frame']})\n")
                        f.write(f"- **File:** [{os.path.basename(page_data['file_path'])}]({os.path.basename(page_data['file_path'])})\n\n")
            
            print(f"📋 Created summary file: {summary_path}")
            
            total_pages = len(successful_frames) + len(depth1_pages)
            if total_pages > 0:
                print(f"\n🎉 Successfully crawled and saved {total_pages} page(s)!")
                print(f"   - Frames: {len(successful_frames)}")
                print(f"   - Depth=1 pages: {len(depth1_pages)}")
                print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
                return {
                    'main_html': main_html,
                    'base_url': base_url,
                    'frames': successful_frames,
                    'depth1_pages': depth1_pages,
                    'output_dir': output_dir,
                    'files': {
                        'main_analysis': main_md_path,
                        'summary': summary_path,
                        'frames': [f['file_path'] for f in successful_frames],
                        'depth1': [p['file_path'] for p in depth1_pages]
                    },
                    'success': True
                }
            else:
                print("❌ No pages could be successfully crawled")
                return None

# Run the enhanced crawler
async def main():
    result = await crawl_orthodox_and_save()
    if result:
        print(f"\n✅ Crawl completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Base URL: {result['base_url']}")
        print(f"   - Frames crawled: {len(result['frames'])}")
        print(f"   - Depth=1 pages crawled: {len(result['depth1_pages'])}")
        print(f"   - Total pages crawled: {len(result['frames']) + len(result['depth1_pages'])}")
        print(f"   - Output directory: {result['output_dir']}")
        print(f"   - Files generated: {len(result['files']['frames']) + len(result.get('files', {}).get('depth1', [])) + 2}")
        return result
    else:
        print("❌ Crawl failed")
        return None

if __name__ == "__main__":
    asyncio.run(main())