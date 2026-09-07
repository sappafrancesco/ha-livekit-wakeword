# LiveKit WakeWord: Add-on Home Assistant

Low-latency wake word detection for Home Assistant, based on
[livekit-wakeword](https://github.com/livekit/livekit-wakeword), exposed
via the [Wyoming](https://github.com/rhasspy/wyoming) protocol.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg)](livekit_wakeword/CHANGELOG.md)

## Why this add-on

The official [openWakeWord](https://github.com/home-assistant/addons/tree/master/openwakeword)
add-on uses a flat DNN classification head (flatten + dense layers) on top
of the mel-spectrogram/embedding front-end shared with the openWakeWord
ecosystem. [livekit-wakeword](https://github.com/livekit/livekit-wakeword)
replaces that head with a **conv-attention** classifier (1D convolutions +
multi-head self-attention), keeping the same front-end.

On the "hey livekit" validation set (15,000 positive clips, 45,084 negative
clips, 25 hours of audio), the comparison published in the
[livekit-wakeword README](https://github.com/livekit/livekit-wakeword#results) is:

| Metric               | openWakeWord (DNN) | livekit-wakeword (conv-attention) |
| --------------------- | :-----------------: | :---------------------------------: |
| AUT (lower is better) | 0.0720               | **0.0012**                          |
| False positives/hour  | 8.50                 | **0.08**                            |
| Recall                | 68.6%                | **86.1%**                           |

In short: roughly 60x lower AUT and 100x fewer false positives per hour
than openWakeWord, with higher recall. Full details and DET curves in the
["Why livekit-wakeword"](https://github.com/livekit/livekit-wakeword#why-livekit-wakeword)
section of the upstream repo.

## Compatibility

`.onnx` models exported by livekit-wakeword use the **same front-end**
(mel-spectrogram + Google speech embedding) as openWakeWord, so:

- livekit-wakeword `.onnx` models only work with this add-on (the official
  openWakeWord Wyoming server expects `.tflite` files, not `.onnx`);
- livekit-wakeword can in turn **evaluate** `.onnx` models trained with
  openWakeWord for benchmarking purposes
  (`livekit-wakeword eval config.yaml -m model.onnx`) and can export to a
  `.tflite` format compatible with openWakeWord (`dnn` head only, requires
  the `tflite` extra), see
  [Export & Inference](https://github.com/livekit/livekit-wakeword/blob/main/docs/export-and-inference.md#tflite-export-openwakeword-compatible).

So don't expect to load an existing `.tflite` file directly in this
add-on: it needs to be re-exported/trained as `.onnx` first.

**Important, verified by testing:** even though openWakeWord's own `.onnx`
classifier exports match the `(16, 96)` input shape, we tested running
them live through this add-on's actual detection pipeline (streaming
audio, not a one-shot offline check) and detection quality was poor
(best score 0.37 on a clean "alexa" sample, below the 0.5 default
threshold; other models scored near zero). Their `timer`/`weather`
models are not usable at all here: they expect 34-frame and 22-frame
embedding windows instead of the fixed 16-frame window this add-on uses,
and `timer` is a 7-class intent classifier, not a binary wake word. For
this reason none of openWakeWord's pretrained models are bundled with
this add-on; only models trained natively with livekit-wakeword's
`conv_attention` head are included (see below).

## Installing as a Home Assistant add-on

[![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsappafrancesco%2Fha-livekit-wakeword)

1. Click the badge above, or go to **Settings > Add-ons > Add-on Store >
   menu (three dots) > Repositories** and add:
   `https://github.com/sappafrancesco/ha-livekit-wakeword`
2. Find "LiveKit WakeWord" in the store and install it.
3. Start the add-on: it will be automatically discovered by the Wyoming
   integration.

Configuration details and options: [`livekit_wakeword/DOCS.md`](livekit_wakeword/DOCS.md).

## Standalone install via Docker

For anyone not using Home Assistant OS/Supervisor, the same image can be
built standalone from a generic Debian base image (without s6-overlay,
running the server directly):

```sh
docker build --build-arg BUILD_FROM=debian:bookworm-slim \
  -t wyoming-livekit-wakeword livekit_wakeword

docker run -it -p 10400:10400 \
  -v /path/to/custom/models:/models \
  wyoming-livekit-wakeword \
  python3 -m wyoming_livekit_wakeword \
    --uri tcp://0.0.0.0:10400 \
    --custom-model-dir /models \
    --threshold 0.5 \
    --trigger-level 1
```

10 wake word models ship inside the Python package (see
[Getting .onnx models](#getting-onnx-models)); `hey_livekit` loads by
default. To use a different bundled model, or your own custom ones, pass
the desired names in the Wyoming `detect` message from your client (e.g.
Home Assistant Assist with the Wyoming integration).

## Configuration

| Option          | Type  | Default | Description                                                                    |
| ---------------- | ----- | ------- | -------------------------------------------------------------------------------- |
| `threshold`       | float | `0.5`   | Activation threshold (0-1); higher means fewer activations.                     |
| `trigger_level`   | int   | `1`     | Number of consecutive activations required before a detection is registered.    |
| `debug_logging`   | bool  | `false` | Enable debug logging (satellite connections, every detection).                  |

The same options are exposed as CLI flags (`--threshold`,
`--trigger-level`, `--debug`) in standalone use.

## Getting .onnx models {#getting-onnx-models}

### Bundled models

10 models ship with the add-on, all using the native livekit-wakeword
`conv_attention` architecture (no openWakeWord models are bundled, see
[Compatibility](#compatibility) for why). Select one or more by name in
the Wyoming `detect` message; `hey_livekit` loads by default when no
name is given.

| Name                     | Phrase      | Language | Source                                                                                                  | License    |
| ------------------------- | ----------- | -------- | --------------------------------------------------------------------------------------------------------- | ---------- |
| `hey_livekit`              | Hey LiveKit | en       | [livekit-wakeword examples](https://github.com/livekit/livekit-wakeword/tree/main/examples/resources)      | Apache-2.0 |
| `nihao_livekit`            | Nihao LiveKit | zh     | [livekit-wakeword examples](https://github.com/livekit/livekit-wakeword/tree/main/examples/resources)      | Apache-2.0 |
| `hey_buddy_en_medium`      | Hey Buddy   | en       | [LAION Bud-E wake word models](https://huggingface.co/laion/bud-e_wakeword-models_livekit-wakeword)        | Apache-2.0 |
| `hey_buddy_en_small`       | Hey Buddy   | en       | LAION Bud-E wake word models                                                                                | Apache-2.0 |
| `hey_buddy_en_medium_v2`   | Hey Buddy   | en       | LAION Bud-E wake word models (speed/pitch-robust variant)                                                   | Apache-2.0 |
| `hey_buddy_en_large_v3`    | Hey Buddy   | en       | LAION Bud-E wake word models (adversarial confusable-phrase training)                                       | Apache-2.0 |
| `hey_buddy_de_medium`      | Hey Buddy   | de       | LAION Bud-E wake word models                                                                                | Apache-2.0 |
| `hey_buddy_de_small`       | Hey Buddy   | de       | LAION Bud-E wake word models                                                                                | Apache-2.0 |
| `stop_buddy_en_large_v2`   | Stop Buddy  | en       | LAION Bud-E wake word models (companion command word)                                                       | Apache-2.0 |
| `go_buddy_en_large_v2`     | Go Buddy    | en       | LAION Bud-E wake word models (companion command word)                                                       | Apache-2.0 |

The LAION models were picked from a larger published set based on their
own reported evaluation metrics (AUT, false positives/hour, recall);
see their [model card](https://huggingface.co/laion/bud-e_wakeword-models_livekit-wakeword)
for the full list of sizes/variants and how to train more languages or
phrases with the same toolkit.

Loading multiple models at once (e.g. `hey_buddy_en_medium` +
`stop_buddy_en_large_v2` + `go_buddy_en_large_v2` together) works and was
tested; each active model runs its own classifier pass per audio window,
so CPU usage scales with the number of concurrently active models.

**Custom models:** copy `.onnx` files into `/share/livekit_wakeword`
(via the Samba add-on, or directly on the Home Assistant OS filesystem)
and reload the Wyoming integration: the new wake words will appear in the
Voice Assistants settings page.

**Training your own wake word** with livekit-wakeword:

```sh
pip install livekit-wakeword[train,eval,export]
livekit-wakeword setup --config configs/prod.yaml
livekit-wakeword run configs/prod.yaml   # synthetic data generation, augmentation, training, export to .onnx
```

Minimal config:

```yaml
model_name: hey_robot
target_phrases:
  - "hey robot"
n_samples: 10000
model:
  model_type: conv_attention
  model_size: small
steps: 50000
target_fp_per_hour: 0.2
```

Full guide: [docs/training.md](https://github.com/livekit/livekit-wakeword/blob/main/docs/training.md)
and [docs/export-and-inference.md](https://github.com/livekit/livekit-wakeword/blob/main/docs/export-and-inference.md)
in the livekit-wakeword repo.

## Troubleshooting

**The add-on isn't discovered by Home Assistant.**
Check that the Wyoming integration is installed and that the add-on's
Docker network allows zeroconf/mDNS; alternatively add the integration
manually pointing to `tcp://<host-ip>:10400`.

**Too many false positives / too few detections.**
Raise `threshold` for fewer false positives, raise `trigger_level` to
require more consecutive activations before reporting a detection. See
also the FPPH/Recall metrics in the ["Why this add-on"](#why-this-add-on)
section.

**A custom model doesn't show up.**
Files must have the `.onnx` extension and live in
`/share/livekit_wakeword` (not `/share/openwakeword`, which is reserved
for the official add-on). Reload the Wyoming integration after adding new
files.

**High CPU usage on limited hardware.**
livekit-wakeword's `WakeWordModel.predict()` is stateless: it recomputes
the mel-spectrogram and embeddings over the full 2-second window on every
80ms frame, instead of processing incrementally in streaming fashion like
openWakeWord/tflite does. On very limited hardware (e.g. Raspberry Pi
Zero) this is a known limitation of the upstream library, not of this
add-on.

## Contributing

PRs and issues welcome. Before opening a PR, verify that
`docker build --build-arg BUILD_FROM=debian:bookworm-slim -t test livekit_wakeword`
completes without errors and that the server responds to a Wyoming
`describe` event on `tcp://localhost:10400`.

## License and credits

This repository is distributed under the **Apache-2.0** license (see
[LICENSE](LICENSE)).

It conceptually derives from and builds on:

- [wyoming-openwakeword](https://github.com/rhasspy/wyoming-openwakeword)
  (Apache-2.0), the Wyoming server protocol structure, of which
  `wyoming_livekit_wakeword/handler.py` is a direct adaptation.
- [openWakeWord](https://github.com/dscripka/openWakeWord) (Apache-2.0),
  the original wake word detection project and mel-spectrogram/embedding
  front-end.
- [livekit-wakeword](https://github.com/livekit/livekit-wakeword)
  (Apache-2.0), the inference/training library used by this add-on,
  including the bundled `hey_livekit.onnx` and `nihao_livekit.onnx`
  models.
- [LAION Bud-E wake word models](https://huggingface.co/laion/bud-e_wakeword-models_livekit-wakeword)
  (Apache-2.0), the bundled `hey_buddy`/`stop_buddy`/`go_buddy` models,
  trained with the livekit-wakeword toolkit.

All bundled `.onnx` models are Apache-2.0. See the
[bundled models table](#getting-onnx-models) for per-model sources.
