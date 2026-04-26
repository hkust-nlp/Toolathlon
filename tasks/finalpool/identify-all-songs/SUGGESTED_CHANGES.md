# Suggested Task Fix Notes

## What We Plan to Change
- Add a small, curated alternative song list for a confirmed matching video version.
- Recommend that the task eventually pin a URL or video ID.

## Why This Change May Be Needed
Different YouTube uploads can have the same or very similar title but different track lists. A correct answer for one matching upload can fail if the evaluator only accepts a different upload's list.

## Original Logic and Suggested New Logic
- Original: the task gave a YouTube title.
- Suggested: the prompt should ideally name the exact target video.
- Original: evaluation accepted only the static ground-truth song list.
- Suggested: until the video is pinned, evaluation can accept only manually confirmed song lists tied to known matching videos.
