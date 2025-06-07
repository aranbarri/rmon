import curses
import psutil
import time
import shutil
import subprocess
import os
import RPi.GPIO as GPIO

SAFE_GPIO = list(range(4, 28))
RESERVED = [2, 3]

GPIO.setmode(GPIO.BCM)
for pin in SAFE_GPIO:
    try:
        GPIO.setup(pin, GPIO.IN)
    except:
        pass

def is_part_of_raspmesh():
    net_ifaces = psutil.net_if_addrs()
    return 'bat0' in net_ifaces

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read()) / 1000
    except:
        return None

def get_cpu_freq():
    try:
        with open("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "r") as f:
            return int(f.read()) // 1000
    except:
        return None

def get_voltage():
    try:
        output = subprocess.check_output(["vcgencmd", "measure_volts"], text=True)
        return output.strip().split("=")[1]
    except:
        return None

def get_i2c_devices():
    try:
        output = subprocess.check_output(['i2cdetect', '-y', '1'], text=True)
        lines = output.strip().split('\n')[1:]
        found = []
        for line in lines:
            parts = line.split()
            found += [addr for addr in parts[1:] if addr != '--']
        return found
    except:
        return ["error"]

def draw_bar_vertical(stdscr, x, y_top, height, percent, color=0):
    bar_height = int((percent / 100.0) * height)
    for i in range(height):
        y = y_top + height - 1 - i
        char = 'X' if i < bar_height else ' '
        stdscr.addstr(y, x, char, curses.color_pair(color))

def draw_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # CPU
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)    # MEM
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # DISK
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # I2C
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)     # GPIO + LOGO
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)   # NET
    curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)    # SYS

    bar_height = 10

    while True:
        stdscr.erase()
        width = shutil.get_terminal_size().columns

        # Logo RMON en rojo
        logo = [
            " ____  __  __  ____  _   _ ",
            "|  _ \\|  \\/  |/ __ \\| \\ | |",
            "| |_) | |\\/| | |  | |  \\| |",
            "|  _ <| |  | | |  | | |\\  |",
            "|_| \\_\\_|  |_|\\____/|_| \\_|",
            "         by AAB"
        ]
        for i, line in enumerate(logo):
            stdscr.addstr(i, 2, line, curses.color_pair(5))

        stdscr.addstr(7, 2, "Raspberry Pi Monitor (press 'q' to quit)")

        headers = ["CPU", "MEM", "DISK", "NET", "SYS", "I2C", "GPIO"]
        col_width = width // len(headers)

        for i, header in enumerate(headers):
            col_start = i * col_width
            stdscr.addstr(9, col_start + 1, header)
            stdscr.vline(9, col_start, '|', 24)

        # CPU
        cpus = psutil.cpu_percent(percpu=True)
        step = 4
        for i, usage in enumerate(cpus):
            x = 1 + i * step
            stdscr.addstr(10, x, f"{int(usage)%100:02d}", curses.color_pair(1))
            draw_bar_vertical(stdscr, x, 11, bar_height, usage, 1)

        # MEM
        mem = psutil.virtual_memory().percent
        stdscr.addstr(10, col_width + 1, f"MEM: {mem:5.1f}%", curses.color_pair(2))
        draw_bar_vertical(stdscr, col_width + 1, 11, bar_height, mem, 2)

        # DISK
        disk = psutil.disk_usage('/')
        stdscr.addstr(10, col_width*2 + 1, f"Used: {disk.used // (1024**3)} GB", curses.color_pair(3))
        stdscr.addstr(11, col_width*2 + 1, f"Free: {disk.free // (1024**3)} GB", curses.color_pair(3))
        stdscr.addstr(12, col_width*2 + 1, f"{disk.percent}% used", curses.color_pair(3))

        # NET
        net = psutil.net_io_counters()
        stdscr.addstr(10, col_width*3 + 1, f"Sent: {net.bytes_sent // (1024**2)} MB", curses.color_pair(6))
        stdscr.addstr(11, col_width*3 + 1, f"Recv: {net.bytes_recv // (1024**2)} MB", curses.color_pair(6))

        # SYS
        temp = get_cpu_temp()
        freq = get_cpu_freq()
        volt = get_voltage()
        raspmesh = is_part_of_raspmesh()
        if temp is not None:
            stdscr.addstr(10, col_width*4 + 1, f"Temp: {temp:.1f} degC", curses.color_pair(7))
        if freq is not None:
            stdscr.addstr(11, col_width*4 + 1, f"Freq: {freq} MHz", curses.color_pair(7))
        if volt is not None:
            stdscr.addstr(12, col_width*4 + 1, f"Volt: {volt}", curses.color_pair(7))
        stdscr.addstr(13, col_width*4 + 1, f"RaspMesh: {'YES' if raspmesh else 'NO'}", curses.color_pair(7))

        # I2C
        devices = get_i2c_devices()
        stdscr.addstr(10, col_width*5 + 1, f"Found: {len(devices)}", curses.color_pair(4))
        if devices and devices[0] != "error":
            for i, addr in enumerate(devices[:5]):
                stdscr.addstr(11 + i, col_width*5 + 1, f"0x{addr}", curses.color_pair(4))
        else:
            stdscr.addstr(11, col_width*5 + 1, "No I2C", curses.color_pair(4))

        # GPIO
        all_pins = SAFE_GPIO + RESERVED
        stdscr.addstr(10, col_width*6 + 1, f"GPIOs: {len(all_pins)}", curses.color_pair(5))
        for i, pin in enumerate(all_pins[:18]):
            if pin in RESERVED:
                status = "N/A"
            else:
                try:
                    val = GPIO.input(pin)
                    status = "ON" if val else "OFF"
                except:
                    status = "RES"
            stdscr.addstr(11 + i, col_width*6 + 1, f"GPIO {pin:>2}: {status}", curses.color_pair(5))

        stdscr.refresh()
        time.sleep(1)

        try:
            if stdscr.getch() == ord('q'):
                break
        except:
            pass

try:
    curses.wrapper(draw_screen)
finally:
    GPIO.cleanup()
