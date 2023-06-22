"""

Created on Wed Oct  2 14:21:49 2019

@author: HPersson

"""
import xlwings as xw
import isocs_utility_functions as utilities
#from detector import AegisBEGe
from experiment import Iteration
import os

def main():
    """
    This function is desinged to be called from the excel spreadsheet.
    Creates a standard configuration of the detector model and parameters entered
    on the initialization tab.

    Returns
    -------
    None.

    """
    wb = xw.Book.caller()
    config_sheet = utilities.sheet_from_name(wb, 'Current CFG')
    init_sheet = utilities.sheet_from_name(wb, 'Initialization')
    standard_sheet = utilities.sheet_from_name(wb, 'StandardCFGs')
    experiment = Iteration.default_parameters(utilities.serial_number(wb), utilities.model_number(wb), init_sheet, standard_sheet, os.path.dirname(wb.fullname), utilities.order_number(wb))
    experiment.write_config_page(config_sheet)


if __name__ == '__main__':
    # Expects the Excel file next to this source file, adjust accordingly.
    xw.Book('SN1730_v5_6_20_b.xlsm').set_mock_caller()
    main()