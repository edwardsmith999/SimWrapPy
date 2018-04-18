#! /usr/bin/env python2.7
import matplotlib.pyplot as plt
import numpy as np
import string
import itertools
import sys
import multiprocessing
import cPickle as pickle

ppdir = '/home/es205/cpl-library-private/utils/'
sys.path.append(ppdir)
import simwraplib as swl
import postproclib as ppl
from misclib import round_to_n

# Number of threads and runs per thread
ncpus = 30
maxlicenses = ncpus

# Inputs that are the same for every thread
srcdir =  '/home/es205/cpl-library-private/flowmol/src/'
basedir = srcdir
executables = './parallel_md.exe'

# Specify information needed for each run
inputfile = 'MD_heat_flux.in'
outputfile = 'MD.out'
finish = [{'final_state':'final_state'}]

# Specify input file changes for each thread 
inputs1 = swl.InputDict({'LIQUIDDENSITY': [0.60,0.65,0.70,0.75,0.85]})
inputs2 = swl.InputDict({'RCUTOFF': [1.12246204830937] })
changes = inputs1*inputs2
filenames = changes.filenames()

threadlist =[]
for thread in range(0,len(changes)):
     rundir = srcdir + '../runs/' + filenames[thread] 

     run = swl.MDRun(
                  srcdir,
                  basedir,
                  rundir,
                  executables,
                  inputfile,
                  outputfile,
                  inputchanges=changes[thread],
                  finishargs = {},
                  dryrun=False
                  )

     runlist = [run]
     threadlist.append(runlist)
     print('Run in directory '  + rundir + ' and dryrun is '  + str(run.dryrun))

# Run the study
#study = swl.Study(threadlist,ncpus)
from pickle_data import pickle_data

normal =1
component=1
load_pickle = False

#Thermostat region 2, tethered 4, binsize 0.7215 so 5.5 are not liquid.
# Call it 8 to be on the safe side
botwall = 8
topwall = -8
skip = 5
for thread in range(0,len(changes)):
    fdir = srcdir + '../runs/' + filenames[thread] + "/results/"
    name = fdir.replace("/home/es205/cpl-library-private/flowmol/src/../runs/","").replace("/results/","")


    #PPObj = ppl.MD_PostProc(fdir)

    #Get plotting object
    q_CVobj = ppl.MD_heatfluxCVField(fdir)
    #q_CVobj = PPObj.plotlist['q_CV']
    qobj = ppl.MD_heatfluxVAField(fdir,fname='hfVA')
    #qobj = PPObj.plotlist['q']
    dTdrobj = ppl.MD_dTdrField(fdir)
    #dTdrobj = PPObj.plotlist['dTdr']

    endrec=q_CVobj.maxrec #1590
    startrec=30 #endrec-int(q_CVobj.maxrec/2.)

    #plot
    fig, ax = plt.subplots(2,1)

    if load_pickle:
        y, q, q_CV, dTdr=pickle.load(open(name+".p",'r'))
    else:
        #Get profile
        y, q = qobj.profile(axis=normal, 
                            startrec=startrec, 
                            endrec=endrec)

        y, q_CV = q_CVobj.profile(axis=normal, 
                                  startrec=startrec, 
                                  endrec=endrec)

        y, dTdr = dTdrobj.profile(axis=normal, 
                                  startrec=startrec, 
                                  endrec=endrec)


    ax[0].plot(y[botwall:topwall],q_CV[botwall:topwall,component],'k-')
    ax[0].plot(y[botwall:topwall:skip],q[botwall:topwall:skip,component],'ko',alpha=0.4)
    ax[0].plot(y[botwall:topwall],dTdr[botwall:topwall,component],'r-')

    k = -np.divide(q[botwall:topwall,component],dTdr[botwall:topwall,component])
    k[np.isnan(k)] = 0.0
    ax[1].plot(y[botwall:topwall],k)

    k_CV = -np.divide(q_CV[botwall:topwall,component],dTdr[botwall:topwall,component]) 
    k_CV[np.isnan(k_CV)] = 0.0
    ax[1].plot(y[botwall:topwall],k_CV)


    print(name, 
          q_CVobj.maxrec, 
          np.mean(k), 
          np.mean(k_CV), 
          np.mean(q[botwall:topwall,component]), 
          np.mean(q_CV[botwall:topwall,component]), 
          np.mean(dTdr[botwall:topwall,component]))

    ax[0].set_ylim([-1.,1.])
    ax[1].set_ylim([-10.,10.])
    
    plt.savefig(name+".png",bbox_inches="tight")

    if not load_pickle:
        pickle.dump([y, q, q_CV, dTdr],open(name+'.p','w'))
    #plt.show()

