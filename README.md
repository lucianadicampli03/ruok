# RUOK

A lunchbox robot that rolls up, asks **are you okay?**, and helps with food, medicine, or shelter.

Write code anywhere. **Run it on the HP** — that machine has USB-A for the ESP32. This Mac has no adaptor.

## On the HP (do this)

1. Install [Python 3](https://www.python.org/downloads/) and [Arduino IDE 2](https://www.arduino.cc/en/software).
2. Arduino IDE → Boards Manager → **esp32 by Espressif**. Library Manager → **DHT sensor library** (Adafruit) + **Adafruit Unified Sensor**.
3. Clone this repo, plug the ESP32 into the HP, pick **ESP32 Dev Module** and the `COMx` port.
4. Upload `firmware/ruok_esp32/ruok_esp32.ino`.
5. Open Serial Monitor at **115200**. Wave at the PIR. You should see JSON. Then **close** the Monitor (only one app can use the cable).
6. In PowerShell:

```bat
cd path\to\ruok
pip install -r software\requirements.txt
python software\brain.py
```

If it cannot find the board: `python software\brain.py --port COM4`  
If the board is busy or you just want to hear the voice: `python software\brain.py --demo`

Speakers / laptop volume = the HP. Windows will speak the lines out loud.

## What you should see

- PIR motion → wheels approach (ULN2003 on D12/D14/D18/D19)
- Ultrasonic in talk range (~40–160 cm) → stop → “Hey. Are you okay?…”
- Buttons: Food / Medicine / Shelter / Walk with me
- Touch pad on the robot also picks Food if you cannot reach the laptop
- Rain / humidity → it will not offer to open the box
- Obstacle, too-close ultrasonic, or vibration → stop + beep

## Pins

All on one ESP32. See the comments at the top of `firmware/ruok_esp32/ruok_esp32.ino`.

There is **no lid servo** on this map yet. Open the lunchbox by hand for the demo.

## Later (not Hour 1)

- ElevenLabs instead of Windows voice
- Google ADK agents (Greeter / Pilot / Watch) in `software/agents.py`
- Phone camera + YOLO person-detect, AND-ed with PIR
