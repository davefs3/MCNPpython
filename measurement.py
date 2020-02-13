# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 15:11:58 2020

@author: HPersson
"""
import xlwings as xw
import isocs_utility_functions as isocs
import os
from collections import OrderedDict
from com.canberra.datasources.spectroscopy.cam import Datasource, ParameterCodes
import numpy as np

class Line:
    def __init__(self, energy, efficiency, sigma, peak_area, ctf_gps,
                 decay_factor, lt_ratio, real_time, source_error, meas_date,
                 peak_cps, cps_error, fit_energy, energy_error, fwhm,
                 fwhm_error, fit_channel, channel_error, peak_error, rise_time,
                 flat_top, fd_mode, fd_setting, purg_setting, lt_trim, ltc_on,
                 sys_error):
        """
        Initializes the Line class which stores the data associated with a line
        in the spectrum used for the characterization

        Parameters
        ----------
        energy : float
            The energy of the line.
        efficiency : float
            The efficiency of the line.
        sigma : float
            The one sigma uncertainty of the line.
        peak_area : float
            The measured peak area.
        ctf_gps : float
            The emission rate (gammas emitted per second) from the source.
        decay_factor : float
            The decay correction factor.
        lt_ratio : float
            The live time to real time ratio.
        real_time : float
            The measurement real time.
        source_error : float
            The uncertainty of the source emission rate.
        meas_date : datetime
            The measurement date.
        peak_cps : float
            peak area divided by the live time.
        cps_error : float
            uncertainty in peak_cps.
        fit_energy : float
            The measured peak centroid in (keV).
        energy_error : float
            The uncertainty in the measured peak centroid.
        fwhm : float
            the measured peak FWHM.
        fwhm_error : float
            The uncertainty in the FWHM.
        fit_channel : float
            The measured peak centroid in channels.
        channel_error : float
            The uncertainty in the fit channel.
        peak_error : float
            The uncertainty in the peak area.
        rise_time : float
            The rise time used for the measurement.
        flat_top : float
            The flat top used for the measurement.
        fd_mode : string
            The fast discriminator mode.
        fd_setting : float
            The fast discriminator setting.
        purg_setting : float
            The pile up rejction guard setting.
        lt_trim : float
            The live time trim setting.
        ltc_on : float
            Live time correction on/off (1/0).
        sys_error : float
            Systematic uncertainty of the measurement.

        Returns
        -------
        None.

        """
        self.energy = energy
        self.efficiency = efficiency
        self.sigma = sigma
        self.peak_area = peak_area
        self.ctf_gps = ctf_gps
        self.decay_factor = decay_factor
        self.lt_ratio = lt_ratio
        self.real_time = real_time
        self.source_error = source_error
        self.meas_date = meas_date
        self.peak_cps = peak_cps
        self.cps_error = cps_error
        self.fit_energy = fit_energy
        self.energy_error = energy_error
        self.fwhm = fwhm
        self.fwhm_error = fwhm_error
        self.fit_channel = fit_channel
        self.channel_error = channel_error
        self.peak_error = peak_error
        self.rise_time = rise_time
        self.flat_top = flat_top
        self.fd_mode = fd_mode
        self.fd_setting = fd_setting
        self.purg_setting = purg_setting
        self.lt_trim = lt_trim
        self.ltc_on = ltc_on
        self.sys_error = sys_error

    def __lt__(self, other):
        """
        Determines if the current line is less than another Line.

        Parameters
        ----------
        other : Line
            The line that the current line is to be compared with.

        Returns
        -------
        Bool
            True if current line is less then other line.

        """
        return self.energy < other.energy

    def table_entry(self, spectrum):
        """
        Formats the list that is used to populate the table that will go into
        the spreadsheet.

        Parameters
        ----------
        spectrum : String
            Label that will go into the fist column of the table in the spreadsheet.

        Returns
        -------
        list
            formatted strings that will be displayed in the spreadsheet.

        """
        return [spectrum, f'{self.energy:<.2f}', str(self.efficiency), str(self.sigma/self.efficiency * 100),
                str(self.peak_area), str(self.ctf_gps), str(self.decay_factor), str(self.lt_ratio),
                str(self.real_time), str(self.source_error), self.meas_date.isoformat(),
                str(self.peak_cps), str(self.cps_error), str(self.fit_energy),
                str(self.energy_error), str(self.fwhm), str(self.fwhm_error),
                str(self.fit_channel), str(self.channel_error), str(self.peak_error),
                str(self.rise_time), str(self.flat_top), str(self.fd_mode), str(self.fd_setting),
                str(self.purg_setting), str(self.lt_trim), str(self.ltc_on), str(self.sys_error)]
        
        
class Geometry:
    def __init__(self, label):
        """
        Class to handle a measurement geometry from used in the characterization
        process

        Parameters
        ----------
        label : String
            The ISOCS label of the geometry.

        Returns
        -------
        None.

        """
        self.label = label
        self.lines = []
    
    def add_line(self, line):
        """
        Add a line to the measurement energy

        Parameters
        ----------
        line : Line
            The line that should be added.

        Returns
        -------
        None.

        """
        self.lines.append(line)

    def sorted_lines(self):
        """
        Sortes the lines in the geometry based on the energy p

        Returns
        -------
        List
            A list of lines sorted in energy.

        """
        return sorted(self.lines)


def extract_generic(sheet, serial_number, tolerance=10.0):
    """
    Extracts the measurement data for generic detectors and puts it in the 
    spreadsheet.

    Parameters
    ----------
    sheet : Sheet
        The measurement sheet that contains the input data and that the output 
        data will be populated in.
    serial_number : String
        The serial number of the detector that is getting characterized.
    tolerance : float, optional
        The tolerance between the measured peak energies and the certificate 
        reference energy. The default is 10.0.

    Returns
    -------
    None.

    """
    #start_column = sheet.range((1, 10))
    start_row = 5
    end_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
    file_range = sheet.range((start_row, 1), (end_row, 5))
    geometries = OrderedDict()
    with Datasource() as ds, Datasource() as ctf:
        for row in file_range.rows:
            filename = row[0].value
            ctfname = row[1].value
            meas_type = row[4].value
            if meas_type in geometries:
                geometry = geometries[meas_type]
            else:
                geometry = Geometry(meas_type)
                geometries[meas_type] = geometry
            ds.open(filename)
            peaks = ds.peaks
            
            # measurement parameters
            meas_date = ds.getParameter(ParameterCodes.CAM_X_ASTIME)
            elive = ds.getParameter(ParameterCodes.CAM_X_ELIVE)
            ereal = ds.getParameter(ParameterCodes.CAM_X_EREAL)
            lt_ratio = elive / ereal
            rise_time = ds.getParameter(ParameterCodes.CAM_F_AMPFILTERRT)
            flat_top = ds.getParameter(ParameterCodes.CAM_F_AMPFILTERFT)
            fd_mode = ds.getParameter(ParameterCodes.CAM_T_AMPFDMODE)
            fd_setting = ds.getParameter(ParameterCodes.CAM_F_AMPFD)
            purg_setting = ds.getParameter(ParameterCodes.CAM_F_AMPPURG)
            lt_trim = ds.getParameter(ParameterCodes.CAM_L_AMPLTTRIM)
            ltc_on = ds.getParameter(ParameterCodes.CAM_L_AMPFPUREJ)

            # Get the systematic error from the random systematic sample parameter
            # This should include all contribution to the uncertainty except the
            # source uncertainty, the decay correction uncertainty and the peak statistical uncertainty
            sys_error = ds.getParameter(ParameterCodes.CAM_F_SSYSERR)
            
            # Certificate parameters
            ctf.open(os.path.join(os.path.dirname(filename), ctfname))
            records = ctf.count(ParameterCodes.CAM_F_CTFENER)
            ctf_date = ctf.getParameter(ParameterCodes.CAM_X_CTFDATE)
            ctf_quant = ctf.getParameter(ParameterCodes.CAM_F_CTFQUANT)
            
            decay_time = (meas_date - ctf_date).total_seconds()
            
            # Find matches between peak records and certifcate records
            for record in range(1, records + 1):
                ctf_energy = ctf.getParameter(ParameterCodes.CAM_F_CTFENER, record)
                for peak in peaks:
                    if ctf_energy - tolerance < peak.energy.value < ctf_energy + tolerance:
                        # halflife is stored in seconds
                        halflife = ctf.getParameter(ParameterCodes.CAM_X_CTFHLFLIFE, record)
                        halflife_unc = ctf.getParameter(ParameterCodes.CAM_X_CTFHLFERR, record)
                        ctf_gps = ctf.getParameter(ParameterCodes.CAM_F_CTFRATE, record) * ctf_quant
                        source_error = ctf.getParameter(ParameterCodes.CAM_F_CTFERROR, record)
                        decay_factor = np.exp(-np.log(2.0)*decay_time/halflife)
                        decay_factor_unc = decay_factor*np.log(2.0)*decay_time/halflife**2*halflife_unc
                        
                        peak_area = peak.area.value
                        peak_cps = peak.countrate.value
                        cps_error = peak.countrate.uncertainty
                       
                        
                        efficiency = peak_cps / ctf_gps / decay_factor
                        sigma = efficiency*np.sqrt((cps_error/100.0)**2 +
                                                   (decay_factor_unc/decay_factor)**2 +
                                                   (source_error/100.0)**2 + 
                                                   (sys_error/100.0)**2)
                        
                        fit_energy = peak.energy.value
                        energy_error = peak.energy.uncertainty
                        fwhm = peak.fwhm.value
                        fwhm_error = peak.fwhm.uncertainty
                        fit_channel = peak.centroid.value
                        channel_error = peak.centroid.uncertainty
                        
                        peak_error = peak.area.uncertainty
                        
                        line = Line(ctf_energy, efficiency, sigma, peak_area,
                                    ctf_gps, decay_factor, lt_ratio, ereal,
                                    source_error, meas_date, peak_cps, 
                                    cps_error, fit_energy, energy_error, fwhm,
                                    fwhm_error, fit_channel, channel_error,
                                    peak_error, rise_time, flat_top, fd_mode,
                                    fd_setting, purg_setting, lt_trim, ltc_on,
                                    sys_error)

                        geometry.add_line(line)
            ds.close()
            ctf.close()


        # Put the results into the spread sheet
        table= []
        for label, geometry in geometries.items():
            for line in geometry.sorted_lines():
                table.append(line.table_entry(f'{serial_number}_{label}'))

        sheet.range('G5').value = table


def main():
    """
    This function is desinged to be called from the excel spreadsheet.
    Extracts the measurement data from the cam files for generic detectors.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    serial_number = isocs.serial_number(wb)
    model = isocs.model_number(wb)
    
    measurement_sheet = utilities.sheet_from_name(wb, 'Measurements')
    
    if model == 'Generic':
        extract_generic(measurement_sheet, serial_number)
    else:
        pass
        
             
# This code is used for debugging
if __name__ == '__main__':
    # Expects the Excel file next to this source file, adjust accordingly.
    xw.Book('SN#####_v5_0_0.xlsm').set_mock_caller()
    main()

