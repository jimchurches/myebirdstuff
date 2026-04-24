# Code Review

**When to use:** Before opening or updating a PR, or before committing a **larger** change (multi-file / behaviour change). For tiny edits, a full pass is usually overkill.

## Overview

Perform a thorough code review that verifies functionality, maintainability, and
security before approving a change. Focus on architecture, readability,
performance implications, and provide actionable suggestions for improvement.

For **myebirdstuff**, skim `docs/AI_CONTEXT.md` for repo guardrails (Streamlit vs core, caching, dataframe usage) and call out anything that conflicts.

The AI_CONTEXT.md document gives more context including the following mindset statement:

> Write Python the way a highly regarded engineer who loves teaching would want it written:
> neat, easy to read, efficient where it matters, and easy to follow.


## Steps

0. **Establish the baseline (PR or large local change)**
    - Use the PR diff, or `git diff` / `git log` against the intended merge target (e.g. `beta-next` or `main`) so the review is about the **whole** change, not only the last edit
    - If the change touches Python meaningfully, run `python3 -m ruff check explorer/` and `python3 -m pytest tests/ -q` (or a narrower path) when feasible; fold failures into the review
1. **Understand the change**
    - Read the PR description and related issues for context
    - Identify the scope of files and features impacted
    - Note any assumptions or questions to clarify with the author
2. **Validate functionality**
    - Confirm the code delivers the intended behavior
    - Exercise edge cases or guard conditions mentally or by running locally
    - Check error handling paths and logging for clarity
3. **Assess quality**
    - Ensure functions are focused, names are descriptive, and code is readable
    - Watch for duplication, dead code, or missing tests
    - Verify documentation and comments reflect the latest changes
4. **Review security and risk**
    - Look for injection points, insecure defaults, or missing validation
    - Confirm secrets or credentials are not exposed
    - Evaluate performance or scalability impacts of the change
5. **Identify in-scope TODO and other unfinished work**
    - Look for unfinished work (`TODO`, `FIXME`, commented-out code paths, missing tests for new behaviour)
    - **Review-first:** default to listing gaps and suggested follow-ups; only apply trivial fixes in-repo if the author clearly wants that in the same session
    - If the unfinished work is not minor or is deliberately left for later, ask how to proceed and suggest a GitHub issue so it is not lost

## Review Checklist

### Functionality

- [ ] Intended behavior works and matches requirements
- [ ] Edge cases handled gracefully
- [ ] Error handling is appropriate and informative

### Code Quality

- [ ] Code structure is clear and maintainable
- [ ] No unnecessary duplication or dead code
- [ ] Tests/documentation updated as needed
- [ ] Change size matches the request (no unrelated drive-by edits)

### Security & Safety

- [ ] No obvious security vulnerabilities introduced
- [ ] Inputs validated and outputs sanitized
- [ ] Sensitive data handled correctly

## Additional Review Notes

- Architecture and design decisions considered
- Performance bottlenecks or regressions assessed
- Coding standards and best practices followed
- Resource management, error handling, and logging reviewed
- Suggested alternatives, additional test cases, or documentation updates captured
- **PR hygiene:** commit message / issue linkage, migration or config notes for other contributors, anything that should live in the PR description rather than only in chat

## Subtractions (what this command is not)

- Not a substitute for CI or human reviewers when policy requires them
- Not an instruction to rewrite large areas unless the review explicitly recommends it and the author agrees

Provide constructive feedback with concrete examples and actionable guidance for
the author.