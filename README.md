# rpi_status_display
Status OLED display 0,96" SPI pro Raspberry Pi 5

# Raspberry Pi 5 Synced Status OLED & Safe Shutdown

Minimalistický Python ovladač a skript pro monitorování stavu zařízení (vhodné pro NAS) na bázi Raspberry Pi 5. Komunikuje s OLED displejem SSD1306/SSD1315 přes rozhraní SPI bez nutnosti instalovat velké knihovny jako `luma.oled` nebo `Pillow`.

## Hlavní vlastnosti
- **Zero Dependencies:** Využívá pouze vestavěné standardní linuxové knihovny systému (`spidev` a `gpiod`).
- **Časová synchronizace (NTP):** Pokud provozujete více zařízení vedle sebe, přepínání obrazovek i pulzování LED diod běží na všech strojích v naprosto identický moment.
- **Detekce chyb:** Sleduje teplotu, síť a kapacitu disku. V případě chyby začne LED rychle blikat a displej ukáže problém.
- **Multifunkční tlačítko:** Krátký stisk potvrdí/umlčí hlášení chyby. Dlouhý stisk (3s) provede bezpečné softwarové vypnutí systému pro ochranu integrity SD karty/SSD.
- **Grafické indikátory:** Zobrazení zaplnění pro 5 datových disků formou vodorovných grafických progress barů.

## Schéma zapojení (RPi 5 Header)
| OLED Pin | Funkce | RPi Pin | GPIO |
| :--- | :--- | :--- | :--- |
| **VCC** | Napájení 3.3V | Pin 1 | 3.3V |
| **GND** | Zem | Pin 6 | GND |
| **D0 (CLK)**| SPI Hodiny | Pin 23 | GPIO 11 (SPI0_SCLK) |
| **D1 (MOSI)**| SPI Data | Pin 19 | GPIO 10 (SPI0_MOSI) |
| **RES** | Reset | Pin 22 | GPIO 25 |
| **DC** | Data / Command| Pin 18 | GPIO 24 |
| **CS** | Chip Select | Pin 24 | GPIO 8 (SPI0_CE0) |

*Tlačítko s LED zapojte na GPIO 26 (Pin 37) proti GND (Pin 39). Anodu LED zapojte přes odpor na GPIO 21 (Pin 40).*

## Použití
1. Povolte SPI rozhraní v systému (`sudo raspi-config` -> Interface Options -> SPI).
2. Spusťte hlavní skript:
   ```bash
   python3 main.py

sudo apt update
sudo apt install -y git python3-spidev python3-gpiod
git clone https://github.com/studenak/rpi_status_display.git ~/nas-monitor
cd ~/nas-monitor
sudo raspi-config
-
sudo bash -c 'cat <<EOF > /etc/systemd/system/nas-monitor.service
[Unit]
Description=NAS Monitor OLED and LED Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/petr/nas-monitor/main.py
WorkingDirectory=/home/petr/nas-monitor
StandardOutput=inherit
StandardError=inherit
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF'
-
sudo systemctl daemon-reload
sudo systemctl enable nas-monitor.service
sudo systemctl start nas-monitor.service
