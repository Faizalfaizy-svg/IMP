#!/bin/bash
# =====================================================================
#  setup.sh  -  run ONCE on the Raspberry Pi 5:   bash setup.sh
#  Installs the libraries and turns on I2C, SPI and the serial port.
# =====================================================================
set -e

echo "== Installing libraries =="
sudo apt update
sudo apt install -y python3-lgpio python3-flask python3-serial python3-spidev \
                    python3-opencv python3-numpy python3-picamera2 imx500-all
pip3 install --break-system-packages smbus2 pynmea2

echo "== Turning on I2C, SPI and UART (serial login shell OFF) =="
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_serial_cons 1
sudo raspi-config nonint do_serial_hw 0

echo "== Allow full USB power (for the RPLIDAR) =="
# The Pi is powered from the HW-688 (5V 5A) through a USB-A -> USB-C cable.
# That buck cannot "talk" USB-PD, so the Pi assumes a weak supply and limits
# USB to 600 mA. The HW-688 can give 5A, so this removes that limit.
CFG=/boot/firmware/config.txt
grep -q "^usb_max_current_enable=1" "$CFG" || echo "usb_max_current_enable=1" | sudo tee -a "$CFG"

echo "== Adding user to hardware groups =="
sudo usermod -aG gpio,i2c,spi,dialout,video "$USER"

echo ""
echo "Done. Now restart the Pi:   sudo reboot"
