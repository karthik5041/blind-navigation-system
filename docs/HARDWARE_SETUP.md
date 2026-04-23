# Hardware Setup Guide

## Bill of Materials

| Component | Model | Purpose |
|---|---|---|
| SBC | Raspberry Pi 4 (4GB) | Main compute unit |
| Camera | Pi Camera Module v2 | Frame capture |
| Proximity | HC-SR04 Ultrasonic Sensor | Obstacle detection |
| Audio | 3.5mm earpiece / USB speaker | Audio feedback |
| Power | 5V 3A USB-C supply | Stable power |
| Storage | 32GB+ Class 10 microSD | OS + application |
| Enclosure | 3D printed wearable housing | Wearable form factor |

## Wiring Diagram

```
Raspberry Pi 4 GPIO Header
                                    
  3.3V  [1] [2]  5V
  SDA   [3] [4]  5V
  SCL   [5] [6]  GND ──────────────── HC-SR04 GND
        [7] [8]  
  GND   [9] [10] 
        [11][12] 
        [13][14] GND
        [15][16] GPIO23 ─────────────── HC-SR04 TRIG
  3.3V [17][18] GPIO24 ─────────────── HC-SR04 ECHO (via voltage divider)
        ...
        
HC-SR04 VCC → 5V Pin
HC-SR04 ECHO → 1kΩ resistor → GPIO24 → 2kΩ resistor → GND
(Voltage divider: 5V signal → 3.3V safe for GPIO)

Pi Camera → CSI ribbon cable → Camera connector (between USB ports and HDMI)
```

## Voltage Divider for HC-SR04 ECHO

The HC-SR04 outputs 5V on the ECHO pin. The Raspberry Pi GPIO is 3.3V tolerant only.
Use a voltage divider: R1=1kΩ (top), R2=2kΩ (bottom).

```
HC-SR04 ECHO ──[1kΩ]──┬── GPIO24
                       │
                      [2kΩ]
                       │
                      GND
```

## OS Setup

1. Flash **Raspberry Pi OS Lite (64-bit)** using Raspberry Pi Imager
2. Enable SSH and configure Wi-Fi in the imager settings
3. Boot and SSH in: `ssh pi@raspberrypi.local`
4. Run the setup script:
   ```bash
   git clone https://github.com/karthik5041/blind-navigation-system
   cd blind-navigation-system
   sudo ./scripts/setup.sh
   ```

## Camera Verification

```bash
# Test camera is detected
libcamera-hello --timeout 2000

# Or via v4l2
v4l2-ctl --list-devices
```

## AWS IoT Certificate Deployment

After running `terraform apply`, retrieve the device certificate:

```bash
# Certificates are output by Terraform
terraform output -raw device_certificate > /etc/blind-nav/certs/device.pem.crt
terraform output -raw device_private_key > /etc/blind-nav/certs/private.pem.key

# Download Amazon Root CA
curl -o /etc/blind-nav/certs/AmazonRootCA1.pem \
  https://www.amazontrust.com/repository/AmazonRootCA1.pem

chmod 400 /etc/blind-nav/certs/*.pem /etc/blind-nav/certs/*.key
chown blindnav: /etc/blind-nav/certs/*
```
