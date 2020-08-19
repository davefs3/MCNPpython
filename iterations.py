# -*- coding: utf-8 -*-
"""
Created on Wed Oct  2 13:44:37 2019

@author: HPersson
"""
import xlwings as xw
import os
import numpy as np
from experiment import Iteration
import isocs_utility_functions as utilities

def main():
    """
    This function is desinged to be called from the excel spreadsheet.
    Run an iteration and compare the calculated and measured efficiency.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')
    iteration_sheet = utilities.sheet_from_name(wb, 'Iterations')
    standard_sheet = utilities.sheet_from_name(wb, 'StandardCFGs')
    low_energy_validation = utilities.low_energy_validation(wb)
    experiment = Iteration.from_config_sheet(config_sheet, os.path.dirname(wb.fullname), low_energy_validation)
    experiment.run(iteration_sheet, standard_sheet)


def clear_initialize():
    """
    This function is desinged to be called from the excel spreadsheet.
    Clear and initilizes the iterations sheet

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    sheet = utilities.sheet_from_name(wb, 'Iterations')
    meas_sheet = utilities.sheet_from_name(wb, 'Measurements')
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')

    clear_init(wb, sheet, config_sheet, meas_sheet)


class MeasurementEnergy:
    def __init__(self, energy, efficiency, independent_uncertainty, correlated_uncertainty):
        self.enerrgy = energy
        self.efficiencies = []
        self.uncertainties = []
        self.add_measurement(efficiency, independent_uncertainty)
        self.correlated_uncertainty = correlated_uncertainty / 100.0

    def efficiency(self):
        efficiencies = np.array(self.efficiencies)
        uncertainties = np.array(self.uncertainties) * efficiencies /100.0
        # remove measurements with 0 efficiencies and uncertainty
        efficiencies = efficiencies[efficiencies != 0.0]
        uncertainties = uncertainties[uncertainties != 0.0]
        if np.sum(efficiencies) == 0.0:
            return '', ''

        weighted_average = np.sum(efficiencies/uncertainties**2) / np.sum(1.0 / uncertainties**2)
        uncertainty = np.sqrt(1.0 / np.sum(1.0 / uncertainties**2)) / weighted_average
        stdev = np.std(efficiencies) / weighted_average
        uncertainty = np.sqrt(uncertainty**2 + self.correlated_uncertainty**2 + stdev**2) * 100.0

        return weighted_average, uncertainty

    def add_measurement(self, efficiency, independent_uncertainty):
        self.efficiencies.append(efficiency)
        self.uncertainties.append(independent_uncertainty)


class Measurement:
    def __init__(self, geometry):
        self.geometry = geometry
        self.energies = {}
        self.minimum_energy = {'0D':13.8,
                               '45D':13.8,
                               '90D':38,
                               '135D':38,
                               'DC':13.8,
                               'DF':13.8,
                               'WE':13.8,
                               'RELEFF':1332}


    def add_energy(self, energy, efficiency, independent_uncertainty, correlated_uncertainty):
        if energy in self.energies:
            self.energies[energy].add_measurement(efficiency, independent_uncertainty)
        else:
            self.energies[energy] = MeasurementEnergy(energy, efficiency, independent_uncertainty, correlated_uncertainty)

    def table(self):
        table = []
        low_energy_indicies = []
        for index, temp in enumerate(self.energies.items()):
            energy, measurement_energy = temp
            if energy > self.minimum_energy.get(self.geometry, 13.8):
                if energy < utilities.low_energy_cutoff.get(self.geometry, 13.8):
                    low_energy_indicies.append(index)
                eff, unc = measurement_energy.efficiency()
                table.append([self.geometry, energy, eff, unc])
        return table, low_energy_indicies


def clear_init(wb, sheet, config_sheet, meas_sheet):

    low_energy_validation = utilities.low_energy_validation(wb)
    experiment = Iteration.from_config_sheet(config_sheet, os.path.dirname(wb.fullname), low_energy_validation)

    # over ride the values for doing the characterization
#    if sheet.name == 'Characterize':
#        experiment.defaulthist = 100000
#        experiment.maxhist = 100000000
#        experiment.queue = 'bravo'

    sheet.range((9, 16)).value = 0
    sheet.range((10, 16)).value = 0
    sheet.range('O11:Q11').clear()
    sheet.range('A14:IV5000').clear()
    sheet.range('A14:IV5000').api.Font.Size = 8
    sheet.range('A1:C15').api.Interior.ColorIndex = 15
    sheet.range('A16').value = 'SPECTRUM'
    sheet.range('B16').value = 'ENERGY'
    sheet.range('C16').value = 'EFFICIENCY'
    sheet.range('D16').value = '% SIGMA'

    sheet.range((16, 1), (16, 100)).api.Borders(9).LineStyle = 1
    sheet.range((16, 1), (16, 100)).api.Borders(9).Weight = 2

    start_row = 5
    start_column = 7
    end_column = start_column + 27
    end_row = meas_sheet.range('G' + str(sheet.cells.last_cell.row)).end('up').row

    meas_range = meas_sheet.range((start_row, start_column), (end_row, end_column))

    table = []
    first_row = 17
    line_end = 100

    measurements = {}

    measurement_order = ['0D', '45D', '90D', '135D', 'DC', 'DF', 'WE', 'FP_1', 'RELEFF']

    for row in meas_range.rows:
        # Extract the geometry and remove trailing digits
        geometry = row[0].value.split('_')[-1].rstrip('1234567890')
        energy = row[1].value
        efficiency = row[2].value if row[2].value is not None else 0.0
        peak_unc = row[12].value if row[12].value is not None else 0.0
        source_unc = row[9].value if row[9].value is not None else 0.0
        other_unc = row[27].value if row[27].value is not None else 0.0
        independent_uncertainty = np.sqrt(peak_unc**2 + other_unc**2)
        correlated_uncertainty = source_unc

            # convert to relative efficiency
        if geometry == 'DR':
            geometry = 'RELEFF'
            nrg = energy
            if 1332.4 < nrg < 1332.6:
                efficiency = efficiency / 0.0012
            else:
                continue

        if geometry in measurements:
            measurements[geometry].add_energy(energy, efficiency, independent_uncertainty, correlated_uncertainty)
        else:
            measurements[geometry] = Measurement(geometry)
            measurements[geometry].add_energy(energy, efficiency, independent_uncertainty, correlated_uncertainty)

    table = []
    for geometry in measurement_order:
        if geometry in measurements:
            geometry_table, low_energy_indicies = measurements[geometry].table()
            if not low_energy_validation:
                for index in low_energy_indicies:
                    sheet.range((first_row + len(table) + index, 1), (first_row + len(table) + index, 4)).api.Interior.ColorIndex = 20

            table += geometry_table
            sheet.range((first_row + len(table), 1), (first_row + len(table), line_end)).api.Borders(8).LineStyle = 1
            sheet.range((first_row + len(table), 1), (first_row + len(table), line_end)).api.Borders(8).Weight = 2

    sheet.range((first_row + len(table), 1), (first_row + len(table), line_end)).api.Borders(8).LineStyle = 1
    sheet.range((first_row + len(table), 1), (first_row + len(table), line_end)).api.Borders(8).Weight = 2

    table.append(['PARAMETER', 'INITIAL', '', ''])
    table.append(['~serialnumber', experiment.detector.serialnumber,'',''])
    table.append(['~modelnumber', experiment.detector.modelnumber,'',''])
    table.append(['~ordernumber', experiment.ordernumber,'',''])
    table.append(['~customer', experiment.customer,'',''])
    table.append(['~coorname', 'expt','',''])
    table.append(['~simtype', experiment.simtype,'',''])
    table.append(['~errlimit', experiment.errlimit,'',''])
    table.append(['~defaulthist', experiment.defaulthist,'',''])
    table.append(['~maxhist', experiment.maxhist,'',''])
    table.append(['~queue', experiment.queue,'',''])
    table.append(['~electrontrack', experiment.electrontrack,'',''])
    table.append(['#Start', '','', ''])

    for key, value in experiment.detector.dimensions.items():
        table.append([key, str(value),'',''])

    table.append(['#End', '','',''])

    sheet.range('A17').value = table


if __name__ == '__main__':
    # Expects the Excel file next to this source file, adjust accordingly.
    xw.Book('SN11369_v5_6.xlsm').set_mock_caller()
    #clear_initialize()
    main()



