import curses
import psutil
import time
import shutil
import subprocess
import os
import socket
import RPi.GPIO as GPIO

GPIO_LAYOUT = [
    ("3.3V", "5V"),    (2, "5V"),     (3, "GND"),     (4, 14),      ("GND", 15),
    (17, 18),          (27, "GND"),   (22, 23),       ("3.3V", 24), (10, "GND"),
    (9, 25),           (11, 8),       ("GND", 7),     ("ID_SD", "ID_SC"),
    (5, "GND"),        (6, 12),       (13, "GND"),    (19, 16),     (26, "GND"),
    (20, 21),
]

ALL_GPIO_PINS = list(set(pin for pair in GPIO_LAYOUT for pin in pair if isinstance(pin, int)))

GPIO.setmode(GPIO.BCM)
for pin in ALL_GPIO_PINS:
    try:
        GPIO.setup(pin, GPIO.IN)
    except:
        pass

def is_part_of_raspmesh():
    return 'bat0' in psutil.net_if_addrs()

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

def get_uptime():
    return time.time() - psutil.boot_time()

def get_load_avg():
    return os.getloadavg()

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
        char = 'O' if i < bar_height else ' '
        stdscr.addstr(y, x, char, curses.color_pair(color))

def draw_screen(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)

    bar_height = 10
    hostname = socket.gethostname()
    try:
        ip = socket.gethostbyname(hostname)
    except:
        ip = "N/A"

    while True:
        stdscr.erase()
        width = shutil.get_terminal_size().columns

        # Logo
        logo = [
            " ____  __  __  ____  _   _ ",
            "|  _ \\|  \\/  |/ __ \\| \\ | |",
            "| |_) | |\\/| | |  | |  \\| |",
            "|  _ <| |  | | |  | | |\\  |",
            "|_| \\_\\_|  |_|\\____/|_| \\_|"
        ]
        for i, line in enumerate(logo):
            stdscr.addstr(i, 2, line, curses.color_pair(5))

        stdscr.addstr(6, 2, "Raspberry Pi Monitor (press 'q' to quit)", curses.color_pair(6))
        stdscr.addstr(6, width - len(hostname) - 10, f"Host: {hostname}", curses.color_pair(6))

        headers = ["CPU", "MEM", "DISK", "NET", "SYS"]
        col_width = width // len(headers)

        for i, header in enumerate(headers):
            col_start = i * col_width
            stdscr.addstr(8, col_start + 1, header)
            stdscr.vline(8, col_start, '|', 14)

        # CPU
        cpus = psutil.cpu_percent(percpu=True)
        step = 4
        for i, usage in enumerate(cpus):
            x = 1 + i * step
            stdscr.addstr(9, x, f"{int(usage)%100:02d}", curses.color_pair(1))
            draw_bar_vertical(stdscr, x, 10, bar_height, usage, 1)

        # MEM
        mem = psutil.virtual_memory().percent
        stdscr.addstr(9, col_width + 1, f"MEM: {mem:5.1f}%", curses.color_pair(2))
        draw_bar_vertical(stdscr, col_width + 1, 10, bar_height, mem, 2)

        # DISK
        disk = psutil.disk_usage('/')
        stdscr.addstr(9, col_width*2 + 1, f"Used: {disk.used // (1024**3)} GB", curses.color_pair(3))
        stdscr.addstr(10, col_width*2 + 1, f"Free: {disk.free // (1024**3)} GB", curses.color_pair(3))
        stdscr.addstr(11, col_width*2 + 1, f"{disk.percent}% used", curses.color_pair(3))

        # NET
        net = psutil.net_io_counters()
        stdscr.addstr(9, col_width*3 + 1, f"Sent: {net.bytes_sent // (1024**2)} MB", curses.color_pair(6))
        stdscr.addstr(10, col_width*3 + 1, f"Recv: {net.bytes_recv // (1024**2)} MB", curses.color_pair(6))

        # SYS
        temp = get_cpu_temp()
        freq = get_cpu_freq()
        volt = get_voltage()
        raspmesh = is_part_of_raspmesh()
        uptime = get_uptime()
        load1, load5, load15 = get_load_avg()
        processes = len(psutil.pids())

        y_base = 9
        if temp is not None:
            stdscr.addstr(y_base, col_width*4 + 1, f"Temp: {temp:.1f} degC", curses.color_pair(7)); y_base += 1
        if freq is not None:
            stdscr.addstr(y_base, col_width*4 + 1, f"Freq: {freq} MHz", curses.color_pair(7)); y_base += 1
        if volt is not None:
            stdscr.addstr(y_base, col_width*4 + 1, f"Volt: {volt}", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"RaspMesh: {'YES' if raspmesh else 'NO'}", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"Uptime: {int(uptime//3600)}h", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"LoadAvg: {load1:.2f}", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"Processes: {processes}", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"Host: {hostname}", curses.color_pair(7)); y_base += 1
        stdscr.addstr(y_base, col_width*4 + 1, f"IP:   {ip}", curses.color_pair(7))

        # Separator
        stdscr.hline(23, 0, '-', width)

        # I2C Devices
        devices = get_i2c_devices()
        if devices and devices[0] != "error":
            i2c_str = ", ".join([f"0x{addr}" for addr in devices[:8]])
        else:
            i2c_str = "None"
        stdscr.addstr(24, 2, f"I2C Devices Found: {len(devices)} [{i2c_str}]", curses.color_pair(4))

        # GPIO Layout (vertical)
        stdscr.addstr(26, 2, "GPIO Layout (physical pins 1–40)", curses.color_pair(5))
        for i, (left, right) in enumerate(GPIO_LAYOUT):
            pin1 = 1 + i * 2
            pin2 = 2 + i * 2
            line = f"({pin1:2}) "

            if isinstance(left, int):
                try:
                    line += f"{'ON':<6}" if GPIO.input(left) else f"{'OFF':<6}"
                except:
                    line += f"{'N/A':<6}"
            elif isinstance(left, str):
                line += f"{left:<6}"
            else:
                line += " " * 6

            line += f"({pin2:2}) "

            if isinstance(right, int):
                try:
                    line += f"{'ON':<6}" if GPIO.input(right) else f"{'OFF':<6}"
                except:
                    line += f"{'N/A':<6}"
            elif isinstance(right, str):
                line += f"{right:<6}"
            else:
                line += " " * 6

            stdscr.addstr(27 + i, 2, line, curses.color_pair(5))

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
