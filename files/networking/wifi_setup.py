import os
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw
from font_source_serif_pro import SourceSerifProSemibold
from font_source_sans_pro import SourceSansProSemibold
import RPi.GPIO as GPIO
import pickle
import signal
import hitherdither



# Gpio pins for each button (from top to bottom)
BUTTONS = [5, 6, 16, 24]
# Set up RPi.GPIO with the "BCM" numbering scheme
GPIO.setmode(GPIO.BCM)
# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# These correspond to buttons A, B, C and D respectively
LABELS = ['A', 'B', 'C', 'D']

colors = ['Black', 'White', 'Green', 'Blue', 'Red', 'Yellow', 'Orange']

inky = auto(ask_user=True, verbose=True)
inky.set_border(colors.index('Orange'))

# "handle_button" will be called every time a button is pressed
# It receives one argument: the associated input pin.
def handle_button(pin):
    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))
    if label == "A":
        try:
            configure_wifi(wifi[0][0], wifi[0][1])
        except IndexError:
            print("no such option")
    elif label == "B":
        try:
            configure_wifi(wifi[1][0], wifi[1][1])
        except IndexError:
            print("no such option")
    elif label == "C":
        try:
            configure_wifi(wifi[2][0], wifi[2][1])
        except IndexError:
            print("no such option")
    elif label == "D":
        try:
            configure_wifi(wifi[3][0], wifi[3][1])
        except IndexError:
            print("no such option")
    os.popen("python3 /home/a-lid/a-lid-a-tog/a-lid-a-tog.py")

# Loop through out buttons and attach the "handle_button" function to each
# We're watching the "FALLING" edge (transition from 3.3V to Ground) and
# picking a generous bouncetime of 250ms to smooth out button presses.
for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=250)

# from Vivek Maskara
def configure_wifi(ssid, password):
    config_lines = [
        'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev',
        'update_config=1',
        'country=US',
        '\n',
        'network={',
        '\tssid="{}"'.format(ssid),
        '\tpsk="{}"'.format(password),
        '}'
        ]
    config = '\n'.join(config_lines)

    #give access and writing. may have to do this manually beforehand
    os.popen("sudo chmod a+w /etc/wpa_supplicant/wpa_supplicant.conf")

    #writing to file
    with open("/etc/wpa_supplicant/wpa_supplicant.conf", "w") as wifi_config:
        wifi_config.write(config)

    print("Wifi config added. Refreshing configs")
    ## refresh configs
    os.popen("sudo wpa_cli -i wlan0 reconfigure")

f = open('/home/a-lid/a-lid-a-tog/wifi.p', 'rb')
wifi = pickle.load(f)
f.close()
message = "Welcome to A-Lid-A-Tog!\nChoose your wifi network: \n\n"
for i in range(len(wifi)):
    message += "— " + wifi[i][0] + " (press button " + LABELS[i] + ")\n\n"

padding = 20
width = 150
img = Image.new("P", (inky.width, inky.height), colors.index("Green"))

logo = Image.open("/home/a-lid/a-lid-a-tog/aleph.jpeg")
resizedlogo = logo.resize((width, width), resample=Image.LANCZOS).convert("RGB")
img.paste(resizedlogo, (inky.width - width - padding, padding))

draw = ImageDraw.Draw(img)
font = ImageFont.truetype(SourceSansProSemibold, 26)
draw.multiline_text((padding, padding), message, fill=colors.index("White"), font=font, align="left")

inky.set_image(img, .5)
inky.show()
signal.pause()
