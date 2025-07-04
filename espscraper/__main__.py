import logging
import sys
import os
from espscraper.session_manager import SessionManager
from espscraper.scrape_product_details import ProductDetailScraper

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ESP Product Detail Scraper (Production Entry Point)")
    parser.add_argument('--collect-links', action='store_true', help='Run link scraper before detail scraper (uses --limit for number of links)')
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of products to scrape (and links to collect if --collect-links is set)')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--force-relogin', action='store_true')
    parser.add_argument('--output-file', type=str, default=None)
    parser.add_argument('--links-file', type=str, default=None)
    parser.add_argument('--overwrite-output', action='store_true')
    parser.add_argument('--batch-size', type=int, default=None)
    parser.add_argument('--batch-number', type=int, default=None)
    parser.add_argument('--log-file', type=str, default=None)
    parser.add_argument('--clear-session', action='store_true', help='Clear session/cache before running')
    parser.add_argument('--new-only', action='store_true', help='Only collect links for products not already scraped (based on the detail output file)')
    parser.add_argument('--no-aggressive-cleanup', action='store_true', help='Disable aggressive Chrome process cleanup (keeps your browser windows open)')
    args = parser.parse_args()

    # Ensure log directory exists if log-file is specified
    if args.log_file:
        log_dir = 'log'
        os.makedirs(log_dir, exist_ok=True)
        # If only a filename is given, place it in the log folder
        if not os.path.dirname(args.log_file):
            args.log_file = os.path.join(log_dir, args.log_file)

    # Setup logging
    logging.basicConfig(
        filename=args.log_file,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s'
    )
    logger = logging.getLogger()
    if not args.log_file:
        # Also log to stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)

    # Ensure tmp directory exists
    os.makedirs('tmp', exist_ok=True)

    # Optionally clear session/cache
    if args.clear_session:
        for f in ['tmp/session_cookies.json', 'tmp/session_state.json']:
            try:
                os.remove(f)
                logging.info(f"Deleted {f}")
            except FileNotFoundError:
                pass

    try:
        if args.collect_links:
            from espscraper.api_scraper import ApiScraper
            session_manager = SessionManager()
            scraper = ApiScraper(session_manager)
            status = scraper.collect_product_links(force_relogin=args.force_relogin, limit=args.limit, new_only=args.new_only, detail_output_file=args.output_file)
            if status and status.get('all_links_collected'):
                logging.info("All links already collected. Proceeding to detail scraping.")
            elif status:
                logging.info(f"New links collected: {status.get('new_links_collected', 0)}")
        if args.overwrite_output:
            output_file = args.output_file or os.getenv("DETAILS_OUTPUT_FILE", "final_product_details.jsonl")
            open(output_file, 'w').close()  # Truncate the file
            logging.warning(f"Output file '{output_file}' has been cleared.")
        session_manager = SessionManager(
            cookie_file='tmp/session_cookies.json',
            state_file='tmp/session_state.json'
        )
        scraper = ProductDetailScraper(
            session_manager,
            headless=args.headless,
            limit=args.limit,
            output_file=args.output_file,
            links_file=args.links_file,
            aggressive_cleanup=not args.no_aggressive_cleanup
        )
        # Batching logic
        if args.batch_size is not None and args.batch_number is not None:
            all_links = scraper.read_product_links()
            start = args.batch_number * args.batch_size
            end = start + args.batch_size
            batch_links = all_links[start:end]
            def batch_read_links():
                return batch_links
            scraper.read_product_links = batch_read_links
            logging.info(f"Processing batch {args.batch_number} (products {start} to {end-1})")
        scraper.scrape_all_details(force_relogin=args.force_relogin)
    except Exception as e:
        logging.exception("Fatal error in main")
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 