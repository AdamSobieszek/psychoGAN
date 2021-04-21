import csv
import numpy as np
import pandas as pd
import PIL.Image
from PIL import Image, ImageDraw
import cv2
import dnnlib
import dnnlib.tflib as tflib
import imageio
import matplotlib.pyplot as plt
from pathlib import Path
from pretrained_networks import load_networks

class generator():
    def __init__(self, network_pkl_path,direction_name,coefficient,truncation,n_levels,n_photos,type_of_preview,result_dir,generator_number):
        self.no_generator = generator_number
        self.coefficient = coefficient          # Siła manipluacji / przemnożenie wektora
        self.truncation = truncation            # Parametr stylegan "jak różnorodne twarze"
        self.n_levels = n_levels                # liczba poziomów manipulacji 1-3
        self.n_photos = n_photos                # Ile zdjęć wygenerować
        self.preview_face = np.array([])        # Array z koordynatami twarzy na podglądzie 1
        self.preview_3faces = np.array([])      # Array z koordynatami twarzy na podglądzie 3
        self.synthesis_kwargs = {}              # Keyword arguments które przyjmuje stylegan
        self.type_of_preview = type_of_preview  # Typ podglądu, wartości: "3_faces", "manipulation" w zależności od tego które ustawienia są zmieniane
        self.dir = {"results":          Path(result_dir+str(self.no_generator)),
                    "images":           Path(result_dir+str(self.no_generator)) / 'images',
                    "thumbnails":       Path(result_dir+str(self.no_generator)) / 'thumbnails',
                    "coordinates":      Path(result_dir+str(self.no_generator)) / 'coordinates',
                    "dominance":        Path("stylegan2/stylegan2directions/dominance.npy"),
                    "trustworthiness":  Path("stylegan2/stylegan2directions/trustworthiness.npy")}
        self.direction_name = direction_name.lower()            # Wybrany wymiar
        self.direction = np.load(self.dir["direction_name"])    # Wgrany wektor cechy
        for directory in self.dir.values():
            directory.mkdir(exist_ok=True, parents=True)
        self._G, self._D, self.Gs = load_networks(network_pkl_path)

    def refresh_preview(self):
        """Przełączniki co wywołać w zależności od wartości type_of_preview"""
        pass

    def __create_coordinates(self, n_photos):
        all_z = np.random.randn(n_photos, *self.Gs.input_shape[1:])
        all_w = self.__map_vectors(all_z)
        return self.__truncate_vectors(all_w)


    def change_face(self):
        if self.type_of_preview == "manipulation":
            self.preview_face = self.__create_coordinates(1)
        else:
            self.preview_3faces = self.__create_coordinates(3)

    def __save_image(self, face, face_no, condition):   #Dodać kilka folderów wynikowych
        image_pil = PIL.Image.fromarray(face,  'RGB')
        image_pil.save(
        self.dir["images"] / '{}{}cond{}.png'.format(face_no, self.dim,condition))
        Image.thumbnail().save(
        self.dir["thumbnails"] / '{}{}cond{}.png'.format(face_no, self.dim,condition))



    def generate(self):
        """Zapisuje wyniki, na razie n_levels=1 """
        minibatch_size = 8

        self.__set_synthesis_kwargs(minibatch_size)

        coeff = [i/self.n_levels*self.coefficient for i in range(-self.n_levels, self.n_levels)]

        for i in range(self.n_photos // minibatch_size +1): # dodajmy ładowanie w interfejsie
            all_w = self.__create_coordinates(minibatch_size)

            for k in coeff:

                manip_w = all_w.copy()

                for j in range(len(all_w)):
                    manip_w[j][0:8] = (manip_w[j] + k * self.direction)[0:8]

                manip_images = self.Gs.components.synthesis.run(manip_w,
                                                     **self.synthesis_kwargs)

                for j in range(len(all_w)):
                    self.__save_image(pos_images[j])
                    #pos_image_pil = PIL.Image.fromarray(pos_images[j], 'RGB') #Można pomyśleć nad funkcją zapisującą obraazki która będzie miała możliwość zapisywania full jakości i miniaturkowej jakości
                    #pos_image_pil.save(
                            #self.dir["images"]  / '{}cond{}.png'.format(i * minibatch_size +
                                                           #j, self.coefficient))

                    if i*minibatch_size + j < self.n_photos:
                        self.__save_image(manip_images[j])

            for j, (dlatent) in enumerate(all_w):
                #image_pil = PIL.Image.fromarray(image, 'RGB')
                #image_pil.save(self.dir["images"] / (str(i * minibatch_size + j) + '.png'))
                np.save(self.dir["coordinates"] / (str(i * minibatch_size + j) + '.npy'),
                    dlatent[0])

    def __generate_preview_face_manip(self):
        """Zwraca array ze zdjeciem, sklejonymi 3 twarzami: w środku neutralna, po bokach zmanipulowana"""
        self.__set_synthesis_kwargs(minibatch_size=3)
        all_w = self.preview_face.copy()

        all_w = np.array([all_w[0],all_w[0],all_w[0]])  # Przygotowujemy miejsca na twarze zmanipulowane

        # Przesunięcie twarzy o wektor (już rozwinięty w 18)
        all_w[0][0:8] = (all_w[0] - self.coefficient * self.direction)[0:8]
        all_w[2][0:8] = (all_w[2] + self.coefficient * self.direction)[0:8]

        all_images = self.Gs.components.synthesis.run(all_w, **self.synthesis_kwargs)

        return np.hstack(all_images)

    def __generate_preview_3faces(self):
        """__generate_preview_face_manip tylko że używa zmiennej preview_3faces zamiast preview_face"""
        self.__set_synthesis_kwargs(minibatch_size=3)
        all_w = self.preview_3faces.copy()

        all_images = self.Gs.components.synthesis.run(all_w, **self.synthesis_kwargs)

        return np.hstack(all_images)

    def __tile_vector(self, faces_w):
        """Przyjmuje listę 512-wymierowych wektorów twarzy i rozwija je w taki które przyjmuje generator"""
        return np.array([np.tile(face, (18, 1)) for face in faces_w])

    def __generate_preview_face_face_3(self):
        """__generate_preview_face_manip tylko że używa zmiennej preview_3faces zamist preview_face"""

    def __map_vectors(self, faces_z):
         """Przyjmuje array wektorów z koordynatami twarzy w Z-space, gdzie losowane są wektory,
         zwraca array przerzucony do w-space, gdzie dzieje się manipulacja"""
         return self.Gs.components.mapping.run(faces_z, None)

    def __truncate_vectors(self, faces_w):
        """Zwraca wektory z faces_w przesunięte w kierunku uśrednionej twarzy"""
        w_avg = self.Gs.get_var('dlatent_avg')
        return w_avg + (faces_w - w_avg) * self.truncation

    def __set_synthesis_kwargs(self,minibatch_size = 3):
        """Za pierwszym razem tworzy keyword arguments do gnereowania,
        następnie może być użyta do zienienia minibatch_size"""
        if len(self.synthesis_kwargs)==0:
            Gs_syn_kwargs = dnnlib.EasyDict()
            Gs_syn_kwargs.output_transform = dict(func=tflib.convert_images_to_uint8,
                                                  nchw_to_nhwc=True)
            Gs_syn_kwargs.randomize_noise = False
            self.synthesis_kwargs = Gs_syn_kwargs

        Gs_syn_kwargs.minibatch_size = minibatch_size