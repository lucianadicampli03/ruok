# RUOK

A robot that comes to you and asks **are you okay?**  
It helps with **food**, **shelter**, and **emotional support**. Also weather, hazards, and 911 if someone saw a weapon.

Repo: https://github.com/lucianadicampli03/ruok

## Two demos

**Mac (no USB adaptor)** — fake sensors, website talks:

```bash
python3 software/brain.py --demo
```

Open **http://127.0.0.1:8765**

**HP (ESP32 plugged in)** — live board. Close Serial Monitor first.

```bat
cd ruok
git pull
pip install -r software\requirements.txt
python software\brain.py
```

`--port COM4` if it does not find the board.

`--demo` = no robot. Do not use `--demo` on the HP if the board is plugged in.

## What the box does (hardware)

Jay / Luciana’s demo sketch:

| Distance / input | What happens |
| --- | --- |
| over 120 cm | **WAIT** (red) |
| 25–120 cm | **APPROACH** (green, wheels) |
| 25 cm or closer | **STOP** (red) |
| **TOUCH** | **HELP** — stop and stay stopped (green) |

Startup lights: red once, green twice.

The laptop page shows the same states: waiting → approaching → stopped → help.

## What the website does (software)

It says **Hello, I am RUOK. Can I help you?** then waits.

- **Food** — snack in the compartment on top. Open the lid by hand. After ~5 seconds it offers nearby meals.
- **Shelter** — a safe place, or walk with you.
- **Support** — stays with you. Crisis → 988.
- **Hazard / weapon** — get safe, call 911. It does not drive toward danger.

Pills: food, shelter, support, hazard.

Gemini writes most answers from the latest sensors. Food / 911 / 988 stay written by us.

Voice: ElevenLabs Brian if the key works, else the browser / Windows / Mac voice.

## Software on the laptop

| Piece | Job |
| --- | --- |
| `firmware/ruok_esp32/ruok_esp32.ino` | Older JSON + full sensor hub (PIR, rain, DHT, vibe, …) |
| Hardware team sketch | Distance + touch + LEDs (the table above). Prints text, not JSON. |
| `software/brain.py` | Reads serial JSON or `--demo` fake packets |
| `software/agents.py` | Watch (safety), Pilot (wheels), Greeter (talk) |
| `software/gemini.py` | Gemini replies |
| `software/siri/index.html` | Face of the demo |
| `software/resources.json` | Miami food / shelter / 988 / 311 |

Agents: **Watch** can stop the wheels. **Pilot** only moves. **Greeter** talks.

## Optional

```bat
pip install -r software\requirements-vision.txt
python software\brain.py --vision --camera 0
```

Phone camera on the page only. YOLO draws a “person” badge. It does **not** drive the wheels.

## API keys

Copy `.env.example` to `.env` next to this file. Do not commit `.env`.

- `GEMINI_API_KEY` — [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- `GEMINI_MODEL=gemini-flash-lite-latest`
- `ELEVENLABS_API_KEY` — [elevenlabs.io](https://elevenlabs.io/app/settings/api-keys)
- `ELEVENLABS_VOICE_ID` — Brian `nPczCjzI2devNBz1zQrb`

No Maps key. No chat saved.

## Devpost (what to tick)

**Yes:** Best Overall (automatic), Waymo, Microsoft (demo the robot, not only chat), MLH Gemini, MLH ElevenLabs.  
**First-time hacker** only if half the team has never submitted.  
**Skip:** Sperry, Blackstone, State Farm, INIT, Solana, databases, GoDaddy unless you used them.

## Judge script (no hardware)

1. Over 120 cm it waits. 25–120 it approaches. At 25 it stops. Touch = help, stay stopped.
2. *Hello, I am RUOK. Can I help you?*
3. Tap **food** → snack in the lid → wait → nearby places.
4. Tap **shelter**, then **support**.
5. Mac has no USB. Motors/lights are on the HP.
