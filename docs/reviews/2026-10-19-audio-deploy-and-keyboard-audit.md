# Audio distribution and transcript keyboard audit (2026-10-19)

## Scope

This pass reviewed \`deploy/install_audio_archive.py\`,
\`scripts/audio_readiness.py\`, \`static/js/audio-player.js\`, the
transcript template and production Render installation. The previous A1
content/CEFR audit in PR #34 is already merged and unchanged here.

## Two verified implementation faults

1. **Non-transactional release replacement:** the Render installer formerly
   unpacked an archive directly into \`static/audio\` before checking all 33
   Kokoro manifests. An incomplete but correctly checksummed archive could
   overwrite the beginning of an existing working bundle, then fail validation,
   leaving a mixed and damaged release. The new installer first verifies ZIP
   paths and duplicate destinations, unpacks into a same-filesystem temporary
   directory, validates *all* 33 manifests against that isolated staging tree,
   then swaps the audio directory into place. A failed replacement restores
   the old directory. Test fixtures deliberately inject a failed filesystem
   move and assert the original data survives.
2. **Incomplete keyboard semantics for clickable transcript lines:**
   voice playback offered click and Enter for individual lines, but not
   Space activation, which is expected of button-like controls. Interactive
   \`<p>\` elements did not expose a button role. Now JS progressively adds
   \`role="button"\`, \`aria-keyshortcuts="Enter Space"\`, supports both
   keys with default scroll cancellation for Space, and clears previous
   \`is-your-turn\` and \`aria-current\` markers when playback advances.
   A browser-simulation Node test exercises events and DOM state.

3. **Broken playback timeline accepted as real audio:** the readiness gate used
   to check only the declared engine and the file's RIFF/MP3 signature. It
   would approve a manifest missing `timings` or containing inverted, negative,
   out-of-order, non-finite or out-of-duration offsets. The actual transcript
   player indexes `timings` on time updates, so this manifested as a broken
   highlight or a JavaScript exception after publication. Validation now
   requires a nonempty ordered timeline with contiguous line indices for all
   three tempos, a finite positive declared duration, and the same line count
   across speeds. Nine malformed-manifest regressions demonstrate rejection
   using otherwise structurally valid WAV files.

## Verification / acceptance

- \`uv run pytest -q tests/test_audio_archive.py tests/test_audio_distribution.py\`
- \`node --test tests/js/*.test.cjs\`
- \`uv run pytest -q\`
- \`uv run python manage.py check\`
- \`uv run python scripts/audio_readiness.py\`
- GitHub Actions CI and Quality Evolution for the PR head SHA.

The tests assert safe distribution and input semantics, **not** that the
sounds are correctly pronounced or that TalkBack announces everything as
expected on physical Android hardware.

## Still outside automated verification

- True Kokoro American-English speech must be generated using the manually
  dispatched \`.github/workflows/build-a1-audio.yml\` or the supported local
  generator, downloaded, and listened to by a qualified reviewer.
- The build workflow intentionally outputs **unreviewed** speech. Audio
  synthesis, audio presence, checksum verification and verified native-like
  pronunciation are four distinct states.
- Rendering on the user's actual Render deployment requires a 33-bundle
  SHA-256-pinned external archive and the two Render environment variables
  \`A1_AUDIO_ARCHIVE_URL\` and \`A1_AUDIO_ARCHIVE_SHA256\`; this PR does not
  create or set those secrets.
- Accessibility checks on an actual Android + TalkBack, keyboard-only
  desktop, reduced motion, zoom and 390px layouts remain necessary.
- A complete human language review of all 500 senses and 28 teaching scripts
  remains open. 457 pending and 41 partially matched CEFR items are not
  silently promoted to verified.

Because these require physical devices, manual listening or external source
evidence, do not claim a final score of 9.5/10 on the strength of CI alone.
