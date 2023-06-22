import xlwings as xw
import collections
import ctypes

# Module to read parameters from the initialization page

def sheet_from_name(wb, name):
    """
    Get sheet from referencing a name
    Returns None if there is no sheet with name

    Parameters
    ----------
    wb : WorkBook
        The excel workbook.
    name : string
        the name of the sheet.

    Returns
    -------
    Sheet
        The sheet with name, None if the sheet doesn't exist.

    """
    if name in [sh.name for sh in wb.sheets]:
        return wb.sheets[name]
    else:
        return None


def __read_reference(xl, reference, func=str, default='', sheet_name='Initialization'):
    """
    Reads the value from a cell in the workbook or sheet. The function will call
    func on the value that was read from the cell if a particular type is required.
    
    Thus function is intended to be called from reference functions to for 
    example the serial number.

    Parameters
    ----------
    xl : xw.Book or Sheet
        The book or the sheet from where the values will be read from.
    reference : string
        The reference in the sheet, for example C14.
    func : callable, optional
        function that will be applied to the value in the cell. The default is str.
    default : any, optional
        The default value to be returned if an error occurs when func is called. The default is ''.
    sheet_name : string
        The name of the sheet that contains the cell, used if xl is xw.Book, optional. The default is 'Initialization'.

    Returns
    -------
    type returned from func, default str
        The value from the cell.

    """
    if isinstance(xl, xw.Book):
        sheet = sheet_from_name(xl, sheet_name)
        value = sheet.range(reference).value
    else:
        value = xl.range(reference).value   
    try:
        return func(value)
    except:
        return default
    
def __set_reference(xl, reference, value, sheet_name):
    """
    Sets a value to a cell in the workbook or sheet.
    

    Parameters
    ----------
    xl : xw.Book or Sheet
        The book or the sheet from where the values will be set to..
    reference :  string
        The reference in the sheet, for example C14.
    value : string, float, int
        The value that is written to the cell in the workbook or sheet.
    sheet_name : string
        The name of the sheet.

    Returns
    -------
    None.

    """
    if isinstance(xl, xw.Book):
        sheet = sheet_from_name(xl, sheet_name)
        sheet.range(reference).value = value
    else:
        xl.range(reference).value = value   


def well_source_number(xl):
    """
    Read the well source ID number from the workbook or sheet. Always use this function
    when accessing the well source ID number from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the well source ID number.

    Returns
    -------
    string
        The well source ID number.

    """
    reference = 'C36'
    return __read_reference(xl, reference)    


def serial_number(xl):
    """
    Read the serial number from the workbook or sheet. Always use this function
    when accessing the serial number from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the serial number.

    Returns
    -------
    string
        The serial number.

    """
    reference = 'C14'
    return __read_reference(xl, reference)


def model_number(xl):
    """
    Read the model number from the workbook or sheet. Always use this function
    when accessing the model number from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the model number.

    Returns
    -------
    string
        The model number.

    """
    reference = 'C15'
    return __read_reference(xl, reference)

def order_number(xl):
    """
    Read the order number from the workbook or sheet. Always use this function
    when accessing the order number from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the order number.

    Returns
    -------
    string
        The order number.

    """
    reference = 'C13'
    return __read_reference(xl, reference)

def dcgdir(xl):
    """
    Read the dcg directory from the workbook or sheet. Always use this function
    when accessing the dcg directory from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the dcg directory.

    Returns
    -------
    string
        The dcg directory.

    """
    reference = 'C5'
    return __read_reference(xl, reference)

def surferdir(xl):
    """
    Read the surfer directory from the workbook or sheet. Always use this function
    when accessing the surfer directory from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the surfer directory.

    Returns
    -------
    string
        The surfer directory.

    """
    reference = 'C6'
    return __read_reference(xl, reference)

def ec_xtal_dist(xl):
    """
    Read the crystal to end cap distance from the workbook or sheet. Always use this function
    when accessing the crystal to end cap distance from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal to end cap distance.

    Returns
    -------
    float
        The crystal to end cap distance.

    """
    reference = 'C18'
    return __read_reference(xl, reference, float, 0.0)

def xtal_length(xl):
    """
    Read the crystal length from the workbook or sheet. Always use this function
    when accessing the crystal length from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal length.

    Returns
    -------
    float
        The crystal length.

    """
    reference = 'C19'
    return __read_reference(xl, reference, float, 0.0)

def xtal_diameter(xl):
    """
    Read the crystal diameter from the workbook or sheet. Always use this function
    when accessing the crystal diameter from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal diameter.

    Returns
    -------
    float
        The crystal diameter.

    """
    reference = 'C20'
    return __read_reference(xl, reference, float, 0.0)

def well_depth(xl):
    """
    Read the crystal well depth from the workbook or sheet. Always use this function
    when accessing the crystal well depth from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal well depth.

    Returns
    -------
    float
        The crystal well depth.

    """
    reference = 'C21'
    return __read_reference(xl, reference, float, 0.0)

def well_diameter(xl):
    """
    Read the crystal well diameter from the workbook or sheet. Always use this function
    when accessing the crystal well diameter from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal well diameter.

    Returns
    -------
    float
        The crystal well diameter.

    """
    reference = 'C22'
    return __read_reference(xl, reference, float, 0.0)

def front_dl(xl):
    """
    Read the crystal front dead layer from the workbook or sheet. Always use this function
    when accessing the crystal front dead layer from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal front dead layer.

    Returns
    -------
    float
        The crystal front dead layer.

    """
    reference = 'C23'
    return __read_reference(xl, reference, float, 0.0)

def side_dl(xl):
    """
    Read the crystal side dead layer from the workbook or sheet. Always use this function
    when accessing the crystal side dead layer from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal side dead layer.

    Returns
    -------
    float
        The crystal side dead layer.

    """
    reference = 'C24'
    return __read_reference(xl, reference, float, 0.0)

def bevel_radius(xl):
    """
    Read the crystal bevel radius from the workbook or sheet. Always use this function
    when accessing the crystal bevel radius from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal bevel radius.

    Returns
    -------
    float
        The crystal bevel radius.

    """
    reference = 'C25'
    return __read_reference(xl, reference, float, 0.0)

def taper_radius(xl):
    """
    Read the crystal taper radius from the workbook or sheet. Always use this function
    when accessing the crystal taper radius from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal taper radius.

    Returns
    -------
    float
        The crystal taper radius.

    """
    reference = 'C26'
    return __read_reference(xl, reference, float, 0.0)

def taper_bottom(xl):
    """
    Read the crystal taper bottom from the workbook or sheet. Always use this function
    when accessing the crystal taper bottom from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the crystal taper bottom.

    Returns
    -------
    float
        The crystal taper bottom.

    """
    reference = 'C27'
    return __read_reference(xl, reference, float, 0.0)

def holder_model(xl):
    """
    Read the holder model from the workbook or sheet. Always use this function
    when accessing the holder model from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the holder model.

    Returns
    -------
    string
        The holder model.

    """
    reference = 'C29'
    return __read_reference(xl, reference)

def endcap_model(xl):
    """
    Read the endcap model from the workbook or sheet. Always use this function
    when accessing the endcap model from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the endcap model.

    Returns
    -------
    string
        The endcap model.

    """
    reference = 'C30'
    return __read_reference(xl, reference)

def preamp_model(xl):
    """
    Read the preamp model from the workbook or sheet. Always use this function
    when accessing the preamp model from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the preamp model.

    Returns
    -------
    string
        The preamp model.

    """
    reference = 'C31'
    return __read_reference(xl, reference)

def cryostat_model(xl):
    """
    Read the cryostat model from the workbook or sheet. Always use this function
    when accessing the cryostat model from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the cryostat model.

    Returns
    -------
    string
        The cryostat model.

    """
    reference = 'C32'
    return __read_reference(xl, reference)

def measured_endcap_diameter(xl):
    """
    Read the measured end cap diameter from the workbook or sheet. Always use this function
    when accessing the measured end cap diameter from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet that contains the measured end cap diameter.

    Returns
    -------
    string
        The measured end cap diameter.

    """
    reference = 'C33'
    return __read_reference(xl, reference, float, 0.0)

def mcnp_running(xl):
    """
    Read the if mcnp is running for the detector from the workbook or sheet. Always use this function
    when accessing determining if MCNP is running from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet.

    Returns
    -------
    int
        1 if mcnp is running for the detector, 0 otherwise.

    """
    reference = 'P1'
    sheet_name = 'Iterations'
    return __read_reference(xl, reference, int, 0, sheet_name)

def set_mcnp_running(xl, value):
    """
    Set the if mcnp is running for the detector from the workbook or sheet. Always use this function
    when accessing determining if MCNP is running from the ISOCS excel spreadsheet.

    Parameters
    ----------
    xl : xl.Book or Sheet
        The workbook or sheet.
    value : integer
        1 if MCNP is running and 0 otherwise 

    """
    reference = 'P1'
    sheet_name = 'Iterations'
    __set_reference(xl, reference, value, sheet_name)

def find_tag_in_column(tag, sheet, column, start_row=1):
    """
    Find the row in a column that contains the tag

    Parameters
    ----------
    tag : str, float, int
        The value to look for.
    sheet : Sheet
        The excel spreadsheet.
    column : string
        The character that represents the column.
    start_row : integer, optional
        The start row. The default is 1.

    Returns
    -------
    integer
        The row that contains tag, -1 if the tag is not found.

    """
    last_row = sheet.range(column + str(sheet.cells.last_cell.row)).end('up').row
    cells = sheet.range('{}{}:{}{}'.format(column, start_row, column, last_row))
    for cell in cells:
        if cell.value == tag:
            return cell.row
    return -1

def find_standard_detector_values(header, model_number, sheet):
    """
    Find the default dimensions for a detector type on the standard cfg sheet.

    Parameters
    ----------
    header : string
        The header tag used in the standard cfg sheet.
    model_number : string
        The model number of the detector.
    sheet : Sheet
        The standard config sheet.

    Returns
    -------
    standard_values : OrderedDict
        An ordered dictionary where the dimension keyword is the key and the value of
        the dimension is the value.

    """
    standard_values = collections.OrderedDict()
    last_row = sheet.range('A' + str(sheet.cells.last_cell.row)).end('up').row
    cells = sheet.range('A1:A'+ str(last_row))
    header_found = False
    first_row = -1
    last_row = -1
    for cell in cells:
        if cell.value == header:
            first_row = cell.row
            header_found = True
        if header_found and cell.value == '#End':
            last_row = cell.row - 1
            break
    
    if first_row == -1 or last_row == -1:
        return standard_values
    
    last_column = sheet.range((first_row+1, 1), (first_row+1,sheet.cells.last_cell.column)).end('right').column
    cells = sheet.range((first_row+1, 1), (first_row+1,last_column))
    for cell in cells:
        if cell.value == model_number:
            value_column = cell.column
        elif cell.value == '# Detector model number (required)':
            description_column = cell.column
    
    name_range = sheet.range((first_row + 2, 1), (last_row, 1))
    value_range = sheet.range((first_row + 2, value_column), (last_row, value_column))
    description_range = sheet.range((first_row + 2, description_column), (last_row, description_column))
    
    for name, value, description in zip(name_range, value_range, description_range):
        standard_values[name.value] = (value.value, description.value)
    
    return standard_values

def find_endcap_values(standard_values, endcap_model, sheet):
    """
    Find the default dimensions for an endcap on the standard cfg sheet.

    Parameters
    ----------.
    endcap_model : string
        The model number of the detector.
    sheet : Sheet
        The standard config sheet.

    Returns
    -------
    standard_values : OrderedDict
        An ordered dictionary where the dimension keyword is the key and the value of
        the dimension is the value.

    """
    if (len(endcap_model) < 7):
        ctypes.windll.user32.MessageBoxW(0, 'Endcap model number not supported, default values used', 'Unsupported endcap model number', 0)
        return       
    
    if endcap_model[0:7] == "102001-":
        ec_code = "102001-DL"
        ec_params = endcap_model[7:9]
        ec_vars = "DL"
    elif endcap_model[0:6] == "100510":
        ec_code = "100510DL"
        ec_params = endcap_model[6:8]
        ec_vars = "DL"
    elif endcap_model[0:6] == "901605":
        ec_code = "901605LAMW"
        ec_params = endcap_model[6:10]
        ec_vars = "LAMW"
    elif endcap_model[0:6] == "901606":
        ec_code = "901606DLMW"
        ec_params = endcap_model[6:10]
        ec_vars = "DLMW"
    elif endcap_model[0:5] == "70758":
        ec_code = "70758DD"
        ec_params = endcap_model[5:7]
        ec_vars = "DD"        
    elif endcap_model[0:6] == "902206":
        ec_code = "902206DLWM"
        ec_params = endcap_model[6:10]
        ec_vars = "DLWM"
    elif endcap_model[0:6] == "708956":
        ec_code = "708956D"
        ec_params = endcap_model[6:7]
        ec_vars = "D"
    else:
        ctypes.windll.user32.MessageBoxW(0, 'Endcap model number not supported, default values used', 'Unsupported endcap model number', 0)
        return  

    var_number = len(ec_vars)
    if "DD" in ec_vars:
        var_number -= 1
    
    
    last_row = sheet.range('B' + str(sheet.cells.last_cell.row)).end('up').row
    B_cells = sheet.range('B1:B'+ str(last_row))   
    first_row = -1
    for cell in B_cells:
        if cell.value == ec_code:
            first_row = cell.row
            break
    if first_row == -1:
        ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
        return 
    second_row = first_row + 1
    A_cells = sheet.range('A' + str(second_row) + ':A'+ str(last_row))
    last_row = -1
    for cell in A_cells:
        if cell.value == "TheModel" or cell.value == None:
            last_row = cell.row - 1
            break
    if last_row == -1:
        ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
        return
    
    doubleFlag = False
    paramFlag = False
    first_row += 1
    
    for i in range(len(ec_vars)):
        if doubleFlag:
            doubleFlag = False
            continue
            
        char = ec_vars[i]
        digit = ec_params[i]
        if char != sheet.range((first_row,1)).value:
            if len(ec_vars) < i+2:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
                return 
            else:
                char = ec_vars[i:i+2]
                digit = ec_params[i:i+2]
                doubleFlag = True
        if char != sheet.range((first_row,1)).value:
            ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
            return 
        
        last_column = sheet.range((first_row, 1), (first_row,sheet.cells.last_cell.column)).end('right').column
        cells = sheet.range((first_row, 2), (first_row, last_column))
        for cell in cells:
            cval = cell.value
            if type(cval) == float:
                cval = int(cval)
            if type(cval) == int:
                cval = str(cval)
            
            if cval == digit:
                value_column = cell.column
                paramFlag = True
                break
        
        if paramFlag == False:
            ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
            return 
        
        
        endFlag = False
        breakFlag = False
                    
        if (i != len(ec_vars) - 1 and doubleFlag == False) or (i != len(ec_vars) -2 and doubleFlag): 
            A_cells = sheet.range((first_row+1, 1), (last_row+1, 1))
            for cell in A_cells:
                if cell.value not in standard_values.keys():
                    end_row = cell.row
                    endFlag = True
                    break
            if endFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
                return 
            name_range = sheet.range((first_row + 1, 1), (end_row-1, 1))
            value_range = sheet.range((first_row + 1, value_column), (end_row-1, value_column))
            for name, value in zip(name_range, value_range):
                descriptor = standard_values[name.value][1]
                standard_values[name.value] = (value.value, descriptor)
                
            first_row = end_row 
            
        if (i == len(ec_vars) - 1 and doubleFlag == False) or (i == len(ec_vars) -2 and doubleFlag):
            C_cells = sheet.range((first_row+1, 3), (last_row+1, 3))
            for cell in C_cells:
                if cell.value is None:
                    break_row = cell.row
                    breakFlag = True
                    break
            if breakFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
                return 
            name_range = sheet.range((first_row + 1, 1), (break_row-1, 1))
            value_range = sheet.range((first_row + 1, value_column), (break_row-1, value_column))
            for name, value in zip(name_range, value_range):
                descriptor = standard_values[name.value][1]
                standard_values[name.value] = (value.value, descriptor)
            
            A_cells = sheet.range((break_row, 1), (last_row + 1, 1))
            for cell in A_cells:
                if cell.value not in standard_values.keys():
                    end_row = cell.row
                    endFlag = True
                    break
            if endFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter endcap parameters manually', 'Error', 0)
                return     
            if end_row == break_row:
                return standard_values
            else:
                name_range = sheet.range((break_row, 1), (end_row-1, 1))
                value_range = sheet.range((break_row, 2), (end_row-1, 2))
                for name, value in zip(name_range, value_range):
                    descriptor = standard_values[name.value][1]
                    standard_values[name.value] = (value.value, descriptor)

    return standard_values
    
    
    
"""    
    if ec_code == "102001-DL":
        d_param = endcap_model[7]
        l_param = endcap_model[8]
        d_param_flag = False
        l_param_flag = False
        
        last_column = sheet.range((first_row+1, 1), (first_row+1,sheet.cells.last_cell.column)).end('right').column
        cells = sheet.range((first_row+1, 2), (first_row+1,last_column))
        for cell in cells:
            cval = cell.value
            if type(cval) == float:
                cval = int(cval)
            if type(cval) == int:
                cval = str(cval)
            
            if cval == d_param:
                value_column = cell.column
                d_param_flag = True
                break
        if d_param_flag == False:
            raise ValueError('Error, enter endcap parameters manually')
            return standard_values
        
        name_range = sheet.range((first_row + 2, 1))
        value_range = sheet.range((first_row + 2, value_column))
        for name, value in zip(name_range, value_range):
            descriptor = standard_values[name.value][1]
            standard_values[name.value] = (value.value, descriptor)
        
        last_column = sheet.range((first_row+3, 1), (first_row+3,sheet.cells.last_cell.column)).end('right').column
        cells = sheet.range((first_row+3, 2), (first_row+3,last_column))
        for cell in cells:
            cval = cell.value
            if type(cval) == float:
                cval = int(cval)
            if type(cval) == int:
                cval = str(cval)
                
            if cval == l_param:
                value_column = cell.column
                l_param_flag = True
                break
        if l_param_flag == False:
            raise ValueError('Error, enter endcap parameters manually')
            return standard_values
        
        name_range = sheet.range((first_row + 4, 1))
        value_range = sheet.range((first_row + 4, value_column))
        for name, value in zip(name_range, value_range):
            descriptor = standard_values[name.value][1]
            standard_values[name.value] = (value.value, descriptor)
            
        name_range = sheet.range((first_row + 5, 1), (last_row, 1))
        value_range = sheet.range((first_row + 5, 2), (last_row, 2))
        for name, value in zip(name_range, value_range):
            descriptor = standard_values[name.value][1]
            standard_values[name.value] = (value.value, descriptor)
"""        
def find_holder_values(standard_values, holder_model, sheet):
    """
    Find the default dimensions for a holder on the standard cfg sheet.

    Parameters
    ----------.
    holder_model : string
        The holder model number of the detector.
    sheet : Sheet
        The standard config sheet.

    Returns
    -------
    standard_values : OrderedDict
        An ordered dictionary where the dimension keyword is the key and the value of
        the dimension is the value.

    """
    if (len(holder_model) < 6):
        ctypes.windll.user32.MessageBoxW(0, 'Holder model number not supported, default values used', 'Unsupported holder model number', 0)
        return 
    if holder_model[0] == "1" and holder_model[2:6] == "1042":
        h_code = "1Y1042DDL"
        h_params = holder_model[1] + holder_model[8]
        h_vars = "YL"
    elif holder_model[0:6] == "191784":
        h_code = "191784DLM"
        h_params = holder_model[6:9]
        h_vars = "DLM"
    elif holder_model[0:6] == "707804":
        h_code = "707804L"
        h_params = holder_model[6]
        h_vars = "L"
    elif holder_model[0:6] == "707941":
        h_code = "707941L"
        h_params = holder_model[6]
        h_vars = "L"
    elif holder_model[0] == "1" and holder_model[2:6] == "csnv":
        h_code = "1YcsnvDDL"
        h_params = holder_model[1] + holder_model[8]
        h_vars = "YL"        
    elif holder_model[0] == "2" and holder_model[2:6] == "csnv":
        h_code = "2YcsnvDDL"
        h_params = holder_model[1] + holder_model[8]
        h_vars = "YL"  
    elif holder_model[0] == "3" and holder_model[2:6] == "csnv":
        h_code = "3YcsnvDD"
        h_params = holder_model[1]
        h_vars = "Y"
    elif holder_model[0] == "4" and holder_model[2:6] == "csnv":
        h_code = "4YcsnvDD"
        h_params = holder_model[1]
        h_vars = "Y"         
    elif holder_model[0:6] == "BEcsnv":
        h_code = "BEcsnvD"
        h_params = ""
        h_vars = ""
    else:
        ctypes.windll.user32.MessageBoxW(0, 'Endcap model number not supported, default values used', 'Unsupported encap model number', 0)
        return standard_values  

    
    last_row = sheet.range('B' + str(sheet.cells.last_cell.row)).end('up').row
    B_cells = sheet.range('B1:B'+ str(last_row))   
    first_row = -1
    for cell in B_cells:
        if cell.value == h_code:
            first_row = cell.row
            break
    if first_row == -1:
        ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
        return 
    #second_row = first_row + 1
    A_cells = sheet.range((first_row+1, 1), (last_row+1, 1))
    last_row = -1
    for cell in A_cells:
        if cell.value == "TheModel" or cell.value == None:
            last_row = cell.row - 1
            break
    if last_row == -1:
        ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
        return 
    
    doubleFlag = False
    paramFlag = False
    first_row += 1
    
    if h_vars == "":
        A_cells = sheet.range((first_row, 1), (last_row + 1, 1))
        for cell in A_cells:
            if cell.value not in standard_values.keys():
                end_row = cell.row
                endFlag = True
                break
        if endFlag == False:
            ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
            return     
        if end_row == last_row:
            return standard_values
        else:
            name_range = sheet.range((first_row, 1), (end_row-1, 1))
            value_range = sheet.range((first_row, 2), (end_row-1, 2))
            for name, value in zip(name_range, value_range):
                descriptor = standard_values[name.value][1]
                standard_values[name.value] = (value.value, descriptor)
            return standard_values
    
    if h_code == "707804L" or h_code == "707941L":
        name_range = sheet.range((first_row, 1))
        value_range = sheet.range((first_row, 2))
        for name, value in zip(name_range, value_range):
            descriptor = standard_values[name.value][1]
            standard_values[name.value] = (value.value, descriptor)
        first_row += 1
    
    for i in range(len(h_vars)):
        if doubleFlag:
            doubleFlag = False
            continue
            
        char = h_vars[i]
        digit = h_params[i]
        if char != sheet.range((first_row,1)).value:
            if len(h_vars) < i+2:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
                return 
            else:
                char = h_vars[i:i+2]
                digit = h_params[i:i+2]
                doubleFlag = True
        if char != sheet.range((first_row,1)).value:
            ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
            return 
        
        last_column = sheet.range((first_row, 1), (first_row,sheet.cells.last_cell.column)).end('right').column
        cells = sheet.range((first_row, 2), (first_row, last_column))
        for cell in cells:
            cval = cell.value
            if type(cval) == float:
                cval = int(cval)
            if type(cval) == int:
                cval = str(cval)
            
            if cval == digit:
                value_column = cell.column
                paramFlag = True
                break
        
        if paramFlag == False:
            ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
            return
        
        
        endFlag = False
        breakFlag = False
                    
        if (i != len(h_vars) - 1 and doubleFlag == False) or (i != len(h_vars) -2 and doubleFlag): 
            A_cells = sheet.range((first_row+1, 1), (last_row+1, 1))
            for cell in A_cells:
                if cell.value not in standard_values.keys():
                    end_row = cell.row
                    endFlag = True
                    break
            if endFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
                return
            name_range = sheet.range((first_row + 1, 1), (end_row-1, 1))
            value_range = sheet.range((first_row + 1, value_column), (end_row-1, value_column))
            for name, value in zip(name_range, value_range):
                descriptor = standard_values[name.value][1]
                standard_values[name.value] = (value.value, descriptor)
                
            first_row = end_row 
            
        if (i == len(h_vars) - 1 and doubleFlag == False) or (i == len(h_vars) -2 and doubleFlag):
            C_cells = sheet.range((first_row+1, 3), (last_row+1, 3))
            for cell in C_cells:
                if cell.value is None:
                    break_row = cell.row
                    breakFlag = True
                    break
            if breakFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
                return 
            name_range = sheet.range((first_row + 1, 1), (break_row-1, 1))
            value_range = sheet.range((first_row + 1, value_column), (break_row-1, value_column))
            for name, value in zip(name_range, value_range):
                descriptor = standard_values[name.value][1]
                standard_values[name.value] = (value.value, descriptor)
            
            A_cells = sheet.range((break_row, 1), (last_row + 1, 1))
            for cell in A_cells:
                if cell.value not in standard_values.keys():
                    end_row = cell.row
                    endFlag = True
                    break
            if endFlag == False:
                ctypes.windll.user32.MessageBoxW(0, 'Error, enter holder parameters manually', 'Error', 0)
                return     
            if end_row == break_row:
                return standard_values
            else:
                name_range = sheet.range((break_row, 1), (end_row-1, 1))
                value_range = sheet.range((break_row, 2), (end_row-1, 2))
                for name, value in zip(name_range, value_range):
                    descriptor = standard_values[name.value][1]
                    standard_values[name.value] = (value.value, descriptor)

    return standard_values            

    
def range_to_array(xlrange, func):
    """
    Convert a Range object to an list, calls func on each element in the range

    Parameters
    ----------
    xlrange : Range
        The range object that is converted to an list.
    func : callable
        The function that will be called on every element.

    Returns
    -------
    array : List
        A list containg all elements of the range.

    """
    array = []
    for cell in xlrange:
        array.append(func(cell.value))
    return array
    
def low_energy_validation(wb):
    """
    Return True if the low energy validation check box is checked

    Parameters
    ----------
    wb : xw.Book
        The excel spreadsheet.

    Returns
    -------
    bool
        True if low energy validation is checked, false if unchecked.

    """
    sheet = sheet_from_name(wb, 'Iterations')
    return sheet.api.OLEObjects('LEvalidation').Object.Value

def set_low_energy_validation(wb, value):
    """
    Set the low energy validation to value

    Parameters
    ----------
    wb : xw.Book
        The excel spreadsheet.
    value : bool
        The value that the check box will be set to.

    Returns
    -------
    None.

    """
    sheet = sheet_from_name(wb, 'Iterations')
    sheet.api.OLEObjects('LEvalidation').Object.Value = value
    
# The low energy cut off for the different geometries.
low_energy_cutoff = {'0D':38,
                     '45D':38,
                     '90D':38,
                     '135D':38,
                     'DC':38,
                     'DF':38,
                     'WE':38,
                     'RELEFF':38}
