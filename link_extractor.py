from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
import re

def normalize_url(url, base_url, current_url=None):
    """
    Normalize a URL to an absolute URL with proper path normalization
    
    Args:
        url (str): URL to normalize
        base_url (str): Base URL of the site
        current_url (str, optional): URL of the current page
        
    Returns:
        str: Normalized URL with resolved path segments and cleaned slashes
    """
    # Skip javascript: and empty links
    if url.startswith('javascript:') or not url or url == '#' or url.lower() == 'nohref':
        return None
    
    # Already an absolute URL
    if url.startswith(('http://', 'https://')):
        absolute_url = url
    elif url.startswith('/'):
        # Root-relative URL
        absolute_url = f"{base_url.rstrip('/')}{url}"
    else:
        # Relative URL
        if current_url:
            # Get the directory of the current URL
            current_dir = '/'.join(current_url.split('/')[:-1])
            absolute_url = f"{current_dir}/{url}"
        else:
            absolute_url = f"{base_url.rstrip('/')}/{url}"
    
    # Now normalize the path segments
    return normalize_url_path(absolute_url)

def normalize_url_path(url):
    """
    Normalize URL by resolving '..' and '.' path segments and cleaning multiple slashes

    Args:
        url (str): URL to normalize

    Returns:
        str: Normalized URL with resolved path segments and cleaned slashes
    """
    if not url:
        return url

    try:
        # Parse the URL
        parsed = urlparse(url)

        # Clean multiple slashes in the path (but preserve the protocol://)
        path = parsed.path

        # Remember if the original path ended with a slash
        ends_with_slash = path.endswith('/') and len(path) > 1

        # Replace multiple consecutive slashes with single slash
        path = re.sub(r'/+', '/', path)

        # Split the path into segments
        path_segments = path.split('/')

        # Resolve '..' and '.' segments
        normalized_segments = []
        for segment in path_segments:
            if segment == '..':
                # Go up one level (remove last segment if exists)
                if normalized_segments and normalized_segments[-1] != '':
                    normalized_segments.pop()
            elif segment == '.' or segment == '':
                # Skip current directory references and empty segments
                # (except for the first empty segment which represents root)
                if not normalized_segments:
                    normalized_segments.append('')
            else:
                normalized_segments.append(segment)

        # Reconstruct the path
        normalized_path = '/'.join(normalized_segments)

        # Ensure path starts with / if it's not empty
        if normalized_path and not normalized_path.startswith('/'):
            normalized_path = '/' + normalized_path

        # Handle empty path case
        if not normalized_path:
            normalized_path = '/'

        # Restore trailing slash if it was present and we have content after root
        if ends_with_slash and normalized_path != '/' and not normalized_path.endswith('/'):
            normalized_path += '/'

        # Reconstruct the URL
        normalized_parsed = parsed._replace(path=normalized_path)
        return urlunparse(normalized_parsed)

    except Exception as e:
        print(f"Warning: Failed to normalize URL {url}: {e}")
        return url

def normalize_url_for_deduplication(url):
    """
    Normalize URL for deduplication by removing fragments (hash parts)

    Fragment identifiers (#section) don't represent different pages,
    they're just anchors within the same page, so they should be
    treated as the same URL for crawling purposes.

    Args:
        url (str): URL to normalize

    Returns:
        str: URL without fragment identifier
    """
    if not url:
        return url

    # Parse the URL and remove the fragment
    parsed = urlparse(url)
    # Reconstruct without fragment
    normalized_parsed = parsed._replace(fragment='')
    return urlunparse(normalized_parsed)

def is_same_domain(url, base_url):
    """
    Check if a URL belongs to the same domain as the base URL

    Args:
        url (str): URL to check
        base_url (str): Base URL of the site

    Returns:
        bool: True if the URL is from the same domain, False otherwise
    """
    try:
        url_domain = urlparse(url).netloc
        base_domain = urlparse(base_url).netloc

        # Handle www. prefix
        if url_domain.startswith('www.'):
            url_domain = url_domain[4:]
        if base_domain.startswith('www.'):
            base_domain = base_domain[4:]

        return url_domain == base_domain
    except:
        return False

def should_skip_url(url, config, base_url):
    """
    Check if a URL should be skipped based on configuration
    
    Args:
        url (str): URL to check
        config (dict): Configuration dictionary
        base_url (str): Base URL of the site
        
    Returns:
        bool: True if the URL should be skipped, False otherwise
    """
    # Skip external domains
    if not is_same_domain(url, base_url):
        return True
    
    # Skip based on extensions
    for ext in config['skip_extensions']:
        if ext and url.lower().endswith(ext.lower()):
            return True
    
    # Skip based on patterns
    for pattern in config['skip_patterns']:
        if pattern and pattern in url:
            return True
    
    # Skip based on domains
    for domain in config['exclude_domains']:
        if domain and domain in url:
            return True
    
    return False

def extract_links_from_html(html, base_url, current_url, config):
    """
    Extract links from HTML - with improved fragment handling

    Args:
        html (str): HTML content
        base_url (str): Base URL of the site
        current_url (str): URL of the current page
        config (dict): Configuration dictionary

    Returns:
        list: List of link dictionaries
    """
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    
    # Track URLs we've already processed to avoid duplicates with different fragments
    processed_urls = set()

    # Extract links from <a> tags
    for a_tag in soup.find_all('a', href=True):
        link_url = a_tag['href']
        link_text = a_tag.get_text().strip() or link_url

        # Normalize the URL (now includes path normalization)
        normalized_url = normalize_url(link_url, base_url, current_url)
        if not normalized_url:
            continue

        # Check if we should skip this URL
        if should_skip_url(normalized_url, config, base_url):
            continue
            
        # Remove fragment for deduplication
        deduplicated_url = normalize_url_for_deduplication(normalized_url)
        
        # Skip if we've already processed this URL (ignoring fragment)
        if deduplicated_url in processed_urls:
            continue
            
        # Add to processed URLs set
        processed_urls.add(deduplicated_url)

        # Store both the original URL and the deduplicated URL
        links.append({
            'url': deduplicated_url,  # Use deduplicated URL (without fragment) for crawling
            'original_url': normalized_url,  # Keep original URL with fragment for reference
            'text': link_text
        })

    # Extract links from <area> tags (for image maps)
    for area_tag in soup.find_all('area', href=True):
        link_url = area_tag['href']
        link_text = area_tag.get('alt', '') or area_tag.get('title', '') or link_url

        # Normalize the URL (now includes path normalization)
        normalized_url = normalize_url(link_url, base_url, current_url)
        if not normalized_url:
            continue

        # Check if we should skip this URL
        if should_skip_url(normalized_url, config, base_url):
            continue
            
        # Remove fragment for deduplication
        deduplicated_url = normalize_url_for_deduplication(normalized_url)
        
        # Skip if we've already processed this URL (ignoring fragment)
        if deduplicated_url in processed_urls:
            continue
            
        # Add to processed URLs set
        processed_urls.add(deduplicated_url)

        links.append({
            'url': deduplicated_url,  # Use deduplicated URL (without fragment) for crawling
            'original_url': normalized_url,  # Keep original URL with fragment for reference
            'text': link_text
        })

    # Extract links from <frame> and <iframe> tags
    for frame_tag in soup.find_all(['frame', 'iframe'], src=True):
        frame_url = frame_tag['src']

        # Skip javascript: and about:blank URLs
        if frame_url.startswith('javascript:') or frame_url == 'about:blank':
            continue

        # Get frame name or title for link text
        frame_name = frame_tag.get('name', '') or frame_tag.get('title', '') or frame_tag.get('id', '')
        link_text = f"Frame: {frame_name}" if frame_name else f"Frame: {frame_url}"

        # Normalize the URL (now includes path normalization)
        normalized_url = normalize_url(frame_url, base_url, current_url)
        if not normalized_url:
            continue

        # Check if we should skip this URL
        if should_skip_url(normalized_url, config, base_url):
            continue
            
        # Remove fragment for deduplication
        deduplicated_url = normalize_url_for_deduplication(normalized_url)
        
        # Skip if we've already processed this URL (ignoring fragment)
        if deduplicated_url in processed_urls:
            continue
            
        # Add to processed URLs set
        processed_urls.add(deduplicated_url)

        links.append({
            'url': deduplicated_url,  # Use deduplicated URL (without fragment) for crawling
            'original_url': normalized_url,  # Keep original URL with fragment for reference
            'text': link_text
        })

    return links