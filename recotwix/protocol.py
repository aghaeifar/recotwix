'''
extract important protocol information from twix header
'''
import numpy as np

class protocol_parse():
    is3D = False
    res = {'x':0, 'y':0, 'z':0}
    isParallelImaging = False
    isRefScanSeparate = False
    acceleration_factor = [0, 0]
    isPartialFourierRO = False
    isPartialFourierPE1 = False
    isPartialFourierPE2 = False
    protName = ''
    TR = 0
    TE = 0
    FA = 0
    OS = 0
    coilName = ''
    shims = {'A00':0, 'X':0, 'Y':0, 'Z':0, 'A20':0, 'A21':0, 'B21':0, 'A22':0, 'B22':0, 'A30':0, 'A31':0, 'B31':0, 'A32':0}


    def __init__(self, twix_obj):
        hdr = twix_obj['hdr']
        img = twix_obj['image']

        self.is3D = True if hdr['MeasYaps']['sKSpace']['ucDimension'] == 4 else False

        self.res  = {'x':hdr['MeasYaps']['sKSpace']['lBaseResolution'], 'y':hdr['MeasYaps']['sKSpace']['lPhaseEncodingLines'], 'z':hdr['MeasYaps']['sSliceArray']['lSize']}
        if self.is3D:
            self.res['z'] = hdr['MeasYaps']['sKSpace']['lPartitions']      

        self.isParallelImaging   = True if hdr['MeasYaps']['sPat']['ucPATMode'] == 2 else False
        self.isRefScanSeparate   = True if hdr['MeasYaps']['sPat']['ucRefScanMode'] == 4 else False
        self.acceleration_factor = [hdr['MeasYaps']['sPat']['lAccelFactPE'], hdr['MeasYaps']['sPat']['lAccelFact3D']]
        self.isPartialFourierRO  = True if abs(self.res['x'] - img.shape[img.dims.index('Col')//2]) > 4 else False
        self.isPartialFourierPE1 = True if hdr['MeasYaps']['sKSpace']['ucPhasePartialFourier'] != 16 else False
        self.isPartialFourierPE2 = True if hdr['MeasYaps']['sKSpace']['ucSlicePartialFourier'] != 16 else False   
        self.protName            = hdr['Meas']['tProtocolName']
        self.TR                  = np.array(hdr['Meas']['alTR'][0]) / 1000 # in ms
        self.TE                  = np.array(hdr['Meas']['alTE'])[0:hdr['Meas']['lContrasts']] # in us.
        self.FA                  = np.array(hdr['Meas']['adFlipAngleDegree'][0])
        # self.OS']                  = np.array(hdr['Meas']['alTI']) / 1000 # in ms
        self.coilName            = hdr['MeasYaps']['sCoilSelectMeas']['aRxCoilSelectData'][0]['asList'][0]['sCoilElementID']['tCoilID']
        # read shims
        alShimCurrent = hdr['Phoenix']['sGRADSPEC'].get('alShimCurrent', 0.0)
        self.shims               = {'A00': hdr['MeasYaps']['sTXSPEC']['asNucleusInfo'][0]['lFrequency'],
                                    'X': hdr['Phoenix']['sGRADSPEC'].get('asGPAData', 0.0)[0].get('lOffsetX', 0),
                                    'Y': hdr['Phoenix']['sGRADSPEC'].get('asGPAData', 0.0)[0].get('lOffsetY', 0),
                                    'Z': hdr['Phoenix']['sGRADSPEC'].get('asGPAData', 0.0)[0].get('lOffsetZ', 0),
                                    'A20': alShimCurrent[0] if len(alShimCurrent) > 0 else 0.0,
                                    'A21': alShimCurrent[1] if len(alShimCurrent) > 1 else 0.0,
                                    'B21': alShimCurrent[2] if len(alShimCurrent) > 2 else 0.0,
                                    'A22': alShimCurrent[3] if len(alShimCurrent) > 3 else 0.0,
                                    'B22': alShimCurrent[4] if len(alShimCurrent) > 4 else 0.0,
                                    'A30': alShimCurrent[5] if len(alShimCurrent) > 5 else 0.0,
                                    'A31': alShimCurrent[6] if len(alShimCurrent) > 6 else 0.0,
                                    'B31': alShimCurrent[7] if len(alShimCurrent) > 7 else 0.0,
                                    'A32': alShimCurrent[8] if len(alShimCurrent) > 8 else 0.0}
