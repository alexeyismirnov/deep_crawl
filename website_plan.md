# Website Reconstruction Plan

After a thorough analysis of the crawled data, I have developed a comprehensive plan to build a modern, user-friendly website. The current site's reliance on outdated frames, coupled with significant character encoding issues, necessitates a complete overhaul. The treasure trove of content, however, provides a solid foundation for a rich and informative new website.

Here is the detailed plan:

### **Phase 1: Content Rescue and Preparation**

The first priority is to extract, clean, and structure the valuable content from the crawled markdown files.

1.  **Automated Content Extraction & Cleaning:**
    *   Develop a script to parse all markdown files in the `output` directory.
    *   This script will extract key metadata: title, original URL, parent URL, and the full HTML content.
    *   The script should remove all <script> tags from HTML content.
    *   Crucially, the script will address the character encoding issues by detecting the original encoding (e.g., `gb2312`, `windows-1251`, `iso-8859-1`) and converting all content to the modern `UTF-8` standard. This will fix the garbled text.
    *   All extracted and cleaned data will be stored in a structured JSON file, creating a clean, portable, and machine-readable dataset to serve as the foundation for the new site.

2.  **Manual Verification:**
    *   Review the generated JSON file to manually verify the accuracy of the automated cleaning process and correct any remaining inconsistencies.

### **Phase 2: Information Architecture & User Experience**

With clean data, the next step is to design a new statically generated website using Hugo framework. The website
should be in RUSSIAN language, including navbar, menus, and content. No "language switching" component is necessary.

 Choose appropriate Hugo theme for an encyclopedia-style website, with a 2-level menu system (i.e. each menu in the navbar can have sub-menus).

 The Hugo website should be placed into "orthodox-china" sub-directory inside project root.

1.  **New Information Architecture:**
    *   Design a clear, hierarchical navigation system. To design the new structure we'll use metadata in JSON file
    generated in the previous step. Specifically, we'll be looking at the "original URL" and "parent URL" to infer the category each particular webpage belongs to. We'll analyze the relative URL part and assign a category to each page.

    In the generated website, all menus should be in RUSSIAN.

    *   **Proposed Site Structure (menus)**
        *   **Home:** A welcoming landing page with an introduction and links to featured content.
        *   **News:** Assign a page to this category if page URL contains "/news/" and if the page
        does not belong to any sub-categories below:
            *   **Archive** - assign to this sub-category if parent URL contains "/news/archive_ru.htm"
            *   **National news** - assign to this sub-category if parent URL contains "/news/index_ru.html"
            *   **Asian news** - assign to this sub-category if parent URL contains "/news/asia_ru.html"
            *   **International** - assign to this sub-category if parent URL contains "/news/intl_ru.htm"
            *   **Events** - assign to this sub-category if parent URL contains "/news/events_ru.htm"
            *   **Interview**  - assign to this sub-category if parent URL contains "/news/interview_ru.htm"
            *  **Publications** - assign to this sub-category if parent URL contains "/news/books_ru.htm"
        *   **Church today**  Assign a page to this category if page URL contains "/contemporary/" and if the page
        does not belong to any sub-categories below:
            *   **Dioceses** - assign to this sub-category if parent URL contains "contemporary/diocese_ru.htm"
            *   **Parishes** - assign to this sub-category if parent URL contains "contemporary/parish_ru.htm"
            *   **Official** - assign to this sub-category if parent URL contains "contemporary/officialdoc_ru.htm"
            *   **Persons** - assign to this sub-category if parent URL contains "contemporary/persons_ru.htm"
            *   **Father Alexander** - assign to this sub-category if parent URL 
            contains "contemporary/fatheralexander_ru.htm"
        *   **Orthodox Church of China** - this menu has no sub-menus. assign to this category if 
        parent URL contains "/localchurch/index_ru.html"
        *   **Catechism** - this menu has no sub-menus. assign to this category if 
        parent URL contains "/catechesis/index_ru.html"
        *   **Other** - assign to this category all pages that have not been assigned to any other category
  
  When creating Markdown files for Hugo, make sure that in 'title' and 'description' metadata fields, all qoute characters are escaped. Otherwise, parsing errors may occur.