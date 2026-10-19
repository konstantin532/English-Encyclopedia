# A1 audio: evidence-driven human listening gate

Date: 2026-10-19. This complements the previous audio archive and playback-timing work.

## Proven findings

**AUD-01 — No reproducible reviewed release.** The manual speech-build
workflow generates 33 Kokoro bundles (5 stories, 14 week dialogues,
14 tongue-twisters), each at 3 tempos, plus a CSV with **99 SHA-256
track hashes**. Before this change there was no command to validate
the completed human worksheet and produce a reviewed manifest.
A Boolean value in the manifest had no traceable connection to the
exact audio bytes a reviewer heard.

**AUD-02 — Unsupported verified flag.** Any manually edited manifest
could have its verified property set to true; the player would then
describe that audio as checked by a human without checking evidence.
Now a true flag needs a human_review record with a named reviewer,
review date and four rubric decisions for each of three tempos.

**AUD-03 — Approval invalidated by edited tracks.** We bind the
review record to each track's SHA-256 and re-check on audit. Replacing
one track after review invalidates its previous attestation.

**AUD-04 — Accidental early release.** The initial GitHub Actions ZIP
must remain unreviewed to enable listening. Final ZIP packaging now
offers an opt-in require-reviewed gate rejecting all unapproved audio.

## Manual acceptance procedure

1. Run GitHub Actions: Build real A1 speech for manual review.
2. Download matching static/audio content and audio-human-review.csv.
   This output is NOT yet confirmed to sound natural.
3. Personally listen to all 99 referenced files. Record reviewer,
   YYYY-MM-DD, American vowels, word stress, pauses/intonation and
   names/numbers as pass only for acceptable tracks. Enter
   manual_approved=yes only after each track was heard and accepted.
4. From the project root run:

       uv run python -m scripts.approve_audio_review --sheet audio-human-review.csv --dry-run
       uv run python -m scripts.approve_audio_review --sheet audio-human-review.csv
       uv run python scripts/audio_readiness.py --strict --require-reviewed
       uv run python -m scripts.package_audio_archive --require-reviewed --output a1-reviewed-audio.zip
       sha256sum a1-reviewed-audio.zip

5. Publish only the reviewed ZIP at a stable HTTPS location and
   pin the new SHA256 in Render. The old synthesis ZIP is unreviewed.

The gate checks all 33 bundles and 99 unique pairs of
(bundle, tempo). The CSV must match the exact paths and SHA256
from the generated worksheet. Every review criterion must be
pass; the named reviewer and date must be consistent for the
three tempos of each bundle. Invalid input rejects the complete
sheet BEFORE modifying any manifest. Individual manifest writes
use atomic replacement.

## Trust boundaries

- A recorded human review does not prove the reviewer actually
  listened, cannot independently certify a native-like accent,
  and is not a cryptographically authenticated signature.
- Test fixtures verify integrity and gate logic; they do not
  prove acoustic excellence.
- The automatic Kokoro workflow continues to generate unreviewed
  files, and the application continues to label those honestly.
- Human Android/TalkBack tests, Render publication, independent
  pronunciation assessment and the 457 pending / 41 partial
  CEFR evidence items remain outside automated validation.
- Do not claim 9.5/10 without user/device studies and independent
  audio and linguistic review.
