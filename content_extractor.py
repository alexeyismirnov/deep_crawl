#!/usr/bin/env python3
"""
Content Extraction and Cleaning Script
Extracts content from crawled markdown files and creates a structured JSON dataset
"""

import json
import re
from bs4 import BeautifulSoup
from pathlib import Path
import logging
from urllib.parse import urlparse, urljoin, urlunparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self, output_dir="output", json_output="extracted_content.json"):
        self.output_dir = Path(output_dir)
        self.json_output = json_output
        self.extracted_data = []

    def normalize_url_path(self, url):
        """
        Normalize URL by resolving '..' and '.' path segments

        Args:
            url (str): URL to normalize

        Returns:
            str: Normalized URL with resolved path segments
        """
        if not url:
            return url

        try:
            # Parse the URL
            parsed = urlparse(url)

            # Split the path into segments
            path_segments = parsed.path.split('/')

            # Resolve '..' and '.' segments
            normalized_segments = []
            for segment in path_segments:
                if segment == '..':
                    # Go up one level (remove last segment if exists)
                    if normalized_segments:
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

            # Reconstruct the URL
            normalized_parsed = parsed._replace(path=normalized_path)
            return urlunparse(normalized_parsed)

        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return url

    def detect_and_fix_encoding(self, text):
        """
        Detect and fix character encoding issues
        """
        if not text:
            return text
            
        # Try to detect if text is already properly encoded
        try:
            # If it's already UTF-8, return as is
            text.encode('utf-8')
            return text
        except UnicodeEncodeError:
            pass
            
        # Try to fix common encoding issues
        try:
            # Try to decode as various encodings and re-encode as UTF-8
            for encoding in ['gb2312', 'gbk', 'windows-1251', 'iso-8859-1', 'cp1252']:
                try:
                    # First encode to bytes if it's a string, then decode with the encoding
                    if isinstance(text, str):
                        bytes_text = text.encode('latin1', errors='ignore')
                    else:
                        bytes_text = text
                    
                    decoded = bytes_text.decode(encoding, errors='ignore')
                    return decoded
                except (UnicodeDecodeError, UnicodeEncodeError, LookupError):
                    continue
        except Exception as e:
            logger.warning(f"Encoding fix failed: {e}")
            
        return text
    
    def clean_html_content(self, html_content):
        """
        Clean HTML content by removing scripts and fixing encoding
        """
        if not html_content:
            return ""
            
        # Fix encoding issues first
        html_content = self.detect_and_fix_encoding(html_content)
        
        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script tags
        for script in soup.find_all('script'):
            script.decompose()
            
        # Remove style tags (optional, but helps with cleaner content)
        for style in soup.find_all('style'):
            style.decompose()
            
        # Return cleaned HTML
        return str(soup)
    
    def extract_metadata_from_markdown(self, file_path):
        """
        Extract metadata and content from a markdown file
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return None
            
        # Initialize metadata
        metadata = {
            'file_path': str(file_path),
            'title': '',
            'original_url': '',
            'parent_url': '',
            'html_content': '',
            'clean_text': '',
            'depth': None,
            'page_type': '',
            'category': 'Other'  # Default category
        }

        # Extract title from markdown
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()

        # Extract HTML content from ## Content section
        content_match = re.search(r'## Content\s*\n\n(.*?)(?=\n## |$)', content, re.DOTALL)
        if content_match:
            html_content = content_match.group(1).strip()
            metadata['html_content'] = self.clean_html_content(html_content)

            # Extract clean text for search/indexing
            soup = BeautifulSoup(metadata['html_content'], 'html.parser')
            metadata['clean_text'] = soup.get_text(strip=True)
        else:
            # Fallback: look for HTML in code blocks
            html_matches = re.findall(r'```html\n(.*?)\n```', content, re.DOTALL)
            if html_matches:
                # Take the largest HTML block (usually the main content)
                html_content = max(html_matches, key=len)
                metadata['html_content'] = self.clean_html_content(html_content)

                # Extract clean text for search/indexing
                soup = BeautifulSoup(metadata['html_content'], 'html.parser')
                metadata['clean_text'] = soup.get_text(strip=True)

        # Extract original URL
        url_match = re.search(r'\*\*URL:\*\*\s*(.+)$', content, re.MULTILINE)
        if url_match:
            metadata['original_url'] = url_match.group(1).strip()

        # Extract parent URL
        parent_match = re.search(r'\*\*Parent URL:\*\*\s*(.+)$', content, re.MULTILINE)
        if parent_match:
            metadata['parent_url'] = parent_match.group(1).strip()
            
        # Extract HTML content (usually in code blocks)
        html_matches = re.findall(r'```html\n(.*?)\n```', content, re.DOTALL)
        if html_matches:
            # Take the largest HTML block (usually the main content)
            html_content = max(html_matches, key=len)
            metadata['html_content'] = self.clean_html_content(html_content)
            
            # Extract clean text for search/indexing
            soup = BeautifulSoup(metadata['html_content'], 'html.parser')
            metadata['clean_text'] = soup.get_text(strip=True)
            
        # Determine depth from filename
        if 'depth1_' in file_path.name:
            metadata['depth'] = 1
        elif 'depth2_' in file_path.name:
            metadata['depth'] = 2
        elif 'depth3_' in file_path.name:
            metadata['depth'] = 3
        elif 'depth4_' in file_path.name:
            metadata['depth'] = 4
        elif 'depth5_' in file_path.name:
            metadata['depth'] = 5
        elif any(frame in file_path.name for frame in ['MENU', 'title', 'CONTENT']):
            metadata['depth'] = 0
            metadata['page_type'] = 'frame'
            
        # Determine category based on URLs
        metadata['category'] = self.categorize_page(metadata['original_url'], metadata['parent_url'])
        
        return metadata
    
    def categorize_page(self, original_url, parent_url):
        """
        Categorize pages based on URL patterns according to the plan
        """
        # Normalize URLs to resolve '..' and '.' path segments
        original_url = self.normalize_url_path(original_url)
        parent_url = self.normalize_url_path(parent_url)

        # Convert to lowercase for easier matching
        orig_lower = original_url.lower() if original_url else ""
        parent_lower = parent_url.lower() if parent_url else ""

        # Orthodox Church of China - check original URL first for saints
        if "/saints/" in orig_lower:
            return "Orthodox Church of China/Holy people and holy icons"

            # Saints pages should always be categorized as Orthodox Church of China
            #if "saints/index_ru.html" in parent_lower:
            #else:
            #    return "Orthodox Church of China"

        # Orthodox Church of China - check for localchurch
        elif "/localchurch/" in orig_lower or "/localchurch/" in parent_lower:
            # Check sub-categories first (based on parent URL)
            if "localchurch/diocese_ru.htm" in parent_lower:
                return "Orthodox Church of China/Dioceses"
            elif "localchurch/persons_ru.htm" in parent_lower:
                return "Orthodox Church of China/Persons"
            elif "localchurch/mission_ru.htm" in parent_lower:
                return "Orthodox Church of China/Russian Spiritual Mission"
            else:
                return "Orthodox Church of China"

        # News categories - check both original URL and parent URL
        elif "/news/" in orig_lower or "/news/" in parent_lower:
            # Check sub-categories first (based on parent URL)
            if "/news/archive_ru.htm" in parent_lower:
                return "News/Archive"
            elif "/news/index_ru.html" in parent_lower:
                return "News/National news"
            elif "/news/asia_ru.htm" in parent_lower:
                return "News/Asian news"
            elif "/news/intl_ru.htm" in parent_lower:
                return "News/International"
            elif "/news/events_ru.htm" in parent_lower:
                return "News/Events"
            elif "/news/interview_ru.htm" in parent_lower:
                return "News/Interview"
            elif "/news/books_ru.htm" in parent_lower:
                return "News/Publications"
            else:
                return "News"

        # Church today categories - check both original URL and parent URL
        elif "/contemporary/" in orig_lower or "/contemporary/" in parent_lower:
            if "contemporary/diocese_ru.htm" in parent_lower:
                return "Church today/Dioceses"
            elif "contemporary/parish_ru.htm" in parent_lower:
                return "Church today/Parishes"
            elif "contemporary/officialdoc_ru.htm" in parent_lower:
                return "Church today/Official"
            elif "contemporary/persons_ru.htm" in parent_lower:
                return "Church today/Persons"
            elif "contemporary/fatheralexander_ru.htm" in parent_lower:
                return "Church today/Father Alexander"
            else:
                return "Church today"

        # Catechism
        elif "/catechesis/" in parent_lower:
            return "Catechism"

        # Default category
        else:
            return "Other"
    
    def process_all_files(self):
        """
        Process all markdown files in the output directory
        """
        logger.info(f"Processing files in {self.output_dir}")
        
        # Find all markdown files
        md_files = list(self.output_dir.glob("*.md"))
        logger.info(f"Found {len(md_files)} markdown files")
        
        for file_path in md_files:
            logger.info(f"Processing {file_path.name}")
            metadata = self.extract_metadata_from_markdown(file_path)
            
            if metadata:
                self.extracted_data.append(metadata)
            else:
                logger.warning(f"Failed to extract metadata from {file_path.name}")
                
        logger.info(f"Successfully processed {len(self.extracted_data)} files")
        
    def save_to_json(self):
        """
        Save extracted data to JSON file
        """
        try:
            with open(self.json_output, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved extracted data to {self.json_output}")
        except Exception as e:
            logger.error(f"Failed to save JSON: {e}")
            
    def print_statistics(self):
        """
        Print statistics about the extracted data
        """
        total_files = len(self.extracted_data)
        categories = {}
        depths = {}
        
        for item in self.extracted_data:
            # Count categories
            category = item['category']
            categories[category] = categories.get(category, 0) + 1
            
            # Count depths
            depth = item['depth']
            if depth is not None:
                depths[depth] = depths.get(depth, 0) + 1
                
        logger.info(f"\n=== EXTRACTION STATISTICS ===")
        logger.info(f"Total files processed: {total_files}")
        logger.info(f"\nBy category:")
        for category, count in sorted(categories.items()):
            logger.info(f"  {category}: {count}")
        logger.info(f"\nBy depth:")
        for depth, count in sorted(depths.items()):
            logger.info(f"  Depth {depth}: {count}")
            
    def run(self):
        """
        Run the complete extraction process
        """
        logger.info("Starting content extraction process...")
        self.process_all_files()
        self.save_to_json()
        self.print_statistics()
        logger.info("Content extraction completed!")

if __name__ == "__main__":
    extractor = ContentExtractor()
    extractor.run()