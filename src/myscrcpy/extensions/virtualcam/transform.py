# -*- coding: utf-8 -*-
"""
    transform use Opencv
    ~~~~~~~~~~~~~~~~~~
    
    Log:
        2024-09-26 0.1.0 Me2sY
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = [
    'gray', 'cartoon', 'edges'
]

import cv2
import numpy as np


def gray(frame: np.ndarray) -> np.ndarray:
    """
        Get a gray frame
    :param frame:
    :return:
    """
    return cv2.cvtColor(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), cv2.COLOR_GRAY2RGB)


def cartoon(frame: np.ndarray) -> np.ndarray:
    """
        Get a cartoon frame using OpenCV.
        Thanks To aiortc
        https://github.com/aiortc/aiortc/blob/main/examples/server/server.py
    :param frame:
    :return:
    """

    color = cv2.pyrDown(cv2.pyrDown(frame))
    for _ in range(6):
        color = cv2.bilateralFilter(color, 9, 9, 7)
    color = cv2.pyrUp(cv2.pyrUp(color))

    edges = cv2.cvtColor(color, cv2.COLOR_RGB2GRAY)
    edges = cv2.adaptiveThreshold(
        cv2.medianBlur(edges, 7),
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        9,
        2
    )
    edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)

    img = cv2.bitwise_and(color, edges)

    return img


def edges(frame: np.ndarray) -> np.ndarray:
    """
        绘制边缘
    :param frame:
    :return:
    """
    return cv2.cvtColor(cv2.Canny(frame, 100, 200), cv2.COLOR_GRAY2RGB)
