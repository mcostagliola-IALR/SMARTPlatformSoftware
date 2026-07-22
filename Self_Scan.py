#!/usr/bin/env python

'''
Contains all the code necessary to render a simple user interface allowing a user to change settings and run the SMART Table.
'''

import wx
import time
import os
import serial
import cv2
import numpy as np
import threading
import parse

# "False" will prevent the program from displaying the g-code messages it sends
verbose = False

def exportCoordinates(coords):
    """
    Exports plant centers to config.txt ready to be used in custom.
    Appends coordinates (0, 0) to the end of the file to save time from homing.
    Could be improved by auto homing at the end of custom.

    :param coords: list of coordinates to plant centers
    :return: nothin
    """
    # Handle the path, serial, and camera info
    configData = ""
    with open("config.txt", "r") as f:
        configData += f.readline()
        configData += f.readline()
        configData += f.readline()

    # Use the coords list to create the gcode instructions
    for c in coords:
        configData += ("X{:.3f} Y{:.3f}\n").format(c[0], c[1])
    # Add an instruction to 0,0 at the end
    configData += "X0 Y0"

    # Write the data to a new file
    # WARNING: If argument is config.txt, old config data will be overwritten
    with open("config.txt", "w") as f:
        f.write(configData)

''' UNUSED, but could be better than tracking position manually
def getCoords():
    s.write(("?\n").encode("UTF-8"))
    finishedReading = False  # indicator as to if coords and 'OK' have been found
    coords = None
    while not finishedReading:
        time.sleep(.2)  # wait 0.2 seconds between checking output
        grbl_out = s.readline().decode("UTF-8")
        if "MPos:" in grbl_out:
            # Parse coords in mm units
            coords = parse.search("MPos:{:f},{:f}", grbl_out)
            print(grbl_out)
            print("coords are X%f, Y%f" % (coords[0], coords[1]))

        if "OK" in grbl_out.upper():
            if coords is None:
                print("grbl_out returned \'ok\' but no coords. Exiting :(")
                exit() # Might as well quit since things arent working
            else:
                return coords
'''

def stream(gcode):
    '''
    Opens a file at the given filename, sends it to the serial port
    Parameter: the filename to open, as a string, e.g. stream("moveRight.gc") sends the contents of file moveRight.gc to the controller
    '''

    with open(os.path.join("Gcode", gcode), 'r') as f:
        # This opens a file at the specified file name, which must be in the same folder as the code itself.
        # The 'r' signifies that the file is open for reading only, not writing. Note: "with... as" is largely equivalent to "f = open(gcode,'r')", but is preferred because it also automatically closes the file at the end of the block
        for line in f:  # it may just be easier to look up how for loops in Python work, but the idea in this case is that "line" is a variable that changes to refer to each line in the file. In other words, whatever I do to the "line" variable will happen to every line in the file I opened.
            l = line.strip()  # Every line in a text file ends with an invisible "new line" character. This removes those so all that's left is the actual text on the file
            if verbose: print(
                'Sending: ' + l)  # This shows in the command prompt each time it sends an instruction. This isn't necessary, I just like keeping track of it.
            s.write((l + '\n').encode(
                "UTF-8"))  # Since l is used to represent the line in this case, this just "writes" the line to the serial port. The extra stuff about encoding in UTF-8 is because Python stores strings (strings = text) a special way, but they have to be changed to a string of bytes to send to a serial port, so this is required for that. Don't worry about it too much.
            received = False  # this is a boolean variable (boolean = true or false) to determine if the line of code has been received by the controller yet
            while not received:  # this will keep running as long as "received" is set to false
                time.sleep(.2)  # wait 0.2 seconds to check if it's been received
                grbl_out = s.readline().decode(
                    "UTF-8")  # check what the controller has sent back (grbl is the name of the firmware on the controller) and turn it back into a regular Python string
                if "OK" in grbl_out.upper():
                    received = True  # set "received" to true if the response was "ok", which is the default response whenever the controller receives a command
    # Since the indentation resets (signaling this code is no longer part of the "with... as" block), the file is closed
    wait()  # call the "wait" function before moving on, this is explained below


def raw_stream(gcode):
    '''
    Sends a string of text to the serial port
    Parameter: the actual gcode to send, as a string, e.g. stream("G0 X-15 Y20") sends those instructions directly
    '''


    l = gcode.strip()  # Make sure there's no invisible new line characters or spaces, for consistency's sake
    if verbose: print(
        'Sending: ' + l)  # This shows in the command prompt each time it sends an instruction. This isn't necessary, I just like keeping track of it.
    s.write((l + '\n').encode(
        "UTF-8"))  # Since l is used to represent the line in this case, this just "writes" the line to the serial port. The extra stuff about encoding in UTF-8 is because Python stores strings (strings = text) a special way, but they have to be changed to a string of bytes to send to a serial port, so this is required for that. Don't worry about it too much.
    received = False  # this is a boolean variable (boolean = true or false) to determine if the line of code has been received by the controller yet
    while not received:  # this will keep running as long as "received" is set to false
        time.sleep(.2)  # wait 0.2 seconds to check if it's been received
        grbl_out = s.readline().decode(
            "UTF-8")  # check what the controller has sent back (grbl is the name of the firmware on the controller) and turn it back into a regular Python string
        print(grbl_out + '\n')
        if "OK" in grbl_out.upper():
            received = True  # set "received" to true if the response was "ok", which is the default response whenever the controller receives a command
    # Since the indentation resets (signaling this code is no longer part of the "with... as" block), the file is closed
    wait()  # call the "wait" function before moving on, this is explained below


def camera(num, rep):
    '''
    Captures an image from a USB-connected camera and saves it to a file
    Accepts the plant number and the number of repetitions the table has already done (used for the filename) as parameters
    The first image taken each cycle should be in /Plant1/, second will be in /Plant2/, etc. Likewise, the first image of a given plant will have a filename starting with 1, the next image of the same plant will have a filename starting with 2, etc.
    This should mean that the bottom-right plant's photos will all be in the Plant1 folder, etc. and can be easily analyzed
    '''

    print("Taking photo", str(num))  # Tells the user that it's taking a photo, this is not necessary for functionality
    with open("config.txt", "r") as f:
        f.readline()
        f.readline()
        camNum = int(f.readline().strip())
        cap.open(camNum,
                 cv2.CAP_DSHOW)  # Open the camera object at port 1, port 0 being the built-in webcam on the laptop (I don't fully understand what the DSHOW thing means but there are various ways to process images and this one is the one that works best with this kind of camera, so just use that)
    # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0) # The camera constantly tries to change its exposure, and the only way I found to fix this is to manually reset it right before taking every photo.
    # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE,0.75)
    # cap.set(cv2.CAP_PROP_EXPOSURE, 0.002)
    (grabbed,
     img) = cap.read()  # Take a frame from the camera feed. "grabbed" is true/false depending on whether it was successful, while "img" is the actual image data
    t = time.localtime()  # check the time
    timestamp = time.strftime('%m-%d-%Y_%H-%M', t)  # put the time into a specific format, month-date-year_hour-minute
    with open("config.txt",
              "r") as file:  # to store the filepath between runs of the program, the user interface writes it to a text file, this just checks that
        folder = file.readline().strip()
    filepath = os.path.join(folder, "Plant" + str(
        num))  # Create the filepath for the image (FOLDER is defined up above, but it's basically the location of the master folder where all the images should be)
    if not os.path.exists(filepath):
        os.mkdir(filepath)  # If the folder doesn't already exist, make it. Pretty simple.
    filename = os.path.join(filepath, timestamp + "-Rep" + str(
        rep + 1) + ".jpg")  # Create the full filename, with the repetition-number and timestamp in the right folder
    cv2.imshow("Image " + str(num), img)  # Show the image on screen
    cv2.waitKey(
        1)  # wait for the user to press a button (I'm not sure how this works, since you still need the sleep line below)
    time.sleep(1)  # wait 1 second before the next line
    cv2.destroyAllWindows()  # close the window (the button-press isn't important since it closes after one second anyway)
    cv2.imwrite(filename, img)  # write the image to the specified filename
    print(filename)  # show the filename in the command prompt
    cap.release()  # release control of the camera (for some reason if you don't release it and reopen it every time the images start getting mixed up somehow)


def forty(reps, intervals, half=False):
    '''
    Moves the camera over either twenty or forty positions and takes photos of each
    Parameters:
    reps - an integer representing the number of times it should repeat the process, i.e. how many pictures you'll end up with of each plant.
    intervals - time taken between runs
    half - defaults to false, but if "true" is given as a parameter it will stop at the halfway point, in case you only want to work with 20 plants
    '''
    stream("start1.gc")  # Moves the camera to the position plant 1 is in
    stream("height.gc")  # Sets the camera to the height chosen by the user
    for i in range(
            reps):  # This just means the code below will run a number of times equal to the reps parameter. So if reps = 1, the following code will run over the entire table one time.
        t1 = time.time()  # Get the current time at the point when this repetition starts
        left = True  # Left should alternate between true/false each line, signaling the head to move left or right (it follows a zigzag path)
        num = 0  # this is the count of which plant we're on
        if half:  # if "half" was set to True, this tells the program to only run for four rows, not eight
            rows = 4
        else:
            rows = 8
        for j in range(rows):  # the following code runs once for each row
            for k in range(
                    4):  # the following code runs once for each column, except the last (and since this is all within the same row, that means this part is what covers moving to each plant in the row)
                num += 1  # Update the number of the plant we're on
                camera(num, i)  # Take the photo
                if left:  # If the "left" variable is set to true, tell the head to move left after taking the photo
                    stream("moveLeft.gc")
                else:  # If it's set to false, the head should move right instead
                    stream("moveRight.gc")
            num += 1  # This part will only run for the last plant in the row, since we don't want it to move left or right again after the last plant, so we can't use the same loop
            camera(num, i)  # Take a photo of the final plant
            if not (
                    num == 40 or num == 20):  # If we're on plant 40 we're at the end, if we're on plant 20 we have a bit more distance to cover since we have to get to the next panel
                stream(
                    "moveup.gc")  # if we're at the end of a row but it's not those two special cases, then we want to move up a certain amount
            elif num == 20 and not half:  # again, if we're on plant 20 then we need to move up further. "nextset.gc" is just an upward movement with a greater magnitude to account for the different distance
                stream("nextset.gc")
            left = not left  # Although this line is a bit weird to read, its functionality is pretty simple. If "left" was already set to true, then "not left" would be false, which means "left" will change to be false, or vice versa. Basically it just toggles between true or false
        stream("reset.gc")  # after all 40 plants have been covered, move back to plant 1 and start all over
        t2 = time.time()  # Get the time after finishing the repetition
        elapsed = t2 - t1  # Calculate how much time it took to run (time at end - time at start)
        if intervals and (
                i < reps - 1):  # If a value was set for "intervals", calculate how long to wait to ensure the photos are that many minutes apart. The second condition is so the program stops running after the last plant. Basically, if you set intervals = 15, and the table takes 11 minutes to run, it will wait the remaining 4 minutes so that the next set of photos will all be 15 minutes after the previous set
            to_wait = (intervals * 60) - elapsed
            if to_wait > 0:
                print("Waiting {0:.2f} minutes before starting the next repetition.".format(to_wait))
                time.sleep(to_wait)
            else:
                print("The interval specified was lower than the table took to run. Running again immediately.")


def wait():
    '''
    Called after every motion to ensure the camera is synced properly. This function
    stays in a loop, asking for a status report each second and only ending once the
    status report indicates the machine has stopped moving. In other words, this just
    means the program won't move on to the next step until the machine has finished its
    motion. Otherwise, it would start moving and immediately take the photo, which isn't what we want at all
    '''

    stopped = False  # Similar to the earlier loop to check every time a message is received, this checks to see if the machine has finished its motion yet.
    while not stopped:  # As long as "stopped" is set to false, keep looping
        time.sleep(
            0.2)  # Wait 0.2 seconds between loops (if this wasn't here, the program would be checking millions of times a second, and that probably slow things down quite a bit)
        s.write("?\n".encode("UTF-8"))  # Writing a ? to the controller requests a status report
        grbl_out = s.readline().decode("UTF-8")  # Read the status report sent back by the controller
        if "IDLE" in grbl_out.upper():  # The status report should say "idle" once the machine has stopped moving
            stopped = True  # set stopped = true once the machine has stopped, to end the loop
        grbl_out = s.readline()  # The controller sends back an "ok" after each status report, so this is to read that (although we don't need it for anything)


def eighty_six(reps, intervals, half=False):
    '''
    Similar to the above function, but covers 86 plants in total, or 43 if half is set to True
    '''
    stream("start2.gc")
    stream("height.gc")
    for i in range(reps):
        t1 = time.time()
        left = True
        num = 0
        if half:
            rows = 9
        else:
            rows = 18
        for j in range(rows):
            for k in range(4):
                if not (k == 2 and j in [0, 8, 9,
                                         17]):  # if it's at one of the positions that doesn't hold a plant, then don't take a picture or increment the number
                    num += 1
                    camera(num, i)
                if left:
                    stream("moveLeft.gc")
                else:
                    stream("moveRight.gc")

            num += 1
            camera(num, i)
            if not (num == 43 or num == 86):
                stream("moveup2.gc")
            elif num == 43 and not half:
                stream("nextset2.gc")
            left = not left
        stream("reset2.gc")
        t2 = time.time()
        elapsed = t2 - t1
        if intervals and (i < reps - 1):
            to_wait = (intervals * 60) - elapsed
            if to_wait > 0:
                print("Waiting {0:.2f} minutes before starting the next repetition.".format(to_wait))
                time.sleep(to_wait)
            else:
                print("The interval specified was lower than the table took to run. Running again immediately.")


def twenty_eight(reps, intervals, half=False):
    '''
    Same as the two above, but covers 28 or 14 plants.
    '''
    stream("start2.gc")
    stream("height.gc")
    for i in range(reps):
        if half:
            max = 14
        else:
            max = 28
        t1 = time.time()
        up = True
        num = 0
        for j in range(max):
            num += 1
            camera(num, i)
            if num in [5, 9, 19, 23]:
                stream("nextcolumn.gc")
                up = not up
            elif num == 14:
                stream("nextset3.gc")
            elif num != 28:
                if up:
                    stream("moveup.gc")
                else:
                    stream("movedown.gc")
        stream("reset2.gc")
        t2 = time.time()
        elapsed = t2 - t1
        if intervals and (i < reps - 1):
            to_wait = (intervals * 60) - elapsed
            if to_wait > 0:
                print("Waiting {0:.2f} minutes before starting the next repetition.".format(to_wait))
                time.sleep(to_wait)
            else:
                print("The interval specified was lower than the table took to run. Running again immediately.")


def custom(reps, intervals):
    """
    For if the user wants to use custom coordinates instead of a specific pattern.
    Same parameters as the other "layout" functions detailed above

    :param reps: number of repetitions to take images
    :param intervals: amount of time between reps
    :return: nothing
    """

    stream("start.gc")
    stream("height.gc")
    raw_stream("G90G20G0")
    for i in range(reps):
        t1 = time.time()
        num = 0
        with open("config.txt", 'r') as instructions:  # Open the config file
            instructions.readline()  # Skip past the first line (the filepath) before starting hthe loop (we "read" the line, but don't do anything with it, so all that does is move the program to the next line)
            instructions.readline()  # Skip through the second line (the port number)
            instructions.readline()  # Skip the third line (the camera port number)
            for line in instructions:  # For every line in the file except the first one (which is the filepath to save images in)
                num += 1
                raw_stream(line)  # stream the contents of the line directly to the controller
                camera(num, i)
        t2 = time.time()
        elapsed = t2 - t1
        if intervals and (i < reps - 1):
            to_wait = (intervals * 60) - elapsed
            if to_wait > 0:
                print("Waiting {0:.2f} minutes before starting the next repetition.".format(to_wait))
                time.sleep(to_wait)
            else:
                print("The interval specified was lower than the table took to run. Running again immediately.")

def binaryEyes():
    """
    Captures an image and gets plant center from green pixels visible.
    :return: nothing, but updates several global variables
    """
    ret, frame = cap.read()  # read frame called
    cv2.imshow('camera', frame)
    cv2.waitKey(1)

    hsvImage = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    height, width, _ = frame.shape

    center_width = (width / 2)  # to find the center of frame
    center_height = (height / 2)

    global cFrameHeight
    global cFrameWidth
    cFrameHeight = int(center_height)
    cFrameWidth = int(center_width)

    global camera
    camera = (cFrameWidth, cFrameHeight)

    cv2.circle(frame, (cFrameWidth, cFrameHeight), 5, (255, 0, 0), 3)  # put a circle at the center of frame

    # create mask (filter) tp pull out only green/the plant from frame
    low_green = np.array([30, 60, 130])
    high_green = np.array([90, 255, 250])
    green_mask = cv2.inRange(hsvImage, low_green, high_green)
    green = cv2.bitwise_and(frame, frame, mask=green_mask)

    GRAY_Image = cv2.cvtColor(green, cv2.COLOR_RGB2GRAY)
    (thresh, GRAY_Image) = cv2.threshold(GRAY_Image, 0, 255, cv2.THRESH_BINARY)
    
    noiseless = cv2.fastNlMeansDenoising(GRAY_Image, 45, 15, 15)

    global count
    count = cv2.countNonZero(noiseless)

    # find local average center of all current green pixels placed on the screen
    # cX = center of green object's widths
    # cY = center of green object's height
    drw = cv2.Canny(noiseless, 100, 200)
    m = cv2.moments(drw)
    global cX
    global cY
    if m["m00"] != 0:
        cX = int(m["m10"] / m["m00"])
        cY = int(m["m01"] / m["m00"])
    else:
        cX, cY = 0, 0
    # put text and highlight the center
    cv2.circle(noiseless, (cX, cY), 5, (60, 60, 40), -1)
    cv2.putText(noiseless, "centroid", (cX - 25, cY - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 60, 40), 2)

    cv2.circle(noiseless, (cFrameWidth, cFrameHeight), 5, (60, 60, 40), 3)

    global plant
    plant = (cX, cY)

    cv2.imshow('output', noiseless)

def selfScan(coordlist):
    """
    Location process for one plant. Compares green center of mass with center of camera and
    moves them closer together until they are within a certain distance.

    Can be improved by implementing checks to prevent going out of bounds, since the table only
    has limit switches toward the origin.

    :param coordlist: list to store plant coordinates
    :return: nothing
    """

    global numX
    global numY
    global plantloco

    binaryEyes()

    if cap.isOpened:
        while camera != plant:
            # Check if in bounds, return if out
            # TODO: Not implemented

            # Call binaryEyes to check green
            binaryEyes()

            if cX > cFrameWidth and not (cX >= 310 and cX <= 330):
                if verbose:
                    print("moving right")
                    print("plant position is x= %d, y= %d" % (cX, cY))
                    print("camera position is x= %d, y= %d" % (cFrameWidth, cFrameHeight))
                stream('moveRightSm.gc')
                numX -= 0.5

            elif cX < cFrameWidth and not (cX >= 310 and cX <= 330):
                if verbose:
                    print("moving Left")
                    print("plant position is x= %d, y= %d" % (cX, cY))
                    print("camera position is x= %d, y= %d" % (cFrameWidth, cFrameHeight))
                stream('moveLeftSm.gc')
                numX += 0.5

            if cY < cFrameHeight and not (cY >= 220 and cY <= 250):
                if verbose:
                    print("moving up")
                    print("plant position is x= %d, y= %d" % (cX, cY))
                    print("camera position is x= %d, y= %d" % (cFrameWidth, cFrameHeight))
                stream('moveUpSm.gc')
                numY += 0.5

            elif cY > cFrameHeight and not (cY >= 220 and cY <= 250):
                if verbose:
                    print("moving down")
                    print("plant position is x= %d, y= %d" % (cX, cY))
                    print("camera position is x= %d, y= %d" % (cFrameWidth, cFrameHeight))
                stream('moveDownSm.gc')
                numY -= 0.5

            if cX >= 300 and cX <= 340 and cY >= 210 and cY <= 260:
                current = (numX, numY)
                if current != (0, 0):
                    #Append the x and y coordinates, since currently cannot append as a tuple
                    coordlist.append(current)
                    plantloco += 1
                break


def scanTable():
    """
    Outermost function for scanning over the table to retrieve plant center coordinates.
    Overwrites found data to config.txt after finishing.

    Needs adjustment to numRows and numCols to account for expected number of plants.
    If increase cols beyond 4 or rows beyond 8, may need to reduce movement in move{direction}Big.gc files,
    which introduces complications due to risk of having multiple plants in view. Spot for improvement.

    Could be improved by having table operate with an unspecified number of rows/cols, but at least
    this is good for testing.

    Could also be improved by finding a way to get coordinates thru OpenBuilds rather than track
    manually.

    :return: nothing, but data is output to config.txt
    """
    coordlist = []  # List of known plant centers, maintained as tuples of (x, y)

    # Sets up fields
    # numX and numY are for manually keeping up with coords
    global numX
    numX = 0
    global numY
    numY = 0
    global plantloco
    plantloco = 0
    # For a rudimentary snake path, prepares the table for dealing with numRows x numCols plants
    numRows = 2
    numCols = 2

    directionFlipper = 0  # Indicates direction to scan, even = left, odd = right

    for i in range(numRows):  # Scan each plant in every row (short end)
        selfScan(coordlist)
        for j in range(numCols - 1):  # Scan each plant in every col
            if directionFlipper % 2 == 0: # Move left on even plants
                stream('moveLeftBig.gc')
                numX += 16
            else:
                stream('moveRightBig.gc')
                numX -= 16
            selfScan(coordlist)
        print("i  = %d, numRows = %d" % (i, numRows))

        if i != numRows - 1: # Advance to next row on all rows except for last
            stream('moveUpBig.gc')
            numY += 16
            directionFlipper += 1

    # Export coords and return to home after finding all plants
    exportCoordinates(coordlist)
    raw_stream("$H")


class MainFrame(wx.Frame):
    """
    A Frame containing settings for the SMART Table, serves as a user interface to change settings and run the table
    """

    def __init__(self, *args, **kw):
        # ensure the parent's __init__ is called
        super(MainFrame, self).__init__(*args, **kw)
        # resize the window, define a bunch of parameters
        self.SetInitialSize(wx.Size(400,600))
        self.pcount = 0
        self.half = False
        self.height = "Z0"
        self.interval = 0
        self.reps = 1
        self.filepath = ""
        # check to see if a filepath has been previously defined
        if os.path.exists("config.txt"):
            with open("config.txt",'r') as f:
                self.filepath = f.readline()
        # if not, just use the folder this program is in
        else:
            self.filepath = os.path.abspath(os.getcwd())

        # create a panel in the frame
        pnl = wx.Panel(self)

        # put some text with a larger bold font on it
        st = wx.StaticText(pnl, label="SMART Table Settings")
        font = st.GetFont()
        font.PointSize += 10
        font = font.Bold()
        st.SetFont(font)

        # Everything below here for a while is just defining buttons and binding their associated function (i.e. if you click the checkbox defined as "check", with the label "only half this amount", it will trigger the "OnHalf" function
        check = wx.CheckBox(pnl, label = "Only half this amount")
        self.Bind(wx.EVT_CHECKBOX, self.OnHalf, check)


        buttonLabel = wx.StaticText(pnl, label="How many plants are you using?")
        button1 = wx.RadioButton(pnl, label = "Eighty-six")
        button2 = wx.RadioButton(pnl, label = "Forty")
        button3 = wx.RadioButton(pnl, label = "Twenty-eight")
        button4 = wx.RadioButton(pnl, label = "Custom")
        button5 = wx.RadioButton(pnl, label="Self-Scan")

        self.Bind(wx.EVT_RADIOBUTTON, self.OnButton1, button1)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnButton2, button2)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnButton3, button3)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnButton4, button4)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnButton5, button5)

        pathLabel = wx.StaticText(pnl, label="Choose folder to save photos in")
        pathLabel2 = wx.StaticText(pnl, label="Current: "+self.filepath)
        pathButton = wx.Button(pnl, label="Choose folder")
        self.Bind(wx.EVT_BUTTON, lambda event: self.OnOpen(event,pathLabel2), pathButton)

        heightLabel = wx.StaticText(pnl, label="Enter z-coordinate to use (use the GUI and camera")
        heightLabel2 = wx.StaticText(pnl, label="to pick an appropriate height)")
        zcount = wx.TextCtrl(pnl, value = "0")
        self.Bind(wx.EVT_TEXT, lambda event: self.OnHeight(event,zcount.GetLineText(0)), zcount)

        repLabel = wx.StaticText(pnl, label="Enter number of repetitions for the table to perform")
        rcount = wx.TextCtrl(pnl, value = "1")
        self.Bind(wx.EVT_TEXT, lambda event: self.OnReps(event,rcount.GetLineText(0)), rcount)

        intLabel = wx.StaticText(pnl, label="Enter number of minutes between each repetition,")
        intLabel2 = wx.StaticText(pnl, label="or leave it as 0 for no waiting between repetitions")
        intcount = wx.TextCtrl(pnl, value = "0")
        self.Bind(wx.EVT_TEXT, lambda event: self.OnInts(event,intcount.GetLineText(0)), intcount)

        run = wx.Button(pnl, label="Run")
        self.Bind(wx.EVT_BUTTON, self.OnRun, run)

        # Now create a sizer (an object that handles layouts) and add everything to it, putting spacing to the left of each of them and above some of them to split it into groups
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(st, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        sizer.Add(buttonLabel, wx.SizerFlags().Border(wx.TOP|wx.LEFT,25))
        sizer.Add(button1, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(button2, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(button3, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(check, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(button4, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(button5, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(pathLabel, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        sizer.Add(pathLabel2,wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(pathButton, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(heightLabel, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        sizer.Add(heightLabel2, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(zcount, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(repLabel, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        sizer.Add(rcount, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(intLabel, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))
        sizer.Add(intLabel2, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(intcount, wx.SizerFlags().Border(wx.LEFT, 25))
        sizer.Add(run, wx.SizerFlags().Border(wx.TOP|wx.LEFT, 25))

        pnl.SetSizer(sizer)


    #def OnExit(self, event):
        """Close the frame, terminating the application."""
        #self.Close(True)

    # The following 4 functions handle the buttons the user clicks to set the number of plants
    def OnButton1(self, event):
        self.pcount = 86

    def OnButton2(self, event):
        self.pcount = 40

    def OnButton3(self, event):
        self.pcount = 28

    def OnButton4(self, event):
        self.pcount = -1

    def OnButton5(self, event):
        self.pcount = -2


    def OnHalf(self, event):
        self.half = True

    # Sets the height of the camera
    def OnHeight(self, event, z):
        self.height = "Z"+z
        with open("height.gc","w") as file:
            file.write(self.height) # writes "height.gc", which the script above will send to the table with the rest of the g-code

    # Lets the user set the number of reps for the table to do
    def OnReps(self, event, r):
        try: self.reps = int(r) # try to convert the value the user enters into an integer and set it to the property "reps"
        except ValueError: pass # if what they enter can't be converted to an integer (i.e. if they leave it blank or something), just don't do anything

    # Lets the user set the time between intervals
    def OnInts(self, event, i):
        try: self.interval = int(i) # same as above
        except ValueError: pass

    # Sets the folder to store the photos in
    def OnOpen(self, e, label):
        with wx.DirDialog(self) as dd: # This opens the default Windows interface to let the user choose a folder
            if dd.ShowModal() == wx.ID_CANCEL:
                return
            pathname = dd.GetPath()
            self.filepath = pathname
            instructions = []
            with open("config.txt",'r') as f:
                f.readline()
                for line in f:
                    instructions.append(line)
            with open("config.txt","w") as f: # writes the filepath the user chose to the "config.txt" file so the program can access it in the future
                f.write(pathname+"\n")
                for instruction in instructions:
                    f.write(instruction)
        label.SetLabel("Current: " + self.filepath)

    # Signals the table to run
    def OnRun(self, event):
        with open("config.txt","r") as f:
            f.readline() # skip past the first line (filepath)
            portNum = f.readline().strip() # check the next line for the port
            camNum = int(f.readline().strip()) # check the third line for the camera number
            print("port num = %s, cam num = %s" % (portNum, camNum))
        global s

        s = serial.Serial(portNum,115200,write_timeout=2,timeout=2) # open the port: 115200 is the rate at which the port sends/receives data, we set timeouts so if it goes 2 seconds without getting a response it will automatically end instead of getting locked up (this shouldn't happen)
        global cap
        cap = cv2.VideoCapture(camNum,cv2.CAP_DSHOW) # Create the object that allows access to the image-capturing functionality

        # wake up grbl (reminder: grbl is the firmware on the Black Box controller)
        s.write("\r\n\r\n".encode(
            "UTF-8"))  # something has to be sent to the controller to signal the firmware to start up
        time.sleep(2)  # wait for it to start up
        s.reset_input_buffer()  # delete the text the controller is already processing, to make sure it's empty

        if self.pcount == 0: # pcount is the default option for number of plants, meaning the user didn't click any of the three options
            print("Choose an option!")
        else:
            self.Close(True)
            raw_stream("$H")
            if self.half:
                print("Running with",str(self.pcount/2),"plants")
            else:
                print("Running with",str(self.pcount),"plants")
            print(self.interval,"minutes between repetitions")
            print(self.reps,"repetitions")
            if self.interval:
                t = self.interval * self.reps # number of minutes it will run
                t = t // 60 # convert that to hours
                d = t // 24 # get how many days that is
                h = t%24 # turn the remainder back into hours
                print("The SMART Table is predicted to run for {0:d} days and {1:d} hours".format(d,h))
                # the "format" command replaces {0} with the first thing you put after it (in this case, the value of variable d), {1} with the second thing, etc. and the :d shows that I want to format it as a number. This could also be done as "The SMART Table is predicted to run for " + d + " days and " + h + "hours" but I thought this way was easier
            # Call the appropriate function (defined above) based on the amount of plants the user is using
            if self.pcount == 28:
                twenty_eight(self.reps,self.interval,self.half)
            if self.pcount == 40:
                forty(self.reps,self.interval,self.half)
            if self.pcount == 86:
                eighty_six(self.reps,self.interval,self.half)
            if self.pcount == -1:
                custom(self.reps,self.interval)
            if self.pcount == -2:
                scanTable()


            s.close() # Close the serial port


if __name__ == '__main__':
    # When this module is run (not imported) then create the app, the
    # frame, show it, and start the event loop.
    app = wx.App()
    frm = MainFrame(None, title='SMART Table Settings')
    frm.Show()
    app.MainLoop()

