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
CONFLUENCE_EMAIL=you@appliedintuition.co
CONFLUENCE_API_TOKEN=your_api_token
```

To get an API token:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and set it as `CONFLUENCE_API_TOKEN`

## Usage

```bash
# Create a new page interactively (prompts for placeholder values)
conflow new --title "My New Page" --parent-page-id 123456 --space-key MYSPACE

# Provide placeholder values via command line
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
  -p PROJECT_NAME="My Project" \
  -p OWNER="John Doe"

# Mix command-line and interactive (prompts only for missing placeholders)
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
  -p PROJECT_NAME="My Project"

# Non-interactive mode with all placeholders provided
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
  -p FIELD1="Value1" -p FIELD2="Value2" --non-interactive

# Create a page with a custom template
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE --template-page-id 999999

# Fill in test results interactively
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE --test-results
```

### Options

| Flag | Description |
|------|-------------|
| `--title` | Title of the new page (required) |
| `--parent-page-id` | ID of the parent page (required) |
| `--space-key` | Confluence space key (required) |
| `--template-page-id` | Override the default template page ID |
| `--placeholder`, `-p` | Provide placeholder value as KEY=VALUE (can be used multiple times) |
| `--test-results` | Interactively fill in test results table (P/F/I) |
| `--non-interactive` | Fail if any placeholders need user input |
| `--verbose`, `-v` | Enable verbose logging for debugging |

## Template Placeholders

Templates use the `{{FIELD_NAME}}` format for placeholders (uppercase letters and underscores only).

### Providing Placeholder Values

There are three ways to provide placeholder values:

1. **Interactive Mode (default)**: You'll be prompted to enter each placeholder value when creating a page.
   ```bash
   conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE
   # Prompts: "Enter value for PROJECT_NAME:", "Enter value for OWNER:", etc.
   ```

2. **Command-Line Mode**: Provide values via `-p` or `--placeholder` flags.
   ```bash
   conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
     -p PROJECT_NAME="My Project" \
     -p OWNER="John Doe"
   ```

3. **Mixed Mode**: Provide some values via command line, get prompted for the rest.
   ```bash
   conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
     -p PROJECT_NAME="My Project"
   # Only prompts for remaining placeholders (e.g., OWNER)
   ```

For automation, use `--non-interactive` to ensure all placeholders are provided via command line:
```bash
conflow new --title "My Page" --parent-page-id 123456 --space-key MYSPACE \
  -p FIELD1="Value1" -p FIELD2="Value2" --non-interactive
# Fails if any placeholders are missing
```

## Test Results

The `--test-results` flag allows you to interactively fill in Pass/Fail/Incomplete results for test rows in the template's Test section table.

### How It Works

1. The CLI parses the Test section table from the template
2. For each test row with "I" (incomplete) in the Raptor or HM400 columns:
   - Prompts: `{Scenario Name} - Raptor: Pass or Fail?`
   - Prompts: `{Scenario Name} - HM400: Pass or Fail?`
3. Updates the cell with "P" (Pass), "F" (Fail), or "I" (Incomplete) in the final page

### Example

```bash
conflow new --title "Test Report" --parent-page-id 123456 --space-key MYSPACE --test-results

# You'll be prompted:
#   Load Haul Dump Cycle - Raptor: Pass or Fail? P
#   Load Haul Dump Cycle - HM400: Pass or Fail? F
#   Emergency Stop - Raptor: Pass or Fail? P
#   ...
```

### Input Options

- Type `Pass`, `P`, `Fail`, `F`, `Incomplete`, or `I` (case-insensitive)
- Rows that already have "P", "F", or "I" are automatically skipped
- Use "I" to mark tests that are incomplete/not yet run
- Cannot be used with `--non-interactive` if any tests need input

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
