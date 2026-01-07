# Contributing Guide

Thanks for contributing to `health_check`.

## Quick start

- Install dependencies:
  - GUI: `cd gui && npm install`
  - Server: `cd server && python -m venv venv && venv\Scripts\pip install -r requirements.txt`
- Run checks before opening a PR:
  - GUI lint: `cd gui && npm run lint`
  - Server tests: `cd server && venv\Scripts\python -m pytest -q`

## Do not commit local artifacts

This repo intentionally ignores local runtime artifacts. Please do **not** commit:

- Logs and captured outputs: `*.log`, `*.out`, `*.err`
- Local Context Engine / Codex state: `.context-engine/`, `.augment-context-state.json`
- One-off local scripts used for debugging (keep them local unless agreed):
  - `server/reset_admin_password.py`
  - `server/test_password.py`

If you already committed an artifact by accident, remove it from tracking and add it to `.gitignore`.

## Secrets and credentials

- Never commit `.env` files, API keys, tokens, passwords, or private keys.
- Default dev credentials in docs are for local testing only; change them for production.

