# -*- coding: utf-8 -*-
"""
    Vector
    ~~~~~~~~~~~~~~~~~~
    

    Log:
        2024-08-25 1.4.0 Me2sY  新增 ScalePointR, 带方向的 ScalePoint

        2024-08-24 1.3.7 Me2sY utils中分离
"""

__author__ = 'Me2sY'
__version__ = '1.4.0'

__all__ = [
    'ROTATION_VERTICAL', 'ROTATION_HORIZONTAL',
    'Point', 'ScalePoint', 'ScalePointR',
    'Coordinate'
]

from typing import NamedTuple, Literal


ROTATION_VERTICAL = 0
ROTATION_HORIZONTAL = 1


class Point(NamedTuple):
    """
        坐标点
    """
    x: int
    y: int

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)

    @property
    def d(self) -> dict:
        return self._asdict()


class ScalePoint(NamedTuple):
    """
        比例点
    """
    x: float
    y: float

    def __add__(self, other: 'ScalePoint') -> 'ScalePoint':
        return ScalePoint(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'ScalePoint') -> 'ScalePoint':
        return ScalePoint(self.x - other.x, self.y - other.y)

    def __mul__(self, scale: float) -> 'ScalePoint':
        return ScalePoint(self.x * scale, self.y * scale)


class ScalePointR(NamedTuple):
    """
        带旋转方向的比例点
    """
    x: float
    y: float
    r: int

    def rotate(self) -> 'ScalePointR':
        return ScalePointR(self.y, self.x, 1 if self.r == 0 else 0)

    def __add__(self, other: 'ScalePointR') -> 'ScalePointR':
        """
            若不同向，则将other旋转后相加
        :param other:
        :return:
        """
        if other.r != self.r:
            other = other.rotate()

        return ScalePointR(
            min(1.0, self.x + other.x),
            min(1.0, self.y + other.y),
            self.r
        )

    def __sub__(self, other: 'ScalePointR') -> 'ScalePointR':
        """
            若不同向，则将other旋转后相减, 最小值0
        :param other:
        :return:
        """
        if other.r != self.r:
            other = other.rotate()

        return ScalePointR(
            max(0.0, self.x - other.x),
            max(0.0, self.y - other.y),
            self.r
        )

    def __mul__(self, scale: float) -> 'ScalePointR':
        return ScalePointR(self.x * scale, self.y * scale, self.r)


class Coordinate(NamedTuple):
    """
        坐标系
    """
    width: int
    height: int

    def __repr__(self):
        return f'w:{self.width}, h:{self.height} {"Up" if self.rotation == ROTATION_VERTICAL else "Right"}'

    def __add__(self, other: 'Coordinate') -> 'Coordinate':
        return Coordinate(self.width + other.width, self.height + other.height)

    def __sub__(self, other: 'Coordinate') -> 'Coordinate':
        return Coordinate(self.width - other.width, self.height - other.height)

    def __mul__(self, scale: float) -> 'Coordinate':
        if 0 < scale:
            return Coordinate(round(self.width * scale), round(self.height * scale))
        else:
            raise ValueError(f"Scale value {scale} is not valid")

    def to_point(self, scale_point: ScalePoint | ScalePointR) -> Point:
        return Point(round(scale_point.x * self.width), round(scale_point.y * self.height))

    def to_scale_point(self, x: int, y: int) -> ScalePoint:
        return ScalePoint(x / self.width, y / self.height)

    def rotate(self) -> 'Coordinate':
        """
            选择
        :return:
        """
        return Coordinate(self.height, self.width)

    @property
    def rotation(self) -> int:
        return ROTATION_VERTICAL if self.height >= self.width else ROTATION_HORIZONTAL

    @property
    def max_size(self) -> int:
        return max(self.width, self.height)

    @property
    def min_size(self) -> int:
        return min(self.width, self.height)

    @property
    def d(self) -> dict:
        return self._asdict()

    def w2h(self, width: float) -> float:
        return width / self.width * self.height

    def h2w(self, height: float) -> float:
        return height / self.height * self.width

    def get_max_coordinate(self, max_width: int = 0, max_height: int = 0) -> 'Coordinate':
        """
            获取限制下最大坐标系
        :param max_width:
        :param max_height:
        :return:
        """

        scale_w = max_width / self.width
        scale_h = max_height / self.height

        if scale_w <= 0 < scale_h:
            _scale = min(scale_h, 1)

        elif scale_w > 0 >= scale_h:
            _scale = min(scale_w, 1)

        elif scale_w > 0 and scale_h > 0:
            _scale = min(scale_h, scale_w, 1)

        else:
            _scale = 1

        return self * _scale

    def fix_height(self, raw_coordinate: 'Coordinate') -> 'Coordinate':
        """
            Width不变，以Width适配raw_coordinate下新坐标系
        """
        return Coordinate(
            self.width,
            round(self.width / raw_coordinate.width * raw_coordinate.height)
        )

    def fix_width(self, raw_coordinate: 'Coordinate') -> 'Coordinate':
        """
            Height不变，以Height适配raw_coordinate下新坐标系
        """
        return Coordinate(
            round(self.height / raw_coordinate.height * raw_coordinate.width),
            self.height
        )
