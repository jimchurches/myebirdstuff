# Hosting Suggestions — Streamlit App

## Purpose

This document captures current thinking on hosting options for the Streamlit version of *Personal eBird Explorer*.

It is not a decision document.  
It is a reference to support future decisions as the app evolves beyond local use and basic sharing.

---

## Current State

The app is currently suitable for:

- Local execution (primary use case)
- Lightweight sharing via Streamlit Community Cloud

Streamlit Community Cloud provides:

- Simple deployment from GitHub
- Free hosting
- No infrastructure management

However, it has important limitations.

---

## Limitations of Streamlit Community Cloud

### 1. Performance

- Cold start delays are common
- Shared infrastructure can feel slow
- Limited CPU and memory

### 2. Stateless Environment

- No persistent local storage
- Config files are not retained between sessions
- Users must re-upload data each time

### 3. Limited Control

- No control over runtime environment beyond Python dependencies
- No background processing
- No custom infrastructure configuration

---

## Key Requirement Shift

Moving beyond Streamlit Cloud is not just a hosting change.

It represents a shift from:

- Stateless demo-style app

to:

- Persistent, user-oriented application

This becomes necessary when users expect:

- Saved configuration (e.g. data file paths)
- Persistent user data
- Faster, more predictable performance

---

## Hosting Options Overview

### Option A — Streamlit Community Cloud (Current)

**Best for:**
- Quick demos
- Sharing with others
- Zero-cost deployment

**Pros:**
- Free
- Simple GitHub integration
- No setup required

**Cons:**
- Slow startup
- No persistence
- Limited resources

---

### Option B — Hugging Face Spaces

**Best for:**
- Slightly more flexible free hosting

**Pros:**
- Supports Streamlit apps
- Free tier available
- Some additional configuration flexibility

**Cons:**
- Still largely stateless
- Performance similar to Streamlit Cloud
- Not a full solution for persistence

---

### Option C — Managed App Platforms (Recommended Next Step)

Examples:
- Railway
- Render
- Heroku

**Best for:**
- Real application hosting with minimal overhead

**Pros:**
- Persistent filesystem (or attachable storage)
- Reduced cold starts
- Predictable performance
- Simple GitHub-based deployment

**Cons:**
- Small monthly cost (~US$5–15)
- Some initial setup required

**Notes:**
- This is the most practical upgrade path
- Provides meaningful improvement without full infrastructure complexity

---

### Option D — VPS / Cloud Infrastructure

Examples:
- AWS EC2
- Google Cloud VM
- Azure VM

**Best for:**
- Full control and custom deployments

**Pros:**
- Complete control over environment
- Persistent storage
- Scalable resources

**Cons:**
- Requires infrastructure management
- Ongoing maintenance (security, updates)
- Higher complexity

**Notes:**
- Docker becomes more valuable in this model
- Suitable if the app evolves into a more serious platform

---

### Option E — Platform-Specific Solutions

Example:
- Snowflake Streamlit

**Best for:**
- Enterprise or data platform integration

**Notes:**
- Likely overkill for current project scope

---

## Recommendation (Current)

### Short Term

- Continue using:
  - Local execution (primary)
  - Streamlit Community Cloud (sharing/demo)

### Medium Term

- Consider moving to:
  - Railway or Render

Trigger conditions:

- Persistent config becomes important
- Performance becomes a user issue
- Sharing expands beyond casual use

### Long Term

- Consider:
  - Docker-based deployment
  - VPS or cloud hosting

Trigger conditions:

- App complexity increases
- Multiple users or environments
- Need for controlled, reproducible deployments

---

## Architectural Considerations

If moving beyond Streamlit Cloud, consider:

### Persistence

- Where config files are stored
- How user data is retained
- Whether per-user or shared state is required

### Data Access

- Local file paths vs uploaded files
- Mounting volumes (Docker/VPS)
- External storage (future option)

### Configuration

- Environment variables vs config files
- Default paths and fallbacks

---

## Key Insight

There is no “free + simple + persistent + fast” option.

Trade-offs are unavoidable:

| Model                  | Cost | Simplicity | Persistence | Performance |
|----------------------|------|-----------|-------------|-------------|
| Streamlit Cloud      | Free | High      | No          | Low         |
| Managed Platforms    | Low  | Medium    | Yes         | Medium–High |
| VPS / Cloud          | Var  | Low       | Yes         | High        |

---

## Future Considerations

- Introduce Docker for consistent deployments
- Add configuration abstraction (to support multiple environments)
- Evaluate simple user persistence models if multi-user use emerges

---

## Status

- Informational only
- No immediate action required
- Revisit when Streamlit limitations become a constraint

---