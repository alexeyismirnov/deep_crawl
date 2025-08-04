#!/bin/bash

# Hugo Website Recreation Script
# This script recreates the orthodox-china Hugo website from scratch

echo "🏗️ Recreating Hugo Website: orthodox-china"
echo "=============================================="

# Step 1: Create Hugo site
echo "📁 Step 1: Creating new Hugo site..."
hugo new site orthodox-china
cd orthodox-china

# Step 2: Initialize git repository
echo "🔧 Step 2: Initializing git repository..."
git init

# Step 3: Add Hugo theme (using Book theme)
echo "🎨 Step 3: Adding Hugo Book theme..."
git submodule add https://github.com/alex-shpak/hugo-book themes/hugo-book
git submodule update --init --recursive

# Step 4: Create basic Hugo configuration
echo "⚙️ Step 4: Creating Hugo configuration..."
cat > hugo.toml << 'EOF'
baseURL = 'https://orthodox-china.netlify.app'
languageCode = 'ru'
title = 'Православие в Китае'
theme = 'hugo-book'

# Book configuration
disablePathToLower = true
enableGitInfo = true

# Needed for mermaid/katex shortcodes
[markup]
[markup.goldmark.renderer]
  unsafe = true

[markup.tableOfContents]
  startLevel = 1

# Multi-lingual mode config
# There are different options to translate files
# See https://gohugo.io/content-management/multilingual/#translation-by-filename
# And https://gohugo.io/content-management/multilingual/#translation-by-content-directory
[languages]
[languages.ru]
  languageName = 'Русский'
  contentDir = 'content'
  weight = 1

[menu]
# [[menu.before]]
[[menu.after]]
  name = "Github"
  url = "https://github.com/orthodox-china"
  weight = 10

[params]
  # (Optional, default light) Sets color theme: light, dark or auto.
  # Theme 'auto' switches between dark and light modes based on browser/os preferences
  BookTheme = 'light'

  # (Optional, default true) Controls table of contents visibility on right side of pages.
  # Start and end levels can be controlled with markup.tableOfContents setting.
  # You can also specify this parameter per page in front matter.
  BookToC = true

  # (Optional, default none) Set the path to a logo for the book. If the logo is
  # /static/logo.png then the path would be logo.png
  # BookLogo = 'logo.png'

  # (Optional, default none) Set leaf bundle to render as side menu
  # When not specified file structure and weights will be used
  # BookMenuBundle = '/menu'

  # (Optional, default docs) Specify root page to render child pages as menu.
  # Page is resoled by .GetPage function: https://gohugo.io/functions/getpage/
  # For backward compatibility you can set '*' to render all sections to menu. Acts same as '/'
  BookSection = '*'

  # Set source repository location.
  # Used for 'Last Modified' and 'Edit this page' links.
  BookRepo = 'https://github.com/orthodox-china/website'

  # (Optional, default 'commit') Specifies commit portion of the link to the page's last modified
  # commit hash for 'doc' page type.
  # Requires 'BookRepo' param.
  # Value used to construct a URL consisting of BookRepo/BookCommitPath/<commit-hash>
  # Github uses 'commit', Bitbucket uses 'commits'
  # BookCommitPath = 'commit'

  # Enable "Edit this page" links for 'doc' page type.
  # Disabled by default. Uncomment to enable. Requires 'BookRepo' param.
  # Edit path must point to root directory of repo.
  BookEditPage = false

  # Configure the date format used on the pages
  # - In git information
  # - In blog posts
  BookDateFormat = 'January 2, 2006'

  # (Optional, default true) Enables search function with flexsearch,
  # Index is built on fly, therefore it might slowdown your website.
  # Configuration for indexing can be adjusted in i18n folder per language.
  BookSearch = true

  # (Optional, default true) Enables comments template on pages
  # By default partals/docs/comments.html includes Disqus template
  # See https://gohugo.io/content-management/comments/#configure-disqus
  # Can be overwritten by same param in page frontmatter
  BookComments = false

  # /!\ This is an experimental feature, might be removed or changed at any time
  # (Optional, experimental, default false) Enables portable links and link checks in markdown pages.
  # Portable links meant to work with text editors and let you write markdown without {{< relref >}} shortcode
  # Theme will print warning if page referenced in markdown does not exists.
  BookPortableLinks = true

  # /!\ This is an experimental feature, might be removed or changed at any time
  # (Optional, experimental, default false) Enables service worker that caches visited pages and resources for offline use.
  BookServiceWorker = true

  # /!\ This is an experimental feature, might be removed or changed at any time
  # (Optional, experimental, default false) Enables a drop-down menu for translations only if a translation is present.
  BookTranslatedOnly = false
EOF

# Step 5: Initial git commit
echo "💾 Step 5: Creating initial git commit..."
git add .
git commit -m "Initial Hugo site setup for Orthodox China"

echo ""
echo "✅ Hugo website recreation completed!"
echo "=============================================="
echo "📁 Website directory: orthodox-china/"
echo "🌐 To run locally: cd orthodox-china && hugo server -D"
echo "🔨 To build: cd orthodox-china && hugo --gc --minify"
echo "📤 Ready for deployment to Netlify"
echo ""
echo "Next steps:"
echo "1. cd orthodox-china"
echo "2. hugo server -D (to test locally)"
echo "3. Push to GitHub and connect to Netlify for deployment"