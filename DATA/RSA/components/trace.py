import logging
from copy import deepcopy
from typing import List, Tuple, Union

import numpy as np
from PyQt5.QtGui import QColor
from skimage.morphology import ball, disk

from .rinfo import RootNode


class Trace(object):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.clear()

    def is_empty(self):
        return self.trace3D is None

    def clear(self):
        self.trace3D: Union[TraceObject, None] = None
        self.logger.debug('The trace data cleared.')

    def init_from_volume(self, volume: np.ndarray):
        self.clear()
        self.trace3D = TraceObject(shape=volume.shape, dimensions = [0,1,2], pen_size=3)

    def draw_trace(self, root_node: RootNode):
        completed_polyline = root_node.completed_polyline()
        if self.trace3D is not None:
            self.trace3D.draw_trace_single(completed_polyline, color=QColor('#ffffffff'))
        
class TraceObject():
    def __init__(self, shape: Tuple, dimensions: List[int] = [0,1,2], pen_size: int=3):
        self.dimensions = deepcopy(dimensions)
        self.shape_full = tuple(shape+(4,))
        self.shape = tuple([shape[d] for d in self.dimensions])+(4,)
        self.pen_size = pen_size

        self.clear()

    def clear(self):
        self.volume = np.zeros(self.shape, dtype=np.uint8)

    def get_slice_generator(self, polyline: List[List[int]]):
        S = self.pen_size*2+1

        for pos in polyline:
            #// skip invalid values
            if any([pos[d]<0 or pos[d]>=self.shape_full[d] for d in range(3)]):
                continue
            
            #// slices for cropping
            slices = []
            pad_slices = []
            for d in range(3):
                slices.append(slice(max(pos[d]-self.pen_size, 0), min(pos[d]+self.pen_size+1, self.shape_full[d])))
                pad_slices.append(slice(-min(pos[d]-self.pen_size, 0), S+min(self.shape_full[d]-pos[d]-self.pen_size-1, 0)))

            not_index = [d for d in range(3) if d not in self.dimensions]
            for d in not_index:
                del slices[d]
                del pad_slices[d]

            yield (slices, pad_slices)

    def draw_trace(self, polyline: List[List[int]], color=QColor('#ffffffff')):
        for slices, pad_slices in self.get_slice_generator(polyline=polyline):
            croped = self.volume[tuple(slices)]
            pen = ball if len(self.dimensions)==3 else disk
            pen = pen(self.pen_size)[tuple(pad_slices)]
            m_ball = [pen*color for color in color.getRgb()]
            m_ball = np.stack(m_ball, axis=len(self.dimensions))

            croped = np.maximum(croped, m_ball)
            self.volume[tuple(slices)] = croped

    def draw_trace_single(self, polyline: List[List[int]], **kwargs):
        self.draw_trace(polyline, **kwargs)
