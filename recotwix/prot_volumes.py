import os
import numpy as np
import nibabel as nib 
from . import transformation as T
import twixtools.twixprot as twixprot


class volume_orientation:
    _norm = None # [norm_sag, norm_cor, norm_tra]
    _rot = None # inplane rotation (radians)
    _pos = None # offset from origin (mm)
    _fov = None # FoV (mm)
    _res = None # resolution (voxels)
    _thickness = None # slice thickness (mm)
    _affine = None
    _transformation = None    
    _name = None

    def __init__(self, volume_structure=None, res=None, thickness=None, name=None) -> None:
        v = volume_structure
        self._norm = [v['sNormal'].get('dSag',0), v['sNormal'].get('dCor',0), v['sNormal'].get('dTra',0)]
        self._rot = v.get('dInPlaneRot', 0)
        self._pos = [v.get('sPosition', {}).get('dSag',0), v.get('sPosition', {}).get('dCor',0), v.get('sPosition', {}).get('dTra',0)]
        self._fov = {'x':v['dReadoutFOV'], 'y':v['dPhaseFOV'], 'z':v['dThickness']}
        if res is None:
            res = {key: int(value) for key, value in self._fov.items()}
        if thickness is None:
            thickness = self._fov['z'] / res['z']
        # Resampling fails when a volume with res['z'] = 1 is given.
        if res['z'] == 1:
            res['z'] = 3
            thickness = thickness / 3

        self._res = res  
        self._thickness = thickness

        dcm = T.calc_norm2dcm(self._norm[0], self._norm[1], self._norm[2], self._rot)
        self._transformation = T.calc_tranformation_matrix(dcm, self._pos)
        self._affine = T.calc_nifti_affine(self._transformation, self._fov, self._res, self._thickness)
        self._name = name

    def write_nifti(self, filename):
        vol = np.ones(self.shape, dtype=np.uint8)
        img = nib.Nifti1Image(vol, self._affine)
        nib.save(img, filename)

    def data(self):
        return np.ones(self.shape, dtype=np.float32)
            
    @property
    def affine(self):
        return self._affine
    
    @property
    def transformation(self):
        return self._transformation
    
    @property
    def shape(self):
        return (self._res['y'], self._res['x'], self._res['z'])  # swap x and y to match the corresponding affine matrix convention
    
    @property
    def fov(self):
        return (self._fov['y'], self._fov['x'], self._fov['z'])
    

class volume():
    _vol_box = list()
    name = None

    def __init__(self, name=None) -> None:
        self._vol_box = list()
        self.name = name

    def add(self, vol):
        self._vol_box.append(vol)

    def __getitem__(self, index):
        if index >= len(self._vol_box):
            raise IndexError(f'Item out of range. {self.name} volume has only {len(self._vol_box)} items but {index} is asked.')
        return self._vol_box[index]
    
    def __len__(self):
        return len(self._vol_box)
    
    def __iter__(self):
        return iter(self._vol_box)
    

class volume_adjustment(volume):
    def __init__(self, xprot=dict()) -> None:
        super().__init__('adjustment')
        if xprot.get('sAdjData', None) is None:
            return
        if xprot['sAdjData'].get('sAdjVolume', None) is None:
            return
        self.add(volume_orientation(xprot['sAdjData']['sAdjVolume']))


class volume_slice(volume):
    def __init__(self, xprot=dict()) -> None:
        super().__init__('slice')
        if xprot.get('sSliceArray', None) is None:
            return
        if xprot['sSliceArray'].get('asSlice', None) is None:
            return

        res  = {'x':xprot['sKSpace']['lBaseResolution'], 'y':xprot['sKSpace']['lPhaseEncodingLines'], 'z':xprot['sKSpace']['lPartitions']}
        res['z'] = res['z'] if xprot['sKSpace']['ucDimension'] == 4 else 1 # in case of 2D scans, lPartitions is not valid
        positions = list()
        for SlcVol in xprot['sSliceArray']['asSlice']:                      
            self.add(volume_orientation(SlcVol, res=res)) 
            positions.append([SlcVol.get('sPosition', {}).get('dSag',0) , SlcVol.get('sPosition', {}).get('dCor',0) , SlcVol.get('sPosition', {}).get('dTra',0)])
        

class volume_ptx(volume):
    def __init__(self, xprot=dict()) -> None:
        super().__init__('pTx')
        if xprot.get('sPTXData', None) is None:
            return
        if xprot['sPTXData'].get('asPTXVolume', None) is None:
            return
        
        for pTxVol in xprot['sPTXData']['asPTXVolume']:            
            self.add(volume_orientation(pTxVol))  


class prot_volumes:
    xprot = None
    _all_volumes = dict()
    num_volumes = 0

    def __init__(self, param=None) -> None:
        if param is None:
            return
        
        if isinstance(param, dict):
            if param.get('hdr', None) is not None:
                self.xprot = param['hdr']['MeasYaps']
            elif param.get('MeasYaps', None) is not None:
                self.xprot = param['MeasYaps']
            elif param.get('ulVersion', None) is not None:
                self.xprot = param
            else:
                raise ValueError(f'Unknown parameter type: {type(param)}')

        elif os.path.isfile(param):
            with open(param, "r") as my_file:
                str = my_file.read()
                self.xprot = twixprot.parse_buffer(str)
        else:
            raise ValueError(f'Unknown parameter type: {type(param)}')
        
        self._all_volumes = dict()
        self._all_volumes['slc'] = volume_slice(self.xprot)
        self._all_volumes['ptx'] = volume_ptx(self.xprot)
        self._all_volumes['adj'] = volume_adjustment(self.xprot)
        self.num_volumes = sum([len(v) for v in self._all_volumes.values()])

    def get_volume_names(self):
        return [name for name in self._all_volumes.keys() if len(self._all_volumes[name])>0]

    def get(self, volume_name):
        if volume_name in self._all_volumes:
            return self._all_volumes[volume_name] 
        else:
            raise ValueError(f'Unknown volume name: {volume_name}')
        