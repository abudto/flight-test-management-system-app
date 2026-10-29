# FTMS — Codex Development Instructions

## Project
Flight Test Management System (FTMS) is a professional Django-based engineering application for managing aircraft flight test activities.

The project is publicly hosted on GitHub as an engineering portfolio.

## Development Principles
- Preserve existing working functionality.
- Prefer incremental development over large rewrites.
- Retain the modular Django monolith architecture.
- Follow Django conventions and maintain clear database relationships.
- Prioritize data integrity, engineering traceability, security, and maintainability.
- Use synthetic data for demonstrations and tests.
- Explain important architecture decisions and tradeoffs.

## Implementation Workflow
1. Inspect relevant existing code before making changes.
2. Explain the proposed implementation.
3. Identify affected models, views, templates, and migrations.
4. Implement the approved scope.
5. Add or update automated tests.
6. Run relevant checks and report results.
7. Summarize modified files, limitations, and recommended manual verification.

## Git and GitHub Rules
- NEVER run `git add`.
- NEVER run `git commit`.
- NEVER run `git push`.
- NEVER merge branches.
- NEVER create or modify GitHub Issues or pull requests.
- NEVER change repository visibility.
- The project owner performs all Git commits, pushes, and GitHub management.
- Read-only Git commands such as `git status` and `git diff` are permitted.
- Do not create or switch branches without explicit approval.

## Database Safety
- Do not delete existing databases.
- Do not reset migrations or remove migration history.
- Explain schema changes before implementing them.
- Use test databases for automated tests.
- Do not modify real engineering data.

## Engineering Requirements
- Preserve program-level data integrity.
- Design for controlled document revisions and traceability.
- Distinguish planned conditions from actual flight test results.
- Ensure exports contain engineering units, tolerances, criteria, and revision information where applicable.
- Do not claim regulatory compliance without supporting evidence.

## Communication
The project owner is experienced in Python and flight test engineering but is learning Django and web development.

Explain significant Django concepts and architectural changes clearly.