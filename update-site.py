#!/usr/bin/env python3
"""
update-site.py — Merges website-data.json into index.html
Used by GitHub Actions to update the news and listings sections
of Dave Ng's property website without touching the template.

IMPORTANT: When the JSON does not include base64 images, this script
preserves existing images from the HTML. This prevents GitHub Actions
from wiping out AIcutPro listing images or Pillow news thumbnails
that were set by the scheduled task.
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


def extract_existing_images(html_content, container_id):
    """Extract existing base64 images from a container, mapped by link URL.

    Returns a dict: { url: data_uri } for each card that has a base64 image.
    Works for both news cards (<a href="..." class="news-card">) and
    listing cards (<a href="..." class="listing-card-link">).
    """
    images = {}

    # Find the container
    marker = f'id="{container_id}"'
    idx = html_content.find(marker)
    if idx == -1:
        return images

    # Get the container's innerHTML
    start_tag_end = html_content.find('>', idx)
    if start_tag_end == -1:
        return images
    content_start = start_tag_end + 1

    # Find closing </div>
    depth = 1
    i = content_start
    content_end = -1
    while i < len(html_content):
        if html_content[i:i+4] == '<div':
            depth += 1
        elif html_content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                content_end = i
                break
        i += 1

    if content_end == -1:
        return images

    container_html = html_content[content_start:content_end]

    # Find all <a href="URL"> cards that contain data:image base64 URIs
    # Pattern: find each <a href="..."> and look for data:image in its content
    card_pattern = re.compile(r'<a\s+href="([^"]+)"[^>]*>', re.IGNORECASE)

    for match in card_pattern.finditer(container_html):
        card_url = match.group(1)
        card_start = match.start()

        # Find the end of this card (next </a>)
        card_end_idx = container_html.find('</a>', card_start)
        if card_end_idx == -1:
            continue

        card_html = container_html[card_start:card_end_idx]

        # Look for base64 image in this card
        # Matches: url('data:image/...;base64,...') or url("data:image/...")
        img_match = re.search(r"url\(['\"]?(data:image/[^)]+)['\"]?\)", card_html)
        if img_match:
            images[card_url] = img_match.group(1)

    return images


def build_news_card(article, existing_image=None):
    icon_key = article.get("icon", "house")
    icon_path = ICONS.get(icon_key, ICONS["house"])
    title_escaped = html.escape(article["title"]).replace("’", "&rsquo;").replace("'", "&rsquo;")
    summary_escaped = html.escape(article["summary"]).replace("’", "&rsquo;").replace("—", "&mdash;")

    # Use existing base64 image if available and JSON doesn't provide one
    bg_style = article['gradient']
    if existing_image:
        # Existing Pillow-generated thumbnail — use it as background
        bg_style = f"url('{existing_image}') center/cover no-repeat"

    return f'''<a href="{article['url']}" target="_blank" rel="noopener noreferrer" class="news-card" style="text-decoration:none;color:inherit;cursor:pointer">
            <div class="news-img" style="background:{bg_style};display:flex;align-items:center;justify-content:center">
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

def build_news_section(articles, existing_images=None):
    if existing_images is None:
        existing_images = {}
    cards = "".join(
        build_news_card(a, existing_images.get(a.get('url', '')))
        for a in articles
    )
    return f'''<div class="news-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:24px;margin:32px 0">

          {cards}

        </div>'''


def build_listing_card(listing, existing_image=None):
    """Build a single listing card HTML."""
    # Priority: JSON image > existing image from HTML > gradient fallback
    image = listing.get("image", "")
    if image and image.startswith("data:image"):
        img_style = f"background:url('{image}') center/cover no-repeat"
    elif existing_image:
        # Preserve existing AIcutPro image from the HTML
        img_style = f"background:url('{existing_image}') center/cover no-repeat"
    else:
        # Fallback gradient if no image anywhere
        img_style = "background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%)"

    return f'''<a href="{listing['url']}" target="_blank" rel="noopener noreferrer" class="listing-card-link" style="text-decoration:none;color:inherit;display:block;border-radius:16px;overflow:hidden;background:var(--card-bg);border:1px solid var(--card-border);transition:transform .2s,box-shadow .2s;cursor:pointer">
  <div style="height:220px;{img_style};position:relative">
    <span style="position:absolute;top:12px;left:12px;background:var(--gold-400);color:#1a1a2e;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;text-transform:uppercase;letter-spacing:.5px">{html.escape(listing['type'])}</span>
    <span style="position:absolute;top:12px;right:12px;background:rgba(34,197,94,.9);color:#fff;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px">Available</span>
  </div>
  <div style="padding:20px">
    <div style="font-size:20px;font-weight:700;color:var(--gold-400);margin-bottom:4px">{html.escape(listing['price'])}</div>
    <h4 style="font-family:'Playfair Display',serif;font-size:17px;margin:0 0 6px">{html.escape(listing['title'])}</h4>
    <div style="font-size:13px;color:var(--text-muted);margin-bottom:12px">{html.escape(listing['address'])}</div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--text-muted)">
      <span>{html.escape(listing['type'])}</span><span>{html.escape(listing['sqft'])} sqft</span><span>{html.escape(listing['bedrooms'])} Bed &middot; {html.escape(listing['bathrooms'])} Bath</span>
    </div>
  </div>
</a>'''


def build_listings_section(listings, existing_images=None):
    """Build the complete listings grid + CTA."""
    if existing_images is None:
        existing_images = {}
    cards = "\n".join(
        build_listing_card(l, existing_images.get(l.get('url', '')))
        for l in listings
    )

    listings_grid = f'''<div class="listings-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:24px;margin-bottom:32px">
{cards}
</div>'''

    cta = '''<div class="cta-banner" style="padding:40px;background:linear-gradient(135deg,var(--navy-900),var(--navy-800));border-radius:16px;text-align:center;margin:32px 0">
          <h3 style="color:#fff;font-size:22px;font-family:'Playfair Display',serif;margin-bottom:8px">Looking for Something Else?</h3>
          <p style="color:rgba(255,255,255,.7);font-size:14px;margin-bottom:24px">I can help you find the perfect property. Browse my full portfolio or reach out directly.</p>
          <div class="btn-row" style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
            <a href="https://www.propertyguru.com.sg/agent/dave-ng-16335961" target="_blank" rel="noopener noreferrer" class="btn btn-gold" style="text-decoration:none">View All on PropertyGuru</a>
            <a href="https://wa.me/6583705070?text=Hi%20Dave%2C%20I%27m%20looking%20for%20a%20property.%20Can%20you%20help?" target="_blank" rel="noopener noreferrer" class="btn btn-green" style="text-decoration:none">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492l4.625-1.476A11.929 11.929 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 21.818c-2.168 0-4.19-.587-5.932-1.608l-.425-.253-2.74.875.867-2.665-.277-.44A9.77 9.77 0 012.182 12c0-5.418 4.4-9.818 9.818-9.818S21.818 6.582 21.818 12s-4.4 9.818-9.818 9.818z"/></svg>
              WhatsApp Me
            </a>
          </div>
        </div>'''

    return listings_grid + '\n' + cta


def replace_container(html_content, container_id, new_inner_html):
    """Replace the innerHTML of a container div by id."""
    marker = f'id="{container_id}"'
    idx = html_content.find(marker)
    if idx == -1:
        print(f"WARNING: Could not find {marker}", file=sys.stderr)
        return html_content

    # Find the opening > of the container div
    start_tag_end = html_content.find('>', idx)
    if start_tag_end == -1:
        print(f"WARNING: Could not find closing > for {container_id}", file=sys.stderr)
        return html_content

    content_start = start_tag_end + 1

    # Find matching closing </div> by counting depth
    depth = 1
    i = content_start
    content_end = -1
    while i < len(html_content):
        if html_content[i:i+4] == '<div':
            depth += 1
        elif html_content[i:i+6] == '</div>':
            depth -= 1
            if depth == 0:
                content_end = i
                break
        i += 1

    if content_end == -1:
        print(f"WARNING: Could not find closing </div> for {container_id}", file=sys.stderr)
        return html_content

    html_content = html_content[:content_start] + '\n        ' + new_inner_html + '\n      ' + html_content[content_end:]
    print(f"Updated {container_id}")
    return html_content


def update_html(html_content, data):
    # Extract existing images BEFORE replacing sections
    existing_news_images = extract_existing_images(html_content, "news-container")
    existing_listing_images = extract_existing_images(html_content, "listings-container")

    if existing_news_images:
        print(f"  Preserved {len(existing_news_images)} existing news image(s)")
    if existing_listing_images:
        print(f"  Preserved {len(existing_listing_images)} existing listing image(s)")

    # Update news section
    if "news" in data and data["news"]:
        news_html = build_news_section(data["news"], existing_news_images)
        html_content = replace_container(html_content, "news-container", news_html)
        print(f"  News: {len(data['news'])} articles")

    # Update listings section
    if "listings" in data and data["listings"]:
        listings_html = build_listings_section(data["listings"], existing_listing_images)
        html_content = replace_container(html_content, "listings-container", listings_html)
        has_json_images = sum(1 for l in data["listings"] if l.get("image", "").startswith("data:image"))
        has_preserved = sum(1 for l in data["listings"] if l.get("url", "") in existing_listing_images)
        print(f"  Listings: {len(data['listings'])} properties ({has_json_images} JSON images, {has_preserved} preserved)")

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
