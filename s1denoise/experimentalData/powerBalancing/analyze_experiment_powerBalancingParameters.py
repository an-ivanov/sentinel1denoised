import os
import os
import os
import sys
import glob
import datetime
import numpy as np
import matplotlib.pyplot as plt

plt.clf()
plt.figure(figsize=(15,4))

platform = 'S1A'
#platform = 'S1B'
mode = 'EW'
region = 'NA'

# dir path to noise scaling training data
in_path = sys.argv[1]

# import data
npzFilesAll = sorted(glob.glob('%s/%s_%s_GRDM_1SDH_*_powerBalancing.npz' % (in_path, platform, mode)))

# Check quality disclaimer #30 and #31 in https://qc.sentinel1.eo.esa.int/disclaimer/
npzFiles = []
for li, npzFile in enumerate(npzFilesAll):
    startDateTime = datetime.datetime.strptime(os.path.basename(npzFile).split('/')[-1][17:32], "%Y%m%dT%H%M%S")
    endDateTime = datetime.datetime.strptime(os.path.basename(npzFile).split('/')[-1][33:48], "%Y%m%dT%H%M%S")
    if (     platform=='S1A'
         and startDateTime >= datetime.datetime(2018,3,13,1,0,42)
         and endDateTime <= datetime.datetime(2018,3,15,14,1,26) ):
        continue
    elif (     platform=='S1B'
           and startDateTime >= datetime.datetime(2018,3,13,2,43,5)
           and endDateTime <= datetime.datetime(2018,3,15,15,19,30) ):
        continue
    else:
        npzFiles.append(npzFile)
# stack processed files
IPFversion = []
powerDifference = []
balancingPower = []
correlationCoefficient = []
fitResidual = []
acqDate = []
for npzFile in npzFiles:
    print('importing %s' % npzFile)
    npz = np.load(npzFile)
    npz.allow_pickle = True
    numberOfSubblocks = np.unique([ len(npz['EW%s' % iSW].item()['balancingPower'])
                                    for iSW in range(1,6) ])
    if numberOfSubblocks.size != 1:
        print('*** numberOfSubblocks are not consistent for all subswaths.')
        continue
    numberOfSubblocks = numberOfSubblocks.item()
    for li in range(numberOfSubblocks):
        powerDifference.append([
              np.nanmean(10*np.log10(npz['EW%s' % iSW].item()['sigma0'][li]))
            - np.nanmean(10*np.log10(npz['EW%s' % iSW].item()['noiseEquivalentSigma0'][li]))
            for iSW in range(1,6) ])
        balancingPower.append([
            npz['EW%s' % iSW].item()['balancingPower'][li]
            for iSW in range(1,6) ])
        correlationCoefficient.append([
            npz['EW%s' % iSW].item()['correlationCoefficient'][li]
            for iSW in range(1,6) ])
        fitResidual.append([
            npz['EW%s' % iSW].item()['fitResidual'][li]
            for iSW in range(1,6) ])
        IPFversion.append(npz['IPFversion'])
        acqDate.append(datetime.datetime.strptime(os.path.basename(npzFile).split('_')[4], '%Y%m%dT%H%M%S'))

powerDifference = np.array(powerDifference)
balancingPower = np.array(balancingPower)
correlationCoefficient = np.array(correlationCoefficient)
fitResidual = np.array(fitResidual)
IPFversion = np.array(IPFversion)
acqDate = np.array(acqDate)

# compute fit values
powerBalancingParameters = {'EW%s' % li: {} for li in range(1,6)}
powerBalancingParametersRMSE = {'EW%s' % li: {} for li in range(1,6)}
for IPFv in np.arange(2.4, 4.0, 0.1):
    if IPFv==2.7 and platform=='S1B':
        valid = np.logical_and( IPFversion==2.72,
                                acqDate < datetime.datetime(2017,1,16,13,42,34) )
    else:
        valid = np.isclose((np.trunc(IPFversion*10)/10.), IPFv, atol=0.01)
    if valid.sum()==0:
        continue
    pd = np.mean(powerDifference[valid], axis=1)
    cc = np.min(correlationCoefficient[valid], axis=1)
    fr = np.max(fitResidual[valid], axis=1)
    w = cc / fr
    for iSW in range(1,6):
        bp = balancingPower[valid][:,iSW-1]
        fitResults = np.polyfit(pd, bp, deg=0, w=w)
        powerBalancingParameters['EW%s' % iSW]['%.1f' % IPFv] = fitResults[0]
        powerBalancingParametersRMSE['EW%s' % iSW]['%.1f' % IPFv] = np.sqrt(np.sum((fitResults[0]-bp)**2 * w) / np.sum(w))



    if IPFv==2.7 and platform=='S1B':
        valid = np.logical_and( IPFversion==2.72,
                                acqDate < datetime.datetime(2017,1,16,13,42,34) )
    else:
        valid = np.isclose((np.trunc(IPFversion*10)/10.), IPFv, atol=0.01)
    pd = np.mean(powerDifference[valid], axis=1)
    cc = np.min(correlationCoefficient[valid], axis=1)
    fr = np.max(fitResidual[valid], axis=1)
    w = cc / fr
    for iSW in range(1,6):
        bp = balancingPower[valid][:,iSW-1]
        fitResults = np.polyfit(pd, bp, deg=0, w=w)
        plt.subplot(1,5,iSW); plt.hold(0)
        plt.hist2d(bp,pd,bins=100,cmin=1,range=[[-2e-3,+2e-3],[-5,15]])
        plt.hold(1)
        plt.plot(np.polyval(fitResults, np.linspace(-5,+15,2)), np.linspace(-5,+15,2), linewidth=0.5, color='r')
        plt.plot([-2e-3,+2e-3],[0,0], linewidth=0.5, color='k')

# Save a figure with statistics on noise scaling
plt.tight_layout()
plt.savefig('%s_%s_%s_power_balancing.png' % (platform, mode, region), bbox_inches='tight', dpi=600)
