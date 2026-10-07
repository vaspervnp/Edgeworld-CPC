#!/usr/bin/env python3
"""Make the manuals' PDFs: each Markdown manual (docs/manual/MANUAL.*.md)
becomes HTML with a print stylesheet, which a headless Chrome prints to PDF.

The Markdown is the plain subset the manuals use: headings, paragraphs,
**bold**, *italic*, `code`, fenced code, lists, tables, images (alone on a
line they are figures, captioned with their alt text; in a table cell or
side by side, inline), horizontal rules, and raw HTML lines (a page break:
<div class="pagebreak"></div>).

Chrome: $CHROME, or the Windows one when run under WSL (the files are then
handed to it by their \\\\wsl.localhost paths).

Usage: mkmanual.py manual.md ... (writes manual.html and manual.pdf beside each)
"""
import html
import os
import re
import shutil
import subprocess
import sys

CSS = """
@page { size: A4; margin: 16mm 16mm 18mm; }
:root { --ink: #1c1a26; --muted: #5a5568; --rule: #d9d4e4; --accent: #6a2fb0; --warm: #c2410c; }
* { box-sizing: border-box; }
body { font: 10.5pt/1.5 "Segoe UI", "Noto Sans", "DejaVu Sans", Arial, sans-serif; color: var(--ink); margin: 0; }
h1 { font: 800 34pt/1.05 "Segoe UI Black", "Segoe UI", Arial, sans-serif; letter-spacing: 1px; margin: 0 0 2mm;
     color: #e5002b; text-align: center; }
h1 + h3 { text-align: center; color: var(--muted); font-weight: 600; margin: 0 0 6mm; }
h2 { font-size: 15pt; color: var(--accent); border-bottom: 2px solid var(--rule); padding-bottom: 1mm;
     margin: 9mm 0 3mm; break-after: avoid; }
h3 { font-size: 12pt; margin: 5mm 0 2mm; break-after: avoid; }
p { margin: 0 0 2.6mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.2mm; }
code { font-family: Consolas, "DejaVu Sans Mono", monospace; background: #f1edf7; padding: 0 3px; border-radius: 3px; }
pre { background: #000080; color: #ffff00; font: 11pt/1.4 Consolas, monospace; padding: 3mm 4mm;
      border-radius: 3px; width: max-content; }
pre code { background: none; padding: 0; }
figure { margin: 3mm 0 5mm; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 105mm; image-rendering: pixelated; border-radius: 2px;
             box-shadow: 0 1px 4px rgb(0 0 0 / .25); }
figcaption { font-size: 9pt; color: var(--muted); margin-top: 1.5mm; }
img.inline { image-rendering: pixelated; vertical-align: middle; max-height: 26mm; }
p.images { text-align: center; }
p.images img { margin: 0 4mm; max-height: 40mm; }
table { border-collapse: collapse; width: 100%; margin: 2mm 0 5mm; font-size: 9.5pt; break-inside: avoid; }
th, td { border-bottom: 1px solid var(--rule); padding: 1.6mm 2mm; text-align: left; vertical-align: middle; }
th { color: var(--muted); font-weight: 600; background: #f6f3fa; }
td:first-child img { max-height: 16mm; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 8mm 0 4mm; }
.pagebreak { break-after: page; }
em { color: var(--muted); }
"""


def inline(text):
    """Inline Markdown in text (already free of block structure)."""
    out = []
    for part in re.split(r"(`[^`]+`)", text):
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            out.append("<code>" + html.escape(part[1:-1]) + "</code>")
            continue
        part = html.escape(part, quote=False)
        part = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
                      lambda m: f'<img class="inline" src="{m.group(2)}" alt="{m.group(1)}">', part)
        part = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", part)
        part = re.sub(r"(?<![*\w])\*([^*]+)\*(?![*\w])", r"<em>\1</em>", part)
        out.append(part)
    return "".join(out)


def convert(md):
    lines = md.split("\n")
    out = []
    i = 0
    para = []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush()
            i += 1
        elif s.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            i += 1
        elif s.startswith("<"):
            flush()
            out.append(s)
            i += 1
        elif s.startswith("#"):
            flush()
            n = len(s) - len(s.lstrip("#"))
            out.append(f"<h{n}>{inline(s[n:].strip())}</h{n}>")
            i += 1
        elif s == "---":
            flush()
            out.append("<hr>")
            i += 1
        elif re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", s):
            flush()
            alt, src = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", s).groups()
            out.append(f'<figure><img src="{src}" alt="{html.escape(alt)}">'
                       f"<figcaption>{html.escape(alt)}</figcaption></figure>")
            i += 1
        elif re.fullmatch(r"(!\[[^\]]*\]\([^)]+\)\s*)+", s):
            flush()
            imgs = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", s)
            out.append('<p class="images">' + "".join(
                f'<img src="{src}" alt="{html.escape(alt)}" title="{html.escape(alt)}">' for alt, src in imgs) + "</p>")
            i += 1
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], [r for r in rows[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
            t = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
            for r in body:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("".join(t) + "</tbody></table>")
        elif not para and re.match(r"^(\d+\.|-)\s", s):   # "6128. ..." inside a paragraph is no list
            flush()
            ordered = s[0].isdigit()
            items = []
            while i < len(lines) and lines[i].strip():
                t = lines[i].strip()
                m = re.match(r"^(\d+\.|-)\s+(.*)", t)
                if m:
                    items.append(m.group(2))
                else:
                    items[-1] += " " + t       # a continued item
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
        else:
            para.append(s)
            i += 1
    flush()
    return "\n".join(out)


def chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"], False
    for c in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(c):
            return c, False
    win = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
    if os.path.exists(win):
        return win, True
    raise SystemExit("no Chrome found: set $CHROME")


def winpath(path):
    return subprocess.run(["wslpath", "-w", os.path.abspath(path)], capture_output=True,
                          text=True, check=True).stdout.strip()


def main(paths):
    exe, windows = chrome()
    for md_path in paths:
        md = open(md_path, encoding="utf-8").read()
        lang = "el" if ".el." in md_path else "en"
        title = re.search(r"^# (.*)$", md, re.M).group(1)
        body = convert(md)
        html_path = os.path.splitext(md_path)[0] + ".html"
        pdf_path = os.path.splitext(md_path)[0] + ".pdf"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
                    f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
                    f"<body>{body}</body></html>")
        src = "file:///" + winpath(html_path).replace("\\", "/") if windows else "file://" + os.path.abspath(html_path)
        dst = winpath(pdf_path) if windows else os.path.abspath(pdf_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        "--allow-file-access-from-files", f"--print-to-pdf={dst}", src],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        if not os.path.exists(pdf_path):
            raise SystemExit(f"{pdf_path}: Chrome made no PDF")
        print(f"{pdf_path}: {os.path.getsize(pdf_path)} bytes")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
