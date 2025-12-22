# Conflow

CLI tool for creating Confluence pages from templates with interactive placeholder substitution.

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd confluence_page_builder

# Option 1: Install with pip
pip install -r requirements.txt

# Option 2: Install with Poetry (if available)
poetry install
```

## Configuration

Set the following environment variables (or create a `.env` file):

```bash
CONFLUENCE_BASE_URL=https://appliedintuition.atlassian.net/wiki
CONFLUENCE_EMAIL=you@appliedintuition.com
CONFLUENCE_API_TOKEN=your_api_token
```

To get an API token:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and set it as `CONFLUENCE_API_TOKEN`

## Usage

```bash
# Create a new page interactively
conflow new --title "My New Page" --parent-page-id 123456 --space-key MYSPACE

# Create a page with a custom template
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE --template-page-id 999999

# Non-interactive mode (fails if any placeholders need values)
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE --non-interactive
```

### Options

| Flag | Description |
|------|-------------|
| `--title` | Title of the new page (required) |
| `--parent-page-id` | ID of the parent page (required) |
| `--space-key` | Confluence space key (required) |
| `--template-page-id` | Override the default template page ID |
| `--non-interactive` | Fail if any placeholders need user input |

## Template Placeholders

Templates use the `{{FIELD_NAME}}` format for placeholders. When creating a page, you'll be prompted to fill in each placeholder value.

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
PYTHONPATH=src pytest -v

# Run the CLI in development
PYTHONPATH=src python -m conflow --help
```

Alternatively, with Poetry:

```bash
poetry install
poetry run pytest
poetry run conflow --help
```
