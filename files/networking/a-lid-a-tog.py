# This Python file uses the following encoding: utf-8
# Copyright (C) 2017-present,  Raphael Halff

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree,
# but you can also find it here: <http://www.gnu.org/licenses/>.


import os
import string
import pickle
import mysql.connector
import sys
import codecs
import math
import signal
import qrcode
import RPi.GPIO as GPIO
from inky.auto import auto
from PIL import Image, ImageFont, ImageDraw
from font_source_serif_pro import SourceSerifProSemibold
from font_source_sans_pro import SourceSansProSemibold

BLUE = 3
YELLOW = 5
inky = auto(ask_user=True, verbose=True)
inky.set_border(BLUE)

# Gpio pins for each button (from top to bottom)
BUTTONS = [5, 6, 16, 24]
# Set up RPi.GPIO with the "BCM" numbering scheme
GPIO.setmode(GPIO.BCM)
# Buttons connect to ground when pressed, so we should set them up
# with a "PULL UP", which weakly pulls the input signal to 3.3V.
GPIO.setup(BUTTONS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# These correspond to buttons A, B, C and D respectively
LABELS = ['A', 'B', 'C', 'D']


f = open('/home/a-lid/a-lid-a-tog/mysql.p', 'rb')
config = pickle.load(f)
f.close()

def getpoem():
  # make connection, format query
  cnx = mysql.connector.connect(**config)
  cursor = cnx.cursor()
  query = "SELECT *, poem.poet as ogpoet, poem.source as ogsource, trans.source as tsource, trans.poet as tpoet, trans.translator as ttranslator FROM poem LEFT JOIN trans on poem.poem=trans.poem LEFT JOIN poet on poem.poet=poet.name_e WHERE genre='poem' AND trans.lang='eng' AND trans.text IS NOT NULL ORDER BY RAND() LIMIT 1"
  cursor.execute(query)
  poem = cursor.fetchall()
  cnx.close()
  return poem

#reverse yiddish text to print rtl. ideally check if string needs to be encoded/decoded
def rtl(text):
  t = text.replace("\r\n", "").split("\n")
  rtl_text = ""
  for line in t:
      rtl_text += line[::-1] + "\n"
  # try:
  #   t = t.decode('utf8')
  # except UnicodeEncodeError:
  #   pass
  return rtl_text

# "handle_button" will be called every time a button is pressed
# It receives one argument: the associated input pin.
def handle_button(pin):
    global poem
    global lang_state
    global sections
    global scroll_state
    global text_windows
    global reflowed

    label = LABELS[BUTTONS.index(pin)]
    print("Button press detected on pin: {} label: {}".format(pin, label))
    if label == "A":
        #reload _poem
        print("reload")
        lang_state = 0
        scroll_state = 0
        sections = 0
        reflowed = ""
        text_windows = []
        poem = getpoem()
        displayeng(poem)
    elif label == "B":
        #switch language
        print("switching languages")
        if lang_state == 0:
            lang_state = 1
            scroll_state = 0
            sections = 0
            text_windows = []
            displayyid(poem)
        elif lang_state == 1:
            lang_state = 0
            scroll_state = 0
            sections = 0
            text_windows = []
            displayeng(poem)
    elif label == "C":
        print("scroll up")
        if scroll_state > 1:
            scroll_state -= 1
            if lang_state == 0:
                displayeng(poem)
            else:
                displayyid(poem)
    elif label == "D":
        print("scroll down")
        if scroll_state < sections:
            scroll_state += 1
            if lang_state == 0:
                displayeng(poem)
            else:
                displayyid(poem)

# Loop through out buttons and attach the "handle_button" function to each
# We're watching the "FALLING" edge (transition from 3.3V to Ground) and
# picking a generous bouncetime of 250ms to smooth out button presses.
for pin in BUTTONS:
    GPIO.add_event_detect(pin, GPIO.FALLING, handle_button, bouncetime=250)

def reflow_quote(quote, width, font):
    global sections
    global scroll_state

    quote = quote.replace("\r\n", "\n")
    lines = quote.split("\n")
    #instead of splitting by words, split line, check size, split and cut if needed
    reflowed = ''
    line_count = 0
    for line in lines:
        if font.getlength(line) > width:
            words = line.split(" ")
            line_length = 0
            for word in words:
                 line_length += font.getlength(word + " ")
                 if line_length <= width:
                     reflowed += word + " "
                 else:
                     reflowed += "\n     " + word + " "
                     line_length = font.getlength("\n     " + word + " ")
                     line_count += 1
            reflowed += "\n"
            line_count += 1
        else:
            reflowed += line + "\n"
            line_count += 1
    print(str(line_count)+ "/17 = " + str((line_count / 17.0)) + ", "+ str(math.ceil((line_count / 17.0))))
    sections = math.ceil((line_count / 17.0))
    scroll_state = 1
    return reflowed

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

def display(text, alignment, font):
    global poem
    global sections
    global scroll_state
    global text_windows
    global reflowed

    img = Image.new("P", (inky.width, inky.height), YELLOW)

    print("pre reflow, scroll_state: " + str(scroll_state) + ", sections: " + str(sections))
    # get qr if section 1
    if scroll_state <= 1:
        qr = qrcode.make("https://xn--7dbli0a4a.us.org/poem.php?poem=" + poem[0][0])
        qr_size = (75,75)
        resizedqr = qr.resize(qr_size)
        qr_space = 5
        if lang_state == 0:
            img.paste(resizedqr, (inky.width - qr_size[1] - qr_space, qr_space))
        else:
            img.paste(resizedqr, (qr_space, qr_space))
    draw = ImageDraw.Draw(img)

    # Also define the max width and height for text
    padding = 20
    max_width = inky.width - (padding * 2)
    max_height = inky.height - (padding * 2)

    # get reflowed text
    if scroll_state == 0:
        reflowed = reflow_quote(text, inky.width, font)
        if lang_state == 1:
            reflowed = rtl(reflowed)

    print("post reflow, scroll_state: " + str(scroll_state) + ", sections: " + str(sections))

    # get scroll windows
    if sections > 1 and scroll_state == 1:
        i = 0
        line_max = 17
        nth = line_max
        line_c = 0
        while line_c < reflowed.count("\n"):
            next = find_nth(reflowed, "\n", nth)
            line_c += 1
            text_windows.append(reflowed[i:next])
            i = next + 1
            nth += line_max
        print(text_windows)
    if sections > 1:
        ready_text = text_windows[scroll_state - 1]
    else:
        ready_text = reflowed

    print("\n\nready_text" + ready_text)
    # x- and y-coordinates for the top left of text
    text_x = (inky.width - max_width) / 2
    if lang_state == 1:
        longest_line = 0
        for line in ready_text.split("\n"):
            if font.getlength(line) > longest_line:
                longest_line = font.getlength(line)
        text_x = max_width - padding - longest_line
    text_y = (inky.height - max_height)

    # Write our quote and author to the canvas
    # direction="rtl" only works with libraqm
    draw.multiline_text((text_x, text_y), ready_text, fill=BLUE, font=font, align=alignment)

    inky.set_image(img)
    inky.show()

def displayyid(poem):
    ruel = ImageFont.truetype("/home/a-lid/a-lid-a-tog/fonts/FrankRuehlCLM-Medium.ttf", 22)
    text = poem[0][1] + "\nפֿון " + poem[0][20] + "\n\n" + poem[0][5]
    display(text, "right", ruel)

def displayeng(poem):
    ubuntu = ImageFont.truetype("/home/a-lid/a-lid-a-tog/fonts/UbuntuMono-Regular.ttf", 20)
    text = poem[0][15] + "\nBy " + poem[0][21] + "\n\n" + poem[0][16]
    display(text, "left", ubuntu)


# main
sections = 0
lang_state = 0
scroll_state = 0
text_windows = []
reflowed = ""
poem = getpoem()
displayeng(poem)
signal.pause()
