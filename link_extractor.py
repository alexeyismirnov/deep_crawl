from bs4 import BeautifulSoup

def normalize_url(url, base_url, current_url=None):
    """
    Normalize a URL to an absolute URL
    
    Args:
        url (str): URL to normalize
        base_url (str): Base URL of the site
        current_url (str, optional): URL of the current page
        
    Returns:
        str: Normalized URL
    """
    # Skip javascript: and empty links
    if url.startswith('javascript:') or not url or url == '#' or url.lower() == 'nohref':
        return None
    
    # Already an absolute URL
    if url.startswith(('http://', 'https://')):
        return url
    
    # Root-relative URL
    if url.startswith('/'):
        return f"{base_url}{url}"
    
    # Relative URL
    if current_url:
        # Get the directory of the current URL
        current_dir = '/'.join(current_url.split('/')[:-1])
        return f"{current_dir}/{url}"
    else:
        return f"{base_url}/{url}"

def should_skip_url(url, config):
    """
    Check if a URL should be skipped based on configuration
    
    Args:
        url (str): URL to check
        config (dict): Configuration dictionary
        
    Returns:
        bool: True if the URL should be skipped, False otherwise
    """
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
    Extract links from HTML
    
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
    
    # Extract links from <a> tags
    for a_tag in soup.find_all('a', href=True):
        link_url = a_tag['href']
        link_text = a_tag.get_text().strip() or link_url
        
        # Normalize the URL
        normalized_url = normalize_url(link_url, base_url, current_url)
        if not normalized_url:
            continue
        
        # Check if we should skip this URL
        if should_skip_url(normalized_url, config):
            continue
        
        links.append({
            'url': normalized_url,
            'text': link_text
        })
    
    # Extract links from <area> tags (for image maps)
    for area_tag in soup.find_all('area', href=True):
        link_url = area_tag['href']
        link_text = area_tag.get('alt', '') or area_tag.get('title', '') or link_url
        
        # Normalize the URL
        normalized_url = normalize_url(link_url, base_url, current_url)
        if not normalized_url:
            continue
        
        # Check if we should skip this URL
        if should_skip_url(normalized_url, config):
            continue
        
        links.append({
            'url': normalized_url,
            'text': link_text
        })
    
    return links