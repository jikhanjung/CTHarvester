import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

mypath = 'D:/RSES_SamLee_Lipopora_lissaANU59521J/tomoLoRes_roi_nc/LowResdata8/'

depth = 1109
width = 656
height = 656

for z_idx in range(0,depth,2):
    num1 = "00000" + str( z_idx )
    num2 = "00000" + str( z_idx +1)
    num3 = "00000" + str(int(z_idx / 2))
    filename1 = num1[-5:] + ".tif"
    filename2 = num2[-5:] + ".tif"
    filename3 = num3[-5:] + ".tif"
    img1 = Image.open(mypath + filename1 )
    img2 = Image.open(mypath + filename2 )
    small_img1 = img1.resize( (int(width/2),int(height/2)) )
    small_img2 = img2.resize((int(width / 2), int(height / 2)))
    result = ImageChops.add( small_img1, small_img2, scale=2 )

    result.save( mypath + "small/" + filename3 )
    #small_img1.save( mypath + "small/orig_" + filename1 )
    #small_img2.save(mypath + "small/orig_" + filename2)
