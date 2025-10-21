#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
import time
import random
import re
import webbrowser
import concurrent.futures
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, quote_plus

# ---- DuckDuckGo Search -------------------------------------------------------
try:
    from ddgs import DDGS  # falls du "ddgs" nutzt
except Exception:
    from duckduckgo_search import DDGS  # Fallback auf Standardpaket

# ---- HTTP & Parsing ----------------------------------------------------------
import requests
from bs4 import BeautifulSoup

# ---- CLI UI (Rich / Questionary) --------------------------------------------
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich import box

try:
    import questionary
except Exception:
    questionary = None

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# Banner
# ──────────────────────────────────────────────────────────────────────────────
BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║      ██████╗ ███████╗███████╗██╗   ██╗                        ║
║     ██╔═══██╗╚══███╔╝╚══███╔╝╚██╗ ██╔╝                        ║
║     ██║   ██║  ███╔╝   ███╔╝  ╚████╔╝                         ║
║     ██║   ██║ ███╔╝   ███╔╝    ╚██╔╝                          ║
║     ╚██████╔╝███████╗███████╗   ██║                           ║
║      ╚═════╝ ╚══════╝╚══════╝   ╚═╝                           ║
║                                                               ║
║   🔎  Intelligente Site-Suche (mit präziser Relevanz-Logik)   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# ──────────────────────────────────────────────────────────────────────────────
# Default-Sites (du kannst beliebige Sites via --sites übergeben)
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_SITES = [
    "forum.mobilism.org",
    "4pda.to",
    "rockmods.net",
    "pdalife.com",
    "an1.com",
    "liteapks.com",
    "modyolo.com",
    "nsaneforums.com",
    "android-zone.ws",
    "9mod.com",
    "rexdl.com",
    "farsroid.com"
]

SITE_EMOJIS = {
    "forum.mobilism.org": "📱",
    "4pda.to": "🇷🇺",
    "rockmods.net": "🎸",
    "pdalife.com": "💎",
    "an1.com": "🌐",
}

# ──────────────────────────────────────────────────────────────────────────────
# HTTP Session
# ──────────────────────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "close",
    })
    return s

HTTP = make_session()

# ──────────────────────────────────────────────────────────────────────────────
# Query- und Text-Helfer
# ──────────────────────────────────────────────────────────────────────────────
STOPWORDS = {
    "pro","apk","android","mod","mods","premium","full","plus","download",
    "updated","update","latest","new","app","apps","appx","page","forum",
    "topic","threads","category","categories","news","and","the","for","of"
}

def norm_text(s: str) -> str:
    s = s or ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def split_query(query: str) -> Tuple[List[str], List[str], str]:
    toks = re.findall(r"[a-z0-9]+", query.lower())
    full_tokens = [t for t in toks if t]
    core_tokens = [t for t in full_tokens if t not in STOPWORDS]
    phrase = " ".join(full_tokens)
    return full_tokens, core_tokens, phrase

def slugify_tokens(tokens: List[str]) -> Tuple[str, str]:
    slug = "-".join(tokens)
    jam = "".join(tokens)
    return slug, jam

def gen_query_variants(query: str) -> List[str]:
    q = query.strip()
    tokens, _, _ = split_query(q)
    slug, jam = slugify_tokens(tokens)
    variants = [
        f"\"{q}\"",
        q,
        f"intitle:\"{q}\"",
        f"{q} apk",
    ]
    if slug and slug != q:
        variants.append(slug)
    if jam and jam != q.replace(" ", ""):
        variants.append(jam)

    seen = set(); out = []
    for v in variants:
        if v not in seen:
            out.append(v); seen.add(v)
    return out

# ──────────────────────────────────────────────────────────────────────────────
# URL-Kanonisierung & Deduplizierung
# ──────────────────────────────────────────────────────────────────────────────
FORUM_QUERY_DROP = {
    "st","start","p","page","hl","view","do","tab","sortby","sortdirection",
    "orderby","per_page","from","to","ref","source","utm_source","utm_medium",
    "utm_campaign","utm_term","utm_content","amp",
}

def canonical_url(u: str) -> str:
    try:
        parts = urlsplit(u)
        scheme = parts.scheme or "https"
        netloc = parts.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path

        q_pairs = parse_qsl(parts.query, keep_blank_values=False)
        q = {k: v for k, v in q_pairs}

        # Foren/Threads: nur die Thread-ID beibehalten
        if "showtopic" in q:
            q = {"showtopic": q["showtopic"]}
        elif "viewtopic" in path and "t" in q:
            q = {"t": q["t"]}
        else:
            q = {k: v for k, v in q.items() if k not in FORUM_QUERY_DROP and not k.lower().startswith("utm_")}

        # Pfad-basierte Paging (?page=2) entfernen
        if "topic/" in path or "/forums/topic/" in path:
            # Häufig: ?page=2 etc. → weg
            q = {k: v for k, v in q.items() if k not in {"page"}}

        query = urlencode(q, doseq=True)
        return urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return u

# ──────────────────────────────────────────────────────────────────────────────
# Relevanz-Gate (entscheidet, ob ein Result überhaupt behalten wird)
# ──────────────────────────────────────────────────────────────────────────────
def build_fieldset(res: Dict[str, Any]) -> Dict[str, str]:
    return {
        "title": (res.get("title") or "").lower(),
        "url": (res.get("href") or "").lower(),
        "body": (res.get("body") or "").lower(),
    }

def match_gate(res: Dict[str, Any], query: str, match_mode: str, fields: List[str]) -> bool:
    full_tokens, core_tokens, phrase = split_query(query)
    fs = build_fieldset(res)

    def in_fields_contains(s: str) -> bool:
        return any(s in fs[f] for f in fields)

    def all_tokens_in_field(tokens: List[str], f: str) -> bool:
        return all(t in fs[f] for t in tokens)

    # „phrase“ = exakt (lowercased, whitespace-normalisiert)
    if match_mode == "phrase":
        return in_fields_contains(phrase)

    if match_mode == "all":
        return any(all_tokens_in_field(full_tokens, f) for f in fields)

    if match_mode == "core":
        toks = core_tokens or full_tokens
        return any(all_tokens_in_field(toks, f) for f in fields)

    # smart (Default):
    if len(full_tokens) >= 2:
        # Exakte Phrase ODER alle Tokens in Titel/URL
        if in_fields_contains(phrase):
            return True
        if any(all_tokens_in_field(full_tokens, f) for f in fields):
            return True
        return False
    else:
        # Ein-Wort-Query: muss in Titel oder URL vorkommen
        tok = (core_tokens or full_tokens)[0]
        return any(tok in fs[f] for f in fields)

# ──────────────────────────────────────────────────────────────────────────────
# Ranking (nach Gate)
# ──────────────────────────────────────────────────────────────────────────────
def score_result(res: Dict[str, Any], query: str, fields: List[str]) -> float:
    title = (res.get("title") or "")
    url   = (res.get("href") or "")
    body  = (res.get("body") or "")

    nt, nu, nb = title.lower(), url.lower(), body.lower()
    full_tokens, core_tokens, phrase = split_query(query)

    from difflib import SequenceMatcher
    # Fuzzy auf Titel (leichter Einfluss)
    fuzz = SequenceMatcher(None, nt, " ".join(full_tokens)).ratio() * 20.0

    # Token-Treffer
    def tok_count(s: str, toks: List[str]) -> int:
        return sum(1 for t in toks if t in s)

    t_title = tok_count(nt, full_tokens)
    t_url   = tok_count(nu, full_tokens)
    t_body  = tok_count(nb, full_tokens)

    score = 0.0
    # Exakte Phrase stark gewichten
    if phrase in nt:
        score += 100.0
    if phrase in nu:
        score += 60.0
    if phrase in nb:
        score += 15.0

    # Alle Tokens in einem Feld?
    if all(t in nt for t in full_tokens):
        score += 40.0
    if all(t in nu for t in full_tokens):
        score += 30.0

    # Token-Treffer (sanft)
    score += t_title * 7.0 + t_url * 3.0 + t_body * 1.0

    # leichte Penalty für Kategorie/Archiv, falls keine Phrase
    if phrase not in nt and phrase not in nu:
        if any(x in nu for x in ["page/", "/category/", "/tag/", "/archives", "/badge/"]):
            score -= 6.0

    score += fuzz
    return score

# ──────────────────────────────────────────────────────────────────────────────
# DDG-Site-Suche & Fallback (interne Suche)
# ──────────────────────────────────────────────────────────────────────────────
def ddg_site_search(query: str, site: str, max_per_variant: int = 25) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for v in gen_query_variants(query):
        full_q = f"{v} site:{site}"
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(full_q, safesearch="off", max_results=max_per_variant):
                    if r and r.get("href"):
                        results.append({
                            "title": r.get("title", "") or "",
                            "href": r.get("href", "") or "",
                            "body": r.get("body", "") or "",
                            "source": "ddg"
                        })
        except Exception:
            pass
        time.sleep(0.2 + random.random() * 0.25)
    return results

def try_fetch(url: str, timeout: float = 10.0) -> str:
    try:
        r = HTTP.get(url, timeout=timeout)
        if r.status_code == 200 and r.text:
            return r.text
    except Exception:
        pass
    return ""

def parse_links_generic(html: str, domain: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if not text or len(text) < 2:
            continue
        if domain in href:
            out.append((text, href))
    return out

def parse_links_wordpress(html: str, domain: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Tuple[str, str]] = []
    for el in soup.find_all(["h2","h3"], class_="entry-title"):
        a = el.find("a", href=True)
        if a and domain in a["href"]:
            out.append((a.get_text(" ", strip=True), a["href"]))
    if not out:
        out = parse_links_generic(html, domain)
    return out

def parse_links_ipb(html: str, domain: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(" ", strip=True)
        if not title or len(title) < 2:
            continue
        if domain in href and ("/topic/" in href or "showtopic=" in href or "/forums/topic/" in href):
            out.append((title, href))
    if not out:
        out = parse_links_generic(html, domain)
    return out

def parse_links_phpbb(html: str, domain: str) -> List[Tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    out: List[Tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(" ", strip=True)
        if not title:
            continue
        if domain in href and ("viewtopic" in href or "t=" in href):
            out.append((title, href))
    if not out:
        out = parse_links_generic(html, domain)
    return out

def site_internal_search(query: str, site: str) -> List[Dict[str, Any]]:
    q = quote_plus(query)
    candidates = [
        (f"https://{site}/?s={q}", "wp"),
        (f"https://{site}/search/?q={q}", "ipb"),
        (f"https://{site}/forum/index.php?act=search&source=all&subforums=1&forums=0&query={q}", "ipb"),
        (f"https://{site}/search.php?keywords={q}&sr=topics&sf=titleonly", "phpbb"),
    ]
    for url, kind in candidates:
        html = try_fetch(url)
        if not html:
            continue
        if kind == "wp":
            pairs = parse_links_wordpress(html, site)
        elif kind == "ipb":
            pairs = parse_links_ipb(html, site)
        elif kind == "phpbb":
            pairs = parse_links_phpbb(html, site)
        else:
            pairs = parse_links_generic(html, site)

        results = []
        for title, href in pairs:
            results.append({
                "title": title,
                "href": href,
                "body": "",
                "source": f"site:{kind}"
            })
        if results:
            return results
    return []

# ──────────────────────────────────────────────────────────────────────────────
# Zusammenführen, Filtern, Deduplizieren, Sortieren
# ──────────────────────────────────────────────────────────────────────────────
def dedupe(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set(); out = []
    for r in results:
        u = canonical_url(r.get("href",""))
        if not u or u in seen:
            continue
        r["href"] = u
        seen.add(u)
        out.append(r)
    return out

def filter_by_gate(results: List[Dict[str, Any]], query: str, match_mode: str, fields: List[str]) -> List[Dict[str, Any]]:
    out = []
    for r in results:
        if match_gate(r, query, match_mode, fields):
            out.append(r)
    return out

def rank(results: List[Dict[str, Any]], query: str, fields: List[str]) -> List[Dict[str, Any]]:
    for r in results:
        r["_score"] = score_result(r, query, fields)
    results.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
    return results

# ──────────────────────────────────────────────────────────────────────────────
# Orchestrierung pro Site
# ──────────────────────────────────────────────────────────────────────────────
def search_on_site(
    query: str,
    site: str,
    max_ddg: int,
    match_mode: str,
    fields: List[str],
    fallback_mode: str,
    fallback_threshold: int
) -> List[Dict[str, Any]]:

    # 1) DDG
    ddg_results = ddg_site_search(query, site, max_per_variant=max_ddg)
    ddg_results = filter_by_gate(dedupe(ddg_results), query, match_mode, fields)

    # 2) Fallback (nur wenn konfiguriert/erforderlich)
    need_fb = False
    if fallback_mode == "always":
        need_fb = True
    elif fallback_mode == "if_empty":
        need_fb = len(ddg_results) <= fallback_threshold
    elif fallback_mode == "never":
        need_fb = False

    fb_results = []
    if need_fb:
        fb_results = site_internal_search(query, site)
        fb_results = filter_by_gate(dedupe(fb_results), query, match_mode, fields)

    combined = dedupe(ddg_results + fb_results)
    combined = rank(combined, query, fields)
    return combined

# ──────────────────────────────────────────────────────────────────────────────
# Anzeige / UI
# ──────────────────────────────────────────────────────────────────────────────
def print_banner():
    console.print(BANNER, style="bold cyan", highlight=False)
    console.print(Align.center("═" * 63), style="bold blue")
    console.print()

def display_search_info(query: str, sites: List[str]):
    sites_text = "\n".join([f"  {SITE_EMOJIS.get(site, '•')} {site}" for site in sites])
    info_panel = Panel(
        f"[bold white]Query:[/bold white] [cyan]{query}[/cyan]\n\n"
        f"[bold white]Searching on:[/bold white]\n{sites_text}",
        title="[bold green]🔎 Search Configuration[/bold green]",
        border_style="green",
        box=box.DOUBLE_EDGE,
        padding=(1, 2)
    )
    console.print(info_panel)
    console.print()

def render_results_table(query: str, all_results: List[Dict[str, Any]]):
    table = Table(
        title=f"✨ Search Results for '{query}' ✨",
        title_style="bold magenta",
        show_header=True,
        header_style="bold cyan",
        border_style="blue",
        box=box.DOUBLE_EDGE,
        show_lines=True,
        padding=(0, 1)
    )
    table.add_column("№", style="bold yellow", width=4, justify="center")
    table.add_column("📌 Title", style="bold white", no_wrap=False)
    table.add_column("🔗 Link", style="green", no_wrap=False)
    table.add_column("⭐", justify="right", width=5, style="dim")

    for idx, r in enumerate(all_results, 1):
        star = f"{int(round(r.get('_score', 0.0)))}"
        table.add_row(str(idx), r.get("title",""), r.get("href",""), star)

    console.print(table)
    console.print()

# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main():
    print_banner()

    parser = argparse.ArgumentParser(description="Intelligente Site-Suche mit präzisem Relevanz-Gate (weniger Rauschen).")
    parser.add_argument("query", nargs='?', default=None, help="Suchanfrage (z. B. App-Name).")
    parser.add_argument("--sites", nargs='+', default=DEFAULT_SITES,
                        help="Domains, auf denen gesucht werden soll (Leerzeichen-getrennt).")
    parser.add_argument("--max-ddg", type=int, default=20,
                        help="max_results pro Query-Variante bei DDG (Standard 20).")

    parser.add_argument("--match", choices=["smart","phrase","all","core"], default="smart",
                        help="Relevanz-Gate: 'smart' (Default), 'phrase', 'all', 'core'.")

    parser.add_argument("--fields", default="title,url",
                        help="Kommaseparierte Felder für das Gate/Scoring (z. B. 'title,url' oder 'title,url,body').")

    parser.add_argument("--fallback", choices=["if_empty","always","never"], default="if_empty",
                        help="Wann interne Seitensuche nutzen (Default: if_empty).")

    parser.add_argument("--fallback-threshold", type=int, default=0,
                        help="Schwelle für 'if_empty' (z. B. 0 = nur wenn gar keine DDG-Resultate).")

    parser.add_argument("--per-site", type=int, default=10,
                        help="Maximale Anzahl der Top-Ergebnisse pro Site (Default 10).")

    args = parser.parse_args()

    query = args.query
    if not query and sys.stdout.isatty() and questionary is not None:
        console.print("┌─────────────────────────────────────────┐", style="bold cyan")
        query = questionary.text("│ 🔍 Was möchtest du suchen?", qmark="└─►").ask()
        console.print("└─────────────────────────────────────────┘\n", style="bold cyan")
    elif not query:
        console.print(Panel(
            "❌ Keine Suchanfrage übergeben.\n\n"
            "Usage: [bold cyan]python smart_site_search.py \"<your query>\"[/bold cyan]",
            title="[bold red]Error[/bold red]", border_style="red", box=box.HEAVY
        ))
        return

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    display_search_info(query, args.sites)

    console.print("╔═══════════════════════════════════════════════════════════════╗", style="bold magenta")
    console.print("║              🚀 Initiating Search Process...                  ║", style="bold magenta")
    console.print("╚═══════════════════════════════════════════════════════════════╝\n", style="bold magenta")

    all_results: List[Dict[str, Any]] = []
    with console.status("[bold green]⚡ Searching...[/]", spinner="dots"):
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(args.sites) or 1)) as ex:
            futs = {
                ex.submit(
                    search_on_site,
                    query, site, max(5, args.max_ddg), args.match, fields, args.fallback, args.fallback_threshold
                ): site for site in args.sites
            }
            for fut in concurrent.futures.as_completed(futs):
                site = futs[fut]
                emoji = SITE_EMOJIS.get(site, "•")
                try:
                    site_results = fut.result()
                except Exception:
                    site_results = []
                if site_results:
                    show_n = max(1, args.per_site)
                    all_results.extend(site_results[:show_n])
                    console.print(f"  ✓ {emoji} {site}: [green]{len(site_results)} results[/green]")
                else:
                    console.print(f"  ○ {emoji} {site}: [dim]no results[/dim]")

    # Global dedupe & rank
    all_results = dedupe(all_results)
    all_results = rank(all_results, query, fields)

    console.print()
    console.print("─" * 63, style="bold blue")
    console.print()

    if all_results:
        render_results_table(query, all_results)
        if sys.stdout.isatty() and questionary is not None:
            console.print(Panel("👇 Wähle ein Ergebnis zum Öffnen", style="bold green", box=box.ROUNDED))
            choices = [f"{i+1}. {r['title']}" for i, r in enumerate(all_results)]
            selected = questionary.select("Choose a link:", choices=choices, qmark="🎯", pointer="►").ask()
            if selected:
                idx = int(selected.split('.')[0]) - 1
                target = all_results[idx]
                console.print()
                console.print(Panel(
                    f"🌐 Opening: [cyan]{target['href']}[/cyan]",
                    title="[bold green]✓ Success[/bold green]",
                    border_style="green",
                    box=box.DOUBLE
                ))
                webbrowser.open(target['href'])
        else:
            console.print(Panel(
                "ℹ️  Non-interactive mode. Kein Auswahlmenü.",
                title="[bold yellow]Info[/bold yellow]", border_style="yellow"
            ))
    else:
        console.print(Panel(
            "😔 Keine Ergebnisse gefunden.\n\n"
            "💡 Tipps:\n"
            "  • Match-Modus auf 'core' oder 'all' wechseln\n"
            "  • 'body' zu --fields hinzufügen\n"
            "  • Andere Schreibweise versuchen",
            title="[bold yellow]⚠️  No Results[/bold yellow]",
            border_style="yellow", box=box.HEAVY, padding=(1, 2)
        ))

    console.print()
    console.print("╔═══════════════════════════════════════════════════════════════╗", style="bold cyan")
    console.print("║                   Thanks for using! 🚀                        ║", style="bold cyan")
    console.print("╚═══════════════════════════════════════════════════════════════╝", style="bold cyan")

if __name__ == "__main__":
    main()
