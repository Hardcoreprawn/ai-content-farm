"""
HTML Feed Generation Functions

Functions for generating HTML pages and XML content that haven't been modularized yet.
RSS, sitemap, and web assets functionality moved to dedicated modules.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urljoin

# Import from same directory (site-generator container)
from rss_generation import generate_rss_feed
from sitemap_generation import generate_sitemap_xml
from web_assets import generate_css_styles, generate_manifest_json, generate_robots_txt

from libs import SecureErrorHandler

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("html-feed-generation")
