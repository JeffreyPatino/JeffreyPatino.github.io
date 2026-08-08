#!/usr/bin/env python3
import os
import re
import sys
import glob

try:
    import markdown
    HAS_MARKDOWN_LIB = True
except ImportError:
    HAS_MARKDOWN_LIB = False

POSTS_DIR = os.path.join(os.path.dirname(__file__), 'content', 'posts')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'writing')
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'article_template.html')
INDEX_PATH = os.path.join(os.path.dirname(__file__), 'index.html')

def parse_frontmatter(content):
    frontmatter = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2].strip()
            current_key = None
            for line in fm_text.split('\n'):
                line = line.rstrip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line and not line.startswith(' '):
                    key, val = line.split(':', 1)
                    key = key.strip()
                    val = val.strip()
                    if val.startswith('[') and val.endswith(']'):
                        items = [item.strip().strip("'\"") for item in val[1:-1].split(',')]
                        frontmatter[key] = [i for i in items if i]
                    elif not val:
                        frontmatter[key] = []
                        current_key = key
                    else:
                        frontmatter[key] = val.strip("'\"")
                elif line.startswith('  - ') and current_key:
                    item = line.replace('  - ', '').strip().strip("'\"")
                    if isinstance(frontmatter[current_key], list):
                        frontmatter[current_key].append(item)
    return frontmatter, body

def simple_md_to_html(md_text):
    if HAS_MARKDOWN_LIB:
        return markdown.markdown(md_text, extensions=['fenced_code', 'codehilite', 'tables'])

    blocks = {}
    block_counter = 0

    # Extract Code blocks first
    def code_block_sub(match):
        nonlocal block_counter
        lang = match.group(1) or 'clike'
        code = match.group(2).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        placeholder = f'__BLOCK_{block_counter}__'
        blocks[placeholder] = f'<pre><code class="language-{lang}">{code.strip()}</code></pre>'
        block_counter += 1
        return placeholder

    html = re.sub(r'```(\w+)?\n(.*?)```', code_block_sub, md_text, flags=re.DOTALL)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Headers
    html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.*$)', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Unordered Lists
    html = re.sub(r'^\* (.*$)', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^- (.*$)', r'<li>\1</li>', html, flags=re.MULTILINE)

    # Wrap sequential <li> tags in <ul>
    html = re.sub(r'((?:<li>.*?</li>\s*)+)', r'<ul>\1</ul>', html, flags=re.DOTALL)

    # Paragraphs (separation by double newlines)
    paragraphs = html.split('\n\n')
    formatted = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if p.startswith('<h') or p.startswith('<ul') or p.startswith('<blockquote') or p in blocks:
            formatted.append(p)
        else:
            p_clean = p.replace('\n', ' ')
            formatted.append(f'<p>{p_clean}</p>')

    res = '\n'.join(formatted)

    # Restore code blocks
    for ph, block_content in blocks.items():
        res = res.replace(ph, block_content)

    return res

def build():
    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    md_files = glob.glob(os.path.join(POSTS_DIR, '*.md'))
    posts = []

    for filepath in md_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()

        fm, body = parse_frontmatter(raw_content)
        title = fm.get('title', 'Untitled')
        subtitle = fm.get('subtitle', '')
        date = fm.get('date', 'Undated')
        slug = fm.get('slug', os.path.splitext(os.path.basename(filepath))[0])
        reading_time = fm.get('reading_time', '5 min')
        tags = fm.get('tags', [])
        summary = fm.get('summary', '')

        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',')]

        body_html = simple_md_to_html(body)
        tags_html = ''.join([f'<span class="portfolio__tech">{t}</span>' for t in tags])

        # Generate standalone article page
        post_html = template
        post_html = post_html.replace('{{TITLE}}', title)
        post_html = post_html.replace('{{SUBTITLE}}', subtitle)
        post_html = post_html.replace('{{DATE}}', date)
        post_html = post_html.replace('{{READING_TIME}}', reading_time)
        post_html = post_html.replace('{{TAGS_HTML}}', tags_html)
        post_html = post_html.replace('{{CONTENT}}', body_html)

        out_path = os.path.join(OUTPUT_DIR, f'{slug}.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(post_html)

        posts.append({
            'title': title,
            'subtitle': subtitle,
            'date': date,
            'slug': slug,
            'reading_time': reading_time,
            'tags_html': tags_html,
            'summary': summary,
            'filepath': filepath
        })
        print(f"Generated writing/{slug}.html")

    # Sort posts by date descending if possible
    posts.sort(key=lambda x: x['date'], reverse=True)

    # Generate homepage cards HTML
    cards_html = []
    if not posts:
        cards_html.append('''
        <article class="portfolio__card writing__card">
            <div class="portfolio__content">
                <div class="portfolio__info">
                    <h3 class="portfolio__title">Technical Deep Dives Coming Soon</h3>
                    <p class="portfolio__description">Detailed security analysis, reverse engineering breakdowns, and system architecture explorations will be posted here.</p>
                </div>
            </div>
        </article>
        ''')
    else:
        for p in posts:
            card = f'''
            <article class="portfolio__card writing__card">
                <div class="portfolio__content">
                    <div class="portfolio__info">
                        <span class="writing__date"><i class="uil uil-calendar-alt"></i> {p['date']} &bull; {p['reading_time']} read</span>
                        <h3 class="portfolio__title">{p['title']}</h3>
                        <p class="portfolio__description">{p['summary'] or p['subtitle']}</p>
                        <div class="portfolio__technologies">
                            {p['tags_html']}
                        </div>
                        <a href="writing/{p['slug']}.html" class="portfolio__demo">
                            Read Deep Dive <i class="uil uil-arrow-right"></i>
                        </a>
                    </div>
                </div>
            </article>
            '''
            cards_html.append(card.strip())

    writing_cards_block = '\n'.join(cards_html)

    # Update index.html between markers
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, 'r', encoding='utf-8') as f:
            index_content = f.read()

        start_marker = '<!--==================== WRITING CARDS START ====================-->'
        end_marker = '<!--==================== WRITING CARDS END ====================-->'

        if start_marker in index_content and end_marker in index_content:
            pattern = re.escape(start_marker) + r'.*?' + re.escape(end_marker)
            replacement = f"{start_marker}\n{writing_cards_block}\n{end_marker}"
            new_index_content = re.sub(pattern, replacement, index_content, flags=re.DOTALL)
            with open(INDEX_PATH, 'w', encoding='utf-8') as f:
                f.write(new_index_content)
            print("Updated writing section cards in index.html")
        else:
            print("Notice: Start/End markers for writing cards not yet added to index.html.")

if __name__ == '__main__':
    build()
