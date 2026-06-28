---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''
---

The following is a guide on how to give developer(s) enough information to find, reproduce and fix a reported bug. Treat this as a guide and not prescriptive; we will understand if not all information is included on a simple bug that is easy to find/explain for example.

Feel free to remove text below that is not required. Clear and concise is better than verbose and cluttered.

## Base branch

`beta-next` | `feat/social-cards` | other (name it)

Default is **`beta-next`** when this section is left unchanged.

## PR target

Usually the same as base branch. For feature-line work (e.g. Social Cards), both are often `feat/social-cards`.

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Environment (please complete the following information):**
- OS: [e.g. macOS, Windows]
- Python version: [e.g. 3.11]
- Browser: [e.g. Chrome, Safari] (if applicable)

## Acceptance criteria

- [ ] Bug no longer reproduces with steps above
- [ ] …

## Test plan

- [ ] e.g. `python3 -m pytest tests/path/to/test_module.py -q`
- [ ] Manual repro verified after fix

**Additional context**
Add any other context about the problem here.
