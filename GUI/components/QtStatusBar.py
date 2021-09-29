import psutil
from PyQt5.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import QLabel, QProgressBar, QSizePolicy, QStatusBar


class QtStatusBarW(QObject):
    pyqtSignal_update_progressbar = pyqtSignal(int, int, str)

    def __init__(self, parent):
        super().__init__()
        self.__parent = parent
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.start()

        self.widget = QtStatusBar(parent=parent)
        self.pyqtSignal_update_progressbar.connect(self.widget.update_progress)

    def parent(self):
        return self.__parent

    def set_main_message(self, msg):
        self.widget.set_main_message(msg=msg)

class QtStatusBar(QStatusBar):
    def __init__(self, parent):
        super().__init__(**{'parent':parent})

        self.progress = QProgressBar()
        self.status_msg = QLabel('')

        self.prev_mouse_pos = [0,0,0]
        self.mem_msg = QLabel('')
        self.cpu_msg = QLabel('')

        self.addWidget(self.progress)
        self.addWidget(self.status_msg, 2048)

        self.progress.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
    
        self.addPermanentWidget(self.cpu_msg,140)
        self.addPermanentWidget(self.mem_msg,140)

        self.progress.setValue(0)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_meter)
        self.timer.start(1000)
        
    def update_progress(self, i, maximum, msg):
        self.progress.setMaximum(maximum)
        self.progress.setValue(i +1)

        self.set_main_message(f'{msg}: {i+1} / {maximum}')

    def set_main_message(self, msg):
        if self.parent().is_control_locked():
            msg = 'BUSY: '+msg 
        else:
             msg = 'READY: '+msg 

        self.status_msg.setText(msg)

    def update_meter(self):
        mem_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent()

        for msg, hard, p in zip([self.mem_msg, self.cpu_msg], ['Memory', 'CPU'], [mem_percent, cpu_percent]):
            bg_color = 'yellow' if p > 80 else 'transparent'
            msg.setStyleSheet("QLabel { background-color : %s; color : black; }" % bg_color)
            msg.setText(' %s: %.01f %% ' % (hard, p))

