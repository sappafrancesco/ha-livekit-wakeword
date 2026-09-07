# Home Assistant Add-on: LiveKit WakeWord

## Installation

1. In Home Assistant, go to **Settings** > **Add-ons** > **Add-on store**.
2. Find the "LiveKit WakeWord" add-on and click it.
3. Click on the "INSTALL" button.

## How to use

After this add-on is installed and running, it will be automatically
discovered by the Wyoming integration in Home Assistant. To finish the
setup, go to **Settings** > **Devices & Services** and the discovered
"Wyoming Protocol" integration should appear, or add it manually.

## Configuration

### Option: `threshold`

Activation threshold (0-1), where higher means fewer activations. See
trigger level for the relationship between activations and wake word
detections.

### Option: `trigger_level`

Number of activations before a detection is registered. A higher trigger
level means fewer detections.

### Option: `debug_logging`

Enable debug logging. Useful for seeing satellite connections and each wake
word detection in the logs.

## Custom Wake Word Models

The add-on automatically loads custom wake word models (`.onnx`) from the
`/share/livekit_wakeword` directory. [Install the Samba add-on](https://www.home-assistant.io/common-tasks/supervised/#installing-and-using-the-samba-add-on)
to copy model files there.

After adding new models, reload the Wyoming integration for LiveKit
WakeWord so the new wake words become selectable in the Voice Assistants
settings page.

Models must be exported to `.onnx` and use the same mel-spectrogram +
speech-embedding front-end as openWakeWord/livekit-wakeword. Plain
openWakeWord `.tflite` files are **not** compatible, only `.onnx` classifier
exports are. See the [main README](../README.md#getting-onnx-models) for
where to get or train them.

## Support

Got questions? Open an issue on the repository's GitHub issue tracker.
