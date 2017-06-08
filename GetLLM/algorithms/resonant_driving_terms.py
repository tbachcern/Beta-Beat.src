'''
Created on May 15, 2014

@author: fcarlier

@version: 0.0.1

GetLLM.algorithms.resonant_driving_terms.py stores helper functions for RDT calculations for GetLLM.
This module is not intended to be executed. It stores only functions.
'''

import sys

import Utilities.bpm
import helper
import numpy as np

exist_curve_fit = True

try:
    from scipy.optimize import curve_fit
except ImportError:
    exist_curve_fit = False

DEBUG = sys.flags.debug # True with python option -d! ("python -d GetLLM.py...") (vimaier)


RDT_LIST = ['f1001H', 'f1010H', 'f0110V', 'f1010V',  #Quadrupolar
            'f3000H', 'f1200H', 'f1020H', 'f1002H',  #Normal Sextupolar
            'f0111V', 'f1020V', 'f0120V', 'f1011V', 
            'f0030V', 'f0012V', 'f0210V', 'f2010V',  #Skew Sextupolar
            'f1101H', 'f2010H', 'f1110H', 'f2001H', 
            'f4000H', 'f1300H', 'f2002H', 'f1120H',  #Normal Octupolar
            'f1102H', 'f2020H', 'f2020V', 'f2011V', 
            'f0220V', 'f0211V', 'f0040V', 'f0013V',
            'f3001H', 'f1210H', 'f0130V', 'f1012V',  #Skew Octupolar
            'f1220H', 'f3002H', 'f1130H', 'f2003H'
#             'f0220V', 'f2011V', 'f1201H', 'f3010H',  ## LINES NOT IN DRIVE, YET....
#             'f1003H', 'f1030H', 'f0310V', 'f3010V'   ## LINES NOT IN DRIVE, YET....
            ]


def determine_lines(rdt):
    r = list(rdt)
    j, k, l, m, plane = int(r[1]), int(r[2]), int(r[3]), int(r[4]), r[5]
    if plane == 'H':
        line = (1-j+k, m-l)
    elif plane == 'V':
        line = (k-j, 1-l+m)
    return line, plane


def calculate_RDTs(mad_twiss, getllm_d, twiss_d, phase_d, tune_d, files_dict, inv_x, inv_y):
    '''
    Calculates line RDT amplitudes and phases and fills the following TfsFiles:
        f3000_line.out ...

    :Parameters:
        'getllm_d': _GetllmData (In-param, values will only be read)
            lhc_phase, accel, beam_direction and num_beams_for_coupling are used.
        'twiss_d': _TwissData (In-param, values will only be read)
            Holds twiss instances of the src files.
        'tune_d': _TuneData (In-param, values will only be read)
            Holds tunes and phase advances.
    '''
    print "Calculating RDTs"

    """
    The rdt_set holds all RDTs which should be investigated with the parameters to call GetRDT()
    syntax is: rdt_set = [(plane, out_file, line), ...]
    with:
        plane in ["H", "V"]
        out_file in files_dict is the out file to write the data to (must be added to GetLLM.py)
        line in (int, int) is the corresponding line to the driving term
    """
    beam = getllm_d.beam_direction

    if exist_curve_fit:
        for rdt in RDT_LIST:
            line, plane = determine_lines(rdt)
            _process_RDT(mad_twiss, phase_d, twiss_d, (plane, files_dict[rdt+'_line.out'], files_dict[rdt+'.out'], line), inv_x, inv_y, rdt, beam)
    else:
        print 'Curve fit not imported.. RDTs skipped'


def _process_RDT(mad_twiss, phase_d, twiss_d, (plane, out_file, rdt_out_file, line), inv_x, inv_y, rdt, beam):
    assert plane in ["H", "V"] # check user input plane
    
    # get plane corresponding phase and twiss data
    if plane == "H":
        phase_data = phase_d.ph_x
        list_zero_dpp = twiss_d.zero_dpp_x
    else:
        phase_data = phase_d.ph_y
        list_zero_dpp = twiss_d.zero_dpp_y

    dbpms = Utilities.bpm.intersect(list_zero_dpp)
    dbpms = Utilities.bpm.model_intersect(dbpms, mad_twiss)
    bpm_positions, bpm_names = zip(*dbpms)


    # init out file
    out_file.add_column_names(["NAME", "S", "COUNT", "AMP", "EAMP", "PHASE", "EPHASE"])
    out_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le", "%le", "%le"])

    line_amplitudes = []
    line_amplitudes_err = []
    line_phases = []
    line_phases_err = []

    use_line = False
    use_opposite_line = False   
    
    
    try:
        _, _ = _line_to_amp_and_phase_attr(line, list_zero_dpp[0])
        use_line = True
    except AttributeError:
        print >> sys.stderr, "Line not found, trying opposite line.. (%s, %s)!\n\t" % line
    try:
        _, _ = _line_to_amp_and_phase_attr((-line[0],-line[1]), list_zero_dpp[0])
        use_opposite_line = True
    except AttributeError:
        print >> sys.stderr, "Opposite line not found.. (%s, %s)!\n\t" % (-line[0],-line[1])

    if use_line or use_opposite_line:  
        for i in range(len(dbpms)-4):
            bpm1 = dbpms[i][1].upper()
            try:
                bpm_pair_data = phase_data[bpm1][7], phase_data[bpm1][8], phase_data[bpm1][9]
            except KeyError:
                print >> sys.stderr, "Could not find a BPM pair (%s, %s)!\n\t" % (plane, bpm1)
                continue
            
            bpm2 = bpm_pair_data[0]
            for j in range(0,len(list_zero_dpp)):
    
                if use_line and use_opposite_line:
                    amp_line, phase_line = _line_to_amp_and_phase_attr(line, list_zero_dpp[j])
                    amp_line_opp, phase_line_opp = _line_to_amp_and_phase_attr((-line[0],-line[1]), list_zero_dpp[j])
                    phase_line_opp = -phase_line_opp 
                    amp_line = (amp_line + amp_line_opp)/2.
                    phase_line = (phase_line + phase_line_opp)/2.
                elif use_line and not use_opposite_line:
                    amp_line, phase_line = _line_to_amp_and_phase_attr(line, list_zero_dpp[j])
                elif use_opposite_line and not use_line:
                    amp_line, phase_line = _line_to_amp_and_phase_attr((-line[0],-line[1]), list_zero_dpp[j])
                    phase_line = -phase_line 

                if beam == 1:
                    delta, edelta = bpm_pair_data[1:]
                    amp1 = amp_line[list_zero_dpp[j].indx[bpm1]]
                    amp2 = amp_line[list_zero_dpp[j].indx[bpm2]]
                    phase1 = phase_line[list_zero_dpp[j].indx[bpm1]]
                    phase2 = phase_line[list_zero_dpp[j].indx[bpm2]]
                
                    line_amp, line_phase, line_amp_e, line_phase_e = helper.ComplexSecondaryLineExtended(delta,edelta, amp1, amp2, phase1, phase2)
                    out_file.add_table_row([bpm1, dbpms[i][0], len(list_zero_dpp), line_amp, line_amp_e, line_phase, line_phase_e])
                    line_amplitudes.append(line_amp)
                    line_amplitudes_err.append(line_amp_e)
                    line_phases.append(line_phase)
                    line_phases_err.append(line_phase_e)
    
                elif beam == -1:
                    delta, edelta = bpm_pair_data[1:]
                    amp1 = amp_line[list_zero_dpp[j].indx[bpm1]]
                    amp2 = amp_line[list_zero_dpp[j].indx[bpm2]]
                    phase1 = phase_line[list_zero_dpp[j].indx[bpm1]]
                    phase2 = phase_line[list_zero_dpp[j].indx[bpm2]]
                    bpm_position = bpm_positions[bpm_names.index(bpm2)]

                    line_amp, line_phase, line_amp_e, line_phase_e = helper.ComplexSecondaryLineExtended(delta,edelta, amp2, amp1, phase2, phase1)
                    out_file.add_table_row([bpm2, bpm_position, len(list_zero_dpp), line_amp, line_amp_e, line_phase, line_phase_e])
                    line_amplitudes.append(line_amp)
                    line_amplitudes_err.append(line_amp_e)
                    line_phases.append(line_phase)
                    line_phases_err.append(line_phase_e)

    else:
        print >> sys.stderr, "Could not find line for %s !\n\t" %rdt
    # init out file
    rdt_out_file.add_column_names(["NAME", "S", "COUNT", "AMP", "EAMP"])
    rdt_out_file.add_column_datatypes(["%s", "%le", "%le", "%le", "%le"])

    for k in range(len(line_amplitudes)/len(list_zero_dpp)):
        num_meas = len(list_zero_dpp)
        bpm_name = dbpms[k][1].upper()
        bpm_rdt_data = line_amplitudes[k*num_meas:(k+1)*num_meas]
        res, res_err = do_fitting(bpm_rdt_data, inv_x, inv_y, rdt, plane)
        rdt_out_file.add_table_row([bpm_name, dbpms[k][0], len(list_zero_dpp), res[0], res_err[0]])


def rdt_function_gen(rdt, plane):
    '''
    Note that the factor 2 in 2*j*f_jklm*.... is absent due to the normalization with the main line. 
    The main line has an amplitude of sqrt(2J*beta)/2
    '''
    r = list(rdt)
    j, k, l, m, plane = int(r[1]), int(r[2]), int(r[3]), int(r[4]), r[5]
    if plane == 'H':
        def rdt_function(x, f):
            return 2 * j * f * x[0]**((j+k-2)/2.) * x[1]**((l+m)/2.)
    elif plane == 'V':
        def rdt_function(x, f):
            return 2 * l * f * x[0]**((j+k)/2.) * x[1]**((l+m-2)/2.)
    return rdt_function


def do_fitting(bpm_rdt_data, kick_x, kick_y, rdt, plane):
    func = rdt_function_gen(rdt, plane)
    kick_data = np.vstack((np.transpose(kick_x)[0]**2, np.transpose(kick_y)[0]**2))
    popt, pcov = curve_fit(func, kick_data, bpm_rdt_data)
    perr = np.sqrt(np.diag(pcov))
    return popt, perr


def _line_to_amp_and_phase_attr(line, zero_dpp):
    '''To turn input line (-1,2) to (zero_dpp.AMP_12, zero_dpp.PHASE_12).'''
    line = (str(line[0])+str(line[1])).replace("-", "_")
    return (getattr(zero_dpp, "AMP"+line), getattr(zero_dpp, "PHASE"+line))
