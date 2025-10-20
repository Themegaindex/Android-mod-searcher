import argparse
import sys
import webbrowser
import questionary
from ddgs import DDGS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

# Initialize the Rich Console
console = Console()

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

def search_site(query, site):
    """
    Performs a more precise search and filters the results for relevance.
    """
    try:
        search_query = f'"{query}" site:{site}'
        unfiltered_results = []
        
        with DDGS() as ddgs:
            unfiltered_results = list(ddgs.text(search_query, max_results=10))

        # Filter results
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

        for idx, result in enumerate(all_results, 1):
            table.add_row(
                str(idx),
                result['title'],
                result['href']
            )

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
