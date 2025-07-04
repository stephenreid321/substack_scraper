# Substack Post Scraper 📰

A Python script that fetches Substack newsletter posts published within a specified time window, along with their like counts, subscriber data, and metadata.

## Features ✨

- **Flexible Input Options**: Single URL, file with multiple URLs, or Substack profile username
- **Time Window Filtering**: Fetch posts only within specified date ranges
- **Resume Functionality**: Automatically skips already-scraped newsletters if the script fails
- **Rate Limiting Protection**: Built-in exponential backoff for API rate limits
- **Rich Metadata**: Collects likes, subscriber counts, word counts, author info, and more
- **Multiple Output Formats**: Individual CSV files per newsletter + combined results
- **Robust Error Handling**: Continues processing even if individual newsletters fail

## Installation 🛠️

1. **Clone or download** this repository
2. **Install required dependencies**:
   ```bash
   pip install requests tqdm
   pip install git+https://github.com/NHagar/substack_api
   ```

## Usage 📋

### Basic Usage

**Single Newsletter:**
```bash
python substack_scraper.py --url https://example.substack.com --from 2024-01-01 --to 2024-12-31
```

**Multiple Newsletters from File:**
```bash
python substack_scraper.py --urls newsletters.txt --from 2024-01-01 --to 2024-12-31 --output posts.csv
```

**From Substack Profile:**
```bash
python substack_scraper.py --user stephenreid --from 2024-01-01 --to 2024-12-31
```

### Advanced Usage

**With Specific Date/Time:**
```bash
python substack_scraper.py --urls urls.txt --from "2024-01-01 12:00:00" --to "2024-01-31 23:59:59"
```

**Limit Posts Per Newsletter:**
```bash
python substack_scraper.py --url https://example.substack.com --from 2024-01-01 --to 2024-12-31 --max-posts 50
```

**Force Re-scraping:**
```bash
python substack_scraper.py --urls urls.txt --from 2024-01-01 --to 2024-12-31 --force-rescrape
```

## Command Line Arguments 🔧

### Required Arguments
- `--url` OR `--urls` OR `--user`: Input source (mutually exclusive)
  - `--url`: Single Substack newsletter URL
  - `--urls`: File containing URLs (one per line)
  - `--user`: Substack profile username (e.g., `stephenreid` or `@stephenreid`)
- `--from`: Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
- `--to`: End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)

### Optional Arguments
- `--output`: Output file name (default: `posts.csv`)
- `--max-posts`: Maximum posts per newsletter (default: auto-calculated)
- `--force-rescrape`: Force re-scraping existing newsletters

## Input File Format 📄

For `--urls`, create a text file with one URL per line:

```
https://newsletter1.substack.com
https://newsletter2.substack.com
https://custom-domain.com
# Comments start with #
https://newsletter3.substack.com
```

## Output Format 📊

The script generates CSV files with the following columns:

| Column | Description |
|--------|-------------|
| `newsletter_name` | Name extracted from URL |
| `newsletter_url` | Normalized newsletter URL |
| `free_subscriber_count` | Number of free subscribers |
| `likes` | Post reaction/like count |
| `likes_per_free_subscriber` | Engagement rate (likes per 100 subscribers) |
| `post_url` | Direct link to the post |
| `post_title` | Post title |
| `post_subtitle` | Post subtitle |
| `post_date` | Publication date (YYYY-MM-DD HH:MM:SS) |
| `author` | Author name(s) |
| `word_count` | Post word count |
| `is_paid` | Whether post is paid-only |
| `post_id` | Unique post identifier |

## Resume Functionality 🔄

If the script fails partway through:

1. **Simply run the same command again**
2. **Already-scraped newsletters will be skipped** (unless `--force-rescrape` is used)
3. **Processing continues** from where it left off

The script creates individual CSV files for each newsletter, allowing for robust resume capability.

## Output Structure 📁

For multiple newsletters:
```
substack_posts/
├── newsletter1.csv
├── newsletter2.csv
└── newsletter3.csv
combined.csv
```

For single newsletter:
```
posts.csv (or your specified filename)
```

## Error Handling 🛡️

- **Rate Limiting**: Automatic exponential backoff (1s, 2s, 4s, 8s, up to 60s)
- **Network Errors**: Retries with backoff for transient failures
- **Invalid URLs**: Skips malformed URLs with warnings
- **Missing Data**: Graceful handling of missing post metadata
- **Date Parsing**: Flexible date format support

## Examples 🎯

### Example 1: Single Newsletter
```bash
python substack_scraper.py --url https://platformer.news --from 2024-06-01 --to 2024-06-30
```

### Example 2: Multiple Newsletters
Create `urls.txt`:
```
https://newsletter1.substack.com
https://newsletter2.substack.com
https://custom-domain.com
```

Run:
```bash
python substack_scraper.py --urls urls.txt --from 2024-01-01 --to 2024-12-31
```

### Example 3: From Profile
```bash
python substack_scraper.py --user stephenreid --from 2024-01-01 --to 2024-12-31
```

## Supported URL Formats 🔗

- `https://newsletter.substack.com`
- `https://custom-domain.com`
- `https://substack.com/@username` (automatically converted)
- Post URLs (automatically extracts newsletter URL)

## Requirements 📋

- Python 3.6+
- `requests`
- `tqdm`
- `substack-api`

## Troubleshooting 🔧

**Common Issues:**

1. **Rate Limited**: The script handles this automatically with backoff
2. **No Posts Found**: Check date range and newsletter activity
3. **Invalid URLs**: Ensure URLs are properly formatted
4. **Permission Errors**: Check file write permissions in output directory

**Tips:**
- Use `--force-rescrape` to refresh existing data
- Check the console output for detailed progress information
- Individual newsletter files are saved immediately for resume capability

---

*Generated example files in `/example` with:*
```bash
python substack_scraper.py --urls urls.txt --from 2025-06-01 --to 2025-06-30
```