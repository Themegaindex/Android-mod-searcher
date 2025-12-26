import argparse
import sys
import webbrowser
import questionary
import os
from ddgs import DDGS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

# AI Imports
try:
    from llama_cpp import Llama
    from huggingface_hub import hf_hub_download
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Initialize the Rich Console
console = Console()

# AI Configuration
MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ██╗   ██╗██╗██████╗  ██████╗ ██╗██╗         ║
║   ██║   ██║██║██╔══██╗██╔════╝ ██║██║         ║
║   ██║   ██║██║██████╔╝██║  ███╗██║██║         ║
║   ╚██╗ ██╔╝██║██╔══██╗██║   ██║██║██║         ║
║    ╚████╔╝ ██║██║  ██║╚██████╔╝██║███████╗    ║
║     ╚═══╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝╚══════╝    ║
║                                                               ║
║           🔍  Advanced APK Search Engine  🔍                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# List of websites to search
WEBSITES = [
    "forum.mobilism.org",
    "4pda.to",
    "rockmods.net",
    "pdalife.com",
    "an1.com",
]

SITE_EMOJIS = {
    "forum.mobilism.org": "📱",
    "4pda.to": "🇷🇺",
    "rockmods.net": "🎸",
    "pdalife.com": "💎",
    "an1.com": "🌐",
}

def print_banner():
    """Display the fancy ASCII banner"""
    console.print(BANNER, style="bold cyan", highlight=False)
    console.print(
        Align.center("═" * 63),
        style="bold blue"
    )
    console.print()

def get_model():
    """Download and load the AI model"""
    if not AI_AVAILABLE:
        return None

    try:
        model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME)
        return Llama(
            model_path=model_path,
            n_ctx=2048,
            verbose=False,
            n_gpu_layers=0  # Run on CPU
        )
    except Exception as e:
        console.print(f"[bold red]Failed to load AI model:[/bold red] {e}")
        return None

def evaluate_result(model, query, result):
    """Ask AI to score the relevance of a result"""
    if not model:
        return 0

    prompt = f"""<|im_start|>system
You are a search result evaluator for Android mods and APKs. Rate the relevance of the search result to the user's query on a scale from 0 to 10.
0 means completely irrelevant. 10 means perfect match (correct app, correct version/mod).
Output ONLY the number.
<|im_end|>
<|im_start|>user
Query: "{query}"
Result Title: "{result.get('title', '')}"
Result Body: "{result.get('body', '')}"
<|im_end|>
<|im_start|>assistant
"""
    try:
        output = model(
            prompt,
            max_tokens=5,
            stop=["<|im_end|>", "\n"],
            echo=False
        )
        text = output['choices'][0]['text'].strip()
        # Extract number
        import re
        match = re.search(r'\d+', text)
        if match:
            return int(match.group())
        return 0
    except Exception:
        return 0

def rank_results_with_ai(query, results):
    """Rank all results using Qwen AI"""
    if not AI_AVAILABLE:
        return results

    model = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task1 = progress.add_task("[cyan]Loading AI Brain (Qwen 1.5B)...", total=None)
        model = get_model()
        progress.update(task1, visible=False)

        if not model:
            return results

        task2 = progress.add_task(f"[magenta]AI Analyzing {len(results)} results...", total=len(results))

        scored_results = []
        for res in results:
            score = evaluate_result(model, query, res)
            res['ai_score'] = score
            scored_results.append(res)
            progress.advance(task2)

    # Sort by score descending
    scored_results.sort(key=lambda x: x.get('ai_score', 0), reverse=True)
    return scored_results

def search_site(query, site):
    """
    Performs a more precise search and filters the results for relevance.
    """
    try:
        search_query = f'"{query}" site:{site}'
        unfiltered_results = []
        
        with DDGS() as ddgs:
            unfiltered_results = list(ddgs.text(search_query, max_results=10))

        # Filter results (Basic keyword match)
        filtered_results = []
        for result in unfiltered_results:
            title = result.get('title', '').lower()
            body = result.get('body', '').lower()
            if query.lower() in title or query.lower() in body:
                filtered_results.append(result)

        return filtered_results[:5]

    except Exception as e:
        console.print(
            Panel(
                f"❌ Error: {e}",
                title=f"[bold red]Search Failed on {site}[/bold red]",
                border_style="red",
                box=box.DOUBLE
            )
        )
        return []

def display_search_info(query, sites):
    """Display search information in a nice panel"""
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

def main():
    """
    Main function to run the CLI search tool.
    """
    print_banner()

    parser = argparse.ArgumentParser(description="Search for content on specific websites.")
    parser.add_argument("query", nargs='?', default=None, help="The search query.")
    parser.add_argument("--sites", nargs='+', choices=WEBSITES, default=WEBSITES, help="Specify the websites to search.")
    args = parser.parse_args()

    query = args.query
    
    # Only prompt for input if running in an interactive terminal
    if not query and sys.stdout.isatty():
        console.print("┌─────────────────────────────────────────┐", style="bold cyan")
        query = questionary.text(
            "│ 🔍 What would you like to search for?",
            qmark="└─►"
        ).ask()
        console.print("└─────────────────────────────────────────┘\n", style="bold cyan")
    elif not query:
        console.print(
            Panel(
                "❌ No search query provided.\n\n"
                "Usage: [bold cyan]python search_cli.py \"<your query>\"[/bold cyan]",
                title="[bold red]Error[/bold red]",
                border_style="red",
                box=box.HEAVY
            )
        )
        return

    if not query:
        console.print(
            Panel(
                "⚠️  No search query entered.",
                title="[bold yellow]Warning[/bold yellow]",
                border_style="yellow"
            )
        )
        return

    display_search_info(query, args.sites)

    all_results = []
    
    # Search with animated status
    console.print("╔═══════════════════════════════════════════════════════════════╗", style="bold magenta")
    console.print("║              🚀 Initiating Search Process...                  ║", style="bold magenta")
    console.print("╚═══════════════════════════════════════════════════════════════╝\n", style="bold magenta")
    
    with console.status("[bold green]⚡ Searching...[/]", spinner="dots") as status:
        for idx, site in enumerate(args.sites, 1):
            emoji = SITE_EMOJIS.get(site, "•")
            status.update(f"[bold cyan]{emoji} [{idx}/{len(args.sites)}] Searching on {site}...[/]")
            search_results = search_site(query, site)
            if search_results:
                all_results.extend(search_results)
                console.print(f"  ✓ {emoji} {site}: [green]{len(search_results)} results found[/green]")
            else:
                console.print(f"  ○ {emoji} {site}: [dim]no results[/dim]")

    console.print()
    console.print("─" * 63, style="bold blue")
    console.print()

    if all_results:
        # AI Re-ranking
        if AI_AVAILABLE:
            console.print(Panel("🧠 AI Re-ranking in progress... results may be reordered by relevance.", style="dim cyan"))
            all_results = rank_results_with_ai(query, all_results)
            console.print()

        # Create beautiful results table
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
        if AI_AVAILABLE:
            table.add_column("🤖 Score", style="bold magenta", justify="center")

        for idx, result in enumerate(all_results, 1):
            row_data = [
                str(idx),
                result['title'],
                result['href']
            ]
            if AI_AVAILABLE:
                score = result.get('ai_score', 0)
                score_str = f"{score}/10"
                if score >= 8:
                    score_str = f"[bold green]{score}/10[/bold green]"
                elif score >= 5:
                    score_str = f"[yellow]{score}/10[/yellow]"
                else:
                    score_str = f"[red]{score}/10[/red]"
                row_data.append(score_str)

            table.add_row(*row_data)

        console.print(table)
        console.print()

        # Only prompt for selection if running in an interactive terminal
        if sys.stdout.isatty():
            console.print(
                Panel(
                    "👇 Select a result to open in your browser",
                    style="bold green",
                    box=box.ROUNDED
                )
            )
            console.print()

            choices = [f"{i+1}. {result['title']}" for i, result in enumerate(all_results)]
            
            selected_result_str = questionary.select(
                "Choose a link:",
                choices=choices,
                qmark="🎯",
                pointer="►"
            ).ask()

            if selected_result_str:
                idx = int(selected_result_str.split('.')[0]) - 1
                selected_result = all_results[idx]
                
                console.print()
                console.print(
                    Panel(
                        f"🌐 Opening: [cyan]{selected_result['href']}[/cyan]",
                        title="[bold green]✓ Success[/bold green]",
                        border_style="green",
                        box=box.DOUBLE
                    )
                )
                webbrowser.open(selected_result['href'])
        else:
            console.print(
                Panel(
                    "⚠️  Non-interactive mode. Cannot select a link to open.",
                    title="[bold yellow]Info[/bold yellow]",
                    border_style="yellow"
                )
            )
    else:
        console.print(
            Panel(
                "😔 No results found across all sites.\n\n"
                "💡 Try:\n"
                "  • Using different keywords\n"
                "  • Checking your spelling\n"
                "  • Using more general terms",
                title="[bold yellow]⚠️  No Results[/bold yellow]",
                border_style="yellow",
                box=box.HEAVY,
                padding=(1, 2)
            )
        )

    # Closing banner
    console.print()
    console.print("╔═══════════════════════════════════════════════════════════════╗", style="bold cyan")
    console.print("║                   Thanks for using Virgil! 🚀                 ║", style="bold cyan")
    console.print("╚═══════════════════════════════════════════════════════════════╝", style="bold cyan")

if __name__ == "__main__":
    main()
