
````
_____  __  __  ____  _   _
|  _ \|  \/  |/ __ \| \ | |
| |_) | |\/| | |  | |  \| |
|  _ <| |  | | |  | | |\  |
|_| \_\_|  |_|\____/|_| \_|
````
# RMON – Raspberry Pi Terminal Monitor

**RMON** is a terminal-based system monitor for **Raspberry Pi**, inspired by `nmon`, with real-time display of CPU, memory, GPIO states, I2C devices, and more.  


![image](https://github.com/user-attachments/assets/0414577d-755e-48cd-86db-05c4bc1e58a5)

---

##  Features

- `nmon`-style system monitoring in the terminal (via `curses`)
- Per-core CPU usage and memory load shown with vertical bars
- Real-time status of **GPIO** pins (input mode, ON/OFF)
- **I2C** device detection using `i2cdetect`
- **RaspMesh** detection (checks for `bat0` mesh interface)
- System metrics: CPU temperature, frequency, voltage

---

##  Requirements

- Raspberry Pi OS or similar (tested on Pi 3, 4, 5)
- Python 3.x
- Root privileges (`sudo`)
- Packages:
  - `psutil`
  - `RPi.GPIO`
  - `curses` (built-in)
  - `i2cdetect` from `i2c-tools`

---

##  Installation

```bash
sudo apt update
sudo apt install python3-pip i2c-tools
pip3 install psutil RPi.GPIO
```

Clone and run:

```bash
git clone https://github.com/aranbarri/rmon.git
cd rmon
sudo python3 rmon.py
```

> `sudo` is required to access GPIO and I2C.

---

## 🔍 What It Monitors

| Section | Metric                                 |
|--------:|----------------------------------------|
| CPU     | Per-core load with vertical bars       |
| MEM     | RAM usage percentage                   |
| DISK    | Used and free disk space               |
| NET     | Sent/received bytes                    |
| SYS     | CPU temp, frequency, voltage, mesh     |
| I2C     | Devices detected via `i2cdetect`       |
| GPIO    | States of GPIO pins (ON/OFF/N/A/RES)   |

> GPIO pins monitored: BCM 4–27 (excluding 2 and 3, reserved for I2C)

---

## 📝 License

MIT License. Free to use, modify, and share.
