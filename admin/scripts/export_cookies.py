#!/usr/bin/env python3
"""
Export YouTube/Google authentication cookies from Firefox to a Netscape cookies file.
Upload the file to S3 via AWS CLI.

Requires: browser-cookie3
"""

import argparse
import os
import subprocess
import sys
import tempfile
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Iterable, Tuple

import browser_cookie3
from browser_cookie3 import BrowserCookieError

ALLOWED_DOMAINS = (
    ".youtube.com",
    ".google.com",
    ".accounts.google.com",
)


def _cookie_key(cookie) -> Tuple:
    return (
        cookie.domain,
        cookie.name,
        cookie.path,
        cookie.secure,
        cookie.expires,
        cookie.port,
        cookie.version,
    )


def _is_allowed_domain(domain: str) -> bool:
    if not domain:
        return False
    domain = domain.lower()
    return any(domain == d or domain.endswith(d) for d in ALLOWED_DOMAINS)


def _load_firefox_cookies() -> Iterable:
    cookies = []
    errors = []

    for domain in ALLOWED_DOMAINS:
        try:
            try:
                jar = browser_cookie3.firefox(
                    domain_name=domain,
                    ignore_discard=True,
                    ignore_expires=True,
                )
            except TypeError:
                # Older browser-cookie3 versions don't support ignore_discard/ignore_expires
                jar = browser_cookie3.firefox(domain_name=domain)
            cookies.extend(jar)
        except BrowserCookieError as exc:
            errors.append(str(exc))
        except Exception as exc:  # pragma: no cover
            errors.append(str(exc))

    if not cookies:
        detail = "; ".join(errors) if errors else "No cookies returned"
        raise RuntimeError(
            "Failed to read Firefox cookies. "
            "Make sure Firefox is installed and a profile with cookies exists. "
            f"Details: {detail}"
        )

    filtered = [c for c in cookies if _is_allowed_domain(c.domain)]
    if not filtered:
        raise RuntimeError("No cookies found for YouTube/Google domains in Firefox.")

    return filtered


def export_cookies(output_path: Path) -> int:
    cookies = _load_firefox_cookies()

    jar = MozillaCookieJar(str(output_path))
    seen = set()
    for cookie in cookies:
        key = _cookie_key(cookie)
        if key in seen:
            continue
        seen.add(key)
        jar.set_cookie(cookie)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    jar.save(ignore_discard=True, ignore_expires=True)
    os.chmod(output_path, 0o600)

    return len(seen)


def upload_to_s3(output_path: Path, s3_uri: str) -> None:
    if not s3_uri.startswith("s3://"):
        raise ValueError("--s3-uri must start with s3://")

    cmd = ["aws", "s3", "cp", str(output_path), s3_uri]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "Unknown error"
        raise RuntimeError(f"AWS CLI upload failed: {stderr}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export YouTube/Google cookies from Firefox to a Netscape cookies.txt file and upload to S3"
    )
    parser.add_argument(
        "--s3-uri",
        required=True,
        help="S3 destination (e.g., s3://bucket/key)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "cookies.txt"
            count = export_cookies(output_path)
            print(f"Exported {count} cookies")

            content = output_path.read_text(encoding="utf-8", errors="replace")
            print("--- BEGIN COOKIES.TXT ---")
            print(content.rstrip())
            print("--- END COOKIES.TXT ---")

            upload_to_s3(output_path, args.s3_uri)
            print(f"Uploaded cookies to {args.s3_uri}")

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

# python admin/scripts/export_cookies.py --s3-uri s3://ml-pipeline-ml-vault/cookies-www-youtube-com
