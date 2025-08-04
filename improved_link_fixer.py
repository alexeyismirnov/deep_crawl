#!/usr/bin/env python3
"""
Link Fixer for Hugo Content - Improved Version
Fixes internal links in Hugo markdown files by mapping original URLs to new Hugo URLs
"""

import json
import re
from pathlib import Path
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import os

from link_extractor import normalize_url_path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ImprovedLinkFixer:
    def __init__(self, json_file="extracted_content.json", hugo_dir="orthodox-china"):
        self.json_file = json_file
        self.hugo_dir = Path(hugo_dir)
        self.content_dir = self.hugo_dir / "content"
        self.url_mapping = {}
        self.base_url = "https://orthodox.cn/"

    def load_data_and_build_mapping(self):
        """Load extracted data and build URL mapping"""
        logger.info("Loading extracted data and building URL mapping...")

        with open(self.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Build mapping from original URLs to Hugo file paths
        for item in data:
            original_url = item.get('original_url', '')
            if original_url:
                # Normalize the original URL first
                normalized_original = normalize_url_path(original_url)

                # Remove base URL to get relative path
                if normalized_original.startswith(self.base_url):
                    relative_original = normalized_original[len(self.base_url):]
                else:
                    # Handle URLs that might have different formats
                    parsed = urlparse(normalized_original)
                    relative_original = parsed.path.lstrip('/')

                # Find corresponding Hugo file
                hugo_path = self.find_hugo_file_for_url(original_url)
                if hugo_path:
                    self.url_mapping[relative_original] = hugo_path

                    # Also map variations of the URL
                    # Handle URLs with and without leading slashes
                    if not relative_original.startswith('/'):
                        self.url_mapping['/' + relative_original] = hugo_path

                    # Map the original (non-normalized) version too
                    if original_url.startswith(self.base_url):
                        original_relative = original_url[len(self.base_url):]
                        if original_relative != relative_original:
                            self.url_mapping[original_relative] = hugo_path
                            if not original_relative.startswith('/'):
                                self.url_mapping['/' + original_relative] = hugo_path

        logger.info(f"Built URL mapping with {len(self.url_mapping)} entries")
        return data

    def find_hugo_file_for_url(self, original_url):
        """Find the Hugo markdown file that corresponds to an original URL"""
        # Search through all Hugo content files
        for md_file in self.content_dir.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Look for the original_url in the front matter
                    if f'original_url: "{original_url}"' in content:
                        # Convert file path to Hugo URL
                        relative_path = md_file.relative_to(self.content_dir)
                        # Remove .md extension and convert to URL path
                        url_path = str(relative_path.with_suffix(''))
                        return '/' + url_path.replace('\\', '/') + '/'
            except Exception as e:
                logger.warning(f"Error reading {md_file}: {e}")
                continue

        return None

    def fix_links_without_context(self, html_content):
        """Fix internal links when we don't have the original URL context"""
        if not html_content:
            return html_content

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links_fixed = 0

            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Skip external links, anchors, and mailto links
                if (href.startswith('http://') or href.startswith('https://') or
                    href.startswith('#') or href.startswith('mailto:') or
                    href.startswith('javascript:')):
                    continue

                # Try to match common patterns and fix them
                hugo_url = None

                # Clean the href by removing relative path indicators and normalize
                clean_href = href.lstrip('../')

                # Apply comprehensive URL normalization to the cleaned href
                if clean_href.startswith('/'):
                    # Absolute path - normalize it
                    normalized_href = normalize_url_path(self.base_url + clean_href.lstrip('/'))
                    if normalized_href.startswith(self.base_url):
                        clean_href = normalized_href[len(self.base_url):]
                else:
                    # Relative path - create a dummy URL to normalize path segments
                    dummy_url = f"https://example.com/{clean_href}"
                    normalized_dummy = normalize_url_path(dummy_url)
                    clean_href = normalized_dummy.replace("https://example.com/", "")

                # Try exact match first
                if clean_href in self.url_mapping:
                    hugo_url = self.url_mapping[clean_href]
                elif ('/' + clean_href) in self.url_mapping:
                    hugo_url = self.url_mapping['/' + clean_href]
                else:
                    # Try partial matching for complex relative paths
                    for original_path, hugo_path in self.url_mapping.items():
                        if clean_href in original_path or original_path.endswith(clean_href):
                            hugo_url = hugo_path
                            break
                        # Also try matching the filename part
                        if '/' in clean_href:
                            filename = clean_href.split('/')[-1]
                            if filename in original_path and original_path.endswith(filename):
                                hugo_url = hugo_path
                                break

                if hugo_url:
                    link['href'] = hugo_url
                    links_fixed += 1
                    logger.debug(f"Fixed link (no context): {href} -> {hugo_url}")

            if links_fixed > 0:
                logger.info(f"Fixed {links_fixed} internal links without context")

            return str(soup)

        except Exception as e:
            logger.error(f"Error fixing links without context: {e}")
            return html_content

    def normalize_relative_url(self, href, current_page_url):
        """Normalize a relative URL based on the current page's original URL"""
        try:
            # Join the relative URL with the current page's base URL
            full_url = urljoin(current_page_url, href)

            # Apply comprehensive URL normalization
            normalized_full_url = normalize_url_path(full_url)

            # Remove the base URL to get the relative path
            if normalized_full_url.startswith(self.base_url):
                relative_path = normalized_full_url[len(self.base_url):]
            else:
                parsed = urlparse(normalized_full_url)
                relative_path = parsed.path.lstrip('/')

            return relative_path
        except Exception as e:
            logger.warning(f"Error normalizing URL {href} from {current_page_url}: {e}")
            return href

    def fix_links_in_html(self, html_content, current_page_original_url):
        """Fix internal links in HTML content"""
        if not html_content:
            return html_content

        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            links_fixed = 0

            # Find all anchor tags with href attributes
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Skip external links, anchors, and mailto links
                if (href.startswith('http://') or href.startswith('https://') or
                    href.startswith('#') or href.startswith('mailto:') or
                    href.startswith('javascript:')):
                    continue

                # Normalize the relative URL to get the full original path
                normalized_href = self.normalize_relative_url(href, current_page_original_url)

                # Check if we have a mapping for this URL
                hugo_url = None

                # Try exact match first
                if normalized_href in self.url_mapping:
                    hugo_url = self.url_mapping[normalized_href]
                else:
                    # Try with leading slash
                    if ('/' + normalized_href) in self.url_mapping:
                        hugo_url = self.url_mapping['/' + normalized_href]
                    else:
                        # Try without leading slash
                        clean_href = normalized_href.lstrip('/')
                        if clean_href in self.url_mapping:
                            hugo_url = self.url_mapping[clean_href]

                if hugo_url:
                    link['href'] = hugo_url
                    links_fixed += 1
                    logger.debug(f"Fixed link: {href} -> {hugo_url}")
                else:
                    logger.debug(f"No mapping found for: {href} (normalized: {normalized_href})")

            if links_fixed > 0:
                logger.info(f"Fixed {links_fixed} internal links")

            return str(soup)

        except Exception as e:
            logger.error(f"Error fixing links in HTML: {e}")
            return html_content
            return html_content
    
    def fix_all_hugo_files(self):
        """Fix internal links in all Hugo markdown files"""
        logger.info("Starting to fix internal links in Hugo files...")
        
        data = self.load_data_and_build_mapping()
        
        # Create a mapping from Hugo files to original URLs for context
        file_to_original_url = {}
        for item in data:
            original_url = item.get('original_url', '')
            if original_url:
                hugo_path = self.find_hugo_file_for_url(original_url)
                if hugo_path:
                    # Convert Hugo URL back to file path
                    file_path = self.content_dir / (hugo_path.strip('/') + '.md')
                    file_to_original_url[file_path] = original_url
        
        total_files = 0
        files_with_fixes = 0
        
        # Process all markdown files
        for md_file in self.content_dir.rglob("*.md"):
            if md_file.name.startswith('_index.md'):
                continue  # Skip index files
                
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split front matter and content
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    front_matter = parts[1]
                    html_content = parts[2]
                    
                    # Get the original URL for this file
                    original_url = file_to_original_url.get(md_file)
                    if not original_url:
                        # Try to extract from front matter
                        original_url_match = re.search(r'original_url:\s*"([^"]+)"', front_matter)
                        if original_url_match:
                            original_url = original_url_match.group(1)
                    
                    # Fix links in the HTML content
                    original_html = html_content
                    if original_url:
                        fixed_html = self.fix_links_in_html(html_content, original_url)
                    else:
                        # For files without original_url, try pattern matching
                        fixed_html = self.fix_links_without_context(html_content)
                    
                    if fixed_html != original_html:
                        # Write back the fixed content
                        new_content = f"---{front_matter}---{fixed_html}"
                        with open(md_file, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        files_with_fixes += 1
                        context_type = "with context" if original_url else "without context"
                        logger.info(f"Fixed links ({context_type}) in: {md_file.relative_to(self.content_dir)}")
                
                total_files += 1
                
            except Exception as e:
                logger.error(f"Error processing {md_file}: {e}")
        
        logger.info(f"Processed {total_files} files, fixed links in {files_with_fixes} files")
        
        # Print some mapping examples for debugging
        logger.info("Sample URL mappings:")
        for i, (original, hugo) in enumerate(list(self.url_mapping.items())[:10]):
            logger.info(f"  {original} -> {hugo}")
        
        return files_with_fixes

def main():
    """Main function to run the improved link fixer"""
    fixer = ImprovedLinkFixer()
    files_fixed = fixer.fix_all_hugo_files()
    
    if files_fixed > 0:
        logger.info(f"✅ Successfully fixed internal links in {files_fixed} files!")
        logger.info("You may want to rebuild your Hugo site to see the changes.")
    else:
        logger.info("No files needed link fixes.")

if __name__ == "__main__":
    main()