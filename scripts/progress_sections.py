#!/usr/bin/env python3
"""
progress_sections.py - the hub's own session-start read of project_progress.md: runs
resume_digest.py against this hub's outer root, so the hub and every connected project read their
progress file through the same capped, fixed-order digest (Current Status, Next Up, Decisions,
newest Work Log entry, with absent sections stated and every truncation marked).

Usage: python progress_sections.py [--max-lines N] [--max-chars N]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resume_digest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if __name__ == '__main__':
    sys.argv = [sys.argv[0], '--project-root', str(PROJECT_ROOT)] + sys.argv[1:]
    resume_digest.main()
