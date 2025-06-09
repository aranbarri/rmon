import curses
import psutil
import time
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

def get_i2c_matrix():
    try:
        output = subprocess.check_output(['i2cdetect', '-y', '1'], text=True)
        return output.strip().split('\n')
    except:
        return ["Error reading I2C"]

def draw_bar_vertical(stdscr, x, y_top, height, percent, color=0):
    bar_height = int((percent / 100.0) * height)
    for i in range(height):
        y = y_top + height - 1 - i
        char = 'O' if i < bar_height else ' '
        try:
            stdscr.addstr(y, x, char, curses.color_pair(color))
        except curses.error:
            pass

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
        height, width = stdscr.getmaxyx()

        if height < 30 or width < 80:
            try:
                stdscr.clear()
                stdscr.addstr(0, 0, "Terminal is too small...", curses.color_pair(5))
                stdscr.refresh()
            except curses.error:
                pass
            time.sleep(1)
            continue

        logo = [
            " ____  __  __  ____  _   _ ",
            "|  _ \\|  \\/  |/ __ \\| \\ | |",
            "| |_) | |\\/| | |  | |  \\| |",
            "|  _ <| |  | | |  | | |\\  |",
            "|_| \\_\\_|  |_|\\____/|_| \\_|"
        ]
        for i, line in enumerate(logo):
            try:
                stdscr.addstr(i, 2, line, curses.color_pair(5))
            except curses.error:
                pass

        try:
            stdscr.addstr(6, 2, "Raspberry Pi Monitor (press 'q' to quit)", curses.color_pair(6))
            stdscr.addstr(6, width - len(hostname) - 10, f"Host: {hostname}", curses.color_pair(6))
        except curses.error:
            pass

        headers = ["CPU", "MEM", "SYS", "NET", "DISK"]
        col_width = width // len(headers)

        for i, header in enumerate(headers):
            col_start = i * col_width
            try:
                stdscr.addstr(8, col_start + (col_width - len(header)) // 2, header)
                if i > 0:
                    stdscr.vline(9, col_start, '|', 12)
            except curses.error:
                pass

        cpus = psutil.cpu_percent(percpu=True)
        step = 4
        for i, usage in enumerate(cpus):
            x = 1 + i * step
            try:
                stdscr.addstr(9, x, f"{int(usage)%100:02d}", curses.color_pair(1))
            except curses.error:
                pass
            draw_bar_vertical(stdscr, x, 10, bar_height, usage, 1)

        mem = psutil.virtual_memory().percent
        try:
            stdscr.addstr(9, col_width + 1, f"MEM: {mem:5.1f}%", curses.color_pair(2))
        except curses.error:
            pass
        draw_bar_vertical(stdscr, col_width + 2, 10, bar_height, mem, 2)

        temp = get_cpu_temp()
        freq = get_cpu_freq()
        volt = get_voltage()
        raspmesh = is_part_of_raspmesh()
        uptime = get_uptime()
        load1, load5, load15 = get_load_avg()
        processes = len(psutil.pids())

        y_base = 9
        for info in [
            (f"Temp: {temp:.1f} C" if temp is not None else None),
            (f"Freq: {freq} MHz" if freq is not None else None),
            (f"Volt: {volt}" if volt is not None else None),
            f"RaspMesh: {'YES' if raspmesh else 'NO'}",
            f"Uptime: {int(uptime//3600)}h",
            f"LoadAvg: {load1:.2f}",
            f"Processes: {processes}",
            f"IP:   {ip}"
        ]:
            if info:
                try:
                    stdscr.addstr(y_base, col_width*2 + 1, info, curses.color_pair(7))
                except curses.error:
                    pass
                y_base += 1

        net = psutil.net_io_counters()
        try:
            stdscr.addstr(9, col_width*3 + 1, f"Sent: {net.bytes_sent // (1024**2)} MB", curses.color_pair(6))
            stdscr.addstr(10, col_width*3 + 1, f"Recv: {net.bytes_recv // (1024**2)} MB", curses.color_pair(6))
        except curses.error:
            pass

        disk = psutil.disk_usage('/')
        try:
            stdscr.addstr(9, col_width*4 + 1, f"Used: {disk.used // (1024**3)} GB", curses.color_pair(3))
            stdscr.addstr(10, col_width*4 + 1, f"Free: {disk.free // (1024**3)} GB", curses.color_pair(3))
            stdscr.addstr(11, col_width*4 + 1, f"{disk.percent}% used", curses.color_pair(3))
        except curses.error:
            pass

        try:
            stdscr.hline(21, 0, '-', width)
        except curses.error:
            pass

        matrix = get_i2c_matrix()
        try:
            stdscr.addstr(22, 2, "I2C Matrix:", curses.color_pair(4))
        except curses.error:
            pass
        for i, line in enumerate(matrix):
            try:
                stdscr.addstr(23 + i, 4, line, curses.color_pair(4))
            except curses.error:
                pass

        devices = []
        for line in matrix:
            if ':' in line:
                parts = line.split(':', 1)[1].strip().split()
                for val in parts:
                    if val != '--':
                        devices.append(f"0x{val.lower()}")

        det_start_line = 23 + len(matrix) + 1
        box_width = 26
        box_height = len(devices) + 2
        try:
            stdscr.addstr(det_start_line, 2, "+" + "-"*(box_width-2) + "+", curses.color_pair(6))
            stdscr.addstr(det_start_line + 1, 2, "| Devices [I2C]" + " "*(box_width - len(" Devices I2C") - 3), curses.color_pair(6))
            for i, dev in enumerate(devices):
                line = f"| - {dev}" + " "*(box_width - len(dev) - 6)
                stdscr.addstr(det_start_line + 2 + i, 2, line, curses.color_pair(6))
            if not devices:
                stdscr.addstr(det_start_line + 2, 2, "| 0" + " "*(box_width - 10), curses.color_pair(6))
                box_height += 1
            stdscr.addstr(det_start_line + box_height, 2, "+" + "-"*(box_width-2) + "+", curses.color_pair(6))
        except curses.error:
            pass

        start_line = det_start_line + box_height + 1
        try:
            stdscr.addstr(start_line, 2, "GPIO Layout (physical pins 1–40)", curses.color_pair(5))
        except curses.error:
            pass
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
            try:
                stdscr.addstr(start_line + 1 + i, 2, line, curses.color_pair(5))
            except curses.error:
                pass

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
