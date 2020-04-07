# -*- coding: utf-8 -*-
"""
Created on Tue Oct  1 13:19:26 2019

@author: HPersson
"""
import collections
import os
import numpy as np
import ctypes
import subprocess
import shutil
from abc import ABC, abstractmethod
from scipy.interpolate import CubicSpline
import isocs_utility_functions as utilities
import parfile
import experiment

class Detector(ABC):
    def __init__(self, serialnumber):
        """
        Abstract class that provides the basic functionallity for all
        detectors. Specific detector classes needs to implement all methods
        with the abstractmethod decorator

        This class cannot be instanciated

        If any of the implemented functions doesnt provide the desired behavior
        they need to be overridden.

        Parameters
        ----------
        serialnumber : string
            The serial number.

        Returns
        -------
        None.

        """
        self.serialnumber = serialnumber
        self.dimensions = collections.OrderedDict()
        self.header = None
        self.modelnumber = None

    def initial_detector_dimensions(self, init_sheet, standard_sheet):
        """
        Populate the detector dimensions with the default values from the
        standard config sheet and override with any detector specific
        values from the intialization sheet.

        Parameters
        ----------
        init_sheet : Sheet
            The initilization sheet.
        standard_sheet : Sheet
            The standard config sheet.

        Returns
        -------
        None.

        """
        self.dimensions = utilities.find_standard_detector_values(self.header, self.short_modelnumber, standard_sheet)
        self.holder_model = utilities.holder_model(init_sheet)
        self.endcap_model = utilities.endcap_model(init_sheet)
#        if self.holder_model is not '':
#            holder_dimensions = utilities.find_holder_values(self.holder_model, sheet)
#        if self.endcap_model is not '':
#            endcap_dimensions = utilities.find_endcap_values(self.endcap_model, sheet)
        value = utilities.ec_xtal_dist(init_sheet)
        if value > 0 and 'ec_xtal_dist' in self.dimensions:
            self.dimensions['ec_xtal_dist'] = (value  / 10.0, self.dimensions['ec_xtal_dist'][1])
        value = utilities.xtal_length(init_sheet)
        if value > 0 and 'xtal_len' in self.dimensions:
            self.dimensions['xtal_len'] = (value / 10.0, self.dimensions['xtal_len'][1])
        value = utilities.xtal_diameter(init_sheet)
        if value > 0 and 'xtal_rad' in self.dimensions:
            self.dimensions['xtal_rad'] = (value / 20.0, self.dimensions['xtal_rad'][1])
        value = utilities.front_dl(init_sheet)
        if value > 0.0 and 'front_dl' in self.dimensions:
            self.dimensions['front_dl'] = (value / 10.0, self.dimensions['front_dl'][1])
        value = utilities.side_dl(init_sheet)
        if value > 0.0 and 'side_dl' in self.dimensions:
            self.dimensions['side_dl'] = (value / 10.0, self.dimensions['side_dl'][1])
        value = utilities.well_depth(init_sheet)
        if value > 0.0 and 'well_depth' in self.dimensions:
            self.dimensions['well_depth'] = (value / 10.0, self.dimensions['well_depth'][1])
        value = utilities.well_diameter(init_sheet)
        if value > 0.0 and 'well_radius' in self.dimensions:
            self.dimensions['well_radius'] = (value / 20.0, self.dimensions['well_radius'][1])
        value = utilities.bevel_radius(init_sheet)
        if value > 0.0 and 'bevel_rad' in self.dimensions:
            self.dimensions['bevel_rad'] = (value / 10.0, self.dimensions['bevel_rad'][1])
        value = utilities.taper_radius(init_sheet)
        if value > 0.0 and 'taper_top' in self.dimensions:
            self.dimensions['taper_top'] = (value / 10.0, self.dimensions['taper_top'][1])
        value = utilities.taper_bottom(init_sheet)
        if value > 0.0 and 'taper_side' in self.dimensions:
            self.dimensions['taper_side'] = (value / 10.0, self.dimensions['taper_side'][1])
        self.measured_endcap_radius = utilities.measured_endcap_diameter(init_sheet) * 2.54 / 2.0


    def create_point_dcgfile(self, folder_name):
        """
        Creates the input file used by MakeDCGTools to generate the points
        file used for the loop during the characterization process

        Parameters
        ----------
        folder_name : string
            path to the folder where the file will be created.

        Returns
        -------
        dcg_filename : string
            The full path to the created file.

        """
        dcg_filename = os.path.join(folder_name, f'{self.serialnumber}.dcg')
        with open(dcg_filename, 'w') as dcg_file:
            text = [f'~cmd Pnt\n',
                    '~Pnt O=P SS=2.8 SC=20\n',
                    f'~serialnumber {self.serialnumber}\n',
                    f'~input_folder {folder_name}\n',
                    f'~output_folder {folder_name}\n',
                    f'~ErrFile {folder_name}\MakeDcgTools.err\n',
                    '~simtype full\n',
                    '~MuLibTot P:\ISOCSProduction\Codes\MakeDCGTools\mu_tot_01_8lb.txt\n',
                    '~MuLib P:\ISOCSProduction\Codes\MakeDCGTools\mu01_8lb.txt\n',
                    ]

            text = text + self.dcg_parameters()
            dcg_file.writelines(text)
            dcg_file.close()
        return dcg_filename

    def create_par_dcgfile(self, folder_name):
        """
        Creates the input file used by MakeDCGTools to generate the parfile

        Parameters
        ----------
        folder_name : string
            path to the folder where the file will be created.

        Returns
        -------
        dcg_filename : string
            The full path to the created file.

        """
        dcg_filename = os.path.join(folder_name, f'{self.serialnumber}_makepar.dcg')
        with open(dcg_filename, 'w') as dcg_file:
            text = [f'~cmd Grid\n',
                    '~Grid A\n',
                    f'~serialnumber {self.serialnumber}\n',
                    f'~input_folder {folder_name}\n',
                    f'~output_folder {folder_name}\n',
                    f'~ErrFile {folder_name}\MakeDcgTools.err\n',
                    '~simtype full\n',
                    '~MuLibTot P:\ISOCSProduction\Codes\MakeDCGTools\mu_tot_01_8lb.txt\n',
                    '~MuLib P:\ISOCSProduction\Codes\MakeDCGTools\mu01_8lb.txt\n',
                    ]

            text = text + self.dcg_parameters()
            dcg_file.writelines(text)
            dcg_file.close()
        return dcg_filename

    def mode(self, electrontrack):
        """
        Return the MODE card for MCNP simulations

        Parameters
        ----------
        electrontrack : bool
            If false the MODE in the MCNP will be P if True the MODE will be P E.

        Returns
        -------
        str
            The MODE card for MCNP.

        """
        if electrontrack:
            return 'MODE P E\n'
        return 'MODE P\n'

    def tally_energy(self, energy):
        """
        Return the E tally modifier card (Energy bins) for the MCNP simulation

        Parameters
        ----------
        energy : float
            The energy of the simulation.

        Returns
        -------
        str
            The E tally modifier card.

        """
        return f'E8   0 1.E-6 1.E-3 {energy/1000.0 - 0.0000199:.7f} 3I {energy/1000.0 + 0.0000201:.7f}\n'

    def world_cells(self, source, electrontrack):
        """
        Return the cell cards that consist of the air around the detector and
        source and the void

        Parameters
        ----------
        source : Source
            The source used for the MCNP simulation.
        electrontrack : bool
            If True electron importances will be included, if False they will not be included.

        Returns
        -------
        text : List
            List of cell card.

        """
        text = ['C World cells\n'
                f'89   3 -{source.air_density()} -99 #{self.endcap_boundary()} {source.cell_numbers()} {self.importance(electrontrack)} $ AIR SPHERE\n',
                f'99   0          99         {self.importance(electrontrack, void=True)}    $ VOID\n'
                ]
        return text

    def world_surfaces(self, source):
        """
        Return the surface card(s) that consist of world to void boundary

        Parameters
        ----------
        source : Source
            The source used for the MCNP simulation.

        Returns
        -------
        text : List
            List of surface card(s).

        """
        text = ['C World surfaces\n',
                f'99   SO {source.max_radius()}    $ SPHERE DEFINING THE BOUNDARY OF THE UNIVERSE\n'
                ]
        return text

    def importance(self, electrontrack, crystal=False, void=False):
        """
        Return the IMP part of the cell card for MCNP.

        Parameters
        ----------
        electrontrack : bool
            If True electron importances will be included, if false they will be excluded.
        crystal : bool, optional
            If true the electron importance will be set to 1, if not it will be 0. The default is False.
        void : bool, optional
            If True all importances will be set to 0. The default is False.

        Returns
        -------
        str
            The IMP part of the cell card.

        """
        if electrontrack:
            if crystal:
                return 'IMP:P=1 IMP:E=1'
            elif void:
                return 'IMP:P=0 IMP:E=0'
            else:
                return 'IMP:P=1 IMP:E=0'
        else:
            if void:
                return 'IMP:P=0'
            return 'IMP:P=1'

    def materials(self, source):
        """
        The materials card for MCNP.
        This function should be improved to read from a repository of
        materials and only add the material that are being used in the
        simulation.

        Parameters
        ----------
        source : Source
            The source used for the simulation.

        Returns
        -------
        text : List
            List of material cards.

        """
        text = ['M1    6000 1.0      $ Carbon (2.62 g/cc)\n',
                'M2    4000 1.0      $ Be (1.85 g/cc)\n',
                'M3    7000 0.785    $ vacuum (0.0000012 g/cc)\n',
                '      8000 0.211    $      \n',
                '     18000 0.004    $      \n',
                'M4   13000 1.0      $ Al (2.7 g/cc)\n',
                'M5   32000 1.0      $ Ge (5.35 g/cc)\n',
                'M6   82000 1.0      $ Pb (11.4 g/cc)\n',
                'M7   12000 1.0      $ Mg (1.74 g/cc)\n',
                'M8    1000 0.66667  $ Water 1.0 g/cm3\n',
                '      8000 0.33333\n',
                'M9    6000 0.40   $ Delrin 1.45 g/cm3\n',
                '      1000 0.07\n',
                '      8000 0.53\n',
                'M10  29000 1.0      $ Cu (8.96 g/cc)\n',
                'M11   9000 0.6667   $ teflon (2.1 g/cc)\n',
                '      6000 0.3333   $      \n',
                'M12   8000 0.2273   $ Mylar/paper (1.4 g/cc)\n',
                '      6000 0.3636   $      \n',
                '      1000 0.4091   $      \n',
                'M13  74000 1.0      $ W (17 g/cc)\n',
                'M14   1000 -0.0706     $ Polycarbonate (used for FiltPap and AmCs spacer)\n',
                '      6000 -0.7892    $ 1.17 g/cm3    \n',
                '      8000 -0.1402                    \n',
                'M15   8000 -0.4556  $ Glass fiber   (used for FiltPap)\n',
                '     11000 -0.1156  $ 0.23 g/cm3     \n',
                '     14000 -0.3283                  \n',
                '     20000 -0.3283                  \n',
                'M16  24000 -0.19    $ Stainless steel\n',
                '     26000 -0.72    $ 7.8 g/cm3\n',
                '     28000 -0.09      \n',
                'M17   1000 0.0481   $ Kapton (2.1 g/cc)\n',
                '      6000 0.5775   $      \n',
                '      7000 0.0749   $      \n',
                '      8000 0.2995   $      \n',
                'M18   5000 -0.00930   $ Porous Glass according to N. Kasate (E&Z) (1.87 g/cc)\n',
                '      8000 -0.53720   $      \n',
                '      14000 -0.4535   $      \n',
                'M19   1000 0.0702   $ Acrylic (1.15 g/cc)\n',
                '      6000 0.5581   $\n',
                '      8000 0.3717   $\n',
                'M20   1000 0.1437   $ Polypropelene (0.91 g/cc)\n',
                '      6000 0.8563   $\n',
                'M22   5000 0.5     $ ceramic (2.0 g/cc approx.)\n',
                '      7000 0.5     $    \n',
                'M23   49000 1.0     $ Indium 7.31 g/cc \n',
                'M24   22000 1.0     $ Titanium 4.506 g/cc \n',
                'M25   3000 -0.0081  $ CLLBC 4.08 g/cm3 \n',
                '      17000 -0.0341 \n',
                '      35000 -0.4842 \n',
                '      55000 -0.311  \n',
                '      57000 -0.1626  \n'
                ]
        return text

    def corners(self, full_detector=True):
        """
        Calculate the corners of the detector, this is used for the directional
        bias algorithm in MCNP. If full_detector is True the corners are the corners
        of the endcap and the entire detector is illuminated. This is required
        for the total efficiency to be correct. Setting full_detector to false,
        will only illuminate the crystal which should make the simulation run
        faster but it the total efficiency will not be correct.

        Parameters
        ----------
        full_detector : bool, optional
            If True the corners of the end cap are returned, if false the corners of the crystal. The default is True.

        Returns
        -------
        corners : List
            List of np.arrays with the cartesian coordinates of the corners of the detector .

        """
        if full_detector:
            corners = [np.array([-self.dimensions['ec_rad'], 0.0, 0.0]),
                       np.array([self.dimensions['ec_rad'], 0.0, 0.0]),
                       np.array([-self.dimensions['ec_rad'], 0.0, self.dimensions['ec_len']]),
                       np.array([self.dimensions['ec_rad'], 0.0, self.dimensions['ec_len']])
                       ]
        else:
            corners = [np.array([-self.dimensions['xtal_rad'], 0.0, self.dimensions['ec_xtal_dist']]),
                       np.array([self.dimensions['xtal_rad'], 0.0, self.dimensions['ec_xtal_dist']]),
                       np.array([-self.dimensions['xtal_rad'], 0.0, self.dimensions['ec_xtal_dist'] + self.dimensions['xtal_len']]),
                       np.array([self.dimensions['xtal_rad'], 0.0, self.dimensions['ec_xtal_dist'] + self.dimensions['xtal_len']])
                       ]
        return corners

    def center(self, full_detector=True):
        """
        Return the center of the detector. If full detector is True the center is
        the center of the endcap, if full_detector is false the center is the
        center of the crystal.

        Parameters
        ----------
        full_detector : bool, optional
            If True the center is the center of the endcap, if false the center
            is the center of the crystal. The default is True.

        Returns
        -------
        center : np.array
            Numpy array with the cartesian coordinates of the center.

        """
        if full_detector:
            center = np.array([0.0, 0.0, self.dimensions['ec_len']/2.0])
        else:
            center = np.array([0.0, 0.0, self.dimensions['xtal_ec_dist'] + self.dimensions['xtal_len']/2.0])
        return center

    def create_input_file(self, source, file_name, full_detector=True, electrontrack=False):
        """
        Create the MCNP input file.

        Parameters
        ----------
        source : Source
            The source used for the simulation.
        file_name : string
            The name of the input file that will be created.
        full_detector : bool, optional
            If True the directional bias algorithm will emit photons in a solid angle covering
            the entire endcap, if false the emitted photons will only cover the crystal
            Setting the full_detector to True is required for the total efficiency
            calculation to be correct. Setting it to False could speed up the simulation
            time. The default is True.
        electrontrack : bool, optional
            If true electron tracking will be used in the MCNP simulation,
            if false only photons will be tracked. The default is False.

        Returns
        -------
        None.

        """
        with open(file_name, 'w') as file:
            file.write(f'C  !Energy = {source.energy}\n')
            file.write(f'C  !Position = {source.position()}\n')
            file.write(f'C  !Weight = {source.weight(self, full_detector)}\n')
            file.write(f'C  !Type = {source.type}\n')
            file.write('C  **************************************************************\n')
            file.write('C    CELLS\n')
            file.write('C  **************************************************************\n')
            file.writelines(self.cells(source, electrontrack))
            file.writelines(source.cells(self, electrontrack))
            file.writelines(self.world_cells(source, electrontrack))
            file.write('C    ************************************************************\n')
            file.write('\n')
            file.write('C    ************************************************************\n')
            file.write('C    SURFACES\n')
            file.write('C    ************************************************************\n')
            file.writelines(self.surfaces())
            file.writelines(source.surfaces())
            file.writelines(self.world_surfaces(source))
            file.write('C    ************************************************************\n')
            file.write('\n')
            file.write('C    ************************************************************\n')
            file.write('C    SOURCE\n')
            file.write('C    ************************************************************\n')
            file.write(self.mode(electrontrack))
            file.writelines(source.source(self, full_detector))
            file.write('C    ************************************************************\n')
            file.writelines(source.transformation())
            file.write('C    ************************************************************\n')
            file.write('C    MATERIAL\n')
            file.write('C    ************************************************************\n')
            file.writelines(self.materials(source))
            file.write('F8:P 40\n')
            file.write('C  **  **  **  **  **  **  **\n')
            file.write('C    FIRST THREE ENERGIES SHOULD BE 0 1.E-6 AND 1.E-3\n')
            file.write('C    THEN SHOULD HAVE E-0.00199 3I E+0.00201\n')
            file.write('C  **  **  **  **  **  **  **\n')
            file.writelines(self.tally_energy(source.energy))
            file.write('C   TF8  6J 6\n')
            file.write('DBCN  7J 123456\n')
            file.write(source.lost_card())
            file.write(f'NPS  {source.nps}\n')
            file.close()

    def validate_model(self, standard_sheet):
        """
        Validates that the model is correctly defined.
        Checks that all detector dimensions on the standard config sheet
        are defined and gives a warning if there are detector dimensions that
        are not used. It also does a detector specific consistency check of the
        defined dimensions.

        Parameters
        ----------
        standard_sheet : Sheet
            The standard configuration sheet.

        Returns
        -------
        bool
            True if model passes all validation checks, False if it fails at least one.

        """
        required_dimensions = set(utilities.find_standard_detector_values(self.header, self.short_modelnumber, standard_sheet).keys())
        present_dimensions = set(self.dimensions.keys())

        missing_dimensions = required_dimensions.difference(present_dimensions)
        extra_dimensions = present_dimensions.difference(required_dimensions)

        if len(extra_dimensions) > 0:
            ctypes.windll.user32.MessageBoxW(0, f'Dimensions not used: {str(extra_dimensions)}', 'Extra dimension keyword', 0)
        if len(missing_dimensions) > 0:
            ctypes.windll.user32.MessageBoxW(0, f'Missing dimensions: {str(missing_dimensions)}\nCannot create MCNP model', 'Missing dimensions', 0)
            return False

        model_valid, message = self.validate_dimensions()

        if not model_valid:
            ctypes.windll.user32.MessageBoxW(0, message, 'Dimension Error', 0)

        return model_valid

    def make_par(self, char_sheet, folder_name, ordernumber, customer):
        """
        Make the parfile after the MCNP loop has completed, if the parfile
        was created successfully the detector.txt file is also created.

        Parameters
        ----------
        char_sheet : Sheet
            The characterization sheet.
        folder_name : string
            Name of the folder where the characterization files are stored.
        ordernumber : string
            The order number.
        customer : string
            The customer.

        Returns
        -------
        None.

        """
        if char_sheet.range((14, 6)).value != 'complete':
            ctypes.windll.user32.MessageBoxW(0, f'MCNP loop not complete', 'Loop not complete', 0)
            return

        endfile_name = os.path.join(folder_name, f'{self.serialnumber}.end')
        if os.path.isfile(endfile_name):
            os.remove(endfile_name)

        processed_name = self.process_outfile(folder_name)

        dcg_filename = self.create_par_dcgfile(folder_name)
        subprocess.call(['P:\ISOCSProduction\Codes\MakeDCGTools\MakeDCGTools_v1_2.exe', dcg_filename])

        # Check to see if the parfile was created.
        parfile_name = os.path.join(folder_name, f'{self.serialnumber}.par')
        if not os.path.isfile(parfile_name):
            ctypes.windll.user32.MessageBoxW(0, f'Parfile was not created, check for errors', 'Parfile not created', 0)
            return

        self.process_parfile(parfile_name, processed_name)

        self.create_detectortxt(folder_name, ordernumber, customer)

        char_sheet.range((16, 5)).value = 'Parfile'
        char_sheet.range((16, 6)).value = 'created'
        char_sheet.range((16, 5)).api.Interior.ColorIndex = 4
        char_sheet.range((16, 6)).api.Interior.ColorIndex = 4

    def process_parfile(self, parfile_name, processed_name):
        """
        Hook for detector specific processing of the parfile.

        Parameters
        ----------
        processed_name : string
            The path to the out file that has been processed.

        original_name : string
            The path to the full out file.

        Returns
        -------
        None.

        """
        pass

    def process_outfile(self, folder_name):
        """
        Hook for detector specific processing of the out file.
        The function has to do any processing that makes the serialnumber.out
        file compatibile with the MakeDCGTools program.

        Returns
        -------
        str
            Name of file that contains the processed output.

        """


        return ''

    def create_detectortxt(self, folder_name, ordernumber, customer):
        """
        Create the detector.txt file from the detector parameters.

        Parameters
        ----------
        folder_name : string
            The folder where the characterzition files are located.
        ordernumber : string
            The order number for the characterization.
        customer : string
            The customer.

        Returns
        -------
        None.

        """

        mat_lib = MCNPMaterialLibrary()
        crystal_mat, crystal_den = self.crystal_material(mat_lib)
        # kludge to get AEGIS to use a different end cap back material
        ec_back_mat, ec_back_den = self.endcap_back_material(mat_lib)
        with open(os.path.join(folder_name, 'detector.txt'), 'w') as det_text:
            det_text.write(f'# {ordernumber} - {customer} - {self.modelnumber} - S/N {self.serialnumber}\n')
            if self.dimensions['win_thick'] == self.dimensions['ec_face']:
                win_diameter = 0.0
                thin_window_xtal_gap = self.dimensions["ec_xtal_dist"]*10.0
            else:
                win_diameter = 20.0*self.dimensions['win_rad']
                # TODO: Understand this calculation, copied from MCNPtcl
                thin_window_xtal_gap = 5.0 * (self.dimensions['ec_face'] - self.dimensions['win_thick'] + self.dimensions["ec_xtal_dist"])
            det_text.write(f'{self.serialnumber},{self.dimensions["xtal_rad"]*20.0:.4g},{self.dimensions["xtal_len"]*10.0:.4g},{win_diameter:.4g},{self.dimensions["ec_rad"]*20.0:.4g},{self.dimensions["ec_len"]*10.0:.4g},{thin_window_xtal_gap:.4g},{self.dimensions["ec_xtal_dist"]*10.0:.4g},26,{self.serialnumber}.par,4, #\n')
            det_text.write(f'{crystal_mat},{self.dimensions["front_dl"]*10.0:.4g},{crystal_den}, #\n')
            if win_diameter > 0:
                det_text.write(f'{self.dimensions["win_mat"]},{self.dimensions["win_thick"]*10.0:.4g},{mat_lib.density(self.dimensions["win_mat"])}, #\n')
            else:
                det_text.write(',,, #\n')
            det_text.write(f'{self.dimensions["ec_mat"]},{self.dimensions["ec_face"]*10.0:.4g},{mat_lib.density(self.dimensions["ec_mat"])}, #\n')
            det_text.write(f'{crystal_mat},{self.dimensions["side_dl"]*10.0:.4g},{crystal_den}, #\n')
            holder_thick = self.holder_thickness()
            det_text.write(f'{self.dimensions["holder_mat"]},{holder_thick*10.0:.4g},{mat_lib.density(self.dimensions["holder_mat"])}, #\n')
            det_text.write(f'{self.dimensions["ec_mat"]},{self.dimensions["ec_side"]*10.0:.4g},{mat_lib.density(self.dimensions["ec_mat"])}, #\n')
            # The dead layer thickness is set so that the total detector volume is correct
            # this accounts for the detector well (Coax) and groove. Current calc doesn't account for the bevel (probably minimal effect)
            back_dl = self.back_dead_layer()
            det_text.write(f'{crystal_mat},{back_dl:.4g},{crystal_den}, #\n')
            det_text.write(f'{self.dimensions["holder_mat"]},{self.dimensions["holder_back"]*10.0:.4g},{mat_lib.density(self.dimensions["holder_mat"])}, #\n')
            det_text.write(f'{ec_back_mat},{self.dimensions["ec_back"]*10.0:.4g},{ec_back_den}\n')

    def crystal_material(self, mat_lib):
        """
        Return the name and density of the crystal material
        This method returns the values for HPGe.

        If the detector is not made of HPGe this method needs to be overriden.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A material library.

        Returns
        -------
        string, float
            Name of crystal material, density of crystal material.

        """
        return 'ge', mat_lib.density('ge')

    def endcap_back_material(self, mat_lib):
        """
        Return the material and density of the back of the endcap.
        This method returns the same material and density as the rest of the
        endcap.

        Override this method if the endcap material is different than the rest
        of the endcap.

        Parameters
        ----------
        mat_lib :  MaterialLibrary
            A material library.

        Returns
        -------
        string, float
            Name of endcap back material, density of endcap back material.

        """
        return self.dimensions['ec_mat'], mat_lib.density(self.dimensions['ec_mat'])


    def add_characterization_points(self, filename):
        """
        Method for adding points to the points file. This method doesn't
        add any points. Implement this function for detectors that require
        additional points.

        Parameters
        ----------
        filename : string
            The path to the points file.

        Returns
        -------
        None.

        """
        pass

    @abstractmethod
    def validate_dimensions(self):
        """
        This method should implement detector specific validation of the detector
        dimensions.

        """
        raise NotImplementedError

    @abstractmethod
    def holder_thickness(self):
        """
        This method should implement detector specific calculation of the holder
        thickness for the detector.txt file.

        """
        raise NotImplementedError

    @abstractmethod
    def back_dead_layer(self):
        """
        This method should implement detector specific calculation of the back
        deadlayer so that the volume of the crystal is correct, used for the
        detector.txt file.

        """
        raise NotImplementedError

    @abstractmethod
    def dcg_parameters(self):
        """
        This method should implement detector specific part of the dcg input file.

        """
        raise NotImplementedError

    @abstractmethod
    def surfaces(self):
        """
        This method should implement detector specific surface cards for the
        MCNP simulation.

        """
        raise NotImplementedError

    @abstractmethod
    def cells(self, electrontrack):
        """
        This method should implement detector specific cell cards for the
        MCNP simulation.

        """
        raise NotImplementedError

    @abstractmethod
    def endcap_boundary(self):
        """
        This method should implement detector specific surfaces of the endcap
        boundary.

        """
        raise NotImplementedError


class Aegis(Detector, ABC):
    def __init__(self, serialnumber):
        """
        Abstract Base Class for Aegis detectors.
        This class contains the common code for the Aegis detector types.
        It cannot be instanciated use one of the derived classes instead.

        Parameters
        ----------
        serialnumber : string
            The serial number.

        Returns
        -------
        None.

        """
        super().__init__(serialnumber)

    def cells(self, source, electrontrack):
        """
        The cell cards for the Aegis detector.

        Parameters
        ----------
        source : Source
            The source that the geometry is used with

        electrontrack : bool
            If True electron will be enabled, if False electron tracking
            will be disabled.

        Returns
        -------
        text : List
            List containing the cell cards for the Aegis detector.

        """
        mat_lib = MCNPMaterialLibrary()

        text = ['C detector cells\n']

        # Endcap front with and without a thin window
        if self.dimensions['win_rad'] > 0.0:
            text.append(f'1    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")}  1 -2 -3 {self.importance(electrontrack)}  $ Front thin window gap\n')
            text.append(f'2    {mat_lib.number(self.dimensions["win_mat"])} -{mat_lib.density(self.dimensions["win_mat"])}  2 -4 -3 {self.importance(electrontrack)}  $ thin window\n')
            text.append(f'4    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -4 3 -7 {self.importance(electrontrack)}  $ End cap lip\n')
        else:
            text.append(f'4    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -4 -7 {self.importance(electrontrack)}  $ End cap front\n')

        text.append(f'5    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])} 4 -8 6 -7 {self.importance(electrontrack)}  $ Side of End cap\n')
        text.append(f'6    {mat_lib.number(self.dimensions["ec_back_mat"])} -{mat_lib.density(self.dimensions["ec_back_mat"])} 8 -9 -7 #70 {self.importance(electrontrack)}  $ Back of End cap\n')
        text.append(f'11   {mat_lib.number("ge")} -{mat_lib.density("ge")} 11 -12 -18 {self.importance(electrontrack)}  $ Front dead layer\n')
        text.append(f'12   {mat_lib.number("ge")} -{mat_lib.density("ge")} 15 -14 -13 -18 12 #36 #37 {self.importance(electrontrack)} $ Side dead layer\n')
        text.append(f'14   {mat_lib.number("ge")} -{mat_lib.density("ge")} 35 -15 16 -13 {self.importance(electrontrack)} $ Back dead layer\n')
        text.append(f'15   {mat_lib.number("ge")} -{mat_lib.density("ge")} 35 -17 18 11 -14 {self.importance(electrontrack)} $ Bevel dead layer\n')
        text.append(f'16   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 17 11 -14 {self.importance(electrontrack)} $ Air outside of bevel\n')

        text += self.well_cells(mat_lib, electrontrack)

        text.append(f'31   {mat_lib.number("ge")} -{mat_lib.density("ge")} 41 -16 35 -44 {self.importance(electrontrack)} $ Groove outer radius dead layer\n')
        text.append(f'32   {mat_lib.number("ge")} -{mat_lib.density("ge")} 41 -33 34 -35 {self.importance(electrontrack)} $ Groove back dead layer\n')
        text.append(f'33   {mat_lib.number("ge")} -{mat_lib.density("ge")} 41 -45 43 -34 {self.importance(electrontrack)} $ Groove inner radius dead layer\n')
        text.append(f'34   {mat_lib.number("ge")} -{mat_lib.density("ge")} 45 -13 -34 {self.importance(electrontrack)} $ Dead layer between well and groove\n')
        text.append(f'35   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 33 -13 34 -35 {self.importance(electrontrack)}  $ Air (in Groove)\n')
        text.append(f'36   {mat_lib.number(self.dimensions["win_mat"])} -{mat_lib.density(self.dimensions["win_mat"])} 36 37 -14 {self.importance(electrontrack)}  $ Al (in Cleat Groove)\n')
        text.append(f'37   {mat_lib.number("ge")} -{mat_lib.density("ge")} 38 39 -14 #36 {self.importance(electrontrack)}  $ dl (Cleat Groove)\n')

        text += self.crystal_cell(mat_lib, electrontrack)

        text += self.air_outside_holder_cell(mat_lib, electrontrack)

        text.append(f'46   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} -11 60 -54 {self.importance(electrontrack)} $ Air outside crystal\n')

        text += self.air_inside_holder_cell(mat_lib, electrontrack)

        text.append(f'51   {mat_lib.number(self.dimensions["insul_f_mat"])} -{self.dimensions["insul_f_den"]} 51 -60 -61  {self.importance(electrontrack)}  $ Front inner insulator\n')
        text.append(f'52   {mat_lib.number(self.dimensions["insul_f2_mat"])} -{self.dimensions["insul_f2_den"]} 52 -51 -61 {self.importance(electrontrack)} $ Front outer insulator\n')
        text.append(f'53   {mat_lib.number(self.dimensions["insul_s_mat"])} -{self.dimensions["insul_s_den"]} 11 -72 14 -53  {self.importance(electrontrack)} $ side inner insulator\n')
        text.append(f'54   {mat_lib.number(self.dimensions["insul_s2_mat"])} -{self.dimensions["insul_s2_den"]} 11 -72 53 -54  {self.importance(electrontrack)} $ side outer insulator\n')
        text.append(f'60   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 60 -62 54 -61  {self.importance(electrontrack)} $ holder side\n')
        text.append(f'61   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 64 -65 61 -63  {self.importance(electrontrack)} $ ring 1\n')
        text.append(f'62   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 67 -68 61 -66  {self.importance(electrontrack)} $ ring 2\n')
        text.append(f'63   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 70 -71 61 -69  {self.importance(electrontrack)} $ ring 3\n')
        text.append(f'64   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 72 -62 73 -54  {self.importance(electrontrack)} $ holder back\n')

        text += self.holder_floor_cells(mat_lib, electrontrack)

        text.append(f'69   {mat_lib.number(self.dimensions["cup_mat"])} -{mat_lib.density(self.dimensions["cup_mat"])} 83 -87 85 -86 {self.importance(electrontrack)} $ FET cover side\n')
        text.append(f'70   {mat_lib.number(self.dimensions["cup_mat"])} -{mat_lib.density(self.dimensions["cup_mat"])} 87 -88 -86 {self.importance(electrontrack)} $ FET cover back\n')
        text.append(f'100  {mat_lib.number(self.dimensions["isolator_mat"])} -{mat_lib.density(self.dimensions["isolator_mat"])} 100 -101 102 -103 #101 #102 #103 #104 #105 #106 #107 #108 #109\n')
        text.append(f'     #110 #111 #112 #113 #114 #115 #116 #117 #118 #119 #120 #121 #122 #123\n')
        text.append(f'     #124 #125 #126 #127 #128 #129 #130 {self.importance(electrontrack)} $ Isolator\n')
        text.append(f'101  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 105 -106 104 -103 {self.importance(electrontrack)} $ Isolator groove 1\n')
        text.append(f'102  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 107 -108 102 -103 {self.importance(electrontrack)} $ Isolator gap 1\n')
        text.append(f'103  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 109 -110 104 -103 {self.importance(electrontrack)} $ Isolator groove 2\n')
        text.append(f'104  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 111 -112 104 -103 {self.importance(electrontrack)} $ Isolator groove 3\n')
        text.append(f'105  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 113 -114 102 -103 {self.importance(electrontrack)} $ Isolator gap 2\n')
        text.append(f'106  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 115 -116 104 -103 {self.importance(electrontrack)} $ Isolator groove 4\n')
        text.append(f'107  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 117 -118 104 -103 {self.importance(electrontrack)} $ Isolator groove 5\n')
        text.append(f'108  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 119 -120 102 -103 {self.importance(electrontrack)} $ Isolator gap 3\n')
        text.append(f'109  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 121 -122 104 -103 {self.importance(electrontrack)} $ Isolator groove 6\n')
        text.append(f'110  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 123 -124 104 -103 {self.importance(electrontrack)} $ Isolator groove 7\n')
        text.append(f'111  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 125 -126 102 -103 {self.importance(electrontrack)} $ Isolator gap 4\n')
        text.append(f'112  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 127 -128 104 -103 {self.importance(electrontrack)} $ Isolator groove 8\n')
        text.append(f'113  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 129 -130 104 -103 {self.importance(electrontrack)} $ Isolator groove 9\n')
        text.append(f'114  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 131 -132 102 -103 {self.importance(electrontrack)} $ Isolator gap 5\n')
        text.append(f'115  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 133 -134 104 -103 {self.importance(electrontrack)} $ Isolator groove 10\n')
        text.append(f'116  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 135 -136 104 -103 {self.importance(electrontrack)} $ Isolator groove 11\n')
        text.append(f'117  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 137 -138 102 -103 {self.importance(electrontrack)} $ Isolator gap 6\n')
        text.append(f'118  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 139 -140 104 -103 {self.importance(electrontrack)} $ Isolator groove 12\n')
        text.append(f'119  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 141 -142 104 -103 {self.importance(electrontrack)} $ Isolator groove 13\n')
        text.append(f'120  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 143 -144 102 -103 {self.importance(electrontrack)} $ Isolator gap 7\n')
        text.append(f'121  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 145 -146 104 -103 {self.importance(electrontrack)} $ Isolator groove 14\n')
        text.append(f'122  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 147 -148 104 -103 {self.importance(electrontrack)} $ Isolator groove 15\n')
        text.append(f'123  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 149 -150 102 -103 {self.importance(electrontrack)} $ Isolator gap 8\n')
        text.append(f'124  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 151 -152 104 -103 {self.importance(electrontrack)} $ Isolator groove 16\n')
        text.append(f'125  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 153 -154 104 -103 {self.importance(electrontrack)} $ Isolator groove 17\n')
        text.append(f'126  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 155 -156 102 -103 {self.importance(electrontrack)} $ Isolator gap 9\n')
        text.append(f'127  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 157 -158 104 -103 {self.importance(electrontrack)} $ Isolator groove 18\n')
        text.append(f'128  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 159 -160 104 -103 {self.importance(electrontrack)} $ Isolator groove 19\n')
        text.append(f'129  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 161 -162 102 -103 {self.importance(electrontrack)} $ Isolator gap 10\n')
        text.append(f'130  {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 163 -164 104 -103 {self.importance(electrontrack)} $ Isolator groove 20\n')

        return text

    def surfaces(self):
        """
        The surface cards for the Aegis detector

        Returns
        -------
        text : List
            A list with the surface cards for the Aegis detector.

        """

        # Varibles used to populate the surfaces in the
        window_front_face = self.dimensions['ec_face'] - self.dimensions['win_thick']
        endcap_inner_radius = self.dimensions['ec_rad'] - self.dimensions['ec_side']
        endcap_back_inside = self.dimensions['ec_len'] - self.dimensions['ec_back']
        front_dead_layer = self.dimensions['ec_xtal_dist'] + self.dimensions['front_dl']
        crystal_back = self.dimensions['ec_xtal_dist']+ self.dimensions['xtal_len']
        side_dead_layer = self.dimensions['xtal_rad'] - self.dimensions['side_dl']
        back_dead_layer = crystal_back - self.dimensions['back_dl']
        bevel_cone_position = - (self.dimensions['xtal_rad'] - self.dimensions['ec_xtal_dist']) + self.dimensions['bevel_rad'] / np.sqrt(2.0)
        bevel_dl_cone_position = bevel_cone_position + self.dimensions['bevel_dl'] / np.sqrt(2.0)
        groove_front_surface = crystal_back - self.dimensions['groove_depth']
        cleat_groove_forward_cone_position = self.dimensions['ec_xtal_dist']+ self.dimensions['cleat_groove_height'] + (self.dimensions['xtal_rad'] - self.dimensions['cleat_groove_depth'])*np.tan(np.deg2rad(self.dimensions['cleat_groove_f_angle']))
        cleat_groove_forward_cone_opening  = np.tan(np.deg2rad(90.0 - self.dimensions['cleat_groove_f_angle']))**2
        cleat_groove_rear_cone_position = self.dimensions['ec_xtal_dist']+ self.dimensions['cleat_groove_height'] - (self.dimensions['xtal_rad'] - self.dimensions['cleat_groove_depth'])*np.tan(np.deg2rad(self.dimensions['cleat_groove_r_angle']))
        cleat_groove_rear_cone_opening  = np.tan(np.deg2rad(90.0 - self.dimensions['cleat_groove_r_angle']))**2
        cleat_dl_forward_cone_position = cleat_groove_forward_cone_position - self.dimensions['side_dl'] / np.cos(np.deg2rad(self.dimensions['cleat_groove_f_angle']))
        cleat_dl_rear_cone_position = cleat_groove_rear_cone_position + self.dimensions['side_dl'] / np.cos(np.deg2rad(self.dimensions['cleat_groove_r_angle']))
        groove_front_dead_layer = groove_front_surface - self.dimensions['groove_dl']
        groove_inner_dead_layer = self.dimensions['groove_irad'] - self.dimensions['groove_dl']
        groove_outer_dead_layer = self.dimensions['groove_orad'] + self.dimensions['groove_dl']
        dead_layer_inside_groove = self.dimensions['ec_xtal_dist']+ self.dimensions['xtal_len'] - self.dimensions['contact_dl']

        holder_top = self.dimensions['ec_xtal_dist'] + self.dimensions['xtal_prot']
        inner_front_insulator = holder_top - self.dimensions['insul_front']
        outer_front_insulator = inner_front_insulator - self.dimensions['insul_front2']
        inner_side_insulator = self.dimensions['xtal_rad'] + self.dimensions['insul_side']
        outer_side_insulator = inner_side_insulator + self.dimensions['insul_side2']
        holder_outer_radius = outer_side_insulator + self.dimensions['holder_thick']
        holder_bottom = holder_top + self.dimensions['holder_len']
        ring1_outer_radius = holder_outer_radius + self.dimensions['holder_r1_thick']
        ring1_top = holder_top + self.dimensions['holder_r1_pos']
        ring1_bottom = ring1_top + self.dimensions['holder_r1_width']
        ring2_outer_radius = holder_outer_radius + self.dimensions['holder_r2_thick']
        ring2_top = holder_top + self.dimensions['holder_r2_pos']
        ring2_bottom = ring2_top + self.dimensions['holder_r2_width']
        ring3_outer_radius = holder_outer_radius + self.dimensions['holder_r3_thick']
        ring3_top = holder_top + self.dimensions['holder_r3_pos']
        ring3_bottom = ring3_top + self.dimensions['holder_r3_width']
        holder_back_front_surface = holder_bottom - self.dimensions['holder_back']

        floor_back = crystal_back + self.dimensions['floor_indium_thick'] + self.dimensions['floor_thickness']

        fet_cover_front_inner_radius = self.dimensions['cup_rad'] - self.dimensions['cup_sidethick']
        fet_cover_back = floor_back + self.dimensions['cup_len']
        fet_cover_back_front_surface = fet_cover_back - self.dimensions['cup_backthick']

        isolator_top = ring1_bottom + self.dimensions['isolator_holder_ring1_dist']
        isolator_back = isolator_top + self.dimensions['isolator_len']
        isolator_groove1_top = isolator_top + self.dimensions['isolator_lip_width']
        isolator_groove1_bottom = isolator_groove1_top + self.dimensions['isolator_groove1_width']
        isolator_gap1_top = isolator_groove1_bottom + self.dimensions['isolator_lip_width']
        isolator_gap1_bottom = isolator_gap1_top + self.dimensions['isolator_gap_width']
        isolator_groove2_top = isolator_gap1_bottom + self.dimensions['isolator_lip_width']
        isolator_groove2_bottom = isolator_groove2_top + self.dimensions['isolator_groove_width']
        isolator_groove3_top = isolator_groove2_bottom + self.dimensions['isolator_solid_width']
        isolator_groove3_bottom = isolator_groove3_top + self.dimensions['isolator_groove_width']
        isolator_gap2_top = isolator_groove3_bottom + self.dimensions['isolator_lip_width']
        isolator_gap2_bottom = isolator_gap2_top + self.dimensions['isolator_gap_width']
        isolator_groove4_top = isolator_gap2_bottom + self.dimensions['isolator_lip_width']
        isolator_groove4_bottom = isolator_groove4_top + self.dimensions['isolator_groove_width']
        isolator_groove5_top = isolator_groove4_bottom + self.dimensions['isolator_solid_width']
        isolator_groove5_bottom = isolator_groove5_top + self.dimensions['isolator_groove_width']
        isolator_gap3_top = isolator_groove5_bottom + self.dimensions['isolator_lip_width']
        isolator_gap3_bottom = isolator_gap3_top + self.dimensions['isolator_gap_width']
        isolator_groove6_top = isolator_gap3_bottom + self.dimensions['isolator_lip_width']
        isolator_groove6_bottom = isolator_groove6_top + self.dimensions['isolator_groove_width']
        isolator_groove7_top = isolator_groove6_bottom + self.dimensions['isolator_solid_width']
        isolator_groove7_bottom = isolator_groove7_top + self.dimensions['isolator_groove_width']
        isolator_gap4_top = isolator_groove7_bottom + self.dimensions['isolator_lip_width']
        isolator_gap4_bottom = isolator_gap4_top + self.dimensions['isolator_gap_width']
        isolator_groove8_top = isolator_gap4_bottom + self.dimensions['isolator_lip_width']
        isolator_groove8_bottom = isolator_groove8_top + self.dimensions['isolator_groove_width']
        isolator_groove9_top = isolator_groove8_bottom + self.dimensions['isolator_solid_width']
        isolator_groove9_bottom = isolator_groove9_top + self.dimensions['isolator_groove_width']
        isolator_gap5_top = isolator_groove9_bottom + self.dimensions['isolator_lip_width']
        isolator_gap5_bottom = isolator_gap5_top + self.dimensions['isolator_gap_width']
        isolator_groove10_top = isolator_gap5_bottom + self.dimensions['isolator_lip_width']
        isolator_groove10_bottom = isolator_groove10_top + self.dimensions['isolator_groove_width']
        isolator_groove11_top = isolator_groove10_bottom + self.dimensions['isolator_solid_width']
        isolator_groove11_bottom = isolator_groove11_top + self.dimensions['isolator_groove_width']
        isolator_gap6_top = isolator_groove11_bottom + self.dimensions['isolator_lip_width']
        isolator_gap6_bottom = isolator_gap6_top + self.dimensions['isolator_gap_width']
        isolator_groove12_top = isolator_gap6_bottom + self.dimensions['isolator_lip_width']
        isolator_groove12_bottom = isolator_groove12_top + self.dimensions['isolator_groove_width']
        isolator_groove13_top = isolator_groove12_bottom + self.dimensions['isolator_solid_width']
        isolator_groove13_bottom = isolator_groove13_top + self.dimensions['isolator_groove_width']
        isolator_gap7_top = isolator_groove13_bottom + self.dimensions['isolator_lip_width']
        isolator_gap7_bottom = isolator_gap7_top + self.dimensions['isolator_gap_width']
        isolator_groove14_top = isolator_gap7_bottom + self.dimensions['isolator_lip_width']
        isolator_groove14_bottom = isolator_groove14_top + self.dimensions['isolator_groove_width']
        isolator_groove15_top = isolator_groove14_bottom + self.dimensions['isolator_solid_width']
        isolator_groove15_bottom = isolator_groove15_top + self.dimensions['isolator_groove_width']
        isolator_gap8_top = isolator_groove15_bottom + self.dimensions['isolator_lip_width']
        isolator_gap8_bottom = isolator_gap8_top + self.dimensions['isolator_gap_width']
        isolator_groove16_top = isolator_gap8_bottom + self.dimensions['isolator_lip_width']
        isolator_groove16_bottom = isolator_groove16_top + self.dimensions['isolator_groove_width']
        isolator_groove17_top = isolator_groove16_bottom + self.dimensions['isolator_solid_width']
        isolator_groove17_bottom = isolator_groove17_top + self.dimensions['isolator_groove_width']
        isolator_gap9_top = isolator_groove17_bottom + self.dimensions['isolator_lip_width']
        isolator_gap9_bottom = isolator_gap9_top + self.dimensions['isolator_gap_width']
        isolator_groove18_top = isolator_gap9_bottom + self.dimensions['isolator_lip_width']
        isolator_groove18_bottom = isolator_groove18_top + self.dimensions['isolator_groove_width']
        isolator_groove19_top = isolator_groove18_bottom + self.dimensions['isolator_solid_width']
        isolator_groove19_bottom = isolator_groove19_top + self.dimensions['isolator_groove_width']
        isolator_gap10_top = isolator_groove19_bottom + self.dimensions['isolator_lip_width']
        isolator_gap10_bottom = isolator_gap10_top + self.dimensions['isolator_gap_width']
        isolator_groove20_top = isolator_gap10_bottom + self.dimensions['isolator_lip_width']
        isolator_groove20_bottom = isolator_groove20_top + self.dimensions['isolator_groove1_width']

        text = ['C   Detector\n']
        text.append('1    PZ 0    $ Front of Detector End Cap\n')
        if self.dimensions["win_rad"] > 0.0:
            text.append(f'2    PZ {window_front_face} $ Thin window front face\n')
            text.append(f'3    CZ {self.dimensions["win_rad"]} $ Radius of thin window\n')

        text.append(f'4    PZ {self.dimensions["ec_face"]} $ Back of end cap face\n')
        text.append(f'6    CZ {endcap_inner_radius} $ Inner radius of end cap\n')
        text.append(f'7    CZ {self.dimensions["ec_rad"]} $ Outer radius of end cap\n')
        text.append(f'8    PZ {endcap_back_inside} $ Inside of end cap back\n')
        text.append(f'9    PZ {self.dimensions["ec_len"]} $ Outside of end cap back\n')
        text.append(f'11   PZ {self.dimensions["ec_xtal_dist"]} $ Crystal Front\n')
        text.append(f'12   PZ {front_dead_layer} $ Front dead layer\n')
        text.append(f'13   PZ {crystal_back} $ Back of crystal\n')
        text.append(f'14   CZ {self.dimensions["xtal_rad"]} $ Crystal radius\n')
        text.append(f'15   CZ {side_dead_layer} $ Side dead layer\n')
        text.append(f'16   PZ {back_dead_layer} $ Back dead layer\n')
        text.append(f'17   KZ {bevel_cone_position} 1 1 $ Front of bevel\n')
        text.append(f'18   KZ {bevel_dl_cone_position} 1 1 $ Back of bevel dl\n')

        text += (self.well_surfaces())

        text.append(f'33   PZ {groove_front_surface}  $ Front surface of the groove\n')
        text.append(f'34   CZ {self.dimensions["groove_irad"]} $ Groove inner radius\n')
        text.append(f'35   CZ {self.dimensions["groove_orad"]} $ Groove outer radius\n')
        text.append(f'36   KZ {cleat_groove_forward_cone_position} {cleat_groove_forward_cone_opening} -1 $ Forward cone of cleat groove\n')
        text.append(f'37   KZ {cleat_groove_rear_cone_position} {cleat_groove_rear_cone_opening} 1 $ Rear cone of cleat groove\n')
        text.append(f'38   KZ {cleat_dl_forward_cone_position} {cleat_groove_forward_cone_opening} -1 $ Forward dl cone of cleat groove\n')
        text.append(f'39   KZ {cleat_dl_rear_cone_position} {cleat_groove_rear_cone_opening} 1 $ Rear dl cone of cleat groove\n')
        text.append(f'41   PZ {groove_front_dead_layer} $ Front surface of groove dead layer\n')
        text.append(f'43   CZ {groove_inner_dead_layer} $ Groove inner radius dead layer\n')
        text.append(f'44   CZ {groove_outer_dead_layer} $ Groove outer radius dead layer\n')
        text.append(f'45   PZ {dead_layer_inside_groove} $ dead layer inside the groove\n')
        text.append(f'51   PZ {inner_front_insulator} $ inner front insulator\n')
        text.append(f'52   PZ {outer_front_insulator} $ outer front insulator\n')
        text.append(f'53   CZ {inner_side_insulator} $ inner side insulator\n')
        text.append(f'54   CZ {outer_side_insulator} $ outer side insulator\n')
        text.append(f'60   PZ {holder_top} $ holder top\n')
        text.append(f'61   CZ {holder_outer_radius} $ holder outside radius\n')
        text.append(f'62   PZ {holder_bottom} $ holder side bottom\n')
        text.append(f'63   CZ {ring1_outer_radius} $ ring 1 OR\n')
        text.append(f'64   PZ {ring1_top} $ ring 1 top\n')
        text.append(f'65   PZ {ring1_bottom} $ ring 1 bottom\n')
        text.append(f'66   CZ {ring2_outer_radius} $ ring 2 OR\n')
        text.append(f'67   PZ {ring2_top} $ ring 2 top\n')
        text.append(f'68   PZ {ring2_bottom} $ ring 2 bottom\n')
        text.append(f'69   CZ {ring3_outer_radius} $ ring 3 OR\n')
        text.append(f'70   PZ {ring3_top} $ ring 3 top\n')
        text.append(f'71   PZ {ring3_bottom} $ ring 3 bottom\n')
        text.append(f'72   PZ {holder_back_front_surface} $ Holder back front surface\n')
        text.append(f'73   CZ {self.dimensions["holder_back_opening"]} $ Holder back opening radius\n')

        text += self.holder_floor_surfaces(crystal_back)

        text.append(f'85   CZ {fet_cover_front_inner_radius} $ FET Cover side inner radius\n')
        text.append(f'86   CZ {self.dimensions["cup_rad"]} $ FET Cover side outer radius\n')
        text.append(f'87   PZ {fet_cover_back_front_surface} $ FET Cover back front surface\n')
        text.append(f'88   PZ {fet_cover_back} $ FET Cover back back surface\n')
        text.append(f'C Isolator\n')
        text.append(f'100  PZ {isolator_top} $ Isolator top\n')
        text.append(f'101  PZ {isolator_back} $ Isolator back\n')
        text.append(f'102  CZ {self.dimensions["isolator_irad"]} $ Isolator inner radius\n')
        text.append(f'103  CZ {self.dimensions["isolator_orad"]} $ Isolator outer radius\n')
        text.append(f'104  CZ {self.dimensions["isolator_groove_rad"]} $ Isolator groove radius\n')
        text.append(f'105  PZ {isolator_groove1_top} $ Isolator groove 1 top\n')
        text.append(f'106  PZ {isolator_groove1_bottom} $ Isolator groove 1 bottom\n')
        text.append(f'107  PZ {isolator_gap1_top} $ Isolator gap 1 top\n')
        text.append(f'108  PZ {isolator_gap1_bottom} $ Isolator gap 1 bottom\n')
        text.append(f'109  PZ {isolator_groove2_top} $ Isolator groove 2 top\n')
        text.append(f'110  PZ {isolator_groove2_bottom} $ Isolator groove 2 bottom\n')
        text.append(f'111  PZ {isolator_groove3_top} $ Isolator groove 3 top\n')
        text.append(f'112  PZ {isolator_groove3_bottom} $ Isolator groove 3 bottom\n')
        text.append(f'113  PZ {isolator_gap2_top} $ Isolator gap 2 top\n')
        text.append(f'114  PZ {isolator_gap2_bottom} $ Isolator gap 2 bottom\n')
        text.append(f'115  PZ {isolator_groove4_top} $ Isolator groove 4 top\n')
        text.append(f'116  PZ {isolator_groove4_bottom} $ Isolator groove 4 bottom\n')
        text.append(f'117  PZ {isolator_groove5_top} $ Isolator groove 5 top\n')
        text.append(f'118  PZ {isolator_groove5_bottom} $ Isolator groove 5 bottom\n')
        text.append(f'119  PZ {isolator_gap3_top} $ Isolator gap 3 top\n')
        text.append(f'120  PZ {isolator_gap3_bottom} $ Isolator gap 3 bottom\n')
        text.append(f'121  PZ {isolator_groove6_top} $ Isolator groove 6 top\n')
        text.append(f'122  PZ {isolator_groove6_bottom} $ Isolator groove 6 bottom\n')
        text.append(f'123  PZ {isolator_groove7_top} $ Isolator groove 7 top\n')
        text.append(f'124  PZ {isolator_groove7_bottom} $ Isolator groove 7 bottom\n')
        text.append(f'125  PZ {isolator_gap4_top} $ Isolator gap 4 top\n')
        text.append(f'126  PZ {isolator_gap4_bottom} $ Isolator gap 4 bottom\n')
        text.append(f'127  PZ {isolator_groove8_top} $ Isolator groove 8 top\n')
        text.append(f'128  PZ {isolator_groove8_bottom} $ Isolator groove 8 bottom\n')
        text.append(f'129  PZ {isolator_groove9_top} $ Isolator groove 9 top\n')
        text.append(f'130  PZ {isolator_groove9_bottom} $ Isolator groove 9 bottom\n')
        text.append(f'131  PZ {isolator_gap5_top} $ Isolator gap 5 top\n')
        text.append(f'132  PZ {isolator_gap5_bottom} $ Isolator gap 5 bottom\n')
        text.append(f'133  PZ {isolator_groove10_top} $ Isolator groove 10 top\n')
        text.append(f'134  PZ {isolator_groove10_bottom} $ Isolator groove 10 bottom\n')
        text.append(f'135  PZ {isolator_groove11_top} $ Isolator groove 11 top\n')
        text.append(f'136  PZ {isolator_groove11_bottom} $ Isolator groove 11 bottom\n')
        text.append(f'137  PZ {isolator_gap6_top} $ Isolator gap 6 top\n')
        text.append(f'138  PZ {isolator_gap6_bottom} $ Isolator gap 6 bottom\n')
        text.append(f'139  PZ {isolator_groove12_top} $ Isolator groove 12 top\n')
        text.append(f'140  PZ {isolator_groove12_bottom} $ Isolator groove 12 bottom\n')
        text.append(f'141  PZ {isolator_groove13_top} $ Isolator groove 13 top\n')
        text.append(f'142  PZ {isolator_groove13_bottom} $ Isolator groove 13 bottom\n')
        text.append(f'143  PZ {isolator_gap7_top} $ Isolator gap 7 top\n')
        text.append(f'144  PZ {isolator_gap7_bottom} $ Isolator gap 7 bottom\n')
        text.append(f'145  PZ {isolator_groove14_top} $ Isolator groove 14 top\n')
        text.append(f'146  PZ {isolator_groove14_bottom} $ Isolator groove 14 bottom\n')
        text.append(f'147  PZ {isolator_groove15_top} $ Isolator groove 15 top\n')
        text.append(f'148  PZ {isolator_groove15_bottom} $ Isolator groove 15 bottom\n')
        text.append(f'149  PZ {isolator_gap8_top} $ Isolator gap 8 top\n')
        text.append(f'150  PZ {isolator_gap8_bottom} $ Isolator gap 8 bottom\n')
        text.append(f'151  PZ {isolator_groove16_top} $ Isolator groove 16 top\n')
        text.append(f'152  PZ {isolator_groove16_bottom} $ Isolator groove 16 bottom\n')
        text.append(f'153  PZ {isolator_groove17_top} $ Isolator groove 17 top\n')
        text.append(f'154  PZ {isolator_groove17_bottom} $ Isolator groove 17 bottom\n')
        text.append(f'155  PZ {isolator_gap9_top} $ Isolator gap 9 top\n')
        text.append(f'156  PZ {isolator_gap9_bottom} $ Isolator gap 9 bottom\n')
        text.append(f'157  PZ {isolator_groove18_top} $ Isolator groove 18 top\n')
        text.append(f'158  PZ {isolator_groove18_bottom} $ Isolator groove 18 bottom\n')
        text.append(f'159  PZ {isolator_groove19_top} $ Isolator groove 19 top\n')
        text.append(f'160  PZ {isolator_groove19_bottom} $ Isolator groove 19 bottom\n')
        text.append(f'161  PZ {isolator_gap10_top} $ Isolator gap 10 top\n')
        text.append(f'162  PZ {isolator_gap10_bottom} $ Isolator gap 10 bottom\n')
        text.append(f'163  PZ {isolator_groove20_top} $ Isolator groove 20 top\n')
        text.append(f'164  PZ {isolator_groove20_bottom} $ Isolator groove 20 bottom\n')

        return text

    def endcap_boundary(self):
        """
        The endcap boundary in MCNP

        Returns
        -------
        str
            Surfaces that describes the endcap boundary in MCNP.

        """
        return '(1 -9 -7)'

    def holder_thickness(self):
        """
        The "effective" holder thickness, it takes into account the isolator
        thickness and the thicknesses of the rings.

        Returns
        -------
        thickness : float
            The "effective" thickness of the holder.

        """
        holder_side_len = self.dimensions['holder_len'] - self.dimensions['holder_back']
        r1_thick = self.dimensions['holder_r1_thick'] * self.dimensions['holder_r1_width'] / holder_side_len
        r2_thick = self.dimensions['holder_r2_thick'] * self.dimensions['holder_r2_width'] / holder_side_len
        r3_thick = self.dimensions['holder_r3_thick'] * self.dimensions['holder_r3_width'] / holder_side_len

        solid_thickness = self.dimensions['isolator_orad'] - self.dimensions['isolator_irad']
        groove_thickness = self.dimensions['isolator_groove_rad'] - self.dimensions['isolator_irad']

        solid_width = self.dimensions['isolator_lip_width'] * 22 + self.dimensions['isolator_solid_width'] * 9
        groove_width = self.dimensions['isolator_groove1_width'] * 2 + self.dimensions['isolator_groove_width'] * 18
        isolator_thickness = (solid_width * solid_thickness + groove_thickness * groove_width) / self.dimensions['isolator_len']

        thickness = self.dimensions['holder_thick'] + r1_thick + r2_thick + r3_thick + isolator_thickness
        return thickness

    def back_dead_layer(self):
        """
        The "effective" back dead layer thickness that makes sure that the crystal
        volume is correct. It is important for the total efficiency calculation
        in ISOCS.

        Returns
        -------
        float
            The "effective" back dead layer thickness.

        """
        # Actual dead layer volume
        groove_dl_or = self.dimensions['groove_orad'] + self.dimensions['groove_dl']
        groove_dl_ir = self.dimensions['groove_irad'] - self.dimensions['groove_dl']
        groove_dl_depth = self.dimensions['groove_depth'] + self.dimensions['groove_dl']

        # Get the well dl outer radius and depth from the COAX or BEGe model
        well_dl_or, well_dl_depth = self.well_dl_parameters()

        back_dl_volume =  (self.dimensions['xtal_rad']**2 - groove_dl_or**2) * self.dimensions['back_dl']
        groove_volume = (groove_dl_or**2 - groove_dl_ir**2) * groove_dl_depth
        contact_dl_volume = (groove_dl_ir**2 - well_dl_or**2) * self.dimensions['contact_dl']
        well_volume = well_dl_or**2 * well_dl_depth
        # This is a simplified calculation that assumes both cleat groove angles to be 45 and it is an approximation
        # TODO: Complete the cleat groove area calculation
        cleat_groove_or = self.dimensions['xtal_rad'] - self.dimensions['side_dl']
        cleat_groove_ir = cleat_groove_or - self.dimensions['cleat_groove_depth'] - self.dimensions['side_dl']/np.sqrt(2)
        cleat_groove_width = cleat_groove_or - cleat_groove_ir
        cleat_groove_volume = (cleat_groove_or - cleat_groove_ir)**2 * cleat_groove_width

        total_volume = back_dl_volume + groove_volume + contact_dl_volume + cleat_groove_volume + well_volume

        thickness = total_volume / self.dimensions['xtal_rad']**2
        return thickness * 10.0

    def endcap_back_material(self, mat_lib):
        """
        The Aegis has a parameter for the endcap back material.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A material library.

        Returns
        -------
        string, float
            The endcap back name, the end cap back density.

        """
        return mat_lib.isocs_name(self.dimensions['ec_back_mat']), mat_lib.density(self.dimensions['ec_back_mat'])


class AegisBEGe(Aegis):
    def __init__(self, serialnumber):
        """
        The class for the Aegis BEGe detector. Currently only tested for the
        RDC version.

        Parameters
        ----------
        serialnumber : string
            The serial number of the detector.

        Returns
        -------
        None.

        """
        super().__init__(serialnumber)
        self.modelnumber = 'AEGIS-BEGE5030'
        self.short_modelnumber = 'AEGIS-BEGE5030'
        self.header = 'AEGIS-BEGE'
        self.low_energy_validation = True


    def validate_dimensions(self):
        """
        Dimension validation for the Aegis BEGe detector.
        This function needs to be expanded

        Returns
        -------
        bool
            True if the detector passes all validation checks, false otherwise.
        str
            Error message to print if check is failed.

        """
        # TODO: Add more validation checks.
        if self.dimensions['xtal_prot'] >= 0.0:
            return False, 'Crystal protrusion >= 0.0'

        return True, ''

    def well_surfaces(self):
        """
        The surfaces that describes the well. The Aegis BEGe does not have
        a well so there are no surfaces for it.

        Returns
        -------
        list
            List of the surfaces.

        """
        return []

    def holder_floor_surfaces(self, crystal_back):
        """
        The surfaces that describes the holder floor of the Aegis detector

        Parameters
        ----------
        crystal_back : float
            The distance from the endcap to the back of the crystal.

        Returns
        -------
        text : List
            List of holder floor surfaces.

        """
        indium_back_surface = crystal_back + self.dimensions['floor_indium_thick']
        floor_front_back_surface = indium_back_surface + self.dimensions['floor_front_thick']
        floor_lip_inner_radius = self.dimensions['floor_front_rad'] - self.dimensions['floor_lip_rad_thick']
        floor_ring_outer_radius = self.dimensions['floor_ring_inner_rad'] + self.dimensions['floor_ring_thick']
        floor_back = indium_back_surface + self.dimensions['floor_thickness']
        floor_back_front_surface = floor_back - self.dimensions['floor_lip_thick']

        text = [f'74   PZ {indium_back_surface} $ Floor indium back\n',
                f'75   CZ {self.dimensions["floor_opening"]} $ Floor opening radius\n',
                f'76   CZ {self.dimensions["floor_front_rad"]} $ Floor front radius\n',
                f'77   PZ {floor_front_back_surface} $ Floor front back surface\n',
                f'78   CZ {self.dimensions["floor_ring_inner_rad"]} $ Floor ring inner radius\n',
                f'79   CZ {floor_ring_outer_radius} $ Floor ring outer radius\n',
                f'80   CZ {floor_lip_inner_radius} $ Floor lip inner radius\n',
                f'81   CZ {self.dimensions["floor_bottom_rad"]} $ Floor bottom radius\n',
                f'82   PZ {floor_back_front_surface} $ Floor back front surface\n',
                f'83   PZ {floor_back} $ Floor back\n']

        return text

    def well_cells(self, mat_lib, electrontrack):
        """
        The cell cards for the well. The Aegis BEGe detector does not have
        a well so the list returned will be empty.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A material library.
        electrontrack : bool
            If True electron tracking will be available, if false electron tracking
            will be disabled.

        Returns
        -------
        list
            List of cell cards.

        """
        return []

    def crystal_cell(self, mat_lib, electrontrack):
        """
        The cell card for the crystal

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        list
            The cell cards for the crystal cell.

        """
        return [f'40   {mat_lib.number("ge")} -{mat_lib.density("ge")} 11 -13 -14 #11 #12 #14 #15 #16 #31 #32 #33 #34 #35 #36 #37\n',
                f'     {self.importance(electrontrack, crystal=True)} $ Crystal Active Volume\n']

    def air_outside_holder_cell(self, mat_lib, electrontrack):
        """
        The cell card for the air outside the holder

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cell cards that descibes the cell for the air outside the holder.

        """
        text = [f'45   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} (4 -52 -6):(-6 61 4 -8 #61 #62 #63 #68 #(100 -101 102 -103)):\n',
                f'     (-8 62 -61 #67 #68 #69 #70) {self.importance(electrontrack)}  $ Air outside holder\n']

        return text

    def air_inside_holder_cell(self, mat_lib, electrontrack):
        """
        The cell card for the air inside the holder

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cell cards that descibes the cell for the air inside the holder.

        """
        return f'47   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 13 -62 -14 #64 #65 #66 #67 #68 {self.importance(electrontrack)}  $ Air inside holder\n'

    def holder_floor_cells(self, mat_lib, electrontrack):
        """
        The cells that describe the holder floor.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cells describing the holder floor.

        """
        text = [f'65   {mat_lib.number("in")} -{mat_lib.density("in")} 13 -74 75 -76 {self.importance(electrontrack)} $ floor indium\n',
                f'66   {mat_lib.number(self.dimensions["floor_mat"])} -{mat_lib.density(self.dimensions["floor_mat"])} 74 -77 75 -76 {self.importance(electrontrack)} $ floor front\n',
                f'67   {mat_lib.number(self.dimensions["floor_mat"])} -{mat_lib.density(self.dimensions["floor_mat"])} 77 -83 78 -79 {self.importance(electrontrack)} $ floor ring\n',
                f'68   {mat_lib.number(self.dimensions["floor_mat"])} -{mat_lib.density(self.dimensions["floor_mat"])} (77 -83 80 -76):(82 -83 76 -81) {self.importance(electrontrack)} $ floor lip\n']

        return text

    def dcg_parameters(self):
        """
        The Aegis BEGe specific dcg parameters

        Returns
        -------
        text : List
            list of detector specifc dsg parameters.

        """
        mat_lib = MCNPMaterialLibrary()
        text =  ['~ModelNumber BE5030\n',
                 '\n',
                 f'xtal_rad {self.dimensions["xtal_rad"]}\n',
                 f'xtal_len {self.dimensions["xtal_len"]}\n',
                 f'front_dl {self.dimensions["front_dl"]}\n',
                 f'side_dl {self.dimensions["side_dl"]}\n',
                 f'back_dl {self.dimensions["back_dl"]}\n',
                 f'groove_depth {self.dimensions["groove_depth"]}\n',
                 f'groove_irad {self.dimensions["groove_irad"]}\n',
                 f'groove_orad {self.dimensions["groove_orad"]}\n',
                 f'groove_dl {self.dimensions["groove_dl"]}\n',
                 f'kludge {self.dimensions["contact_dl"]}\n',
                 f'tophat_rad {self.dimensions["bevel_rad"]}\n',
                 f'tophat_dep {self.dimensions["bevel_rad"]}\n',
                 f'ec_xtal_dist {self.dimensions["ec_xtal_dist"]}\n',
                 f'ec_rad {self.dimensions["ec_rad"]}\n',
                 f'ec_len {self.dimensions["ec_len"]}\n',
                 f'ec_face {self.dimensions["ec_face"]}\n',
                 f'ec_side {self.dimensions["ec_side"]}\n',
                 f'ec_back {self.dimensions["ec_back"]}\n',
                 f'ec_mat {self.dimensions["ec_mat"]}\n',
                 f'win_rad {self.dimensions["win_rad"]}\n',
                 f'win_mat {self.dimensions["win_mat"]}\n',
                 f'win_thick {self.dimensions["win_thick"]}\n',
                 f'xtal_prot {self.dimensions["xtal_prot"]}\n',
                 f'holder_lippos {self.dimensions["holder_r1_pos"]}\n',
                 f'holder_mat {self.dimensions["holder_mat"]}\n',
                 f'holder_thick {self.dimensions["holder_thick"]}\n',
                 f'holder_lipthick {self.dimensions["holder_r1_thick"]}\n',
                 f'holder_lipwid {self.dimensions["holder_r1_width"]}\n',
                 f'holder_back {self.dimensions["holder_back"]}\n',
                 f'cup_rad {self.dimensions["cup_rad"]}\n',
                 f'cup_sidethick {self.dimensions["cup_sidethick"]}\n',
                 f'cup_len {self.dimensions["cup_len"]}\n',
                 f'cup_backthick {self.dimensions["cup_backthick"]}\n',
                 f'insul_front {self.dimensions["insul_front"]}\n',
                 f'insul_f_mat {mat_lib.dcg_name(self.dimensions["insul_f_mat"])}\n',
                 f'insul_f_den {self.dimensions["insul_f_den"]}\n',
                 f'insul_front2 {self.dimensions["insul_front2"]}\n',
                 f'insul_f2_mat {mat_lib.dcg_name(self.dimensions["insul_f2_mat"])}\n',
                 f'insul_f2_den {self.dimensions["insul_f2_den"]}\n',
                 f'insul_side {self.dimensions["insul_side"]}\n',
                 f'insul_s_mat {mat_lib.dcg_name(self.dimensions["insul_s_mat"])}\n',
                 f'insul_s_den {self.dimensions["insul_s_den"]}\n',
                 f'insul_side2 {self.dimensions["insul_side2"]}\n',
                 f'insul_s2_mat {mat_lib.dcg_name(self.dimensions["insul_s2_mat"])}\n',
                 f'insul_s2_den {self.dimensions["insul_s2_den"]}\n',
                 f'insul_back {self.dimensions["insul_back"]}\n',
                 f'insul_b_mat {mat_lib.dcg_name(self.dimensions["insul_b_mat"])}\n',
                 f'insul_b_den {self.dimensions["insul_b_den"]}\n',
                 f'insul_back2 {self.dimensions["insul_back2"]}\n',
                 f'insul_b2_mat {mat_lib.dcg_name(self.dimensions["insul_b2_mat"])}\n',
                 f'insul_b2_den {self.dimensions["insul_b2_den"]}\n',
        ]
        return text

    def well_dl_parameters(self):
        """
        The Aegis BEGe does not have well dead layer parameters

        Returns
        -------
        float
            0.0.
        float
            0.0.

        """
        return 0.0, 0.0


class AegisCoax(Aegis):
    def __init__(self, serialnumber, crystal_type):
        """
        The class for the Aegis Coax detector. Currently only tested for the
        RDC version. This should be used for both the GC and GX type detectors.


        Parameters
        ----------
        serialnumber : string
            The serial number of the detector.
        crystal_type : string
            'GC' for the Aegis GC40 detector and 'GX' for the Aegis GX40 detector.

        Raises
        ------
        ValueError
            If the crystal type is not 'GC' or 'GX'

        Returns
        -------
        None.

        """

        super().__init__(serialnumber)
        if crystal_type == 'GC':
            self.modelnumber = 'AEGIS-GC40'
            self.low_energy_validation = False
            self.short_modelnumber = 'AEGIS-GC40'
        elif crystal_type == 'GX':
            self.modelnumber = 'AEGIS-GX40'
            self.low_energy_validation = True
            self.short_modelnumber = 'AEGIS-GX40'
        else:
            raise ValueError('Unknown crystal type')
        self.header = 'AEGIS-COAX'

    def validate_dimensions(self):
        """
        Dimension validation for the Aegis BEGe detector.
        This function needs to be expanded

        Returns
        -------
        bool
            True if the detector passes all validation checks, false otherwise.
        str
            Error message to print if check is failed.

        """
        # TODO: Add more validation checks.
        if self.dimensions['xtal_prot'] >= 0.0:
            return False, 'Crystal protrution >= 0.0'

        return True, ''

    def well_surfaces(self):
        """
        The surfaces that describes the well.

        Returns
        -------
        list
            List of the surfaces.

        """
        front_surface = self.dimensions["ec_xtal_dist"] + self.dimensions["xtal_len"] - self.dimensions["well_depth"]
        insulator_radius = self.dimensions["well_cu"] + self.dimensions["well_insul"]
        front_dl = front_surface - self.dimensions["well_dl"]
        side_dl = self.dimensions["well_radius"] + self.dimensions["well_dl"]

        text = [f'20   CZ {self.dimensions["well_radius"]} $ Well radius\n',
                f'21   PZ {front_surface}  $ Front surface of the well\n',
                f'22   CZ {self.dimensions["well_cu"]}  $ well cu radius\n',
                f'23   PZ {front_dl}  $ well front dead layer\n',
                f'24   CZ {side_dl}  $ well side dead layer\n',
                f'25   CZ {insulator_radius}  $ well insulator radius\n',
        ]
        return text

    def well_cells(self, mat_lib, electrontrack):
        """
        The cell cards for the well.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A material library.
        electrontrack : bool
            If True electron tracking will be available, if false electron tracking
            will be disabled.

        Returns
        -------
        list
            List of cell cards.

        """
        text = [f'20   {mat_lib.number("ge")} -{mat_lib.density("ge")} 23 -21 -24 {self.importance(electrontrack)} $ Well front dead layer\n',
                f'21   {mat_lib.number("ge")} -{mat_lib.density("ge")} 21 -45 20 -24 {self.importance(electrontrack)} $ Well side dead layer\n',
                f'22   {mat_lib.number("cu")} -{mat_lib.density("cu")} 21 -45 -22 {self.importance(electrontrack)} $ Well copper rod\n',
                f'23   {mat_lib.number("teflon")} -{mat_lib.density("teflon")} 21 -45 22 -25 {self.importance(electrontrack)} $ Well insulator\n',
                f'24   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 21 -45 25 -20 {self.importance(electrontrack)} $ Air in well\n',
                ]
        return text

    def holder_floor_surfaces(self, crystal_back):
        """
        The surfaces that describes the holder floor of the Aegis detector

        Parameters
        ----------
        crystal_back : float
            The distance from the endcap to the back of the crystal.

        Returns
        -------
        text : List
            List of holder floor surfaces.

        """
        indium_back_surface = crystal_back + self.dimensions['floor_indium_thick']
        floor_front_back_surface = indium_back_surface + self.dimensions['floor_front_thick']
        floor_lip_inner_radius = self.dimensions['floor_front_rad'] - self.dimensions['floor_lip_rad_thick']
        floor_back = indium_back_surface + self.dimensions['floor_thickness']
        floor_back_front_surface = floor_back - self.dimensions['floor_lip_thick']

        text = [f'74   PZ {indium_back_surface} $ Floor indium back\n',
                f'75   CZ {self.dimensions["floor_opening"]} $ Floor opening radius\n',
                f'76   CZ {self.dimensions["floor_front_rad"]} $ Floor front radius\n',
                f'77   PZ {floor_front_back_surface} $ Floor front back surface\n',
                f'80   CZ {floor_lip_inner_radius} $ Floor lip inner radius\n',
                f'81   CZ {self.dimensions["floor_bottom_rad"]} $ Floor bottom radius\n',
                f'82   PZ {floor_back_front_surface} $ Floor back front surface\n',
                f'83   PZ {floor_back} $ Floor back\n']

        return text


    def crystal_cell(self, mat_lib, electrontrack):
        """
        The cell card for the crystal

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        list
            The cell cards for the crystal cell.

        """
        return [f'40   {mat_lib.number("ge")} -{mat_lib.density("ge")} 11 -13 -14 #11 #12 #14 #15 #16 #31 #32 #33 #34 #35 #36 #37\n',
                f'     #(23 -45 -24) {self.importance(electrontrack, crystal=True)} $ Crystal Active Volume\n']

    def air_outside_holder_cell(self, mat_lib, electrontrack):
        """
        The cell card for the air outside the holder

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cell cards that descibes the cell for the air outside the holder.

        """
        text = [f'45   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} (4 -52 -6):(-6 61 4 -8 #61 #62 #63 #68 #(100 -101 102 -103)):\n',
                f'     (-8 62 -61 #68 #69 #70) {self.importance(electrontrack)}  $ Air outside holder\n']

        return text

    def air_inside_holder_cell(self, mat_lib, electrontrack):
        """
        The cell card for the air inside the holder

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cell cards that descibes the cell for the air inside the holder.

        """
        return f'47   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 13 -62 -14 #64 #65 #66 #67 #68 {self.importance(electrontrack)}  $ Air inside holder\n'

    def holder_floor_cells(self, mat_lib, electrontrack):
        """
        The cells that describe the holder floor.

        Parameters
        ----------
        mat_lib : MaterialLibrary
            A Material library.
        electrontrack : bool
            If True, electron tracking will be enabled, if false electron tracking
            will be disabled.

        Returns
        -------
        text : list
            The cells describing the holder floor.

        """
        text = [f'65   {mat_lib.number("in")} -{mat_lib.density("in")} 13 -74 75 -76 {self.importance(electrontrack)} $ floor indium\n',
                f'66   {mat_lib.number(self.dimensions["floor_mat"])} -{mat_lib.density(self.dimensions["floor_mat"])} 74 -77 75 -76 {self.importance(electrontrack)} $ floor front\n',
                f'68   {mat_lib.number(self.dimensions["floor_mat"])} -{mat_lib.density(self.dimensions["floor_mat"])} (77 -83 80 -76):(82 -83 76 -81) {self.importance(electrontrack)} $ floor lip\n']

        return text

    def well_dl_parameters(self):
        """
        The well dead layer outer radius and the well dead layer depth

        Returns
        -------
        well_dl_or : float
            The outer radius of the dead layer.
        well_dl_depth : float
            The depth of the dead layer.

        """
        well_dl_or = self.dimensions['well_radius'] + self.dimensions['well_dl']
        well_dl_depth = self.dimensions['well_depth'] + self.dimensions['well_dl']
        return well_dl_or, well_dl_depth

    def dcg_parameters(self):
        """
        The Aegis Coax specific dcg parameters

        Returns
        -------
        text : List
            list of detector specifc dsg parameters.

        """
        mat_lib = MCNPMaterialLibrary()
        text =  ['~ModelNumber GC4018\n',
                 '\n',
                 f'xtal_rad {self.dimensions["xtal_rad"]}\n',
                 f'xtal_len {self.dimensions["xtal_len"]}\n',
                 f'front_dl {self.dimensions["front_dl"]}\n',
                 f'side_dl {self.dimensions["side_dl"]}\n',
                 f'back_dl {self.dimensions["back_dl"]}\n',
                 f'bevel_rad {self.dimensions["bevel_rad"]}\n',
                 f'well_depth {self.dimensions["well_depth"]}\n',
                 f'well_radius {self.dimensions["well_radius"]}\n',
                 f'well_dl {self.dimensions["well_dl"]}\n',
                 f'well_cu {self.dimensions["well_cu"]}\n',
                 f'well_insul {self.dimensions["well_insul"]}\n',
                 f'ec_xtal_dist {self.dimensions["ec_xtal_dist"]}\n',
                 f'ec_rad {self.dimensions["ec_rad"]}\n',
                 f'ec_len {self.dimensions["ec_len"]}\n',
                 f'ec_side {self.dimensions["ec_side"]}\n',
                 f'ec_face {self.dimensions["ec_face"]}\n',
                 f'ec_back {self.dimensions["ec_back"]}\n',
                 f'ec_mat {self.dimensions["ec_mat"]}\n',
                 f'win_rad {self.dimensions["win_rad"]}\n',
                 f'win_mat {self.dimensions["win_mat"]}\n',
                 f'win_thick {self.dimensions["win_thick"]}\n',
                 f'xtal_prot {self.dimensions["xtal_prot"]}\n',
                 f'groove_depth {self.dimensions["groove_depth"]}\n',
                 f'groove_irad {self.dimensions["groove_irad"]}\n',
                 f'groove_orad {self.dimensions["groove_orad"]}\n',
                 f'groove_dl {self.dimensions["groove_dl"]}\n',
                 f'kludge {self.dimensions["contact_dl"]}\n',
                 f'holder_mat {self.dimensions["holder_mat"]}\n',
                 f'holder_thick {self.dimensions["holder_thick"]}\n',
                 f'holder_lipthick {self.dimensions["holder_r1_thick"]}\n',
                 f'holder_lipwid {self.dimensions["holder_r1_width"]}\n',
                 f'holder_r1pos {self.dimensions["holder_r2_pos"]}\n',
                 f'holder_r1wid {self.dimensions["holder_r2_width"]}\n',
                 f'holder_r2pos {self.dimensions["holder_r3_pos"]}\n',
                 f'holder_r2wid {self.dimensions["holder_r3_width"]}\n',
                 f'holder_len {self.dimensions["holder_len"]}\n',
                 f'holder_back {self.dimensions["holder_back"]}\n',
                 f'insul_front {self.dimensions["insul_front"]}\n',
                 f'insul_f_mat {mat_lib.dcg_name(self.dimensions["insul_f_mat"])}\n',
                 f'insul_f_den {self.dimensions["insul_f_den"]}\n',
                 f'insul_side {self.dimensions["insul_side"]}\n',
                 f'insul_s_mat {mat_lib.dcg_name(self.dimensions["insul_s_mat"])}\n',
                 f'insul_s_den {self.dimensions["insul_s_den"]}\n',
                 f'insul_front2 {self.dimensions["insul_front2"]}\n',
                 f'insul_f2_mat {mat_lib.dcg_name(self.dimensions["insul_f2_mat"])}\n',
                 f'insul_f2_den {self.dimensions["insul_f2_den"]}\n',
                 f'insul_side2 {self.dimensions["insul_side2"]}\n',
                 f'insul_s2_mat {mat_lib.dcg_name(self.dimensions["insul_s2_mat"])}\n',
                 f'insul_s2_den {self.dimensions["insul_s2_den"]}\n',
                 f'insul_back {self.dimensions["insul_back"]}\n',
                 f'insul_b_mat {mat_lib.dcg_name(self.dimensions["insul_b_mat"])}\n',
                 f'insul_b_den {self.dimensions["insul_b_den"]}\n',
                 f'insul_back2 {self.dimensions["insul_back2"]}\n',
                 f'insul_b2_mat {mat_lib.dcg_name(self.dimensions["insul_b2_mat"])}\n',
                 f'insul_b2_den {self.dimensions["insul_b2_den"]}\n'
        ]
        return text


class GCW(Detector):
    def __init__(self, serialnumber, model):
        """
        Class for the GCW traditional well detector. The detector is similar
        to a coaxial detector that is turned upside down and there is a well
        in the end cap.

        Parameters
        ----------
        serialnumber : string
            The serial number of the detector.

        Returns
        -------
        None.

        """
        super().__init__(serialnumber)
        self.modelnumber = model
        self.header = 'GCW'
        if len(model) == 5:
            short_model = model
        elif len(model) == 7:
            short_model = model[0:5]
        elif len(model)  == 8:
            short_model = model[0:6]
        else:
            raise ValueError(f'Unknown model: {model}')
        self.short_modelnumber = short_model
        self.low_energy_validation = False


    def validate_dimensions(self):
        """
        This method should implement detector specific validation of the detector
        dimensions.

        """
         # TODO: Add more validation checks.
        if self.dimensions['xtal_rad'] >= self.dimensions['ec_rad']:
            return False, 'Crystal radius >= Endcap radius'

        return True, ''

    def holder_thickness(self):
        """
        This method should implement detector specific calculation of the holder
        thickness for the detector.txt file.

        """
        return self.dimensions['holder_thick']

    def back_dead_layer(self):
        """
        This method should implement detector specific calculation of the back
        deadlayer so that the volume of the crystal is correct, used for the
        detector.txt file.

        """
        return self.dimensions['back_dl']

    def dcg_parameters(self):
        """
        The GCW specific dcg parameters

        Returns
        -------
        text : List
            list of detector specifc dcg parameters.

        """
        mat_lib = MCNPMaterialLibrary()
        text =  ['~ModelNumber GC4018\n',
                 '\n',
                 f'xtal_rad {self.dimensions["xtal_rad"]}\n',
                 f'xtal_len {self.dimensions["xtal_len"]}\n',
                 f'front_dl {self.dimensions["front_dl"]}\n',
                 f'side_dl {self.dimensions["side_dl"]}\n',
                 f'back_dl {self.dimensions["back_dl"]}\n',
                 f'bevel_rad {self.dimensions["bevel_rad"]}\n',
                 f'well_depth {self.dimensions["well_depth"]}\n',
                 f'well_radius {self.dimensions["well_radius"]}\n',
                 f'well_dl {self.dimensions["well_dl_side"]}\n',
                 f'well_cu {1.0}\n',
                 f'well_insul {0.01}\n',
                 f'ec_xtal_dist {self.dimensions["ec_xtal_dist"]}\n',
                 f'ec_rad {self.dimensions["ec_rad"]}\n',
                 f'ec_len {self.dimensions["ec_len"]}\n',
                 f'ec_side {self.dimensions["ec_side"]}\n',
                 f'ec_face {self.dimensions["ec_face"]}\n',
                 f'ec_back {self.dimensions["ec_back"]}\n',
                 f'ec_mat {self.dimensions["ec_mat"]}\n',
                 f'win_rad {self.dimensions["win_rad"]}\n',
                 f'win_mat {self.dimensions["well_mat"]}\n',
                 f'win_thick {self.dimensions["win_thick"]}\n',
                 f'xtal_prot {self.dimensions["xtal_prot"]}\n',
                 f'groove_depth {self.dimensions["groove_depth"]}\n',
                 f'groove_irad {self.dimensions["groove_irad"]}\n',
                 f'groove_orad {self.dimensions["groove_orad"]}\n',
                 f'groove_dl {self.dimensions["groove_dl"]}\n',
                 f'kludge {self.dimensions["contact_dl"]}\n',
                 f'holder_mat {self.dimensions["holder_mat"]}\n',
                 f'holder_thick {self.dimensions["holder_thick"]}\n',
                 f'holder_lipthick {self.dimensions["holder_lipthick"]}\n',
                 f'holder_lipwid {self.dimensions["holder_lipwid"]}\n',
                 f'holder_r1pos {self.dimensions["holder_r1pos"]}\n',
                 f'holder_r1wid {self.dimensions["holder_r1wid"]}\n',
                 f'holder_r2pos {self.dimensions["holder_r2pos"]}\n',
                 f'holder_r2wid {self.dimensions["holder_r2wid"]}\n',
                 f'holder_len {self.dimensions["holder_len"]}\n',
                 f'holder_back {self.dimensions["holder_back"]}\n',
                 f'insul_front {self.dimensions["insul_front"]}\n',
                 f'insul_f_mat {mat_lib.dcg_name(self.dimensions["insul_f_mat"])}\n',
                 f'insul_f_den {self.dimensions["insul_f_den"]}\n',
                 f'insul_side {self.dimensions["insul_side"]}\n',
                 f'insul_s_mat {mat_lib.dcg_name(self.dimensions["insul_s_mat"])}\n',
                 f'insul_s_den {self.dimensions["insul_s_den"]}\n',
                 f'insul_front2 {self.dimensions["insul_front2"]}\n',
                 f'insul_f2_mat {mat_lib.dcg_name(self.dimensions["insul_f2_mat"])}\n',
                 f'insul_f2_den {self.dimensions["insul_f2_den"]}\n',
                 f'insul_side2 {self.dimensions["insul_side2"]}\n',
                 f'insul_s2_mat {mat_lib.dcg_name(self.dimensions["insul_s2_mat"])}\n',
                 f'insul_s2_den {self.dimensions["insul_s2_den"]}\n',
                 f'insul_back {self.dimensions["insul_back"]}\n',
                 f'insul_b_mat {mat_lib.dcg_name(self.dimensions["insul_b_mat"])}\n',
                 f'insul_b_den {self.dimensions["insul_b_den"]}\n',
                 f'insul_back2 {self.dimensions["insul_back2"]}\n',
                 f'insul_b2_mat {mat_lib.dcg_name(self.dimensions["insul_b2_mat"])}\n',
                 f'insul_b2_den {self.dimensions["insul_b2_den"]}\n'
        ]
        return text

    def surfaces(self):
        """
        The surface cards for the GCW detector

        Returns
        -------
        text : List
            A list with the surface cards for the GCW detector.

        """

        # Varibles used to populate the surfaces in the
        endcap_well_outer_radius = self.dimensions['ec_well_radius'] + self.dimensions['ec_well_side']
        endcap_well_bottom_bottom = self.dimensions["ec_well_depth"] + self.dimensions["ec_well_bottom"]
        endcap_inner_radius = self.dimensions['ec_rad'] - self.dimensions['ec_side']
        endcap_back_inside = self.dimensions['ec_len'] - self.dimensions['ec_back']

        xtal_back = self.dimensions["ec_xtal_dist"] + self.dimensions["xtal_len"]
        front_dl = self.dimensions["ec_xtal_dist"] + self.dimensions["front_dl"]
        side_dl =  self.dimensions["xtal_rad"] - self.dimensions["side_dl"]
        back_dl = xtal_back - self.dimensions["back_dl"]
        xtal_well_depth = self.dimensions["ec_xtal_dist"] + self.dimensions["well_depth"]
        xtal_core_depth = xtal_well_depth + self.dimensions["core_depth"]
        well_side_dl = self.dimensions["well_radius"] + self.dimensions["well_dl_side"]
        well_bottom_dl = xtal_well_depth + self.dimensions["well_dl_bottom"]
        core_side_dl = self.dimensions["core_radius"] + self.dimensions["well_dl_side"]
        core_bottom_dl = xtal_core_depth + self.dimensions["well_dl_bottom"]
        groove_bottom = self.dimensions["ec_xtal_dist"] + self.dimensions["groove_depth"]
        groove_dl_bottom = groove_bottom + self.dimensions["groove_dl"]
        groove_dl_inner_rad = self.dimensions["groove_irad"] - self.dimensions["groove_dl"]
        groove_dl_outer_rad = self.dimensions["groove_orad"] + self.dimensions["groove_dl"]
        contact_dl = self.dimensions["ec_xtal_dist"] + self.dimensions["contact_dl"]
        front_bevel_apex = self.dimensions["ec_xtal_dist"] - self.dimensions["xtal_rad"] + self.dimensions["bevel_rad"]*np.sqrt(2)
        front_bevel_dl_apex = front_bevel_apex + self.dimensions["bevel_dl"]*np.sqrt(2)
        back_bevel_apex = xtal_back + self.dimensions["xtal_rad"] - self.dimensions["bevel_rad"]*np.sqrt(2)
        back_bevel_dl_apex = back_bevel_apex - self.dimensions["bevel_dl"]*np.sqrt(2)

        front_insulator1 = self.dimensions["ec_xtal_dist"] - self.dimensions["insul_front"]
        front_insulator2 = front_insulator1 - self.dimensions["insul_front2"]
        side_insulator1 = self.dimensions["xtal_rad"] + self.dimensions["insul_side"]
        side_insulator2 = side_insulator1 + self.dimensions["insul_side2"]
        back_insulator1 = xtal_back + self.dimensions["insul_back"]
        back_insulator2 = back_insulator1 + self.dimensions["insul_back2"]

        holder_front = self.dimensions["ec_xtal_dist"] + self.dimensions["xtal_prot"]
        holder_back = holder_front + self.dimensions["holder_len"]
        holder_side = side_insulator2 + self.dimensions["holder_thick"]
        holder_back_front = holder_back - self.dimensions["holder_back"]
        holder_ring_radius = holder_side + self.dimensions["holder_lipthick"]
        holder_lip_back = holder_front + self.dimensions["holder_lipwid"]
        holder_ring1_front = holder_front + self.dimensions["holder_r1pos"]
        holder_ring1_back = holder_ring1_front + self.dimensions["holder_r1wid"]
        holder_ring2_front = holder_front + self.dimensions["holder_r2pos"]
        holder_ring2_back = holder_ring2_front + self.dimensions["holder_r2wid"]

        text = ['C   Detector\n']
        text.append('1    PZ 0    $ Front of Detector End Cap\n')
        if self.dimensions["win_rad"] > 0.0:
            text.append(f'2    PZ {self.dimensions["win_thick"]} $ Window lip surface\n')
            text.append(f'3    CZ {self.dimensions["win_rad"]} $ Radius of thin window\n')
        text.append(f'4    CZ {endcap_well_outer_radius} $ End cap well outer radius\n')
        text.append(f'5    CZ {self.dimensions["ec_well_radius"]} $ End cap well inner radius\n')
        text.append(f'6    PZ {self.dimensions["ec_well_depth"]} $ End cap well bottom\n')
        text.append(f'7    PZ {endcap_well_bottom_bottom} $ End cap well bottom\n')
        text.append(f'8    PZ {self.dimensions["ec_face"]} $ Back of end cap face\n')
        text.append(f'9    CZ {endcap_inner_radius} $ Inner radius of end cap\n')
        text.append(f'10    CZ {self.dimensions["ec_rad"]} $ Outer radius of end cap\n')
        text.append(f'11    PZ {endcap_back_inside} $ Inside of end cap back\n')
        text.append(f'12    PZ {self.dimensions["ec_len"]} $ Outside of end cap back\n')

        text.append(f'20    PZ {self.dimensions["ec_xtal_dist"]} $ Crystal front\n')
        text.append(f'21    PZ {xtal_back} $ Crystal back\n')
        text.append(f'22    CZ {self.dimensions["xtal_rad"]} $ Crystal radius\n')
        text.append(f'23    PZ {front_dl} $ Front dl\n')
        text.append(f'24    CZ {side_dl} $ Side dl\n')
        text.append(f'25    PZ {back_dl} $ Back dl\n')
        text.append(f'26    CZ {self.dimensions["well_radius"]} $ Crystal well radius\n')
        text.append(f'27    PZ {xtal_well_depth} $ Crystal well depth\n')
        text.append(f'28    CZ {self.dimensions["core_radius"]} $ Crystal core radius\n')
        text.append(f'29    PZ {xtal_core_depth} $ Crystal core depth\n')
        text.append(f'30    CZ {well_side_dl} $ Well side dead layer\n')
        text.append(f'31    PZ {well_bottom_dl} $ Well bottom dead layer\n')
        text.append(f'32    CZ {core_side_dl} $ Well side dead layer\n')
        text.append(f'33    PZ {core_bottom_dl} $ Well bottom dead layer\n')
        text.append(f'34    PZ {groove_bottom} $ Groove bottom\n')
        text.append(f'35    CZ {self.dimensions["groove_irad"]} $ Groove inner radius\n')
        text.append(f'36    CZ {self.dimensions["groove_orad"]} $ Groove outer radius\n')
        text.append(f'37    PZ {groove_dl_bottom} $ Groove dead layer bottom\n')
        text.append(f'38    CZ {groove_dl_inner_rad} $ Groove dead layer inner radius\n')
        text.append(f'39    CZ {groove_dl_outer_rad} $ Groove dead layer outer radius\n')
        text.append(f'40    PZ {contact_dl} $ Contact dead layer\n')
        text.append(f'41    KZ {front_bevel_apex} 1 1 $ Front bevel cone\n')
        text.append(f'42    KZ {front_bevel_dl_apex} 1 1 $ Front bevel dead layer cone\n')
        text.append(f'43    KZ {back_bevel_apex} 1 -1 $ Back bevel cone\n')
        text.append(f'44    KZ {back_bevel_dl_apex} 1 -1 $ Back bevel dead layer cone\n')

        text.append(f'50    PZ {front_insulator1} $ Front Insulator 1\n')
        text.append(f'51    PZ {front_insulator2} $ Front Insulator 2\n')
        text.append(f'52    CZ {side_insulator1} $ Side Insulator 1\n')
        text.append(f'53    CZ {side_insulator2} $ Side Insulator 2\n')
        text.append(f'54    PZ {back_insulator1} $ Back Insulator 1\n')
        text.append(f'55    PZ {back_insulator2} $ Back Insulator 2\n')

        text.append(f'60    PZ {holder_front} $ Holder front\n')
        text.append(f'61    PZ {holder_back} $ Holder back\n')
        text.append(f'62    CZ {holder_side} $ Holder side\n')
        text.append(f'63    PZ {holder_back_front} $ Holder back front surface\n')
        text.append(f'64    CZ {holder_ring_radius} $ Holder ring radius\n')
        text.append(f'65    PZ {holder_lip_back} $ Holder lip bottom\n')
        text.append(f'66    PZ {holder_ring1_front} $ Holder ring 1 front\n')
        text.append(f'67    PZ {holder_ring1_back} $ Holder ring 1 back\n')
        text.append(f'68    PZ {holder_ring2_front} $ Holder ring 2 front\n')
        text.append(f'69    PZ {holder_ring2_back} $ Holder ring 2 back\n')

        return text

    def cells(self, source, electrontrack):
        """
        The cell cards for the GCW detector.

        Parameters
        ----------
        source : Source
            The source that the geometry is used with

        electrontrack : bool
            If True electron will be enabled, if False electron tracking
            will be disabled.

        Returns
        -------
        text : List
            List containing the cell cards for the GCW detector.

        """
        mat_lib = MCNPMaterialLibrary()

        text = ['C detector cells\n']

        # Endcap front with and without a thin window
        if self.dimensions['win_rad'] > 0.0:
            text.append(f'1    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -8 -10 3 {self.importance(electrontrack)}  $ End cap front\n')
            text.append(f'2    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  2 -8 -3 4 {self.importance(electrontrack)}  $ End cap front lip\n')
            text.append(f'3    {mat_lib.number(self.dimensions["well_mat"])} -{mat_lib.density(self.dimensions["well_mat"])}  1 -2 -3 4 {self.importance(electrontrack)}  $ Window front lip\n')
        else:
            text.append(f'1    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -8 -10 4 {self.importance(electrontrack)}  $ End cap front\n')

        text.append(f'4    {mat_lib.number(self.dimensions["well_mat"])} -{mat_lib.density(self.dimensions["well_mat"])}  1 -7 -4 5 {self.importance(electrontrack)}  $ End cap well side\n')
        text.append(f'5    {mat_lib.number(self.dimensions["well_mat"])} -{mat_lib.density(self.dimensions["well_mat"])}  6 -7 -5 {self.importance(electrontrack)}  $ End cap well side\n')
        if source.well_source:
            text.append(f'6    {mat_lib.number("air")} -{source.air_density()}  1 -6 -5 {source.cell_numbers()} {self.importance(electrontrack)}  $ Air inside well\n')
        else:
            text.append(f'6    {mat_lib.number("air")} -{source.air_density()}  1 -6 -5 {self.importance(electrontrack)}  $ Air inside well\n')
        text.append(f'7    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])} 8 -11 9 -10 {self.importance(electrontrack)}  $ Side of End cap\n')
        text.append(f'8    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])} 11 -12 -10 {self.importance(electrontrack)}  $ Back of End cap\n')

        text.append(f'20    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -22 -23 -42 39 {self.importance(electrontrack)}  $ Front dead layer\n')
        text.append(f'21    {mat_lib.number("ge")} -{mat_lib.density("ge")} 23 -42 -44 -25 24 -22 {self.importance(electrontrack)}  $ Side dead layer\n')
        text.append(f'22    {mat_lib.number("ge")} -{mat_lib.density("ge")} 25 -21 -22 -44 {self.importance(electrontrack)}  $ Back dead layer\n')
        text.append(f'23    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 20 -27 -26 4 {self.importance(electrontrack)}  $ Well side air gap\n')
        text.append(f'24    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 7 -27 -4 {self.importance(electrontrack)}  $ Well bottom air gap\n')
        text.append(f'25    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 27 -29 -28 {self.importance(electrontrack)}  $ Core air gap\n')
        text.append(f'26    {mat_lib.number("ge")} -{mat_lib.density("ge")} 40 -31 26 -30 {self.importance(electrontrack)}  $ Well side dead layer\n')
        text.append(f'27    {mat_lib.number("ge")} -{mat_lib.density("ge")} 27 -31 28 -26 {self.importance(electrontrack)}  $ Well bottom dead layer\n')
        text.append(f'28    {mat_lib.number("ge")} -{mat_lib.density("ge")} 31 -33 28 -32 {self.importance(electrontrack)}  $ Core side dead layer\n')
        text.append(f'29    {mat_lib.number("ge")} -{mat_lib.density("ge")} 29 -33 -28 {self.importance(electrontrack)}  $ Core bottom dead layer\n')
        text.append(f'30    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 20 -34 35 -36 {self.importance(electrontrack)}  $ Vacuum in groove\n')
        text.append(f'31    {mat_lib.number("ge")} -{mat_lib.density("ge")} 34 -37 35 -36 {self.importance(electrontrack)}  $ Groove bottom dead layer\n')
        text.append(f'32    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -37 38 -35 {self.importance(electrontrack)}  $ Groove inner dead layer\n')
        text.append(f'33    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -37 36 -39 {self.importance(electrontrack)}  $ Groove outer dead layer\n')
        text.append(f'34    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -40 26 -38 {self.importance(electrontrack)}  $ Contact dead layer\n')
        text.append(f'35    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 20 -22 41 {self.importance(electrontrack)}  $ Vacuum outside front bevel\n')
        text.append(f'36    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -22 42 -41 {self.importance(electrontrack)}  $ Front bevel dead layer\n')
        text.append(f'37    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} -21 -22 43 {self.importance(electrontrack)}  $ Vacuum outside back bevel\n')
        text.append(f'38    {mat_lib.number("ge")} -{mat_lib.density("ge")} -21 -22 44 -43 {self.importance(electrontrack)}  $ Back bevel dead layer\n')
        text.append(f'40    {mat_lib.number("ge")} -{mat_lib.density("ge")} 20 -25 -24 #20 #23 #25 #28 #29 #30 #31 #32 #33\n')
        text.append(f'      #34 #35 #36 #37 #38 #(20 -31 -30) {self.importance(electrontrack, crystal=True)}  $ Active Crystal\n')

        text.append(f'50    {mat_lib.number(self.dimensions["insul_f_mat"])} -{self.dimensions["insul_f_den"]} 50 -20 4 -53 {self.importance(electrontrack)}  $ Front insulator 1\n')
        text.append(f'51    {mat_lib.number(self.dimensions["insul_f2_mat"])} -{self.dimensions["insul_f2_den"]} 51 -50 4 -53 {self.importance(electrontrack)}  $ Front insulator 2\n')
        text.append(f'52    {mat_lib.number(self.dimensions["insul_s_mat"])} -{self.dimensions["insul_s_den"]} 20 -21 22 -52 {self.importance(electrontrack)}  $ Side insulator 1\n')
        text.append(f'53    {mat_lib.number(self.dimensions["insul_s2_mat"])} -{self.dimensions["insul_s2_den"]} 20 -21 52 -53 {self.importance(electrontrack)}  $ Side insulator 2\n')
        text.append(f'54    {mat_lib.number(self.dimensions["insul_b_mat"])} -{self.dimensions["insul_b_den"]} 21 -54 -53 {self.importance(electrontrack)}  $ Back insulator 1\n')
        text.append(f'55    {mat_lib.number(self.dimensions["insul_b2_mat"])} -{self.dimensions["insul_b2_den"]} 54 -55 -53 {self.importance(electrontrack)}  $ Back insulator 2\n')

        text.append(f'60    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 60 -61 53 -62 {self.importance(electrontrack)}  $ Holder side\n')
        text.append(f'61    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 63 -61 -53 {self.importance(electrontrack)}  $ Holder back\n')
        text.append(f'62    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 55 -63 -53 {self.importance(electrontrack)}  $ Vacuum between insulator and holder back\n')
        text.append(f'63    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 60 -65 62 -64 {self.importance(electrontrack)}  $ Holder lip\n')
        text.append(f'64    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 66 -67 62 -64  {self.importance(electrontrack)}  $ Holder ring 1\n')
        text.append(f'65    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 68 -69 62 -64  {self.importance(electrontrack)}  $ Holder ring 2\n')

        text.append(f'70    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 8 -51 4 -53 {self.importance(electrontrack)}  $ Vacuum between insulator and holder back\n')
        text.append(f'71    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 8 -60 53 -9 {self.importance(electrontrack)}  $ Vacuum above holder\n')
        text.append(f'72    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 60 -61 64 -9 {self.importance(electrontrack)}  $ Vacuum between holder and endcap\n')
        text.append(f'73    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 65 -61 62 -64 #64 #65 {self.importance(electrontrack)}  $ Vacuum between holder rings\n')
        text.append(f'74    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} 61 -11 -9 {self.importance(electrontrack)}  $ Vacuum behind holder\n')

        return text

    def endcap_boundary(self):
        """
        The endcap boundary in MCNP

        Returns
        -------
        str
            Surfaces that describes the endcap boundary in MCNP.

        """
        return '(1 -10 -12)'

    def add_characterization_points(self, filename):
        """
        Add points in the well to the characterization points file.
        This was ported from the MCNP tcl script. One modification
        was made, the corner points include 90 degree points

        Parameters
        ----------
        filename : string
            The path to the points file.

        Returns
        -------
        None.

        """

        radial_points = 20
        corner_points = 20
        text = []

        # Adding points in well
        well_radius = self.dimensions['ec_well_radius']
        well_depth = self.dimensions['ec_well_depth']

        corner_angle = np.arctan(well_depth/well_radius) + np.pi / 2.0
        phi_step = np.pi/72.0
        r_step = np.log(500000.0)/439.0

        for i in range(37, 73):
            phi = i * phi_step
            if phi < corner_angle:
                max_radius = well_radius / np.sin(phi)
            else:
                max_radius = well_depth / np.cos(np.pi - phi)

            step = (max_radius - 0.1001) / (radial_points - 1)
            for j in range(0, radial_points):
                r = 0.1 + j * step
                p = phi / np.pi * 180.0
                text.append(f'{r:<12.6f}  {p:>10.6f}\n')

        # Adding points at the well end cap corner
        # Changed the first point to be 5 steps from the edge.
        well_radius *= 10.0
        first_point = int(np.floor(np.log(well_radius)/r_step)) - 5

        for i in range(32, 37):
            phi = i * phi_step
            for j in range(first_point, first_point + corner_points):
                r = np.exp(r_step*j)/10
                p = phi / np.pi * 180
                text.append(f'{r:<12.6f}  {p:>10.6f}\n')

        # Write to the file
        with open(filename, 'a') as file:
            file.writelines(text)
            file.close()

    def process_outfile(self, folder_name):
        """
        Removes the points in the well from the .out file and stores the well
        points in a separate file

        Ported from the MCNPtcl script

        Returns
        -------
        well_file : str
            The results from the MCNP simulations in the well.

        """

        out_filename = os.path.join(folder_name, f'{self.serialnumber}.out')
        well_filename = os.path.join(folder_name, f'{self.serialnumber}_well.out')
        temp_filename = os.path.join(folder_name, f'{self.serialnumber}_temp.out')

        well_radius = self.dimensions['ec_well_radius']
        well_depth = self.dimensions['ec_well_depth']

        max_well_distance = np.sqrt(well_radius**2 + well_depth**2)

        with open(out_filename, 'r') as out_file, open(well_filename, 'w') as well_file, open(temp_filename, 'w') as temp_file:
            for line in out_file:
                r = float(line.split()[0])
                phi = float(line.split()[1])
                if r < max_well_distance and phi > 90:
                    well_file.write(line)
                else:
                    temp_file.write(line)
            out_file.close()
            temp_file.close()
            well_file.close()

        shutil.copy(temp_filename, out_filename)
        os.remove(temp_filename)

        return well_filename

    def process_parfile(self, parfile_name, processed_name):
        """
        Add the vacuum efficiency in the well.

        Ported from MCNPtcl

        Parameters
        ----------
        processed_name : str
            Path to file that contains the MCNP calculations in the well.

        Returns
        -------
        None.

        """


        well_radius = self.dimensions['ec_well_radius']
        well_depth = self.dimensions['ec_well_depth']
        corner_angle = np.arctan(well_depth/well_radius) + np.pi / 2.0

        shutil.copy(parfile_name, f'{self.serialnumber}_outside_well.par')
        # with open(processed_name, 'r') as well_file, open(parfile_name, 'r+b') as parfile:
        #     content = parfile.read()
        #     position = 18
        #     minimumEnergy, maximumEnergy, numberOfEnergies = struct.unpack("ddh", content[:18])
        #     energies = struct.unpack("d" * self.numberOfEnergies, content[position:(position + 8 * self.numberOfEnergies)])
        #     for i, energy in enumerate(energies):

        par = parfile.Parfile(parfile_name)

        well_points = {}

        # read in the well points in a double nested dictionary
        with open(processed_name, 'r') as well_file:
            for line in well_file:
                res = experiment.Result.from_string(line)
                energy = well_points.get(res.energy, {})
                theta = energy.get(res.theta, ([], []))
                theta[0].append(res.r * 10.0)
                theta[1].append(res.eff)
                energy[res.theta] = theta
                well_points[res.energy] = energy

        # Create the cubic spline and interpolate at  the parfile points
        for energy, temp in well_points.items():
            vacuum_efficiency = par.get_vacuum_efficiency(energy)
            step_r = vacuum_efficiency.stepR
            for theta, value in temp.items():
                r = np.array(value[0])
                eff = np.array(value[1])
                cubic_spline = CubicSpline(r, eff)
                if np.deg2rad(theta) < corner_angle:
                    max_radius = 10 * well_radius / np.sin(np.deg2rad(theta))
                else:
                    max_radius = 10 * well_depth / np.cos(np.pi-np.deg2rad(theta))
                radii = []
                temp = 1
                counter = 0
                while temp < max_radius:
                    radii.append(temp)
                    counter += 1
                    temp = np.exp(counter*step_r)

                radii = np.array(radii)
                efficiencies = cubic_spline(radii)
                index = parfile.iround(theta / 2.5)
                vacuum_efficiency.vacuumEfficiency[:len(radii), index] = efficiencies

        par.write_parfile(parfile_name)


    def create_detectortxt(self, folder_name, ordernumber, customer):
        """
        Create the detector.txt file from the detector parameters.

        Parameters
        ----------
        folder_name : string
            The folder where the characterzition files are located.
        ordernumber : string
            The order number for the characterization.
        customer : string
            The customer.

        Returns
        -------
        None.

        """

        mat_lib = MCNPMaterialLibrary()
        crystal_mat, crystal_den = self.crystal_material(mat_lib)
        # kludge to get AEGIS to use a different end cap back material
        ec_back_mat, ec_back_den = self.endcap_back_material(mat_lib)
        with open(os.path.join(folder_name, 'detector.txt'), 'w') as det_text:
            det_text.write(f'# {ordernumber} - {customer} - {self.modelnumber} - S/N {self.serialnumber}\n')
            if self.dimensions['win_thick'] == self.dimensions['ec_face']:
                win_diameter = 0.0
                thin_window_xtal_gap = self.dimensions["ec_xtal_dist"]*10.0
            else:
                win_diameter = 20.0*self.dimensions["ec_well_radius"]
                # TODO: Understand this calculation, copied from MCNPtcl
                thin_window_xtal_gap = 5.0 * (self.dimensions['ec_face'] - self.dimensions['win_thick'] + self.dimensions["ec_xtal_dist"])
            ec_well_thick = (self.dimensions['ec_well_side'] + self.dimensions['ec_well_bottom']) / 2.0 * 10.0
            well_dl_thick = (self.dimensions['well_dl_side'] + self.dimensions['well_dl_bottom']) / 2.0 * 10.0
            det_text.write(f'{self.serialnumber},{self.dimensions["xtal_rad"]*20.0:.4g},{self.dimensions["xtal_len"]*10.0:.4g},{win_diameter:.4g},{self.dimensions["ec_rad"]*20.0:.4g},{self.dimensions["ec_len"]*10.0:.4g},{thin_window_xtal_gap:.4g},{self.dimensions["ec_xtal_dist"]*10.0:.4g},26,{self.serialnumber}.par,4,{self.dimensions["ec_well_radius"]*20:.4g},{self.dimensions["ec_well_depth"]*10:.4g},{ec_well_thick:.4g},{self.dimensions["well_radius"]*20:.4g},{self.dimensions["well_depth"]*10:.4g},{well_dl_thick:.4g},{self.dimensions["xtal_rad"]*20.0-0.1:.4g},{self.dimensions["xtal_len"]*10.0-0.1:.4g},  #\n')
            det_text.write(f'{crystal_mat},{self.dimensions["front_dl"]*10.0:.4g},{crystal_den}, #\n')
            if win_diameter > 0:
                det_text.write(f'{self.dimensions["well_mat"]},{self.dimensions["win_thick"]*10.0:.4g},{mat_lib.density(self.dimensions["well_mat"])}, #\n')
            else:
                det_text.write(',,, #\n')
            det_text.write(f'{self.dimensions["ec_mat"]},{self.dimensions["ec_face"]*10.0:.4g},{mat_lib.density(self.dimensions["ec_mat"])}, #\n')
            det_text.write(f'{crystal_mat},{self.dimensions["side_dl"]*10.0:.4g},{crystal_den}, #\n')
            holder_thick = self.holder_thickness()
            det_text.write(f'{self.dimensions["holder_mat"]},{holder_thick*10.0:.4g},{mat_lib.density(self.dimensions["holder_mat"])}, #\n')
            det_text.write(f'{self.dimensions["ec_mat"]},{self.dimensions["ec_side"]*10.0:.4g},{mat_lib.density(self.dimensions["ec_mat"])}, #\n')
            # The dead layer thickness is set so that the total detector volume is correct
            # this accounts for the detector well (Coax) and groove. Current calc doesn't account for the bevel (probably minimal effect)
            back_dl = self.back_dead_layer()
            det_text.write(f'{crystal_mat},{back_dl:.4g},{crystal_den}, #\n')
            det_text.write(f'{self.dimensions["holder_mat"]},{self.dimensions["holder_back"]*10.0:.4g},{mat_lib.density(self.dimensions["holder_mat"])}, #\n')
            det_text.write(f'{ec_back_mat},{self.dimensions["ec_back"]*10.0:.4g},{ec_back_den}\n')


class Generic(Detector):
    def __init__(self, serialnumber):
        """
        Class for generic detectors. The generic detector contains a cylindrical
        crystal with dead layers, a holder, three generic absorbers and an endcap
        with a thin window.

        Parameters
        ----------
        serialnumber : string
            This string will be the name of the parfile, for HPGe detectors it
            is the serial number but for generic detectors it usually is the
            name of the detector type. For example "NaIS2x2"

        Returns
        -------
        None.

        """
        super().__init__(serialnumber)
        self.modelnumber = 'Generic'
        self.header = 'Generic'
        self.low_energy_validation = True

    def validate_dimensions(self):
        """
        Dimension validation for the Generic detector.
        This function needs to be expanded

        Returns
        -------
        bool
            True if the detector passes all validation checks, false otherwise.
        str
            Error message to print if check is failed.

        """
        if self.dimensions['xtal_rad'] >= self.dimensions['ec_rad']:
            return False, 'Crystal Radius larger or equal to EC radius'

        return True, ''

    def holder_thickness(self):
        """
        The holder thickness of the generic detector

        Returns
        -------
        float
            The thickness of the holder.

        """
        return self.dimensions['holder_thick']

    def back_dead_layer(self):
        """
        The back dead layer of the generic detector

        Returns
        -------
        float
            The back dead layer.

        """
        return self.dimensions["back_dl"]

    def dcg_parameters(self):
        """
        The dcg parameters for the generic detector.
        It uses the BEGe model because the generic detector does not
        have a well.

        Returns
        -------
        text : List
            List of the dcg parameters for the generic detector.

        """
        mat_lib = MCNPMaterialLibrary()
        text =  ['~ModelNumber BE5030\n',
                 '\n',
                 f'xtal_rad {self.dimensions["xtal_rad"]}\n',
                 f'xtal_len {self.dimensions["xtal_len"]}\n',
                 f'front_dl {self.dimensions["front_dl"]}\n',
                 f'side_dl {self.dimensions["side_dl"]}\n',
                 f'back_dl {self.dimensions["back_dl"]}\n',
                 f'groove_depth {0.01}\n',
                 f'groove_irad {0.01}\n',
                 f'groove_orad {0.01}\n',
                 f'groove_dl {0.01}\n',
                 f'kludge {0.01}\n',
                 f'tophat_rad {0.01}\n',
                 f'tophat_dep {0.01}\n',
                 f'ec_xtal_dist {self.dimensions["ec_xtal_dist"]}\n',
                 f'ec_rad {self.dimensions["ec_rad"]}\n',
                 f'ec_len {self.dimensions["ec_len"]}\n',
                 f'ec_face {self.dimensions["ec_face"]}\n',
                 f'ec_side {self.dimensions["ec_side"]}\n',
                 f'ec_back {self.dimensions["ec_back"]}\n',
                 f'ec_mat {self.dimensions["ec_mat"]}\n',
                 f'win_rad {self.dimensions["win_rad"]}\n',
                 f'win_mat {self.dimensions["win_mat"]}\n',
                 f'win_thick {self.dimensions["win_thick"]}\n',
                 f'xtal_prot {0.01}\n',
                 f'holder_lippos {0.01}\n',
                 f'holder_mat Al\n',
                 f'holder_thick {self.dimensions["holder_thick"]}\n',
                 f'holder_lipthick {0.01}\n',
                 f'holder_lipwid {0.01}\n',
                 f'holder_back {self.dimensions["holder_back"]}\n',
                 f'cup_rad {0.01}\n',
                 f'cup_sidethick {0.01}\n',
                 f'cup_len {0.01}\n',
                 f'cup_backthick {0.01}\n',
                 f'insul_front {self.dimensions["insul_front"]}\n',
                 f'insul_f_mat {mat_lib.dcg_name(self.dimensions["insul_f_mat"])}\n',
                 f'insul_f_den {self.dimensions["insul_f_den"]}\n',
                 f'insul_front2 {self.dimensions["insul_front2"]}\n',
                 f'insul_f2_mat {mat_lib.dcg_name(self.dimensions["insul_f2_mat"])}\n',
                 f'insul_f2_den {self.dimensions["insul_f2_den"]}\n',
                 f'insul_side {self.dimensions["insul_side"]}\n',
                 f'insul_s_mat {mat_lib.dcg_name(self.dimensions["insul_s_mat"])}\n',
                 f'insul_s_den {self.dimensions["insul_s_den"]}\n',
                 f'insul_side2 {self.dimensions["insul_side2"]}\n',
                 f'insul_s2_mat {mat_lib.dcg_name(self.dimensions["insul_s2_mat"])}\n',
                 f'insul_s2_den {self.dimensions["insul_s2_den"]}\n',
                 f'insul_back {self.dimensions["insul_back"]}\n',
                 f'insul_b_mat {mat_lib.dcg_name(self.dimensions["insul_b_mat"])}\n',
                 f'insul_b_den {self.dimensions["insul_b_den"]}\n',
                 f'insul_back2 {self.dimensions["insul_back2"]}\n',
                 f'insul_b2_mat {mat_lib.dcg_name(self.dimensions["insul_b2_mat"])}\n',
                 f'insul_b2_den {self.dimensions["insul_b2_den"]}\n',
        ]
        return text

    def surfaces(self):
        """
        The surface cards for the Generic detector

        Returns
        -------
        text : List
            A list with the surface cards for the Generic detector.

        """
        # Varibles used to populate the surfaces in the
        window_front_face = self.dimensions['ec_face'] - self.dimensions['win_thick']
        endcap_inner_radius = self.dimensions['ec_rad'] - self.dimensions['ec_side']
        endcap_back_inside = self.dimensions['ec_len'] - self.dimensions['ec_back']
        front_dead_layer = self.dimensions['ec_xtal_dist'] + self.dimensions['front_dl']
        crystal_back = self.dimensions['ec_xtal_dist']+ self.dimensions['xtal_len']
        side_dead_layer = self.dimensions['xtal_rad'] - self.dimensions['side_dl']
        back_dead_layer = crystal_back - self.dimensions['back_dl']
        holder_side = self.dimensions['xtal_rad'] + self.dimensions['holder_thick']
        holder_back = crystal_back + self.dimensions['holder_back']
        front_ins_1 = self.dimensions['ec_xtal_dist'] - self.dimensions['insul_front']
        front_ins_2 = front_ins_1 - self.dimensions['insul_front2']
        front_ins_3 = front_ins_2 - self.dimensions['insul_front3']
        side_ins_1 = holder_side + self.dimensions['insul_side']
        side_ins_2 = side_ins_1 + self.dimensions['insul_side2']
        side_ins_3 = side_ins_2 + self.dimensions['insul_side3']
        back_ins_1 = holder_back + self.dimensions['insul_back']
        back_ins_2 = back_ins_1 + self.dimensions['insul_back2']
        back_ins_3 = back_ins_2 + self.dimensions['insul_back3']

        if self.dimensions["win_rad"] > 0.0:
            endcap_front = f'2    PZ {window_front_face} $ Thin window front face\n'
            endcap_front += f'3    CZ {self.dimensions["win_rad"]} $ Radius of thin window\n'
        else:
            endcap_front = ''


        text = ['C   Detector\n',
                '1    PZ 0    $ Front of Detector End Cap\n',
                f'{endcap_front}'
                f'4    PZ {self.dimensions["ec_face"]} $ Back of end cap face\n',
                f'5    CZ {endcap_inner_radius} $ Inner radius of end cap\n',
                f'6    CZ {self.dimensions["ec_rad"]} $ Outer radius of end cap\n',
                f'7    PZ {endcap_back_inside} $ Inside of end cap back\n',
                f'8    PZ {self.dimensions["ec_len"]} $ Outside of end cap back\n',
                f'9    PZ {self.dimensions["ec_xtal_dist"]} $ Crystal Front\n',
                f'10   PZ {front_dead_layer} $ Front dead layer\n',
                f'11   PZ {crystal_back} $ Back of crystal\n',
                f'12   CZ {self.dimensions["xtal_rad"]} $ Crystal radius\n',
                f'13   CZ {side_dead_layer} $ Side dead layer\n',
                f'14   PZ {back_dead_layer} $ Back dead layer\n',
                f'15   CZ {holder_side} $ Holder outer radius\n',
                f'16   PZ {holder_back} $ Holder back\n',
                f'20   PZ {front_ins_1} $ Front insulator 1\n',
                f'21   PZ {front_ins_2} $ Front insulator 2\n',
                f'22   PZ {front_ins_3} $ Front insulator 3\n',
                f'23   CZ {side_ins_1} $ Side insulator 1\n',
                f'24   CZ {side_ins_2} $ Side insulator 2\n',
                f'25   CZ {side_ins_3} $ Side insulator 3\n',
                f'26   PZ {back_ins_1} $ Back insulator 1\n',
                f'27   PZ {back_ins_2} $ Back insulator 2\n',
                f'28   PZ {back_ins_3} $ Back insulator 3\n',
]
        return text


    def cells(self, electrontrack):
        """
        The cell cards for the Generic detector.

        Parameters
        ----------
        electrontrack : bool
            If True electron will be enabled, if False electron tracking
            will be disabled.

        Returns
        -------
        text : List
            List containing the cell cards for the Generic detector.

        """
        mat_lib = MCNPMaterialLibrary()
        if self.dimensions['win_rad'] > 0.0:
            endcap_front = f'1    {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")}  1 -2 -3 {self.importance(electrontrack)}  $ Front thin window gap\n'
            endcap_front += f'2    {mat_lib.number(self.dimensions["win_mat"])} -{mat_lib.density(self.dimensions["win_mat"])}  2 -4 -3 {self.importance(electrontrack)}  $ thin window\n'
            endcap_front += f'3    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -4 3 -6 {self.importance(electrontrack)}  $ End cap lip\n'
        else:
            endcap_front = f'3    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])}  1 -4 -6 {self.importance(electrontrack)}  $ End cap front\n'

        text = ['C detector cells\n',
                f'{endcap_front}',
                f'4    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])} 3 -7 5 -6 {self.importance(electrontrack)}  $ Side of End cap\n',
                f'5    {mat_lib.number(self.dimensions["ec_mat"])} -{mat_lib.density(self.dimensions["ec_mat"])} 7 -8 -6 {self.importance(electrontrack)}  $ Back of End cap\n',
                f'6    {mat_lib.number(self.dimensions["xtal_mat"])} -{self.dimensions["xtal_den"]} 9 -10 -12 {self.importance(electrontrack)}  $ Front dead layer\n',
                f'7    {mat_lib.number(self.dimensions["xtal_mat"])} -{self.dimensions["xtal_den"]} 10 -14 -12 13 {self.importance(electrontrack)} $ Side dead layer\n',
                f'8    {mat_lib.number(self.dimensions["xtal_mat"])} -{self.dimensions["xtal_den"]} 14 -11 -12 {self.importance(electrontrack)} $ Back dead layer\n',
                f'9    {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 9 -11 -15 12 {self.importance(electrontrack)} $ Holder side\n',
                f'10   {mat_lib.number(self.dimensions["holder_mat"])} -{mat_lib.density(self.dimensions["holder_mat"])} 11 -16 -15 {self.importance(electrontrack)} $ Holder back\n',
                f'20   {mat_lib.number(self.dimensions["insul_f_mat"])} -{self.dimensions["insul_f_den"]} 20 -9 -23 {self.importance(electrontrack)} $ Holder back\n',
                f'21   {mat_lib.number(self.dimensions["insul_f2_mat"])} -{self.dimensions["insul_f2_den"]} 21 -20 -24 {self.importance(electrontrack)} $ Holder back\n',
                f'22   {mat_lib.number(self.dimensions["insul_f3_mat"])} -{self.dimensions["insul_f3_den"]} 22 -21 -25 {self.importance(electrontrack)} $ Holder back\n',
                f'23   {mat_lib.number(self.dimensions["insul_s_mat"])} -{self.dimensions["insul_s_den"]} 9 -16 -23 15 {self.importance(electrontrack)} $ Holder back\n',
                f'24   {mat_lib.number(self.dimensions["insul_s2_mat"])} -{self.dimensions["insul_s2_den"]} 20 -26 -24 23 {self.importance(electrontrack)} $ Holder back\n',
                f'25   {mat_lib.number(self.dimensions["insul_s3_mat"])} -{self.dimensions["insul_s3_den"]} 21 -27 -25 24 {self.importance(electrontrack)} $ Holder back\n',
                f'26   {mat_lib.number(self.dimensions["insul_b_mat"])} -{self.dimensions["insul_b_den"]} 16 -26 -23 {self.importance(electrontrack)} $ Holder back\n',
                f'27   {mat_lib.number(self.dimensions["insul_b2_mat"])} -{self.dimensions["insul_b2_den"]} 26 -27 -24 {self.importance(electrontrack)} $ Holder back\n',
                f'28   {mat_lib.number(self.dimensions["insul_b3_mat"])} -{self.dimensions["insul_b3_den"]} 27 -28 -25 {self.importance(electrontrack)} $ Holder back\n',
                f'40   {mat_lib.number(self.dimensions["xtal_mat"])} -{self.dimensions["xtal_den"]} 10 -14 -13 {self.importance(electrontrack, crystal=True)} $ Crystal Active Volume\n',
                f'41   {mat_lib.number("det_vacuum")} -{mat_lib.density("det_vacuum")} (3 -22 -5):(22 -28 25 -5):(28 -7 -5) {self.importance(electrontrack)} $ Vacuum inside end cap\n',

        ]
        return text

    def endcap_boundary(self):
        """
        The endcap boundary in MCNP

        Returns
        -------
        str
            Surfaces that describes the endcap boundary in MCNP.

        """
        return '(1 -8 -6)'

    def crystal_material(self, mat_lib):
        """
        The name and density for the crystal material of the generic detector.
        The generic detector gets the crystal material and density
        from the xtal_mat and xtal_den parameters.

        Parameters
        ----------
        mat_lib : MCNPMaterialLibrary
            A material library.

        Returns
        -------
        string
            The crystal material name.
        float
            The crystal material density.

        """
        return self.dimensions['xtal_mat'], self.dimensions['xtal_den']


class MCNPMaterialLibrary:
    def __init__(self):
        """
        Class to map material names to MCNP material numbers, default densities and isocs
        material fractions.
        This should ideally parse the information from the spreadsheet instead of
        hardcoding them.

        Returns
        -------
        None.

        """
        self.materials = {'c':MCNPMaterial(1, 2.62),
                          'be':MCNPMaterial(2, 1.85),
                          'air':MCNPMaterial(3, 0.0012, 'N:78.50%O:21.1%AR:0.40%[Air]'),
                          'al':MCNPMaterial(4, 2.7, 'Al:100%[Al]', 'Al'),
                          'ge':MCNPMaterial(5, 5.35),
                          'pb':MCNPMaterial(6, 11.4),
                          'mg':MCNPMaterial(7, 1.74),
                          'water':MCNPMaterial(8, 1.0),
                          'delrin':MCNPMaterial(9, 1.45),
                          'cu':MCNPMaterial(10, 8.96),
                          'teflon':MCNPMaterial(11, 2.1, 'C:33.33%F:66.67%[Teflon]'),
                          'mylar':MCNPMaterial(12, 1.4),
                          'w':MCNPMaterial(13, 17.0),
                          'polycarb':MCNPMaterial(14, 1.17),
                          'glassfiber':MCNPMaterial(15, 0.23),
                          'ss':MCNPMaterial(16, 7.8, isocs_name='304ss'),
                          'kapton':MCNPMaterial(17, 2.1, 'H:4.81%C:57.75%N:7.49%O:29.95%[Kapton]'),
                          'porousglass':MCNPMaterial(18, 1.85),
                          'ceramic':MCNPMaterial(22, 2.0),
                          'in':MCNPMaterial(23, 7.31),
                          'ti':MCNPMaterial(24, 4.506),
                          'det_vacuum':MCNPMaterial(3, 0.000012),
                          'char_vacuum':MCNPMaterial(3, 1.2e-10),
                          'cllbc':MCNPMaterial(25, 4.08),
                          }

    def material(self, name):
        return self.materials[name.lower()]

    def number(self, name):
        return self.material(name).number

    def density(self, name):
        return self.material(name).density

    def dcg_name(self, name):
        return self.material(name).dcg_name

    def isocs_name(self, name):
        return self.material(name).isocs_name

class MCNPMaterial:
    def __init__(self, number, density, dcg_name='', isocs_name=''):
        """
        Contains information about a material in the MCNP material library

        Parameters
        ----------
        number : integer
            The integer number that is used for the material definition in MCNP.
        density : float
            Default density.
        dcg_name : string, optional
            The MakeDCGTools formated mass fractions. The default is ''.
        isocs_name : string, optional
            The name in the ISOCS mu library. The default is ''.

        Returns
        -------
        None.

        """
        self.number = number
        self.density = density
        self.dcg_name = dcg_name
        self.isocs_name = isocs_name
