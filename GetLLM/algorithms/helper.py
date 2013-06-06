'''
Created on 5 Jun 2013

@author: vimaier

@version: 0.0.1

GetLLM.algorithms.helper contains the helper funtions which are used by GetLLM.py.
This module is not intended to be executed. It stores only functions.

Change history:
 - <version>, <author>, <date>:
    <description>
'''

import sys
if "/afs/cern.ch/eng/sl/lintrack/Python_Classes4MAD/" not in sys.path: # add internal path for python scripts to current environment (tbach)
    sys.path.append('/afs/cern.ch/eng/sl/lintrack/Python_Classes4MAD/')
if "/afs/cern.ch/eng/sl/lintrack/Beta-Beat.src/" not in sys.path: # added for Utilities.bpm (vimaier)
    sys.path.append('/afs/cern.ch/eng/sl/lintrack/Beta-Beat.src/')
import metaclass
import os
import string
import math

from numpy import sin,cos,tan
import numpy as np

import Utilities.bpm





#===================================================================================================
# helper-functions
#===================================================================================================
#------------ Get phases

def phiLastAndLastButOne(phi,ftune):
    if ftune > 0.0:
        phit=phi+ftune
        if phit>1.0: phit=phit-1.0
    elif ftune <= 0.0:
        phit=phi+(1.0+ftune)
        if phit>1.0: phit=phit-1.0
    return phit

def PhaseMean(phase0,norm):  #-- phases must be in [0,1) or [0,2*pi), norm = 1 or 2*pi
    phase0 = np.array(phase0)%norm
    phase1 = (phase0+0.5*norm)%norm - 0.5*norm
    phase0ave = np.mean(phase0)
    phase1ave = np.mean(phase1)
    # Since phase0std and phase1std are only used for comparing, I modified the expressions to avoid
    # math.sqrt(), np.mean() and **2. 
    # Old expressions:
    #     phase0std = math.sqrt(np.mean((phase0-phase0ave)**2))
    #     phase1std = math.sqrt(np.mean((phase1-phase1ave)**2))
    # -- vimaier 
    mod_phase0std = sum(abs(phase0-phase0ave))
    mod_phase1std = sum(abs(phase1-phase1ave))
    if mod_phase0std < mod_phase1std: 
        return phase0ave
    else: 
        return phase1ave%norm

def PhaseStd(phase0,norm):  #-- phases must be in [0,1) or [0,2*pi), norm = 1 or 2*pi
    phase0   =np.array(phase0)%norm
    phase1   =(phase0+0.5*norm)%norm-0.5*norm
    phase0ave=np.mean(phase0)
    phase1ave=np.mean(phase1)
    phase0std=math.sqrt(np.mean((phase0-phase0ave)**2))
    phase1std=math.sqrt(np.mean((phase1-phase1ave)**2))
    return min(phase0std,phase1std)


def GetPhasesTotal(MADTwiss,ListOfFiles,Q,plane,bd,oa,op):
    commonbpms = Utilities.bpm.intersect(ListOfFiles)
    commonbpms = Utilities.bpm.modelIntersect(commonbpms, MADTwiss)
    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if op=="1" and oa=="LHCB1": s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    if op=="1" and oa=="LHCB2": s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    bn1=string.upper(commonbpms[0][1])
    phaseT={}
    print "Reference BPM:", bn1, "Plane:", plane
    for i in range(0,len(commonbpms)):
        #bn2=string.upper(commonbpms[i+1][1]) ?
        bn2=string.upper(commonbpms[i][1])
        if plane=='H':
            phmdl12=(MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[bn1]]) % 1
        if plane=='V':
            phmdl12=(MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[bn1]]) % 1

        phi12=[]
        for j in ListOfFiles:
            # Phase is in units of 2pi
            if plane=='H':
                phm12=(j.MUX[j.indx[bn2]]-j.MUX[j.indx[bn1]]) % 1
            if plane=='V':
                phm12=(j.MUY[j.indx[bn2]]-j.MUY[j.indx[bn1]]) % 1
            #-- To fix the phase shift by Q in LHC
            try:
                if commonbpms[i][0]>s_lastbpm: phm12+=bd*Q
            except: pass
            phi12.append(phm12)
        phi12=np.array(phi12)
        # for the beam circulating reversely to the model
        if bd==-1: phi12=1.0-phi12

        #phstd12=math.sqrt(np.average(phi12*phi12)-(np.average(phi12))**2.0+2.2e-15)
        #phi12=np.average(phi12)
        phstd12=PhaseStd(phi12,1.0)
        phi12  =PhaseMean(phi12,1.0)
        phaseT[bn2]=[phi12,phstd12,phmdl12,bn1]

    return [phaseT,commonbpms]


def GetPhases(MADTwiss,ListOfFiles,Q,plane,outputpath,beam_direction,accel,lhcphase):
    commonbpms = Utilities.bpm.intersect(ListOfFiles)
    commonbpms = Utilities.bpm.modelIntersect(commonbpms, MADTwiss)
    length_commonbpms = len(commonbpms)
    #print len(commonbpms)
    #sys.exit()

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if lhcphase=="1" and accel=="LHCB1": 
        s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    if lhcphase=="1" and accel=="LHCB2": 
        s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    mu=0.0
    tunem=[]
    phase={} # Dictionary for the output containing [average phase, rms error]
    for i in range(0,length_commonbpms): # To find the integer part of tune as well, the loop is up to the last monitor
        bn1=string.upper(commonbpms[i%length_commonbpms][1])
        bn2=string.upper(commonbpms[(i+1)%length_commonbpms][1])
        bn3=string.upper(commonbpms[(i+2)%length_commonbpms][1])
        
        if bn1 == bn2 :
            print >> sys.stderr, "There seem two lines with the same BPM name "+bn1+" in linx/y file."
            print >> sys.stderr, "Please check your input data....leaving GetLLM."
            sys.exit(1)
            
        if plane == 'H':
            phmdl12 = MADTwiss.MUX[MADTwiss.indx[bn2]] - MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl13 = MADTwiss.MUX[MADTwiss.indx[bn3]] - MADTwiss.MUX[MADTwiss.indx[bn1]]
        elif plane == 'V':
            phmdl12 = MADTwiss.MUY[MADTwiss.indx[bn2]] - MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl13 = MADTwiss.MUY[MADTwiss.indx[bn3]] - MADTwiss.MUY[MADTwiss.indx[bn1]]
            
        if i == length_commonbpms-2:
            if plane == 'H':
                madtune = MADTwiss.Q1 % 1.0
            elif plane == 'V':
                madtune = MADTwiss.Q2 % 1.0
            
            if madtune > 0.5:
                madtune -= 1.0
            
            phmdl13 = phmdl13 % 1.0
            phmdl13 = phiLastAndLastButOne(phmdl13,madtune)
        elif i == length_commonbpms-1:
            if plane == 'H':
                madtune = MADTwiss.Q1 % 1.0
            elif plane == 'V':
                madtune = MADTwiss.Q2 % 1.0
            
            if madtune>0.5:
                madtune -= 1.0
            
            phmdl12 = phmdl12 % 1.0
            phmdl13 = phmdl13 % 1.0
            phmdl12 = phiLastAndLastButOne(phmdl12,madtune)
            phmdl13 = phiLastAndLastButOne(phmdl13,madtune)




        phi12=[]
        phi13=[]
        tunemi=[]
        for j in ListOfFiles:
            # Phase is in units of 2pi
            if plane=='H':
                phm12=(j.MUX[j.indx[bn2]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM2
                phm13=(j.MUX[j.indx[bn3]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM3
                tunemi.append(j.TUNEX[j.indx[bn1]])
            elif plane=='V':
                phm12=(j.MUY[j.indx[bn2]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM2
                phm13=(j.MUY[j.indx[bn3]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM3
                tunemi.append(j.TUNEY[j.indx[bn1]])
            #-- To fix the phase shift by Q in LHC
            try:
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn2]] >s_lastbpm: 
                    phm12 += beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn3]] >s_lastbpm: 
                    phm13 += beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn2]]<=s_lastbpm: 
                    phm12 += -beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn3]]<=s_lastbpm: 
                    phm13 += -beam_direction*Q
            except: pass
            if phm12<0: phm12+=1
            if phm13<0: phm13+=1
            phi12.append(phm12)
            phi13.append(phm13)

        phi12=np.array(phi12)
        phi13=np.array(phi13)
        if beam_direction==-1: # for the beam circulating reversely to the model
            phi12=1.0-phi12
            phi13=1.0-phi13

        #if any(phi12)>0.9 and i !=len(commonbpms): # Very small phase advance could result in larger than 0.9 due to measurement error
        #       print 'Warning: there seems too large phase advance! '+bn1+' to '+bn2+' = '+str(phi12)+'in plane '+plane+', recommended to check.'
        phstd12=PhaseStd(phi12,1.0)
        phstd13=PhaseStd(phi13,1.0)
        phi12=PhaseMean(phi12,1.0)
        phi13=PhaseMean(phi13,1.0)
        #phstd12=math.sqrt(np.average(phi12*phi12)-(np.average(phi12))**2.0+2.2e-15)
        #phstd13=math.sqrt(np.average(phi13*phi13)-(np.average(phi13))**2.0+2.2e-15)
        #phi12=np.average(phi12)
        #phi13=np.average(phi13)
        tunemi=np.array(tunemi)
        if i<length_commonbpms-1 :
            tunem.append(np.average(tunemi))

        # Note that the phase advance between the last monitor and the first monitor should be find by taking into account the fractional part of tune.
        if i==length_commonbpms-2:
            tunem=np.array(tunem)
            tune=np.average(tunem)
            phi13=phiLastAndLastButOne(phi13,tune)
        elif i==length_commonbpms-1:
            phi12=phiLastAndLastButOne(phi12,tune)
            phi13=phiLastAndLastButOne(phi13,tune)
        mu=mu+phi12

        small=0.0000001
        if (abs(phmdl12) < small):
            phmdl12=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl13) < small):
            phmdl13=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi12) < small ):
            phi12 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi13) < small):
            phi13 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        phase[bn1]=[phi12,phstd12,phi13,phstd13,phmdl12,phmdl13,bn2]

#TODO: Phase advance for last to first BPM?
 
        bn1 = string.upper(commonbpms[i%len(commonbpms)][1])
        bn2 = string.upper(commonbpms[(i+1)%len(commonbpms)][1])
        bn3 = string.upper(commonbpms[(i+2)%len(commonbpms)][1])
        bn4 = string.upper(commonbpms[(i+3)%len(commonbpms)][1])
        bn5 = string.upper(commonbpms[(i+4)%len(commonbpms)][1])
        bn6 = string.upper(commonbpms[(i+5)%len(commonbpms)][1])
        bn7 = string.upper(commonbpms[(i+6)%len(commonbpms)][1])


        phi12=[]
        phi13=[]
        phi14=[]
        phi15=[]
        phi16=[]
        phi17=[]

        for j in ListOfFiles:
            # Phase is in units of 2pi
            if plane=='H':
                phm12=(j.MUX[j.indx[bn2]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM2
                phm13=(j.MUX[j.indx[bn3]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM3
                phm14=(j.MUX[j.indx[bn4]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM4
                phm15=(j.MUX[j.indx[bn5]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM5
                phm16=(j.MUX[j.indx[bn6]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM6
                phm17=(j.MUX[j.indx[bn7]]-j.MUX[j.indx[bn1]]) # the phase advance between BPM1 and BPM7
            elif plane=='V':
                phm12=(j.MUY[j.indx[bn2]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM2
                phm13=(j.MUY[j.indx[bn3]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM3
                phm14=(j.MUY[j.indx[bn4]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM4
                phm15=(j.MUY[j.indx[bn5]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM5
                phm16=(j.MUY[j.indx[bn6]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM6
                phm17=(j.MUY[j.indx[bn7]]-j.MUY[j.indx[bn1]]) # the phase advance between BPM1 and BPM7
            #-- To fix the phase shift by Q in LHC
            try:
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn2]] >s_lastbpm: phm12+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn3]] >s_lastbpm: phm13+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn4]] >s_lastbpm: phm14+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn5]] >s_lastbpm: phm15+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn6]] >s_lastbpm: phm16+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]]<=s_lastbpm and MADTwiss.S[MADTwiss.indx[bn7]] >s_lastbpm: phm17+= beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn2]]<=s_lastbpm: phm12+=-beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn3]]<=s_lastbpm: phm13+=-beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn4]]<=s_lastbpm: phm14+=-beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn5]]<=s_lastbpm: phm15+=-beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn6]]<=s_lastbpm: phm16+=-beam_direction*Q
                if MADTwiss.S[MADTwiss.indx[bn1]] >s_lastbpm and MADTwiss.S[MADTwiss.indx[bn7]]<=s_lastbpm: phm17+=-beam_direction*Q
            except: pass
            if phm12<0: phm12+=1
            if phm13<0: phm13+=1
            if phm14<0: phm14+=1
            if phm15<0: phm15+=1
            if phm16<0: phm16+=1
            if phm17<0: phm17+=1
            phi12.append(phm12)
            phi13.append(phm13)
            phi14.append(phm14)
            phi15.append(phm15)
            phi16.append(phm16)
            phi17.append(phm17)

        phi12=np.array(phi12)
        phi13=np.array(phi13)
        phi14=np.array(phi14)
        phi15=np.array(phi15)
        phi16=np.array(phi16)
        phi17=np.array(phi17)
        if beam_direction==-1: # for the beam circulating reversely to the model
            phi12=1.0-phi12
            phi13=1.0-phi13
            phi14=1.0-phi14
            phi15=1.0-phi15
            phi16=1.0-phi16
            phi17=1.0-phi17

        phstd12=PhaseStd(phi12,1.0)
        phstd13=PhaseStd(phi13,1.0)
        phstd14=PhaseStd(phi14,1.0)
        phstd15=PhaseStd(phi15,1.0)
        phstd16=PhaseStd(phi16,1.0)
        phstd17=PhaseStd(phi17,1.0)
        phi12=PhaseMean(phi12,1.0)
        phi13=PhaseMean(phi13,1.0)
        phi14=PhaseMean(phi14,1.0)
        phi15=PhaseMean(phi15,1.0)
        phi16=PhaseMean(phi16,1.0)
        phi17=PhaseMean(phi17,1.0)
        

        if plane=='H':
            phmdl12=MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl13=MADTwiss.MUX[MADTwiss.indx[bn3]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl14=MADTwiss.MUX[MADTwiss.indx[bn4]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl15=MADTwiss.MUX[MADTwiss.indx[bn5]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl16=MADTwiss.MUX[MADTwiss.indx[bn6]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
            phmdl17=MADTwiss.MUX[MADTwiss.indx[bn7]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
        elif plane=='V':
            phmdl12=MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl13=MADTwiss.MUY[MADTwiss.indx[bn3]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl14=MADTwiss.MUY[MADTwiss.indx[bn4]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl15=MADTwiss.MUY[MADTwiss.indx[bn5]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl16=MADTwiss.MUY[MADTwiss.indx[bn6]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
            phmdl17=MADTwiss.MUY[MADTwiss.indx[bn7]]-MADTwiss.MUY[MADTwiss.indx[bn1]]
 
        
        if (abs(phmdl12) < small):
            phmdl12=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl13) < small):
            phmdl13=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi12) < small ):
            phi12 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn2+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi13) < small):
            phi13 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn3+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl14) < small):
            phmdl14=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn4+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl15) < small):
            phmdl15=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn5+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi14) < small ):
            phi14 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn4+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi15) < small):
            phi15 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn5+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl16) < small):
            phmdl16=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn6+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phmdl17) < small):
            phmdl17=small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn7+" in MAD model is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi16) < small ):
            phi16 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn6+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
        if (abs(phi17) < small):
            phi17 = small
            print "Note: Phase advance (Plane"+plane+") between "+bn1+" and "+bn7+" in measurement is EXACTLY n*pi. GetLLM slightly differ the phase advance here, artificially."
            print "Beta from amplitude around this monitor will be slightly varied."
            
        if plane=='H':
            phase["".join(['H',bn1,bn2])] = [phi12,phstd12,phmdl12]
            phase["".join(['H',bn1,bn3])] = [phi13,phstd13,phmdl13]
            phase["".join(['H',bn1,bn4])] = [phi14,phstd14,phmdl14]
            phase["".join(['H',bn1,bn5])] = [phi15,phstd15,phmdl15]
            phase["".join(['H',bn1,bn6])] = [phi16,phstd16,phmdl16]
            phase["".join(['H',bn1,bn7])] = [phi17,phstd17,phmdl17]
        elif plane=='V':
            phase["".join(['V',bn1,bn2])] = [phi12,phstd12,phmdl12]
            phase["".join(['V',bn1,bn3])] = [phi13,phstd13,phmdl13]
            phase["".join(['V',bn1,bn4])] = [phi14,phstd14,phmdl14]
            phase["".join(['V',bn1,bn5])] = [phi15,phstd15,phmdl15]
            phase["".join(['V',bn1,bn6])] = [phi16,phstd16,phmdl16]
            phase["".join(['V',bn1,bn7])] = [phi17,phstd17,phmdl17]


    return [phase,tune,mu,commonbpms]

#-------- Beta from pahses

def BetaFromPhase_BPM_left(bn1,bn2,bn3,MADTwiss,phase,plane):  
    ''' 
    Calculates the beta/alfa function and their errors using the 
    phase advance between three BPMs for the case that the probed BPM is left of the other two BPMs
    :Parameters: 
        'bn1':string 
            Name of probed BPM 
        'bn2':string 
            Name of first BPM right of the probed BPM
        'bn3':string 
            Name of second BPM right of the probed BPM 
        'MADTwiss':twiss 
            model twiss file 
        'phase':dict
            measured phase advances 
        'plane':string 
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd) 
        'bet':float 
            calculated beta function at probed BPM
        'betstd':float 
            calculated error on beta function at probed BPM
        'alf':float 
            calculated alfa function at probed BPM
        'alfstd':float 
            calculated error on alfa function at probed BPM
    '''
    ph2pi12=2.*np.pi*phase["".join([plane,bn1,bn2])][0]
    ph2pi13=2.*np.pi*phase["".join([plane,bn1,bn3])][0]
      
    # Find the model transfer matrices for beta1
    phmdl12 = 2.*np.pi*phase["".join([plane,bn1,bn2])][2]
    phmdl13=2.*np.pi*phase["".join([plane,bn1,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl1=MADTwiss.ALFX[MADTwiss.indx[bn1]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl1=MADTwiss.ALFY[MADTwiss.indx[bn1]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta1 and alpha1 from phases assuming model transfer matrix
    # Matrix M: BPM1-> BPM2
    # Matrix N: BPM1-> BPM3
    M11=math.sqrt(betmdl2/betmdl1)*(cos(phmdl12)+alpmdl1*sin(phmdl12))
    M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
    N11=math.sqrt(betmdl3/betmdl1)*(cos(phmdl13)+alpmdl1*sin(phmdl13))
    N12=math.sqrt(betmdl1*betmdl3)*sin(phmdl13)

    denom=M11/M12-N11/N12+1e-16
    numer=1/tan(ph2pi12)-1/tan(ph2pi13)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    denom=M12/M11-N12/N11+1e-16
    numer=-M12/M11/tan(ph2pi12)+N12/N11/tan(ph2pi13)
    alf=numer/denom

    alfstd=        (M12/M11*2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    alfstd=alfstd+(N12/N11*2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    alfstd=math.sqrt(alfstd)/denom

    return bet, betstd, alf, alfstd
    
def BetaFromPhase_BPM_mid(bn1,bn2,bn3,MADTwiss,phase,plane): 
    ''' 
    Calculates the beta/alfa function and their errors using the 
    phase advance between three BPMs for the case that the probed BPM is between the other two BPMs
    :Parameters: 
        'bn1':string 
            Name of BPM left of the probed BPM
        'bn2':string 
            Name of probed BPM 
        'bn3':string 
            Name of BPM right of the probed BPM 
        'MADTwiss':twiss 
            model twiss file 
        'phase':dict
            measured phase advances 
        'plane':string 
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd) 
        'bet':float 
            calculated beta function at probed BPM
        'betstd':float 
            calculated error on beta function at probed BPM
        'alf':float 
            calculated alfa function at probed BPM
        'alfstd':float 
            calculated error on alfa function at probed BPM
    '''
    ph2pi12=2.*np.pi*phase["".join([plane,bn1,bn2])][0]
    ph2pi23=2.*np.pi*phase["".join([plane,bn2,bn3])][0]
      
    # Find the model transfer matrices for beta1
    phmdl12=2.*np.pi*phase["".join([plane,bn1,bn2])][2]
    phmdl23=2.*np.pi*phase["".join([plane,bn2,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl2=MADTwiss.ALFX[MADTwiss.indx[bn2]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl2=MADTwiss.ALFY[MADTwiss.indx[bn2]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta2 and alpha2 from phases assuming model transfer matrix
    # Matrix M: BPM1-> BPM2
    # Matrix N: BPM2-> BPM3
    M22=math.sqrt(betmdl1/betmdl2)*(cos(phmdl12)-alpmdl2*sin(phmdl12))
    M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
    N11=math.sqrt(betmdl3/betmdl2)*(cos(phmdl23)+alpmdl2*sin(phmdl23))
    N12=math.sqrt(betmdl2*betmdl3)*sin(phmdl23)

    denom=M22/M12+N11/N12+1e-16
    numer=1/tan(ph2pi12)+1/tan(ph2pi23)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    denom=M12/M22+N12/N11+1e-16
    numer=M12/M22/tan(ph2pi12)-N12/N11/tan(ph2pi23)
    alf=numer/denom

    alfstd=        (M12/M22*2*np.pi*phase["".join([plane,bn1,bn2])][1]/sin(ph2pi12)**2)**2
    alfstd=alfstd+(N12/N11*2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    alfstd=math.sqrt(alfstd)/abs(denom)

    return bet, betstd, alf, alfstd

def BetaFromPhase_BPM_right(bn1,bn2,bn3,MADTwiss,phase,plane):
    ''' 
    Calculates the beta/alfa function and their errors using the 
    phase advance between three BPMs for the case that the probed BPM is right the other two BPMs
    :Parameters: 
        'bn1':string 
            Name of second BPM left of the probed BPM
        'bn2':string 
            Name of first BPM left of the probed BPM
        'bn3':string 
            Name of probed BPM 
        'MADTwiss':twiss 
            model twiss file 
        'phase':dict
            measured phase advances 
        'plane':string 
            'H' or 'V'
    :Return:tupel (bet,betstd,alf,alfstd) 
        'bet':float 
            calculated beta function at probed BPM
        'betstd':float 
            calculated error on beta function at probed BPM
        'alf':float 
            calculated alfa function at probed BPM
        'alfstd':float 
            calculated error on alfa function at probed BPM
    '''
    ph2pi23=2.*np.pi*phase["".join([plane,bn2,bn3])][0]
    ph2pi13=2.*np.pi*phase["".join([plane,bn1,bn3])][0]
      
    # Find the model transfer matrices for beta1
    phmdl13=2.*np.pi*phase["".join([plane,bn1,bn3])][2]
    phmdl23=2.*np.pi*phase["".join([plane,bn2,bn3])][2]
    if plane=='H':
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETX[MADTwiss.indx[bn3]]
        alpmdl3=MADTwiss.ALFX[MADTwiss.indx[bn3]]
    elif plane=='V':
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        betmdl3=MADTwiss.BETY[MADTwiss.indx[bn3]]
        alpmdl3=MADTwiss.ALFY[MADTwiss.indx[bn3]]
    if betmdl3 < 0 or betmdl2<0 or betmdl1<0:
        print >> sys.stderr, "Some of the off-momentum betas are negative, change the dpp unit"
        sys.exit(1)

    # Find beta3 and alpha3 from phases assuming model transfer matrix
    # Matrix M: BPM2-> BPM3
    # Matrix N: BPM1-> BPM3
    M22=math.sqrt(betmdl2/betmdl3)*(cos(phmdl23)-alpmdl3*sin(phmdl23))
    M12=math.sqrt(betmdl2*betmdl3)*sin(phmdl23)
    N22=math.sqrt(betmdl1/betmdl3)*(cos(phmdl13)-alpmdl3*sin(phmdl13))
    N12=math.sqrt(betmdl1*betmdl3)*sin(phmdl13)

    denom=M22/M12-N22/N12+1e-16
    numer=1/tan(ph2pi23)-1/tan(ph2pi13)
    bet=numer/denom

    betstd=        (2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    betstd=betstd+(2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    betstd=math.sqrt(betstd)/abs(denom)

    denom=M12/M22-N12/N22+1e-16
    numer=M12/M22/tan(ph2pi23)-N12/N22/tan(ph2pi13)
    alf=numer/denom

    alfstd=        (M12/M22*2*np.pi*phase["".join([plane,bn2,bn3])][1]/sin(ph2pi23)**2)**2
    alfstd=alfstd+(N12/N22*2*np.pi*phase["".join([plane,bn1,bn3])][1]/sin(ph2pi13)**2)**2
    alfstd=math.sqrt(alfstd)/abs(denom)


    return bet, betstd, alf, alfstd

def BetaFromPhase(MADTwiss,ListOfFiles,phase,plane):
    ''' 
    Uses 3 BPM left and right of a probed BPM and calculates the beta/alfa from the
    phase advances (15 combinations of 3 BPM stes -> 15 betas).
    The 3 betas with the lowest errors are chosen, and averaged for the final beta.
    :Parameters: 
        'MADTwiss':twiss 
            model twiss file 
        'ListOfFiles':twiss 
            measurement files 
        'phase':dict
            measured phase advances 
        'plane':string 
            'H' or 'V'
    :Return:tupel (beta,rmsbb,alfa,commonbpms) 
        'beta':dict
            calculated beta function for all BPMs
        'rmsbb':float 
            rms beta-beating
        'alfa':dict 
            calculated alfa function for all BPMs
        'commonbpms':dict 
            intersection of common BPMs in measurement files and model
    '''
    alfa={}
    beta={}

    commonbpms = Utilities.bpm.intersect(ListOfFiles)
    commonbpms = Utilities.bpm.modelIntersect(commonbpms,MADTwiss)

    delbeta=[]
    for i in range(0,len(commonbpms)):
        bn1=string.upper(commonbpms[i%len(commonbpms)][1])
        bn2=string.upper(commonbpms[(i+1)%len(commonbpms)][1])
        bn3=string.upper(commonbpms[(i+2)%len(commonbpms)][1])
        bn4=string.upper(commonbpms[(i+3)%len(commonbpms)][1])
        bn5=string.upper(commonbpms[(i+4)%len(commonbpms)][1])
        bn6=string.upper(commonbpms[(i+5)%len(commonbpms)][1])
        bn7=string.upper(commonbpms[(i+6)%len(commonbpms)][1]) 


        candidates = []


        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_right(bn1,bn2,bn4,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_right(bn1,bn3,bn4,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_right(bn2,bn3,bn4,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])


        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn1,bn4,bn5,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn2,bn4,bn5,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn3,bn4,bn5,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn1,bn4,bn6,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn2,bn4,bn6,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn3,bn4,bn6,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn1,bn4,bn7,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn2,bn4,bn7,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_mid(bn3,bn4,bn7,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])

        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_left(bn4,bn5,bn6,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_left(bn4,bn5,bn7,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])
        tbet, tbetstd, talf, talfstd = BetaFromPhase_BPM_left(bn4,bn6,bn7,MADTwiss,phase,plane)
        candidates.append([tbetstd,tbet,talfstd,talf])

        sort_cand = sorted(candidates)

        beti = (sort_cand[0][1] + sort_cand[1][1] + sort_cand[2][1])/3.
        alfi = (sort_cand[0][3] + sort_cand[1][3] + sort_cand[2][3])/3.

        betstd = math.sqrt(sort_cand[0][0]**2 + sort_cand[1][0]**2 + sort_cand[2][0]**2)/math.sqrt(3.)
        alfstd = math.sqrt(sort_cand[0][2]**2 + sort_cand[1][2]**2 + sort_cand[2][2]**2)/math.sqrt(3.)


        try:
            beterr = math.sqrt((sort_cand[0][1]**2 + sort_cand[1][1]**2 + sort_cand[2][1]**2)/3.-beti**2.)
        except:
            beterr=0

        try:
            alferr = math.sqrt((sort_cand[0][3]**2 + sort_cand[1][3]**2 + sort_cand[2][3]**2)/3.-alfi**2.)
        except:
            alferr=0


        beta[bn4]=(beti,beterr,betstd)
        alfa[bn4]=(alfi,alferr,alfstd)
        if plane=='H':
            betmdl1=MADTwiss.BETX[MADTwiss.indx[bn4]]
        elif plane=='V':
            betmdl1=MADTwiss.BETY[MADTwiss.indx[bn4]]
        delbeta.append((beti-betmdl1)/betmdl1)


    delbeta=np.array(delbeta)
    rmsbb=math.sqrt(np.average(delbeta*delbeta))

    return [beta,rmsbb,alfa,commonbpms]



#------------- Beta from amplitude

def BetaFromAmplitude(MADTwiss,ListOfFiles,plane):

    beta={}
    root2J=[]
    commonbpms=Utilities.bpm.intersect(ListOfFiles)
    commonbpms=Utilities.bpm.modelIntersect(commonbpms,MADTwiss)
    SumA=0.0
    Amp=[]
    Amp2=[]
    Kick2=[]
    for i in range(0,len(commonbpms)): # this loop have become complicated after modifications... anybody simplify?
        bn1=string.upper(commonbpms[i][1])
        if plane=='H':
            tembeta=MADTwiss.BETX[MADTwiss.indx[bn1]]
        elif plane=='V':
            tembeta=MADTwiss.BETY[MADTwiss.indx[bn1]]
        Ampi=0.0
        Ampj2=[]
        root2Ji=0.0
        jj=0
        for j in ListOfFiles:
            if i==0:
                Kick2.append(0)
            if plane=='H':
                Ampi+=j.AMPX[j.indx[bn1]]
                Ampj2.append(j.AMPX[j.indx[bn1]]**2)
                root2Ji+=j.PK2PK[j.indx[bn1]]/2.

            elif plane=='V':
                Ampi+=j.AMPY[j.indx[bn1]]
                Ampj2.append(j.AMPY[j.indx[bn1]]**2)
                root2Ji+=j.PK2PK[j.indx[bn1]]/2.
            Kick2[jj]+=Ampj2[jj]/tembeta
            jj+=1
        Ampi=Ampi/len(ListOfFiles)
        root2Ji=root2Ji/len(ListOfFiles)
        Amp.append(Ampi)
        Amp2.append(Ampj2)



        SumA+=Ampi**2/tembeta
        root2J.append(root2Ji/math.sqrt(tembeta))


    Kick=SumA/len(commonbpms) # Assuming the average of beta is constant
    Kick2=np.array(Kick2)
    Kick2=Kick2/len(commonbpms)
    Amp2=np.array(Amp2)
    root2J=np.array(root2J)
    root2Jave=np.average(root2J)
    root2Jrms=math.sqrt(np.average(root2J*root2J)-root2Jave**2+2.2e-16)

    #print Amp2/Kick2


    delbeta=[]
    for i in range(0,len(commonbpms)):
        bn1=string.upper(commonbpms[i][1])
        location=commonbpms[i][0]
        for j in range(0,len(ListOfFiles)):
            Amp2[i][j]=Amp2[i][j]/Kick2[j]
        #print np.average(Amp2[i]*Amp2[i]),np.average(Amp2[i])**2
        try:
            betstd=math.sqrt(np.average(Amp2[i]*Amp2[i])-np.average(Amp2[i])**2+2.2e-16)
        except:
            betstd=0

        beta[bn1]=[Amp[i]**2/Kick,betstd,location]
        if plane=='H':
            betmdl=MADTwiss.BETX[MADTwiss.indx[bn1]]
        elif plane=='V':
            betmdl=MADTwiss.BETY[MADTwiss.indx[bn1]]
        delbeta.append((beta[bn1][0]-betmdl)/betmdl)

    invariantJ=[root2Jave,root2Jrms]

    delbeta=np.array(delbeta)
    rmsbb=math.sqrt(np.average(delbeta*delbeta))
    return [beta,rmsbb,commonbpms,invariantJ]

#-------------------------

def GetCO(MADTwiss, ListOfFiles):

    commonbpms=Utilities.bpm.intersect(ListOfFiles)
    commonbpms=Utilities.bpm.modelIntersect(commonbpms, MADTwiss)
    co={} # Disctionary for output
    for i in range(0,len(commonbpms)):
        bn1=string.upper(commonbpms[i][1])
        coi=0.0
        coi2=0.0
        for j in ListOfFiles:
            coi=coi + j.CO[j.indx[bn1]]
            coi2=coi2 + j.CO[j.indx[bn1]]**2
        coi=coi/len(ListOfFiles)
        corms=math.sqrt(coi2/len(ListOfFiles)-coi**2+2.2e-16)
        co[bn1]=[coi,corms]
    return [co, commonbpms]


def NormDispX(MADTwiss, ListOfZeroDPPX, ListOfNonZeroDPPX, ListOfCOX, betax, COcut):

    nzdpp=len(ListOfNonZeroDPPX) # How many non zero dpp
    zdpp=len(ListOfZeroDPPX)  # How many zero dpp
    if zdpp==0 or nzdpp ==0:
        print 'Warning: No data for dp/p!=0 or even for dp/p=0.'
        print 'No output for the  dispersion.'
        dum0={}
        dum1=[]
        return [dum0, dum1]


    coac=ListOfCOX[0] # COX dictionary after cut bad BPMs
    coact={}
    for i in coac:
        if (coac[i][1] < COcut):
            coact[i]=coac[i]
    coac=coact


    nda={} # Dictionary for the output containing [average Disp, rms error]

    ALL=ListOfZeroDPPX+ListOfNonZeroDPPX
    commonbpmsALL=Utilities.bpm.intersect(ALL)
    commonbpmsALL=Utilities.bpm.modelIntersect(commonbpmsALL, MADTwiss)

    mydp=[]
    gf=[]
    for j in ListOfNonZeroDPPX:
        mydp.append(float(j.DPP))
        gf.append(0.0) # just to initialize the array, may not be a clever way...
    mydp=np.array(mydp)
    wf=np.array(abs(mydp))/sum(abs(mydp))*len(mydp) #Weight for the average depending on DPP


    # Find the global factor
    nd=[]
    ndmdl=[]
    badco=0
    for i in range(0,len(commonbpmsALL)):
        bn1=string.upper(commonbpmsALL[i][1])
        bns1=commonbpmsALL[i][0]
        ndmdli=MADTwiss.DX[MADTwiss.indx[bn1]]/math.sqrt(MADTwiss.BETX[MADTwiss.indx[bn1]])
        ndmdl.append(ndmdli)

        try:
            coi=coac[bn1]

            ampi=0.0
            for j in ListOfZeroDPPX:
                ampi+=j.AMPX[j.indx[bn1]]
            ampi=ampi/zdpp

            ndi=[]
            for j in range(0,nzdpp): # the range(0,nzdpp) instead of ListOfNonZeroDPPX is used because the index j is used in the loop
                codpp=ListOfCOX[j+1]
                orbit=codpp[bn1][0]-coi[0]
                ndm=orbit/ampi
                gf[j]+=ndm
                ndi.append(ndm)
            nd.append(ndi)
        except:
            badco+=1
            coi=0

    ndmdl=np.array(ndmdl)
    avemdl=np.average(ndmdl)

    gf=np.array(gf)
    gf=gf/avemdl/(len(commonbpmsALL)-badco)


    # Find normalized dispersion and Dx construction
    nd=np.array(nd)
    Dx={}
    dummy=0.0 # dummy for DXSTD
    bpms=[]
    badco=0
    for i in range(0,len(commonbpmsALL)):
        ndi=[]
        bn1=string.upper(commonbpmsALL[i][1])
        bns1=commonbpmsALL[i][0]
        try:
            coac[bn1]
            for j in range(0,nzdpp): # the range(0,nzdpp) instead of ListOfZeroDPPX is used because the index j is used in the loop
                ndi.append(nd[i-badco][j]/gf[j])
            ndi=np.array(ndi)
            ndstd=math.sqrt(np.average(ndi*ndi)-(np.average(ndi))**2.0+2.2e-16)
            ndas=np.average(wf*ndi)
            nda[bn1]=[ndas,ndstd]
            Dx[bn1]=[nda[bn1][0]*math.sqrt(betax[bn1][0]),dummy]
            bpms.append([bns1,bn1])
        except:
            badco+=1
    DPX=GetDPX(MADTwiss, Dx, bpms)

    return [nda,Dx,DPX,bpms]


#---------- DPX, New!
def GetDPX(MADTwiss,Dx,commonbpms):

    DPX={}
    for i in range(0,len(commonbpms)):
        bn1=string.upper(commonbpms[i][1])
        if i==len(commonbpms)-1: # The first BPM is BPM2 for the last BPM
            bn2=string.upper(commonbpms[0][1])
            phmdl12=2.*np.pi*(MADTwiss.Q1+MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[bn1]])
        else:
            bn2=string.upper(commonbpms[i+1][1])
            phmdl12=2.*np.pi*(MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[bn1]])
        betmdl1=MADTwiss.BETX[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETX[MADTwiss.indx[bn2]]
        alpmdl1=MADTwiss.ALFX[MADTwiss.indx[bn1]]
        dxmdl1=MADTwiss.DX[MADTwiss.indx[bn1]]
        dpxmdl1=MADTwiss.DPX[MADTwiss.indx[bn1]]
        dxmdl2=MADTwiss.DX[MADTwiss.indx[bn2]]

        M11=math.sqrt(betmdl2/betmdl1)*(cos(phmdl12)+alpmdl1*sin(phmdl12))
        M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
        M13=dxmdl2-M11*dxmdl1-M12*dpxmdl1
        # use the beta from amplitude
        DPX[bn1]=(-M13+Dx[bn2][0]-M11*Dx[bn1][0])/M12

    return DPX



#----------- DPY, New!
def GetDPY(MADTwiss,Dy,commonbpms):
    DPY={}
    for i in range(0,len(commonbpms)):
        bn1=string.upper(commonbpms[i][1])
        if i==len(commonbpms)-1: # The first BPM is BPM2 for the last BPM
            bn2=string.upper(commonbpms[0][1])
            phmdl12=2.*np.pi*(MADTwiss.Q2+MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[bn1]])
        else:
            bn2=string.upper(commonbpms[i+1][1])
            phmdl12=2.*np.pi*(MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[bn1]])
        betmdl1=MADTwiss.BETY[MADTwiss.indx[bn1]]
        betmdl2=MADTwiss.BETY[MADTwiss.indx[bn2]]
        alpmdl1=MADTwiss.ALFY[MADTwiss.indx[bn1]]
        dymdl1=MADTwiss.DY[MADTwiss.indx[bn1]]
        dpymdl1=MADTwiss.DPY[MADTwiss.indx[bn1]]
        dymdl2=MADTwiss.DY[MADTwiss.indx[bn2]]

        M11=math.sqrt(betmdl2/betmdl1)*(cos(phmdl12)+alpmdl1*sin(phmdl12))
        M12=math.sqrt(betmdl1*betmdl2)*sin(phmdl12)
        M13=dymdl2-M11*dymdl1-M12*dpymdl1
        #M13=-M11*dymdl1-M12*dpymdl1
        # use the beta from amplitude
        DPY[bn1]=(-M13+Dy[bn2][0]-M11*Dy[bn1][0])/M12
        #DPY[bn1]=(-M13-M11*Dy[bn1][0])/M12

    return DPY


def DispersionfromOrbit(ListOfZeroDPP,ListOfNonZeroDPP,ListOfCO,COcut,BPMU):

    if BPMU=='um': scalef=1.0e-6
    elif BPMU=='mm': scalef=1.0e-3
    elif BPMU=='cm': scalef=1.0e-2
    elif BPMU=='m': scalef=1.0


    coac=ListOfCO[0]
    coact={}
    for i in coac:
        if (coac[i][1] < COcut):
            coact[i]=coac[i]

    coac=coact # COY dictionary after cut bad BPMs

    ALL=ListOfZeroDPP+ListOfNonZeroDPP
    commonbpmsALL=Utilities.bpm.intersect(ALL)



    mydp=[]
    for j in ListOfNonZeroDPP:
        mydp.append(float(j.DPP))
    mydp=np.array(mydp)
    wf=np.array(abs(mydp))/sum(abs(mydp))*len(mydp) #Weitghs for the average


    dco={} # Dictionary for the output containing [(averaged)Disp, rms error]
    bpms=[]
    for i in range(0,len(commonbpmsALL)):
        bn1=string.upper(commonbpmsALL[i][1])
        bns1=commonbpmsALL[i][0]

        try:
            coi=coac[bn1]
            dcoi=[]
            for j in ListOfNonZeroDPP:
                dcoi.append((j.CO[j.indx[bn1]]-coi[0])*scalef/float(j.DPP))
            dcoi=np.array(dcoi)
            dcostd=math.sqrt(np.average(dcoi*dcoi)-(np.average(dcoi))**2.0+2.2e-16)
            dcos=np.average(wf*dcoi)
            dco[bn1]=[dcos,dcostd]
            bpms.append([bns1,bn1])
        except:
            coi=0
    return [dco,bpms]


#-----------

def GetCoupling1(MADTwiss, ListOfZeroDPPX, ListOfZeroDPPY, Q1, Q2):

    # not applicable to db=-1 for the time being...

    tp=2.0*np.pi

    # find operation point
    try:
        #TODO: There is no global outputpath. Will always crash. See Github issue #9 (vimaier)
        fdi=open(outputpath+'Drive.inp','r')  # Drive.inp file is normally in the outputpath directory in GUI operation
        for line in fdi:
            if "TUNE X" in line:
                fracxinp = line.split("=")
                fracx = fracxinp[1]
            if "TUNE Y" in line:
                fracyinp = line.split("=")
                fracy = fracyinp[1]
        fdi.close()
    except:
        fracx = Q1 # Otherwise, the fractional parts are assumed to be below 0.5
        fracy = Q2

    if fracx < 0.0 :
        fracx = 1.0 - Q1
    else:
        fracx = Q1
    if fracy < 0.0 :
        fracx = 1.0 - Q2
    else:
        fracy=Q2

    if fracx > fracy:
        sign_QxmQy = 1.0
    else:
        sign_QxmQy = -1.0

    # check linx/liny files, if it's OK it is confirmed that ListofZeroDPPX[i] and ListofZeroDPPY[i]
    # come from the same (simultaneous) measurement.
    if len(ListOfZeroDPPX)!=len(ListOfZeroDPPY):
        print 'Leaving GetCoupling as linx and liny files seem not correctly paired...'
        dum0={}
        dum1=[]
        return [dum0,dum1]


    XplusY=ListOfZeroDPPX+ListOfZeroDPPY
    dbpms=Utilities.bpm.intersect(XplusY)
    dbpms=Utilities.bpm.modelIntersect(dbpms, MADTwiss)


    # caculate fw and qw, exclude bpms having wrong phases

    fwqw={}
    dbpmt=[]
    countBadPhase=0
    for i in range(0,len(dbpms)):
        bn1=string.upper(dbpms[i][1])

        fij=[]
        q1j=[]
        q2j=[]
        badbpm=0
        for j in range(0,len(ListOfZeroDPPX)):
            jx=ListOfZeroDPPX[j]
            jy=ListOfZeroDPPY[j]
            C01ij=jx.AMP01[jx.indx[bn1]]
            C10ij=jy.AMP10[jy.indx[bn1]]
            fij.append(0.5*math.atan(math.sqrt(C01ij*C10ij)))

            #q1=(jx.MUX[jx.indx[bn1]]-jy.PHASE10[jy.indx[bn1]]+0.25)%1.0 # note that phases are in units of 2pi
            #q2=(jx.PHASE01[jx.indx[bn1]]-jy.MUY[jy.indx[bn1]]-0.25)%1.0
            #q1=(0.5-q1)%1.0 # This sign change in the real part is to comply with MAD output
            #q2=(0.5-q2)%1.0
            q1j.append((jx.MUX[jx.indx[bn1]]-jy.PHASE10[jy.indx[bn1]]+0.25)%1.0) # note that phases are in units of 2pi
            q2j.append((jx.PHASE01[jx.indx[bn1]]-jy.MUY[jy.indx[bn1]]-0.25)%1.0)
            q1j[j]=(0.5-q1j[j])%1.0 # This sign change in the real part is to comply with MAD output
            q2j[j]=(0.5-q2j[j])%1.0

            #if abs(q1-q2)<0.25:
            #       qij.append((q1+q2)/2.0)
            #elif abs(q1-q2)>0.75: # OK, for example q1=0.05, q2=0.95 due to measurement error
            #       qij.append(q1) # Note that q1 and q2 are confined 0. to 1.
            #else:
            #       badbpm=1
            #       countBadPhase += 1
            #       #print "Bad Phases in BPM ",bn1, "total so far", countBadPhase
        q1j=np.array(q1j)
        q2j=np.array(q2j)
        q1=np.average(q1j)
        q2=np.average(q2j)

        if abs(q1-q2)<0.25:  # Very rough cut !!!!!!!!!!!!!!!!!!!
            qi=(q1+q2)/2.0
        elif abs(q1-q2)>0.75: # OK, for example q1=0.05, q2=0.95 due to measurement error
            qi=q1 # Note that q1 and q2 are confined 0. to 1.
        else:
            badbpm=1
            countBadPhase += 1
            #print "Bad Phases in BPM ",bn1, "total so far", countBadPhase



        if badbpm==0:
            fij=np.array(fij)
            fi=np.average(fij)
            fistd=math.sqrt(np.average(fij*fij)-(np.average(fij))**2.0+2.2e-16)
            #qij=np.array(qij)
            #qi=np.average(qij)
            #qistd=math.sqrt(np.average(qij*qij)-(np.average(qij))**2.0+2.2e-16)
            qistd=math.sqrt(np.average(q1j*q1j)-(np.average(q1j))**2.0+2.2e-16) # Not very exact...
            fi=fi*complex(cos(tp*qi),sin(tp*qi))
            dbpmt.append([dbpms[i][0],dbpms[i][1]])
            # Trailing "0,0" in following lists because of compatibility. 
            # See issue on github pylhc/Beta-Beat.src#3
            # --vimaier
            fwqw[bn1]=[[fi,fistd,0,0],[qi,qistd,0,0]]


    dbpms=dbpmt


    # compute global values
    CG=0.0
    QG=0.0
    for i in range(0,len(dbpms)):
        jx=ListOfZeroDPPX[j]
        jy=ListOfZeroDPPY[j]
        bn1=string.upper(dbpms[i][1])
        CG=CG+math.sqrt(fwqw[bn1][0][0].real**2+fwqw[bn1][0][0].imag**2)
        QG=QG+fwqw[bn1][1][0]-(jx.MUX[jx.indx[bn1]]-jy.MUY[jy.indx[bn1]])


    CG=abs(4.0*(Q1-Q2)*CG/len(dbpms))
    QG=(QG/len(dbpms)+0.5*(1.0-sign_QxmQy*0.5))%1.0
    fwqw['Global']=[CG,QG]


    return [fwqw,dbpms]

#-----------

def ComplexSecondaryLine(delta, cw, cw1, pw, pw1):
    tp=2.0*np.pi
    a1=complex(1.0,-tan(tp*delta))
    a2=cw*complex(cos(tp*pw),sin(tp*pw))
    a3=-1.0/cos(tp*delta)*complex(0.0,1.0)
    a4=cw1*complex(cos(tp*pw1),sin(tp*pw1))
    SL=a1*a2+a3*a4
    sizeSL=math.sqrt(SL.real**2+SL.imag**2)
    phiSL=(np.arctan2(SL.imag , SL.real)/tp) %1.0
    #SL=complex(-SL.real,SL.imag)    # This sign change in the real part is to comply with MAD output
    return [sizeSL,phiSL]


def ComplexSecondaryLineExtended(delta,edelta, amp1,amp2, phase1,phase2):
    '''
     Input : - delta: phase advance between two BPMs
             - edelta: error on the phase advance between two BPMs
             - amp1: amplitude of secondary line at ith BPM
             - amp2: amplitude of secondary line at i+1th BPM
             - phase1: phase of secondary line at ith BPM
             - phase2: phase of secondary line at i+1th BPM
     Return: - amp: amplitude of the complex signal
             - phase: phase of the complex signal
             - eamp: error on amplitude of the complex signal
             - ephase: error on phase of the complex signal
    '''


    # functions
    tp=2.0*np.pi
    C=cos(delta*tp)
    T=tan(delta*tp)
    SC=sin(delta*tp)/((cos(delta*tp*2)+1)/2)

    # signal
    cs1=cos(tp*phase1)
    ss1=sin(tp*phase1)
    cs2=cos(tp*phase2)
    ss2=sin(tp*phase2)

    sig1=amp1*complex(cs1,ss1)
    sig2=amp2*complex(cs2,ss2)

    # computing complex secondary line (h-)
    sig=sig1*complex(1,-T)-sig2*complex(0,1)*(1/C)

    amp=abs(sig)
    phase=(np.arctan2(sig.imag,sig.real)/tp) %1.0

    # computing error secondary line (h-)
    esig=(sig1*complex(1,-(1/C))-sig2*complex(0,1)*(SC))*edelta

    eamp=abs(esig)
    ephase=(np.arctan2(esig.imag,esig.real)/tp) %1.0

    return [amp,phase,eamp,ephase]


def GetCoupling2(MADTwiss, ListOfZeroDPPX, ListOfZeroDPPY, Q1, Q2, phasex, phasey, bd, oa):

    # find operation point
    try:
        fdi=open(outputpath+'Drive.inp','r')  # Drive.inp file is normally in the outputpath directory in GUI operation
        for line in fdi:
            if "TUNE X" in line:
                fracxinp=line.split("=")
                fracx=fracxinp[1]
            if "TUNE Y" in line:
                fracyinp=line.split("=")
                fracy=fracyinp[1]
        fdi.close()
    except:
        fracx=Q1 # Otherwise, the fractional parts are assumed to be below 0.5
        fracy=Q2

    if fracx<0.0 :
        fracx=1.0-Q1
    else:
        fracx=Q1

    if fracy<0.0 :
        fracx=1.0-Q2
    else:
        fracy=Q2

    if fracx>fracy:
        sign_QxmQy=1.0
    else:
        sign_QxmQy=-1.0

    # check linx/liny files, if it's OK it is confirmed that ListofZeroDPPX[i] and ListofZeroDPPY[i]
    # come from the same (simultaneous) measurement. It might be redundant check.
    if len(ListOfZeroDPPX)!=len(ListOfZeroDPPY):
        print 'Leaving GetCoupling as linx and liny files seem not correctly paired...'
        dum0={}
        dum1=[]
        return [dum0,dum1]


    XplusY=ListOfZeroDPPX+ListOfZeroDPPY
    dbpms=Utilities.bpm.intersect(XplusY)
    dbpms=Utilities.bpm.modelIntersect(dbpms, MADTwiss)

    # caculate fw and qw, exclude bpms having wrong phases

    tp=2.0*np.pi
    fwqw={}
    dbpmt=[]
    countBadPhase=0
    for i in range(0,len(dbpms)-1):
        bn1=string.upper(dbpms[i][1])
        bn2=string.upper(dbpms[i+1][1])

        delx= phasex[bn1][0] - 0.25  # Missprint in the coupling note
        dely= phasey[bn1][0] - 0.25

        f1001ij=[]
        #q1001ij=[]
        f1010ij=[]
        #q1010ij=[]
        q1js=[]
        q2js=[]
        q1jd=[]
        q2jd=[]
        badbpm=0
        for j in range(0,len(ListOfZeroDPPX)):
            jx=ListOfZeroDPPX[j]
            jy=ListOfZeroDPPY[j]
            [SA0p1ij,phi0p1ij]=ComplexSecondaryLine(delx, jx.AMP01[jx.indx[bn1]], jx.AMP01[jx.indx[bn2]],
                    jx.PHASE01[jx.indx[bn1]], jx.PHASE01[jx.indx[bn2]])
            [SA0m1ij,phi0m1ij]=ComplexSecondaryLine(delx, jx.AMP01[jx.indx[bn1]], jx.AMP01[jx.indx[bn2]],
                    -jx.PHASE01[jx.indx[bn1]], -jx.PHASE01[jx.indx[bn2]])
            [TBp10ij,phip10ij]=ComplexSecondaryLine(dely, jy.AMP10[jy.indx[bn1]], jy.AMP10[jy.indx[bn2]],
                    jy.PHASE10[jy.indx[bn1]], jy.PHASE10[jy.indx[bn2]])
            [TBm10ij,phim10ij]=ComplexSecondaryLine(dely, jy.AMP10[jy.indx[bn1]], jy.AMP10[jy.indx[bn2]],
                    -jy.PHASE10[jy.indx[bn1]], -jy.PHASE10[jy.indx[bn2]])


            #print SA0p1ij,phi0p1ij,SA0m1ij,phi0m1ij,TBp10ij,phip10ij,TBm10ij,phim10ij
            f1001ij.append(0.5*math.sqrt(TBp10ij*SA0p1ij/2.0/2.0))
            f1010ij.append(0.5*math.sqrt(TBm10ij*SA0m1ij/2.0/2.0))

            if bd==1:
                q1jd.append((phi0p1ij-jy.MUY[jy.indx[bn1]]+0.25)%1.0) # note that phases are in units of 2pi
                q2jd.append((-phip10ij+jx.MUX[jx.indx[bn1]]-0.25)%1.0)
            elif bd==-1:
                q1jd.append((phi0p1ij-jy.MUY[jy.indx[bn1]]+0.25)%1.0) # note that phases are in units of 2pi
                q2jd.append(-(-phip10ij+jx.MUX[jx.indx[bn1]]-0.25)%1.0)
            #print q1,q2
            q1jd[j]=(0.5-q1jd[j])%1.0 # This sign change in the real part is to comply with MAD output
            q2jd[j]=(0.5-q2jd[j])%1.0


            #if abs(q1-q2)<0.25:
                #q1001ij.append((q1+q2)/2.0)
            #elif abs(q1-q2)>0.75: # OK, for example q1=0.05, q2=0.95 due to measurement error
                #q1001ij.append(q1) # Note that q1 and q2 are confined 0. to 1.
            #else:
                #badbpm=1
                #q1001ij.append(q1)
                #countBadPhase += 1
                #print "Bad Phases in BPM ",bn1,bn2, "total so far", countBadPhase

            if bd==1:
                q1js.append((phi0m1ij+jy.MUY[jy.indx[bn1]]+0.25)%1.0) # note that phases are in units of 2pi
                q2js.append((phim10ij+jx.MUX[jx.indx[bn1]]+0.25)%1.0)
            if bd==-1:
                q1js.append((phi0m1ij+jy.MUY[jy.indx[bn1]]+0.25)%1.0) # note that phases are in units of 2pi
                q2js.append(-(phim10ij+jx.MUX[jx.indx[bn1]]+0.25)%1.0)
            #print q1,q2
            q1js[j]=(0.5-q1js[j])%1.0 # This sign change in the real part is to comply with MAD output
            q2js[j]=(0.5-q2js[j])%1.0

            #if abs(q1-q2)<0.25:
                #q1010ij.append((q1+q2)/2.0)
            #elif abs(q1-q2)>0.75: # OK, for example q1=0.05, q2=0.95 due to measurement error
                #q1010ij.append(q1) # Note that q1 and q2 are confined 0. to 1.
            #else:
                #badbpm=1
                #if (oa=="SPS" or oa=="RHIC"):
                #       badbpm=0
                #q1010ij.append(q1)
                #countBadPhase += 1
                #print "Bad Phases in BPM ",bn1,bn2, "total so far", countBadPhase

        q1jd=np.array(q1jd)
        q2jd=np.array(q2jd)
        q1d=PhaseMean(q1jd,1.0)
        q2d=PhaseMean(q2jd,1.0)

        q1js=np.array(q1js)
        q2js=np.array(q2js)
        q1s=PhaseMean(q1js,1.0)
        q2s=PhaseMean(q2js,1.0)

        if min(abs(q1d-q2d),1.0-abs(q1d-q2d))>0.25 or min(abs(q1s-q2s),1.0-abs(q1s-q2s))>0.25:
            badbpm=1
            countBadPhase += 1

        if (oa=="SPS" or oa=="RHIC"):
            # No check for the SPS or RHIC
            badbpm=0
            q1010i=q1d
            q1010i=q1s
            countBadPhase += 1
            #print "Bad Phases in BPM ",bn1,bn2, "total so far", countBadPhase

        if badbpm==0:

            f1001ij=np.array(f1001ij)
            f1001i=np.average(f1001ij)
            f1001istd=math.sqrt(np.average(f1001ij*f1001ij)-(np.average(f1001ij))**2.0+2.2e-16)
            f1010ij=np.array(f1010ij)
            f1010i=np.average(f1010ij)
            f1010istd=math.sqrt(np.average(f1010ij*f1010ij)-(np.average(f1010ij))**2.0+2.2e-16)

            q1001i=PhaseMean(np.array([q1d,q2d]),1.0)
            q1010i=PhaseMean(np.array([q1s,q2s]),1.0)
            q1001istd=PhaseStd(np.append(q1jd,q2jd),1.0)
            q1010istd=PhaseStd(np.append(q1js,q2js),1.0)

            f1001i=f1001i*complex(cos(tp*q1001i),sin(tp*q1001i))
            f1010i=f1010i*complex(cos(tp*q1010i),sin(tp*q1010i))
            dbpmt.append([dbpms[i][0],dbpms[i][1]])

            if bd==1:
                fwqw[bn1]=[[f1001i,f1001istd,f1010i,f1010istd],[q1001i,q1001istd,q1010i,q1010istd]]
            elif bd==-1:
                fwqw[bn1]=[[f1010i,f1010istd,f1001i,f1001istd],[q1010i,q1010istd,q1001i,q1001istd]]


    dbpms=dbpmt

    # possible correction ??
    #bn0=string.upper(dbpms[0][1])
    #up1=fwqw[bn0][0][0]
    #up2=fwqw[bn0][0][2]
    #for i in range(1,len(dbpms)):
        #bn0=string.upper(dbpms[i-1][1])
        #bn1=string.upper(dbpms[i][1])
        #df1001=math.sqrt(fwqw[bn0][0][0].real**2+fwqw[bn0][0][0].imag**2)/math.sqrt(fwqw[bn1][0][0].real**2+fwqw[bn1][0][0].imag**2)
        #df1010=math.sqrt(fwqw[bn0][0][2].real**2+fwqw[bn0][0][2].imag**2)/math.sqrt(fwqw[bn1][0][2].real**2+fwqw[bn1][0][2].imag**2)
        #fwqw[bn0][0][0]=up1
        #fwqw[bn0][0][2]=up2
        #up1=complex(df1001*fwqw[bn1][0][0].real,fwqw[bn1][0][0].imag)
        #up2=complex(df1010*fwqw[bn1][0][2].real,fwqw[bn1][0][2].imag)

    #fwqw[bn1][0][0]=up1
    #fwqw[bn1][0][2]=up2
    # end of possible correction

    # compute global values
    CG=0.0
    QG=0.0
    for i in range(0,len(dbpms)-1):
        jx=ListOfZeroDPPX[0]
        jy=ListOfZeroDPPY[0]
        bn1=string.upper(dbpms[i][1])
        CG=CG+math.sqrt(fwqw[bn1][0][0].real**2+fwqw[bn1][0][0].imag**2)
        QG=QG+fwqw[bn1][1][0]-(jx.MUX[jx.indx[bn1]]-jy.MUY[jy.indx[bn1]])

    if len(dbpms)==0:
        print 'Warning: There is no BPM to output linear coupling properly... leaving Getcoupling.'
        fwqw['Global']=[CG,QG] #Quick fix Evian 2012
        return [fwqw,dbpms]
    else:
        CG=abs(4.0*(Q1-Q2)*CG/len(dbpms))
        QG=(QG/len(dbpms)+0.5*(1.0-sign_QxmQy*0.5))%1.0
    fwqw['Global']=[CG,QG]

    return [fwqw,dbpms]

#---------------------------
def PseudoDoublePlaneMonitors(MADTwiss, ListOfZeroDPPX, ListOfZeroDPPY, BPMdictionary):



    # check linx/liny files, if it's OK it is confirmed that ListofZeroDPPX[i] and ListofZeroDPPY[i]
    # come from the same (simultaneous) measurement. It might be redundant check.
    if len(ListOfZeroDPPX)!=len(ListOfZeroDPPY):
        print 'Leaving PseudoDoublePlaneMonitors as linx and liny files seem not correctly paired...'
        dum0={}
        dum1=[]
        return [dum0,dum1]

    bpmh=Utilities.bpm.intersect(ListOfZeroDPPX)
    bpmv=Utilities.bpm.intersect(ListOfZeroDPPY)
    bpmh=Utilities.bpm.modelIntersect(bpmh, MADTwiss)
    bpmv=Utilities.bpm.modelIntersect(bpmv, MADTwiss)


    fbpmx=[]
    fbpmy=[]
    for i in range(0,len(ListOfZeroDPPX)):
        filex='temp'+str(i)+'_linx'
        filey='temp'+str(i)+'_liny'
        fbpmxi=open(filex,'w')
        fbpmyi=open(filey,'w')
        fbpmx.append(fbpmxi)
        fbpmy.append(fbpmyi)
        fbpmx[i].write('* NAME   S      TUNEX  MUX    AMPX   AMP01  PHASE01\n')
        fbpmy[i].write('* NAME   S      TUNEY  MUY    AMPY   AMP10  PHASE10\n')
        fbpmx[i].write('$ %s     %le    %le    %le    %le    %le    %le\n')
        fbpmy[i].write('$ %s     %le    %le    %le    %le    %le    %le\n')

        # bpmhp will be used for storing in this section. Not used further. Replaced by 
        # 'tentative solution' with bpmpair. See some lines below.
        # --vimaier
#     bpmhp=[]
#     for i in range(0,len(bpmh)):
#         smin=1.0e10
#         jsave=0
#         for j in range (0,len(bpmv),10):
#             sdiff=abs(bpmh[i][0]-bpmv[j][0])
#             if sdiff<smin:
#                 smin=sdiff
#                 jsave=j

#         jlower=jsave-9
#         jupper=jsave+9
#         if jupper > len(bpmv):
#             jupper=len(bpmv)
#         for j in range (jlower,jupper):
#             sdiff=abs(bpmh[i][0]-bpmv[j][0])
#             if sdiff<smin:
#                 smin=sdiff
#                 jsave=j
# 
#         bpmhp.append([bpmh[i][0],bpmh[i][1],bpmv[jsave][1],0])


    #bpmvp=[]
    #for i in range(0,len(bpmv)):
        #smin=1.0e10
        #jsave=0
        #for j in range (0,len(bpmh),10):
            #sdiff=abs(bpmv[i][0]-bpmh[j][0])
            #if sdiff<smin:
                #smin=sdiff
                #jsave=j
        #jlower=jsave-9
        #jupper=jsave+9
        #if jupper > len(bpmh):
            #jupper=len(bpmh)
        #for j in range (jlower,jupper):
            #sdiff=abs(bpmv[i][0]-bpmh[j][0])
            #if sdiff<smin:
                #smin=sdiff
                #jsave=j

        #bpmvp.append([bpmv[i][0],bpmv[i][1],bpmh[jsave][1],1])


    #dbpms=combinebpms(bpmhp,bpmvp)
    # dbpms is replaced through 'tentative solution' (vimaier)
#     dbpms=bpmhp

    # tentative solution
    dbpms=bpmpair() # model BPM name
    countofmissingBPMs=0
    for i in range(0,len(dbpms)):
        wname=string.upper(dbpms[i][1]) # horizontal BPM basis of the pairing (model name)
        pname=string.upper(dbpms[i][2]) # vertical pair of the horizontal as in SPSBPMpairs (model name)
        #print wname
        ws=dbpms[i][0]  # Location
        #print "name ",wname, pname
        #Check whether the inputs (linx/y) have BPM name of model or experiment
        try:
            exwname=BPMdictionary[wname][0] #Experimental BPM name of horizontal To be paired
            #print exwname

            expname=BPMdictionary[pname][1] #Experimental BPM name of vertical  (one of them does not exist!) to be paired

            #print expname

        except:
            if len(BPMdictionary)!=0:
                countofmissingBPMs = countofmissingBPMs + 1
                print wname, "or", pname, "not found in the BPMdictionary. Total so far = ",countofmissingBPMs
        try:
            for j in range(0,len(ListOfZeroDPPX)):
                jx=ListOfZeroDPPX[j]
                jy=ListOfZeroDPPY[j]
                #if dbpms[i][3]==0:
                # dphix is used only in commented out code beneath (vimaier)
#                 dphix=MADTwiss.MUX[MADTwiss.indx[string.upper(pname)]]-MADTwiss.MUX[MADTwiss.indx[string.upper(wname)]]
                dphiy=MADTwiss.MUY[MADTwiss.indx[string.upper(pname)]]-MADTwiss.MUY[MADTwiss.indx[string.upper(wname)]]
                # Going to try using model names, to be able to use simulation data
                try:
                    wampx=jx.AMPX[jx.indx[wname]]
                    wampy=jy.AMPY[jy.indx[pname]]
                    wamp01=jx.AMP01[jx.indx[wname]]
                    wamp10=jy.AMP10[jy.indx[pname]]
                    wtunex=jx.TUNEX[jx.indx[wname]]
                    wtuney=jy.TUNEY[jy.indx[pname]]
                    wmux=jx.MUX[jx.indx[wname]]
                    wmuy=(jy.MUY[jy.indx[pname]]-dphiy)%1.0
                    if (wmuy > 0.5): wmuy=wmuy-1.0
                    wphase01=jx.PHASE01[jx.indx[wname]]
                    wphase10=(jy.PHASE10[jy.indx[pname]]-dphiy)%1.0
                    if (wphase10 > 0.5): wphase10=wphase10-1.0
                # This seems to be experiment data, going to try with experimental names
                except:
                    wampx=jx.AMPX[jx.indx[exwname]]
                    wampy=jy.AMPY[jy.indx[expname]]
                    wamp01=jx.AMP01[jx.indx[exwname]]
                    wamp10=jy.AMP10[jy.indx[expname]]
                    wtunex=jx.TUNEX[jx.indx[exwname]]
                    wtuney=jy.TUNEY[jy.indx[expname]]
                    wmux=jx.MUX[jx.indx[exwname]]
                    wmuy=(jy.MUY[jy.indx[expname]]-dphiy)%1.0
                    if (wmuy > 0.5): wmuy=wmuy-1.0
                    wphase01=jx.PHASE01[jx.indx[exwname]]
                    wphase10=(jy.PHASE10[jy.indx[expname]]-dphiy)%1.0
                    if (wphase10 > 0.5): wphase10=wphase10-1.0
                #elif dbpms[i][3]==1:
                    #wampx=jx.AMPX[jx.indx[pname]]
                    #wampy=jy.AMPY[jy.indx[wname]]
                    #wamp01=jx.AMP01[jx.indx[pname]]
                    #wamp10=jy.AMP10[jy.indx[wname]]
                    #wtunex=jx.TUNEX[jx.indx[pname]]
                    #wtuney=jy.TUNEY[jy.indx[wname]]
                    #dphix=MADTwiss.MUX[MADTwiss.indx[string.upper(pname)]]-MADTwiss.MUX[MADTwiss.indx[string.upper(wname)]]
                    #dphiy=MADTwiss.MUY[MADTwiss.indx[string.upper(pname)]]-MADTwiss.MUY[MADTwiss.indx[string.upper(wname)]]
                    #wmux=(jx.MUX[jx.indx[pname]]-dphix)%1.0
                    #if (wmux > 0.5): wmux=wmux-1
                    #wmuy=jy.MUY[jy.indx[wname]]
                    #wphase01=(jx.PHASE01[jx.indx[pname]]-dphix)%1.0
                    #wphase10=jy.PHASE10[jy.indx[wname]]
                    #if (wphase01 > 0.5): wphase01=wphase01-1
                #elif dbpms[i][3]==2:
                    #wampx=jx.AMPX[jx.indx[wname]]
                    #wampy=jy.AMPY[jy.indx[wname]]
                    #wamp01=jx.AMP01[jx.indx[wname]]
                    #wamp10=jy.AMP10[jy.indx[wname]]
                    #wtunex=jx.TUNEX[jx.indx[wname]]
                    #wtuney=jy.TUNEY[jy.indx[wname]]
                    #wmux=jx.MUX[jx.indx[wname]]
                    #wmuy=jy.MUY[jy.indx[wname]]
                    #wphase01=jx.PHASE01[jx.indx[wname]]
                    #wphase10=jy.PHASE10[jy.indx[wname]]
                fbpmx[j].write('"'+wname+'" '+str(ws)+' '+str(wtunex)+' '+str(wmux)+' '+str(wampx)+' '+str(wamp01)+' '+str(wphase01)+'\n')
                fbpmy[j].write('"'+wname+'" '+str(ws)+' '+str(wtuney)+' '+str(wmuy)+' '+str(wampy)+' '+str(wamp10)+' '+str(wphase10)+'\n')
        except:
            if len(BPMdictionary)!=0:
                countofmissingBPMs = countofmissingBPMs + 1
                print wname, "or", pname, "not found in the DATA. Total so far = ",countofmissingBPMs


    PseudoListX=[]
    PseudoListY=[]
    for j in range(0,len(ListOfZeroDPPX)):
        fbpmx[j].close()
        fbpmy[j].close()
        filex='temp'+str(j)+'_linx'
        filey='temp'+str(j)+'_liny'
        PseudoListX.append(metaclass.twiss(filex))
        PseudoListY.append(metaclass.twiss(filey))
        
        # Delete temp files again. (vimaier)
        os.remove(filex)
        os.remove(filey)


    return [PseudoListX,PseudoListY]

#----------------------- for finding the lines of the sextupoles (@ Glenn Vanbavinckhove)
def f2h(amp,ampphase,termj,factor,term,M2M):    # converts from f-term to h-term

    # conversion to include f2h
    tp=2.0*np.pi
    H=(amp/(termj*factor))*(1-np.e**complex(0,term*tp))

    Ampi=H.imag
    Ampr=H.real
    Amp=abs(H)/M2M
    phase=(math.atan2(Ampi,Ampr))/tp


    fh=[Ampi,Ampr,Amp,phase]

    return fh


def Getsextupole(MADTwiss,amp20list,phase,tune,j,k):
    '''
    function written to calculate resonance driving terms
    '''

    # constructing complex amplitude and phase using two BPM method

    bpms=Utilities.bpm.intersect(amp20list)
    bpms=Utilities.bpm.modelIntersect(bpms,MADTwiss)

    # Since beta,rmsbb(return_value[0:2]) are not used, slice return value([2:4])(vimaier)
    [bpms,invariantJx] = ( BetaFromAmplitude(MADTwiss,amp20list,'H') )[2:4]
    sqrt2jx=invariantJx[0]

    Q=tune+float(str(MADTwiss.Q1).split(".")[0])

    afactor=(1-cos(2*(j-k)*np.pi*Q))#(2*sin(np.pi*(j-k)*Q))
    #print (2*sin(np.pi*(j-k)*Q)),(1-cos(6*np.pi*Q))
    #sys.exit()
    pfactor=(np.pi*(j-k)*Q)

    htot={}

    for i in range(len(bpms)):

        if i<(len(bpms)-1):
            bpm=bpms[i][1]
            bpm1=bpms[i+1][1]
            s=bpms[i][0]
        else:
            bpm=bpms[i][1]
            bpm1=bpms[0][1]
            s=bpms[i][0]

        amp_i_list=[]
        phase_i_list=[]

        hlist=[]
        hplist=[]

        flist=[]
        fplist=[]


        for fileamp in amp20list:

            amp_201=fileamp.AMP_20[fileamp.indx[bpm]]*fileamp.AMPX[fileamp.indx[bpm]]
            amp_202=fileamp.AMP_20[fileamp.indx[bpm1]]*fileamp.AMPX[fileamp.indx[bpm1]]

            phase_201=fileamp.PHASE_20[fileamp.indx[bpm]]
            phase_202=fileamp.PHASE_20[fileamp.indx[bpm1]]

            delta=phase[bpm.upper()][0]-0.25
            edelta=phase[bpm.upper()][1]

            #computing complex line
            # Since eampi,ephasei(return_value[2:4]) are not used, slice return value([0:1])(vimaier)
            ampi,phasei = ( ComplexSecondaryLineExtended(delta,edelta,amp_201,amp_202,phase_201,phase_202) )[0:2]


            if ampi!=0.0:

                amp_i_list.append(ampi)
                phase_i_list.append(phasei)

                if (j==3 and k==0):
                    factor=math.sqrt(2)### factor
                    fterm=ampi/(factor*2*j*sqrt2jx**2)
                    pterm=(phasei-phase[bpm.upper()][0]+0.25)%1

                    hterm=fterm/afactor

                    hpterm=(pterm-pfactor)%1


                elif (j==2 and k==1):
                    factor=math.sqrt(2)### factor
                    fterm=ampi/(factor*2*j*sqrt2jx**2)
                    pterm=(phasei-phase[bpm][0]+0.25)%1

                    hterm=fterm/afactor

                    hpterm=(pterm-pfactor)%1

                flist.append(fterm)
                fplist.append(pterm)
                hlist.append(hterm)
                hplist.append(hpterm)


        if len(amp_i_list)!=0.0:
            al=np.mean(amp_i_list)
            alstd=np.std(amp_i_list)

            pl=np.mean(phase_i_list)
            plstd=np.mean(phasei)

            fl=np.mean(flist)
            fstd=np.std(flist)

            fpl=np.mean(fplist)
            fpstd=np.std(fplist)

            hl=np.mean(hlist)
            hstd=np.std(hlist)

            hpl=np.mean(hplist)
            hpstd=np.std(hplist)


            htot[bpm]=[bpm,s,al,alstd,pl,plstd,fl,fstd,fpl,fpstd,hl,hstd,hpl,hpstd]


    return htot,afactor,pfactor

def Getoctopole(MADTwiss,plane,twiss_files,phaseI,Q,fname,fM,NAMES):
    '''
    for finding secondary lines of the octuple (@ Glenn Vanbavinckhove)
    '''

        # intersects BPMs
    dbpms=Utilities.bpm.intersect(twiss_files[0])
    dbpms=Utilities.bpm.modelIntersect(dbpms,MADTwiss)



    # value definition
    hMODELT=[]
    hMODELTi=[]
    hMODELTr=[]
    h_phase_MODELT=[]

    AT=[]
    A_RMST=[]

    phaseT=[]
    phase_RMST=[]

    hT=[]
    hTi=[]
    hTr=[]
    h_RMST=[]

    h_phaseT=[]
    h_phase_RMST=[]

    invarianceJx=[]
    invarianceJy=[]

    # finding the invariances
    for j in range(0,len(twiss_files[0])):
        singleFilex=[twiss_files[0][j]]
        singleFiley=[twiss_files[1][j]]

        # Since beta,rmsbb,bpms(return_value[0:3]) are not used, slice return value([3])(vimaier)
        invariantJx = ( BetaFromAmplitude(MADTwiss,singleFilex,'H') )[3] 

        # Since beta,rmsbb,bpms(return_value[0:3]) are not used, slice return value([3])(vimaier)
        invariantJy = ( BetaFromAmplitude(MADTwiss,singleFiley,'V') )[3]

        invarianceJx.append(invariantJx)
        invarianceJy.append(invariantJy)


    # for the model
    for i in range(0,len(dbpms)):

        bpm=string.upper(dbpms[i][1])

        bpmC=MADTwiss.NAME[MADTwiss.indx[bpm]]


        for j in range(0,len(NAMES)):
            try:
                name=NAMES[j]

                if name==bpmC:

                    amp=abs(fM[j])
                    ampr=fM[i].real
                    ampi=fM[j].imag
                    phase=np.arctan2(ampi,ampr)%1

                    hMODELT.append(amp)
                    hMODELTr.append(ampr)
                    hMODELTi.append(ampi)
                    h_phase_MODELT.append(phase)



            except:
                print 'name '+str(NAMES[j])+' is not found in dictionary'
            hMODEL=[hMODELT,hMODELTi,hMODELTr,h_phase_MODELT]

    #calculation of f,q,h,qh
    for i in range(0,len(dbpms)-1):

        bn1=string.upper(dbpms[i][1])
        bn2=string.upper(dbpms[i+1][1])

        #print bn1
        #print phaseT


        dell= phaseI[bn1][0] - 0.25



        # internal value definition
        AS=[]
        A_SRMS=[]
        phaseS=[]
        phase_RMSS=[]

        hS=[]
        hSi=[]
        hSr=[]
        h_RMSS=[]
        h_phaseS=[]
        h_phase_RMSS=[]

        for j in range(0,len(twiss_files[0])):

            single_twiss = twiss_files[0][j]

            # for f4000
            if fname=='f4000':

                [A,phi]=ComplexSecondaryLine(dell, single_twiss.AMP_30[single_twiss.indx[bn1]], single_twiss.AMP_30[single_twiss.indx[bn2]], single_twiss.PHASE_30[single_twiss.indx[bn1]], single_twiss.PHASE_30[single_twiss.indx[bn2]])

                factor=float(8*invarianceJx[j][0]**1.5)   # 1 to fit with model
                term=float(4*Q[0])
                termj=4
                M2M=0.5

            #------ converting
            h=f2h(A,phi,termj,factor,term,M2M)

            #----- adding the terms
            AS.append(A)
            phaseS.append(phi)
            hSi.append(h[0])
            hSr.append(h[1])
            hS.append(h[2])
            h_phaseS.append(h[3])

        # array and taking average for all the input files for one BPM
        AS=np.array(AS)
        A_SRMS=math.sqrt(np.average(AS*AS)-(np.average(AS))**2+2.2e-16)

        phaseS=np.array(phaseS)
        try:
            phase_RMSS=math.sqrt(np.average(phaseS*phaseS)-(np.average(phaseS))**2+2.2e-16)
        except:
            phase_RMSS=0

        hS=np.array(hS)
        hSi=np.array(hSi)
        hSr=np.array(hSr)
        try:
            h_RMSS=math.sqrt(np.average(hS*hS)-(np.average(hS))**2+2.2e-16)
        except:
            h_RMSS=0

        h_phaseS=np.array(h_phaseS)
        try:
            phase_rms=np.average(h_phaseS*h_phaseS)-(np.average(h_phaseS))**2+2.2e-16
        except:
            phase_rms=0
        h_phase_RMSS=math.sqrt(phase_rms)

        # real output
        AT.append(np.average(AS))
        A_RMST.append(A_SRMS)

        phaseT.append(np.average(phaseS))
        phase_RMST.append(phase_RMSS)

        hT.append(np.average(hS))
        hTi.append(np.average(hSi))
        hTr.append(np.average(hSr))
        h_RMST.append(h_RMSS)

        h_phaseT.append(np.average(h_phaseS))
        h_phase_RMST.append(h_phase_RMSS)

        A=[AT,A_RMST,phaseT,phase_RMST]
        h=[hT,hTi,hTr,h_RMST,h_phaseT,h_phase_RMST]




    return [A,h,hMODEL,dbpms]


def computeChiTerms(amp,phase_20,phase,terms,J,plane,ima,rea):
    ''' for finding the chi terms '''

    #computes the chiterms for different inputs
    twoPi=2*np.pi

    delta1=((phase[1]-phase[0]-0.25)*twoPi)
    delta2=((phase[2]-phase[1]-0.25)*twoPi)

    inp=0.13 # ????
    #term1=((amp[0]*np.e**complex(0,phase_20[0]*twoPi)))/cos(delta1)
    #term2=((amp[1]*np.e**complex(0,phase_20[1]*twoPi)))*(tan(delta1)+tan(delta2))
    #term3=((amp[2]*np.e**complex(0,phase_20[2]*twoPi)))/cos(delta2)
    term1=((amp[0]*np.e**complex(0,(phase_20[0]+inp)*twoPi)))/cos(delta1)
    term2=((amp[1]*np.e**complex(0,(phase_20[1]+inp)*twoPi)))*(tan(delta1)+tan(delta2))
    term3=((amp[2]*np.e**complex(0,(phase_20[2]+inp)*twoPi)))/cos(delta2)
    chiTOT=(term1+term2+term3)

    chiAMP=abs(chiTOT)

    chiAMPi=chiTOT.imag
    chiAMPr=chiTOT.real
    #print chiTOT.imag,chiTOT.real
    chiPHASE=(((np.arctan2(chiTOT.imag,chiTOT.real)))/twoPi)%1
    #chiPHASE=(0.5-chiPHASE)%1



    JX=J[0]**(2.*(terms[0]+terms[1]-2.)/2.)
    JY=J[1]**(2.*(terms[2]+terms[3])/2.)


    Invariance=JX*JY
    Facot4AMP=Invariance*4/2 # to for conversion complex, invariance = ((2*JX)^(j+k-2)/2)*((2*JY)^(l+m)/2)


    chiAMP=chiAMP/Facot4AMP
    chiAMPi=chiAMPi/Facot4AMP
    chiAMPr=chiAMPr/Facot4AMP

    #print 'measured ima + real '+ str(chiAMPi)+' '+str(chiAMPr) + ' model ima + real '+str(ima)+' '+str(rea)

    return [chiAMP,chiAMPi,chiAMPr,chiPHASE]

def getChiTerms(MADTwiss,filesF,plane,name,ListOfZeroDPPX,ListOfZeroDPPY):

    # bmps
    files = filesF[0]

    dbpms = Utilities.bpm.intersect(files)
    dbpms = Utilities.bpm.modelIntersect(dbpms, MADTwiss)


    # initiliasing variables
    XIT=[]
    XITi=[]
    XITr=[]
    XIrmsT=[]
    XI_phase_T=[]
    XI_phaseRMS_T=[]

    POS1=[]
    POS2=[]
    POS3=[]

    XITMODEL=[]
    XITMODELi=[]
    XITMODELr=[]
    XITMODEL_phase=[]

    BPMS=[]
    invarianceJx=[]
    invarianceJy=[]

    for i in range(0,len(dbpms)): # ask rogelio

        bn1=string.upper(dbpms[i][1])

        BPMS.append(bn1)

    #### invariance
    for j in range(0,len(ListOfZeroDPPX)):
        # Since betax,rmsbbx,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJX = ( BetaFromAmplitude(MADTwiss,ListOfZeroDPPX,'H') )[3]
        # Since betay,rmsbby,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJY= ( BetaFromAmplitude(MADTwiss,ListOfZeroDPPY,'V') )[3]
        invarianceJx.append(invariantJX[0])
        invarianceJy.append(invariantJY[0])

    #print invarianceJx
    #### model chi
    MADTwiss.chiterms(BPMS)
    if name=='chi3000':
        MODEL=MADTwiss.chi
    elif name=='chi4000':
        MODEL=MADTwiss.chi4000


    for i in range(0,len(MODEL)):

        MODEL[i]=MODEL[i]
        amp=abs(MODEL[i])
        ampi=MODEL[i].imag
        ampr=MODEL[i].real

        if(MODEL[i].real==0. ):

            phase=0

        else:

            phase=np.arctan2(MODEL[i].imag,MODEL[i].real)%1


        XITMODEL.append(amp)
        XITMODELi.append(ampi)
        XITMODELr.append(ampr)
        XITMODEL_phase.append(phase)

    XIMODEl=[XITMODEL,XITMODELi,XITMODELr,XITMODEL_phase]

    for i in range(0,len(dbpms)-2):

        XI=[]
        XIi=[]
        XIr=[]
        XIrms=[]
        XI_phase=[]
        XI_phaseRMS=[]

        bn1=string.upper(dbpms[i][1])
        bn2=string.upper(dbpms[i+1][1])
        bn3=string.upper(dbpms[i+2][1])

        filej=ListOfZeroDPPX[0]

        pos1=filej.S[filej.indx[bn1]]
        pos2=filej.S[filej.indx[bn2]]
        pos3=filej.S[filej.indx[bn3]]


        POS1.append(pos1)
        POS2.append(pos2)
        POS3.append(pos3)

        imaM=XITMODELi[i]
        realM=XITMODELr[i]

        for j in range(0,len(files)):
            jx=files[j]




            # for chi3000
            if name=='chi3000':
                phase1=jx.PHASE_20[jx.indx[bn1]]
                phase2=jx.PHASE_20[jx.indx[bn2]]
                phase3=jx.PHASE_20[jx.indx[bn3]]
                phase_SL=[phase1,phase2,phase3]

                terms=[3,0,0,0]
                amp1=jx.AMP_20[jx.indx[bn1]]
                amp2=jx.AMP_20[jx.indx[bn2]]
                amp3=jx.AMP_20[jx.indx[bn3]]
                amp=[amp1,amp2,amp3]

            # for chi4000
            elif name=='chi4000':
                phase1=jx.PHASE_30[jx.indx[bn1]]
                phase2=jx.PHASE_30[jx.indx[bn2]]
                phase3=jx.PHASE_30[jx.indx[bn3]]
                phase_SL=[phase1,phase2,phase3]

                terms=[4,0,0,0]
                amp1=jx.AMP_30[jx.indx[bn1]]
                amp2=jx.AMP_30[jx.indx[bn2]]
                amp3=jx.AMP_30[jx.indx[bn3]]
                amp=[amp1,amp2,amp3]

            phase11=jx.MUX[jx.indx[bn1]]
            phase12=jx.MUX[jx.indx[bn2]]
            phase13=jx.MUX[jx.indx[bn3]]
            phase=[phase11,phase12,phase13]


            J=[ invarianceJx[j],invarianceJy[j]]



            chi=computeChiTerms(amp,phase_SL,phase,terms,J,'H',imaM,realM)



            XI.append(chi[0])
            XIi.append(chi[1])
            XIr.append(chi[2])
            XI_phase.append(chi[3])



        XI=np.array(XI)
        XIi=np.array(XIi)
        XIr=np.array(XIr)
        try:
            XIrms=math.sqrt(np.average(XI*XI)-np.average(XI)**2+2.2e-16)
        except:
            XIrms=0
        XI_phase=np.array(XI_phase)
        try:
            XI_phaseRMS=math.sqrt(np.average(XI_phase*XI_phase)-np.average(XI_phase)**2+2.2e-16)
        except:
            XI_phaseRMS=0


        XIT.append(np.average(XI))
        XITi.append(np.average(XIi))
        XITr.append(np.average(XIr))
        XIrmsT.append(XIrms)
        XI_phase_T.append(np.average(XI_phase))
        XI_phaseRMS_T.append(XI_phaseRMS)

        POS=[POS1,POS2,POS3]

        XItot=[XIT,XITi,XITr,XIrmsT,XI_phase_T,XI_phaseRMS_T]

    return [dbpms,POS,XItot,XIMODEl]

def getchi1010(MADTwiss,filesF,plane,name,ListOfZeroDPPX,ListOfZeroDPPY):

        # bmps
    files=filesF[0]
    filesy=filesF[1]

    dbpms=Utilities.bpm.intersect(files+filesy)
    dbpms=Utilities.bpm.modelIntersect(dbpms, MADTwiss)

    dbpmsy=Utilities.bpm.intersect(filesy+files)
    dbpmsy=Utilities.bpm.modelIntersect(dbpmsy, MADTwiss)


    # initiliasing variables
    XIT=[]
    XIrmsT=[]
    XI_phase_T=[]
    XI_phaseRMS_T=[]

    invarianceJx=[]
    invarianceJy=[]

    #### invariance
    for j in range(0,len(files)):
        # Since betax,rmsbbx,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJX = ( BetaFromAmplitude(MADTwiss,ListOfZeroDPPX,'H') )[3]
        # Since betay,rmsbby,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJY = ( BetaFromAmplitude(MADTwiss,ListOfZeroDPPY,'V') )[3]
        invarianceJx.append(invariantJX[0])
        invarianceJy.append(invariantJY[0])


    for i in range(0,len(dbpms)):

        XI=[]
        XIrms=[]
        XI_phase=[]
        XI_phaseRMS=[]

        bn=string.upper(dbpms[i][1])
        bny=string.upper(dbpmsy[i][1])

        for j in range(0,len(files)):

            jx=files[j]

            jy=filesy[j]

            amp10x=jx.AMP01[jx.indx[bn]]
            amp10y=jy.AMP10[jy.indx[bny]]
            phase10x=jx.PHASE01[jx.indx[bn]]
            phasex=jx.MUX[jx.indx[bn]]

            XI1010=0.25*math.sqrt(amp10x*amp10y)
            phase1010=phase10x+phasex

            XI.append(XI1010)
            XI_phase.append(phase1010)

        XI=np.array(XI)
        XIrms=math.sqrt(np.average(XI*XI)-np.average(XI)**2+2.2e-16)
        XI_phase=np.array(XI_phase)
        XI_phaseRMS=math.sqrt(np.average(XI_phase*XI_phase)-np.average(XI_phase)**2+2.2e-16)


        XIT.append(np.average(XI))
        XIrmsT.append(XIrms)
        XI_phase_T.append(np.average(XI_phase))
        XI_phaseRMS_T.append(XI_phaseRMS)

        XItot=[XIT,XIrmsT,XI_phase_T,XI_phaseRMS_T]

    return [dbpms,XItot]

#---- construct offmomentum
def ConstructOffMomentumModel(MADTwiss,dpp, dictionary):

    j=MADTwiss
    bpms=Utilities.bpm.intersect([MADTwiss])

    Qx=j.Q1+dpp*j.DQ1
    Qy=j.Q2+dpp*j.DQ2

    ftemp_name = "./TempTwiss.dat"
    ftemp=open(ftemp_name,"w")
    ftemp.write("@ Q1 %le "+str(Qx)+"\n")
    ftemp.write("@ Q2 %le "+str(Qy)+"\n")
    ftemp.write("@ DPP %le "+str(dpp)+"\n")
    ftemp.write("* NAME S BETX BETY ALFX ALFY MUX MUY\n")
    ftemp.write("$ %s %le %le  %le  %le  %le  %le %le\n")


    for i in range(0,len(bpms)):
        bn=string.upper(bpms[i][1])
        bns=bpms[i][0]

        # dbeta and dalpha will be extract via metaclass. As it is for the time being.
        ax=j.WX[j.indx[bn]]*cos(2.0*np.pi*j.PHIX[j.indx[bn]])
        bx=j.WX[j.indx[bn]]*sin(2.0*np.pi*j.PHIX[j.indx[bn]])
        bx1=bx+j.ALFX[j.indx[bn]]*ax
        NBETX=j.BETX[j.indx[bn]]*(1.0+ax*dpp)
        NALFX=j.ALFX[j.indx[bn]]+bx1*dpp
        NMUX=j.MUX[j.indx[bn]]+j.DMUX[j.indx[bn]]*dpp

        ay=j.WY[j.indx[bn]]*cos(2.0*np.pi*j.PHIY[j.indx[bn]])
        by=j.WY[j.indx[bn]]*sin(2.0*np.pi*j.PHIY[j.indx[bn]])
        by1=by+j.ALFY[j.indx[bn]]*ay
        NBETY=j.BETY[j.indx[bn]]*(1.0+ay*dpp)
        NALFY=j.ALFY[j.indx[bn]]+by1*dpp
        NMUY=j.MUY[j.indx[bn]]+j.DMUY[j.indx[bn]]*dpp

        ftemp.write('"'+bn+'" '+str(bns)+" "+str(NBETX)+" "+str(NBETY)+" "+str(NALFX)+" "+str(NALFY)+" "+str(NMUX)+" "+str(NMUY)+"\n")

    ftemp.close()
    dpptwiss=metaclass.twiss(ftemp_name,dictionary)
    
    # Delete temp file again(vimaier)
    os.remove(ftemp_name)
    

    return dpptwiss


#---- finding kick
def getkick(files,MADTwiss):

    invarianceJx=[]
    invarianceJy=[]

    tunex=[]
    tuney=[]

    tunexRMS=[]
    tuneyRMS=[]

    dpp=[]



        # finding the invariances
    for j in range(0,len(files[0])):
        x=files[0][j]
        y=files[1][j]

        # Since beta,rmsbb,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJx = ( BetaFromAmplitude(MADTwiss,[x],'H') )[3]
        # Since beta,rmsbb,bpms(return_value[0:3]) are not used, slice the return value([3]) (vimaier)
        invariantJy = ( BetaFromAmplitude(MADTwiss,[y],'V') )[3]

        invarianceJx.append(invariantJx)
        invarianceJy.append(invariantJy)

        try:
            dpp.append(x.DPP)
        except:
            dpp.append(0.0)
        tunex.append(x.Q1)
        tuney.append(y.Q2)
        tunexRMS.append(x.Q1RMS)
        tuneyRMS.append(y.Q2RMS)




    tune=[tunex,tuney]
    tuneRMS=[tunexRMS,tuneyRMS]

    return [invarianceJx,invarianceJy,tune,tuneRMS,dpp]

def BPMfinder(IP,model,measured):

    # last index
    indxes=model.S

    bpml="null"
    bpmh="null"
    for ind in range(len(indxes)):
        #print ind
        name=model.NAME[ind]
        if "BPMSW.1L"+IP in name:
            bpml=name
            try:
                test = measured[0][bpml][0]  # @UnusedVariable
            except:
                bpml="null"
        if "BPMSW.1R"+IP in name:
            bpmh=name
            try:
                test = measured[0][bpmh][0]  # @UnusedVariable
            except:
                bpmh="null"
    return [bpml,bpmh]



def getIP(IP,measured,model,phase,bpms):

    BPMleft,BPMright=BPMfinder(IP,model,measured)

    #print "IN ip"

    if "null" in BPMleft or "null" in BPMright:

        print "skipping IP"+IP+" calculation, no BPM found"
        betahor=[IP,0,0,0,0,0,0]
        betaver=[IP,0,0,0,0,0,0]
        #sys.exit()

    else:
        # model
        sxl=model.S[model.indx[BPMleft]]
        sip=model.S[model.indx["IP"+IP]]
        sxr=model.S[model.indx[BPMright]]
        betaipx=model.BETX[model.indx["IP"+IP]]
        #alxl=model.ALFX[[model.indx[BPMleft]]
        #alyl=model.ALFY[[model.indx[BPMleft]]
        #alxr=model.ALFX[[model.indx[BPMright]]
        #alyr=model.ALFY[[model.indx[BPMright]]
        #print betaipx
        betaipy=model.BETY[model.indx["IP"+IP]]
        #print betaipy

        # measured value
        betaxl=measured[0][BPMleft][0]
        betayl=measured[1][BPMleft][0]

        betaxr=measured[0][BPMright][0]
        betayr=measured[1][BPMright][0]

        deltaphimodel=abs(model.MUX[model.indx[BPMright]]-model.MUX[model.indx[BPMleft]])


        L=((sip-sxl)+(sxr-sip))/2
        betastar=(2*math.sqrt(betaxl)*math.sqrt(betaxr)*sin(deltaphimodel*2*np.pi))/(betayl+betayr-2*math.sqrt(betaxl)*math.sqrt(betaxr)*cos(2*np.pi*deltaphimodel))*L
        location=((betaxl-betaxr)/(betaxl+betaxr-2*math.sqrt(betaxl)*math.sqrt(betaxr)*cos(2*np.pi*deltaphimodel)))*L

        deltaphi=(math.atan((L-location)/betastar)+math.atan((L+location)/betastar))/(2*np.pi)

        betahor=[IP,betastar,location,deltaphi,betaipx,deltaphimodel,0]


        print "horizontal betastar for ",IP," is ",str(betastar)," at location ",str(location), " of IP center with phase advance ",str(deltaphi)

        #vertical
        deltaphimodel=abs(model.MUY[model.indx[BPMright]]-model.MUY[model.indx[BPMleft]])


        betastar=(2*math.sqrt(betayl)*math.sqrt(betayr)*sin(deltaphimodel*2*np.pi))/(betayl+betayr-2*math.sqrt(betayl)*math.sqrt(betayr)*cos(2*np.pi*deltaphimodel))*L
        location=((betayl-betayr)/(betayl+betayr-2*math.sqrt(betayl)*math.sqrt(betayr)*cos(2*np.pi*deltaphimodel)))*L

        deltaphi=(math.atan((L-location)/betastar)+math.atan((L+location)/betastar))/(2*np.pi)

        betaver=[IP,betastar,location,deltaphi,betaipy,deltaphimodel,0]

        print "vertical betastar for ",IP," is ",str(betastar)," at location ",str(location), " of IP center with phase advance ",str(deltaphi)


    return [betahor,betaver]

def GetIP2(MADTwiss,Files,Q,plane,bd,oa,op):

    #-- Common BPMs
    bpm = Utilities.bpm.modelIntersect(Utilities.bpm.intersect(Files),MADTwiss)
    bpm = [(b[0],string.upper(b[1])) for b in bpm]

    #-- Loop for IPs
    result={}
    for ip in ('1','2','5','8'):

        bpml='BPMSW.1L'+ip+'.'+oa[3:]
        bpmr='BPMSW.1R'+ip+'.'+oa[3:]

        if (bpml in zip(*bpm)[1]) and (bpmr in zip(*bpm)[1]):

            #-- Model values
            L=0.5*(MADTwiss.S[MADTwiss.indx[bpmr]]-MADTwiss.S[MADTwiss.indx[bpml]])
            if L<0: L+=0.5*MADTwiss.LENGTH  #-- For sim starting in the middle of an IP
            if plane=='H':
                betlmdl=MADTwiss.BETX[MADTwiss.indx[bpml]]
                alflmdl=MADTwiss.ALFX[MADTwiss.indx[bpml]]
            if plane=='V':
                betlmdl=MADTwiss.BETY[MADTwiss.indx[bpml]]
                alflmdl=MADTwiss.ALFY[MADTwiss.indx[bpml]]
            betsmdl=betlmdl/(1+alflmdl**2)
            betmdl =betlmdl-2*alflmdl*L+L**2/betsmdl
            alfmdl =alflmdl-L/betsmdl
            dsmdl  =alfmdl*betsmdl

            #-- Measurement for each file
            betall=[]
            alfall=[]
            betsall=[]
            dsall=[]
            rt2Jall=[]
            for i in range(len(Files)):
                try:
                    if plane=='H':
                        al=Files[i].AMPX[Files[i].indx[bpml]]
                        ar=Files[i].AMPX[Files[i].indx[bpmr]]
                        if list(zip(*bpm)[1]).index(bpmr)>list(zip(*bpm)[1]).index(bpml):
                            dpsi=2*np.pi*bd*(Files[i].MUX[Files[i].indx[bpmr]]-Files[i].MUX[Files[i].indx[bpml]])
                        else:
                            dpsi=2*np.pi*(Q+bd*(Files[i].MUX[Files[i].indx[bpmr]]-Files[i].MUX[Files[i].indx[bpml]]))
                        #-- To compensate the phase shift by tune
                        if op=='1':
                            if (bd==1 and ip=='2') or (bd==-1 and ip=='8'): dpsi+=2*np.pi*Q
                    if plane=='V':
                        al=Files[i].AMPY[Files[i].indx[bpml]]
                        ar=Files[i].AMPY[Files[i].indx[bpmr]]
                        if list(zip(*bpm)[1]).index(bpmr)>list(zip(*bpm)[1]).index(bpml):
                            dpsi=2*np.pi*bd*(Files[i].MUY[Files[i].indx[bpmr]]-Files[i].MUY[Files[i].indx[bpml]])
                        else:
                            dpsi=2*np.pi*(Q+bd*(Files[i].MUY[Files[i].indx[bpmr]]-Files[i].MUY[Files[i].indx[bpml]]))
                        #-- To compensate the phase shift by tune
                        if op=='1':
                            if (bd==1 and ip=='2') or (bd==-1 and ip=='8'): dpsi+=2*np.pi*Q

                    #-- bet, alf, and math.sqrt(2J) from amp and phase advance
                    bet =L*(al**2+ar**2+2*al*ar*cos(dpsi))/(2*al*ar*sin(dpsi))
                    alf =(al**2-ar**2)/(2*al*ar*sin(dpsi))
                    bets=bet/(1+alf**2)
                    ds  =alf*bets
                    rt2J=math.sqrt(al*ar*sin(dpsi)/(2*L))
                    betall.append(bet)
                    alfall.append(alf)
                    betsall.append(bets)
                    dsall.append(ds)
                    rt2Jall.append(rt2J)
                except:
                    
                    pass

            #-- Ave and Std
            betall =np.array(betall) ; betave =np.mean(betall) ; betstd =math.sqrt(np.mean((betall-betave)**2))
            alfall =np.array(alfall) ; alfave =np.mean(alfall) ; alfstd =math.sqrt(np.mean((alfall-alfave)**2))
            betsall=np.array(betsall); betsave=np.mean(betsall); betsstd=math.sqrt(np.mean((betsall-betsave)**2))
            dsall  =np.array(dsall)  ; dsave  =np.mean(dsall)  ; dsstd  =math.sqrt(np.mean((dsall-dsave)**2))
            rt2Jall=np.array(rt2Jall); rt2Jave=np.mean(rt2Jall); rt2Jstd=math.sqrt(np.mean((rt2Jall-rt2Jave)**2))
            result['IP'+ip]=[betave,betstd,betmdl,alfave,alfstd,alfmdl,betsave,betsstd,betsmdl,dsave,dsstd,dsmdl,rt2Jave,rt2Jstd]

    return result

def GetIPFromPhase(MADTwiss,psix,psiy,oa):

    IP=('1','2','5','8')
    result={}
    for i in IP:
        bpml='BPMSW.1L'+i+'.'+oa[3:]
        bpmr=bpml.replace('L','R')
        try:
            if psix[bpml][-1]==bpmr:
                #-- Model
                L       =0.5*(MADTwiss.S[MADTwiss.indx[bpmr]]-MADTwiss.S[MADTwiss.indx[bpml]])
                dpsixmdl=MADTwiss.MUX[MADTwiss.indx[bpmr]]-MADTwiss.MUX[MADTwiss.indx[bpml]]
                dpsiymdl=MADTwiss.MUY[MADTwiss.indx[bpmr]]-MADTwiss.MUY[MADTwiss.indx[bpml]]
                betxmdl =MADTwiss.BETX[MADTwiss.indx[bpml]]/(1+MADTwiss.ALFX[MADTwiss.indx[bpml]]**2)
                betymdl =MADTwiss.BETY[MADTwiss.indx[bpml]]/(1+MADTwiss.ALFY[MADTwiss.indx[bpml]]**2)
                #-- For sim starting in the middle of an IP
                if L < 0:
                    L += 0.5 * MADTwiss.LENGTH
                    dpsixmdl += MADTwiss.Q1
                    dpsiymdl += MADTwiss.Q2
                #-- Measurement
                dpsix   =psix['BPMSW.1L'+i+'.'+oa[3:]][0]
                dpsiy   =psiy['BPMSW.1L'+i+'.'+oa[3:]][0]
                dpsixstd=psix['BPMSW.1L'+i+'.'+oa[3:]][1]
                dpsiystd=psiy['BPMSW.1L'+i+'.'+oa[3:]][1]
                betx    =L/tan(np.pi*dpsix)
                bety    =L/tan(np.pi*dpsiy)
                betxstd =L*np.pi*dpsixstd/(2*sin(np.pi*dpsix)**2)
                betystd =L*np.pi*dpsiystd/(2*sin(np.pi*dpsiy)**2)
                result['IP'+i]=[2*L,betx,betxstd,betxmdl,bety,betystd,betymdl,dpsix,dpsixstd,dpsixmdl,dpsiy,dpsiystd,dpsiymdl]
        except: pass
        #-- This part due to the format difference of phasef2 (from the model)
        try:
            if psix[bpml][-2]==bpmr:
                #-- Model
                L       =0.5*(MADTwiss.S[MADTwiss.indx[bpmr]]-MADTwiss.S[MADTwiss.indx[bpml]])
                dpsixmdl=MADTwiss.MUX[MADTwiss.indx[bpmr]]-MADTwiss.MUX[MADTwiss.indx[bpml]]
                dpsiymdl=MADTwiss.MUY[MADTwiss.indx[bpmr]]-MADTwiss.MUY[MADTwiss.indx[bpml]]
                betxmdl =MADTwiss.BETX[MADTwiss.indx[bpml]]/(1+MADTwiss.ALFX[MADTwiss.indx[bpml]]**2)
                betymdl =MADTwiss.BETY[MADTwiss.indx[bpml]]/(1+MADTwiss.ALFY[MADTwiss.indx[bpml]]**2)
                #-- For sim starting in the middle of an IP
                if L < 0:
                    L += 0.5 * MADTwiss.LENGTH
                    dpsixmdl += MADTwiss.Q1
                    dpsiymdl += MADTwiss.Q2
                #-- Measurement
                dpsix   =psix['BPMSW.1L'+i+'.'+oa[3:]][0]
                dpsiy   =psiy['BPMSW.1L'+i+'.'+oa[3:]][0]
                dpsixstd=psix['BPMSW.1L'+i+'.'+oa[3:]][1]
                dpsiystd=psiy['BPMSW.1L'+i+'.'+oa[3:]][1]
                betx    =L/tan(np.pi*dpsix)
                bety    =L/tan(np.pi*dpsiy)
                betxstd =L*np.pi*dpsixstd/(2*sin(np.pi*dpsix)**2)
                betystd =L*np.pi*dpsiystd/(2*sin(np.pi*dpsiy)**2)
                result['IP'+i]=[2*L,betx,betxstd,betxmdl,bety,betystd,betymdl,dpsix,dpsixstd,dpsixmdl,dpsiy,dpsiystd,dpsiymdl]
        except: pass

    return result

def getCandGammaQmin(fqwq,bpms,tunex,tuney,twiss):
    # Cut the fractional part of Q1 and Q2
    QQ1 = float( int(twiss.Q1) )
    QQ2 = float( int(twiss.Q2) )

    tunex=float(tunex)+QQ1
    tuney=float(tuney)+QQ2

    tunefactor=(cos(2*np.pi*tunex)-cos(2*np.pi*tuney))/(np.pi*(sin(2*np.pi*tunex)+sin(2*np.pi*tuney)))

    coupleterms={}
    Qmin=[]


    if len(bpms)==0:
        print "No bpms in getCandGammaQmin. Returning emtpy stuff"
        return coupleterms,0,0,bpms

    for bpm in bpms:

        bpmm=bpm[1].upper()

        detC=1-(1/(1+4*(abs(fqwq[bpmm][0][0])**2-abs(fqwq[bpmm][0][2])**2)))


        check2=0.25+abs(fqwq[bpmm][0][0])**2


        if check2>abs(fqwq[bpmm][0][2])**2: # checking if sum or difference resonance is dominant!
            gamma=math.sqrt(1/(1/(1+4*(abs(fqwq[bpmm][0][0])**2-abs(fqwq[bpmm][0][2])**2))))
            #print detC
            ffactor= 2*gamma*tunefactor*math.sqrt(abs(detC)) # cannot take abs
            C11=-(fqwq[bpmm][0][0].imag-fqwq[bpmm][0][2].imag)*2*gamma
            C12=-(fqwq[bpmm][0][0].real+fqwq[bpmm][0][2].real)*2*gamma
            C21=(fqwq[bpmm][0][0].real+fqwq[bpmm][0][2].real)*2*gamma
            C22=(fqwq[bpmm][0][0].imag-fqwq[bpmm][0][2].imag)*2*gamma
        else: # negative gamma
            gamma=-1
            ffactor=-1
            C11=C12=C21=C22=-1


        Qmin.append(ffactor)

        if (abs(fqwq[bpmm][0][0])**2-abs(fqwq[bpmm][0][2])**2)>0.0:

            err=(2*((abs(fqwq[bpmm][0][1])*abs(fqwq[bpmm][0][0]))+(abs(fqwq[bpmm][0][3])*abs(fqwq[bpmm][0][2]))))/(abs(fqwq[bpmm][0][0])**2-abs(fqwq[bpmm][0][2])**2)

        else:
            err=-1


        coupleterms[bpmm]=[detC,err,gamma,err,C11,C12,C21,C22]

    if gamma==-1:
        print "WARN: Sum resonance is dominant! "

    Qmin=np.array(Qmin)

    Qminerr=math.sqrt(np.average(Qmin*Qmin)-(np.average(Qmin))**2+2.2e-16)
    Qminav=np.average(Qmin)




    return coupleterms,Qminav,Qminerr,bpms






###### ac-dipole stuff

def getFreeBeta(modelfree,modelac,betal,rmsbb,alfal,bpms,plane): # to check "+"

    # ! how to deal with error !

    #print "Calculating free beta using model"
    #TODO: twice modelIntersect? check it! (vimaier)
    bpms=Utilities.bpm.modelIntersect(bpms, modelfree)
    bpms=Utilities.bpm.modelIntersect(bpms, modelac)
    betan={}
    alfan={}
    for bpma in bpms:

        bpm=bpma[1].upper()
        beta,beterr,betstd=betal[bpm]
        alfa,alferr,alfstd=alfal[bpm]

        if plane=="H":
            betmf=modelfree.BETX[modelfree.indx[bpm]]
            betma=modelac.BETX[modelac.indx[bpm]]
            bb=(betma-betmf)/betmf
            alfmf=modelfree.ALFX[modelfree.indx[bpm]]
            alfma=modelac.ALFX[modelac.indx[bpm]]
            aa=(alfma-alfmf)/alfmf
        else:
            betmf=modelfree.BETY[modelfree.indx[bpm]]
            betma=modelac.BETY[modelac.indx[bpm]]
            alfmf=modelfree.ALFY[modelfree.indx[bpm]]
            alfma=modelac.ALFY[modelac.indx[bpm]]
            bb=(betma-betmf)/betmf
            aa=(alfma-alfmf)/alfmf

        betan[bpm]=beta*(1+bb),beterr,betstd # has to be plus!
        alfan[bpm]=alfa*(1+aa),alferr,alfstd

    #sys.exit()
    return betan,rmsbb,alfan,bpms

def getFreeCoupling(tunefreex,tunefreey,tunedrivenx,tunedriveny,fterm,twiss,bpms):

    print "Calculating free fterms"
    couple={}
    couple['Global']=[fterm['Global'][0],fterm['Global'][1]]

    QQ1=float(str(twiss.Q1).split('.')[0])
    QQ2=float(str(twiss.Q2).split('.')[0])

    if(tunefreey>0.50):
        tunefreey=1-tunefreey
        tunefreey=abs(QQ2+tunefreey)
    else:
        tunefreey=abs(QQ2+abs(tunefreey))
    if(tunefreex>0.50):
        tunefreex=1-float(tunefreex)
        tunefreex=abs(QQ1+tunefreex)
    else:
        tunefreex=abs(QQ1+abs(tunefreex))

    if(tunedrivenx>0.50):
        tunedrivenx=1-tunedrivenx
    if(tunedriveny>0.50):
        tunedriveny=1-tunedriveny

    tunedrivenx=abs(QQ1+abs(tunedrivenx))
    tunedriveny=abs(QQ2+abs(tunedriveny))


    # diff f1001
    factor_top_diff=math.sqrt(sin(np.pi*(tunedrivenx-tunefreey))*sin(np.pi*(tunefreex-tunedriveny)))
    factor_bottom_diff=sin(np.pi*(tunefreex-tunefreey))

    factor_diff=abs((factor_top_diff/factor_bottom_diff))

    print "Factor for coupling diff ",factor_diff

    # sum f1010
    factor_top_sum=math.sqrt(sin(np.pi*(tunedrivenx+tunefreey))*sin(np.pi*(tunefreex+tunedriveny)))
    factor_bottom_sum=sin(np.pi*(tunefreex+tunefreey))

    factor_sum=abs((factor_top_sum/factor_bottom_sum))

    print "Factor for coupling sum ",factor_sum

    for bpm in bpms:

        bpmm=bpm[1].upper()
        [amp,phase]=fterm[bpmm]

        #print amp[2]

        ampp=[amp[0]*factor_diff,amp[1],amp[2]*factor_sum,amp[3]]
        pphase=[phase[0]*factor_diff,phase[1],phase[2]*factor_sum,phase[3]]

        couple[bpmm]=[ampp,pphase]

    return couple,bpms

def getFreeAmpBeta(betai,rmsbb,bpms,invJ,modelac,modelfree,plane): # "-"

    #
    # Why difference in betabeta calculation ??
    #
    #

    betas={}

    #print "Calculating free beta from amplitude using model"

    for bpm in bpms:

        bpmm=bpm[1].upper()
        beta=betai[bpmm][0]

        if plane=="H":
            betmf=modelfree.BETX[modelfree.indx[bpmm]]
            betma=modelac.BETX[modelac.indx[bpmm]]
            bb=(betmf-betma)/betma

        else:
            betmf=modelfree.BETY[modelfree.indx[bpmm]]
            betma=modelac.BETY[modelac.indx[bpmm]]
            bb=(betmf-betma)/betma

        #print beta,beta*(1+bb)

        betas[bpmm]=[beta*(1+bb),betai[bpmm][1],betai[bpmm][2]]

    return betas,rmsbb,bpms,invJ

def getfreephase(phase,Qac,Q,bpms,MADTwiss_ac,MADTwiss,plane):
    '''
    :Parameters:
        'phase': dict
            (bpm_name:string) --> (phase_list:[phi12,phstd12,phi13,phstd13,phmdl12,phmdl13,bn2])
            phi13, phstd13, phmdl12 and phmdl13 are note used.
        
    '''

    #print "Calculating free phase using model"

    phasef={}
    phi=[]

    for bpm in bpms:
        bn1=bpm[1].upper()

        phase_list = phase[bn1]
        phi12 = phase_list[0]
        phstd12 = phase_list[1]
        bn2 =phase_list[6]
        bn2s=MADTwiss.S[MADTwiss.indx[bn2]]
        #model ac
        if plane=="H":
            ph_ac_m=MADTwiss_ac.MUX[MADTwiss_ac.indx[bn2]]-MADTwiss_ac.MUX[MADTwiss_ac.indx[bn1]]
            ph_m=MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[bn1]]
        else:
            ph_ac_m=MADTwiss_ac.MUY[MADTwiss_ac.indx[bn2]]-MADTwiss_ac.MUY[MADTwiss_ac.indx[bn1]]
            ph_m=MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[bn1]]

        # take care the last BPM
        if bn1==bpms[-1][1].upper():
            ph_ac_m+=Qac; ph_ac_m=ph_ac_m%1
            ph_m   +=Q  ; ph_m   =ph_m%1

        phi12f=phi12-(ph_ac_m-ph_m)
        phi.append(phi12f)
        phstd12f=phstd12
        phmdl12f=ph_m

        phasef[bn1]=phi12f,phstd12f,phmdl12f,bn2,bn2s

    mu=sum(phi)


    return phasef,mu,bpms

def getfreephaseTotal(phase,bpms,plane,MADTwiss,MADTwiss_ac):
    '''
    :Parameters:
        'phase': dict
            (bpm_name:string) --> (phase_list:[phi12,phstd12,phmdl12,bn1])
            phmdl12 and bn1 are note used.
        
    '''
    #print "Calculating free total phase using model"

    first=bpms[0][1]

    phasef={}

    for bpm in bpms:
        bn2=bpm[1].upper()

        if plane=="H":

            ph_ac_m=(MADTwiss_ac.MUX[MADTwiss_ac.indx[bn2]]-MADTwiss_ac.MUX[MADTwiss_ac.indx[first]])%1
            ph_m=(MADTwiss.MUX[MADTwiss.indx[bn2]]-MADTwiss.MUX[MADTwiss.indx[first]])%1

        else:
            ph_ac_m=(MADTwiss_ac.MUY[MADTwiss_ac.indx[bn2]]-MADTwiss_ac.MUY[MADTwiss_ac.indx[first]])%1
            ph_m=(MADTwiss.MUY[MADTwiss.indx[bn2]]-MADTwiss.MUY[MADTwiss.indx[first]])%1

        phase_list = phase[bn2]
        phi12 = phase_list[0]
        phstd12 = phase_list[1]


        phi12=phi12-(ph_ac_m-ph_m)
        phstd12=phstd12

        phasef[bn2]=phi12,phstd12,ph_m

    return phasef,bpms

# free coupling from equations

def GetFreeIP2(MADTwiss,MADTwiss_ac,IP,plane,oa):

    for i in ('1','2','5','8'):

        bpml='BPMSW.1L'+i+'.'+oa[3:]
        bpmr='BPMSW.1R'+i+'.'+oa[3:]
        if 'IP'+i in IP:

            L=0.5*(MADTwiss.S[MADTwiss.indx[bpmr]]-MADTwiss.S[MADTwiss.indx[bpml]])
            if L<0: L+=0.5*MADTwiss.LENGTH
            #-- bet and alf at the left BPM
            if plane=='H':
                betl =MADTwiss.BETX[MADTwiss.indx[bpml]]; betdl=MADTwiss_ac.BETX[MADTwiss_ac.indx[bpml]]
                alfl =MADTwiss.ALFX[MADTwiss.indx[bpml]]; alfdl=MADTwiss_ac.ALFX[MADTwiss_ac.indx[bpml]]
            if plane=='V':
                betl =MADTwiss.BETY[MADTwiss.indx[bpml]]; betdl=MADTwiss_ac.BETY[MADTwiss_ac.indx[bpml]]
                alfl =MADTwiss.ALFY[MADTwiss.indx[bpml]]; alfdl=MADTwiss_ac.ALFY[MADTwiss_ac.indx[bpml]]
            #-- IP parameters propagated from the left BPM
            bets =betl/(1+alfl**2)       ; betds=betdl/(1+alfdl**2)
            bet  =betl-2*alfl*L+L**2/bets; betd =betdl-2*alfdl*L+L**2/betds
            alf  =alfl-L/bets            ; alfd =alfdl-L/betds
            ds   =alf*bets               ; dsd  =alfd*betds
            #-- Apply corrections
            IP['IP'+i][0]=IP['IP'+i][0]+bet-betd  ; IP['IP'+i][2] =bet
            IP['IP'+i][3]=IP['IP'+i][3]+alf-alfd  ; IP['IP'+i][5] =alf
            IP['IP'+i][6]=IP['IP'+i][6]+bets-betds; IP['IP'+i][8] =bets
            IP['IP'+i][9]=IP['IP'+i][9]+ds-dsd    ; IP['IP'+i][11]=ds

    return IP

#---------  The following is functions to compensate the AC dipole effect based on analytic formulae (by R. Miyamoto)

def GetACPhase_AC2BPMAC(MADTwiss,Qd,Q,plane,oa):
    if   oa=='LHCB1':
        bpmac1='BPMYA.5L4.B1'
        bpmac2='BPMYB.6L4.B1'
    elif oa=='LHCB2':
        bpmac1='BPMYB.5L4.B2'
        bpmac2='BPMYA.6L4.B2'
    else:
        return {}

    if plane=='H':
        psi_ac2bpmac1=MADTwiss.MUX[MADTwiss.indx[bpmac1]]-MADTwiss.MUX[MADTwiss.indx['MKQA.6L4.'+oa[3:]]]  #-- B1 direction for B2
        psi_ac2bpmac2=MADTwiss.MUX[MADTwiss.indx[bpmac2]]-MADTwiss.MUX[MADTwiss.indx['MKQA.6L4.'+oa[3:]]]  #-- B1 direction for B2
    if plane=='V':
        psi_ac2bpmac1=MADTwiss.MUY[MADTwiss.indx[bpmac1]]-MADTwiss.MUY[MADTwiss.indx['MKQA.6L4.'+oa[3:]]]  #-- B1 direction for B2
        psi_ac2bpmac2=MADTwiss.MUY[MADTwiss.indx[bpmac2]]-MADTwiss.MUY[MADTwiss.indx['MKQA.6L4.'+oa[3:]]]  #-- B1 direction for B2

    r=sin(np.pi*(Qd-Q))/sin(np.pi*(Qd+Q))
    psid_ac2bpmac1=np.arctan((1+r)/(1-r)*tan(2*np.pi*psi_ac2bpmac1-np.pi*Q))%np.pi-np.pi+np.pi*Qd
    psid_ac2bpmac2=np.arctan((1+r)/(1-r)*tan(2*np.pi*psi_ac2bpmac2+np.pi*Q))%np.pi-np.pi*Qd

    return {bpmac1:psid_ac2bpmac1,bpmac2:psid_ac2bpmac2}


def GetFreePhaseTotal_Eq(MADTwiss,Files,Qd,Q,psid_ac2bpmac,plane,bd,op):

    #-- Select common BPMs
    bpm=Utilities.bpm.modelIntersect(Utilities.bpm.intersect(Files),MADTwiss)
    bpm=[(b[0],string.upper(b[1])) for b in bpm]

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if op=="1" and bd== 1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    if op=="1" and bd==-1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    #-- Determine the BPM closest to the AC dipole and its position
    for b in psid_ac2bpmac.keys():
        if '5L4' in b: bpmac1=b
        if '6L4' in b: bpmac2=b
    try:
        k_bpmac=list(zip(*bpm)[1]).index(bpmac1)
        bpmac=bpmac1
    except:
        try:
            k_bpmac=list(zip(*bpm)[1]).index(bpmac2)
            bpmac=bpmac2
        except:
            return [{},[]]

    #-- Model phase advances
    if plane=='H': psimdl=np.array([(MADTwiss.MUX[MADTwiss.indx[b[1]]]-MADTwiss.MUX[MADTwiss.indx[bpm[0][1]]])%1 for b in bpm])
    if plane=='V': psimdl=np.array([(MADTwiss.MUY[MADTwiss.indx[b[1]]]-MADTwiss.MUY[MADTwiss.indx[bpm[0][1]]])%1 for b in bpm])

    #-- Global parameters of the driven motion
    r=sin(np.pi*(Qd-Q))/sin(np.pi*(Qd+Q))

    #-- Loop for files, psid, Psi, Psid are w.r.t the AC dipole
    psiall=np.zeros((len(bpm),len(Files)))
    for i in range(len(Files)):
        if plane=='H': psid=bd*2*np.pi*np.array([Files[i].MUX[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        if plane=='V': psid=bd*2*np.pi*np.array([Files[i].MUY[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        for k in range(len(bpm)):
            try:
                if bpm[k][0]>s_lastbpm: psid[k]+=2*np.pi*Qd  #-- To fix the phase shift by Q
            except: pass
        psid=psid-(psid[k_bpmac]-psid_ac2bpmac[bpmac])
        Psid=psid+np.pi*Qd
        Psid[k_bpmac:]=Psid[k_bpmac:]-2*np.pi*Qd
        Psi=np.arctan((1-r)/(1+r)*np.tan(Psid))%np.pi
        for k in range(len(bpm)):
            if Psid[k]%(2*np.pi)>np.pi: Psi[k]=Psi[k]+np.pi
        psi=Psi-Psi[0]
        psi[k_bpmac:]=psi[k_bpmac:]+2*np.pi*Q
        for k in range(len(bpm)): psiall[k][i]=psi[k]/(2*np.pi)  #-- phase range back to [0,1)

    #-- Output
    result={}
    for k in range(len(bpm)):
        psiave=PhaseMean(psiall[k],1)
        psistd=PhaseStd(psiall[k],1)
        result[bpm[k][1]]=[psiave,psistd,psimdl[k],bpm[0][1]]

    return [result,bpm]


def GetFreePhase_Eq(MADTwiss,Files,Qd,Q,psid_ac2bpmac,plane,bd,op):

    #-- Select common BPMs
    bpm=Utilities.bpm.modelIntersect(Utilities.bpm.intersect(Files),MADTwiss)
    bpm=[(b[0],string.upper(b[1])) for b in bpm]

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if op=="1" and bd== 1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    if op=="1" and bd==-1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    #-- Determine the position of the AC dipole BPM
    for b in psid_ac2bpmac.keys():
        if '5L4' in b: bpmac1=b
        if '6L4' in b: bpmac2=b
    try:
        k_bpmac=list(zip(*bpm)[1]).index(bpmac1)
        bpmac=bpmac1
    except:
        try:
            k_bpmac=list(zip(*bpm)[1]).index(bpmac2)
            bpmac=bpmac2
        except:
            print >> sys.stderr,'WARN: BPMs next to AC dipoles missing. AC dipole effects not calculated for '+plane+' with eqs !'
            return [{},'',[]]

    #-- Model phase advances
    if plane=='H': psimdl=np.array([MADTwiss.MUX[MADTwiss.indx[b[1]]] for b in bpm])
    if plane=='V': psimdl=np.array([MADTwiss.MUY[MADTwiss.indx[b[1]]] for b in bpm])
    psi12mdl=(np.append(psimdl[1:],psimdl[0] +Q)-psimdl)%1
    psi13mdl=(np.append(psimdl[2:],psimdl[:2]+Q)-psimdl)%1
    psi14mdl=(np.append(psimdl[3:],psimdl[:3] +Q)-psimdl)%1
    psi15mdl=(np.append(psimdl[4:],psimdl[:4] +Q)-psimdl)%1
    psi16mdl=(np.append(psimdl[5:],psimdl[:5] +Q)-psimdl)%1
    psi17mdl=(np.append(psimdl[6:],psimdl[:6] +Q)-psimdl)%1

    #-- Global parameters of the driven motion
    r=sin(np.pi*(Qd-Q))/sin(np.pi*(Qd+Q))

    #-- Loop for files, psid, Psi, Psid are w.r.t the AC dipole
    psi12all=np.zeros((len(bpm),len(Files)))
    psi13all=np.zeros((len(bpm),len(Files)))
    psi14all=np.zeros((len(bpm),len(Files)))
    psi15all=np.zeros((len(bpm),len(Files)))
    psi16all=np.zeros((len(bpm),len(Files)))
    psi17all=np.zeros((len(bpm),len(Files)))
    for i in range(len(Files)):
        if plane=='H': psid=bd*2*np.pi*np.array([Files[i].MUX[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        if plane=='V': psid=bd*2*np.pi*np.array([Files[i].MUY[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        for k in range(len(bpm)):
            try:
                if bpm[k][0]>s_lastbpm: psid[k]+=2*np.pi*Qd  #-- To fix the phase shift by Q
            except: pass
        psid=psid-(psid[k_bpmac]-psid_ac2bpmac[bpmac])
        Psid=psid+np.pi*Qd
        Psid[k_bpmac:]=Psid[k_bpmac:]-2*np.pi*Qd
        Psi=np.arctan((1-r)/(1+r)*np.tan(Psid))%np.pi
        for k in range(len(bpm)):
            if Psid[k]%(2*np.pi)>np.pi: Psi[k]=Psi[k]+np.pi
        psi=Psi-Psi[0]
        psi[k_bpmac:]=psi[k_bpmac:]+2*np.pi*Q
        psi12=(np.append(psi[1:],psi[0] +2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        #psi12=(np.append(psi[1:],psi[0])-psi)/(2*np.pi*)  #-- phase range back to [0,1)
        psi13=(np.append(psi[2:],psi[:2]+2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        psi14=(np.append(psi[3:],psi[:3]+2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        psi15=(np.append(psi[4:],psi[:4]+2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        psi16=(np.append(psi[5:],psi[:5]+2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        psi17=(np.append(psi[6:],psi[:6]+2*np.pi*Q)-psi)/(2*np.pi)  #-- phase range back to [0,1)
        for k in range(len(bpm)):
            psi12all[k][i]=psi12[k]
            psi13all[k][i]=psi13[k]
            psi14all[k][i]=psi14[k]
            psi15all[k][i]=psi15[k]
            psi16all[k][i]=psi16[k]
            psi17all[k][i]=psi17[k]

    #-- Output
    result={}
    muave=0.0  #-- mu is the same as psi but w/o mod
    for k in range(len(bpm)):
        psi12ave=PhaseMean(psi12all[k],1)
        psi12std=PhaseStd(psi12all[k],1)
        psi13ave=PhaseMean(psi13all[k],1)
        psi13std=PhaseStd(psi13all[k],1)
        psi14ave=PhaseMean(psi14all[k],1)
        psi14std=PhaseStd(psi14all[k],1)
        psi15ave=PhaseMean(psi15all[k],1)
        psi15std=PhaseStd(psi15all[k],1)
        psi16ave=PhaseMean(psi16all[k],1)
        psi16std=PhaseStd(psi16all[k],1)
        psi17ave=PhaseMean(psi17all[k],1)
        psi17std=PhaseStd(psi17all[k],1)
        muave=muave+psi12ave
        try:    result[bpm[k][1]]=[psi12ave,psi12std,psi13ave,psi13std,psi12mdl[k],psi13mdl[k],bpm[k+1][1]]
        except: result[bpm[k][1]]=[psi12ave,psi12std,psi13ave,psi13std,psi12mdl[k],psi13mdl[k],bpm[0][1]]    #-- The last BPM

        bn1 = string.upper(bpm[k%len(bpm)][1])
        bn2 = string.upper(bpm[(k+1)%len(bpm)][1])
        bn3 = string.upper(bpm[(k+2)%len(bpm)][1])
        bn4 = string.upper(bpm[(k+3)%len(bpm)][1])
        bn5 = string.upper(bpm[(k+4)%len(bpm)][1])
        bn6 = string.upper(bpm[(k+5)%len(bpm)][1])
        bn7 = string.upper(bpm[(k+6)%len(bpm)][1])

        if plane=='H':
            result["".join(['H',bn1,bn2])] = [psi12ave,psi12std,psi12mdl[k]]
            result["".join(['H',bn1,bn3])] = [psi13ave,psi13std,psi13mdl[k]]
            result["".join(['H',bn1,bn4])] = [psi14ave,psi14std,psi14mdl[k]]
            result["".join(['H',bn1,bn5])] = [psi15ave,psi15std,psi15mdl[k]]
            result["".join(['H',bn1,bn6])] = [psi16ave,psi16std,psi16mdl[k]] 
            result["".join(['H',bn1,bn7])] = [psi17ave,psi17std,psi17mdl[k]]
        elif plane=='V':
            result["".join(['V',bn1,bn2])] = [psi12ave,psi12std,psi12mdl[k]]    
            result["".join(['V',bn1,bn3])] = [psi13ave,psi13std,psi13mdl[k]]
            result["".join(['V',bn1,bn4])] = [psi14ave,psi14std,psi14mdl[k]]
            result["".join(['V',bn1,bn5])] = [psi15ave,psi15std,psi15mdl[k]]
            result["".join(['V',bn1,bn6])] = [psi16ave,psi16std,psi16mdl[k]]
            result["".join(['V',bn1,bn7])] = [psi17ave,psi17std,psi17mdl[k]]

    return [result,muave,bpm]


def GetFreeBetaFromAmp_Eq(MADTwiss_ac,Files,Qd,Q,psid_ac2bpmac,plane,bd,op):

    #-- Select common BPMs
    bpm = Utilities.bpm.modelIntersect(Utilities.bpm.intersect(Files),MADTwiss_ac)
    bpm = [(b[0],string.upper(b[1])) for b in bpm]

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if op=="1" and bd==1: 
        s_lastbpm=MADTwiss_ac.S[MADTwiss_ac.indx['BPMSW.1L2.B1']]
    if op=="1" and bd==-1: 
        s_lastbpm=MADTwiss_ac.S[MADTwiss_ac.indx['BPMSW.1L8.B2']]

    #-- Determine the BPM closest to the AC dipole and its position
    for b in psid_ac2bpmac.keys():
        if '5L4' in b: 
            bpmac1=b
        if '6L4' in b: 
            bpmac2=b
    try:
        k_bpmac=list(zip(*bpm)[1]).index(bpmac1)
        bpmac=bpmac1
    except:
        try:
            k_bpmac=list(zip(*bpm)[1]).index(bpmac2)
            bpmac=bpmac2
        except ValueError:
            print >> sys.stderr,'WARN: BPMs next to AC dipoles missing.'
            return [{},'',[],[]]

    #-- Model beta and phase advance
    if plane=='H': betmdl=np.array([MADTwiss_ac.BETX[MADTwiss_ac.indx[b[1]]] for b in bpm])
    if plane=='V': betmdl=np.array([MADTwiss_ac.BETY[MADTwiss_ac.indx[b[1]]] for b in bpm])

    #-- Global parameters of the driven motion
    r=sin(np.pi*(Qd-Q))/sin(np.pi*(Qd+Q))

    #-- Loop for files
    betall=np.zeros((len(bpm),len(Files)))
    Adall=np.zeros((len(bpm),len(Files)))
    for i in range(len(Files)):
        if plane=='H':
            amp =np.array([2*Files[i].AMPX[Files[i].indx[b[1]]] for b in bpm])
            psid=bd*2*np.pi*np.array([Files[i].MUX[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        if plane=='V':
            amp =np.array([2*Files[i].AMPY[Files[i].indx[b[1]]] for b in bpm])
            psid=bd*2*np.pi*np.array([Files[i].MUY[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        for k in range(len(bpm)):
            try:
                if bpm[k][0]>s_lastbpm: psid[k]+=2*np.pi*Qd  #-- To fix the phase shift by Q
            except: pass
        Ad  =amp/map(math.sqrt,betmdl)
        psid=psid-(psid[k_bpmac]-psid_ac2bpmac[bpmac])
        Psid=psid+np.pi*Qd
        Psid[k_bpmac:]=Psid[k_bpmac:]-2*np.pi*Qd
        bet =(amp/np.mean(Ad))**2*(1+r**2+2*r*np.cos(2*Psid))/(1-r**2)
        for k in range(len(bpm)):
            betall[k][i]=bet[k]
            Adall[k][i]=Ad[k]

    #-- Output
    result={}
    bb=[]
    Adave=[]
    for k in range(len(bpm)):
        betave=np.mean(betall[k])
        betstd=math.sqrt(np.mean((betall[k]-betave)**2))
        bb.append((betave-betmdl[k])/betmdl[k])
        Adave.append(np.mean(Adall[k]))
        result[bpm[k][1]]=[betave,betstd,bpm[k][0]]
    bb=math.sqrt(np.mean(np.array(bb)**2))
    Ad=[np.mean(Adave),math.sqrt(np.mean((Adave-np.mean(Adave))**2))]

    return [result,bb,bpm,Ad]


def GetFreeCoupling_Eq(MADTwiss,FilesX,FilesY,Qh,Qv,Qx,Qy,psih_ac2bpmac,psiv_ac2bpmac,bd):

    #-- Details of this algorithms is in http://www.agsrhichome.bnl.gov/AP/ap_notes/ap_note_410.pdf

    #-- Check linx/liny files, may be redundant
    if len(FilesX)!=len(FilesY): return [{},[]]

    #-- Select common BPMs
    bpm=Utilities.bpm.modelIntersect(Utilities.bpm.intersect(FilesX+FilesY),MADTwiss)
    bpm=[(b[0],string.upper(b[1])) for b in bpm]

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    #if op=="1" and bd== 1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    #if op=="1" and bd==-1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    #-- Determine the BPM closest to the AC dipole and its position
    for b in psih_ac2bpmac.keys():
        if '5L4' in b: bpmac1=b
        if '6L4' in b: bpmac2=b
    try:
        k_bpmac=list(zip(*bpm)[1]).index(bpmac1)
        bpmac=bpmac1
    except:
        try:
            k_bpmac=list(zip(*bpm)[1]).index(bpmac2)
            bpmac=bpmac2
        except:
            print >> sys.stderr,'WARN: BPMs next to AC dipoles missing. AC dipole effects not calculated with analytic eqs for coupling'
            return [{},[]]

    #-- Global parameters of the driven motion
    dh =Qh-Qx
    dv =Qv-Qy
    rh =sin(np.pi*(Qh-Qx))/sin(np.pi*(Qh+Qx))
    rv =sin(np.pi*(Qv-Qy))/sin(np.pi*(Qv+Qy))
    rch=sin(np.pi*(Qh-Qy))/sin(np.pi*(Qh+Qy))
    rcv=sin(np.pi*(Qx-Qv))/sin(np.pi*(Qx+Qv))

    #-- Loop for files
    f1001Abs =np.zeros((len(bpm),len(FilesX)))
    f1010Abs =np.zeros((len(bpm),len(FilesX)))
    f1001xArg=np.zeros((len(bpm),len(FilesX)))
    f1001yArg=np.zeros((len(bpm),len(FilesX)))
    f1010xArg=np.zeros((len(bpm),len(FilesX)))
    f1010yArg=np.zeros((len(bpm),len(FilesX)))
    for i in range(len(FilesX)):

        #-- Read amplitudes and phases
        amph  =     np.array([FilesX[i].AMPX[FilesX[i].indx[b[1]]]    for b in bpm])
        ampv  =     np.array([FilesY[i].AMPY[FilesY[i].indx[b[1]]]    for b in bpm])
        amph01=     np.array([FilesX[i].AMP01[FilesX[i].indx[b[1]]]   for b in bpm])
        ampv10=     np.array([FilesY[i].AMP10[FilesY[i].indx[b[1]]]   for b in bpm])
        psih  =2*np.pi*np.array([FilesX[i].MUX[FilesX[i].indx[b[1]]]     for b in bpm])
        psiv  =2*np.pi*np.array([FilesY[i].MUY[FilesY[i].indx[b[1]]]     for b in bpm])
        psih01=2*np.pi*np.array([FilesX[i].PHASE01[FilesX[i].indx[b[1]]] for b in bpm])
        psiv10=2*np.pi*np.array([FilesY[i].PHASE10[FilesY[i].indx[b[1]]] for b in bpm])
        #-- I'm not sure this is correct for the coupling so I comment out this part for now (by RM 9/30/11).
        #for k in range(len(bpm)):
        #       try:
        #               if bpm[k][0]>s_lastbpm:
        #                       psih[k]  +=bd*2*np.pi*Qh  #-- To fix the phase shift by Qh
        #                       psiv[k]  +=bd*2*np.pi*Qv  #-- To fix the phase shift by Qv
        #                       psih01[k]+=bd*2*np.pi*Qv  #-- To fix the phase shift by Qv
        #                       psiv10[k]+=bd*2*np.pi*Qh  #-- To fix the phase shift by Qh
        #       except: pass

        #-- Construct Fourier components
        #   * be careful for that the note is based on x+i(alf*x*bet*x')).
        #   * Calculating Eqs (87)-(92) by using Eqs (47) & (48) (but in the Fourier space) in the note.
        #   * Note that amph(v)01 is normalized by amph(v) and it is un-normalized in the following.
        dpsih  =np.append(psih[1:]  ,2*np.pi*Qh+psih[0]  )-psih
        dpsiv  =np.append(psiv[1:]  ,2*np.pi*Qv+psiv[0]  )-psiv
        dpsih01=np.append(psih01[1:],2*np.pi*Qv+psih01[0])-psih01
        dpsiv10=np.append(psiv10[1:],2*np.pi*Qh+psiv10[0])-psiv10

        X_m10=2*amph*np.exp(-1j*psih)
        Y_0m1=2*ampv*np.exp(-1j*psiv)
        X_0m1=amph*np.exp(-1j*psih01)/(1j*sin(dpsih))*(amph01*np.exp(1j*dpsih)-np.append(amph01[1:],amph01[0])*np.exp(-1j*dpsih01))
        X_0p1=amph*np.exp( 1j*psih01)/(1j*sin(dpsih))*(amph01*np.exp(1j*dpsih)-np.append(amph01[1:],amph01[0])*np.exp( 1j*dpsih01))
        Y_m10=ampv*np.exp(-1j*psiv10)/(1j*sin(dpsiv))*(ampv10*np.exp(1j*dpsiv)-np.append(ampv10[1:],ampv10[0])*np.exp(-1j*dpsiv10))
        Y_p10=ampv*np.exp( 1j*psiv10)/(1j*sin(dpsiv))*(ampv10*np.exp(1j*dpsiv)-np.append(ampv10[1:],ampv10[0])*np.exp( 1j*dpsiv10))

        #-- Construct f1001hv, f1001vh, f1010hv (these include math.sqrt(betv/beth) or math.sqrt(beth/betv))
        f1001hv=-np.conjugate(1/(2j)*Y_m10/X_m10)  #-- - sign from the different def
        f1001vh=-1/(2j)*X_0m1/Y_0m1             #-- - sign from the different def
        f1010hv=-1/(2j)*Y_p10/np.conjugate(X_m10)  #-- - sign from the different def
        f1010vh=-1/(2j)*X_0p1/np.conjugate(Y_0m1)  #-- - sign from the different def
##              f1001hv=conjugate(1/(2j)*Y_m10/X_m10)
##              f1001vh=1/(2j)*X_0m1/Y_0m1
##              f1010hv=1/(2j)*Y_p10/conjugate(X_m10)
##              f1010vh=1/(2j)*X_0p1/conjugate(Y_0m1)

        #-- Construct phases psih, psiv, Psih, Psiv w.r.t. the AC dipole
        psih=psih-(psih[k_bpmac]-psih_ac2bpmac[bpmac])
        psiv=psiv-(psiv[k_bpmac]-psiv_ac2bpmac[bpmac])

        Psih=psih-np.pi*Qh
        Psih[:k_bpmac]=Psih[:k_bpmac]+2*np.pi*Qh
        Psiv=psiv-np.pi*Qv
        Psiv[:k_bpmac]=Psiv[:k_bpmac]+2*np.pi*Qv

        Psix=np.arctan((1-rh)/(1+rh)*np.tan(Psih))%np.pi
        Psiy=np.arctan((1-rv)/(1+rv)*np.tan(Psiv))%np.pi
        for k in range(len(bpm)):
            if Psih[k]%(2*np.pi)>np.pi: Psix[k]=Psix[k]+np.pi
            if Psiv[k]%(2*np.pi)>np.pi: Psiy[k]=Psiy[k]+np.pi

        psix=Psix-np.pi*Qx
        psix[k_bpmac:]=psix[k_bpmac:]+2*np.pi*Qx
        psiy=Psiy-np.pi*Qy
        psiy[k_bpmac:]=psiy[k_bpmac:]+2*np.pi*Qy

        #-- Construct f1001h, f1001v, f1010h, f1010v (these include math.sqrt(betv/beth) or math.sqrt(beth/betv))
        f1001h=1/math.sqrt(1-rv**2)*(np.exp(-1j*(Psiv-Psiy))*f1001hv+rv*np.exp( 1j*(Psiv+Psiy))*f1010hv)
        f1010h=1/math.sqrt(1-rv**2)*(np.exp( 1j*(Psiv-Psiy))*f1010hv+rv*np.exp(-1j*(Psiv+Psiy))*f1001hv)
        f1001v=1/math.sqrt(1-rh**2)*(np.exp( 1j*(Psih-Psix))*f1001vh+rh*np.exp(-1j*(Psih+Psix))*np.conjugate(f1010vh))
        f1010v=1/math.sqrt(1-rh**2)*(np.exp( 1j*(Psih-Psix))*f1010vh+rh*np.exp(-1j*(Psih+Psix))*np.conjugate(f1001vh))

        #-- Construct f1001 and f1010 from h and v BPMs (these include math.sqrt(betv/beth) or math.sqrt(beth/betv))
        g1001h          =np.exp(-1j*((psih-psih[k_bpmac])-(psiy-psiy[k_bpmac])))*(ampv/amph*amph[k_bpmac]/ampv[k_bpmac])*f1001h[k_bpmac]
        g1001h[:k_bpmac]=1/(np.exp(2*np.pi*1j*(Qh-Qy))-1)*(f1001h-g1001h)[:k_bpmac]
        g1001h[k_bpmac:]=1/(1-np.exp(-2*np.pi*1j*(Qh-Qy)))*(f1001h-g1001h)[k_bpmac:]

        g1010h          =np.exp(-1j*((psih-psih[k_bpmac])+(psiy-psiy[k_bpmac])))*(ampv/amph*amph[k_bpmac]/ampv[k_bpmac])*f1010h[k_bpmac]
        g1010h[:k_bpmac]=1/(np.exp(2*np.pi*1j*(Qh+Qy))-1)*(f1010h-g1010h)[:k_bpmac]
        g1010h[k_bpmac:]=1/(1-np.exp(-2*np.pi*1j*(Qh+Qy)))*(f1010h-g1010h)[k_bpmac:]

        g1001v          =np.exp(-1j*((psix-psix[k_bpmac])-(psiv-psiv[k_bpmac])))*(amph/ampv*ampv[k_bpmac]/amph[k_bpmac])*f1001v[k_bpmac]
        g1001v[:k_bpmac]=1/(np.exp(2*np.pi*1j*(Qx-Qv))-1)*(f1001v-g1001v)[:k_bpmac]
        g1001v[k_bpmac:]=1/(1-np.exp(-2*np.pi*1j*(Qx-Qv)))*(f1001v-g1001v)[k_bpmac:]

        g1010v          =np.exp(-1j*((psix-psix[k_bpmac])+(psiv-psiv[k_bpmac])))*(amph/ampv*ampv[k_bpmac]/amph[k_bpmac])*f1010v[k_bpmac]
        g1010v[:k_bpmac]=1/(np.exp(2*np.pi*1j*(Qx+Qv))-1)*(f1010v-g1010v)[:k_bpmac]
        g1010v[k_bpmac:]=1/(1-np.exp(-2*np.pi*1j*(Qx+Qv)))*(f1010v-g1010v)[k_bpmac:]

        f1001x=np.exp(1j*(psih-psix))*f1001h
        f1001x=f1001x-rh*np.exp(-1j*(psih+psix))/rch*np.conjugate(f1010h)
        f1001x=f1001x-2j*sin(np.pi*dh)*np.exp(1j*(Psih-Psix))*g1001h
        f1001x=f1001x-2j*sin(np.pi*dh)*np.exp(-1j*(Psih+Psix))/rch*np.conjugate(g1010h)
        f1001x=1/math.sqrt(1-rh**2)*sin(np.pi*(Qh-Qy))/sin(np.pi*(Qx-Qy))*f1001x

        f1010x=np.exp(1j*(psih-psix))*f1010h
        f1010x=f1010x-rh*np.exp(-1j*(psih+psix))*rch*np.conjugate(f1001h)
        f1010x=f1010x-2j*sin(np.pi*dh)*np.exp(1j*(Psih-Psix))*g1010h
        f1010x=f1010x-2j*sin(np.pi*dh)*np.exp(-1j*(Psih+Psix))*rch*np.conjugate(g1001h)
        f1010x=1/math.sqrt(1-rh**2)*sin(np.pi*(Qh+Qy))/sin(np.pi*(Qx+Qy))*f1010x

        f1001y=np.exp(-1j*(psiv-psiy))*f1001v
        f1001y=f1001y+rv*np.exp(1j*(psiv+psiy))/rcv*f1010v
        f1001y=f1001y+2j*sin(np.pi*dv)*np.exp(-1j*(Psiv-Psiy))*g1001v
        f1001y=f1001y-2j*sin(np.pi*dv)*np.exp(1j*(Psiv+Psiy))/rcv*g1010v
        f1001y=1/math.sqrt(1-rv**2)*sin(np.pi*(Qx-Qv))/sin(np.pi*(Qx-Qy))*f1001y

        f1010y=np.exp(1j*(psiv-psiy))*f1010v
        f1010y=f1010y+rv*np.exp(-1j*(psiv+psiy))*rcv*f1001v
        f1010y=f1010y-2j*sin(np.pi*dv)*np.exp(1j*(Psiv-Psiy))*g1010v
        f1010y=f1010y+2j*sin(np.pi*dv)*np.exp(-1j*(Psiv+Psiy))*rcv*g1001v
        f1010y=1/math.sqrt(1-rv**2)*sin(np.pi*(Qx+Qv))/sin(np.pi*(Qx+Qy))*f1010y

        #-- For B2, must be double checked
        if bd == -1:
            f1001x=-np.conjugate(f1001x)
            f1001y=-np.conjugate(f1001y)
            f1010x=-np.conjugate(f1010x)
            f1010y=-np.conjugate(f1010y)

        #-- Separate to amplitudes and phases, amplitudes averaged to cancel math.sqrt(betv/beth) and math.sqrt(beth/betv)
        for k in range(len(bpm)):
            f1001Abs[k][i] =math.sqrt(abs(f1001x[k]*f1001y[k]))
            f1010Abs[k][i] =math.sqrt(abs(f1010x[k]*f1010y[k]))
            f1001xArg[k][i]=np.angle(f1001x[k])%(2*np.pi)
            f1001yArg[k][i]=np.angle(f1001y[k])%(2*np.pi)
            f1010xArg[k][i]=np.angle(f1010x[k])%(2*np.pi)
            f1010yArg[k][i]=np.angle(f1010y[k])%(2*np.pi)

    #-- Output
    fwqw={}
    goodbpm=[]
    for k in range(len(bpm)):

        #-- Bad BPM flag based on phase
        badbpm=0
        f1001xArgAve=PhaseMean(f1001xArg[k],2*np.pi)
        f1001yArgAve=PhaseMean(f1001yArg[k],2*np.pi)
        f1010xArgAve=PhaseMean(f1010xArg[k],2*np.pi)
        f1010yArgAve=PhaseMean(f1010yArg[k],2*np.pi)
        if min(abs(f1001xArgAve-f1001yArgAve),2*np.pi-abs(f1001xArgAve-f1001yArgAve))>np.pi/2: badbpm=1
        if min(abs(f1010xArgAve-f1010yArgAve),2*np.pi-abs(f1010xArgAve-f1010yArgAve))>np.pi/2: badbpm=1

        #-- Output
        if badbpm==0:
            f1001AbsAve=np.mean(f1001Abs[k])
            f1010AbsAve=np.mean(f1010Abs[k])
            f1001ArgAve=PhaseMean(np.append(f1001xArg[k],f1001yArg[k]),2*np.pi)
            f1010ArgAve=PhaseMean(np.append(f1010xArg[k],f1010yArg[k]),2*np.pi)
            f1001Ave   =f1001AbsAve*np.exp(1j*f1001ArgAve)
            f1010Ave   =f1010AbsAve*np.exp(1j*f1010ArgAve)
            f1001AbsStd=math.sqrt(np.mean((f1001Abs[k]-f1001AbsAve)**2))
            f1010AbsStd=math.sqrt(np.mean((f1010Abs[k]-f1010AbsAve)**2))
            f1001ArgStd=PhaseStd(np.append(f1001xArg[k],f1001yArg[k]),2*np.pi)
            f1010ArgStd=PhaseStd(np.append(f1010xArg[k],f1010yArg[k]),2*np.pi)
            fwqw[bpm[k][1]]=[[f1001Ave          ,f1001AbsStd       ,f1010Ave          ,f1010AbsStd       ],
                             [f1001ArgAve/(2*np.pi),f1001ArgStd/(2*np.pi),f1010ArgAve/(2*np.pi),f1010ArgStd/(2*np.pi)]]  #-- Phases renormalized to [0,1)
            goodbpm.append(bpm[k])

    #-- Global parameters not implemented yet
    fwqw['Global']=['"null"','"null"']

    return [fwqw,goodbpm]

def GetFreeIP2_Eq(MADTwiss,Files,Qd,Q,psid_ac2bpmac,plane,bd,oa,op):

    #-- Common BPMs
    bpm = Utilities.bpm.modelIntersect(Utilities.bpm.intersect(Files),MADTwiss)
    bpm=[(b[0],string.upper(b[1])) for b in bpm]

    #-- Last BPM on the same turn to fix the phase shift by Q for exp data of LHC
    if op=="1" and bd== 1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L2.B1']]
    if op=="1" and bd==-1: s_lastbpm=MADTwiss.S[MADTwiss.indx['BPMSW.1L8.B2']]

    #-- Determine the BPM closest to the AC dipole and its position
    for b in psid_ac2bpmac.keys():
        if '5L4' in b: bpmac1=b
        if '6L4' in b: bpmac2=b
    try:
        k_bpmac=list(zip(*bpm)[1]).index(bpmac1)
        bpmac=bpmac1
    except:
        try:
            k_bpmac=list(zip(*bpm)[1]).index(bpmac2)
            bpmac=bpmac2
        except:
            return [{},[]]

    #-- Global parameters of the driven motion
    r=sin(np.pi*(Qd-Q))/sin(np.pi*(Qd+Q))

    #-- Determine Psid (w.r.t the AC dipole) for each file
    Psidall=[]
    for i in range(len(Files)):
        if plane=='H': psid=bd*2*np.pi*np.array([Files[i].MUX[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        if plane=='V': psid=bd*2*np.pi*np.array([Files[i].MUY[Files[i].indx[b[1]]] for b in bpm])  #-- bd flips B2 phase to B1 direction
        for k in range(len(bpm)):
            try:
                if bpm[k][0]>s_lastbpm: psid[k]+=2*np.pi*Qd  #-- To fix the phase shift by Q
            except: pass
        psid=psid-(psid[k_bpmac]-psid_ac2bpmac[bpmac])
        Psid=psid+np.pi*Qd
        Psid[k_bpmac:]=Psid[k_bpmac:]-2*np.pi*Qd
        Psidall.append(Psid)

    #-- Loop for IPs
    result={}
    for ip in ('1','2','5','8'):

        bpml='BPMSW.1L'+ip+'.'+oa[3:]
        bpmr='BPMSW.1R'+ip+'.'+oa[3:]
        if (bpml in zip(*bpm)[1]) and (bpmr in zip(*bpm)[1]):

            #-- Model values
            L=0.5*(MADTwiss.S[MADTwiss.indx[bpmr]]-MADTwiss.S[MADTwiss.indx[bpml]])
            if L<0: L+=0.5*MADTwiss.LENGTH
            if plane=='H':
                betlmdl=MADTwiss.BETX[MADTwiss.indx[bpml]]
                alflmdl=MADTwiss.ALFX[MADTwiss.indx[bpml]]
            if plane=='V':
                betlmdl=MADTwiss.BETY[MADTwiss.indx[bpml]]
                alflmdl=MADTwiss.ALFY[MADTwiss.indx[bpml]]
            betsmdl=betlmdl/(1+alflmdl**2)
            betmdl =betlmdl-2*alflmdl*L+L**2/betsmdl
            alfmdl =alflmdl-L/betsmdl
            dsmdl  =alfmdl*betsmdl

            #-- Measurement for each file
            betall=[]
            alfall=[]
            betsall=[]
            dsall=[]
            rt2Jall=[]
            for i in range(len(Files)):
                try:    #-- Maybe not needed, to avoid like math.sqrt(-...)
                    if plane=='H':
                        al=Files[i].AMPX[Files[i].indx[bpml]]
                        ar=Files[i].AMPX[Files[i].indx[bpmr]]
                    if plane=='V':
                        al=Files[i].AMPY[Files[i].indx[bpml]]
                        ar=Files[i].AMPY[Files[i].indx[bpmr]]
                    Psidl=Psidall[i][list(zip(*bpm)[1]).index(bpml)]
                    Psidr=Psidall[i][list(zip(*bpm)[1]).index(bpmr)]
                    dpsid=Psidr-Psidl

                    #-- betd, alfd, and math.sqrt(2Jd) at BPM_left from amp and phase advance
                    betdl=2*L*al/(ar*sin(dpsid))
                    alfdl=(al-ar*cos(dpsid))/(ar*sin(dpsid))
                    rt2J =math.sqrt(al*ar*sin(dpsid)/(2*L))
                    #-- Convert to free bet and alf
                    betl=(1+r**2+2*r*np.cos(2*Psidl))/(1-r**2)*betdl
                    alfl=((1+r**2+2*r*np.cos(2*Psidl))*alfdl+2*r*sin(2*Psidl))/(1-r**2)
                    #-- Calculate IP parameters
                    bets=betl/(1+alfl**2)
                    bet =betl-2*alfl*L+L**2/bets
                    alf =alfl-L/bets
                    ds  =alf*bets
                    betall.append(bet)
                    alfall.append(alf)
                    betsall.append(bets)
                    dsall.append(ds)
                    rt2Jall.append(rt2J)
                except:
                    pass

            #-- Ave and Std
            betall =np.array(betall) ; betave =np.mean(betall) ; betstd =math.sqrt(np.mean((betall-betave)**2))
            alfall =np.array(alfall) ; alfave =np.mean(alfall) ; alfstd =math.sqrt(np.mean((alfall-alfave)**2))
            betsall=np.array(betsall); betsave=np.mean(betsall); betsstd=math.sqrt(np.mean((betsall-betsave)**2))
            dsall  =np.array(dsall)  ; dsave  =np.mean(dsall)  ; dsstd  =math.sqrt(np.mean((dsall-dsave)**2))
            rt2Jall=np.array(rt2Jall); rt2Jave=np.mean(rt2Jall); rt2Jstd=math.sqrt(np.mean((rt2Jall-rt2Jave)**2))
            result['IP'+ip]=[betave,betstd,betmdl,alfave,alfstd,alfmdl,betsave,betsstd,betsmdl,dsave,dsstd,dsmdl,rt2Jave,rt2Jstd]

    return result

def getkickac(MADTwiss_ac,files,Qh,Qv,Qx,Qy,psih_ac2bpmac,psiv_ac2bpmac,bd,op):

    invarianceJx=[]
    invarianceJy=[]
    tunex       =[]
    tuney       =[]
    tunexRMS    =[]
    tuneyRMS    =[]
    dpp=[]

    for j in range(len(files[0])):

        x=files[0][j]
        y=files[1][j]
        # Since beta,rmsbb,bpms(return_value[:3]) are not used, slice the return value([3]) (vimaier)
        invariantJx = ( GetFreeBetaFromAmp_Eq(MADTwiss_ac,[x],Qh,Qx,psih_ac2bpmac,'H',bd,op) )[3]
        # Since beta,rmsbb,bpms(return_value[:3]) are not used, slice the return value([3]) (vimaier)
        invariantJy = ( GetFreeBetaFromAmp_Eq(MADTwiss_ac,[y],Qv,Qy,psiv_ac2bpmac,'V',bd,op) )[3]
        invarianceJx.append(invariantJx)
        invarianceJy.append(invariantJy)
        try:
            dpp.append(x.DPP)
        except:
            dpp.append(0.0)
        tunex.append(x.Q1)
        tuney.append(y.Q2)
        tunexRMS.append(x.Q1RMS)
        tuneyRMS.append(y.Q2RMS)

    tune   =[tunex,tuney]
    tuneRMS=[tunexRMS,tuneyRMS]

    return [invarianceJx,invarianceJy,tune,tuneRMS,dpp]

######### end ac-dipole stuff



#----------------- end glenn part

#---- Functions for Andy's BetaFromAmp re-scaling

def filterbpm(ListOfBPM):
    '''Filter non-arc BPM'''
    if len(ListOfBPM)==0:
        print >> sys.stderr, "Nothing to filter!!!!"
        sys.exit(1)
    result=[]
    for b in ListOfBPM:
        if ('BPM.' in b[1] or 'bpm.' in b[1]):
            result.append(b)
    return result

def union(a, b):
    ''' return the union of two lists '''
    return list(set(a) | set(b))

def fix_output(outputpath):
    if not os.path.isdir(outputpath):
        os.makedirs(outputpath)
    if '/'!=outputpath[-1]:
        outputpath+='/'
    return outputpath

