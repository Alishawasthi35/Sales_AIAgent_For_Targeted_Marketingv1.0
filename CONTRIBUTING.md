# Contributing

Thanks for helping improve this project.

## Setup

1. Python 3.11+ recommended (match your team standard).
2. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Copy `secrets\.env.example` to `secrets\.env` and fill in values for local testing. Never commit `secrets\.env`.

## Git author (optional)

For commits in this repo, set your name and email (use your GitHub noreply address if you prefer not to expose a personal email):

```powershell
git config user.name "Your Name"
git config user.email "you@example.com"
```

Use your real address, or the private no-reply address shown under GitHub **Settings → Emails**.

## Before you open a pull request

- Run the same checks as CI locally (see `.github/workflows/ci.yml`): install deps and `python -m compileall app scripts`.
- Keep changes focused on one concern; match existing style in nearby code.
- Do not add real phone numbers, API keys, or customer data to fixtures or docs.

## Security

See [SECURITY.md](SECURITY.md) for reporting sensitive issues.
