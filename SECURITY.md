# Security

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security-sensitive reports (exposed credentials, RCE, data leaks, etc.).

1. Email or message the repository maintainers privately with:
   - A short description of the issue and affected component
   - Steps to reproduce (if safe to share)
   - Any suggested fix or mitigation you have in mind

2. If you accidentally committed secrets, **revoke and rotate** those credentials at the provider (Twilio, Sarvam, etc.) immediately, then remove them from history if they were pushed (consider GitHub support or `git filter-repo` for published repos).

## Project-specific notes

- Real credentials belong only in `secrets/.env` (gitignored). Use `secrets/.env.example` as a template.
- Webhooks and media streams assume a **trusted** deployment path; expose `PUBLIC_BASE_URL` only over HTTPS in production.
