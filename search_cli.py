import argparse
from ddgs import DDGS
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

# List of websites to search. Easy to extend in the future.
WEBSITES = [
    "forum.mobilism.org",
    "4pda.to",
    "rockmods.net",
    "pdalife.com",
    "an1.com",
]

def search_site(query, site):
    """
    Performs a more precise search and filters the results for relevance.
    """
    try:
        # Enclose query in quotes for a more exact search
        search_query = f'"{query}" site:{site}'

        unfiltered_results = []
        with DDGS() as ddgs:
            # Fetch results from DuckDuckGo
            unfiltered_results = list(ddgs.text(search_query, max_results=10)) # Fetch more results to have a better chance after filtering

        # Filter results to ensure the query term is present in the title or body
        filtered_results = []
        for result in unfiltered_results:
            title = result.get('title', '').lower()
            body = result.get('body', '').lower()
            if query.lower() in title or query.lower() in body:
                filtered_results.append(result)

        # Return only the top 5 most relevant results
        return filtered_results[:5]

    except Exception as e:
        console.print(f"Error during search on {site}: {e}", style="bold red")
        return []

if __name__ == "__main__":
    console = Console()

    console.print(Panel("Welcome to the CLI Search Wizard!", title="[bold green]Virgil Search[/bold green]", expand=False))

    parser = argparse.ArgumentParser(description="Search for content on specific websites.")
    parser.add_argument("query", nargs='?', default=None, help="The search query.")
    args = parser.parse_args()

    if args.query:
        query = args.query
    else:
        query = Prompt.ask("[bold yellow]What would you like to search for?[/bold yellow]")

    with console.status(f"[bold green]Searching for '{query}'...[/]") as status:
        for site in WEBSITES:
            console.print(f"\n[bold cyan]--- Searching on {site} ---[/bold cyan]")
            search_results = search_site(query, site)

            if search_results:
                for i, result in enumerate(search_results, 1):
                    title = Text(f"{i}. {result['title']}", style="bold blue")
                    link = Text(result['href'], style="green")
                    console.print(title)
                    console.print(link)
            else:
                console.print("[italic red]No results found.[/italic red]")

    console.print("\n[bold green]Search complete![/bold green]")