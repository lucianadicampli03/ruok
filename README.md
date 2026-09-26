# RUOK

A lunchbox robot that rolls up, asks **are you okay?**, and helps with food, medicine, or shelter.

Run everything on the **HP** (USB-A). This Mac has no adaptor.

## On the HP

1. Install [Python 3](https://www.python.org/downloads/) and [Arduino IDE 2](https://www.arduino.cc/en/software).
2. Boards Manager → **esp32 by Espressif**. Library Manager → **DHT sensor library** (Adafruit) + **Adafruit Unified Sensor**.
3. `git clone` / `git pull` this repo. Plug in the ESP32. Board = **ESP32 Dev Module**.
4. Upload `firmware/ruok_esp32/ruok_esp32.ino`.
5. Serial Monitor **115200** — wave at PIR, see JSON, then **close** it.
6. PowerShell:

```bat
cd ruok
pip install -r software\requirements.txt
python software\brain.py
```

`--port COM4` if it misses the board. `--demo` to hear voice with no robot.

Optional eyes (phone/webcam taped on the front, DroidCam counts as a camera):

```bat
pip install -r software\requirements-vision.txt
python software\brain.py --vision
python software\brain.py --vision --require-person
```

## Demo beat

PIR (and optional YOLO person) → wheels approach → ultrasonic talk-range → stop → “Are you okay?” → Food / Medicine / Shelter / Walk. Walk opens Google Maps walking directions to a Miami help site. Rain keeps the box closed and pushes shelter.

Agents: **Watch** (safety veto), **Pilot** (wheels), **Greeter** (spoken line + resource).

## Pins

See the top of `firmware/ruok_esp32/ruok_esp32.ino`. No lid servo on the map — open the lunchbox by hand.

## API keys (only if you want the prize path)

The robot **runs with zero keys**. Windows speaks. Places come from `software/resources.json`.

Copy `.env.example` to `.env` next to this README and paste:

| Key | Where to get it | What it does |
| --- | --- | --- |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) | Greeter writes a new sentence from wet/dark/need |
| `ELEVENLABS_API_KEY` | [ElevenLabs](https://elevenlabs.io/app/settings/api-keys) or MLH table | Human voice on the speakers |
| `ELEVENLABS_VOICE_ID` | optional | Defaults to Rachel (`21m00Tcm4TlvDq8ikWAM`) |

No Google Maps key. Directions use a public maps link.

Do not commit `.env`.
