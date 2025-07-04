#!/usr/bin/env python3
"""
Substack Post Scraper

This script takes a list of Substack newsletter URLs and fetches all posts 
published within a specified time window, along with their like counts and metadata.

The script includes resume functionality - if it fails halfway through, it will
skip newsletters that have already been scraped (by checking for existing CSV files).

Usage:
    python substack_scraper.py --urls urls.txt --from 2024-01-01 --to 2024-12-31 --output posts.csv
    python substack_scraper.py --url https://example.substack.com --from 2024-01-01 --to 2024-12-31
    python substack_scraper.py --user stephenreid --from 2024-01-01 --to 2024-12-31
"""

import os
import csv
import argparse
import time
import re
import requests
import sys
import json
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from tqdm import tqdm
from typing import List, Dict, Optional, Callable, Any
from substack_api import Newsletter, Post

# Configuration constants
DEFAULT_MAX_RETRIES = 8
MAX_BACKOFF_WAIT_TIME = 60  # seconds
REQUEST_TIMEOUT = 10  # seconds


def retry_with_backoff(func: Callable[[], Any], max_retries: int = DEFAULT_MAX_RETRIES, 
                      operation_name: str = "operation") -> Any:
    """Execute a function with exponential backoff retry logic for rate limiting."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a rate limiting error (429)
            if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
                if attempt < max_retries - 1:
                    # Exponential backoff with cap: 1s, 2s, 4s, 8s, 16s (max 60s)
                    wait_time = min(2 ** attempt, MAX_BACKOFF_WAIT_TIME)
                    print(f"⏳ Rate limited for {operation_name}, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    return 'Rate limited'
            else:
                # For other errors, don't retry
                return f'Error: {str(e)}'
    
    return 'Failed after retries'

def ensure_directory(file_path: str):
    """Create directory for file path if it doesn't exist."""
    output_dir = os.path.dirname(file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
def parse_datetime(date_str: str, raise_on_error: bool = False) -> Optional[datetime]:
    """
    Parse datetime string in various formats, returning None if parsing fails.
    
    Args:
        date_str: The date string to parse
        raise_on_error: If True, raises ValueError on parsing failure instead of returning None
    
    Returns:
        datetime object with UTC timezone, or None if parsing fails (when raise_on_error=False)
    """
    if not date_str:
        if raise_on_error:
            raise ValueError("Empty date string provided")
        return None
    
    # Try ISO format first (most common for APIs)
    try:
        if 'T' in date_str:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        pass
    
    # Try various datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2024-01-01 12:00:00
        '%Y-%m-%d',           # 2024-01-01
        '%Y/%m/%d',           # 2024/01/01
        '%m/%d/%Y',           # 01/01/2024
        '%d/%m/%Y',           # 01/01/2024 (European)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    
    # If we get here, parsing failed
    if raise_on_error:
        raise ValueError(f"Unable to parse date: {date_str}")
    return None

def calculate_default_max_posts(from_date: datetime, to_date: datetime) -> int:
    """Calculate default max posts based on days since the from date (1 post per day)."""
    now = datetime.now(timezone.utc)
    days_since = (now - from_date).days
    # Ensure at least 1 day and cap at a reasonable maximum
    return max(1, min(days_since, 365))  # Between 1 and 365 days


def load_urls_from_file(file_path: str) -> List[str]:
    """Load Substack URLs from a text file (one URL per line)."""
    urls = []
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line and not line.startswith('#'):  # Skip empty lines and comments
                # Basic URL validation
                if line.startswith(('http://', 'https://')):
                    urls.append(line)
                else:
                    print(f"⚠️  Line {line_num}: Invalid URL format: {line}")
    
    return urls


def normalize_substack_url(url: str) -> str:
    """Normalize Substack URL to ensure it's in the correct format."""
    # Remove trailing slashes and ensure proper format
    url = url.rstrip('/')
    
    # Handle @username format (e.g., https://substack.com/@tuckerwalsh -> https://tuckerwalsh.substack.com)
    if 'substack.com/@' in url:
        parsed = urlparse(url)
        username = parsed.path.lstrip('/@')  # Remove leading /@ from path
        url = f"{parsed.scheme}://{username}.substack.com"
    
    # If it's a post URL, extract the newsletter URL
    elif '/p/' in url:
        parsed = urlparse(url)
        url = f"{parsed.scheme}://{parsed.netloc}"
    
    return url


def get_free_subscriber_count(publication_url: str, max_retries: int = DEFAULT_MAX_RETRIES) -> str:
    """Get free subscriber count for a Substack newsletter with retries."""
    if not publication_url:
        return 'No URL'
    
    publication_url = normalize_substack_url(publication_url)
    
    def get_subscriber_count():
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(publication_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        content = response.text
        
        # Look for freeSubscriberCount in the content
        subscriber_match = re.search(r'\\"freeSubscriberCount\\":\\"([^"]+)\\"', content)
        if subscriber_match:
            return subscriber_match.group(1)
        
        # Fallback to freeSubscriberCountOrderOfMagnitude if freeSubscriberCount not found
        magnitude_match = re.search(r'\\"freeSubscriberCountOrderOfMagnitude\\":\\"([^"]+)\\"', content)
        if magnitude_match:
            return magnitude_match.group(1)
        
        return 'UNKNOWN'  # No subscriber count found
    
    return retry_with_backoff(get_subscriber_count, max_retries, f"subscriber count {publication_url}...")


def fetch_newsletter_posts(newsletter_url: str, from_date: datetime, to_date: datetime, max_posts: Optional[int] = None) -> List[Dict]:
    """Fetch all posts from a newsletter published within the specified time window."""
    try:
        original_newsletter_url = newsletter_url
        newsletter_url = normalize_substack_url(newsletter_url)
        print(f"📰 Fetching posts from: {newsletter_url}")
        
        # Initialize newsletter
        newsletter = Newsletter(newsletter_url)
        
        # Always use URL extraction for newsletter name consistency
        newsletter_name = extract_newsletter_name_from_url(newsletter_url)
        
        # Get free subscriber count for the newsletter
        print("   👥 Fetching subscriber count...")
        free_subscriber_count = get_free_subscriber_count(newsletter_url)
        print(f"   👥 Free subscribers: {free_subscriber_count}")
        
        # Fetch posts - the API doesn't support offset-based pagination
        # We'll fetch a large batch and filter on our end
        print("   📄 Fetching posts...")
        
        # Start with a reasonable limit (API may have its own internal limits)
        fetch_limit = max_posts if max_posts else 100
        
        # Add retry mechanism for getting posts (in case of rate limiting)
        def get_posts():
            return newsletter.get_posts(limit=fetch_limit)
        
        posts = retry_with_backoff(get_posts, DEFAULT_MAX_RETRIES, "posts")
        
        if isinstance(posts, str):  # Error message from retry_with_backoff
            print(f"   ❌ {posts}")
            return []
        
        if not posts:
            print("   ⚠️  No posts found (empty list returned)")
            return []
        
        print(f"   📄 Retrieved {len(posts)} posts, filtering by date window...")
        
        # Make to_date inclusive by adding one day
        to_date_inclusive = to_date + timedelta(days=1)
        
        filtered_posts = []
        for post in tqdm(posts, desc="Filtering posts", unit="post"):

            if 'substack.com/@' in original_newsletter_url:
                # For @username URLs, we need to follow redirects to get the actual post URL
                try:
                    def get_redirected_post_url():
                        # Get the post's initial URL (this might be in @username format)
                        post_id = post.url.split('p-')[-1]                        
                        initial_url = f"https://{original_newsletter_url.split('@')[-1]}.substack.com/p/{post_id}"

                        response = requests.get(initial_url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                        response.raise_for_status()
                        
                        return response.url
                    
                    redirected_url = retry_with_backoff(get_redirected_post_url, DEFAULT_MAX_RETRIES, "post URL redirect")
                    
                    if isinstance(redirected_url, str) and redirected_url.startswith('http'):
                        # Successfully got redirected URL, create new post object with correct URL
                        post = Post(redirected_url)
                    else:
                        print(f"   ⚠️  Failed to get redirected URL, skipping post")
                        continue
                        
                except Exception as e:
                    print(f"   ⚠️  Failed to follow redirect for post: {str(e)}")
                    continue

            try:
                # Retry mechanism with exponential backoff for individual post
                def get_post_metadata():
                    return post.get_metadata()
                
                post_data = retry_with_backoff(get_post_metadata, DEFAULT_MAX_RETRIES, "post metadata")
                
                if isinstance(post_data, str) or not post_data:  # Error or no data
                    continue
                
                print(f"🔍 Post metadata: {post_data.get('title', 'Unknown Title')}")
                
                # Parse post date
                post_date_str = post_data.get('post_date') or post_data.get('created_at')
                if not post_date_str:
                    print(f"   ⚠️  No date found for post: {post_data.get('title', 'Unknown')}")
                    continue
                
                # Convert to datetime using the flexible parser
                post_date = parse_datetime(post_date_str)
                if not post_date:
                    print(f"   ⚠️  Could not parse date '{post_date_str}' for post: {post_data.get('title', 'Unknown')}")
                    continue
                
                # Check if post is within the specified time window (to_date is now inclusive)
                if from_date <= post_date < to_date_inclusive:
                    # Safely extract author name
                    published_bylines = post_data.get('publishedBylines', [])
                    author_name = newsletter_name  # Default fallback
                    if published_bylines and len(published_bylines) > 0:
                        author_names = [byline.get('name', '') for byline in published_bylines if byline.get('name')]
                        author_name = ', '.join(author_names) if author_names else newsletter_name
                    
                    post_info = {
                        'newsletter_name': newsletter_name,
                        'newsletter_url': newsletter_url,
                        'free_subscriber_count': free_subscriber_count,
                        'likes': post_data.get('reaction_count', 0),
                        'likes_per_free_subscriber': calculate_likes_per_free_subscriber(post_data.get('reaction_count', 0), free_subscriber_count),
                        'post_url': post.url if hasattr(post, 'url') else post_data.get('canonical_url', ''),                        
                        'post_title': post_data.get('title', 'No Title'),
                        'post_subtitle': post_data.get('subtitle', ''),                        
                        'post_date': post_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'author': author_name,
                        'word_count': post_data.get('wordcount', 0),                        
                        'is_paid': post_data.get('audience', 'everyone') != 'everyone',
                        'post_id': post_data.get('id', ''),
                    }
                    filtered_posts.append(post_info)
                    
                    # Check if we have enough posts
                    if max_posts and len(filtered_posts) >= max_posts:
                        break
                elif post_date < from_date:
                    # Post is older than from_date, stop fetching since posts are chronological
                    print(f"   ⏹️  Reached post older than {from_date.strftime('%Y-%m-%d')} (post date: {post_date.strftime('%Y-%m-%d')}), stopping...")
                    break
            
            except Exception as e:
                print(f"⚠️  Unexpected error processing post: {str(e)[:100]}")
                continue
        
        if max_posts and len(filtered_posts) < max_posts:
            print(f"   ℹ️  Only found {len(filtered_posts)} posts in time window {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
        
        return filtered_posts
        
    except Exception as e:
        print(f"❌ Error processing newsletter {newsletter_url}: {e}")
        return []


def calculate_likes_per_free_subscriber(likes: str, free_subscriber_count: str) -> float:
    
    if free_subscriber_count == 'UNKNOWN':
        return 'UNKNOWN'
        
    subscriber_count = free_subscriber_count.replace(',', '')
    try:
        subscriber_num = float(subscriber_count)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid subscriber count: {subscriber_count}")
        
    return round(100 * (likes / subscriber_num), 2)


def save_posts_to_csv(posts: List[Dict], output_file: str):
    """Save post data to a CSV file."""
    ensure_directory(output_file)
    
    if not posts:
        print("📝 Creating empty CSV file (no posts to save)...")
    else:
        print(f"💾 Writing {len(posts)} posts to CSV...")
            
    fieldnames = [
        'newsletter_name', 'newsletter_url', 'free_subscriber_count',
        'likes', 'likes_per_free_subscriber',
        'post_url', 'post_title', 'post_subtitle', 'post_date',
        'author', 'word_count',  
        'is_paid', 'post_id'
    ]
    
    # Write posts to CSV file (or create empty file with headers)
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        if posts:
            for post in tqdm(posts, desc="Writing CSV", unit="row"):
                writer.writerow(post)
    
    print(f"✅ Successfully saved {len(posts)} posts to: {output_file}")


def check_existing_newsletter_file(url: str) -> Optional[str]:
    """Check if a CSV file already exists for this newsletter and return the filename if it does."""
    # Generate the expected filename for this newsletter
    newsletter_name = extract_newsletter_name_from_url(url)
    newsletter_name_safe = sanitize_filename(newsletter_name)
    
    # Check for individual newsletter file in substacks directory
    expected_filename = os.path.join('substacks', f"{newsletter_name_safe}.csv")
    
    # Also check the original filename (in case it's a single newsletter run)
    possible_files = [expected_filename]
    
    for filename in possible_files:
        if os.path.exists(filename):  # Now accepts empty files too (size >= 0)
            return filename
    
    return None


def load_existing_posts_from_csv(csv_file: str) -> List[Dict]:
    """Load existing posts from a CSV file."""
    posts = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                posts.append(dict(row))
        print(f"   📄 Loaded {len(posts)} existing posts from {csv_file}")
        return posts
    except Exception as e:
        print(f"   ⚠️  Error loading existing CSV {csv_file}: {e}")
        return []


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    # Replace or remove characters that are not safe for filenames
    # Keep alphanumeric, spaces, hyphens, and underscores
    
    # Replace unsafe characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace multiple spaces/underscores with single underscore
    sanitized = re.sub(r'[_\s]+', '_', sanitized)
    # Remove leading/trailing underscores and spaces
    sanitized = sanitized.strip('_ ')
    # Limit length to avoid filesystem issues
    if len(sanitized) > 50:
        sanitized = sanitized.rstrip('_')
    return sanitized if sanitized else 'unknown'


def extract_newsletter_name_from_url(url: str) -> str:
    """Extract newsletter name from Substack URL."""
    try:
        # First normalize the URL to handle @username format and other cases
        normalized_url = normalize_substack_url(url)
        parsed = urlparse(normalized_url)
        
        if '.substack.com' in parsed.netloc:
            # Extract the subdomain part (e.g., 'cryptogood' from 'cryptogood.substack.com')
            subdomain = parsed.netloc.split('.substack.com')[0]
            newsletter_name = subdomain if subdomain else parsed.netloc
        else:
            # For custom domains, use the full domain
            newsletter_name = parsed.netloc
            
        return sanitize_filename(newsletter_name)
    except Exception as e:
        print(f"   ⚠️  Error extracting newsletter name from URL {url}: {e}")
        return 'unknown'


def get_newsletters_from_profile(profile_url: str) -> List[str]:
    """Extract newsletter URLs from a Substack profile page."""
    try:
        print(f"📋 Fetching newsletters from profile: {profile_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(profile_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        content = response.text
                
        # More flexible regex to handle various whitespace patterns and escaped quotes
        # The JSON string can contain escaped quotes and span multiple lines
        preloads_match = re.search(r'window\._preloads\s*=\s*JSON\.parse\s*\(\s*"((?:[^"\\]|\\.)*)"\s*\)', content, re.DOTALL)
        if not preloads_match:
            # Try alternative pattern in case the JSON string uses single quotes or different structure
            preloads_match = re.search(r'window\._preloads\s*=\s*JSON\.parse\s*\(\s*\'((?:[^\'\\]|\\.)*)\'\s*\)', content, re.DOTALL)
        
        if not preloads_match:
            print("   ❌ Could not find profile data in page")
            return []
        
        # Decode the JSON string (it's double-encoded)
        json_str = preloads_match.group(1)
        # Unescape the JSON string
        json_str = json_str.replace('\\"', '"').replace('\\\\', '\\')
        
        try:
            data = json.loads(json_str)
            print(f"   ✅ Successfully parsed JSON data")
        except json.JSONDecodeError as e:
            print(f"   ❌ Failed to parse profile JSON: {e}")
            return []
        
        # Extract newsletter URLs from subscriptions
        newsletter_urls = []
        profile_data = data.get('profile', {})
        
        subscriptions = profile_data.get('subscriptions', [])
        
        if not subscriptions:
            print("   ⚠️  No subscriptions found in profile")
            return []
        
        for subscription in subscriptions:
            publication = subscription.get('publication', {})
            if publication:
                subdomain = publication.get('subdomain')
                custom_domain = publication.get('custom_domain')
                
                if custom_domain:
                    url = f"https://{custom_domain}"
                elif subdomain:
                    url = f"https://{subdomain}.substack.com"
                else:
                    continue
                
                newsletter_urls.append(url)
        
        print(f"   ✅ Found {len(newsletter_urls)} newsletter(s)")
        return newsletter_urls
        
    except requests.RequestException as e:
        print(f"   ❌ Error fetching profile page: {e}")
        return []
    except Exception as e:
        print(f"   ❌ Unexpected error parsing profile: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Fetch Substack posts published within a time window with like counts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python substack_scraper.py --url https://example.substack.com --from 2024-01-01 --to 2024-12-31
  python substack_scraper.py --urls newsletters.txt --from 2023-12-01 --to 2023-12-31 --output posts.csv
  python substack_scraper.py --user stephenreid --from 2024-01-01 --to 2024-12-31
  python substack_scraper.py --urls urls.txt --from "2024-01-01 12:00:00" --to "2024-01-31 23:59:59"
  
Resume functionality:
  If the script fails halfway through, simply run the same command again.
  It will automatically skip newsletters that have already been scraped.
        """
    )
    
    # URL input options (mutually exclusive)
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument('--url', type=str, help='Single Substack newsletter URL')
    url_group.add_argument('--urls', type=str, help='File containing Substack URLs (one per line)')
    url_group.add_argument('--user', type=str, help='Substack profile username (e.g., stephenreid or @stephenreid)')
    
    # Required arguments
    parser.add_argument('--from', type=str, required=True, dest='from_date',
                       help='Start date for time window (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--to', type=str, required=True, dest='to_date',
                       help='End date for time window (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    
    # Optional arguments
    parser.add_argument('--output', type=str, default='posts.csv', 
                       help='Output file name (default: posts.csv)')
    parser.add_argument('--max-posts', type=int, default=None,
                       help='Maximum number of posts per newsletter')
    parser.add_argument('--force-rescrape', action='store_true',
                       help='Force re-scraping of all newsletters, even if CSV files exist')
    
    args = parser.parse_args()
    
    # Parse the from and to dates
    try:
        from_date = parse_datetime(args.from_date, raise_on_error=True)
        to_date = parse_datetime(args.to_date, raise_on_error=True)
        
        # Validate date range
        if from_date >= to_date:
            raise ValueError("From date must be earlier than to date")
        
    except ValueError as e:
        print(f"❌ {e}")
        return
    
    # Calculate default max posts based on days in the time window
    if args.max_posts is None:
        default_max_posts = calculate_default_max_posts(from_date, to_date)
        print(f"📊 Default max posts set to {default_max_posts} (1 per day since {from_date.strftime('%Y-%m-%d')})")
        args.max_posts = default_max_posts
    
    # Get list of URLs
    if args.url:
        urls = [args.url]
    elif args.user:
        # Handle profile username - add @ if not present and construct full URL
        username = args.user.lstrip('@')  # Remove @ if present
        profile_url = f"https://substack.com/@{username}"
        urls = get_newsletters_from_profile(profile_url)
    else:
        urls = load_urls_from_file(args.urls)
        if not urls:
            print("❌ No valid URLs found.")
            return
    
    print(f"🔗 Processing {len(urls)} newsletter(s)...")
    
    # Track all posts for final summary
    all_posts = []
    
    # Track skipped and processed newsletters
    skipped_newsletters = []
    processed_newsletters = []
    
    # Process each newsletter individually
    for i, url in enumerate(urls, 1):
        print(f"\n📰 Processing newsletter {i}/{len(urls)}: {url}")
        
        # Check if this newsletter was already scraped (unless force-rescrape is enabled)
        if not args.force_rescrape:
            existing_file = check_existing_newsletter_file(url)
            if existing_file:
                print(f"   ✅ Found existing file: {existing_file}")
                print(f"   ⏭️  Skipping this newsletter (use --force-rescrape to override)")
                
                # Load existing data
                existing_posts = load_existing_posts_from_csv(existing_file)
                
                # Add to collections regardless of whether there are posts (empty files are valid)
                all_posts.extend(existing_posts)
                skipped_newsletters.append(url)
                continue
        
        try:
            posts = fetch_newsletter_posts(url, from_date, to_date, args.max_posts)
            
            if not posts:
                print(f"   📝 No posts found for this newsletter - creating empty file to mark as processed")
            else:
                print(f"   ✅ Found {len(posts)} posts")
                            
            # Add to total collection (even if empty, for tracking)
            all_posts.extend(posts)
            processed_newsletters.append(url)
            
            # Save CSV immediately after processing this newsletter
            print(f"   💾 Saving results for this newsletter...")
            
            # Create output filename with newsletter name
            if len(urls) > 1:
                # For multiple newsletters, create individual files using newsletter name
                newsletter_name = extract_newsletter_name_from_url(url)
                newsletter_name_safe = sanitize_filename(newsletter_name)
                
                # Create filename in substacks directory
                individual_output = os.path.join('substacks', f"{newsletter_name_safe}.csv")
            else:
                # For single newsletter, use original filename in root directory
                individual_output = args.output
            
            save_posts_to_csv(posts, individual_output)
            
            print(f"   ✅ Saved {len(posts)} posts to: {individual_output}")
        
        except Exception as e:
            print(f"   ❌ Error processing newsletter {url}: {e}")
            print(f"   🔄 You can resume by running the same command again - completed newsletters will be skipped")
            continue
    
    # Save combined results if processing multiple newsletters
    if len(urls) > 1:
        print(f"\n💾 Saving combined results from all {len(urls)} newsletters...")
        
        # Create combined output filename in substacks directory
        combined_output = os.path.join('combined.csv')
        
        save_posts_to_csv(all_posts, combined_output)
        
        print(f"✅ Saved combined results: {combined_output}")
    
    # Summary
    print(f"\n🎉 Completed! Processed {len(all_posts)} posts total.")
    if processed_newsletters:
        print(f"📊 Newly processed newsletters: {len(processed_newsletters)}")
    if skipped_newsletters:
        print(f"⏭️  Skipped newsletters (already existed): {len(skipped_newsletters)}")
    
    print(f"📊 Individual newsletter files saved after each processing step")
    if len(urls) > 1:
        print(f"📊 Combined results also saved for all newsletters")
    
    if processed_newsletters and not skipped_newsletters:
        print(f"🚀 All newsletters were freshly processed")
    elif skipped_newsletters and not processed_newsletters:
        print(f"♻️  All newsletters were loaded from existing files")
    else:
        print(f"🔄 Resume functionality used - some newsletters skipped, others processed")


if __name__ == '__main__':
    main() 