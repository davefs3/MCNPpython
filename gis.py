# -*- coding: utf-8 -*-
"""
Created on Tue Jan  4 14:30:29 2022

@author: edang
"""
import os, sys

def well_maker(well_depth, path):
    adjust = 40 - well_depth
    
    """Original text for .bkr file with well depth of 40 mm """
    
    originalfile="""# Inner Contour
# -------------
#
# D1,mm        H1,mm        D2,mm        H2,mm        ID  Material  Density g/cc
#-------------------------------------------------------------------------------
  0          , -39        , 0.85       , -38.98     , i,  POLYPROP, 0.91
  0.85       , -38.98     , 1.693      , -38.93     , i,  POLYPROP, 0.91
  1.693      , -38.93     , 2.523      , -38.83     , i,  POLYPROP, 0.91
  2.523      , -38.83     , 3.335      , -38.71     , i,  POLYPROP, 0.91
  3.335      , -38.71     , 4.121      , -38.54     , i,  POLYPROP, 0.91
  4.121      , -38.54     , 4.875      , -38.35     , i,  POLYPROP, 0.91
  4.875      , -38.35     , 5.592      , -38.12     , i,  POLYPROP, 0.91
  5.592      , -38.12     , 6.267      , -37.86     , i,  POLYPROP, 0.91
  6.267      , -37.86     , 6.894      , -37.57     , i,  POLYPROP, 0.91
  6.894      , -37.57     , 7.47       , -37.26     , i,  POLYPROP, 0.91
  7.47       , -37.26     , 7.987      , -36.92     , i,  POLYPROP, 0.91
  7.987      , -36.92     , 8.444      , -36.56     , i,  POLYPROP, 0.91
  8.444      , -36.56     , 8.837      , -36.19     , i,  POLYPROP, 0.91
  8.837      , -36.19     , 9.16       , -35.79     , i,  POLYPROP, 0.91
  9.16       , -35.79     , 9.418      , -35.39     , i,  POLYPROP, 0.91
  9.418      , -35.39     , 9.601      , -34.97     , i,  POLYPROP, 0.91
  9.601      , -34.97     , 9.713      , -34.55     , i,  POLYPROP, 0.91
  9.713      , -34.55     , 9.75       , -34.13     , i,  POLYPROP, 0.91
  9.75       , -34.13     , 9.75       , 35         , i,  POLYPROP, 0.91
  9.75       , 35         , 0          , 35         , i,  POLYPROP, 0.91
#-------------------------------------------------------------------------------
# Outer Contour
# -------------
#
# D1,mm        H1,mm        D2,mm        H2,mm        ID  Material  Density g/cc
#-------------------------------------------------------------------------------
  0          , -40        , 1.024      , -39.98     , o,  POLYPROP, 0.91
  1.024      , -39.98     , 2.04       , -39.91     , o,  POLYPROP, 0.91
  2.04       , -39.91     , 3.041      , -39.8      , o,  POLYPROP, 0.91
  3.041      , -39.8      , 4.018      , -39.65     , o,  POLYPROP, 0.91
  4.018      , -39.65     , 4.966      , -39.45     , o,  POLYPROP, 0.91
  4.966      , -39.45     , 5.875      , -39.21     , o,  POLYPROP, 0.91
  5.875      , -39.21     , 6.74       , -38.94     , o,  POLYPROP, 0.91
  6.74       , -38.94     , 7.553      , -38.63     , o,  POLYPROP, 0.91
  7.553      , -38.63     , 8.309      , -38.3      , o,  POLYPROP, 0.91
  8.309      , -38.3      , 9.001      , -37.9      , o,  POLYPROP, 0.91
  9.001      , -37.9      , 9.625      , -37.49     , o,  POLYPROP, 0.91
  9.625      , -37.49     , 10.18      , -37.06     , o,  POLYPROP, 0.91
  10.18      , -37.06     , 10.65      , -36.61     , o,  POLYPROP, 0.91
  10.65      , -36.61     , 11.04      , -36.13     , o,  POLYPROP, 0.91
  11.04      , -36.13     , 11.35      , -35.65     , o,  POLYPROP, 0.91
  11.35      , -35.65     , 11.57      , -35.15     , o,  POLYPROP, 0.91
  11.57      , -35.15     , 11.71      , -34.64     , o,  POLYPROP, 0.91
  11.71      , -34.64     , 11.75      , -34.13     , o,  POLYPROP, 0.91
  11.75      , -34.13     , 11.75      , 35         , o,  POLYPROP, 0.91
  11.75      , 35         , 0          , 35         , o,  POLYPROP, 0.91
#-------------------------------------------------------------------------------
"""
    
    
    wellfile = ""
    
    """Split 40 mm file into a list of strings for each line"""
    
    
    brokenstring = originalfile.splitlines()
    
    """Make modifications to the numbers in the strings corresponding to the
       appropriate line"""
    
    for i in range(len(brokenstring)):
        if i > 4 and i < 23:
            line1 = brokenstring[i]
            
            d1 = line1[15:21]
            d01 = float(d1)
            newd01= format(d01+adjust,'.2f')
            
            d2 = line1[41:47]
            d02 = float(d2)
            newd02= format(d02+adjust, '.2f')
            
            line1 = line1[0:15] + newd01 + line1[21:41] + newd02 + line1[47:72]
            brokenstring[i] = line1
        
        if i == 23:
            line1 = brokenstring[i]
            
            d1 = line1[15:21]
            d01 = float(d1)
            newd01= format(d01+adjust,'.2f')
            
            line1 = line1[0:15] + newd01 + line1[21:72] 
            brokenstring[i] = line1
        
        if i > 30 and i < 49:
            line1 = brokenstring[i]
            
            d1 = line1[15:21]
            d01 = float(d1)
            newd01= format(d01+adjust,'.2f')
            
            d2 = line1[41:47]
            d02 = float(d2)
            newd02= format(d02+adjust, '.2f')
            
            line1 = line1[0:15] + newd01 + line1[21:41] + newd02 + line1[47:72]
            brokenstring[i] = line1
            
        if i == 49:
            line1 = brokenstring[i]
            
            d1 = line1[15:21]
            d01 = float(d1)
            newd01= format(d01+adjust,'.2f')
            
            line1 = line1[0:15] + newd01 + line1[21:72] 
            brokenstring[i] = line1
        
        """Rewrite the new list of strings into a new well file"""
        
        wellfile += brokenstring[i] + '\n'
    
    #bkr_file = open("WE.bkr", "w")
        with open(os.path.join(path, 'WE.bkr'), "w") as bkr_file:
            n = bkr_file.write(wellfile)
            #bkr_file.write('\n' + path)
            bkr_file.close()

well_maker(42, r"P:\ISOCSProduction\Det_Junk1\1734_98684")

print (os.getcwd())
#print(wellfile)
        
