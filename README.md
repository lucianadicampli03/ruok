# RUOK

Lunchbox robot that rolls up, asks **are you okay?**, and helps with food, medicine, or shelter.

**Software is done.** The ESP32 JSON is only the sensor feed. Everything else below is what makes a demo.

Repo: https://github.com/lucianadicampli03/ruok

## Besides the JSON — you still need

**Always (demo dies without these)**
- HP plugged into the ESP32 (this Mac has no USB adaptor)
- Firmware uploaded (`firmware/ruok_esp32/ruok_esp32.ino`)
- Serial Monitor **closed**, then `python software\brain.py`
- Laptop/USB **speakers** unmuted (the ESP32 buzzer only beeps)
- Chrome or Edge open to **http://127.0.0.1:8765**

**Hardware the sketch already drives**
- Wheels (ULN2003) — PIR → `approach`, too close → `stop`
- PIR, ultrasonic, obstacle, touch, vibe, rain, DHT11, light, LED, buzzer

**Do by hand**
- Open the lunchbox lid (no servo on the pin map)

**Optional extras**
- Phone camera can sit on the robot as a **screen feed only** (`--vision`). It does not drive wheels or override JSON sensors.
- `.env` keys for Gemini + ElevenLabs (see bottom)

## 60-second judge demo

1. Wave in front of the PIR → it rolls.
2. Stand ~1 m away → it stops and says *are you okay?*
3. Ask on the Siri page: “what’s the humidity?” / “how’s the weather?” → it **talks** and the chips light up from live JSON.
4. Say or tap **food** / **shelter** / **walk** → spoken help + Google Maps.
5. Cover the obstacle or shake the box → stop + “I’ve got you.”
6. If raining/wet → it will not offer to open the box.

Agents: **Watch** (safety), **Pilot** (wheels), **Greeter** (voice + place).

## On the HP

```bat
cd ruok
git pull
pip install -r software\requirements.txt
python software\brain.py
```

`--port COM4` if needed. `--demo` = Siri page with fake JSON (no robot).

```bat
pip install -r software\requirements-vision.txt
python software\brain.py --vision --camera 0
```

`--vision` puts the phone picture on the Siri page (tape it on the box or hold it). YOLO only draws a “person” badge. PIR / ultrasonic / rain still control the robot. Iriun desktop + phone app must show the live picture. `--camera 0` or `1`.

## API keys (optional)

Zero keys still talks (Windows/`say`). Copy `.env.example` to `.env` next to this file:

- `GEMINI_API_KEY` — [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — new sentences
- `ELEVENLABS_API_KEY` — [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys) or MLH — human voice
- `ELEVENLABS_VOICE_ID` — optional

No Maps key. Do not commit `.env`.

## Devpost challenges this fits

Waymo (guide), ElevenLabs, Gemini, Microsoft (not a chat-only app — the box moves), Assurant if you say the session is not saved.
