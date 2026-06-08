import time
import math
import subprocess
import os
import shutil
import socket
import gpiod
from ssd1306_spi import SSD1306_SPI

# --- KONFIGURACE ---
PIN_BTN = 26
PIN_LED = 21
PERIOD_OK = 1.5
PERIOD_ERROR = 0.2
CHECK_INTERVAL = 10
SCREEN_DURATION = 3
TOTAL_CYCLE = 9

NAS_DISKS = ["/mnt/disk1", "/mnt/disk2", "/mnt/disk3", "/mnt/disk4", "/mnt/disk5"]

# Inicializace hardwaru
oled = SSD1306_SPI(spi_bus=0, spi_device=0, pin_dc=24, pin_rst=25)

chip = gpiod.Chip('gpiochip4')
line_btn = chip.get_line(PIN_BTN)
line_led = chip.get_line(PIN_LED)

line_btn.request(consumer="NAS_BTN", flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP, type=gpiod.LINE_REQ_DIR_IN)
line_led.request(consumer="NAS_LED", type=gpiod.LINE_REQ_DIR_OUT)

# Stavové proměnné
last_check = 0
system_error_msg = None
error_acknowledged = False
button_press_time = 0
last_second = 0

# --- POMOCNÉ SYSTÉMOVÉ FUNKCE ---
def check_system_health():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
            if temp > 75.0: return False, f"CPU TEMP: {temp:.0f}C"
    except: pass
    try:
        total, used, free = shutil.disk_usage("/")
        if (used / total) > 0.95: return False, f"SYS DISK FULL: {(used/total)*100:.0f}%"
    except: pass
    try:
        subprocess.check_output(["ping", "-c", "1", "-W", "1", "8.8.8.8"])
    except: return False, "NO INTERNET"
    return True, None

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        return s.getsockname()[0]
    except: return '127.0.0.1'
    finally: s.close()

def get_cpu_usage():
    try:
        cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'"
        return f"{float(subprocess.check_output(cmd, shell=True)):.0f}%"
    except: return "N/A"

def get_ram_usage():
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total = int(lines[0].split()[1])
        free = int(lines[1].split()[1])
        return f"{((total - free) / total) * 100:.0f}%"
    except: return "N/A"

def get_disk_usage_pct_raw(path):
    try:
        if not os.path.exists(path): return 0.0
        total, used, free = shutil.disk_usage(path)
        return used / total
    except: return 0.0

def render_screens(error_msg):
    oled.clear()

    if error_msg and not error_acknowledged:
        oled.draw_text(0, 0, "!! SYSTEM CHYBA !!")
        oled.draw_text(0, 2, error_msg)
        oled.draw_text(0, 4, "------------------")
        oled.draw_text(0, 6, "[STISKNI PRO RESET]")
        oled.flush()
        return

    screen_index = (int(time.time()) % TOTAL_CYCLE) // SCREEN_DURATION

    if screen_index == 0:
        oled.draw_text(0, 0, "NAS OVERVIEW [1/3]")
        oled.draw_text(0, 2, f"IP: {get_ip_address()}")
        oled.draw_text(0, 4, f"CAS: {time.strftime('%H:%M:%S')}")
        total, used, free = shutil.disk_usage("/")
        oled.draw_text(0, 6, f"SYS DISK: {(used/total)*100:.0f}%")

    elif screen_index == 1:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
        oled.draw_text(0, 0, "SYS STATUS   [2/3]")
        oled.draw_text(0, 2, f"CPU LOAD: {get_cpu_usage()}")
        oled.draw_text(0, 4, f"CPU TEMP: {temp:.1f}C")
        oled.draw_text(0, 6, f"RAM USED: {get_ram_usage()}")

    elif screen_index == 2:
        oled.draw_text(0, 0, "STORAGE      [3/3]")
        for i, path in enumerate(NAS_DISKS):
            pct = get_disk_usage_pct_raw(path)
            row = 3 + i
            oled.draw_text(0, row, f"D{i+1}:")
            oled.draw_horizontal_bar(28, row, 95, pct)

    if error_msg and error_acknowledged:
        oled.draw_text(0, 7, f"*ERR: {error_msg[:12]}")

    oled.flush()

# --- HLAVNÍ SMYČKA ---
try:
    while True:
        now = time.time()
        current_second = int(now)

        # 1. Tlačítko
        if line_btn.get_value() == 0:
            if button_press_time == 0:
                button_press_time = now
            if now - button_press_time > 3.0:
                oled.clear()
                oled.draw_text(0, 3, "VYPINAM SYSTEM...")
                oled.flush()
                line_led.set_value(1)
                time.sleep(2)
                os.system("sudo shutdown -h now")
        else:
            if button_press_time > 0:
                if (now - button_press_time) < 2.0 and system_error_msg:
                    error_acknowledged = True
                button_press_time = 0

        # 2. Kontrola chyb
        if now - last_check > CHECK_INTERVAL:
            is_ok, current_error = check_system_health()
            if is_ok:
                system_error_msg = None
                error_acknowledged = False
            else:
                if current_error != system_error_msg:
                    system_error_msg = current_error
                    error_acknowledged = False
            last_check = now

        # 3. Displej
        if current_second != last_second or (system_error_msg and not error_acknowledged):
            render_screens(system_error_msg)
            last_second = current_second

        # 4. LED dioda (NTP synchronizované pulzování)
        if system_error_msg and not error_acknowledged:
            line_led.set_value(1 if (int(now / PERIOD_ERROR) % 2) == 0 else 0)
            time.sleep(0.05)
        else:
            duty_cycle = (math.sin((now * 2 * math.pi) / PERIOD_OK) + 1) / 2
            if (now % 0.016) < (0.016 * duty_cycle):
                line_led.set_value(1)
            else:
                line_led.set_value(0)
            time.sleep(0.002)

except KeyboardInterrupt:
    oled.clear()
    oled.flush()
    line_led.set_value(0)
