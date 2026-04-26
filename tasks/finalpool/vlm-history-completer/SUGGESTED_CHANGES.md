# Suggested Task Fix Notes

## What We Plan to Change
- Normalize source URLs for trailing slash, `www`, case, and URL encoding.
- Add a confirmed acceptable source alias for `StableDiffusion 1.5`.

## Why This Change May Be Needed
The same source page can be written with small URL-format differences. Also, `runwayml/stable-diffusion` appears to be a reasonable confirmed source for the Stable Diffusion entry.

## Original Logic and Suggested New Logic
- Original: evaluation checked whether the expected source string appeared in the submitted source field.
- Suggested: evaluation should compare canonicalized HTTPS URLs for harmless formatting differences.
- Original: the Stable Diffusion entry accepted only one repository path.
- Suggested: ground truth can list confirmed aliases explicitly.
