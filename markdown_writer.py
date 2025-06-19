import os
from utils import get_formatted_datetime

def write_main_page_analysis(output_path, main_html, base_url, encoding, frames, title=None, keywords=None):
    """
    Write the main page analysis to a markdown file
    
    Args:
        output_path (str): Path to the output file
        main_html (str): HTML content of the main page
        base_url (str): Base URL of the site
        encoding (str): Encoding of the main page
        frames (list): List of frame elements
        title (str, optional): Title of the main page
        keywords (str, optional): Keywords from the main page
        
    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Orthodox.cn Main Page Analysis\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")
        f.write(f"**Base URL:** {base_url}\n")
        f.write(f"**Encoding:** {encoding}\n\n")
        
        # Add title if available
        if title:
            f.write(f"**Title:** {title}\n\n")
        
        # Add keywords if available
        if keywords:
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
    
    print(f"💾 Saved main page analysis to: {output_path}")
    return output_path

def write_frame_content(output_path, frame_number, frame_name, frame_url, content, html, title=None, links=None):
    """
    Write frame content to a markdown file
    
    Args:
        output_path (str): Path to the output file
        frame_number (int): Frame number
        frame_name (str): Frame name
        frame_url (str): Frame URL
        content (str): Cleaned HTML content
        html (str): Raw HTML content
        title (str, optional): Title of the frame
        links (list, optional): List of links found in the frame
        
    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Frame {frame_number}: {frame_name}\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")
        f.write(f"**Frame URL:** {frame_url}\n")
        f.write(f"**Frame Name:** {frame_name}\n")
        f.write(f"**Content Length:** {len(content)} characters\n")
        
        if title:
            f.write(f"**Page Title:** {title}\n")
        
        f.write(f"\n## Content\n\n")
        f.write(content)
        
        # Add links section
        if links:
            f.write(f"\n\n## Links Found ({len(links)})\n\n")
            for link in links:
                f.write(f"- [{link['text']}]({link['url']})\n")
        
        # Add raw HTML section
        f.write(f"\n\n## Raw HTML\n\n")
        f.write(f"```html\n{html}\n```\n")
    
    print(f"💾 Saved frame {frame_number} to: {output_path}")
    return output_path

def write_depth1_page(output_path, title, url, content, html, parent_info, link_text, links=None, additional_info=None):
    """
    Write depth=1 page content to a markdown file
    
    Args:
        output_path (str): Path to the output file
        title (str): Page title
        url (str): Page URL
        content (str): Cleaned HTML content
        html (str): Raw HTML content
        parent_info (dict): Information about the parent page
        link_text (str): Text of the link that led to this page
        links (list, optional): List of links found in the page
        additional_info (str, optional): Additional information to include
        
    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")
        f.write(f"**URL:** {url}\n")
        f.write(f"**Parent:** {parent_info['name']} (Frame {parent_info['frame']})\n")
        f.write(f"**Link Text:** {link_text}\n")
        f.write(f"**Content Length:** {len(content)} characters\n")
        
        # Add additional info if provided
        if additional_info:
            f.write(additional_info)
        
        f.write(f"\n## Content\n\n")
        f.write(content)
        
        # Add links section
        if links:
            f.write(f"\n\n## Links Found ({len(links)})\n\n")
            for link in links[:20]:  # Limit to 20 links in the output
                f.write(f"- [{link['text']}]({link['url']})\n")
        
        # Add raw HTML section
        f.write(f"\n\n## Raw HTML\n\n")
        f.write(f"```html\n{html}\n```\n")
    
    print(f"💾 Saved depth=1 page to: {output_path}")
    return output_path

def write_summary(output_path, base_url, max_depth, frames_info, depth1_pages, main_analysis_path):
    """
    Write a summary of the crawl to a markdown file
    
    Args:
        output_path (str): Path to the output file
        base_url (str): Base URL of the site
        max_depth (int): Maximum crawl depth
        frames_info (list): List of frame information dictionaries
        depth1_pages (list): List of depth=1 page information dictionaries
        main_analysis_path (str): Path to the main page analysis file
        
    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Orthodox.cn Crawl Results\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")
        f.write(f"**Base URL:** {base_url}\n")
        f.write(f"**Max Depth:** {max_depth}\n")
        f.write(f"**Total Frames:** {len(frames_info)}\n")
        f.write(f"**Successfully Crawled Depth=1 Pages:** {len(depth1_pages)}\n")
        f.write(f"**Total Pages Crawled:** {len(frames_info) + len(depth1_pages)}\n\n")
        
        f.write(f"## Files Generated\n\n")
        f.write(f"1. **Main Page Analysis:** `{os.path.basename(main_analysis_path)}`\n")
        
        # List frame files
        for i, frame in enumerate(frames_info):
            f.write(f"{i+2}. **Frame {frame['number']} ({frame['name']}):** `{os.path.basename(frame['file_path'])}`\n")
        
        # List depth=1 files
        for i, page in enumerate(depth1_pages):
            parent_info = f"from {page['parent_name']}"
            frames_info = " (has frames)" if page.get('has_frames', False) else ""
            f.write(f"{len(frames_info)+i+2}. **Depth=1 Page {page['number']} ({parent_info}):{frames_info}** `{os.path.basename(page['file_path'])}`\n")
        
        f.write(f"\n## Site Structure\n\n")
        f.write(f"**Website:** 中国正教会 (Chinese Orthodox Church)\n\n")
        
        if frames_info:
            f.write(f"### Frame Contents\n\n")
            for frame in frames_info:
                f.write(f"#### Frame {frame['number']}: {frame['name']}\n")
                f.write(f"- **URL:** {frame['url']}\n")
                f.write(f"- **Content Length:** {len(frame['content'])} characters\n")
                if frame.get('title'):
                    f.write(f"- **Title:** {frame['title']}\n")
                f.write(f"- **File:** [{os.path.basename(frame['file_path'])}]({os.path.basename(frame['file_path'])})\n")
                
                # List links from this frame that were crawled
                crawled_from_this = [p for p in depth1_pages if p['parent_frame'] == frame['number']]
                if crawled_from_this:
                    f.write(f"- **Links Crawled:** {len(crawled_from_this)}\n")
                    f.write(f"  - " + ", ".join([f"[{p['text']}]({os.path.basename(p['file_path'])})" for p in crawled_from_this]) + "\n\n")
                else:
                    f.write("\n")
        
        if depth1_pages:
            f.write(f"### Depth=1 Pages\n\n")
            for page in depth1_pages:
                frames_info = " (contains frames)" if page.get('has_frames', False) else ""
                f.write(f"#### Page {page['number']}: {page['title']}{frames_info}\n")
                f.write(f"- **URL:** {page['url']}\n")
                f.write(f"- **Content Length:** {len(page['content'])} characters\n")
                f.write(f"- **Parent:** {page['parent_name']} (Frame {page['parent_frame']})\n")
                f.write(f"- **File:** [{os.path.basename(page['file_path'])}]({os.path.basename(page['file_path'])})\n")
                
                # Add frame information if present
                if page.get('has_frames', False) and page.get('frames'):
                    f.write(f"- **Frames ({len(page['frames'])}):**\n")
                    for frame in page['frames']:
                        f.write(f"  - Frame {frame['number']}: {frame['name']} ({frame['url']})\n")
                
                f.write("\n")
    
    print(f"📋 Created summary file: {output_path}")
    return output_path