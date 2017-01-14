import numpy as np
import csv
import matplotlib.pyplot as plt
from kernelPCA_Class import Gaussian_Kernel
from sklearn.decomposition import PCA
import pdb
from random import shuffle
from skimage.util import random_noise


class kPCA_usps():
    def __init__(self):
        self.name = 'usps_example'
        self.data_labels, self.data = self.readData('USPS_dataset//zip.train')
        self.training_images = self.extractDataSets(self.data, self.data_labels, 300)
        self.test_labels, self.test_images = self.readData('USPS_dataset//zip.test')
        # self.test_images = self.extractDataSets(self.test_data, self.test_labels, 50)
        # self.test_images=self.shuffleListAndExtract(self.test_images,50)
        #self.gaussian_images = self.addGaussianNoise(np.copy(self.test_images))
        self.gaussian_images = self.addGaussianNoise_skimage(np.copy(self.test_images), -1, 0.25)
        self.speckle_images = self.addSpeckleNoise(np.copy(self.test_images))
        self.kPCA_gaussian = Gaussian_Kernel()
        self.C = 0.5 * 256
        self.kGram = None
        self.norm_vec = None
        #self.kGram = np.loadtxt('kGram.txt')
        #self.norm_vec = np.loadtxt('normVec.txt')

    def addGaussianNoise_skimage(self, data, mean, var):
        noisy_images = []
        for img in data:
            target = np.reshape(img, [16, 16])
            noisy_img = random_noise(target, mode='gaussian', mean=mean, var=var)
            noisy_images.append(np.reshape(noisy_img, [256,]))
        return noisy_images

    def readData(self, filePath):
        labels = []
        images = []
        with open(filePath, 'r') as f:
            content = f.readlines()
            for index, pixels in enumerate(content):
                # split string of floats into array
                pixels = pixels.split()
                # the first value is the label
                label = int(float(pixels[0]))
                # the reset contains pixels
                pixels = -1 * np.array(pixels[1:],
                                       dtype=float)  # flips black => white so numbers are black, background white
                # Reshape the array into 16 x 16 array (2-dimensional array)
                labels.append(label)
                images.append(pixels)
        return np.asarray(labels), np.asarray(images)

    def extractDataSets(self, data, labels, nEach):
        # shuffleIndices = np.arange(data.shape[0])
        # shuffle(shuffleIndices)
        # data = data[shuffleIndices, :]
        numbers = 10
        number_label = np.ones((10, 1)) * (nEach - 1)
        retVal = np.zeros((nEach * numbers, data.shape[1]), dtype=float)
        count = 0
        for t, i in enumerate(labels):
            if (number_label[i] < 0):
                continue
            number_label[i] -= 1
            retVal[count, :] = data[t, :]
            count += 1
        return retVal

    def shuffleListAndExtract(self, list, noElements):
        noImages = list.shape[0]
        shuffleIndicies = np.arange(noImages)
        shuffle(shuffleIndicies)
        list = list[shuffleIndicies]
        list = list[:noElements]
        return list

    def addSpeckleNoise(self, images):
        noisy_images = []
        for image in images:
            p = 0.4
            pixels_speckle_noise_push = np.array(
                [np.random.choice([-1., num, 1.], p=[p / 2., 1 - p, p / 2.]) for num in image])
            noisy_images.append(pixels_speckle_noise_push)
        return noisy_images

    def addGaussianNoise(self, images):
        noisy_images = []
        for row in images:
            pixels = row
            '''add noise here '''
            mu = -1
            sigma = 0.5
            pixels_plus_noise = pixels + np.random.normal(loc=mu, scale=sigma, size=256)
            index = np.where(abs(pixels_plus_noise) > 1)
            pixels_plus_noise[index] = np.sign(pixels_plus_noise[index])
            noisy_images.append(pixels_plus_noise)
        return np.asarray(noisy_images)

    def display(self, images):
        for image in images:
            image = image.reshape((16, 16))
            plt.imshow(image, 'gray', interpolation='none')
            # plt.show()

    def catch_zero(self, gamma, z_init,counter):
        try:
            approx_z = self.kPCA_gaussian.approximate_z_single(gamma, z_init, self.training_images,
                                                               self.C, 256)
        except ValueError as e:
            counter += 1
            reset_z = self.gaussian_images[np.random.choice(self.gaussian_images.shape[0], size=1)]
            approx_z = self.catch_zero(gamma, np.matrix(reset_z),counter)

        return approx_z, counter

    def kernelPCA_gaussian(self, max_eigVec_lst, threshold, test_image,nIteration):
        # create Projection matrix for all test points and for each max_eigVec
        if self.kGram == None:
            self.kGram, self.norm_vec = self.kPCA_gaussian.normalized_eigenVectors(self.training_images, self.C)
            np.savetxt('kGram.txt', self.kGram)
            np.savetxt('normVec.txt', self.norm_vec)
        projection_kernel = self.kPCA_gaussian.projection_kernel(self.training_images, test_image, self.C)
        projection_matrix_centered = self.kPCA_gaussian.projection_centering(self.kGram, projection_kernel)
        result_lst = []
        for max_eigVec in max_eigVec_lst:
            print(max_eigVec)
            reconstructed_images = []
            projection_matrix = np.dot(projection_matrix_centered, self.norm_vec[:, :max_eigVec])
            # approximate input
            gamma = self.kPCA_gaussian.gamma_weights(self.norm_vec, projection_matrix, max_eigVec)
            # np.random.seed(20)
            # z_init = np.random.rand(self.nClusters * self.nTestPoints, self.nDim)
            z_init = np.copy(test_image)  # according to first section under chapter 4,
            old_old=np.copy(test_image)
            # in de-noising we can use the test points as starting guess
            # for tp in range(len(self.test_images)):
            max_distance = 10
            count = 0
            reSampledStart=0
            while max_distance > threshold and count<nIteration:
                approx_z, reSampledStart = self.catch_zero(gamma, z_init,reSampledStart)
                max_distance = (np.linalg.norm(z_init - approx_z, axis=1, ord=2))
                old_old=np.copy(z_init)
                z_init = np.copy(approx_z)
                count += 1
            print(max_distance)
            print(count)
            print(reSampledStart)
            reconstructed_images.append(z_init)
            result_lst.append(reconstructed_images)
        return result_lst


if __name__ == "__main__":
    usps = kPCA_usps()
    ax1 = plt.subplot(161)
    usps.display(usps.gaussian_images[30:31])
    plt.title('Original')
    print(usps.test_labels[0])
    max_eigVec_lst = [1, 4, 16, 64, 256]
    reconstructed_images = usps.kernelPCA_gaussian(max_eigVec_lst, 10**(-3), np.matrix(usps.gaussian_images[30]),300)
    for i in range(5):
        ax2 = plt.subplot("16%d" % (i + 2))
        usps.display(reconstructed_images[i])
        plt.title('n_comp:%d' % max_eigVec_lst[i])
    plt.show()

