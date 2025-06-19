import asyncio
import os
from bs4 import BeautifulSoup

# Import our modules
from config_loader import load_config
from page_fetcher import fetch_main_page, create_crawler, crawl_page, extract_frames
from link_extractor import extract_links_from_html, normalize_url
from markdown_writer import (
    write_main_page_analysis, write_frame_content, 
    write_depth1_page, write_summary
)
from utils import create_output_directory, create_safe_filename, get_timestamp

async def crawl_orthodox_and_save():
    """
    Enhanced version that saves crawled content to markdown files
    with support for depth=1 crawling
    """
    print("🚀 Starting Orthodox website crawl with markdown export...")
    
    # Load configuration
    config = load_config()
    
    # Create output directory
    output_dir = create_output_directory(config['output_dir'])
    
    # Fetch the main page
    urls_to_try = ["https://orthodox.cn/", "http://orthodox.cn/"]
    main_html, base_url, encoding = await fetch_main_page(urls_to_try)
    
    if not main_html:
        return None
    
    # Extract frames from the main page
    frames = extract_frames(main_html)
    
    # Extract title and keywords from the main page
    soup = BeautifulSoup(main_html, 'html.parser')
    title = soup.find('title')
    title_text = title.get_text().strip() if title else None
    
    keywords_meta = soup.find('meta', {'name': 'keywords'})
    keywords = keywords_meta.get('content', '') if keywords_meta else None
    
    # Save main page analysis
    timestamp = get_timestamp()
    main_md_path = os.path.join(output_dir, f"00_main_page_analysis_{timestamp}.md")
    main_md_path = write_main_page_analysis(
        main_md_path, main_html, base_url, encoding, frames, 
        title=title_text, keywords=keywords
    )
    
    # Create crawler
    async with await create_crawler(config) as crawler:
        successful_frames = []
        all_crawled_pages = []  # Track all crawled pages
        all_links_to_crawl = []  # Links to crawl for depth=1
        
        # First, crawl the frames from the main page
        if frames:
            for i, frame in enumerate(frames):
                src = frame.get('src', '')
                if src and not src.startswith('javascript:') and src != 'about:blank':
                    # Build absolute URL
                    frame_url = normalize_url(src, base_url)
                    if not frame_url:
                        continue
                    
                    print(f"\n🔄 Accessing frame {i+1}: {frame_url}")
                    
                    # Crawl the frame
                    frame_result = await crawl_page(crawler, frame_url, config)
                    
                    if frame_result:
                        print(f"✅ Frame {i+1} success!")
                        print(f"Content length: {len(frame_result['cleaned_html'])}")
                        print(f"Title: {frame_result['title']}")
                        
                        # Extract links from the frame
                        frame_links = extract_links_from_html(
                            frame_result['html'], base_url, frame_url, config
                        )
                        
                        print(f"🔗 Found {len(frame_links)} links in frame {i+1}")
                        
                        # Save frame content to markdown
                        frame_name = frame.get('name', f'frame_{i+1}')
                        safe_name = create_safe_filename(frame_name)
                        frame_md_path = os.path.join(output_dir, f"{i+1:02d}_{safe_name}_{timestamp}.md")
                        
                        frame_md_path = write_frame_content(
                            frame_md_path, i+1, frame_name, frame_url,
                            frame_result['cleaned_html'], frame_result['html'],
                            title=frame_result['title'], links=frame_links
                        )
                        
                        # Add parent information to links
                        for link in frame_links:
                            link['parent_frame'] = i+1
                            link['parent_name'] = frame_name
                        
                        frame_data = {
                            'number': i+1,
                            'name': frame_name,
                            'url': frame_url,
                            'content': frame_result['cleaned_html'],
                            'title': frame_result['title'],
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
            # If no frames, extract links from the main page
            print("\n🔍 No frames found, extracting links from main page...")
            main_links = extract_links_from_html(main_html, base_url, base_url, config)
            
            print(f"Found {len(main_links)} links on main page")
            
            # Add parent information to links
            for link in main_links:
                link['parent_frame'] = 0
                link['parent_name'] = 'main_page'
            
            all_links_to_crawl.extend(main_links[:config['max_links_per_page']])
        
        # Now crawl depth=1 links if max_depth > 0
        depth1_pages = []
        
        if config['max_depth'] > 0:
            if all_links_to_crawl:
                print(f"\n🔄 Starting depth=1 crawl of {len(all_links_to_crawl)} links...")
                print(f"🔍 First 5 links to crawl: {[link['url'] for link in all_links_to_crawl[:5]]}")
                
                # Limit the number of links to crawl if there are too many
                if len(all_links_to_crawl) > config['max_links_per_page'] * 3:
                    print(f"⚠️ Too many links ({len(all_links_to_crawl)}), limiting to {config['max_links_per_page'] * 3}")
                    all_links_to_crawl = all_links_to_crawl[:config['max_links_per_page'] * 3]
                
                for i, link_data in enumerate(all_links_to_crawl):
                    link_url = link_data['url']
                    link_text = link_data['text']
                    parent_info = f"(from {link_data['parent_name']})"
                    
                    # Skip if already crawled
                    if link_url in all_crawled_pages:
                        print(f"⏭️ Skipping already crawled: {link_url}")
                        continue
                    
                    print(f"\n🔄 Crawling depth=1 link {i+1}/{len(all_links_to_crawl)}: {link_url} {parent_info}")
                    
                    # Crawl the page
                    page_result = await crawl_page(crawler, link_url, config)
                    
                    if page_result:
                        print(f"✅ Link {i+1} success!")
                        print(f"Content length: {len(page_result['cleaned_html'])}")
                        print(f"Title: {page_result['title']}")
                        
                        # Extract links from this page
                        page_links = extract_links_from_html(
                            page_result['html'], base_url, link_url, config
                        )
                        
                        # Create a safe filename from the URL
                        safe_name = create_safe_filename(link_url, prefix=f"depth1_{i+1:03d}")
                        page_md_path = os.path.join(output_dir, f"{safe_name}_{timestamp}.md")
                        
                        # Save page content to markdown
                        parent_info = {
                            'name': link_data['parent_name'],
                            'frame': link_data['parent_frame']
                        }
                        
                        page_md_path = write_depth1_page(
                            page_md_path, page_result['title'], link_url,
                            page_result['cleaned_html'], page_result['html'],
                            parent_info, link_text, links=page_links
                        )
                        
                        depth1_pages.append({
                            'number': i+1,
                            'url': link_url,
                            'text': link_text,
                            'title': page_result['title'],
                            'content': page_result['cleaned_html'],
                            'parent_frame': link_data['parent_frame'],
                            'parent_name': link_data['parent_name'],
                            'file_path': page_md_path
                        })
                        
                        all_crawled_pages.append(link_url)
                
                # Update the summary with depth=1 pages
                print(f"\n🎉 Successfully crawled {len(depth1_pages)} depth=1 pages")
            else:
                print("\n⚠️ No links found to crawl at depth=1")
        else:
            print("\nℹ️ Skipping depth=1 crawl (max_depth=0)")
        
        # Create summary file
        summary_path = os.path.join(output_dir, f"README_{timestamp}.md")
        summary_path = write_summary(
            summary_path, base_url, config['max_depth'],
            successful_frames, depth1_pages, main_md_path
        )
        
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