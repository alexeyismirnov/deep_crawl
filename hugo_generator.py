#!/usr/bin/env python3
"""
Hugo Content Generator
Generates Hugo markdown files from the extracted JSON data
"""

import os
import json
import re
from pathlib import Path
import logging
from datetime import datetime
import html

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HugoContentGenerator:
    def __init__(self, json_file="extracted_content.json", hugo_dir="orthodox-china"):
        self.json_file = json_file
        self.hugo_dir = Path(hugo_dir)
        self.content_dir = self.hugo_dir / "content"
        self.data = []
        
        # Russian menu translations
        self.menu_translations = {
            "News": "Новости",
            "News/Archive": "Архив",
            "News/National news": "Национальные новости", 
            "News/Asian news": "Новости Азии",
            "News/International": "Международные новости",
            "News/Events": "События",
            "News/Interview": "Интервью",
            "News/Publications": "Публикации",
            "Church today": "Церковь сегодня",
            "Church today/Dioceses": "Епархии",
            "Church today/Parishes": "Приходы", 
            "Church today/Official": "Официальные документы",
            "Church today/Persons": "Персоналии",
            "Church today/Father Alexander": "Отец Александр",
            "Orthodox Church of China": "Православная Церковь Китая",
            "Catechism": "Катехизис",
            "Other": "Прочее"
        }
        
    def load_data(self):
        """Load extracted data from JSON file"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            logger.info(f"Loaded {len(self.data)} items from {self.json_file}")
        except Exception as e:
            logger.error(f"Failed to load JSON data: {e}")
            return False
        return True
    
    def sanitize_filename(self, text):
        """Create a safe filename from text"""
        if not text:
            return "untitled"
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Replace special characters
        text = re.sub(r'[^\w\s-]', '', text)
        # Replace spaces with hyphens
        text = re.sub(r'[-\s]+', '-', text)
        # Convert to lowercase
        text = text.lower().strip('-')
        # Limit length
        if len(text) > 50:
            text = text[:50].rstrip('-')

        return text or "untitled"

    def escape_yaml_string(self, text):
        """Escape quotes and special characters in YAML strings"""
        if not text:
            return ""

        # Remove HTML tags first
        text = re.sub(r'<[^>]+>', '', text)
        # Replace backslashes first (must be done before other escaping)
        text = text.replace('\\', '\\\\')
        # Escape quotes
        text = text.replace('"', '\\"')
        # Remove newlines and extra spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text
        
        # Remove HTML tags first
        text = re.sub(r'<[^>]+>', '', text)
        # Escape quotes
        text = text.replace('"', '\\"').replace("'", "\\'")
        # Remove newlines and extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_category_path(self, category):
        """Convert category to file path"""
        if not category or category == "Other":
            return "other"
        
        # Convert category to path
        path_parts = category.lower().split('/')
        path_parts = [self.sanitize_filename(part) for part in path_parts]
        return '/'.join(path_parts)
    
    def get_menu_weight(self, category):
        """Get menu weight for ordering"""
        weights = {
            "News": 10,
            "News/Archive": 11,
            "News/National news": 12,
            "News/Asian news": 13,
            "News/International": 14,
            "News/Events": 15,
            "News/Interview": 16,
            "News/Publications": 17,
            "Church today": 20,
            "Church today/Dioceses": 21,
            "Church today/Parishes": 22,
            "Church today/Official": 23,
            "Church today/Persons": 24,
            "Church today/Father Alexander": 25,
            "Orthodox Church of China": 30,
            "Catechism": 40,
            "Other": 90
        }
        return weights.get(category, 99)
    
    def create_content_file(self, item, index):
        """Create a Hugo content file from an item"""
        category = item.get('category', 'Other')
        title = item.get('title', 'Без названия')
        
        # Create directory structure
        category_path = self.get_category_path(category)
        content_path = self.content_dir / category_path
        content_path.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        safe_title = self.sanitize_filename(title)
        filename = f"{safe_title}.md"
        file_path = content_path / filename
        
        # Prepare content
        html_content = item.get('html_content', '')
        clean_text = item.get('clean_text', '')
        original_url = item.get('original_url', '')
        parent_url = item.get('parent_url', '')
        
        # Create front matter - no menu entries for individual articles
        front_matter = f"""---
title: "{self.escape_yaml_string(title)}"
date: {datetime.now().strftime('%Y-%m-%d')}
draft: false
weight: {index}
bookToc: true
bookComments: false
bookSearchExclude: false
bookHidden: true
"""

        # Add metadata
        if original_url:
            front_matter += f'original_url: "{original_url}"\n'
        if parent_url:
            front_matter += f'parent_url: "{parent_url}"\n'
        if item.get('depth') is not None:
            front_matter += f'depth: {item.get("depth")}\n'

        front_matter += "---\n\n"
        
        # Create content
        content = front_matter
        
        # Add original URL info if available
        if original_url:
            content += f"**Оригинальный URL:** {original_url}\n\n"
        
        # Add HTML content
        if html_content:
            content += html_content
        elif clean_text:
            content += f"<p>{html.escape(clean_text)}</p>"
        else:
            content += "<p>Содержимое недоступно</p>"
        
        # Write file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Created {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create {file_path}: {e}")
            return False
    
    def create_section_index_files(self):
        """Create _index.md files for each section"""
        sections = {}

        # Collect all categories
        for item in self.data:
            category = item.get('category', 'Other')
            if category not in sections:
                sections[category] = []
            sections[category].append(item)

        # Analyze category hierarchy
        parent_categories = set()
        subcategories = {}

        for category in sections.keys():
            if '/' in category:
                parent = category.split('/')[0]
                parent_categories.add(parent)
                if parent not in subcategories:
                    subcategories[parent] = []
                subcategories[parent].append(category)
            else:
                parent_categories.add(category)

        # Create parent category index files even if they have no direct items
        for parent in parent_categories:
            if parent in subcategories and len(subcategories[parent]) > 0:
                # This is a parent category with subcategories
                if parent not in sections:
                    # Create empty sections entry for parent categories with no direct items
                    sections[parent] = []

        # Create index files for each section
        for category, items in sections.items():
            category_path = self.get_category_path(category)
            section_dir = self.content_dir / category_path
            section_dir.mkdir(parents=True, exist_ok=True)

            index_file = section_dir / "_index.md"

            # Get Russian title
            russian_title = self.menu_translations.get(category, category)

            # Create index content - no menu entries, let Hugo config handle main menu
            front_matter = f"""---
title: "{russian_title}"
weight: {self.get_menu_weight(category)}
bookCollapseSection: true
bookFlatSection: false
---

"""

            content = front_matter
            content += f"# {russian_title}\n\n"

            # Check if this is a parent category with subcategories
            is_parent_category = category in subcategories and len(subcategories[category]) > 0

            if is_parent_category:
                # For parent categories, show subcategories first, then individual pages
                subcats = subcategories[category]
                direct_items_count = len(items)

                # Calculate total items in all subcategories
                total_subcat_items = 0
                for subcat in subcats:
                    if subcat in sections:
                        total_subcat_items += len(sections[subcat])

                if direct_items_count > 0:
                    content += f"В этом разделе {direct_items_count} материалов в {len(subcats)} подразделах.\n\n"
                else:
                    content += f"В этом разделе {total_subcat_items} материалов в {len(subcats)} подразделах.\n\n"

                # Add subcategories section
                content += "## Подразделы:\n\n"
                sorted_subcats = sorted(subcats, key=lambda x: self.get_menu_weight(x))

                for subcat in sorted_subcats:
                    if subcat in sections:
                        subcat_russian_title = self.menu_translations.get(subcat, subcat.split('/')[-1])
                        # Get the subcategory path relative to the parent
                        subcat_relative_path = self.get_category_path(subcat.split('/')[-1])
                        subcat_count = len(sections[subcat])
                        content += f"- [{subcat_russian_title}]({subcat_relative_path}/) ({subcat_count} материалов)\n"

                content += "\n"

                # Add individual pages in this category (if any)
                if direct_items_count > 0:
                    content += "## Статьи в этом разделе:\n\n"
                    # Sort items by title
                    sorted_items = sorted(items, key=lambda x: x.get('title', ''))
                    for item in sorted_items:
                        title = item.get('title', 'Без названия')
                        # Create relative link to the article
                        safe_title = self.sanitize_filename(title)
                        article_link = f"{safe_title}/"
                        content += f"- [{title}]({article_link})\n"
                    content += "\n"
            else:
                # For subcategories and leaf categories, just show the articles
                content += f"В этом разделе {len(items)} материалов.\n\n"
                content += "## Статьи в этом разделе:\n\n"
                # Sort items by title
                sorted_items = sorted(items, key=lambda x: x.get('title', ''))
                for item in sorted_items:
                    title = item.get('title', 'Без названия')
                    # Create relative link to the article
                    safe_title = self.sanitize_filename(title)
                    article_link = f"{safe_title}/"
                    content += f"- [{title}]({article_link})\n"
                content += "\n"

            # Write index file
            try:
                with open(index_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created section index: {index_file}")
            except Exception as e:
                logger.error(f"Failed to create section index {index_file}: {e}")
    
    def create_home_page(self):
        """Create the home page"""
        home_file = self.content_dir / "_index.md"
        
        content = """---
title: "Православие в Китае"
type: docs
bookToc: false
---

# Добро пожаловать на сайт "Православие в Китае"

Этот сайт содержит обширную коллекцию материалов о Православной Церкви в Китае, включая:

## Разделы сайта

### 📰 [Новости](news/)
Актуальные новости о жизни Православной Церкви в Китае и мире:
- Национальные новости
- Новости Азии  
- Международные новости
- События и интервью
- Публикации

### ⛪ [Церковь сегодня](church-today/)
Современное состояние Православной Церкви:
- Епархии и приходы
- Официальные документы
- Персоналии
- Материалы отца Александра

### 🇨🇳 [Православная Церковь Китая](orthodox-church-of-china/)
История и современность Православия в Китае

### 📚 [Катехизис](catechism/)
Образовательные и катехизические материалы

---

*Сайт создан на основе архивных материалов orthodox.cn*
"""
        
        try:
            with open(home_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Created home page: {home_file}")
        except Exception as e:
            logger.error(f"Failed to create home page: {e}")
    
    def generate_all_content(self):
        """Generate all Hugo content"""
        logger.info("Starting Hugo content generation...")
        
        # Create content directory
        self.content_dir.mkdir(parents=True, exist_ok=True)
        
        # Create home page
        self.create_home_page()
        
        # Create section index files
        self.create_section_index_files()
        
        # Create individual content files
        success_count = 0
        for index, item in enumerate(self.data, 1):
            if self.create_content_file(item, index):
                success_count += 1
        
        logger.info(f"Successfully created {success_count}/{len(self.data)} content files")
        
    def print_statistics(self):
        """Print generation statistics"""
        categories = {}
        for item in self.data:
            category = item.get('category', 'Other')
            categories[category] = categories.get(category, 0) + 1
        
        logger.info("\n=== HUGO CONTENT GENERATION STATISTICS ===")
        logger.info(f"Total content files: {len(self.data)}")
        logger.info("\nBy category:")
        for category, count in sorted(categories.items()):
            russian_name = self.menu_translations.get(category, category)
            logger.info(f"  {russian_name} ({category}): {count}")
    
    def run(self):
        """Run the complete content generation process"""
        if not self.load_data():
            return False
        
        self.generate_all_content()
        self.print_statistics()
        logger.info("Hugo content generation completed!")
        return True

if __name__ == "__main__":
    generator = HugoContentGenerator()
    generator.run()