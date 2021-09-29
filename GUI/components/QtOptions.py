from GUI.components import QtMain
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import (QCheckBox, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QSizePolicy, QSlider,
                             QSpinBox, QVBoxLayout, QWidget)


class QtOptions(QWidget):
    def __init__(self, parent: QtMain):
        super().__init__(parent=parent)
        self.main_window_instance = parent

        self.setLayout(QVBoxLayout(self))

        self.resolution_group = ResolutionGroup(parent=parent)
        self.layout().addWidget(self.resolution_group)
        self.intensity_group = IntensityGroup(parent=parent)
        self.layout().addWidget(self.intensity_group)

        self.flip_group = FlipGroup(parent=parent)
        self.layout().addWidget(self.flip_group)
        self.registration_group = RegistrationGroup(parent=parent)
        self.layout().addWidget(self.registration_group)

        self.export_group = ExportGroup(parent=parent)
        self.layout().addWidget(self.export_group)

        self.layout().addStretch() 

    def update_valid_option(self):
        self.main_window_instance.data.pet_ct_volume

        #// update resolution spinboxes
        for spinbox, resolution in zip(
                    [self.resolution_group.xray_ct_resolution_edit, self.resolution_group.pet_ct_resolution_edit],
                    [self.main_window_instance.data.ct_volume.resolution, self.main_window_instance.data.pet_ct_volume.resolution]
                ):
            spinbox.setText(str(resolution))

        #// update enabled
        for widget in [
                    self.resolution_group,
                    self.export_group,
                    self.registration_group,
                    self.flip_group,
                    self.intensity_group
                ]:
            widget.setEnabled(self.main_window_instance.data.pet_ct_volume.is_empty()==False)
        
class ResolutionGroup(QGroupBox):
    def __init__(self, parent: QtMain) -> None:
        super().__init__('Resolution')
        self.main_window_instance = parent
        self.setLayout(QHBoxLayout(self))

        self.label_layout = QVBoxLayout()
        self.edit_layout = QVBoxLayout()

        self.label_layout.addWidget(QLabel('X-ray CT: '))
        self.xray_ct_resolution_edit = ResolutionLineEdit(toolTip='X-ray CT voxel resolution (double)')
        self.edit_layout.addWidget(self.xray_ct_resolution_edit)

        self.label_layout.addWidget(QLabel('PET CT: '))
        self.pet_ct_resolution_edit = ResolutionLineEdit(toolTip='PET CT voxel resolution (double)')
        self.edit_layout.addWidget(self.pet_ct_resolution_edit)

        self.label_layout.addWidget(QLabel(''))
        self.push_button_rescale = QPushButton(parent=parent, text='Rescale')
        self.edit_layout.addWidget(self.push_button_rescale)

        self.push_button_rescale.clicked.connect(self.on_push_button_rescale_pressed)

        self.layout().addLayout(self.label_layout)
        self.layout().addLayout(self.edit_layout)

    def on_push_button_rescale_pressed(self):
        self.main_window_instance.data.ct_volume.resolution = float(self.xray_ct_resolution_edit.text())
        self.main_window_instance.data.pet_ct_volume.resolution = float(self.pet_ct_resolution_edit.text())

        self.main_window_instance.set_control(True)
        rescaled_pet_ct_volume = self.main_window_instance.data.rescale_pet_ct_volume()
        self.main_window_instance.threeD_viewer.set_pet_ct_volume(rescaled_pet_ct_volume)
        self.main_window_instance.set_control(False)

class ResolutionLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QDoubleValidator())
        self.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed))

class FlipGroup(QGroupBox):
    def __init__(self, parent: QtMain) -> None:
        super().__init__('Flip')
        self.main_window_instance = parent
        self.setLayout(QVBoxLayout(self))

        self.checkbox_layout = QHBoxLayout()
        self.checkbox_x_flip = QCheckBox(text='X')
        self.checkbox_y_flip = QCheckBox(text='Y')
        self.checkbox_z_flip = QCheckBox(text='Z')

        self.checkbox_x_flip.stateChanged.connect(self.state_changed)
        self.checkbox_y_flip.stateChanged.connect(self.state_changed)
        self.checkbox_z_flip.stateChanged.connect(self.state_changed)

        self.checkbox_layout.addWidget(self.checkbox_x_flip)
        self.checkbox_layout.addWidget(self.checkbox_y_flip)
        self.checkbox_layout.addWidget(self.checkbox_z_flip)
        self.layout().addLayout(self.checkbox_layout)

    def state_changed(self, _):
        self.main_window_instance.threeD_viewer.registrator.set_flip_states(
            x_flip=self.checkbox_x_flip.isChecked(), 
            y_flip=self.checkbox_y_flip.isChecked(), 
            z_flip=self.checkbox_z_flip.isChecked()
        )

class RegistrationGroup(QGroupBox):
    def __init__(self, parent: QtMain) -> None:
        super().__init__('Registration')
        self.main_window_instance = parent
        self.setLayout(QHBoxLayout(self))

        self.label_layout = QVBoxLayout()
        self.edit_layout = QVBoxLayout()

        self.spin_box_up_down = SpinBox_Shift()
        self.spin_box_up_down.valueChanged.connect(self.spinbox_changed)
        self.label_layout.addWidget(QLabel('Up & Down: '))
        self.edit_layout.addWidget(self.spin_box_up_down)

        self.spin_box_left_right = SpinBox_Shift()
        self.spin_box_left_right.valueChanged.connect(self.spinbox_changed)
        self.label_layout.addWidget(QLabel('Left & Right: '))
        self.edit_layout.addWidget(self.spin_box_left_right)

        self.spin_box_back_forth = SpinBox_Shift()
        self.spin_box_back_forth.valueChanged.connect(self.spinbox_changed)
        self.label_layout.addWidget(QLabel('Back & Forth: '))
        self.edit_layout.addWidget(self.spin_box_back_forth)

        self.spin_box_rotate = SpinBox_Rotate()
        self.spin_box_rotate.valueChanged.connect(self.spinbox_changed)
        self.label_layout.addWidget(QLabel('Rotate: '))
        self.edit_layout.addWidget(self.spin_box_rotate)

        self.layout().addLayout(self.label_layout)
        self.layout().addLayout(self.edit_layout)

    def spinbox_changed(self):
        if self.spin_box_rotate.value() < 0 or self.spin_box_rotate.value() > 359:
            self.spin_box_rotate.spinbox_changed()
        else:
            self.main_window_instance.threeD_viewer.registrator.do( 
                self.spin_box_left_right.value(), 
                self.spin_box_back_forth.value(),
                self.spin_box_up_down.value(),
                self.spin_box_rotate.value()
            )

class SpinBox_Shift(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setRange(-500, 500)

class SpinBox_Rotate(QSpinBox):
    def __init__(self) -> None:
        super().__init__()
        self.setRange(-1, 360)

    def spinbox_changed(self):
        if self.value() < 0:
            self.setValue(359)
        elif self.value() > 359:
            self.setValue(0)

class IntensityGroup(QGroupBox):
    def __init__(self, parent: QtMain) -> None:
        super().__init__('Intensity')
        self.setLayout(QVBoxLayout(self))

        self.ct_slider = CT_IntensitySlider(parent=parent)
        self.layout().addWidget(QLabel('X-ray CT'))
        self.layout().addWidget(self.ct_slider)

        self.trace_slider = Trace_IntensitySlider(parent=parent)
        self.layout().addWidget(QLabel('CT trace'))
        self.layout().addWidget(self.trace_slider)

        self.pet_ct_slider = PET_IntensitySlider(parent=parent)
        self.layout().addWidget(QLabel('PET CT'))
        self.layout().addWidget(self.pet_ct_slider)

class IntensitySlider(QSlider):
    def __init__(self) -> None:
        super().__init__(Qt.Horizontal)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setTickPosition(True)
        self.setSingleStep(5)
        self.setValue(10)

class CT_IntensitySlider(IntensitySlider):
    def __init__(self, parent: QtMain) -> None:
        super().__init__()
        self.main_window_instance = parent

        self.sliderReleased.connect(self.value_changed)

    def value_changed(self):
        self.main_window_instance.threeD_viewer.ct_volume_intensity_changed(intensity=self.value()/10)

class Trace_IntensitySlider(IntensitySlider):
    def __init__(self, parent: QtMain) -> None:
        super().__init__()
        self.main_window_instance = parent

        self.sliderReleased.connect(self.value_changed)

    def value_changed(self):
        self.main_window_instance.threeD_viewer.ct_trace_intensity_changed(intensity=self.value()/10)

class PET_IntensitySlider(IntensitySlider):
    def __init__(self, parent: QtMain) -> None:
        super().__init__()
        self.main_window_instance = parent

        self.sliderReleased.connect(self.value_changed)

    def value_changed(self):
        self.main_window_instance.threeD_viewer.pet_ct_volume_intensity_changed(intensity=self.value()/10)


class ExportGroup(QGroupBox):
    def __init__(self, parent: QtMain) -> None:
        super().__init__('Export')
        self.main_window_instance = parent
        self.setLayout(QVBoxLayout(self))

        self.push_button_registrated_pet_ct_volume = QPushButton(parent=parent, text='Registrated PET CT volume')
        self.layout().addWidget(self.push_button_registrated_pet_ct_volume)

        self.push_button_registrated_pet_ct_volume.clicked.connect(self.main_window_instance.export_volume)

