# Phone Touchpad

**Control your PC's mouse by drawing directly on your phone.**

Phone Touchpad lets you draw on a live screenshot of your PC screen using your phone's browser. Simply scan a QR code, open the interface, and draw with your finger. When you lift your finger, the entire stroke is sent to your PC and executed as a single continuous mouse operation.

Ideal for drawing applications, digital whiteboards, presentations, screen annotations, and other situations where precise mouse input is useful.

## Download

**[Download EXE here](https://drive.google.com/uc?export=download&id=1g_M5omC-LIHyX44J09H-nMS5AOpYX2M6)**

Download the Windows executable to get started without manually installing Python dependencies.

## Features

- **Browser-based control** — Draw on your PC directly from your phone, with no mobile app required.
- **Live screen preview** — View screenshots of your PC screen on your phone.
- **Efficient stroke transmission** — Sends one request per completed stroke instead of hundreds of individual mouse events.
- **Smooth drawing** — Interpolates short segments and smooths shaky finger movements for more natural lines.
- **Landscape mode** — Rotate the interface for a wider drawing area.
- **Fullscreen mode** — Maximize the available screen space on your phone.
- **Connection indicator** — A white overlay frame with a close button appears on your PC while a phone is connected.
- **Local network operation** — Communication stays on your local network; no external internet connection is required for normal operation.

## How It Works

```text
Phone (Web Browser)
        |
        | Wi-Fi / Local Network
        v
Flask Server on PC
        |
        +-- /screen.jpg
        +-- /api/stroke
        |
        v
PyAutoGUI
        |
        +-- Screen Capture
        +-- Mouse Movement
        +-- Mouse Button Control

Tkinter
        |
        +-- QR Code Window
        +-- Screen Overlay
```

1. The application starts a local web server on port `8765` and displays a QR code.
2. Your phone connects to the web interface and periodically retrieves a screenshot of your PC.
3. You draw directly on the screenshot using your finger.
4. When you lift your finger, the complete stroke is sent to the PC in a single request.
5. The PC converts the stroke into mouse movements, holds the mouse button while drawing, and releases it when the stroke is complete.

## Requirements

- Python 3.9 or newer
- Tkinter
- A phone and PC connected to the same Wi-Fi network
- The required Python packages listed in `requirements.txt`

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/The_Quinn4642/phone-touchpad.git
cd phone-touchpad
python -m pip install -r requirements.txt
```

**Tip:** Use `python -m pip` instead of `pip` to ensure the packages are installed into the same Python environment used to run the application.

## Usage

Start the application:

```bash
python phone_touchpad.py
```

1. Make sure your phone and PC are connected to the **same Wi-Fi network**.
2. Scan the displayed QR code with your phone.
3. Open the link in your phone's browser.
4. Draw directly on the screen preview.

The mobile interface includes the following controls:

- **Refresh** — Manually refresh the screen preview.
- **Rotate** — Switch to landscape orientation.
- **Fullscreen** — Expand the interface to use the available screen space.

To close the application, use the **X button** in the top-left corner of the PC overlay.

## Supported Platforms

| Platform | Support and Notes |
|---|---|
| Windows | Supported. Allow access through Windows Firewall on private networks when prompted. |
| macOS | Requires Accessibility and Screen Recording permissions for the terminal or application. |
| Linux | Supported under X11. Wayland is not supported by PyAutoGUI in this application. |

## Configuration

You can adjust the following settings near the top of `phone_touchpad.py`.

| Setting | Default | Description |
|---|---:|---|
| `PORT` | `8765` | Local web server port. |
| `REFRESH_MS` | `8000` | Automatic screenshot refresh interval in milliseconds. Set to `0` for manual refresh only. |
| `STEP_PX` | `3` | Maximum distance between generated mouse points. Lower values produce smoother, more detailed strokes. |
| `SMOOTH_WINDOW` | `3` | Smoothing window for reducing shaky movements. Set to `1` to disable smoothing. |
| `STEP_DELAY` | `0.002` | Delay between generated mouse points in seconds. Higher values may produce slower drawing. |
| `FRAME_ALPHA` | `0.75` | Opacity of the PC overlay frame. |

## Security

Phone Touchpad is designed for use on a trusted local network. Please keep the following security considerations in mind:

- **Session token:** The access link contains a randomly generated token that changes each time the application starts.
- **Mouse and screen access:** Anyone with a valid session link may be able to view your screen and control your mouse.
- **Unencrypted connection:** Communication uses HTTP rather than HTTPS.
- **Network restrictions:** Do not expose port `8765` directly to the public internet. Keep access restricted to trusted devices and networks.

Only share the QR code or access link with people you trust.

## Building a Windows Executable

You can package the application into a standalone Windows executable using PyInstaller.

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

Build the executable:

```bash
python -m PyInstaller --onefile --noconsole phone_touchpad.py
```

Once the build completes, the executable will be located in the `dist/` directory.

**Note:** Test the packaged executable on your target system. Depending on your environment, additional configuration may be needed to bundle all dependencies correctly.

## Troubleshooting

**`ModuleNotFoundError: No module named 'qrcode'`**

Install the dependencies using the Python interpreter you use to launch the application:

```bash
python -m pip install -r requirements.txt
```

**My phone cannot connect**

- Verify that both devices are connected to the same Wi-Fi network.
- Check your Windows Firewall settings.
- Make sure the application is running and displaying the correct QR code.
- Check whether your router uses client isolation, which can prevent devices from communicating.

**The session has expired**

The session token changes every time the application starts. Scan the newly displayed QR code to reconnect.

**Drawing does not work on macOS**

Check that the application has the required Accessibility and Screen Recording permissions in **System Settings → Privacy & Security**.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.

## Author

Created by [The_Quinn4642](https://github.com/quinthen2-bit).

If you find Phone Touchpad useful, consider giving the repository a ⭐ on GitHub.
