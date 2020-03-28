# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 13:20:45 2019

@author: HPersson
"""

import xlwings as xw
import os
import isocs_utility_functions as utilities
from experiment import Characterization
from iterations import clear_init

def loop():
    """
    This function is desinged to be called from the excel spreadsheet.
    Runs the MCNP loop from the information stored in the excel spreadsheet.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')
    iteration_sheet = utilities.sheet_from_name(wb, 'Iterations')
    characterization_sheet = utilities.sheet_from_name(wb, 'Characterize')
    standard_sheet = utilities.sheet_from_name(wb, 'StandardCFGs')
    low_energy_validation = utilities.low_energy_validation(wb)
    experiment = Characterization.from_config_sheet(config_sheet, characterization_sheet, os.path.dirname(wb.fullname), low_energy_validation)
    experiment.run(characterization_sheet, iteration_sheet, standard_sheet)


def make_par():
    """
    This function is desinged to be called from the excel spreadsheet.
    Generates the parfile after the MCNP loop has finished.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')
    characterization_sheet = utilities.sheet_from_name(wb, 'Characterize')
    low_energy_validation = utilities.low_energy_validation(wb)
    experiment = Characterization.from_config_sheet(config_sheet, characterization_sheet, os.path.dirname(wb.fullname), low_energy_validation)
    experiment.detector.make_par(characterization_sheet, experiment.folder_name, experiment.ordernumber, experiment.customer)


def clear_initialize():
    """
    This function is desinged to be called from the excel spreadsheet.
    Clears and initializes the Characterization tab.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    sheet = utilities.sheet_from_name(wb, 'Characterize')
    meas_sheet = utilities.sheet_from_name(wb, 'Measurements')
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')

    clear_init(wb, sheet, config_sheet, meas_sheet)


# This code is used for debugging
if __name__ == '__main__':
    # Expects the Excel file next to this source file, adjust accordingly.
    xw.Book('SNB20231_v5_1.xlsm').set_mock_caller()
    #xw.Book(r'P:\ISOCSProduction\Det_2019\R4_87677\SNR4_v5_0_0.xlsm').set_mock_caller()
    make_par()
    #clear_initialize()
    #loop()
