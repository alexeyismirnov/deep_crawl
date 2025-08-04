import asyncio
import os
from bs4 import BeautifulSoup

# Import our modules
from config_loader import load_config
from page_fetcher import (
    fetch_main_page, create_crawler, crawl_page, 
    extract_frames, fetch_page_with_frames
)
from link_extractor import extract_links_from_html, normalize_url, normalize_url_for_deduplication
from markdown_writer import (
    write_main_page_analysis, write_frame_content, 
    write_page_content, write_summary
)
from utils import create_output_directory, create_safe_filename, get_timestamp

async def crawl_orthodox_and_save():
    """
    Enhanced version that saves crawled content to markdown files
    with support for arbitrary depth crawling
    """
    print("🚀 Starting Orthodox website crawl with markdown export...")
    
    # Load configuration
    config = load_config()
    
    # Create output directory
    output_dir = create_output_directory(config['output_dir'])
    
    # Use the START_URL from configuration
    start_url = config['start_url']
    print(f"🌐 Using start URL from configuration: {start_url}")

    # Fetch the main page
    main_html, base_url, encoding = await fetch_main_page([start_url], config)
    
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
        title=title_text, keywords=keywords, start_url=start_url
    )
    
    # Create crawler
    async with await create_crawler(config) as crawler:
        # Initialize data structures
        all_crawled_pages = set()  # Track all crawled pages by URL
        all_pages_data = []  # Store data for all crawled pages
        
        # First, crawl the frames from the main page (depth 0)
        frame_pages = []
        
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
                            link['parent_url'] = frame_url
                            link['parent_type'] = 'frame'
                        
                        frame_data = {
                            'id': f"frame_{i+1}",
                            'number': i+1,
                            'name': frame_name,
                            'url': frame_url,
                            'content': frame_result['cleaned_html'],
                            'title': frame_result['title'],
                            'links': frame_links,
                            'file_path': frame_md_path,
                            'depth': 0,
                            'type': 'frame',
                            'parent_id': None,
                            'parent_name': None,
                            'parent_url': None
                        }
                        
                        frame_pages.append(frame_data)
                        all_crawled_pages.add(normalize_url_for_deduplication(frame_url))

                        print(f"💾 Saved frame {i+1} to: {os.path.basename(frame_md_path)}")
                    else:
                        print(f"❌ Frame {i+1} failed or was rejected (likely by language detection)")
                        frame_name = frame.get('name', f'frame_{i+1}')
                        print(f"   Frame name: {frame_name}")
                        print(f"   Frame URL: {frame_url}")
                        print(f"   This frame will not appear in the output")
        else:
            # If no frames, extract links from the main page
            print("\n🔍 No frames found, extracting links from main page...")
            main_links = extract_links_from_html(main_html, base_url, base_url, config)
            
            print(f"Found {len(main_links)} links on main page")
            
            # Add parent information to links
            for link in main_links:
                link['parent_frame'] = 0
                link['parent_name'] = 'main_page'
                link['parent_url'] = base_url
                link['parent_type'] = 'main'
        
        # Add frame pages to all pages data
        all_pages_data.extend(frame_pages)
        
        # Now perform recursive crawling up to max_depth
        if config['max_depth'] > 0:
            # Get all links from depth 0 (frames)
            links_by_depth = {0: []}
            
            # Collect all links from frames
            for frame in frame_pages:
                for link in frame['links']:
                    if normalize_url_for_deduplication(link['url']) not in all_crawled_pages:
                        links_by_depth[0].append(link)
            
            # If no frames, use links from main page
            if not frame_pages and 'main_links' in locals():
                links_by_depth[0] = main_links
            
            # Crawl each depth level
            for current_depth in range(1, config['max_depth'] + 1):
                print(f"\n{'='*80}")
                print(f"🔍 Starting depth={current_depth} crawl")
                print(f"{'='*80}")
                
                # Check if we have links to crawl at this depth
                if current_depth - 1 not in links_by_depth or not links_by_depth[current_depth - 1]:
                    print(f"ℹ️ No links to crawl at depth={current_depth}")
                    break
                
                # Initialize links for the next depth
                links_by_depth[current_depth] = []
                
                # Get links to crawl at this depth
                links_to_crawl = links_by_depth[current_depth - 1]
                
                # No more limiting the number of links to crawl
                print(f"🔄 Crawling all {len(links_to_crawl)} links at depth={current_depth}")
                
                # Crawl each link
                depth_pages = []
                
                for i, link_data in enumerate(links_to_crawl):
                    link_url = link_data['url']
                    link_text = link_data['text']
                    parent_info = f"(from {link_data['parent_name']})"

                    # Normalize URL for deduplication (remove fragments)
                    normalized_link_url = normalize_url_for_deduplication(link_url)

                    # Skip if already crawled (check normalized URL)
                    if normalized_link_url in all_crawled_pages:
                        print(f"⏭️ Skipping already crawled: {link_url} (normalized: {normalized_link_url})")
                        continue
                    
                    print(f"\n🔄 Crawling depth={current_depth} link {i+1}/{len(links_to_crawl)}: {link_url} {parent_info}")

                    # Use the enhanced page fetcher that handles frames
                    # Use normalized URL (without fragment) for actual fetching since fragments don't change content
                    page_result = await fetch_page_with_frames(normalized_link_url, base_url, config)
                    
                    if page_result:
                        print(f"✅ Link {i+1} success!")
                        print(f"Content length: {len(page_result['cleaned_html'])}")
                        print(f"Title: {page_result['title']}")
                        
                        if page_result['has_frames']:
                            print(f"🔍 Page has {len(page_result['frames'])} frames")
                        
                        # Extract links from this page
                        page_links = extract_links_from_html(
                            page_result['html'], base_url, normalized_link_url, config
                        )
                        
                        # Create a safe filename from the URL (use normalized URL without fragment)
                        safe_name = create_safe_filename(normalized_link_url, prefix=f"depth{current_depth}_{i+1:03d}")
                        page_md_path = os.path.join(output_dir, f"{safe_name}_{timestamp}.md")
                        
                        # Save page content to markdown
                        parent_info_dict = {
                            'name': link_data['parent_name'],
                            'type': link_data.get('parent_type', 'page'),
                            'url': link_data['parent_url'],
                            'id': link_data.get('parent_id', link_data['parent_name'])
                        }
                        
                        # Add information about frames if present
                        frames_info = ""
                        if page_result['has_frames']:
                            frames_info = f"\n**Contains {len(page_result['frames'])} frames**\n"
                            for frame in page_result['frames']:
                                frames_info += f"- Frame {frame['number']}: {frame['name']} ({frame['url']})\n"
                        
                        # Add language information if detected
                        if config.get('language'):
                            frames_info += f"\n**Target Language:** {config['language']}\n"
                        
                        page_md_path = write_page_content(
                            page_md_path, page_result['title'], normalized_link_url,
                            page_result['cleaned_html'], page_result['html'],
                            parent_info_dict, link_text, current_depth,
                            links=page_links, additional_info=frames_info
                        )
                        
                        # Generate a unique ID for this page
                        page_id = f"depth{current_depth}_page{i+1}"
                        
                        # Add parent information to links for the next depth
                        for link in page_links:
                            link['parent_id'] = page_id
                            link['parent_name'] = page_result['title']
                            link['parent_url'] = link_url
                            link['parent_type'] = 'page'
                
                            # Add to next depth if not already crawled
                            if normalize_url_for_deduplication(link['url']) not in all_crawled_pages:
                                links_by_depth[current_depth].append(link)
                        
                        page_data = {
                            'id': page_id,
                            'number': i+1,
                            'url': link_url,
                            'text': link_text,
                            'title': page_result['title'],
                            'content': page_result['cleaned_html'],
                            'has_frames': page_result['has_frames'],
                            'frames': page_result.get('frames', []),
                            'links': page_links,
                            'file_path': page_md_path,
                            'depth': current_depth,
                            'type': 'page',
                            'parent_id': link_data.get('parent_id', link_data['parent_name']),
                            'parent_name': link_data['parent_name'],
                            'parent_url': link_data['parent_url']
                        }
                        
                        depth_pages.append(page_data)
                        all_crawled_pages.add(normalized_link_url)
                
                # Add pages from this depth to all pages data
                all_pages_data.extend(depth_pages)
                
                print(f"\n🎉 Successfully crawled {len(depth_pages)} pages at depth={current_depth}")
                print(f"🔗 Found {len(links_by_depth[current_depth])} links for depth={current_depth+1}")
        
        # Create summary file
        summary_path = os.path.join(output_dir, f"README_{timestamp}.md")
        summary_path = write_summary(
            summary_path, base_url, config['max_depth'],
            all_pages_data, main_md_path, start_url=start_url
        )
        
        # Count pages by depth
        pages_by_depth = {}
        for page in all_pages_data:
            depth = page['depth']
            if depth not in pages_by_depth:
                pages_by_depth[depth] = 0
            pages_by_depth[depth] += 1
        
        if all_pages_data:
            print(f"\n🎉 Successfully crawled and saved {len(all_pages_data)} page(s)!")
            for depth, count in sorted(pages_by_depth.items()):
                print(f"   - Depth={depth}: {count} pages")
            print(f"📁 All files saved to: {os.path.abspath(output_dir)}")
            
            return {
                'main_html': main_html,
                'base_url': base_url,
                'pages': all_pages_data,
                'output_dir': output_dir,
                'files': {
                    'main_analysis': main_md_path,
                    'summary': summary_path,
                    'pages': [p['file_path'] for p in all_pages_data]
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
        print(f"   - Total pages crawled: {len(result['pages'])}")
        print(f"   - Output directory: {result['output_dir']}")
        print(f"   - Files generated: {len(result['files']['pages']) + 2}")
        return result
    else:
        print("❌ Crawl failed")
        return None

if __name__ == "__main__":
    asyncio.run(main())