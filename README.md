# Phone Touchpad

> Teken met je telefoon op je pc: scan een QR-code en teken op een live screenshot van je scherm.

Teken met je telefoon op je pc. Scan een QR-code, je ziet een live screenshot van je
scherm op je telefoon en tekent er met je vinger direct op. Zodra je loslaat, wordt de
hele streek in één keer op je pc getekend, met ingedrukte muisknop.

Handig voor tekenprogramma's, whiteboards, presentaties of annoteren op je scherm.

## Functies

- Tekenen direct op de screenshot van je pc, zonder app op je telefoon (alleen een browser)
- Eén request per streek in plaats van honderden losse muisberichten
- Vloeiende lijnen: korte stukjes worden aangevuld en een trillende vinger wordt gladgestreken
- Zijwaartse modus en volledig scherm voor een grotere screenshot
- Witte rand met sluitknop (X) rond je scherm zodra je telefoon verbonden is
- Werkt volledig lokaal: er gaat niets via het internet

## Hoe het werkt

```
telefoon (browser)  ──wifi──▶  Flask-server op je pc  ──▶  pyautogui (muis + screenshot)
  tekent op screenshot          /screen.jpg, /api/stroke       tkinter: QR-code + rand
```

1. Het programma start een webserver op poort 8765 en toont een QR-code.
2. Je telefoon opent de link en haalt elke paar seconden een screenshot op.
3. Je tekent op de telefoon. Bij loslaten gaat de hele streek in één request naar de pc.
4. De pc zet de muisknop in, volgt alle punten en laat los.

## Installatie

Vereist Python 3.9 of nieuwer met tkinter.

```bash
git clone https://github.com/The_Quinn4642/phone-touchpad.git
cd phone-touchpad
python -m pip install -r requirements.txt
```

Gebruik `python -m pip` zodat de libraries zeker in dezelfde Python komen als waarmee je
het programma start (belangrijk als je meerdere Python-versies hebt).

## Gebruik

```bash
python phone_touchpad.py
```

1. Zorg dat je telefoon en pc op **hetzelfde wifi-netwerk** zitten.
2. Scan de QR-code met je telefoon.
3. Teken op de screenshot. De knoppen onderaan zijn **Vernieuwen**, **Draai** (zijwaarts) en **Volledig scherm**.
4. Sluit het programma met de **X** linksboven op je scherm.

### Platformen

| Platform | Opmerkingen |
|----------|-------------|
| Windows  | Werkt direct. Sta de firewall-melding toe voor privénetwerken. |
| macOS    | Geef je terminal (of de app) toegang onder *Systeeminstellingen → Privacy en beveiliging* bij **Toegankelijkheid** en **Schermopname**. |
| Linux    | Alleen X11. Wayland wordt niet ondersteund door pyautogui. |

## Instellingen

Bovenin `phone_touchpad.py`:

| Instelling | Standaard | Omschrijving |
|------------|-----------|--------------|
| `PORT` | `8765` | Poort van de webserver |
| `REFRESH_MS` | `8000` | Automatisch screenshot vernieuwen (ms), `0` = alleen handmatig |
| `STEP_PX` | `3` | Maximale afstand tussen muispunten, kleiner = vloeiender |
| `SMOOTH_WINDOW` | `3` | Gladstrijken tegen trillen, `1` = uit |
| `STEP_DELAY` | `0.002` | Pauze tussen punten (sec), hoger = rustiger tekenen |
| `FRAME_ALPHA` | `0.75` | Doorzichtigheid van de witte rand |

## Veiligheid

- De link bevat een willekeurige token die bij elke start verandert. Wie de link heeft, kan **je muis besturen en je scherm zien**.
- De verbinding is niet versleuteld (http). Gebruik het alleen op een netwerk dat je vertrouwt.
- Zet poort 8765 nooit open naar het internet.

## Een los programma maken

Windows (PyInstaller):

```bash
python -m pip install pyinstaller
python -m PyInstaller --onefile --noconsole phone_touchpad.py
```

Het resultaat staat in `dist/`.

## Problemen oplossen

- **`No module named 'qrcode'`**: je installeert in een andere Python dan waarmee je draait. Gebruik `python -m pip install -r requirements.txt`.
- **Telefoon kan niet verbinden**: controleer wifi (zelfde netwerk) en firewall.
- **"Sessie verlopen"**: de token verandert bij elke start. Scan de QR-code opnieuw.
- **Tekenen werkt niet op macOS**: controleer de rechten voor Toegankelijkheid en Schermopname.

## Licentie

MIT, zie [LICENSE](LICENSE).

Gemaakt door [The_Quinn4642](https://github.com/The_Quinn4642).
