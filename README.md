# Substack Surfacer 📰

There was a golden age of Substack where I subscribed to <50 newsletters, and I could more or less read everything I wanted to. Now, however, I subscribe to >200, and I just don’t have time to keep up.

Enter: Substack Surfacer, a Python script that produces CSVs with the posts from all of the Substacks you follow, in a form that makes it easy to sort by the number of likes or (even more useful) the number of likes per subscriber (since of course, newsletters with more subscribers tend to get more likes).

Announcement post: https://stephenreid.substack.com/p/substack-surfacer-countering-substack

## Features ✨

- **Flexible Input Options**: Single URL, file with multiple URLs, or Substack profile username
- **Category Support**: Tab-separated format for organizing newsletters by category
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
python substack_surfacer.py --url https://example.substack.com --from 2025-01-01 --to 2025-12-31
```

**Multiple Newsletters from File:**
```bash
python substack_surfacer.py --urls newsletters.txt --from 2025-01-01 --to 2025-12-31 --output posts.csv
```

**From Substack Profile:**
```bash
python substack_surfacer.py --user stephenreid --from 2025-01-01 --to 2025-12-31
```

### Advanced Usage

**Limit Posts Per Newsletter:**
```bash
python substack_surfacer.py --url https://example.substack.com --from 2025-01-01 --to 2025-12-31 --max-posts 50
```

**Force Re-scraping:**
```bash
python substack_surfacer.py --urls urls.txt --from 2025-01-01 --to 2025-12-31 --force-rescrape
```

## Command Line Arguments 🔧

### Required Arguments
- `--url` OR `--urls` OR `--user`: Input source (mutually exclusive)
  - `--url`: Single Substack newsletter URL
  - `--urls`: File containing URLs (one per line, or tab-separated URL<TAB>CATEGORY format)
  - `--user`: Substack profile username (e.g., `stephenreid` or `@stephenreid`)
- `--from`: Start date (YYYY-MM-DD)
- `--to`: End date (YYYY-MM-DD)

### Optional Arguments
- `--output`: Output file name (default: `posts.csv`)
- `--max-posts`: Maximum posts per newsletter (default: auto-calculated)
- `--force-rescrape`: Force re-scraping existing newsletters

## Input File Format 📄

For `--urls`, create a text file with URLs in one of these formats:

### Simple Format (one URL per line):
```
https://newsletter1.substack.com
https://newsletter2.substack.com
https://custom-domain.com
# Comments start with #
https://newsletter3.substack.com
```

### Tab-Separated Format (URL + Category):
```
https://newsletter1.substack.com economics
https://newsletter2.substack.com philosophy
```

**Note**: Use actual tab characters (not spaces) to separate URL and category in the tab-separated format.

## Output Format 📊

The script generates CSV files with the following columns:

| Column | Description |
|--------|-------------|
| `newsletter_name` | Name extracted from URL |
| `newsletter_url` | Normalized newsletter URL |
| `category` | Category from tab-separated input (empty if not specified) |
| `free_subscriber_count` | Number of free subscribers |
| `likes` | Post reaction/like count |
| `likes_per_100_free_subscribers` | Engagement rate (likes per 100 free subscribers) |
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
substacks/
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
python substack_surfacer.py --url https://newsletter1.substack.com --from 2025-06-01 --to 2025-06-30
```

### Example 2: Multiple Newsletters (Simple Format)
Create `urls.txt`:
```
https://newsletter1.substack.com
https://newsletter2.substack.com
https://custom-domain.com
```

Run:
```bash
python substack_surfacer.py --urls urls.txt --from 2025-01-01 --to 2025-12-31
```

### Example 3: Multiple Newsletters with Categories
Create `urls.txt` with tab-separated format:
```
https://newsletter1.substack.com economics
https://newsletter2.substack.com philosophy
```

Run:
```bash
python substack_surfacer.py --urls urls.txt --from 2025-01-01 --to 2025-12-31
```

### Example 4: From Profile
```bash
python substack_surfacer.py --user stephenreid --from 2025-01-01 --to 2025-12-31
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

The example files in `/example` were generated with:

```
python substack_surfacer.py --urls urls.txt --from 2025-05-01 --to 2025-06-30
📊 Default max posts set to 65 (1 per day since 2025-05-01)
🔗 Processing 4 newsletter(s)...

📰 Processing newsletter 1/4: https://emergelakefront.substack.com/
📰 Fetching posts from: https://emergelakefront.substack.com
   👥 Fetching subscriber count...
   👥 Free subscribers: 22
   📄 Fetching posts...
   📄 Retrieved 8 posts, filtering by date window...
Filtering posts:   0%|                                           | 0/8 [00:00<?, ?post/s]🔍 Post metadata: A New Season at Lakefront 🌼
Filtering posts:  12%|████▍                              | 1/8 [00:00<00:01,  4.58post/s]🔍 Post metadata: Lakefront Community Kick-off: A Global Gathering at the Edge of the Future 🌍
Filtering posts:  25%|████████▊                          | 2/8 [00:00<00:01,  4.60post/s]🔍 Post metadata: "Fika with Dan Siegel" at Lakefront
Filtering posts:  38%|█████████████▏                     | 3/8 [00:00<00:01,  4.79post/s]🔍 Post metadata: Lakefront resident speaks at Tedx Stockholm
   ⏹️  Reached post older than 2025-05-01 (post date: 2025-04-29), stopping...
Filtering posts:  38%|█████████████▏                     | 3/8 [00:00<00:01,  3.51post/s]
   ℹ️  Only found 3 posts in time window 2025-05-01 to 2025-06-30
   ✅ Found 3 posts
   💾 Saving results for this newsletter...
💾 Writing 3 posts to CSV...
Writing CSV: 100%|█████████████████████████████████████| 3/3 [00:00<00:00, 26490.34row/s]
✅ Successfully saved 3 posts to: substacks/emergelakefront.csv
   ✅ Saved 3 posts to: substacks/emergelakefront.csv

📰 Processing newsletter 2/4: https://substack.com/@tuckerwalsh
📰 Fetching posts from: https://tuckerwalsh.substack.com
   👥 Fetching subscriber count...
   👥 Free subscribers: 182
   📄 Fetching posts...
   📄 Retrieved 44 posts, filtering by date window...
Filtering posts:   0%|                                          | 0/44 [00:00<?, ?post/s]🔍 Post metadata: Deep AF Green
Filtering posts:   2%|▊                                 | 1/44 [00:00<00:20,  2.13post/s]🔍 Post metadata: A Vow to Soul
   ⏹️  Reached post older than 2025-05-01 (post date: 2025-04-22), stopping...
Filtering posts:   2%|▊                                 | 1/44 [00:00<00:42,  1.02post/s]
   ℹ️  Only found 1 posts in time window 2025-05-01 to 2025-06-30
   ✅ Found 1 posts
   💾 Saving results for this newsletter...
💾 Writing 1 posts to CSV...
Writing CSV: 100%|█████████████████████████████████████| 1/1 [00:00<00:00, 15592.21row/s]
✅ Successfully saved 1 posts to: substacks/tuckerwalsh.csv
   ✅ Saved 1 posts to: substacks/tuckerwalsh.csv

📰 Processing newsletter 3/4: https://octopusyarn.substack.com/
📰 Fetching posts from: https://octopusyarn.substack.com
   👥 Fetching subscriber count...
   👥 Free subscribers: UNKNOWN
   📄 Fetching posts...
   📄 Retrieved 23 posts, filtering by date window...
Filtering posts:   0%|                                          | 0/23 [00:00<?, ?post/s]🔍 Post metadata: Why Privacy makes us Human
Filtering posts:   4%|█▍                                | 1/23 [00:00<00:04,  4.56post/s]🔍 Post metadata: Technology is Re-Enchanting the World
   ⏹️  Reached post older than 2025-05-01 (post date: 2025-04-12), stopping...
Filtering posts:   4%|█▍                                | 1/23 [00:00<00:10,  2.16post/s]
   ℹ️  Only found 1 posts in time window 2025-05-01 to 2025-06-30
   ✅ Found 1 posts
   💾 Saving results for this newsletter...
💾 Writing 1 posts to CSV...
Writing CSV: 100%|█████████████████████████████████████| 1/1 [00:00<00:00, 22192.08row/s]
✅ Successfully saved 1 posts to: substacks/octopusyarn.csv
   ✅ Saved 1 posts to: substacks/octopusyarn.csv

📰 Processing newsletter 4/4: https://stephenreid.substack.com/
📰 Fetching posts from: https://stephenreid.substack.com
   👥 Fetching subscriber count...
   👥 Free subscribers: 3,000
   📄 Fetching posts...
   📄 Retrieved 65 posts, filtering by date window...
Filtering posts:   0%|                                          | 0/65 [00:00<?, ?post/s]🔍 Post metadata: Substack Surfacer: countering Substack overwhelm
Filtering posts:   2%|▌                                 | 1/65 [00:00<00:13,  4.66post/s]🔍 Post metadata: Introducing Hilma Church-Turing
Filtering posts:   3%|█                                 | 2/65 [00:00<00:13,  4.75post/s]🔍 Post metadata: In Correspondence #49
Filtering posts:   5%|█▌                                | 3/65 [00:00<00:13,  4.74post/s]🔍 Post metadata: Four reasons to join us at Emerge Lakefront
Filtering posts:   6%|██                                | 4/65 [00:00<00:13,  4.55post/s]🔍 Post metadata: In Correspondence #48
Filtering posts:   8%|██▌                               | 5/65 [00:01<00:14,  4.11post/s]🔍 Post metadata: Life as Practice: A Yearlong Group Mentorship
   ⏹️  Reached post older than 2025-05-01 (post date: 2025-04-30), stopping...
Filtering posts:   8%|██▌                               | 5/65 [00:01<00:16,  3.67post/s]
   ℹ️  Only found 4 posts in time window 2025-05-01 to 2025-06-30
   ✅ Found 4 posts
   💾 Saving results for this newsletter...
💾 Writing 4 posts to CSV...
Writing CSV: 100%|█████████████████████████████████████| 4/4 [00:00<00:00, 40427.03row/s]
✅ Successfully saved 4 posts to: substacks/stephenreid.csv
   ✅ Saved 4 posts to: substacks/stephenreid.csv

💾 Saving combined results from all 4 newsletters...
💾 Writing 9 posts to CSV...
Writing CSV: 100%|█████████████████████████████████████| 9/9 [00:00<00:00, 51080.83row/s]
✅ Successfully saved 9 posts to: combined.csv
✅ Saved combined results: combined.csv

🎉 Completed! Processed 9 posts total.
📊 Newly processed newsletters: 4
📊 Individual newsletter files saved after each processing step
📊 Combined results also saved for all newsletters
🚀 All newsletters were freshly processed
```