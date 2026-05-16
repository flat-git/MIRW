# Changelog

## [0.3.1] - 2026-05-16

### Changed
- `npm run dev` now automatically starts the backend (FastAPI) alongside the frontend (Vite) via a Vite plugin, so only one command is needed to launch the full stack.
- Added `start.sh` as an alternative one-click startup script that opens the browser automatically.

## [0.3.0] - 2026-05-16

### Added
- Report download: Excel export, analysis report download, and report history list.
- Dirty data LLM-assisted import (3-step wizard: analyze → map → clean).

### Fixed
- Report download now has proper error handling to prevent 500 errors.
- Download button switched to JS blob download to fix `.md` becoming `.txt` issue.

### Docs
- Updated README to reflect FastAPI+React architecture and dirty data import features.
