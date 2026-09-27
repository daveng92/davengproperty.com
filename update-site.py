#!/usr/bin/env python3
"""
update-site.py — Merges website-data.json into index.html
Used by GitHub Actions to update the news and listings sections
of Dave Ng's property website without touching the template.
"""
import json
import re
import sys
import html

# SVG icons mapped by name
ICONS = {
    "house": '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/>',
    "layers": '<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>',
    "chart": '<path d="M16 8v8M12 11v5M8 14v2M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2z"/>',
    "trending": '<path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>',
    "gavel": '<path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/><circle cx="12" cy="12" r="4"/>',
    "dollar": '<path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>',
    "building": '<path d="M3 21h18M9 8h1M9 12h1M9 16h1M14 8h1M14 12h1M14 16h1M5 21V5a2 2 0 012-2h10a2 2 0 012 2v16"/>',
    "key": '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.78 7.78 5.5 5.5 0 017.78-7.78zM15.5 7.5l3 3L22 7l-3-3"/>',
}

def build_news_card(article):
    icon_key = article.get("icon", "house")
    icon_path = ICONS.get(icon_key, ICONS["house"])
    title_escaped = html.escape(article["title"]).replace("'", "&rsquo;").replace("'", "&rsquo;")
    summary_escaped = html.escape(article["summary"]).replace("'", "&rsquo;").replace("—", "&mdash;")

    return f'''<a href="{article['url']}" target="_blank" rel="noopener noreferrer" class="news-card" style="text-decoration:none;color:inherit;cursor:pointer">
            <div class="news-img" style="background:{article['gradient']};display:flex;align-items:center;justify-content:center">
              <svg width="48" height="48" fill="none" stroke="rgba(255,255,255,.5)" stroke-width="1.5" viewBox="0 0 24 24">{icon_path}</svg>
              <span class="news-source">{html.escape(article['source'])}</span>
            </div>
            <div class="news-body">
              <div class="news-date">{html.escape(article['date'])}</div>
              <h4 style="font-size:16px;margin-bottom:8px;line-height:1.4">{title_escaped}</h4>
              <p style="font-size:13px;color:var(--text-muted);line-height:1.6">{summary_escaped}</p>
              <span class="news-link">Read Full Article &rarr;</span>
            </div>
          </a>'''

def build_news_section(articles):
    cards = "".join(build_news_card(a) for a in articles)
    return f'''<div class="news-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:24px;margin:32px 0">

          {cards}

        </div>'''

def update_html(html_content, data):
    # Update news section
    news_pattern = r'(<div class="news-grid"[^>]*>).*?(</div>\s*\n\s*(?:</div>|<div class="cta-banner"))'
    news_html = build_news_section(data["news"])

    # Find and replace the news-grid div content
    start_marker = '<div class="news-grid"'
    end_marker = '\n        </div>'

    start_idx = html_content.find(start_marker, html_content.find('id="news-container"'))
    if start_idx == -1:
        print("WARNING: Could not find news-grid section", file=sys.stderr)
        return html_content

    # Find the closing </div> for the news-grid
    # Count div nesting after the start
    search_from = start_idx
    depth = 0
    i = search_from
    end_idx = -1
    while i < len(html_content):
        if html_content[i:i+4] == '<div':
            depth += 1
        elif html_content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                end_idx = i + 6
                break
        i += 1

    if end_idx == -1:
        print("WARNING: Could not find end of news-grid section", file=sys.stderr)
        return html_content

    html_content = html_content[:start_idx] + news_html + html_content[end_idx:]
    print(f"Updated news section with {len(data['news'])} articles")

    return html_content

def main():
    if len(sys.argv) < 3:
        print("Usage: python update-site.py <index.html> <website-data.json>")
        sys.exit(1)

    html_file = sys.argv[1]
    data_file = sys.argv[2]

    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()

    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = update_html(html_content, data)

    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(updated)

    print(f"Successfully updated {html_file} (version {data.get('version', '?')})")

if __name__ == "__main__":
    main()
