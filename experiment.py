# -*- coding: utf-8 -*-
"""
Created on Mon Dec  2 08:17:36 2019

@author: HPersson
"""

import datetime
import ctypes
import os
import numpy as np
import collections
import glob
import shutil
import tkinter as tk
from tkinter import ttk
import subprocess
from sources import ZeroD, NinetyD, OneThirtyFiveD, DC, DF, DR, FortyFiveD, PointSource, WE
import isocs_utility_functions as utilities
from detector import AegisBEGe, AegisCoax, Generic, GCW
import mcnp

class Experiment:
    def __init__(self, detector, ordernumber, folder_name, simtype='full', errlimit=0.01, defaulthist=35000, maxhist=1000000,
                 queue='alpha', coorname=None, electrontrack=False, debug=False,
                 full_detector=True, customer='', priority=1, max_submitted=50,
                 max_lost_particles=10, low_energy_validation=True):
        """
        Class to controll all parameters related to running iterations and
        MCNP loop.

        Parameters
        ----------
        detector : Detector
            The detector that is used for this characterization.
        ordernumber : String
            The order number used for the order.
        folder_name : String
            Path to the folder that contains all files used for the characterization.
        simtype : String, optional
            The simulation type, currently only full is supported, legacy tcl script
            supported bni as well. The default is 'full'.
        errlimit : float, optional
            The relative uncertainty limit for convergence in MCNP. The default is 0.01.
        defaulthist : integer, optional
            The starting number of histories for the simulation. The default is 35000.
        maxhist : integer, optional
            The maximum number of histories . The default is 1000000.
        queue : string, optional
            The name of the queue to be used. 'alpha' and 'bravo' is supported. The default is 'alpha'.
        coorname : string, optional
            The type of experiment, currently not used but the old tcl code supports this option. The default is None.
        electrontrack : bool, optional
            If True electron tracking is used in the simulations, if false electron tracking is turned off. The default is False.
        debug : bool, optional
            If true the MCNP output files are stored in the debug folder, if False the MCNP output files are deleted. The default is False.
        full_detector : bool, optional
            If true the directional bias illuminates the entire detector, if false only the crystal is illuminated. The default is True.
        customer : string, optional
            The name of the customer, will be written in the detctor.txt file. The default is ''.
        priority : string, optional
            The priority of the files sent to the queue. The default is 1.
        max_submitted : integer, optional
            The maximum number of files that is submitted in before checking if the manager is ready to accept more files. The default is 50.
        max_lost_particles : integer, optional
            Maximum lost particles for the MCNP simulations, increasing this number can help for characterizations with high Z materials. The default is 10.
        low_energy_validation : bool, optional
            If True the low energies are used in the forward geometries. The default is True.

        Returns
        -------
        None.

        """
        self.customer = customer
        self.ordernumber = ordernumber
        self.simtype = simtype
        self.errlimit = errlimit
        self.defaulthist = defaulthist
        self.maxhist = maxhist
        self.queue = queue
        self.folder_name = folder_name
        self.coorname = coorname
        self.electrontrack = electrontrack
        self.debug = debug
        self.full_detector = full_detector
        self.detector = detector
        self.sources = []
        self.priority = priority
        self.max_submitted = max_submitted
        self.max_lost_particles = max_lost_particles
        self.low_energy_validation = low_energy_validation

    def write_config_page(self, sheet):
        """
        This method writes the experiment parameters to the config sheet

        Parameters
        ----------
        sheet : Sheet
            The config sheet.

        Returns
        -------
        None.

        """
        table= [['~serialnumber', self.detector.serialnumber,'','','',''],
             ['~modelnumber', self.detector.modelnumber,'','','',''],
             ['~ordernumber', self.ordernumber,'','','',''],
             ['~customer', self.customer,'','','',''],
             ['~coorname', 'expt','','','',''],
             ['~simtype', self.simtype,'','','',''],
             ['~errlimit', self.errlimit,'','','',''],
             ['~defaulthist', self.defaulthist,'','','',''],
             ['~maxhist', self.maxhist,'','','',''],
             ['~queue', self.queue,'','','',''],
             ['~electrontrack', self.electrontrack,'','','',''],
             ['#Start', '','', 'Low Limit', 'High Limit', 'Free']]

        for key, value in self.detector.dimensions.items():
            table.append([key, str(value[0]),str(value[1]),'','',''])

        table.append(['#End', '','','','',''])

        sheet.range('A1').value = table
        utilities.set_low_energy_validation(sheet.book, self.detector.low_energy_validation)

    @classmethod
    def extract_from_config_sheet(cls, config_sheet):
        """
        Extracts the relevant parameters from the config sheet.

        Parameters
        ----------
        config_sheet : Sheet
            The config sheet.

        Raises
        ------
        ValueError
            If the config sheet is missing required keywords.

        Returns
        -------
        detector : Detector
            The detector that is used for this characterization.
        ordernumber : String
            The order number used for the order.
        folder_name : String
            Path to the folder that contains all files used for the characterization.
        simtype : String
            The simulation type, currently only full is supported, legacy tcl script
            supported bni as well.
        errlimit : float
            The relative uncertainty limit for convergence in MCNP.
        defaulthist : integer
            The starting number of histories for the simulation.
        maxhist : integer
            The maximum number of histories.
        queue : string
            The name of the queue to be used. 'alpha' and 'bravo' is supported.
        coorname : string
            The type of experiment, currently not used but the old tcl code supports this option.
        electrontrack : bool
            If True electron tracking is used in the simulations, if false electron tracking is turned off.
        debug : bool
            If true the MCNP output files are stored in the debug folder, if False the MCNP output files are deleted.
        full_detector : bool
            If true the directional bias illuminates the entire detector, if false only the crystal is illuminated.
        customer : string
            The name of the customer, will be written in the detctor.txt file.

        """
        start_row = utilities.find_tag_in_column('#Start', config_sheet, 'A')
        end_row = utilities.find_tag_in_column('#End', config_sheet, 'A')
        table = config_sheet.range((1, 1), (start_row - 1, 2))
        model = ordernumber = serialnumber = simtype = defaulthist = maxhist = queue = None
        # Defaults
        customer = ''
        debug = False
        fulldetector = True
        coorname = 'expt'
        for row in table.rows:
            if row[0].value == '~serialnumber':
                serialnumber = row[1].options(numbers=lambda x: str(int(x))).value
            if row[0].value == '~coorname':
                coorname = row[1].value
            elif row[0].value == '~simtype':
                simtype = row[1].value
            elif row[0].value == '~errlimit':
                errlimit = float(row[1].value)
            elif row[0].value == '~defaulthist':
                defaulthist = int(row[1].value)
            elif row[0].value == '~maxhist':
                maxhist = int(row[1].value)
            elif row[0].value == '~queue':
                queue = row[1].value
            elif row[0].value == '~electrontrack':
                electrontrack = bool(row[1].value)
            elif row[0].value == '~debug':
                debug = True
            elif row[0].value == '~modelnumber':
                model = row[1].value
            elif row[0].value == '~fulldetector':
                fulldetector = bool(row[1].value)
            elif row[0].value == '~customer':
                customer = row[1].value if row[1].value is not None else ''
            elif row[0].value == '~ordernumber':
                ordernumber = row[1].options(numbers=lambda x: str(int(x))).value

        if model == None:
            raise ValueError('modelnumber keyword is missing')
        if serialnumber == None:
            raise ValueError('serialnumber keyword is missing')
        if ordernumber == None:
            raise ValueError('ordernumber keyword is missing')
        if simtype == None:
            raise ValueError('simtype keyword is missing')
        if defaulthist == None:
            raise ValueError('defaulthist keyword is missing')
        if maxhist == None:
            raise ValueError('maxhist keyword is missing')
        if queue == None:
            raise ValueError('queue keyword is missing')

        if model.lower() == 'aegis-bege5030':
            detector = AegisBEGe(serialnumber)
        elif model.lower() == 'aegis-gc40':
            detector = AegisCoax(serialnumber, 'GC')
        elif model.lower() == 'aegis-gx40':
            detector = AegisCoax(serialnumber, 'GX')
        elif model.lower() == 'generic':
            detector = Generic(serialnumber)
        elif model.lower().startswith('gcw'):
            detector = GCW(serialnumber, model)
        else:
            raise ValueError(f'Unknown model: {model}')

        table = config_sheet.range((start_row + 1, 1), (end_row - 1, 2))
        for row in table.rows:
            detector.dimensions[row[0].value] = row[1].value

        return detector, ordernumber, simtype, errlimit, defaulthist, maxhist, queue, coorname, electrontrack, debug, fulldetector, customer


class Iteration(Experiment):
    def __init__(self, detector, ordernumber, folder_name, simtype='full', errlimit=0.01, defaulthist=35000, maxhist=1000000,
                 queue='alpha', coorname=None, electrontrack=False, debug=False,
                 full_detector=True, customer='', low_energy_validation=True):
        """
        Class to handle iterations.

        Parameters
        ----------
        detector : Detector
            The detector that is used for this characterization.
        ordernumber : String
            The order number used for the order.
        folder_name : String
            Path to the folder that contains all files used for the characterization.
        simtype : String, optional
            The simulation type, currently only full is supported, legacy tcl script
            supported bni as well. The default is 'full'.
        errlimit : float, optional
            The relative uncertainty limit for convergence in MCNP. The default is 0.01.
        defaulthist : integer, optional
            The starting number of histories for the simulation. The default is 35000.
        maxhist : integer, optional
            The maximum number of histories . The default is 1000000.
        queue : string, optional
            The name of the queue to be used. 'alpha' and 'bravo' is supported. The default is 'alpha'.
        coorname : string, optional
            The type of experiment, currently not used but the old tcl code supports this option. The default is None.
        electrontrack : bool, optional
            If True electron tracking is used in the simulations, if false electron tracking is turned off. The default is False.
        debug : bool, optional
            If true the MCNP output files are stored in the debug folder, if False the MCNP output files are deleted. The default is False.
        full_detector : bool, optional
            If true the directional bias illuminates the entire detector, if false only the crystal is illuminated. The default is True.
        customer : string, optional
            The name of the customer, will be written in the detctor.txt file. The default is ''.
        low_energy_validation : bool, optional
            If True the low energies are used in the forward geometries. The default is True.

        Returns
        -------
        None.

        """
        super().__init__(detector, ordernumber, folder_name, simtype, errlimit,
             defaulthist, maxhist, queue, coorname, electrontrack, debug,
             full_detector, customer, priority=1, max_submitted=50,
             max_lost_particles=10, low_energy_validation=low_energy_validation)

    @classmethod
    def from_config_sheet(cls, config_sheet, folder_name, low_energy_validation):
        """
        Extracts the relevant parameters from the configuration sheet.

        Parameters
        ----------
        config_sheet : Sheet
            The config sheet.
        folder_name : string
            Path to folder containing all characterization files.
        low_energy_validation : bool
            If True the low energies are used in the forward geometries. The default is True.

        Returns
        -------
        Iterations
            An instance of the Iterations class with the parameters fromt the configuration sheet.

        """

        detector, ordernumber, simtype, errlimit, defaulthist, max_hist, queue, coorname, electrontrack, debug, fulldetector, customer = Experiment.extract_from_config_sheet(config_sheet)

        return cls(detector, ordernumber, folder_name, simtype=simtype, errlimit=errlimit, defaulthist=defaulthist, maxhist=max_hist,
                 queue=queue, coorname=coorname, electrontrack=electrontrack, debug=debug,
                 full_detector=fulldetector, customer=customer, low_energy_validation=low_energy_validation)

    @classmethod
    def default_parameters(cls, serial_number, model, init_sheet, standard_sheet, folder_name, order_number):
        """
        Creates an instance of the Iteration class with the default parameters.


        Parameters
        ----------
        serial_number : string
            The serial number of the detector.
        model : string
            The detector model.
            Supported models are aegis-bege5030, aegis-gc40, aegis-gx40, and generic
        init_sheet : Sheet
            The initialization sheet.
        standard_sheet : Sheet
            The standard cunfiguration sheet.
        folder_name : string
            Path to the folder that contains all characterization files.
        order_number : string
            The order number for the characterization.

        Raises
        ------
        ValueError
            If the model is not one of the supported models.

        Returns
        -------
        Itereations
            An instance of the Iterations class with default parameters.

        """
        simtype = 'full'
        errlimit = 0.01
        defaulthist = 35000
        maxhist = 1000000
        queue = 'alpha'
        coorname = 'expt'
        electrontrack = False
        debug = False
        full_detector = True
        customer = ''

        if model.lower() == 'aegis-bege5030':
            detector = AegisBEGe(serial_number)
        elif model.lower() == 'aegis-gc40':
            detector = AegisCoax(serial_number, 'GC')
        elif model.lower() == 'aegis-gx40':
            detector = AegisCoax(serial_number, 'GX')
        elif model.lower() == 'generic':
            detector = Generic(serial_number)
        elif model.lower().startswith('gcw'):
            detector = GCW(serial_number, model)
        else:
            raise ValueError(f'Unknown model: {model}')
        detector.initial_detector_dimensions(init_sheet, standard_sheet)

        return cls(detector, order_number, folder_name, simtype=simtype, errlimit=errlimit,
                   defaulthist=defaulthist, maxhist=maxhist, queue=queue, coorname=coorname,
                   electrontrack=electrontrack, debug=debug,
                   full_detector=full_detector, customer=customer, low_energy_validation=detector.low_energy_validation)

    def run(self, iteration_sheet, standard_sheet):
        """
        Run an iteration and populate the results on the iteration sheet

        Parameters
        ----------
        iteration_sheet : Sheet
            The iteration sheet.
        standard_sheet : Sheet
            The standard configuration sheet.

        Returns
        -------
        None.

        """

        if not self.detector.validate_model(standard_sheet):
            return

        if utilities.mcnp_running(iteration_sheet) == 1:
            ctypes.windll.user32.MessageBoxW(0, f'MCNP is already running for this detector', 'MCNP running', 0)
            return

        start_time = datetime.datetime.now()
        start_row = utilities.find_tag_in_column('SPECTRUM', iteration_sheet, 'A') + 1
        end_row = utilities.find_tag_in_column('PARAMETER', iteration_sheet, 'A') - 1
        geometry_range = iteration_sheet.range((start_row, 1), (end_row, 1))
        energy_range = iteration_sheet.range((start_row, 2), (end_row, 2))
        counter = 0
        queued = []
        completed = {}
        sample_created = set()

        # create the sources that is used for the iteration
        for geometry, energy in zip(geometry_range, energy_range):
            temp = None
            if '0D' == geometry.value:
                temp = ZeroD(float(energy.value), counter, self.defaulthist, self.detector.dimensions["sou_pt_arm"], self.detector.dimensions["sou_pt_pivot"])
            elif '90D' == geometry.value:
                temp = NinetyD(float(energy.value), counter, self.defaulthist, self.detector.dimensions["sou_pt_arm"], self.detector.dimensions["sou_pt_pivot"])
            elif '135D' == geometry.value:
                temp = OneThirtyFiveD(float(energy.value), counter, self.defaulthist, self.detector.dimensions["sou_pt_arm"], self.detector.dimensions["sou_pt_pivot"])
            elif 'DC' == geometry.value:
                temp = DC(float(energy.value), counter, self.defaulthist)
            elif 'DF' == geometry.value:
                temp = DF(float(energy.value), counter, self.defaulthist)
            elif 'RELEFF' == geometry.value:
                temp = DR(float(energy.value), counter, self.defaulthist)
            elif '45D' == geometry.value:
                temp = FortyFiveD(float(energy.value), counter, self.defaulthist, self.detector.dimensions["sou_pt_arm"], self.detector.dimensions["sou_pt_pivot"])
            elif 'WE' == geometry.value:
                temp = WE(float(energy.value), counter, self.defaulthist, self.detector.dimensions['ec_well_depth'])

            if temp is not None:
                queued.append(temp)
                counter += 1

            # Write the example MCNP file=
            if geometry.value not in sample_created:
                temp.energy = 1000.0
                file_name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_{temp.type}_sample.i')
                self.detector.create_input_file(temp, file_name, self.full_detector)
                sample_created.add(geometry.value)
                temp.energy = energy.value

        # set the inqueue outqueue folders
        if self.queue.lower() == 'alpha':
            inque_folder = r'P:\ISOCSProduction\Manager\InQueue'
            outque_folder = r'P:\ISOCSProduction\Manager\OutQueue'
        elif self.queue.lower() == 'bravo':
            inque_folder = r'P:\ISOCSProduction\ManagerB\InQueue'
            outque_folder = r'P:\ISOCSProduction\ManagerB\OutQueue'
        else:
            ctypes.windll.user32.MessageBoxW(0, f'Unknown queue: {self.interation_queue}', 'Unknown queue', 0)
            return

        name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_iter.out')
        log_name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_iter.log')
        with open(name, 'w') as outfile, open(log_name, 'w') as logfile:

            if self.debug:
                if not os.path.isdir(os.path.join(self.folder_name, 'debug')):
                    os.mkdir(os.path.join(self.folder_name, 'debug'))

            # Set the flag indicating that MCNP is running.
            utilities.set_mcnp_running(iteration_sheet, 1)

            # Launch the Tk windows that handles submitting and recieving MCNP files
            logfile.write(f'{datetime.datetime.now()} Starting Iteration\n')
            app = Window(self, queued, completed,
                         inque_folder, outque_folder, outfile, logfile)

            app.after(100, app.process_mcnp)
            app.mainloop()
            app.destroy()

            # Clear the flag indicating that MCNP is running.
            utilities.set_mcnp_running(iteration_sheet, 0)
            logfile.write(f'{datetime.datetime.now()} Iteration finished\n')

            if app.aborted:
                return

            if app.lost_particles:
                ctypes.windll.user32.MessageBoxW(0, f'Lost particles, check the inputs', 'Lost particles', 0)
                return


            # Compare the modeled and measured efficiencies
            outfile.seek(0)
            outfile.truncate()
            previous_type = ''
            column = iteration_sheet.range((start_row + 11, 1), (start_row + 11, iteration_sheet.cells.last_cell.column)).end('right').column + 1
            eff_range = iteration_sheet.range((start_row, 3), (end_row, 3))
            unc_range = iteration_sheet.range((start_row, 4), (end_row, 4))
            res_range = iteration_sheet.range((start_row, column), (end_row, column + 1))
            efficiencies = np.zeros(len(eff_range))
            one_sigma = 0
            two_sigma = 0
            valid_measurements = 0

            experiments = collections.OrderedDict()
            energy_counter = 1
            for counter in sorted(completed):
                res = completed[counter]
                if res.type != previous_type:
                    outfile.write(f'Experimental Point: {res.type}\n')
                    if previous_type != '':
                        experiments[completed[counter - 1]] = energy_counter
                        energy_counter = 1
                    previous_type = res.type
                else:
                    energy_counter += 1
                outfile.write(str(res) + '\n')
                if res.type == 'DR':
                    eff_ratio = res.eff / eff_range[counter].value / 0.0012 if eff_range[counter].value is not None else 0
                else:
                    eff_ratio = res.eff / eff_range[counter].value if eff_range[counter].value is not None else 0
                #TODO: decide on which uncertainty to display on the tab
                # The CharTables tab assumes that the relative uncertainty in the ratio is displayed
                # leaving it as that for now.
                rel_unc_ratio = np.sqrt((res.unc)**2 + (unc_range[counter].value/100.0)**2 + res.source.geometry_error**2) if unc_range[counter].value is not None else 0
                unc_ratio = eff_ratio * rel_unc_ratio
                res_range[counter, 0].value = eff_ratio
                res_range[counter, 1].value = rel_unc_ratio
                if not self.low_energy_validation and res.energy < utilities.low_energy_cutoff.get(res.type, 13.8):
                    res_range[counter, 0].api.Interior.ColorIndex = 20
                    res_range[counter, 1].api.Interior.ColorIndex = 20
                elif np.abs(eff_ratio - 1.0) > 2.0*unc_ratio:
                    one_sigma += 1
                    two_sigma += 1
                    res_range[counter, 0].api.Interior.ColorIndex = 3
                    valid_measurements += 1
                elif np.abs(eff_ratio - 1.0) > unc_ratio:
                    one_sigma += 1
                    res_range[counter, 0].api.Interior.ColorIndex = 6
                    valid_measurements += 1
                else:
                    valid_measurements += 1
                efficiencies[counter] = eff_ratio

        experiments[res] = energy_counter
        end_time = datetime.datetime.now()
        iteration = int((column - 5) / 2 + 1)
        chart = iteration_sheet.charts[0]
        first = True
        first_energy = start_row
        for res in experiments:
            energies = experiments[res]
            last_energy = first_energy + energies - 1
            a = iteration_sheet.range((first_energy, 2)).get_address(False, False)
            b = iteration_sheet.range((last_energy,2)).get_address(False, False)
            c = iteration_sheet.range((first_energy, column)).get_address(False, False)
            d = iteration_sheet.range((last_energy, column)).get_address(False, False)
            range_string = f'{a}:{b}, {c}:{d}'
            chart_range = iteration_sheet.range(range_string)
            e = iteration_sheet.range((first_energy, column+1)).get_address(False, False)
            f = iteration_sheet.range((last_energy,column+1)).get_address(False, False)
            error_range_string = f'{e}:{f}'
            error_range = iteration_sheet.range(error_range_string)
            error_range_array = utilities.range_to_array(error_range, float)
            if first:
                chart.set_source_data(chart_range)
                chart.title = ''
                first = False
                number = chart.api[1].SeriesCollection().count
            else:
                chart.api[1].SeriesCollection().Add(f'{iteration_sheet.range((first_energy, column)).get_address(False, False)}:{iteration_sheet.range((last_energy,column)).get_address(False, False)}')
                number = chart.api[1].SeriesCollection().count
                chart.api[1].SeriesCollection(number).XValues = utilities.range_to_array(iteration_sheet.range((first_energy, 2), (last_energy, 2)), float)
            chart.api[1].SeriesCollection(number).Name = res.source.type
            chart.api[1].SeriesCollection(number).MarkerStyle = res.source.marker
            chart.api[1].SeriesCollection(number).MarkerSize = 4
            chart.api[1].SeriesCollection(number).Border.ColorIndex = res.source.FColor
            chart.api[1].SeriesCollection(number).MarkerBackgroundColorIndex = res.source.BColor
            chart.api[1].SeriesCollection(number).MarkerForegroundColorIndex = res.source.FColor
            chart.api[1].SeriesCollection(number).ErrorBar(1, 1, -4114, error_range_array, error_range_array)
            chart.api[1].SeriesCollection(number).ErrorBars.EndStyle = 1
            chart.api[1].SeriesCollection(number).ErrorBars.Border.ColorIndex = res.source.FColor
            first_energy = last_energy + 1

        summary_range = iteration_sheet.range((start_row - 3, column), (start_row - 1, column + 1))
        summary_range[0, 0].value = np.mean(efficiencies)
        summary_range[1, 0].value = np.std(efficiencies)
        summary_range[2, 0].value = f'Iteration {iteration}:'
        summary_range[2, 1].value = f'{int((end_time - start_time).total_seconds())}'
        summary_range[0, 1].value = f'{np.abs(np.mean(efficiencies) - 1.0)*np.std(efficiencies)}'

        deviations_range = iteration_sheet.range((9, 15), (11, 17))
        one_sigma_ratio = one_sigma / valid_measurements
        two_sigma_ratio = two_sigma / valid_measurements
        deviations_range[0, 1].value = one_sigma_ratio
        deviations_range[1, 1].value = two_sigma_ratio
        if one_sigma_ratio < 0.32 and two_sigma_ratio < 0.05:
            deviations_range[2, 0].value = 'Fully passes validation criteria'
            deviations_range[2, :].api.Interior.ColorIndex = 4
        elif one_sigma_ratio < 0.5 and two_sigma_ratio < 0.1:
            deviations_range[2, 0].value = 'Approaching validation criteria'
            deviations_range[2, :].api.Interior.ColorIndex = 6
        else:
            deviations_range[2, 0].value = 'Not validated'
            deviations_range[2, :].api.Interior.ColorIndex = 3

        last_row = iteration_sheet.range('A' + str(iteration_sheet.cells.last_cell.row)).end('up').row

        key_range = iteration_sheet.range((end_row + 1, 1), (last_row, 1))
        if iteration == 1:
            previous = 2
        else:
            previous = column - 2
        previous_range = iteration_sheet.range((end_row + 1, previous), (last_row, previous))
        current_range = iteration_sheet.range((end_row + 1, column), (last_row, column))

        for key, previous, current in zip(key_range, previous_range, current_range):
            if key.value == 'PARAMETER':
                current.value = 'PARAMETER'
                continue
            elif key.value.startswith('~serial') or key.value.startswith('~model'):
                current.value = getattr(self.detector, key.value[1:], '')

            elif key.value.startswith('~'):
                current.value = getattr(self, key.value[1:], '')

            elif key.value.startswith('#'):
                current.value = ''

            else:
                current.value = self.detector.dimensions[key.value]

            if previous.value != current.value:
                current.api.Interior.ColorIndex = 4

        table = [['MCNPEffic', 'Error']]
        for counter in sorted(completed):
            table.append([float(completed[counter].eff), float(completed[counter].unc)])

        iteration_sheet.range(last_row + 5, column).value = table


class Characterization(Experiment):
    def __init__(self, detector, ordernumber, folder_name, simtype='full', errlimit=0.01, defaulthist=100000, maxhist=100000000,
                 queue='alpha', coorname=None, electrontrack=False, debug=False,
                 full_detector=True, customer='', low_energy_validation=True,
                 max_lost_particles=100):
        """


        Parameters
        ----------
        detector : Detector
            The detector that is used for this characterization.
        ordernumber : String
            The order number used for the order.
        folder_name : String
            Path to the folder that contains all files used for the characterization.
        simtype : String, optional
            The simulation type, currently only full is supported, legacy tcl script
            supported bni as well. The default is 'full'.
        errlimit : float, optional
            The relative uncertainty limit for convergence in MCNP. The default is 0.01.
        defaulthist : integer, optional
            The starting number of histories for the simulation. The default is 100000.
        maxhist : integer, optional
            The maximum number of histories . The default is 100000000.
        queue : string, optional
            The name of the queue to be used. 'alpha' and 'bravo' is supported. The default is 'alpha'.
        coorname : string, optional
            The type of experiment, currently not used but the old tcl code supports this option. The default is None.
        electrontrack : bool, optional
            If True electron tracking is used in the simulations, if false electron tracking is turned off. The default is False.
        debug : bool, optional
            If true the MCNP output files are stored in the debug folder, if False the MCNP output files are deleted. The default is False.
        full_detector : bool, optional
            If true the directional bias illuminates the entire detector, if false only the crystal is illuminated. The default is True.
        customer : string, optional
            The name of the customer, will be written in the detctor.txt file. The default is ''.
        low_energy_validation : bool, optional
            If True the low energies are used in the forward geometries. The default is True.
        Returns
        -------
        None.

        """
        super().__init__(detector, ordernumber, folder_name, simtype, errlimit,
             defaulthist, maxhist, queue, coorname, electrontrack, debug,
             full_detector, customer, priority=2, max_submitted=50,
             max_lost_particles=max_lost_particles, low_energy_validation=low_energy_validation)
        self.parfile_energies = [10, 12, 16, 22, 32, 45, 60, 80, 100, 122, 186,
                                 300, 500, 662, 898, 1173, 1332, 1836, 3000,
                                 7000]


    @classmethod
    def from_config_sheet(cls, config_sheet, char_sheet, folder_name, low_energy_validation):
        """
        Extracts the relevant parameters from the configuration sheet.

        Parameters
        ----------
        config_sheet : Sheet
            The config sheet.
        folder_name : string
            Path to folder containing all characterization files.
        low_energy_validation : bool
            If True the low energies are used in the forward geometries. The default is True.

        Returns
        -------
        Iterations
            An instance of the Characterization class with the parameters fromt the configuration sheet.

        """

        detector, ordernumber, simtype, errlimit, defaulthist, maxhist, queue, coorname, electrontrack, debug, fulldetector, customer = Experiment.extract_from_config_sheet(config_sheet)

        # Read the characterization specific values from the
        # Characterization sheet

        errlimit = float(char_sheet.range((1, 15)).value)
        defaulthist = int(char_sheet.range((2, 15)).value)
        maxhist = int(char_sheet.range((3, 15)).value)
        queue = char_sheet.range((4, 15)).value
        max_lost_particles = int(char_sheet.range((5, 15)).value)

        return cls(detector, ordernumber, folder_name, simtype=simtype, errlimit=errlimit, defaulthist=defaulthist, maxhist=maxhist,
                 queue=queue, coorname=coorname, electrontrack=electrontrack, debug=debug,
                 full_detector=fulldetector, customer=customer, low_energy_validation=low_energy_validation,
                 max_lost_particles=max_lost_particles)

    def run(self, char_sheet, iter_sheet, standard_sheet):
        """
        Run the MCNP loop for the characterization
        The function detects if the run has already been started and if so
        the loop will continue from where the previous run left off.

        If a restart is desired then the xxxxx_char.out file should be deleted.

        Parameters
        ----------
        char_sheet : Sheet
            The characterization sheet.
        iter_sheet : Sheet
            The iterations sheet.
        standard_sheet : Sheet
            The standard config sheet.

        Returns
        -------
        None.

        """

        start_time = datetime.datetime.now()

        if not self.detector.validate_model(standard_sheet):
            return

        if utilities.mcnp_running(iter_sheet) == 1:
            ctypes.windll.user32.MessageBoxW(0, f'MCNP is already running for this detector', 'MCNP running', 0)
            return

        if char_sheet.range((14,6)).value == 'complete':
            ctypes.windll.user32.MessageBoxW(0, f'MCNP loop has already been completed for this detector', 'MCNP loop completed', 0)
            return

        # Create the dcg input file and use MakeDCGTools executable to generate the
        # file with the points for the MCNP simulations
        dcg_filename = self.detector.create_point_dcgfile(self.folder_name)
        subprocess.call(['P:\ISOCSProduction\Codes\MakeDCGTools\MakeDCGTools_v1_2.exe', dcg_filename])

        name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_Ref_Pnt_Coo.TXT')
        backup_name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_Ref_Pnt_Coo_backup.TXT')
        # The file created from MakeDCGTools has the wrong format
        # so it needs to be reformatted.
        self.reformat_pnt_file(name, backup_name)
        # Add any detector specific points to the points file.
        self.detector.add_characterization_points(name)

        queued = []
        completed = {}
        previous = {}

        # Check if .outfile exist and read the results from previous run
        outfile_name = os.path.join(self.folder_name, f'{self.detector.serialnumber}_char.out')
        logfile_name = os.path.join(self.folder_name, f'{self.detector.serialnumber}.log')
        if os.path.isfile(outfile_name):
            ret_value = ctypes.windll.user32.MessageBoxW(0, f'A previous MCNP loop has been started.\nDo you want to try to continue previus loop?', 'Previous run detected', 4)
            if ret_value == 6:
                with open(outfile_name, 'r') as outfile:
                    for line in outfile:
                        result = Result.from_string(line)
                        key = result.get_coordinates()
                        previous[key] = result
            else:
                os.remove(outfile_name)
                if os.path.isfile(logfile_name):
                    os.remove(logfile_name)

        # Create sources and populate the queued list if the point/energy was not completed
        # in a previos run
        counter = 0
        with open(name, 'r') as dcg_file:
            for line in dcg_file:
                # remove multiple whitespaces
                line = ' '.join(line.split())
                r = float(line.split()[0])
                theta = float(line.split()[1])
                x = r * np.sin(np.deg2rad(theta))
                y = 0.0
                z = -r * np.cos(np.deg2rad(theta))
                for energy in self.parfile_energies:
                    key = (r, theta, 0.0, energy)
                    if key in previous:
                        completed[counter] = previous.pop(key)
                    else:
                        queued.append(PointSource(energy, counter,
                                                  self.defaulthist, x, y, z))
                    counter += 1

        # If not all previous simulations has been accounted for there was
        # a mismatch between the two points file and the loop needs to be aborted.
        if len(previous) != 0:
            ctypes.windll.user32.MessageBoxW(0, f'Missmatch between previous and current points file', 'Points missmatch', 0)
            return

        print(len(queued))

        # Set the queue folders
        if self.queue.lower() == 'alpha':
            inque_folder = r'P:\ISOCSProduction\Manager\InQueue'
            outque_folder = r'P:\ISOCSProduction\Manager\OutQueue'
        elif self.queue.lower() == 'bravo':
            inque_folder = r'P:\ISOCSProduction\ManagerB\InQueue'
            outque_folder = r'P:\ISOCSProduction\ManagerB\OutQueue'
        else:
            ctypes.windll.user32.MessageBoxW(0, f'Unknown queue: {self.queue}', 'Unknown queue', 0)
            return

        if len(queued) > 0:
            with open(outfile_name, 'a') as outfile, open(logfile_name, 'a', buffering=1) as logfile:

                if self.debug:
                    if not os.path.isdir(os.path.join(self.folder_name, 'debug')):
                        os.mkdir(os.path.join(self.folder_name, 'debug'))

                # Set the flag that the loop is running
                utilities.set_mcnp_running(iter_sheet, 1)

                logfile.write(f'{datetime.datetime.now()}Starting loop with {len(queued)} files\n')

                # Start the Tk window that takes care of submitting and
                # recieving the mcnp simulations
                app = Window(self, queued, completed,
                             inque_folder, outque_folder, outfile, logfile)

                app.after(100, app.process_mcnp)
                app.mainloop()
                app.destroy()

                # Clear the flag that the loop is running
                utilities.set_mcnp_running(iter_sheet, 0)

                if app.aborted:
                    utilities.set_mcnp_running(iter_sheet, 0)
                    return

                end_time = datetime.datetime.now()
                runtime = int((end_time - start_time).total_seconds())
                print(runtime)
                logfile.write(f'\nTotal Running time was {runtime} seconds\n')

                if app.lost_particles:
                    ctypes.windll.user32.MessageBoxW(0, 'Some runs was stopped because of lost particles. Proceed with caution or restart with higher max lost particles', 'Lost particles', 0)

        shutil.copy(outfile_name, os.path.join(self.folder_name, f'{self.detector.serialnumber}_char_backup.out'))
        with open(os.path.join(self.folder_name, f'{self.detector.serialnumber}.out'), 'w') as outfile:
            for res in sorted(completed.values()):
                res.type=''
                outfile.write(f'{str(res)}\n')

        # Set the values expected by the Check Loop Status button so that it can
        # figure out that the loop was completed
        #with open(os.path.join(self.folder_name, f'{self.detector.serialnumber}.log'), 'w') as logfile:
        #    logfile.write(f'\nTotal Running time was {runtime} seconds\n')
        with open(os.path.join(self.folder_name, f'{self.detector.serialnumber}.end'), 'w') as endfile:
            endfile.write('\n')

    def reformat_pnt_file(self, file_name, backup_name):
        """
        Reformat the points file generated by the MakeDCGTools executable

        Parameters
        ----------
        file_name : string
            name of the points file, it will be overwritten.
        backup_name : string
            name of the backup file. It will contain the original file.

        Returns
        -------
        None.

        """
        shutil.copy(file_name, backup_name)
        with open(file_name, 'w') as new_file, open(backup_name, 'r') as old_file:
            for line in old_file:
                parts = ' '.join(line.split()).split()
                new_file.write(f'{parts[1]:<13} {parts[0]:>10}\n')


class Window(tk.Tk):
    def __init__(self, experiment, queued, completed, inque_folder, outque_folder, outfile, logfile, lost_file=None):
        """
        Tk window that handles submitting and recieving files with the MCNP manager.

        Parameters
        ----------
        experiment : Experiment
            The experiment that contains the loop parameters.
        queued : List
            List of sources that will be run.
        completed : Dictionary
            Dictionary containing the sources that has already been completed.
        inque_folder : string
            path to the inqueue folder.
        outque_folder : string
            path to the outqueue folder.
        outfile : file
            the file that the results from the MCNP simulations is written to.

        Returns
        -------
        None.

        """
        tk.Tk.__init__(self, None)
        self.experiment = experiment
        self.queued = queued
        self.submitted = {}
        self.completed = completed
        self.inque_folder = inque_folder
        self.outque_folder = outque_folder
        self.outfile = outfile
        self.extension = 'i3'
        if self.experiment.priority == 1:
            self.extension = 'i1'
        elif self.experiment.priority == 2:
            self.extension = 'i2'
        self.finished = False

        # The window layout.
        self.info_frame = tk.LabelFrame(self, text='Information')
        self.info_frame.grid(row=0, column=0)
        self.sn_label = tk.Label(self.info_frame, text=f'Serial Number {self.experiment.detector.serialnumber}')
        self.sn_label.grid(row=0, column=0)
        self.time_label = tk.Label(self.info_frame, text=f'Started at {datetime.datetime.now():%Y-%m-%d %H:%M:%S}')
        self.time_label.grid(row=1, column=0)
        self.progress_frame = tk.LabelFrame(self, text='Progress')
        self.progress_frame.grid(row=1, column=0)
        self.queued_label = tk.Label(self.progress_frame, text=f'Queued: {len(self.queued)}')
        self.submitted_label = tk.Label(self.progress_frame, text=f'Submitted: {len(self.submitted)}')
        self.completed_label = tk.Label(self.progress_frame, text=f'Finished: {len(self.completed)}')
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal",
                                            length=200, mode="determinate")
        self.queued_label.grid(row=0, column=0)
        self.submitted_label.grid(row=1, column=0)
        self.completed_label.grid(row=2, column=0)
        self.progress_bar.grid(row=3, column=0)
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = len(queued) + len(completed)
        self.button = tk.Button(self, text='Abort', command=self.abort)
        self.button.grid(row=2, column=0)
        self.aborted = False
        self.lost_particles = False
        self.logfile = logfile

    def process_mcnp(self):
        """
        Submit new files if the manager is requesting more and process
        the files that the manager has completed.

        Returns
        -------
        None.

        """
        #self.logfile.write(f'{datetime.datetime.now()} Entering process mcnp\n')
        files_submitted = 0
        if len(self.queued) > 0 and os.path.isfile(os.path.join(self.outque_folder, 'MoreFilesPlease.txt')):
            #self.logfile.write(f'{datetime.datetime.now()} More files requested\n')
            while files_submitted < self.experiment.max_submitted:
                if len(self.queued) == 0:
                    break
                source = self.queued.pop(0)
                #self.logfile.write(f'{datetime.datetime.now()} Trying to create {source.counter} with nps {source.nps}\n')
                base_file_name = f'{self.experiment.detector.serialnumber}_{source.counter}.{self.extension}'
                file_name = os.path.join(self.experiment.folder_name, base_file_name)
                self.experiment.detector.create_input_file(source, file_name, self.experiment.full_detector)
                dest_name = os.path.join(self.inque_folder, base_file_name)
                #self.logfile.write(f'{datetime.datetime.now()} Created {source.counter} with nps {source.nps}\n')
                try:
                    if self.experiment.debug:
                        shutil.copy(file_name, os.path.join(self.experiment.folder_name, 'debug', base_file_name))
                    shutil.move(file_name, dest_name)
                    self.submitted[source.counter] = source
                    files_submitted += 1
                    self.logfile.write(f'{datetime.datetime.now()} Submitted {source.counter} with nps {source.nps}\n')

                except:
                    self.logfile.write(f'{datetime.datetime.now()} Error encountered when moving file {base_file_name}\n')
                    os.remove(file_name)
                    self.queued.insert(0, (source))

        #self.logfile.write(f'{datetime.datetime.now()} {files_submitted} files submitted\n')
        filelist = glob.glob(os.path.join(self.outque_folder, f'{self.experiment.detector.serialnumber}_*.o'))
        #self.logfile.write(f'{datetime.datetime.now()} Processing {len(filelist)} files\n')
        for file in filelist:
            try:
                shutil.move(file, os.path.join(self.experiment.folder_name, os.path.basename(file)))
            except PermissionError:
                self.logfile.write(f'{datetime.datetime.now()} Permission Error {file}\n')
                continue
            with open(os.path.join(self.experiment.folder_name, os.path.basename(file))) as iostream:
                try:
                    counter = int(os.path.basename(file).split('_')[-1].split('.')[0])
                    source = self.submitted.pop(counter)
                    tally = mcnp.f8tally(iostream, 8)
                    if len(tally.efficiencies) > 0:
                        if (tally.uncertainties[5] < self.experiment.errlimit and tally.efficiencies[5] > 0.0) or source.nps == self.experiment.maxhist:
                            self._write_tally_result_to_file(tally, source, counter)
                            # r = source.r
                            # phi = source.phi
                            # theta = 180 - np.rad2deg(source.theta)
                            # eff = tally.efficiencies[5] if tally.efficiencies[5] > 0.0 else source.weight(self.experiment.detector) / source.nps
                            # unc = tally.uncertainties[5] if tally.uncertainties[5] > 0.0 else 10.0
                            # total_eff = tally.total_efficiency() if tally.total_efficiency() > 0.0 else source.weight(self.experiment.detector) / source.nps
                            # total_eff_unc = tally.total_efficiency_uncertainty() if tally.total_efficiency_uncertainty() > 0.0 else 10.0
                            # peak_to_total = eff/total_eff if total_eff > 0.0 else 0.0
                            # seconds = tally.run_time
                            # res = Result(r, theta, phi, source.energy, eff,
                            #              unc, total_eff, total_eff_unc,
                            #              peak_to_total, source.nps, seconds,
                            #              source.type, source)
                            # self.completed[counter] = res
                            # self.outfile.write(str(res) + '\n')
                            self.logfile.write(f'{datetime.datetime.now()} Finished {counter}\n')
                        else:
                            if tally.uncertainties[5] == 0.0:
                                new_nps = self.experiment.maxhist
                            else:
                                new_nps = int((tally.uncertainties[5] / self.experiment.errlimit) **2 * source.nps * 1.1)
                                if new_nps > self.experiment.maxhist:
                                    new_nps = self.experiment.maxhist
                            source.nps = new_nps
                            # insert at the front of the queue
                            self.queued.insert(0, (source))
                            self.logfile.write(f'{datetime.datetime.now()} Requeued {counter} with nps {source.nps}\n')
                    else:
                        self.logfile.write(f'{datetime.datetime.now()} Empty tally, requeued {counter}\n')
                        self.queued.insert(0, (source))
                    iostream.close()
                    if self.experiment.debug:
                        shutil.move(os.path.join(self.experiment.folder_name, os.path.basename(file)), os.path.join(self.experiment.folder_name, 'debug', os.path.basename(file)))
                    else:
                        os.remove(os.path.join(self.experiment.folder_name, os.path.basename(file)))
                except ValueError:
                    if source.max_lost_particles < self.experiment.max_lost_particles:
                        source.max_lost_particles = self.experiment.max_lost_particles
                        self.logfile.write(f'{datetime.datetime.now()} Resubmitted {source.counter} with nps {source.nps} and lost {source.max_lost_particles}\n')
                        self.queued.insert(0, (source))
                        iostream.close()
                    else:
                        self.lost_particles = True
                        # counter = int(os.path.basename(file).split('_')[-1].split('.')[0])
                        # source = self.submitted.pop(counter)
                        tally = mcnp.f8tally(iostream, 8, ignore_lost_particles=True)
                        self._write_tally_result_to_file(tally, source, counter)
                        self.logfile.write(f'{datetime.datetime.now()} Simulation {counter} finished because of lost particles but was still written to out file.\n')
                        iostream.close()
                        shutil.copy(os.path.join(self.experiment.folder_name, os.path.basename(file)), os.path.join(self.experiment.folder_name, f'lost_particles_{source.counter}.o'))
                    if self.experiment.debug:
                        shutil.move(os.path.join(self.experiment.folder_name, os.path.basename(file)), os.path.join(self.experiment.folder_name, 'debug', os.path.basename(file)))
                    else:
                        os.remove(os.path.join(self.experiment.folder_name, os.path.basename(file)))

        if len(self.queued) == 0 and len(self.submitted) == 0:
            self.finished = True
            self.quit()

        self.logfile.write(f'{datetime.datetime.now()} queued={len(self.queued)}, submitted={len(self.submitted)}, finished={len(self.completed)}\n')
        self.queued_label['text'] = f'Queued: {len(self.queued)}'
        self.submitted_label['text'] = f'Submitted: {len(self.submitted)}'
        self.completed_label['text'] = f'Finished: {len(self.completed)}'
        self.progress_bar['value'] = len(self.completed)

        self.outfile.flush()
        self.logfile.flush()

        #self.logfile.write('Process MCNP finished\n')
        self.after(1000, self.process_mcnp)

    def abort(self, message='Aborted by user'):
        """
        Handle abort request from the user

        Parameters
        ----------
        message : string, optional
            The discription that will go on the pop up. The default is 'Aborted by user'.

        Returns
        -------
        None.

        """
        # Tell the manager to abort
        with open(os.path.join(self.inque_folder, f'abort_{self.experiment.detector.serialnumber}.txt'), 'w') as file:
            file.close()
        self.aborted = True
        ctypes.windll.user32.MessageBoxW(0, message, 'Abort', 0)
        self.quit()

    def _write_tally_result_to_file(self, tally, source, counter):
        """
        Write the results of the f8 tally to the out file.

        Parameters
        ----------
        tally : F8tally
            The f8 tally that contains the results.
        source : Source
            The Source containing the description of the source used in the calculation.
        counter : Integer
            The counter for the MCNP simulation.

        Returns
        -------
        None.

        """
        r = source.r
        phi = source.phi
        theta = 180 - np.rad2deg(source.theta)
        eff = tally.efficiencies[5] if tally.efficiencies[5] > 0.0 else source.weight(self.experiment.detector) / source.nps
        unc = tally.uncertainties[5] if tally.uncertainties[5] > 0.0 else 10.0
        total_eff = tally.total_efficiency() if tally.total_efficiency() > 0.0 else source.weight(self.experiment.detector) / source.nps
        total_eff_unc = tally.total_efficiency_uncertainty() if tally.total_efficiency_uncertainty() > 0.0 else 10.0
        peak_to_total = eff/total_eff if total_eff > 0.0 else 0.0
        seconds = tally.run_time
        res = Result(r, theta, phi, source.energy, eff,
                     unc, total_eff, total_eff_unc,
                     peak_to_total, source.nps, seconds,
                     source.type, source)
        self.completed[counter] = res
        self.outfile.write(str(res) + '\n')

class Result:
    def __init__(self, r, theta, phi, energy, eff, unc, total_eff, total_eff_unc, peak_to_total, nps, seconds, type, source=None):
        """
        Class to handle the results from the MCNP simulations

        Parameters
        ----------
        r : float
            The r coordinate of the source.
        theta : float
            The theta coordinate of the source.
        phi : float
            The phi coordinate of the source.
        energy : float
            The emission energy of the source.
        eff : float
            the efficiency calculated by MCNP.
        unc : float
            the relative uncertainty reported by MCNP.
        total_eff : float
            the total efficiency calculated by MCNP.
        total_eff_unc : float
            the relative uncertainty of the total efficiency reported by MCNP.
        peak_to_total : float
            The peak to total ratio.
        nps : integer
            number of source particles used in the simulation.
        seconds : float
            MCNP runtime in seconds.
        type : string
            The geometry of the source.
        source : Source, optional
            The Source that was used to run the simulation. The default is None.

        Returns
        -------
        None.

        """
        self.r = r
        self.theta = theta
        self.phi = phi
        self.energy = energy
        self.eff = eff
        self.unc = unc
        self.total_eff = total_eff
        self.total_eff_unc = total_eff_unc
        self.peak_to_total = peak_to_total
        self.nps = nps
        self.seconds = seconds
        self.type = type
        self.source = source

    def get_coordinates(self):
        """
        returns a set of the polar coordinates for the source and the energy

        Returns
        -------
        float
            The r coordinate.
        float
            The theta coordinate.
        float
            The phi coordinate.
        float
            The energy.

        """
        return (self.r, self.theta, self.phi, self.energy)

    def __str__(self):
        """
        The to string function formatted to be compatible with the format of the
        .out file.

        Returns
        -------
        line : string
            The sting that is formatted according to the .out file.

        """
        line = f'{self.r:<12.6f} {self.theta:<8.4f} {self.phi:<8.4f} {self.energy:<9.3f} {self.eff:.6e} {self.unc:.2e} {self.total_eff:.6e} {self.total_eff_unc:.2e} {self.peak_to_total:.6f}  {int(self.nps):<10d} {self.seconds:<10d} {self.type}'
        return line

    def __lt__(self, other):
        """
        Implementetion of the less than operator

        Parameters
        ----------
        other : Result
            An instance of a Result class.

        Returns
        -------
        bool
            Returns True if less than other.

        """
        if self.r < other.r:
            return True
        if self.r == other.r:
            if self.theta < other.theta:
                return True
            if self.theta == other.theta:
                if self.phi < other.phi:
                    return True
                if self.phi == other.phi:
                    return self.energy < other.energy
        return False

    def exist(self, r, theta, phi, energy):
        """


        Parameters
        ----------
        r : float
            The r coordinate.
        theta : float
            The theta coordinate.
        phi : float
            The phi coordinate.
        energy : float
            The energy.

        Returns
        -------
        bool
            True if the coordinates and the energy are equal, False otherwise.

        """
        return self.r == r and self.theta == theta and self.phi == phi and self.energy == energy

    @classmethod
    def from_string(cls, string):
        """
        Method to parse a string from a .out file.

        Parameters
        ----------
        string : string
            String from a .out file.

        Returns
        -------
        Result
            An instance of the Result class coresponding to the information from the .out file.

        """
        split_string = ' '.join(string.split()).split()
        r = float(split_string[0])
        theta = float(split_string[1])
        phi = float(split_string[2])
        energy = float(split_string[3])
        eff = float(split_string[4])
        eff_unc = float(split_string[5])
        total_eff = float(split_string[6])
        total_eff_unc = float(split_string[7])
        peak2total = float(split_string[8])
        nps = int(split_string[9])
        seconds = int(split_string[10])
        if len(split_string) == 12:
            type = split_string[11]
        else:
            type = ''
        return cls(r, theta, phi, energy, eff, eff_unc, total_eff, total_eff_unc, peak2total, nps, seconds, type)


