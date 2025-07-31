# Website Reconstruction Plan

After a thorough analysis of the crawled data, I have developed a comprehensive plan to build a modern, user-friendly website. The current site's reliance on outdated frames, coupled with significant character encoding issues, necessitates a complete overhaul. The treasure trove of content, however, provides a solid foundation for a rich and informative new website.

Here is the detailed plan:

### **Phase 1: Content Rescue and Preparation**

The first priority is to extract, clean, and structure the valuable content from the crawled markdown files.

1.  **Automated Content Extraction & Cleaning:**
    *   Develop a script to parse all markdown files in the `output` directory.
    *   This script will extract key metadata: title, original URL, and the full HTML content.
    *   Crucially, the script will address the character encoding issues by detecting the original encoding (e.g., `gb2312`, `windows-1251`, `iso-8859-1`) and converting all content to the modern `UTF-8` standard. This will fix the garbled text.
    *   All extracted and cleaned data will be stored in a structured JSON file, creating a clean, portable, and machine-readable dataset to serve as the foundation for the new site.

2.  **Manual Verification:**
    *   Review the generated JSON file to manually verify the accuracy of the automated cleaning process and correct any remaining inconsistencies.

### **Phase 2: Information Architecture & User Experience**

With clean data, the next step is to design a logical and intuitive structure for the new website.

1.  **New Information Architecture:**
    *   Discard the confusing frameset structure and design a clear, hierarchical navigation system. The new structure will be organized by topic, making it easy for users to find information.

    *   **Proposed Site Structure:**
        *   **Home:** A welcoming landing page with an introduction and links to featured content.
        *   **About:**
            *   History of Orthodoxy in China
            *   Dioceses and Parishes
            *   Clergy and People
        *   **Faith & Doctrine:**
            *   Catechism
            *   Theology & Patristics
            *   Holy Scriptures
        *   **Worship & Liturgy:**
            *   Liturgical Texts
            *   Church Calendar
            *   Icons
        *   **News & Media:**
            *   Latest News
            *   Publications & Journals
            *   Multimedia (Audio/Video)
        *   **Resources:**
            *   Links
            *   Donations

2.  **Modern URL Structure:**
    *   Implement clean, human-readable, and SEO-friendly URLs. For example:
        *   `https://orthodox.cn/en/about/history`
        *   `https://orthodox.cn/ru/faith-doctrine/catechism`
        *   `https://orthodox.cn/zh/worship-liturgy/icons`

### **Phase 3: Website Development & Deployment**

This phase focuses on building the new website using modern web technologies.

1.  **Technology Choices:**
    *   **Static Site Generator (SSG):** Use a modern SSG like **Hugo** or **Next.js**. This approach will produce a website that is extremely fast, secure, and requires minimal maintenance.
    *   **Frontend Framework:** Use a modern CSS framework like **Tailwind CSS** to create a clean, responsive, and aesthetically pleasing design that works on all devices.

2.  **Development Process:**
    *   Build a set of reusable templates for different page types (e.g., home, article, section landing page).
    *   The clean data from Phase 1 will be used to programmatically generate all the pages of the website.
    *   A client-side search feature will be implemented using a library like **Lunr.js**, allowing users to easily search the entire site's content.
    *   The final static website will be deployed to a modern hosting platform like **Netlify** or **Vercel**, which provides excellent performance and reliability.