import numpy
from PIL import Image, ImageDraw, ImageChops

from os import listdir
from os.path import isfile, join

mypath = "D:/CT/up/reconstructed/"
file_prefix = "tomo_"

begin_idx = 0
end_idx = 2159

for z_idx in range(begin_idx,end_idx,2):
    print("idx:", z_idx)
    num1 = "00000" + str( z_idx )
    num2 = "00000" + str( z_idx +1)
    num3 = "00000" + str(int(z_idx / 2))
    filename1 = file_prefix + num1[-5:] + ".tif"
    filename2 = file_prefix + num2[-5:] + ".tif"
    filename3 = file_prefix + num3[-5:] + ".tif"
    img1 = Image.open(mypath + filename1 )
    img2 = Image.open(mypath + filename2 )
    #print("size:", img1.width, img1.height)
    small_img1 = img1.resize( (int(img1.width/2),int(img1.height/2)) )
    small_img2 = img2.resize((int(img1.width / 2), int(img1.height / 2)))

    new_img = Image.new("L", (small_img1.width,small_img1.height))
    for x in range(small_img1.width):
        for y in range(small_img1.height):
            val1 = small_img1.getpixel((x,y))
            val2 = small_img1.getpixel((x,y))
            val3 = int(( val1 + val2 ) / 512)
            #print(z_idx,x,y,val1, val2, val3)
            new_img.putpixel((x,y),val3)

    new_img.save( mypath + "small/" + filename3 )
    #print(img1.mode, img2.mode)
    
    #result = ImageChops.add( small_img1, small_img2, scale=2 )
    #result = Image.blend(small_img1, small_img2, 0.5)

    #result.save( mypath + "small/" + filename3 )
    #small_img1.save( mypath + "small/orig_" + filename1 )
    #small_img2.save(mypath + "small/orig_" + filename2)
