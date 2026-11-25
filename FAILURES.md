# Failures

Format: what broke, what I tried, what fixed it.

## F1: The cache did not notice code changes (25 Nov)
- **Broke:** I fixed the end-card layout and the subtitle size in `assemble.py`, re-ran it, and
  the output looked identical. The output name was a hash of the *inputs* only, so the old video
  was reused.
- **Tried:** deleting `outputs/final` by hand. That works once, but it defeats caching.
- **Fixed:** added `code_version(__file__)` (a hash of the stage's own source) to the cache key for
  `shots.py` and `assemble.py`. Changing the code now rebuilds only that stage's outputs.

## F2: An API key was pasted into a chat (25 Nov)
- **Broke:** while setting up, the Gemini key was pasted into a chat with the coding agent.
- **Fix:** revoke that key in Google AI Studio and create a new one (_status: to confirm_). Keys live
  only in `.env` (git-ignored) or in the environment's secret store, and `.env.example` documents
  the names. The exposed key was never written to any file in this repo.
