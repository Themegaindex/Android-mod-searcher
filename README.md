# Virgil CLI Search

This is a powerful command-line search tool that allows you to search for content across a curated list of websites. It's designed to be fast, efficient, and easy to use, providing a clean and colorful interface right in your terminal.

## Features

- **CLI Interface:** A simple and intuitive command-line interface.
- **Multi-site Search:** Searches across multiple websites simultaneously.
- **Colorful Output:** Uses the `rich` library to provide a beautiful and readable output.
- **Easy to Extend:** The list of websites to search is easily configurable.
- **Two Modes of Operation:** Run it with a search query as an argument for quick searches, or run it without arguments for an interactive "wizard" mode.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install the dependencies:**
    Make sure you have Python 3 installed. Then, run the following command to install the necessary libraries:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

You can use the tool in two ways:

### 1. Direct Search

Provide the search query as a command-line argument:

```bash
python search_cli.py "Your Search Query"
```

For example:
```bash
python search_cli.py "Max Payne"
```

### 2. Interactive Mode

Simply run the script without any arguments to enter the interactive mode. The script will then prompt you to enter your search query.

```bash
python search_cli.py
```

## How to Add More Websites

This tool is designed to be easily extensible. To add more websites to the search list, simply open the `search_cli.py` file and add the new website's domain to the `WEBSITES` list.

For example, to add `example.com` to the search, modify the list like this:

```python
WEBSITES = [
    "forum.mobilism.org",
    "4pda.to",
    "rockmods.net",
    "pdalife.com",
    "an1.com",
    "example.com",  # Add your new website here
]
```