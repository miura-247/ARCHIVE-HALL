#!/usr/bin/env python3
"""
Simple build script for character_site_v3

Features:
- supports a hybrid workflow:
  - if `data/characters/` contains per-character files (.json or .md), read those
  - else if `data/characters.json` exists, read it as an array of characters
- generates `dist/index.json` (lightweight metadata) and `dist/characters/{id}.html` (full pages)
- copies `styles.css` and `js/` into `dist/`

No external dependencies required.
"""
from pathlib import Path
import json
import shutil
import re
import sys

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
TEMPLATES = ROOT / 'templates'
OUT = ROOT / 'dist'


def load_char_from_md(path: Path):
    text = path.read_text(encoding='utf-8')
    meta = {}
    body = text
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            raw_meta = parts[1]
            body = parts[2].strip()
            for line in raw_meta.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip().strip('"')
    # include body under 'bio' if not present
    if 'bio' not in meta:
        meta['bio'] = body
    if 'id' not in meta:
        meta['id'] = path.stem
    return meta


def load_characters():
    chars = []
    perdir = DATA / 'characters'
    if perdir.exists() and perdir.is_dir():
        for p in sorted(perdir.iterdir()):
            if p.suffix == '.json':
                chars.append(json.loads(p.read_text(encoding='utf-8')))
            elif p.suffix == '.md':
                chars.append(load_char_from_md(p))
    else:
        whole = DATA / 'characters.json'
        if whole.exists():
            chars = json.loads(whole.read_text(encoding='utf-8'))
        else:
            print('No character data found in data/characters/ or data/characters.json', file=sys.stderr)
    # ensure ids
    for c in chars:
        if 'id' not in c:
            raise ValueError(f'Character missing id: {c}')
    return chars


def render_template(path: Path, ctx: dict):
    s = path.read_text(encoding='utf-8')
    # simple placeholder replacement {{key}}
    def repl(m):
        key = m.group(1).strip()
        return str(ctx.get(key, ''))
    return re.sub(r"\{\{\s*(.*?)\s*\}\}", repl, s)


def ensure_out():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / 'characters').mkdir()


def copy_assets():
    # copy styles.css
    for name in ('styles.css',):
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, OUT / name)
    # copy js/
    src_js = ROOT / 'js'
    if src_js.exists() and src_js.is_dir():
        shutil.copytree(src_js, OUT / 'js')
    # copy top-level imgs/ if present
    candidate_imgs = [ROOT / 'imgs', DATA / 'imgs', ROOT / 'assets', DATA / 'assets']
    for src in candidate_imgs:
        if src.exists() and src.is_dir():
            dest = OUT / src.name
            # if dest exists, remove to ensure up-to-date
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)


def build():
    chars = load_characters()
    ensure_out()
    copy_assets()

    index_meta = []

    tpl_char = TEMPLATES / 'character.html'
    tpl_index = TEMPLATES / 'index.html'

    # generate per-character pages and per-character JSON in dist
    for c in chars:
        cid = c['id']
        # images HTML
        images_html = ''
        imgs = c.get('images', []) or []
        if isinstance(imgs, list):
            items = []
            for img in imgs:
                items.append(f'<li><img src="../{img}" alt="{c.get("name","")}"></li>')
            images_html = '\n'.join(items)
        # relations
        rel_html = ''
        rels = c.get('relations', []) or []
        if isinstance(rels, list):
            items = []
            for r in rels:
                rid = r.get('id')
                txt = r.get('text') or r.get('relation') or ''
                if rid:
                    items.append(f'<div class="rel"><a href="../characters/{rid}.html">{rid}</a> <span>{txt}</span></div>')
                else:
                    items.append(f'<div class="rel"><span>{txt}</span></div>')
            rel_html = '\n'.join(items)

        ctx = c.copy()
        # join lists for simple placeholders
        ctx['likes'] = ', '.join(c.get('likes', []))
        ctx['dislikes'] = ', '.join(c.get('dislikes', []))
        ctx['images'] = images_html
        ctx['relations'] = rel_html

        out_html = render_template(tpl_char, ctx)
        (OUT / 'characters' / f"{cid}.html").write_text(out_html, encoding='utf-8')

        # write lightweight per-character json for client fetch if desired
        (OUT / 'characters' / f"{cid}.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding='utf-8')

        # prepare index meta
        excerpt = c.get('bio','')
        if len(excerpt) > 140:
            excerpt = excerpt[:140].rsplit(' ',1)[0] + '...'
        thumb = (c.get('images') or [None])[0]
        index_meta.append({
            'id': cid,
            'name': c.get('name'),
            'category': c.get('category'),
            'tags': c.get('tags', []),
            'excerpt': excerpt,
            'thumb': thumb,
            'link': f'characters/{cid}.html'
        })

    # write index.json
    (OUT / 'index.json').write_text(json.dumps(index_meta, ensure_ascii=False, indent=2), encoding='utf-8')

    # render index.html with simple category grouping
    cats = {}
    for m in index_meta:
        cats.setdefault(m.get('category','その他'), []).append(m)

    sections = []
    toc_items = []
    for cat, items in cats.items():
        cat_id = re.sub(r"[^0-9a-zA-Z_-]", '_', cat)
        toc_items.append(f'<a href="#cat-{cat_id}">{cat} ({len(items)})</a>')
        cards = []
        for it in items:
            tags = ' '.join(it.get('tags', []))
            # prefer use of svg if present in original data
            orig = next((x for x in chars if x['id'] == it['id']), {})
            sv = orig.get('svg', '')
            card = f'<li><a href="{it["link"]}" data-tags="{tags}">{sv}<span class="sr-only">{it["name"]}</span></a></li>'
            cards.append(card)
        sections.append(f'<section id="cat-{cat_id}"><h2>{cat}</h2><ul class="icons">' + '\n'.join(cards) + '</ul></section>')

    index_html = tpl_index.read_text(encoding='utf-8')
    index_html = index_html.replace('<!-- generated toc -->', '<nav class="toc">' + '\n'.join(toc_items) + '</nav>')
    index_html = index_html.replace('<!-- sections -->', '\n'.join(sections))
    (OUT / 'index.html').write_text(index_html, encoding='utf-8')

    print(f'Built to {OUT}')


if __name__ == '__main__':
    build()
