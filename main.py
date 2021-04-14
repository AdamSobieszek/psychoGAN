import sys
import os
sys.path.insert(0, os.getcwd()+"/stylegan2")  #Pozwala importować rzeczy z folderu stylegan
import numpy as np
import pandas as pd
import PIL.Image
from PIL import Image, ImageDraw
import imageio
import matplotlib.pyplot as plt
from generator import generator
def main():
    main_generator = generator(network_pkl_path="gdrive:networks/stylegan2-ffhq-config-f.pkl",
                               direction_path="stylegan2/stylegan2directions/dominance.npy", coefficient=1.5,
                               truncation=0.6, n_levels=3, n_photos=10, type_of_preview="manipulation",
                               result_dir="/results")
    main_generator.change_face()
    main_generator._generator__kwargs()
    Image.fromarray(main_generator._generator__generate_preview_face_manip(), "RGB").save('wynik.png')



main()