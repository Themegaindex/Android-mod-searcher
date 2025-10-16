import argparse
import webbrowser
import questionary
from ddgs import DDGS
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize the Rich Console
console = Console()

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

def main():
    """
    Main function to run the CLI search tool.
    """
    console.print(Panel("Welcome to the CLI Search Wizard!", title="[bold green]Virgil Search[/bold green]", expand=False))

    parser = argparse.ArgumentParser(description="Search for content on specific websites.")
    parser.add_argument("query", nargs='?', default=None, help="The search query.")
    parser.add_argument("--sites", nargs='+', choices=WEBSITES, default=WEBSITES, help="Specify the websites to search.")
    args = parser.parse_args()

    if args.query:
        query = args.query
    else:
        query = questionary.text("What would you like to search for?").ask()

    if not query:
        console.print("[bold red]No search query entered. Exiting.[/bold red]")
        return

    all_results = []
    with console.status(f"[bold green]Searching for '{query}'...[/]") as status:
        for site in args.sites:
            status.update(f"[bold green]Searching on {site}...[/]")
            search_results = search_site(query, site)
            if search_results:
                all_results.extend(search_results)

    if all_results:
        table = Table(title=f"Search Results for '{query}'", show_header=True, header_style="bold magenta")
        table.add_column("Title", style="bold blue")
        table.add_column("Link", style="green")

        for result in all_results:
            table.add_row(result['title'], result['href'])

        console.print(table)

        console.print("\n[bold green]Select a result to open:[/bold green]")

        choices = [f"{result['title']} ({result['href']})" for result in all_results]
        selected_result_str = questionary.select(
            "Choose a link to open (or press Ctrl+C to exit):",
            choices=choices
        ).ask()

        if selected_result_str:
            # Find the corresponding result dictionary
            selected_result = next((r for r in all_results if f"{r['title']} ({r['href']})" == selected_result_str), None)
            if selected_result:
                webbrowser.open(selected_result['href'])
                console.print(f"Opening {selected_result['href']} in your browser.")
    else:
        console.print("\n[bold yellow]No results found across all sites.[/bold yellow]")

if __name__ == "__main__":
    main()