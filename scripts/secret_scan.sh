#!/bin/bash
# Scan the full git history for anything that looks like an API key, and the
# tracked file list for secret-ish filenames. Prints findings or ALL_CLEAR.
cd "$(dirname "$0")/.."
found=0
if git log --all -p | grep -nE 'AIza[0-9A-Za-z_-]{20,}|hf_[A-Za-z0-9]{20,}|gsk_[A-Za-z0-9]{20,}|sk-or-[A-Za-z0-9_-]{20,}' | head -20 | grep .; then
    found=1
fi
if git ls-files | grep -iE '(^|/)\.env$|secret|credential' | grep .; then
    found=1
fi
if [ "$found" = 0 ]; then
    echo ALL_CLEAR
fi
