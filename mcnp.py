# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 19:55:23 2017

@author: hjaderstrom
"""

import numpy as np
from scipy.optimize import curve_fit
import os
import shutil
from com.canberra.datasources.spectroscopy.cam import ParameterCodes, Datasource
from com.canberra.spectroscopy.calibrations import Fwhm
from physpy.CAM.utilities import calibration_data, CalibrationDataOptions
import physpy.CAM.CAM as cam


class MCNP(object):
    """
    This is supposed to be the main MCNP class that will handle everything in
    regards to manipulating MCNP output files
    It's quick and dirty right now but should be improved as we go along.
    Perferably using some third party tool to parse the output file since that
    will be more robust than what we can program.
    """
    def __init__(self, output_file):
        """

        """
        self.output_file_name = output_file
        self.f8tallies = {}
        if self.output_file_name != None:
            """
            dealing with output files goes here
            """
            with open(self.output_file_name) as outfile:
                tally = f8tally(outfile, 8)
                self.f8tallies[8] = tally


    def add_f8_tally_to_datasource(self, ds, tally_number):
        if tally_number in self.f8tallies:
            tally = self.f8tallies[tally_number]
            tally.add_to_datasource(ds)
        else:
            raise ValueError('Incorrect tally number')

class f8tally(object):
    def __init__(self,input=None, tally_number=0, ignore_lost_particles=False):
        self.bins = np.empty(0)
        self.efficiencies = np.empty(0)
        self.uncertainties = np.empty(0)
        self.tallyNumber = tally_number
        self.particeType = 0
        self.NPS = 0
        self.cell = 0
        self.run_time = 0.0

        if input is not None:
            self.parsef8tally(input, tally_number, ignore_lost_particles)

    def parsef8tally(self, input, tally_number, ignore_lost_particles):
        """
        Parses an f8 tally from input. Input needs to give lines formated as
        MCNP f8 tallies when iterated over. tally number specifies which tally is searched for.
        If there are multiple dumps the function will return the last dump.
        The MCNP format can vary a lot and this function has been tested for quite a number of files but it
        could still run into cases where it will fail. Tested with MCNPX and MCNP-CP files.

        if the number of particles is 1000000000 or more the f8tally section of the
        MCNP output file doesnt contain the number of particles and NPS gets set to
        -1
        """
        number_of_dumps = 0
        for line in input:
            if line.startswith('1tally') and 'fluctuation' not in line:
                parts = line.split()
                if (int(parts[1]) == tally_number or tally_number == 0) and 'print table' not in line:
                    number_of_dumps += 1
            if '      run terminated because' in line and 'particles got lost.' in line:
                lost_particles = int(' '.join(line.split()).split(' ')[3])
                if lost_particles > 0 and not ignore_lost_particles:
                    raise ValueError(f'{lost_particles} lost particles')
            if 'computer time =' in line:
                self.run_time = int(float(' '.join(line.split()).split(' ')[3])*60)
            if '      run terminated when' in line:
                self.NPS = int(line[25:36])

        counter = 0
        input.seek(0)
        for line in input:
            if line.startswith('1tally') and 'fluctuation' not in line:
                parts = line.split()
                if (int(parts[1]) == tally_number or tally_number == 0) and 'print table' not in line:
                    counter += 1
                    if counter == number_of_dumps:
#                        if len(parts)>4:
#                            self.NPS = int(parts[4])
#                        else:
#                            if parts[3][1] != '*':
#                                self.NPS = int(parts[3][1:])
#                            else:
#                                # if the number of particles are larger than
#                                # 1000000000 the f8tally section sets the number
#                                # of particles to **********
#                                self.NPS = -1
                        parts = input.readline().split()
                        if not parts[2].endswith('8'):
                            continue
                        self.tallyNumber = int(parts[2])
                        temp = input.readline()
                        self.particeType = []
                        if 'photons' in temp:
                            self.particeType.append('photons')
                        if 'electrons' in temp:
                            self.particeType.append('electrons')
                        while not temp.startswith(' cell'):
                            temp=input.readline()
                        parts = temp.split()
                        self.cell = int(parts[1])
                        while not 'energy' in temp:
                            temp = input.readline()
                        x = []
                        y = []
                        uncertainties = []
                        parts = input.readline().split()
                        while not parts[0] == 'total':
                            x.append(float(parts[0]))
                            y.append(float(parts[1]))
                            uncertainties.append(parts[2])
                            parts = input.readline().split()
                        self.bins = np.array(x,dtype=np.float64)
                        self.efficiencies = np.array(y,dtype=np.float64)
                        self.uncertainties = np.array(uncertainties,dtype=np.float64)
                        return 1
        self.bins = np.empty(0)
        self.efficiencies = np.empty(0)
        self.uncertainties = np.empty(0)
        self.tallyNumber = 0
        self.particeType = 0
        self.NPS = 0
        self.cell = 0

        return 0


    def efficiency_bin(self,binnumber):
        """
        Returns the efficiency for bin with number number
        returns -1 if number is larger than the number of bins
        """
        if binnumber > len(self.efficiencies):
            return -1
        number = int(binnumber)
        return self.efficiencies[number]

    def uncertainty_bin(self,number):
        """
        Returns the uncertainty for bin with number number
        returns -1 if number is larger than the number of bins
        """
        if number > len(self.uncertainties):
            return -1
        return self.uncertainties[int(number)]


    def efficiency(self,energy):
        """
        returns the efficiency for the bin containing energy
        the upper limit is inclusive
        returns -1 if energy is higher then the energy of the highest bin
        """
        binNumber = self.bin_number(energy)
        if binNumber == -1:
            return binNumber
        return self.efficiencies[binNumber]

    def bin_number(self,energy):
        """
        returns the bin number for the bin containing energy
        the upper limit is inclusive
        returns -1 if energy is higher then the energy of the highest bin
        """
        energy = float(energy)
        maxenergy = self.maximum_energy()
        if not 0 < energy < maxenergy:
            raise ValueError('energy has to be between 0 and {:f}'.format(
            maxenergy))
        binNumber=0
        for binEnergy in self.bins:
            if binEnergy > energy:
                break
            binNumber+=1
        return binNumber


    def uncertainty(self,energy):
        """
        returns the uncertainty for the bin containing energy
        the upper limit is inclusive
        returns -1 if energy is higher then the energy of the highest bin
        """
        binNumber = self.bin_number(energy)
        if binNumber == -1:
            return binNumber
        return self.uncertainties[binNumber]

    def total_efficiency(self):
        """
        returns the total efficiency for the f8 tally
        the bin containing energy 0 is not counted in the total efficiency
        """

        binnumber = 0

        while self.bins[binnumber] <= 0:
            binnumber += 1

        binnumber += 1

        if len(self.efficiencies) > binnumber:
            return np.sum(self.efficiencies[binnumber:])

        return 0

    def total_efficiency_uncertainty(self):
        """
        returns the uncertainty of the total efficiency for the f8 tally
        the bin containing energy 0 is not counted in the total efficiency
        uncertainty
        """
        binnumber = 0
        uncertainty = 0

        while self.bins[binnumber] <= 0:
            binnumber += 1

        binnumber += 1
        if len(self.efficiencies) > binnumber:
            for eff in self.efficiencies[binnumber:]:
                uncertainty += (eff*self.uncertainties[binnumber]) ** 2
                binnumber += 1

        totalEfficiency = self.total_efficiency()
        if totalEfficiency == 0:
            uncertainty = 0
        else:
            uncertainty = (uncertainty ** 0.5)/totalEfficiency
        return uncertainty

    def maximum_energy(self):
        """
        returns the maximum energy of the tally.
        """
        return self.bins[len(self.bins)-1]

    def __repr__(self):
        return 'f8Tally'

    def __str__(self):
        return 'f8tally tally number: {:d}\nnumber of bins: {:g}\n\
        maximum bin energy: {:g} MeV\nparticle type: {:s} \n\
        number of particles: {:d} \ncell number: {:d}'.format(self.tallyNumber, len(self.bins),
                                                              self.bins[len(self.bins)-1], self.particleType, self.NPS,
                                                              self.cell)

    def CAMfile(self, filename, skip_bins=0, isNaI=False, weight=1.0):
        """
        returns cam file of the f8 tally, if the numbers of bins are not
        skips first number of bins (the 0 energy results that MCNP adds to the output)
        :return:
        """

        # check if the bins are equidistant
        bin_distance = self.bins[1] - self.bins[0]
        equidistant = True
        # tolerance = 1e-10
        for i in range(len(self.bins) - 1):
            temp = self.bins[i + 1] - self.bins[i]
            tolerance = np.abs(self.bins[i + 1] / 1000)
            if not temp - tolerance < bin_distance < temp + tolerance:
                equidistant = False
                break
        if not equidistant:
            raise RuntimeError('Tally have varying bin sizes')
        if len(self.bins) > 32769:
            raise RuntimeError('Number of bins is larger than 32768')
        binsizes = [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]
        for binsize in binsizes:
            if len(self.bins) <= binsize + 1:
                number_of_bins = binsize
                break

        ds = cam.createCnf(self.normalize(weight)[1:], filename, number_of_bins, skip_bins=skip_bins, isNaI=isNaI)
        return ds

    def normalize(self, weight=1.0):
        """
        Returns a numpy array with the efficiency multiplied by the number of particles.
        :return: numpy array
        """
        return np.rint(self.efficiencies * self.NPS / weight).astype(np.int)

    def add_to_datasource(self, ds):

        # check if the bins are equidistant
        bin_distance = self.bins[1] - self.bins[0]
        equidistant = True
        tolerance = 1e-10
        for i in range(len(self.bins) - 1):
            temp = self.bins[i + 1] - self.bins[i]
            if not temp - tolerance < bin_distance < temp + tolerance:
                equidistant = False
                break
        if not equidistant:
            raise RuntimeError('Tally have varying bin sizes')
        if len(self.bins) > 32769:
            raise RuntimeError('Number of bins is larger than 32768')
        binsizes = [512,1024,2048,4096,8192,16384,32768,65536]
        for binsize in binsizes:
            if len(self.bins) <= binsize + 1:
                number_of_bins = binsize
                break

        spectrum = self.normalize()[1:] + np.array(ds.getSpectrum())
        ds.setParameter(ParameterCodes.CAM_L_CHANNELS, number_of_bins)
        ds.setSpectrum(list(np.array(spectrum,dtype=np.int)))


class F8star_tally:
    def __init__(self, filename, tally_number):
        self.nps = -1
        self.energy_deposited = -1
        self.relative_uncertainty = -1
        self.tfc_nps = []
        self.tfc_mean = []
        self.tfc_error = []
        self.tfc_vov = []
        self.tfc_slope = []
        self.tfc_fom = []
        tally_found = False
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith('1tally'):
                    parts = line.split()
                    if parts[1] in 'fluctuation':
                        line = file.readline()
                        line = file.readline()
                        parts = line.split()
                        tfc_found = False
                        position = -1
                        if tally_number == int(parts[1]):
                            tfc_found = True
                            position = 0
                        elif len(parts) > 2 and tally_number == int(parts[3]):
                            tfc_found = True
                            position = 1
                        elif len(parts) > 4 and tally_number == int(parts[5]):
                            tfc_found = True
                            position = 2
                        if tfc_found:
                            self._read_tfc(file, position)
                        else:
                            while line != '\n':
                                line = file.readline()
                        line = file.readline()
                        if 'tally' in line:
                            parts = line.split()
                            if tally_number == int(parts[1]):
                                tfc_found = True
                                position = 0
                            elif len(parts) > 2 and tally_number == int(parts[3]):
                                tfc_found = True
                                position = 1
                            elif len(parts) > 4 and tally_number == int(parts[5]):
                                tfc_found = True
                                position = 2
                            if tfc_found:
                                self._read_tfc(file, position)

                    elif int(parts[1]) == tally_number:
                        tally_found = True
                        self.nps = int(parts[4])
                        line = file.readline()
                        parts = line.split()
                        if '8*' not in parts[2]:
                            raise ValueError(f'Tally {tally_number} is not an F8* energy deposition tally')
                        while not line.startswith(' cell'):
                            line = file.readline()
                        line = file.readline()
                        parts = line.split()
                        self.energy_deposited = float(parts[0])
                        self.relative_uncertainty = float(parts[1])

        if not tally_found:
            raise ValueError(f'Tally {tally_number} was not found in {filename}.')

    def _read_tfc(self, iostream, position):
        line = iostream.readline()
        while True:
            line = iostream.readline()
            parts = line.split()
            self.tfc_nps.append(int(parts[0]))
            self.tfc_mean.append(float(parts[1 + position * 5]))
            self.tfc_error.append(float(parts[2 + position * 5]))
            self.tfc_vov.append(float(parts[3 + position * 5]))
            self.tfc_slope.append(float(parts[4 + position * 5]))
            self.tfc_fom.append(float(parts[5 + position * 5]))
            if self.tfc_nps[-1] == self.nps:
                break

        self.tfc_nps = np.array(self.tfc_nps)
        self.tfc_mean = np.array(self.tfc_mean)
        self.tfc_error = np.array(self.tfc_error)
        self.tfc_vov = np.array(self.tfc_vov)
        self.tfc_slope = np.array(self.tfc_slope)
        self.tfc_fom = np.array(self.tfc_fom)

    def __str__(self):
        text = f'{self.energy_deposited} {self.relative_uncertainty}\n'
        if len(self.tfc_nps) > 0:
            text += '         nps    mean    error   vov   slope   fom\n'
            for i in range(len(self.tfc_nps)):
                text += f'{self.tfc_nps[i]:>12} {self.tfc_mean[i]:10.5g} {self.tfc_error[i]:6.4} {self.tfc_vov[i]:6.4} {self.tfc_slope[i]:>4} {self.tfc_fom[i]:>7}\n'
        return text


def replace_line(filename, identifier, new_line):
    """replaceLine(filename,identifier,new_line)

    Replaces a line in filename that starts with identifier with the string newString
    """
    temp_name = filename + "_temp"
    try:
        file = open(filename, 'r')
        temp = open(temp_name, 'w')
    except IOError:
        return None
    for line in file:
        if line.startswith(identifier):
            line = new_line
        temp.writelines(line)

    file.close()
    temp.close()
    shutil.copy(temp_name, filename)
    os.remove(temp_name)


def convert_geb_to_sqrt(a, b):
    return a*1000.0, b*1000.0**0.5


def convert_sqrt_to_geb(a, b):
    return a/1000.0, b/1000.0**0.5


def __geb_fit(x, *params):
    a, b, c = params
    return a + b*np.sqrt(x + c*x**2)


def extract_geb_from_datasource(ds):
    # TODO add docstring
#    for calibration in ds.calibrations:
#        if isinstance(calibration, Fwhm):
    energies, fwhms, uncertainties = calibration_data(ds, CalibrationDataOptions.SHAPE)
    energies = energies/1000.0
    fwhms = fwhms/1000.0
    uncertainties = uncertainties/1000.0
    if any(uncertainties == 0.0):
        for i in range(len(uncertainties)):
            uncertainties[i] = fwhms[i]/100.0 if uncertainties[i] == 0.0 else uncertainties[i]
    (a, b, c), cov = curve_fit(__geb_fit, energies, fwhms, [0, 0, 0], uncertainties, True, maxfev=10000)
    return a, b, c


def __main():
    # with Datasource() as ds:
    #     ds.open(r'C:\Projects\CEA ML\data\Simulations\6230\2 spacers\6230_2_spacers.cnf')
    #     a, b, c = extract_geb_from_datasource(ds)
    #     print('a={}, b={}, c={}, fwhm at 1332={}'.format(a, b, c, __geb_fit(1.332, *(a, b, c))))
    #     ds.close()

    f8star = F8star_tally(r'C:\Projects\instadose\PTB\instadose3_PTB_144_short.o', 278)
    print(f8star)


if __name__ == '__main__':
    __main()
