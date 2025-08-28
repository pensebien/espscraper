#!/usr/bin/env python3
"""
Probe ESP media URLs for larger image variants without hitting supplier sites.

Usage:
  python test_esp_large_images.py \
    --input espscraper/data/final_product_details.jsonl \
    --limit 50 \
    --timeout 20

Outputs a table summary and prints best URL per product where found.
"""
import argparse
import json
import os
import sys
import time
from typing import Dict, List, Optional, Tuple

import requests

try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


def build_variants(url: str) -> List[str]:
    """Return possible larger variants for an ESP media URL.

    Known base format example: https://api.asicentral.com/v1/media/332454742
    We'll try common query params seen across CDNs/transformers.
    """
    variants: List[str] = []

    def add_variant(u: str, q: str) -> None:
        if "?" in u:
            variants.append(f"{u}&{q}")
        else:
            variants.append(f"{u}?{q}")

    # Always include original first
    variants.append(url)

    # Common width parameters
    for w in (1200, 1600, 2000, 2400, 3000):
        add_variant(url, f"width={w}")
        add_variant(url, f"w={w}")
        add_variant(url, f"maxWidth={w}")
        add_variant(url, f"wid={w}")
        add_variant(url, f"maxwidth={w}")

    # Quality/format hints
    add_variant(url, "format=jpeg&quality=100")
    add_variant(url, "quality=100")

    # Some CDNs respect height too
    for h in (1200, 2000):
        add_variant(url, f"height={h}")
        add_variant(url, f"h={h}")

    # De-duplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def get_image_metrics(session: requests.Session, url: str, timeout: int) -> Tuple[int, int, int]:
    """Return (width_px, height_px, bytes) for image URL. If PIL unavailable, width/height = 0.
    Returns (0,0,0) on failure.
    """
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code != 200:
            return (0, 0, 0)
        content = resp.content
        size_bytes = len(content)
        if PIL_AVAILABLE:
            try:
                img = Image.open(BytesIO(content))
                return (int(img.width), int(img.height), size_bytes)
            except Exception:
                # Not parsable as image, but we still have bytes
                return (0, 0, size_bytes)
        return (0, 0, size_bytes)
    except Exception:
        return (0, 0, 0)


def is_esp_media_url(url: str) -> bool:
    if not url:
        return False
    return "api.asicentral.com" in url and "/media/" in url


def pick_best(variants_results: List[Tuple[str, Tuple[int, int, int]]]) -> Tuple[str, Tuple[int, int, int]]:
    """Pick the best image by largest area, then by bytes."""
    best_url = ""
    best_metrics = (0, 0, 0)
    best_area = -1
    for u, (w, h, b) in variants_results:
        area = (w or 0) * (h or 0)
        # If we couldn't decode dimensions, fallback on bytes as tie-breaker
        key = (area, b)
        best_key = (best_area, best_metrics[2])
        if key > best_key:
            best_url = u
            best_metrics = (w, h, b)
            best_area = area
    return best_url, best_metrics


def main():
    parser = argparse.ArgumentParser(description="Probe ESP large images")
    parser.add_argument("--input", default="espscraper/data/final_product_details.jsonl")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--supplier-filter", default="", help="Only test products whose supplier matches substring")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",  # avoid brotli surprises
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    })

    if not os.path.exists(args.input):
        print(f"❌ Input not found: {args.input}")
        sys.exit(1)

    tested = 0
    successes = 0
    no_esp_url = 0
    improved = 0

    print("\n🔎 Testing ESP large image availability...\n")
    print("ProductID | Base (WxH / KB) -> Best (WxH / KB) | Best URL")
    print("-" * 120)

    with open(args.input, "r") as f:
        for line in f:
            if args.limit and tested >= args.limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception:
                continue

            # Product identification
            product_id = str(item.get("product_id") or item.get("ProductID") or item.get("id") or "?")
            supplier_name = (item.get("supplier_info", {}) or {}).get("supplier_name") or ""
            if args.supplier_filter and args.supplier_filter.lower() not in str(supplier_name).lower():
                continue

            # Try main image first
            base_url = item.get("image_url") or item.get("ImageURL") or ""
            if not is_esp_media_url(base_url):
                # try other lists
                imgs = []
                for key in ("images", "Images", "VariantImages", "VirtualSampleImages"):
                    v = item.get(key)
                    if isinstance(v, list):
                        for it in v:
                            if isinstance(it, dict):
                                url = it.get("url") or it.get("Url") or it.get("URL")
                            else:
                                url = str(it)
                            if is_esp_media_url(url):
                                imgs.append(url)
                base_url = imgs[0] if imgs else ""

            if not is_esp_media_url(base_url):
                no_esp_url += 1
                continue

            tested += 1

            # Build variants and measure
            variants = build_variants(base_url)
            results: List[Tuple[str, Tuple[int, int, int]]] = []
            for u in variants:
                metrics = get_image_metrics(session, u, args.timeout)
                if metrics[2] > 0:  # some bytes
                    results.append((u, metrics))

            if not results:
                print(f"{product_id} | ❌ No image bytes returned | {base_url}")
                continue

            best_url, (bw, bh, bb) = pick_best(results)
            # Find base metrics explicitly
            base_metrics = next(((w, h, b) for u, (w, h, b) in results if u == base_url), (0, 0, 0))
            bw_kb = round(bb / 1024) if bb else 0
            base_kb = round(base_metrics[2] / 1024) if base_metrics[2] else 0

            improved_flag = (bw * bh) > (base_metrics[0] * base_metrics[1]) and (bw * bh) > 0
            if improved_flag:
                improved += 1

            print(
                f"{product_id} | {base_metrics[0]}x{base_metrics[1]} / {base_kb}KB -> "
                f"{bw}x{bh} / {bw_kb}KB | {best_url}"
            )

            if best_url:
                successes += 1

    print("\nSummary:")
    print(f"  Tested products: {tested}")
    print(f"  With ESP URL found: {tested}")
    print(f"  Without ESP URL: {no_esp_url}")
    print(f"  Any image bytes returned: {successes}")
    print(f"  Improved larger variant found: {improved}")


if __name__ == "__main__":
    main()


