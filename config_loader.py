import configparser

def load_config(config_path='crawler_config.ini'):
    """
    Load and parse the crawler configuration file
    
    Args:
        config_path (str): Path to the configuration file
        
    Returns:
        dict: Dictionary containing all configuration settings
    """
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Create a configuration dictionary with default values
    config_dict = {
        'max_depth': int(config.get('CRAWL_SETTINGS', 'MAX_DEPTH', fallback='1')),
        'max_links_per_page': int(config.get('CRAWL_SETTINGS', 'MAX_LINKS_PER_PAGE', fallback='15')),
        'start_url': config.get('CRAWL_SETTINGS', 'START_URL', fallback='https://orthodox.cn/'),
        'request_delay': float(config.get('CRAWL_SETTINGS', 'REQUEST_DELAY', fallback='1')),
        'page_timeout': int(config.get('CRAWL_SETTINGS', 'PAGE_TIMEOUT', fallback='15000')),
        'delay_before_return': float(config.get('CRAWL_SETTINGS', 'DELAY_BEFORE_RETURN', fallback='2.0')),
        'output_dir': config.get('OUTPUT_SETTINGS', 'OUTPUT_DIR', fallback='output'),
        'max_filename_length': int(config.get('OUTPUT_SETTINGS', 'MAX_FILENAME_LENGTH', fallback='50')),
        'headless': config.getboolean('BROWSER_SETTINGS', 'HEADLESS', fallback=True),
        'user_agent': config.get('BROWSER_SETTINGS', 'USER_AGENT', fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
        'skip_extensions': config.get('FILTERING', 'SKIP_EXTENSIONS', fallback='.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.rar,.exe').split(','),
        'skip_patterns': config.get('FILTERING', 'SKIP_PATTERNS', fallback='/admin/,/login/,/register/,/logout/,/api/').split(','),
        'exclude_domains': config.get('FILTERING', 'EXCLUDE_DOMAINS', fallback='').split(','),
        'language': config.get('FILTERING', 'LANGUAGE', fallback='').strip()
    }
    
    print(f"📋 Configuration:")
    print(f"   - Max depth: {config_dict['max_depth']}")
    print(f"   - Max links per page: {config_dict['max_links_per_page']}")
    print(f"   - Output directory: {config_dict['output_dir']}")
    if config_dict['language']:
        print(f"   - Target language: {config_dict['language']}")
    else:
        print(f"   - Target language: Any (no language filtering)")
    
    return config_dict