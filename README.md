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
# Required
CONFLUENCE_BASE_URL=https://appliedintuition.atlassian.net/wiki
CONFLUENCE_EMAIL=you@appliedintuition.co
CONFLUENCE_API_TOKEN=your_api_token

# Optional - set defaults to avoid specifying on every command
CONFLUENCE_DEFAULT_PARENT_PAGE_ID=2436039354
CONFLUENCE_DEFAULT_SPACE_KEY=Echelon
```

**Required variables:**
- `CONFLUENCE_BASE_URL` - Your Confluence base URL
- `CONFLUENCE_EMAIL` - Your Confluence email
- `CONFLUENCE_API_TOKEN` - Your API token

**Optional variables:**
- `CONFLUENCE_DEFAULT_PARENT_PAGE_ID` - Default parent page ID for new pages
- `CONFLUENCE_DEFAULT_SPACE_KEY` - Default space key for new pages

To get an API token:
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Copy the token and set it as `CONFLUENCE_API_TOKEN`

## Usage

Conflow has two main commands:

**Quick Start:**
```bash
# Create a new page
poetry run conflow new --title "My Page Title"

# Edit an existing page's test results
poetry run conflow edit
```

That's it! Parent page ID and space key are configured in your `.env` file.

### 1. Create New Page (`conflow new`)

Create a new Confluence page from a template.

```bash
# Simple usage (uses config defaults for parent-page-id and space-key)
poetry run conflow new --title "My New Page"

# Create a page with test results
poetry run conflow new --title "Test Report" --test-results

# Provide placeholder values via command line
poetry run conflow new --title "My Page" \
  -p PROJECT_NAME="My Project" \
  -p OWNER="John Doe"

# Override config defaults if needed
poetry run conflow new --title "My Page" --parent-page-id 999999 --space-key OTHER_SPACE

# Create a page with a custom template
poetry run conflow new --title "My Page" --template-page-id 999999
```

**Options for `conflow new`:**

| Flag | Description |
|------|-------------|
| `--title` | Title of the new page (required) |
| `--parent-page-id` | ID of the parent page (uses `CONFLUENCE_DEFAULT_PARENT_PAGE_ID` if not provided) |
| `--space-key` | Confluence space key (uses `CONFLUENCE_DEFAULT_SPACE_KEY` if not provided) |
| `--template-page-id` | Override the default template page ID |
| `--placeholder`, `-p` | Provide placeholder value as KEY=VALUE (can be used multiple times) |
| `--test-results` | Interactively fill in test results table (P/F/I) |
| `--non-interactive` | Fail if any placeholders need user input |
| `--verbose`, `-v` | Enable verbose logging for debugging |

### 2. Edit Existing Page (`conflow edit`)

Edit an existing Confluence page's test results. Test results are enabled by default.

```bash
# Edit an existing page (prompts for page ID)
poetry run conflow edit

# Enable verbose logging
poetry run conflow --verbose edit
```

When you run `conflow edit`, you'll be prompted to enter the page ID:
```
Enter the page ID to edit:
Format: 'pageID: 2436039300' or just '2436039300'

  Page ID: 2436039300
```

The tool will then:
1. Fetch the existing page
2. Prompt you to fill in incomplete test results (cells marked with "I")
3. Apply color coding (green for Pass, red for Fail)
4. Update the page in Confluence

**Options for `conflow edit`:**

| Flag | Description |
|------|-------------|
| `--test-results` | Interactively fill in test results table (enabled by default) |
| `--non-interactive` | Fail if any test results need user input |
| `--verbose`, `-v` | Enable verbose logging for debugging |

## Template Placeholders

Templates use the `{{FIELD_NAME}}` format for placeholders (uppercase letters and underscores only).

### Providing Placeholder Values

There are three ways to provide placeholder values:

1. **Interactive Mode (default)**: You'll be prompted to enter each placeholder value when creating a page.
   ```bash
   poetry run conflow new --title "My Page"
   # Prompts: "Enter value for PROJECT_NAME:", "Enter value for OWNER:", etc.
   ```

2. **Command-Line Mode**: Provide values via `-p` or `--placeholder` flags.
   ```bash
   poetry run conflow new --title "My Page" \
     -p PROJECT_NAME="My Project" \
     -p OWNER="John Doe"
   ```

3. **Mixed Mode**: Provide some values via command line, get prompted for the rest.
   ```bash
   poetry run conflow new --title "My Page" \
     -p PROJECT_NAME="My Project"
   # Only prompts for remaining placeholders (e.g., OWNER)
   ```

For automation, use `--non-interactive` to ensure all placeholders are provided via command line:
```bash
poetry run conflow new --title "My Page" \
  -p FIELD1="Value1" -p FIELD2="Value2" --non-interactive
# Fails if any placeholders are missing
```

## Test Results

The test results feature allows you to interactively fill in Pass/Fail/Incomplete results for test rows in the Test section table.

### When to Use

- **Creating new pages**: Use `--test-results` flag with `conflow new`
- **Editing existing pages**: Test results are **enabled by default** with `conflow edit`

### How It Works

1. The CLI parses the Test section table from the page
2. For each test row with "I" (incomplete) in the Raptor or HM400 columns:
   - Prompts: `{Scenario Name} - Raptor: Pass or Fail?`
   - Prompts: `{Scenario Name} - HM400: Pass or Fail?`
3. Updates the cell with "P" (Pass), "F" (Fail), or "I" (Incomplete)
4. **Applies color coding:**
   - **Green background** for Pass (P)
   - **Red background** for Fail (F)
   - **No color** for Incomplete (I)

### Examples

**Create a new page with test results:**
```bash
poetry run conflow new --title "Test Report" --test-results

# You'll be prompted:
#   Load Haul Dump Cycle - Raptor: Pass or Fail? P
#   Load Haul Dump Cycle - HM400: Pass or Fail? F
#   Emergency Stop - Raptor: Pass or Fail? P
#   ...
```

**Edit an existing page's test results:**
```bash
poetry run conflow edit

# You'll be prompted for page ID:
#   Page ID: 2436039300
#
# Then prompted for each incomplete test:
#   Load Haul Dump Cycle - Raptor: Pass or Fail? P
#   ...
```

### Input Options

- Type `Pass`, `P`, `Fail`, `F`, `Incomplete`, or `I` (case-insensitive)
- Rows that already have "P", "F", "Pass", or "Fail" are **automatically skipped**
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
