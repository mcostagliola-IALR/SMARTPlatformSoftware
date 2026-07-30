import numpy as np
from scipy import misc, ndimage
from matplotlib import pyplot as plt
import xlsxwriter
import glob
import os
import sys
import imageio.v2 as imageio
import traceback
import time
from xlsxwriter.utility import xl_rowcol_to_cell
import re

def formatCellInfoFromFilename(filename):
    """
    Extracts the information from the filename to create a clear and more presentable string.

    :param filename: for the current photo, expected to be in the following format: 06-29-2023_13-52-Rep1.jpg
    :return: formatted string with extracted data, ex: 07/08/2023 09:33AM
    """

    try:
        shortenedname = filename.split("-Rep")[0]
        timeinfo = time.strptime(shortenedname, "%m-%d-%Y_%H-%M")  # struct as defined in time module
        return time.strftime("%m/%d/%Y %I:%M%p", timeinfo)
    except:
        # formatted name could not be parsed, use filename instead
        return filename


def writeData(row, col, filename, newPic, oldPic=None):
    """
    Outputs data for a specific plant and rep to the excel sheet.

    :param row: uppermost row of cell range where work is being written
    :param col: leftmost column of cell range where work is being written
    :param filename: name of the file, containing information to extract for cells
    :param newPic: the matrix representation of green pixels for the current plant
    :param oldPic: the matrix representation of green pixels for the previous plant,
        set to None in the case of the first plant
    :return: nothing
    """

    # Writes the rep number
    Size_Worksheet.write(row, col, row - 1)
    Motion_Worksheet.write(row, col, row - 1)
    Growth_Worksheet.write(row + 1, col, row - 1) #Growth_Worksheet is one ahead due to the pixel flux beneath header

    # Writes the date and time in a more readable format
    Size_Worksheet.write(row, col + 1, formatCellInfoFromFilename(filename))
    Size_Worksheet.set_column(col + 1, col + 1,
                              len(filename))  # Sets col width to fit width of filename, TODO: refactor to use only once...
    Motion_Worksheet.write(row, col + 1, formatCellInfoFromFilename(file))
    Motion_Worksheet.set_column(col + 1, col + 1, len(file))
    Growth_Worksheet.write(row + 1, col + 1, formatCellInfoFromFilename(file))
    Growth_Worksheet.set_column(col + 1, col + 1, len(file))

    # writes the Size value for all plants
    Size_Worksheet.write(row, col + 2, np.count_nonzero(newPic))

    # writes the growth and motion values for all plants aside from the first
    if oldPic is None:
        # N/A when there is no previous data to calculate with
        Motion_Worksheet.write(row, col + 2, "N/A")
        Growth_Worksheet.write(row + 1, col + 2, "N/A")
    else:
        # Counts the number of pixels (under mask) different from previous capture. Done by XOR operation on image matrices
        Motion_Worksheet.write(row, col + 2, np.count_nonzero(newPic ^ oldPic))
        # Counts the difference in pixels between the new capture and the previous capture.
        Growth_Worksheet.write(row + 1, col + 2, np.count_nonzero(newPic) - np.count_nonzero(oldPic))



def Isolate_Green(image):
    """
    Isolates the green pixels of an image by applying several masks and
    converting to a binary representation of pixels.

    :param image: image to isolate green of
    :return: binary closing of the image after masks have been applied
    """
    try:
        '''
        #tomato
        greenmask = image[:, :, 1] > 90
        bluemask = image[:,:,2] < 130
        whiteremovemask = (image[:,:,1] - image[:,:,2]) > 50
        brownremovemask = (image[:,:,0] - image[:,:,1]) > 80
        blackmask = (image[:,:,2] - image[:,:,0]) > 20
        mask = greenmask & \
                bluemask & \
                whiteremovemask & \
                brownremovemask & \
                blackmask

        # pepper
        greenmask = image[:, :, 1] > 90
        bluemask = image[:, :, 2] < 130
        whiteremovemask = (image[:, :, 1] - image[:, :, 2]) > 90
        brownremovemask = (image[:, :, 0] - image[:, :, 1]) > 80
        blackmask = (image[:, :, 2] - image[:, :, 0]) > 20
        mask = greenmask & \
            bluemask & \
            whiteremovemask & \
            brownremovemask & \
            blackmask
        '''
        # Mother of Thousands
        greenmask = image[:, :, 1] > 100
        bluemask = image[:, :, 2] < 130
        whiteremovemask = (image[:, :, 1] - image[:, :, 2]) > 60
        brownremovemask = (image[:, :, 0] - image[:, :, 1]) > 200
        blackmask = (image[:, :, 2] - image[:, :, 0]) > 40
        mask = brownremovemask & blackmask & bluemask & greenmask & whiteremovemask

        '''
        #passion flower
        greenmask = image[:, :, 1] > 100
        bluemask = image[:,:,2] < 180
        whiteremovemask = (image[:,:,1] - image[:,:,2]) > 20
        whiteremovemask2 = (image[:,:,1] > image[:,:,2])
        brownremovemask = (image[:,:,1] - image[:,:,0]) > 0
        mask = greenmask & \
                bluemask & \
                whiteremovemask & \
                brownremovemask & \
                whiteremovemask2
        '''

        fillimopen = ndimage.binary_fill_holes(mask)
        fillimopen = ndimage.binary_closing(mask)
        return fillimopen

    except Exception as err:
        print("Unexpected error when masking.")
        traceback.print_tb(err.__traceback__)
        workbook.close()
        sys.exit()


###########################
## START OF MAIN PROCEDURE
###########################

# stores the desired Excel save name
savename = "MotionSizeGrowth"
# creates the workbook file w/ savename
workbook = xlsxwriter.Workbook(savename + '.xlsx')

# reference containing all acceptable image formats for image analysis
extensions = ('.jpg', '.png')

# outlines format for cells heading data sets
headerformat = workbook.add_format(
    {
        "bold": 1,
        "border": 1,
        "align": "center",
        "valign": "vcenter",
        "fg_color": "yellow",
    }
)

start = time.time()

# changes directory to the desired folder
os.chdir(r"C:\Users\hpruitt\OneDrive - Institute for Advanced Learning and Research\Desktop\Cucumberpythiumtest2finalpart2")

pixelsPerPic = 0 # Set after first pic is collected tuple of dimensions (x, y, z = 3)

Motion_Worksheet = workbook.add_worksheet("Motion_Worksheet")
Size_Worksheet = workbook.add_worksheet("Size_Worksheet")
Growth_Worksheet = workbook.add_worksheet("Growth_Worksheet")

row = 0
col = 0
total_picture_count = 0

oldPic = None  # referenced when determining if we should skip the comparison calculation (for first plant of batch)

# cycles through each folder in the parent
for root, dirs, files in os.walk(os.getcwd()):

    for directory in sorted(dirs):

        print("Starting %s..." % directory)

        # Add header info
        Size_Worksheet.merge_range(row, col, row, col + 2, directory, headerformat)
        Size_Worksheet.write(row + 1, col, "Num", headerformat)
        Size_Worksheet.write(row + 1, col + 1, "Time", headerformat)
        Size_Worksheet.write(row + 1, col + 2, "Green", headerformat)

        Motion_Worksheet.merge_range(row, col, row, col + 2, directory, headerformat)
        Motion_Worksheet.write(row + 1, col, "Num", headerformat)
        Motion_Worksheet.write(row + 1, col + 1, "Time", headerformat)
        Motion_Worksheet.write(row + 1, col + 2, "Motion", headerformat)

        Growth_Worksheet.merge_range(row, col, row, col + 2, directory, headerformat)
        # Skip a row, this will be used later to store percent fluctuation between photos
        Growth_Worksheet.write(row + 2, col, "Num", headerformat)
        Growth_Worksheet.write(row + 2, col + 1, "Time", headerformat)
        Growth_Worksheet.write(row + 2, col + 2, "Green Change", headerformat)
        Growth_Worksheet.set_column(col + 2, col + 2, 14)

        row += 2

        # reset the counts for the growth error calculation
        directoryPicCount = 0
        flux = 0

        # cycle for each image in the folder
        for file in sorted(os.listdir(directory)):
            # splits the end of the path to see if the file is one of
            # the desired file types in the 'extensions' list
            ext = os.path.splitext(file)[-1].lower()
            if ext in extensions:

                total_picture_count += 1
                directoryPicCount += 1
                newPic = imageio.imread(directory + "\\" + file)

                # Set pixelsPerPic, only do this for the first pic
                if pixelsPerPic == 0:
                    pixelsPerPic = newPic.shape[0] * newPic.shape[1] #newPic.shape is a tuple of (height, width, 3(RGB))

                # take out first line below to test speed change
                newIsolatedImage = Isolate_Green(newPic)

                # only evaluates for non-black images in processing
                if np.count_nonzero(newIsolatedImage) > 500:

                    # when reading the first picture, prevents a comparison
                    # attempt with another picture
                    if oldPic is None:
                        writeData(row, col, file, newIsolatedImage)
                    else:
                        writeData(row, col, file, newIsolatedImage, oldIsolatedImage)

                        # update variables for keeping up with average pixel flux percentage
                        flux += abs(np.count_nonzero(newIsolatedImage) - np.count_nonzero(oldIsolatedImage))

                    # add in to test speed change
                    oldIsolatedImage = newIsolatedImage

                    row += 1
                    oldPic = newPic

        print("Finished " + directory)

        # Write average pixel fluctuation percent
        # (This refers to the change in green pixel count between pics, as a percent of the total possible pixels)
        if directoryPicCount != 0: # Prevents divide by zero error if in empty folder
            averageFluctuation = flux / directoryPicCount
            percentFlux = "Percent green pixel flux: {:.2f} %".format(100 * averageFluctuation / pixelsPerPic)
            Growth_Worksheet.merge_range(1, col, 1, col + 2, percentFlux, headerformat)


        # updates variables for next image set
        col += 4
        row = 0
        directoryPicCount = 0
        oldPic = None


workbook.close()
print(f'Finished {total_picture_count} pictures in {int(time.time() - start)} seconds.')
