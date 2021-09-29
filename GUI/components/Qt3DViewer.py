from typing import Union

import config
import numpy as np
import pyqtgraph.opengl as gl
from DATA.RSA.components.volume import Volume
from GUI.components import QtMain
from PyQt5.QtGui import QVector3D


class Registrator(object):
    def __init__(self, gl_ins: gl.GLVolumeItem) -> None:
        """A class registrates GLVolumeItem.

        Args:
            gl_ins (gl.GLVolumeItem): A GLVolumeItem to be registrated.
        """

        super().__init__()
        self.gl_instance = gl_ins
        self.scaling_factor = 1. #// If this value is too large, the coordinates will be misaligned, so it is not used here.

        self.x = 0
        self.y = 0
        self.z = 0
        self.angle = 0

        self.x_flip = 1
        self.y_flip = 1
        self.z_flip = 1

    def set_flip_states(self, x_flip: bool, y_flip: bool, z_flip: bool):
        """Flip the GLVolumeItem

        Args:
            x_flip (bool): If True,flip on X axis.
            y_flip (bool): If True,flip on Y axis.
            z_flip (bool): If True,flip on Z axis.
        """

        self.x_flip = -1 if x_flip == True else 1
        self.y_flip = -1 if y_flip == True else 1
        self.z_flip = -1 if z_flip == True else 1

        self.do()

    def do(self, x: int=None, y: int=None, z: int=None, angle: int=None) -> None:
        """Registrate GLVolumeItem with given parameters

        Args:
            x (int, optional): Shift of X direction. Defaults to None.
            y (int, optional): Shift of Y direction. Defaults to None.
            z (int, optional): Shift of Z direction. Defaults to None.
            angle (int, optional): Rotation angle. Defaults to None.

        Note:
            If the arguments is omitted, the previous parameter will be used.
        """
        self.x = x or self.x
        self.y = y or self.y
        self.z = z or self.z
        self.angle = angle or self.angle

        self.gl_instance.resetTransform()
        self.gl_instance.scale(-1*self.z_flip,-1*self.y_flip,-1*self.x_flip)

        pet_ct_volume = self.gl_instance.data
        assert pet_ct_volume is not None

        self.gl_instance.translate(
            self.z_flip*pet_ct_volume.shape[0]//2+self.z, 
            self.y_flip*pet_ct_volume.shape[1]//2+self.y, 
            self.x_flip*pet_ct_volume.shape[2]//2+self.x
        )
        self.gl_instance.rotate(self.angle, 1, 0, 0)
        
class Qt3DViewer(gl.GLViewWidget):
    label = '3D viewer'
    def __init__(self, parent: QtMain):
        super().__init__(parent=parent)
        self.opts['distance'] = 850
        self.opts['elevation'] = -90
        self.opts['azimuth'] = 0
        self.opts['center'] = QVector3D(0,0,0)

        self.ct_volume = None
        self.ct_trace = None
        self.ct_volume_intensity = 1.
        self.ct_trace_intensity = 1.
        self.pet_ct_volume_intensity = 1.

        self.gl_ct_volume = gl.GLVolumeItem(data=None, sliceDensity=1, smooth=True, glOptions='translucent')
        self.gl_ct_volume.scale(-1,-1,-1)
        self.addItem(self.gl_ct_volume)

        self.gl_pet_ct_volume = gl.GLVolumeItem(data=None, sliceDensity=1, smooth=True, glOptions='additive')
        self.addItem(self.gl_pet_ct_volume)

        self.registrator = Registrator(self.gl_pet_ct_volume)
        self.show()

    def set_ct_volume(self, ct_volume: np.ndarray):
        if ct_volume is None:
            self.gl_ct_volume.setData(None)
            return

        self.gl_ct_volume.resetTransform()
        self.gl_ct_volume.scale(-1,-1,-1)

        self.ct_volume = ct_volume[::config.skip_size, ::config.skip_size, ::config.skip_size]
        self.ct_volume_display = np.zeros(self.ct_volume.shape + (4,), dtype=np.ubyte)
        self.gl_ct_volume.translate(self.ct_volume.shape[0]//2, self.ct_volume.shape[1]//2, self.ct_volume.shape[2]//2)
        self.update_ct_volume()

    def set_pet_ct_volume(self, pet_ct_volume: Union[Volume, None]):
        if pet_ct_volume is None:
            self.gl_pet_ct_volume.setData(None)
            return
            
        #scaling_factor = pet_ct_volume.scaling_factor

        self.gl_pet_ct_volume.resetTransform()
        self.gl_pet_ct_volume.scale(-1,-1,-1)

        ndary = pet_ct_volume.ndary
        if ndary is not None:
            self.pet_ct_volume = ndary[::config.skip_size, ::config.skip_size, ::config.skip_size]
            self.pet_ct_volume_display = np.zeros(self.pet_ct_volume.shape + (4,), dtype=np.ubyte)
            self.gl_pet_ct_volume.translate(self.pet_ct_volume.shape[0]//2, self.pet_ct_volume.shape[1]//2, self.pet_ct_volume.shape[2]//2)

        self.update_pet_ct_volume()

    def set_ct_trace(self, ct_trace: np.ndarray):
        if ct_trace is None:
            ct_trace = None
            return

        self.ct_trace = ct_trace[::2, ::2, ::2]
        self.update_ct_volume()

    def ct_volume_intensity_changed(self, intensity: float):
        self.ct_volume_intensity = intensity
        self.update_ct_volume()

    def pet_ct_volume_intensity_changed(self, intensity: float):
        self.pet_ct_volume_intensity = intensity
        self.update_pet_ct_volume()

    def ct_trace_intensity_changed(self, intensity: float):
        self.ct_trace_intensity = intensity
        self.update_ct_volume()

    def update_pet_ct_volume(self):
        try:
            self.pet_ct_volume_display[...,0] = np.clip(self.pet_ct_volume*self.pet_ct_volume_intensity, 0, 255)
            self.pet_ct_volume_display[...,1] = self.pet_ct_volume_display[...,0]
            #self.pet_ct_volume_display[...,2] = self.pet_ct_volume_display[...,0]
            self.pet_ct_volume_display[...,3] = np.clip(((self.pet_ct_volume_display[...,0]).astype(float) / 255.*2) **2 * 255, 0, 255)

            self.gl_pet_ct_volume.setData(self.pet_ct_volume_display)
        except:
            pass
        self.paintGL()

    def update_ct_volume(self):
        self.ct_volume_display[...,0] = np.clip(self.ct_volume*self.ct_volume_intensity, 0, 255)
        self.ct_volume_display[...,1] = self.ct_volume_display[...,0]
        self.ct_volume_display[...,2] = self.ct_volume_display[...,0]
        self.ct_volume_display[...,3] = np.clip(((self.ct_volume_display[...,1]).astype(float) / 255.*2) **2 * 255, 0, 255)

        if self.ct_trace is not None:
            self.ct_volume_display[...,0][self.ct_trace!=0] = np.clip(self.ct_volume[self.ct_trace!=0]*self.ct_trace_intensity, 0, 255)
            self.ct_volume_display[...,1][self.ct_trace!=0] = self.ct_volume_display[...,0][self.ct_trace!=0]
            self.ct_volume_display[...,2][self.ct_trace!=0] = self.ct_volume_display[...,0][self.ct_trace!=0]
            self.ct_volume_display[...,3] = np.clip(((self.ct_volume_display[...,1]).astype(float) / 255.*2) **2 * 255, 0, 255)

        self.gl_ct_volume.setData(self.ct_volume_display)
        self.paintGL()

    def set_scaling_factor(self, scaling_factor: float):
        self.registrator.scaling_factor = scaling_factor
        self.registrator.do()
