import logging
from typing import Tuple, Union

import numpy as np
from skimage import exposure, transform


class Volume(object):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.clear()

    def clear(self):
        self.ndary: Union[np.ndarray, None] = None
        self.resolution = 0.3
        self.scaling_factor = 1.
        self.logger.debug(f'The volume data cleared.')

    def is_empty(self):
        return self.ndary is None

    def shape(self):
        assert self.ndary is not None
        return self.ndary.shape

    def init_from_volume(self, volume: np.ndarray):
        self.ndary = volume
        self.logger.debug(f'The volume data initialized.')

    def get_rescaled_ndarray(self):
        assert self.ndary is not None

        shape :Tuple[int] = self.ndary.shape
        resized = [int(s*self.scaling_factor) for s in shape]
        
        return np.array(exposure.rescale_intensity(
            transform.resize(self.ndary, resized),
            out_range=np.uint8
        ))




        