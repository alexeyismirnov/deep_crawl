import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import aiohttp
import ssl
from bs4 import BeautifulSoup
import chardet
import os
from datetime import datetime
import re

async def crawl_orthodox_and_save():
    """
    Enhanced version that saves crawled content to markdown files
    """
    print("🚀 Starting Orthodox website crawl with markdown export...")
    
    # Create output directory
    output_dir = "output"
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
        if frames:
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
                                    
                                    # Add links section if available
                                    if hasattr(frame_result, 'links') and frame_result.links:
                                        f.write(f"\n\n## Links Found\n\n")
                                        for link in frame_result.links:
                                            if hasattr(link, 'url') and hasattr(link, 'text'):
                                                f.write(f"- [{link.text}]({link.url})\n")
                                            elif isinstance(link, dict):
                                                url = link.get('url', link.get('href', ''))
                                                text = link.get('text', link.get('title', url))
                                                f.write(f"- [{text}]({url})\n")
                                            else:
                                                f.write(f"- {link}\n")
                                    
                                    # Add raw HTML section
                                    f.write(f"\n\n## Raw HTML\n\n")
                                    f.write(f"```html\n{frame_result.html}\n```\n")
                                
                                print(f"💾 Saved frame {i+1} to: {frame_md_path}")
                                
                                successful_frames.append({
                                    'frame_number': i+1,
                                    'name': frame_name,
                                    'url': frame_url,
                                    'content': frame_result.cleaned_html,
                                    'title': frame_result.metadata.get('title', ''),
                                    'links': getattr(frame_result, 'links', []),
                                    'file_path': frame_md_path
                                })
                            else:
                                print(f"❌ Frame {i+1} failed: {frame_result.error_message}")
                                
                        except Exception as e:
                            print(f"❌ Frame {i+1} exception: {str(e)}")
                
                # Create summary file
                summary_path = os.path.join(output_dir, f"README_{timestamp}.md")
                with open(summary_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Orthodox.cn Crawl Results\n\n")
                    f.write(f"**Crawl Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"**Base URL:** {base_url}\n")
                    f.write(f"**Total Frames:** {len(frames)}\n")
                    f.write(f"**Successfully Crawled:** {len(successful_frames)}\n\n")
                    
                    f.write(f"## Files Generated\n\n")
                    f.write(f"1. **Main Page Analysis:** `{os.path.basename(main_md_path)}`\n")
                    
                    for frame_data in successful_frames:
                        f.write(f"{frame_data['frame_number']+1}. **Frame {frame_data['frame_number']} ({frame_data['name']}):** `{os.path.basename(frame_data['file_path'])}`\n")
                    
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
                            f.write(f"- **File:** [{os.path.basename(frame_data['file_path'])}]({os.path.basename(frame_data['file_path'])})\n\n")
                
                print(f"📋 Created summary file: {summary_path}")
                
                if successful_frames:
                    print(f"\n🎉 Successfully crawled and saved {len(successful_frames)} frame(s)!")
                    print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
                    return {
                        'main_html': main_html,
                        'base_url': base_url,
                        'frames': successful_frames,
                        'output_dir': output_dir,
                        'files': {
                            'main_analysis': main_md_path,
                            'summary': summary_path,
                            'frames': [f['file_path'] for f in successful_frames]
                        },
                        'success': True
                    }
                else:
                    print("❌ No frames could be successfully crawled")
                    return None
        else:
            print("ℹ️ No frames found - this might not be a frame-based site")
            return None

# Run the enhanced crawler
async def main():
    result = await crawl_orthodox_and_save()
    if result:
        print(f"\n✅ Crawl completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Base URL: {result['base_url']}")
        print(f"   - Frames crawled: {len(result['frames'])}")
        print(f"   - Output directory: {result['output_dir']}")
        print(f"   - Files generated: {len(result['files']['frames']) + 2}")
        return result
    else:
        print("❌ Crawl failed")
        return None

if __name__ == "__main__":
    asyncio.run(main())