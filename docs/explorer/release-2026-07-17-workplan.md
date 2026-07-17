# Release workplan — `beta-next` → `main` (`2026-07-17`)

**Status:** Paused overnight — resume tomorrow (merge day target).  
**Created:** 2026-07-16 · **Last updated:** 2026-07-16 (interview locked in; version file bumped)  
**Nature:** Temporary planning / TODO doc. Delete or archive after the release ships.

**Headline:** Social Cards tab — **v1.0 / MVP shipped**; further polish via new issues over time.  
**Also first-class in this release:** Interesting Insights (complete for v1.0; more facts later as ideas appear).  
**Known issue in release notes:** [#332](https://github.com/jimchurches/myebirdstuff/issues/332) — preview vs exported cards don’t match (treat as bug; keep open).  
**Keep open (not closed by release PR):** #332, [#342](https://github.com/jimchurches/myebirdstuff/issues/342) (nice-to-have: persist Social Cards prefs in YAML — not a priority yet).

---



## Quick facts


| Item                               | Value                                                                               |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| Working branch                     | `beta-next`                                                                         |
| Approx commits `main`..`beta-next` | ~327 (as of 2026-07-16)                                                             |
| Embedded build version **file**    | `2026-07-17` — **bumped locally; commit + push still needed**                       |
| Release id / Git tag               | `2026-07-17`                                                                        |
| Label for “done, awaiting main”    | `pending-merge`                                                                     |
| Prior release PR                   | [#264](https://github.com/jimchurches/myebirdstuff/pull/264) — `beta-next` → `main` |
| Prior GitHub Release               | [2026-06-01](https://github.com/jimchurches/myebirdstuff/releases/tag/2026-06-01)   |


---



## Decisions (locked 2026-07-16)



### Close / epic policy


| Decision                                     | Answer                                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **#157** (Social Cards epic)                 | **Close** with this release — MVP / feature v1.0 done. Later polish = new bug/enhancement issues. |
| Related `pending-merge` (incl. Social Cards) | **Close all** via release PR `Closes #…` list                                                     |
| **#332**                                     | **Keep open** — known issue / bug; call out in release notes                                      |
| **#342**                                     | **Keep open** — optional enhancement (persist prefs); not bothering yet                           |
| Engineering `pending-merge` issues           | **Close all**; notes = one short headline only (not a laundry list)                               |




### Version & process


| Decision     | Answer                                                                                         |
| ------------ | ---------------------------------------------------------------------------------------------- |
| Merge day    | **2026-07-17**                                                                                 |
| Version bump | **Now** (file already set to `2026-07-17`; commit when resuming)                               |
| Release PR   | **Draft first** (avoid running CI too often); mark ready after notes/close-list/review settled |




### Release notes tone


| Decision              | Answer                                                                                                                                         |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Audience              | End users, biased to **power users / code-aware** readers (not only “what’s new for friends”)                                                  |
| Interesting Insights  | **In this release** — part of Social Cards / Insights v1.0; not deferred                                                                       |
| Engineering           | Simple note, e.g. *various developer- and agent-focused engineering updates* / *improved workflows and project documentation* — headlines only |
| “What’s next” section | **None** — mood-driven; #332 will be fixed or worked around later                                                                              |




### Still open when resuming (optional preferences)

- Review depth (full `/code-review` vs focused Social Cards + GPS + Maintenance)
- Who publishes the GitHub Release (`gh` from here vs GitHub UI)
- Whether Streamlit Cloud deploy check is an explicit post-merge step

---



## Close-list vs keep-open



### Keep open (do **not** put in `Closes`)


| Issue    | Why                                                                    |
| -------- | ---------------------------------------------------------------------- |
| **#332** | Known bug: Social Cards preview/export mismatch — **in release notes** |
| **#342** | Optional enhancement: persist Social Cards prefs in YAML — deferred    |




### Close on merge (`Closes #…`) — all current open `pending-merge` (2026-07-16)

Re-fetch tomorrow in case the list changed; then paste into the PR body.

**Epic / Social Cards / Insights**

- Closes #157 — Social Media Summary Generator (epic; v1.0 done)
- Closes #273 — Share summary foundation
- Closes #274 — Period stats hardening
- Closes #285 — Richer Spotlight Card fact types
- Closes #293 — Audit grid stat min/max
- Closes #294 — Square format circle layouts
- Closes #295 — Single-circle typography
- Closes #298 — QA audit share-summary tests
- Closes #300 — Larger max circle diameter (playground)
- Closes #302 — Circle playground defaults until edited
- Closes #308 — Dark theme Statistics Grid contrast
- Closes #326 — Social Cards port — tab shell and data wiring
- Closes #327 — Social Cards port — card UI and lazy PNG export
- Closes #328 — Social Cards port — hardening and polish
- Closes #334 — Interesting Insights peak period facts
- Closes #344 — Reuse Playwright Chromium across PNG exports
- Closes #345 — Verify Playwright Chromium PNG export on Streamlit Cloud

**GPS / Maintenance / product**

- Closes #272 — GPS naming bug (Coree)
- Closes #357 — Create location name from GPS (Maintenance)
- Closes #355 — Most-frequent parent common helper → species_logic

**Engineering / DX / testing / deps automation**

- Closes #283 — Python style guide + AI guardrails
- Closes #287 — Auto-approve low-risk Dependabot PRs
- Closes #289 — Cursor rules for project context / style
- Closes #290 — Audit legacy tests for integrity
- Closes #299 — PR Nit-Fixer automation
- Closes #310 — Test Integrity Sentinel command migration
- Closes #311 — Cursor project rules implementation
- Closes #312 — Issue workflow commands (base branch + finish-issue-work)
- Closes #339 — Sentinel pinned model update
- Closes #341 — Streamlit defaults.py ownership audit

**Orphan check (tomorrow):** any merged work on `beta-next` missing `pending-merge` that should also get a `Closes #` — add before marking PR ready.

---



## Phase checklist



### Phase 0 — Scope & close-list

- [x] Confirm release id / merge date = **2026-07-17**
- [x] Interview / policy decisions locked (above)
- [x] Draft close-list from open `pending-merge` (above)
- [x] #157 closes; #332 / #342 stay open; #332 in notes
- [ ] Re-fetch `pending-merge` on resume; adjust close-list if needed
- [ ] Quick orphan scan for missing `pending-merge` issues

---



### Phase 1 — Version bump

- [x] Update `explorer/app/streamlit/explorer_build_version.txt` → `2026-07-17`
- [x] Commit on `beta-next` (intentional release prep — confirm message, then `/commit-work` or ask agent)
- [x] Push `beta-next`
- [x] Spot-check related version tests if desired

Suggested commit message:

```text
chore: bump explorer build version to 2026-07-17
```

(Optionally commit the workplan in the same commit or a tiny docs commit — your call tomorrow.)

---



### Phase 2 — Draft release notes

Audience: end users with a power-user / code-aware bias. Social Cards–led; no laundry list of PRs. No “what’s next.”

- [x] **Overview** — user-focused sell of Social Cards (shareable summary images; no “v1.0” framing)
- [x] **Highlights — Social Cards** — periods/geo, layouts (incl. Interesting Insights), stats, PNG export + themes/formats/Cloud
- [x] **Known issue** — preview vs export can differ — #332
- [x] **Also in this release** (short bullets):
  - [x] GPS checklist location-name fix
  - [x] Maintenance: create location name from GPS
  - [x] Streamlit / dependency bumps (if worth a line)
- [x] **Under the hood / engineering** — one short blurb, e.g. improved developer/agent workflows and project documentation (do not enumerate commands/skills)
- [x] **Upgrade notes** — none unless Cloud PNG / self-host note is useful

Scratch draft (ready for PR body / GitHub Release):

```markdown
## Overview

This release adds a new **Social Cards** tab — turn your personal eBird data
into shareable summary images for a year in review, a busy month, a trip, or
your whole birding life so far.

Pick a period and place, choose a layout and theme, tune which stats appear,
then export a PNG sized for a square post, portrait feed, or story.

## Highlights

### Social Cards

- New **Social Cards** tab for building and exporting shareable birding summary
  cards from your eBird export.
- Scope by **Lifetime**, **Year**, **Month**, **Week**, or a **custom date range**
  (with an optional trip-style heading). Narrow further by **country** and
  **region** when you want a local card.
- Four layouts: **Statistics Tiles** (grid or circle cluster), **Statistics
  List**, **Spotlight** (one hero stat), and **Interesting Insights** (fact
  cards such as most-recorded species, biggest single-checklist count, and peak
  year / month / day facts).
- Choose and reorder the stats on the card — species, lifers, checklists,
  birding days, distance, streaks, taxonomy coverage, and more.
- Export a **PNG** in **Square**, **Portrait**, or **Story** size, in **Light**
  or **Dark** theme. One-click export works on Streamlit Community Cloud as well
  as locally.

### Known issue

Preview and exported Social Cards can differ slightly (especially statistics
grid tiles). See #332 — this does not block using the feature; a fix or
workaround will follow separately.

## Also in this release

- GPS checklist location-name bug fix
- Maintenance tab: create a location name from GPS coordinates
- Dependency / Streamlit updates

## Under the hood

Various developer- and agent-focused engineering updates — improved workflows
and project documentation.

## Upgrade notes

No settings migration is required for this release.
```

---



### Phase 3 — Open release PR (**draft**)

- [ ] Version bump committed + `beta-next` pushed
- [ ] Quality gate:  
  `python3 -m ruff check explorer/`  
  `python3 -m pytest tests/ -q`
- [ ] Confirm title + base `main` with human
- [ ] Open **draft** PR: base `main`, head `beta-next` (defer ready until notes/close-list settled)
- [ ] PR body includes full **Closes #…** list from Phase 0
- [ ] Suggested title: `Release 2026-07-17: Social Cards tab and Interesting Insights`
- [ ] When ready: undraft → wait for CI green

**PR URL:** *TBD*

---



### Phase 4 — Deep review

Promotion review (prefer `/code-review`; confirm depth on resume).

- [ ] Agree review depth
- [ ] Run review; stop on blockers
- [ ] Optional smoke: Social Cards + Insights + GPS + Maintenance GPS tool
- [ ] Do not re-litigate every engineering-only PR unless a problem appears

---



### Phase 5 — Merge to `main`

- [ ] Merge release PR (confirm merge-commit vs other; prior releases merged `beta-next`)
- [ ] Confirm listed issues auto-closed
- [ ] Spot-check: **#157 closed**; **#332** and **#342** still open
- [ ] Optional: tidy `pending-merge` on closed issues

---



### Phase 6 — Tag & publish GitHub Release

- [ ] Tag `main` as `2026-07-17` (calver, no `v` prefix)
- [ ] Publish release notes (from Phase 2; `gh release create` or GitHub UI)
- [ ] Sanity: in-app update notice sees newer remote tag vs embedded `2026-07-17`

**Release URL:** *TBD*

---



### Phase 7 — Post-release hygiene

- [ ] Streamlit Cloud / deploy on `main` confirmed (if using Cloud)
- [ ] #332 remains the documented known issue
- [ ] Fast-forward / update `beta-next` from `main`
- [ ] Delete or archive this workplan file

---



## Suggested order when resuming (tomorrow)

1. Re-fetch `pending-merge` + orphan check (Phase 0)
2. **Commit + push** version bump (and optionally this workplan)
3. Polish release notes → open **draft** PR (Phase 2–3)
4. Review → undraft → merge day Phases 4–7

---



## Resume prompt (paste into chat)

```text
We're resuming the beta-next → main release using
docs/explorer/release-2026-07-17-workplan.md

Decisions are locked (close #157 + all pending-merge; keep #332/#342 open;
version file already 2026-07-17). Start by: re-fetch pending-merge, commit/push
the version bump (ask before commit), then draft release notes and a draft PR
to main. Do not undraft or merge until I confirm.
```

---



## Related

- Prior PR body: `gh pr view 264`
- Prior notes: `gh release view 2026-06-01`
- Label meaning: `.cursor/commands/merge-pr.md`
- Version: `explorer/app/streamlit/explorer_build_version.txt` · `explorer_build_version.py`
- Guardrails: `docs/AI_CONTEXT.md`

