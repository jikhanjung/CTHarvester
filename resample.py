import numpy
from PIL import Image, ImageDraw, ImageChops

import os
from os import listdir
from os.path import isfile, join

mypath_format = "N:/CT data/20230906 yjoh/CO-{}/CO-{}_Rec/small/"
file_prefix_format = "CO-{}__rec"

begin_idx = 215
end_idx = 969

for i in range(2,4):
    for z_idx in range(begin_idx,end_idx,2):
        print("idx:", z_idx)
        num1 = "000000" + str( z_idx )
        num2 = "000000" + str( z_idx +1)
        num3 = "000000" + str(begin_idx+int((z_idx-begin_idx) / 2))
        filename1 = file_prefix_format.format(i) + num1[-8:] + ".bmp"
        filename2 = file_prefix_format.format(i) + num2[-8:] + ".bmp"
        filename3 = file_prefix_format.format(i) + num3[-8:] + ".bmp"
        img1 = Image.open(mypath_format.format(i,i) + filename1 )
        img2 = Image.open(mypath_format.format(i,i) + filename2 )
        #print("size:", img1.width, img1.height)
        small_img1 = img1.resize( (int(img1.width/2),int(img1.height/2)) )
        small_img2 = img2.resize((int(img1.width / 2), int(img1.height / 2)))

        new_img = Image.new("L", (small_img1.width,small_img1.height))
        for x in range(small_img1.width):
            for y in range(small_img1.height):
                val1 = small_img1.getpixel((x,y))
                val2 = small_img1.getpixel((x,y))
                val3 = round(( val1 + val2 ) / 2)
                #print(z_idx,x,y,val1, val2, val3)
                new_img.putpixel((x,y),val3)
        new_path = mypath_format.format(i,i) + "smaller/"
        if not os.path.exists(new_path):
            os.makedirs(new_path)
        new_img.save( new_path + filename3 )
        #print(img1.mode, img2.mode)
        
        #result = ImageChops.add( small_img1, small_img2, scale=2 )
        #result = Image.blend(small_img1, small_img2, 0.5)

        #result.save( mypath + "small/" + filename3 )
        #small_img1.save( mypath + "small/orig_" + filename1 )
        #small_img2.save(mypath + "small/orig_" + filename2)
