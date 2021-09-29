import json
import logging
import os
from copy import deepcopy
from typing import List

import config
import numpy as np
from DATA import File, RSA_Vector, Trace
from DATA.RSA.components.volume import Volume
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QSplitter
from scipy.ndimage import rotate
from skimage import exposure, io, transform

from .Qt3DViewer import Qt3DViewer, Registrator
from .QtOptions import QtOptions
from .QtStatusBar import QtStatusBarW


class GUI_Components(object):
    def __init__(self, parent: 'QtMain'):
        super().__init__()
        self.statusbar = QtStatusBarW(parent=parent)
        self.options = QtOptions(parent=parent)
        self.options.setFixedWidth(300)


class Data(object):
    def __init__(self):
        self.file = File()
        self.ct_volume = Volume()
        self.pet_ct_volume = Volume()
        self.pet_ct_volume_rescaled = Volume()
        self.rinfo = RSA_Vector()
        self.ct_trace = Trace()

    def clear_volumes(self):
        self.ct_volume.clear()
        self.pet_ct_volume.clear()

    def rescale_pet_ct_volume(self):
        ct_resolution = self.ct_volume.resolution
        pet_ct_resolution = self.pet_ct_volume.resolution

        self.pet_ct_volume.scaling_factor = pet_ct_resolution / ct_resolution

        pet_ct_shape = self.pet_ct_volume.shape()
        assert pet_ct_shape is not None
        resized_shape = [int(s*self.pet_ct_volume.scaling_factor) for s in pet_ct_shape]
        rescaled_ndarray = exposure.rescale_intensity(
            transform.resize(self.pet_ct_volume.ndary, resized_shape),
            out_range=np.uint8
        )

        self.pet_ct_volume_rescaled.init_from_volume(rescaled_ndarray)

        return self.pet_ct_volume_rescaled

class QtMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self.GUI_components = GUI_Components(self)

        self.threeD_viewer = Qt3DViewer(parent=self)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(self.threeD_viewer)
        self.main_splitter.addWidget(self.GUI_components.options)
        self.setCentralWidget(self.main_splitter)

        self.resize(800,800)
        self.setAcceptDrops(True)
        self.data = Data()
        
        self.__control_locked = False
        self.setStatusBar(self.GUI_components.statusbar.widget)

        self.GUI_components.options.update_valid_option()
        self.setWindowTitle()

    def dragEnterEvent(self, ev):
        ev.accept()
        
    def dropEvent(self, ev):
        ev.accept()

        flist = [u.toLocalFile() for u in ev.mimeData().urls()]

        if len(flist) != 1 or not os.path.isdir(flist[0]):
            self.logger.error('Only 1 directory at once is acceptable.')
            return

        self.load_from(directory=flist[0])

    def load_from(self, directory: str):
        VolumeFile = File(volume_directory=directory)
        if not VolumeFile.is_valid():
            self.logger.error(f'[Loading error] {directory}')
            self.logger.error(f'At least 64 slice images required.')
            return False

        self.data.clear_volumes()
        self.data.file = VolumeFile
        flist = self.data.file.image_files()
        self.set_control(locked=True)

        self.threeD_viewer.set_ct_volume(None)
        self.threeD_viewer.set_ct_trace(None)
        self.threeD_viewer.set_pet_ct_volume(None)

        self.data.rinfo = RSA_Vector()
        self.data.ct_trace = Trace()

        self.floader = VolumeLoader(flist, progressbar_signal=self.GUI_components.statusbar.pyqtSignal_update_progressbar)
        self.floader.finished.connect(self.on_volume_loaded)
        self.floader.start()

    def on_volume_loaded(self):
        volume = self.floader.data()
        del self.floader

        self.logger.info(f'[Loading succeeded] {self.data.file.directory}')

        self.data.ct_volume.init_from_volume(volume=volume)
        self.data.ct_trace.init_from_volume(volume=volume)
        self.threeD_viewer.set_ct_volume(volume)

        if self.data.file.is_rinfo_file_available():
            ret = QMessageBox.information(None, "Information", "The rinfo file is available. Do you want to import this?", QMessageBox.Yes, QMessageBox.No)
            if ret == QMessageBox.Yes:
                loaded = self.load_rinfo(fname=self.data.file.rinfo_file)
                if loaded:
                    trace_object = self.data.ct_trace.trace3D
                    if trace_object is not None:
                        volume_data = trace_object.volume
                        if volume_data is not None:
                            self.threeD_viewer.set_ct_trace(volume_data[..., 1])
                    
                    self.data.ct_volume.resolution = self.data.rinfo.annotations.resolution()

        if os.path.isdir(self.data.file.pet_directory()):
            ret = QMessageBox.information(None, "Information", "The PET-CT directory is found. Do you want to import this?", QMessageBox.Yes, QMessageBox.No)
            if ret == QMessageBox.Yes:
                pet_file = File(volume_directory=self.data.file.pet_directory())
                if not pet_file.is_valid():
                    self.logger.error(f'[Loading error] {self.data.file.pet_directory()}')
                    self.logger.error(f'At least 64 slice images required.')
                    return False

                pet_volume = [io.imread(f) for f in pet_file.image_files()]
                pet_volume = np.asarray(pet_volume)
                pet_volume = exposure.rescale_intensity(pet_volume, out_range=np.uint8)
                self.data.pet_ct_volume.init_from_volume(pet_volume)
                self.data.pet_ct_volume.resolution = self.data.ct_volume.resolution

                #self.data.rescale_pet_ct_volume()
                self.threeD_viewer.set_pet_ct_volume(self.data.pet_ct_volume)

        self.GUI_components.options.update_valid_option()


        self.set_control(locked=False)
        self.setWindowTitle()
        self.show_default_msg_in_statusbar()

    def setWindowTitle(self):
        text = f'{config.application_name} (version {config.version_string()})'
        if self.data.file.is_valid():
            text += f': {os.path.basename(self.data.file.directory)}'
        super().setWindowTitle(text)

    def set_control(self, locked: bool):
        if self.__control_locked == locked:
            return
            
        self.__control_locked=locked
        self.logger.debug(f'Control locked: {self.__control_locked}')

        if locked:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        else:
            QApplication.restoreOverrideCursor()

    def is_control_locked(self):
        return self.__control_locked

    def show_default_msg_in_statusbar(self):
        if self.data.ct_volume.is_empty():
            msg = 'Open X-ray CT volume files.'
        else:
            msg = 'Opend'
        self.GUI_components.statusbar.set_main_message(msg)

    def load_rinfo_from_dict(self, rinfo_dict: dict, file: str = ""):
        rinfo = self.data.rinfo
        ret = rinfo.load_from_dict(rinfo_dict, file=file)
        if ret == False:
            return False

        base_node = rinfo.base_node(1)
        if base_node is None:
            return False

        total = base_node.child_count()
        for i, root_node in enumerate(base_node.child_nodes()):
            self.GUI_components.statusbar.pyqtSignal_update_progressbar.emit(i, total, 'Making trace volume')
            self.data.ct_trace.draw_trace(root_node=root_node)

        return True

    def load_rinfo(self, fname: str):
        with open(fname, 'r') as f:
            trace_dict = json.load(f)

        return self.load_rinfo_from_dict(trace_dict, file=fname)

    def export_volume(self):
        ct_volume = self.data.ct_volume
        pet_ct_volume = self.data.pet_ct_volume_rescaled
        registrator = self.threeD_viewer.registrator

        ct_ndarray = ct_volume.ndary
        ndarray = pet_ct_volume.ndary
        if ndarray is None or ct_ndarray is None:
            return

        self.set_control(True)
        dest = self.data.file.registrated_pet_directory()
        self.volume_exporter = VolumeExporter(ndarray, registrator, dest, ct_ndarray.shape, self.GUI_components.statusbar.pyqtSignal_update_progressbar)
        self.volume_exporter.finished.connect(self.on_volume_exported)
        self.volume_exporter.start()

        return

    def on_volume_exported(self):
        print("Finished")
        self.set_control(False)
        self.setWindowTitle()
        self.show_default_msg_in_statusbar()

    def closeEvent(self, event):
        self.GUI_components.statusbar.thread.exit()
        super().closeEvent(event)

class VolumeLoader(QThread):
    def __init__(self, files, progressbar_signal):
        super().__init__()
        self.files = files
        self.progressbar_signal = progressbar_signal

    def run(self):
        def fun(f, i, total):
            self.progressbar_signal.emit(i, total, 'File loading')
            return io.imread(f)

        self.__data = [fun(f, i, len(self.files)) for i, f in enumerate(self.files)]
        self.quit()

    def data(self):
        return np.array(self.__data)

class VolumeExporter(QThread):
    def __init__(self, ndarray: np.ndarray, registrator: Registrator, dest: str, output_shape: List[int], progressbar_signal):
        super().__init__()
        self.ndarray = deepcopy(ndarray)
        self.dest = dest
        self.output_shape = output_shape
        self.x = registrator.x
        self.y = registrator.y
        self.z = registrator.z
        self.x_flip = registrator.x_flip
        self.y_flip = registrator.y_flip
        self.z_flip = registrator.z_flip
        self.angle = registrator.angle
        self.progressbar_signal = progressbar_signal

    def run(self):
        self.ndarray = self.ndarray[::self.z_flip,::self.y_flip,::self.x_flip]

        shifted_ndarray = np.zeros_like(self.ndarray)
        shifted_ndarray[
            max(0, -self.z*config.skip_size):min(shifted_ndarray.shape[0], shifted_ndarray.shape[0]-self.z*config.skip_size), 
            max(0, -self.y*config.skip_size):min(shifted_ndarray.shape[1], shifted_ndarray.shape[1]-self.y*config.skip_size), 
            max(0, -self.x*config.skip_size):min(shifted_ndarray.shape[2], shifted_ndarray.shape[2]-self.x*config.skip_size)
        ] = self.ndarray[
            max(self.z*config.skip_size, 0):min(self.ndarray.shape[0], self.ndarray.shape[0]+self.z*config.skip_size), 
            max(self.y*config.skip_size, 0):min(self.ndarray.shape[1], self.ndarray.shape[1]+self.y*config.skip_size), 
            max(self.x*config.skip_size, 0):min(self.ndarray.shape[2], self.ndarray.shape[2]+self.x*config.skip_size)
        ]

        self.progressbar_signal.emit(0, 2, 'Rotating the volume')
        rotate_ndarray = rotate(shifted_ndarray, self.angle, axes=(1,2), reshape=False, prefilter=False, order=1)

        final_array = np.zeros(self.output_shape, dtype=np.uint8)
        
        difference = [x1-x2 for x1, x2 in zip(self.output_shape, self.ndarray.shape)]

        slices_for_final = []
        slices_for_original = []
        for i in range(3):
            slices_for_final.append(
                slice(
                    max(difference[i]//2, 0), 
                    min(self.output_shape[i]-(difference[i]-difference[i]//2), self.output_shape[i])
                )
            )
            slices_for_original.append(
                slice(
                    max(-difference[i]//2, 0), 
                    min(self.ndarray.shape[i]+(difference[i]-difference[i]//2), self.ndarray.shape[i])
                )
            )

        final_array[tuple(slices_for_final)] = rotate_ndarray[tuple(slices_for_original)]

        self.progressbar_signal.emit(1, 2, 'Saving the volume')
        os.makedirs(self.dest, exist_ok=True)
        for i in range(len(final_array)):
            dest_file = os.path.join(self.dest, f'img{i:04}.tif')
            io.imsave(dest_file, final_array[i])

        self.quit()
