import os
from utils import get_formatted_datetime

def write_main_page_analysis(output_path, main_html, base_url, encoding, frames, title=None, keywords=None, start_url=None):
    """
    Write the main page analysis to a markdown file

    Args:
        output_path (str): Path to the output file
        main_html (str): HTML content of the main page
        base_url (str): Base URL of the site (for relative link resolution)
        encoding (str): Encoding of the main page
        frames (list): List of frame elements
        title (str, optional): Title of the main page
        keywords (str, optional): Keywords from the main page
        start_url (str, optional): Original start URL from configuration

    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Orthodox.cn Main Page Analysis\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")

        # Show both start URL and base URL if start URL is provided
        if start_url:
            f.write(f"**Start URL:** {start_url}\n")
            f.write(f"**Base URL:** {base_url}\n")
        else:
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
        
        # f.write(f"\n## Raw HTML Structure\n\n")
        # f.write(f"```html\n{main_html}\n```\n")
    
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
        # f.write(f"\n\n## Raw HTML\n\n")
        # f.write(f"```html\n{html}\n```\n")
    
    print(f"💾 Saved frame {frame_number} to: {output_path}")
    return output_path

def write_page_content(output_path, title, url, content, html, parent_info, link_text, depth, links=None, additional_info=None):
    """
    Write page content to a markdown file
    
    Args:
        output_path (str): Path to the output file
        title (str): Page title
        url (str): Page URL
        content (str): Cleaned HTML content
        html (str): Raw HTML content
        parent_info (dict): Information about the parent page
        link_text (str): Text of the link that led to this page
        depth (int): Depth level of the page
        links (list, optional): List of links found in the page
        additional_info (str, optional): Additional information to include
        
    Returns:
        str: Path to the created file
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")
        f.write(f"**URL:** {url}\n")
        f.write(f"**Depth:** {depth}\n")
        f.write(f"**Parent:** {parent_info['name']} ({parent_info['type']})\n")
        f.write(f"**Parent URL:** {parent_info['url']}\n")
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
        # f.write(f"\n\n## Raw HTML\n\n")
        # f.write(f"```html\n{html}\n```\n")
    
    print(f"💾 Saved depth={depth} page to: {output_path}")
    return output_path

def write_summary(output_path, base_url, max_depth, all_pages, main_analysis_path, start_url=None):
    """
    Write a summary of the crawl to a markdown file

    Args:
        output_path (str): Path to the output file
        base_url (str): Base URL of the site (for relative link resolution)
        max_depth (int): Maximum crawl depth
        all_pages (list): List of all page information dictionaries
        main_analysis_path (str): Path to the main page analysis file
        start_url (str, optional): Original start URL from configuration

    Returns:
        str: Path to the created file
    """
    # Group pages by depth
    pages_by_depth = {}
    for page in all_pages:
        depth = page['depth']
        if depth not in pages_by_depth:
            pages_by_depth[depth] = []
        pages_by_depth[depth].append(page)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Orthodox.cn Crawl Results\n\n")
        f.write(f"**Crawl Date:** {get_formatted_datetime()}\n")

        # Show both start URL and base URL if start URL is provided
        if start_url:
            f.write(f"**Start URL:** {start_url}\n")
            f.write(f"**Base URL:** {base_url}\n")
        else:
            f.write(f"**Base URL:** {base_url}\n")

        f.write(f"**Max Depth:** {max_depth}\n")
        f.write(f"**Total Pages Crawled:** {len(all_pages)}\n\n")

        # Count pages by depth
        f.write(f"## Pages by Depth\n\n")
        f.write(f"| Depth | Count |\n")
        f.write(f"|-------|-------|\n")
        for depth in sorted(pages_by_depth.keys()):
            f.write(f"| {depth} | {len(pages_by_depth[depth])} |\n")

        f.write(f"\n## Files Generated\n\n")
        f.write(f"1. **Main Page Analysis:** `{os.path.basename(main_analysis_path)}`\n")

        # List all pages by depth
        file_counter = 2
        for depth in sorted(pages_by_depth.keys()):
            f.write(f"\n### Depth {depth} Files\n\n")
            for page in pages_by_depth[depth]:
                page_type = page['type']
                page_name = page['name'] if 'name' in page else page['title']
                has_frames = " (has frames)" if page.get('has_frames', False) else ""

                f.write(f"{file_counter}. **{page_type.capitalize()} {page['number']} ({page_name}):{has_frames}** `{os.path.basename(page['file_path'])}`\n")
                file_counter += 1

        f.write(f"\n## Site Structure\n\n")
        f.write(f"**Website:** 中国正教会 (Chinese Orthodox Church)\n\n")

        # Create a page tree
        f.write(f"### Page Hierarchy\n\n")

        # Start with depth 0 pages (frames)
        if 0 in pages_by_depth:
            for page in pages_by_depth[0]:
                f.write(f"- **{page['title']}** ({page['url']})\n")

                # Find children of this page
                children = [p for p in all_pages if p.get('parent_id') == page['id']]
                if children:
                    for child in children:
                        f.write(f"  - [{child['title']}]({os.path.basename(child['file_path'])}) (depth={child['depth']})\n")

                        # Find grandchildren (limit to 3 levels for readability)
                        grandchildren = [p for p in all_pages if p.get('parent_id') == child['id']]
                        if grandchildren:
                            for gc in grandchildren[:5]:  # Limit to 5 grandchildren
                                f.write(f"    - [{gc['title']}]({os.path.basename(gc['file_path'])}) (depth={gc['depth']})\n")

                            if len(grandchildren) > 5:
                                f.write(f"    - ... and {len(grandchildren) - 5} more\n")

        # Detailed page information by depth
        for depth in sorted(pages_by_depth.keys()):
            f.write(f"\n### Depth {depth} Pages\n\n")

            for page in pages_by_depth[depth]:
                page_type = page['type']
                page_title = page['title']
                frames_info = " (contains frames)" if page.get('has_frames', False) else ""

                f.write(f"#### {page_type.capitalize()} {page['number']}: {page_title}{frames_info}\n")
                f.write(f"- **URL:** {page['url']}\n")
                f.write(f"- **Content Length:** {len(page['content'])} characters\n")

                if 'parent_name' in page and page['parent_name']:
                    f.write(f"- **Parent:** {page['parent_name']} ({page.get('parent_url', 'No URL')})\n")

                f.write(f"- **File:** [{os.path.basename(page['file_path'])}]({os.path.basename(page['file_path'])})\n")

                # Add frame information if present
                if page.get('has_frames', False) and page.get('frames'):
                    f.write(f"- **Frames ({len(page['frames'])}):**\n")
                    for frame in page['frames']:
                        f.write(f"  - Frame {frame['number']}: {frame['name']} ({frame['url']})\n")

                # List links that were crawled from this page
                children = [p for p in all_pages if p.get('parent_id') == page.get('id')]
                if children:
                    f.write(f"- **Links Crawled ({len(children)}):**\n")
                    for child in children[:10]:  # Limit to 10 links
                        f.write(f"  - [{child['title']}]({os.path.basename(child['file_path'])})\n")

                    if len(children) > 10:
                        f.write(f"  - ... and {len(children) - 10} more\n")

                f.write("\n")

    print(f"📋 Created summary file: {output_path}")
    return output_path