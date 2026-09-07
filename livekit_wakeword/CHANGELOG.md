# Changelog

## 1.2.0

- Bundle `hey_aurora`, a wake word model trained specifically for this
  add-on with livekit-wakeword's conv_attention architecture (medium
  size, 20k steps, CPU-trained). AUT=0.0059 on 17.5 hours of held-out
  validation audio. Trained without the ACAV100M general-negative-speech
  dataset (disk constrained), so it needs `threshold: 0.9` rather than
  the default `0.5` to keep false positives low (FPPH 0.11 at that
  threshold, vs. 4.57 at 0.5). See the README for details.

## 1.1.0

- Bundle 8 additional wake word models: `nihao_livekit` (livekit-wakeword)
  and 7 `hey_buddy`/`stop_buddy`/`go_buddy` variants (English and German)
  from LAION's Bud-E wake word models, all Apache-2.0 and trained natively
  with livekit-wakeword's `conv_attention` architecture.
- Verified openWakeWord's own pretrained `.onnx` classifiers are not
  usable through this add-on's live detection pipeline (poor detection
  scores in testing, and shape mismatches for the `timer`/`weather`
  models), so none are bundled.

## 1.0.0

- Initial release of the LiveKit WakeWord add-on, wrapping
  [livekit-wakeword](https://github.com/livekit/livekit-wakeword) behind a
  Wyoming protocol server.
