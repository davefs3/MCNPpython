# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 14:31:08 2013

@author: hjaderstrom
"""

import struct
import math
import numpy as np


class VacuumEfficiency:
    """ class to hold the data for the vacuum efficiency for a parfile

    """ 
    def __init__(self):    
        self.energy = None
        self.minPhi = None
        self.minR = None
        self.maxPhi = None
        self.maxR = None
        self.stepPhi = None
        self.stepR = None
        self.vacuumEfficiency = np.array([0])


class Parfile:
    """ The class to read the an ISOCS parfile.

        Use parseParFile method to parse the data from an existing par file.
        Use the writeParFile method to write the data to a new par file in a format
        that can be used by ISOCS.
    """ 
    def __init__(self, filename):
        self.vacuumEfficiencies = []
        self.__parse_parfile(filename)

    def __parse_parfile(self, filename):
        """ Parses the data in the file parFileName

        populates the minimumEnergy, maximumEnergy and numberOfEnergies variables
        The data associated with the vacuum efficiency for an energy is stored in a 
        class called vacuum efficiency which have energy, minPhi, maxPhi, minR, maxR
        stepPhi, stepR and vacuumEfficiency[][] where the last stores the vacuum efficiencies
        for the all data points in space.
        """ 
        try:
            file = open(filename, 'rb')
        except IOError:
            return
        content = file.read()
        self.minimumEnergy, self.maximumEnergy, self.numberOfEnergies = struct.unpack("ddh", content[:18])
        position = 18
        energies = struct.unpack("d" * self.numberOfEnergies, content[position:(position + 8 * self.numberOfEnergies)])
        position = position + 8 * self.numberOfEnergies
    
        for i in range(len(energies)):
            position = 302 + 20 * i
            position = 318 + 20 * i
            temp = struct.unpack("q", content[position:(position+8)])
            position = int(''.join(map(str, temp)))
          
            VE = VacuumEfficiency()
            VE.energy = energies[i]
            numberOfPhi, numberOfR, VE.minPhi, VE.maxPhi, VE.stepPhi, VE.minR, VE.maxR, VE.stepR = struct.unpack("hhffffff",content[position:position+28])
            position += 28
            VE.vacuumEfficiency = np.zeros((numberOfR,numberOfPhi))
            for i in range(numberOfR):
                for j in range(numberOfPhi):
                    temp=struct.unpack("h",content[position:position+2])
                    position+=2
                    temp=float(''.join(map(str,temp)))
                    VE.vacuumEfficiency[i][j] = math.pow(10, -temp/1000.0)
            self.vacuumEfficiencies.append(VE)
        
        file.close()

    def write_parfile(self, filename):
        """ Writes the data of the parfile to fileName in such a way that it can 
            be used by ISOCS/LabSOCS
        
        """
        try:
            file = open(filename, 'wb')
        except IOError:
            return
        s = struct.pack('ddh', self.minimumEnergy, self.maximumEnergy, self.numberOfEnergies)
        file.write(s)
        for VE in self.vacuumEfficiencies:
            s = struct.pack('d',VE.energy)
            file.write(s)
        
        # The parfile requires that the next data is written at position 300        
        file.seek(300)
        
        s = struct.pack('h', len(self.vacuumEfficiencies))
        file.write(s)
        
        offset = []
        counter = 0

        for VE in self.vacuumEfficiencies:
            file.seek(302+20*counter)
            s=struct.pack('dd',math.exp(VE.minR),math.exp(VE.maxR))
            file.write(s)
            counter += 1
        
        #The ISOCS trick, this needs to start at 2000 or ISOCS wont be able to use the file.
        file.seek(2000)

        for VE in self.vacuumEfficiencies:
            offset.append(file.tell())
            s = struct.pack('hhffffff',len(VE.vacuumEfficiency[0]),len(VE.vacuumEfficiency),VE.minPhi,VE.maxPhi,VE.stepPhi,VE.minR,VE.maxR,VE.stepR)
            file.write(s)
            for temp1 in VE.vacuumEfficiency:
                for temp2 in temp1:
                    if temp2 <= 0:
                        print("warning: efficiency <= 0, setting it to 1")
                        s = struct.pack('h', (0))
                        file.write(s)
                    else:
                        s = struct.pack('h', (iround(-1000*math.log10(temp2))))
                        file.write(s)
           
        counter = 0
        for value in offset:
            file.seek(318+20*counter)
            s = struct.pack('l', value)
            file.write(s)
            counter += 1

        return

    def get_vacuum_efficiency(self, energy):
        """ Returns the Vacuum Efficiency for energy
            if energy is not in the parfile than None is returned        
        """
        for VE in self.vacuumEfficiencies:
            if VE.energy == energy:
                return VE
        return None
        
    def create_points_file(self, filename, min_angle=0, max_angle=180, min_radius=0, max_radius=600000):
        """ creates fileName with the points that have non-zero efficiency (outside
        the endcap) the format of the file is r theta phi
        """
        try:
            file = open(filename, 'w')
        except IOError:
            return 1
                
        VE = self.vacuumEfficiencies[0]
        numberOfPhi = len(VE.vacuumEfficiency[0])
        numberOfR = len(VE.vacuumEfficiency)
        for r in range(numberOfR):
            for phi in range(numberOfPhi):
                if(VE.vacuumEfficiency[r][phi] < 1):
                    radius = math.exp(r*VE.stepR)
                    angle = math.degrees(phi*VE.stepPhi)
                    if(min_radius <= radius <= max_radius and min_angle-0.00001 <= angle <= max_angle + 0.00001):
                        line = '{:.3f}\t{:.3f}\t0.000\n'.format(radius, angle)
                        file.write(line)
                    
        file.close()
        return 0

    def create_energy_file(self, filename):
        """ creates fileName with the points that have non-zero efficiency (outside
        the endcap) the format of the file is r theta phi
        """
        try:
            file = open(filename, 'w')
        except IOError:
            return 1

        for VE in self.vacuumEfficiencies:
            file.write(str(VE.energy) + '\n')
                
        return 0


def iround(x):
    """iround(number) -> integer
    Round a number to nearest integer."""
    y = round(x) - .5
    return int(y) + (y > 0)
