# -*- coding: utf-8 -*-
"""
    预览窗口插件
    ~~~~~~~~~~~~~~~~~~

    Log:
        2024-09-20 0.1.0 Me2sY  创建，预览窗口
"""

__author__ = 'Me2sY'
__version__ = '0.1.0'

__all__ = [
    'CPMPreview', 'CPMImages'
]

from collections import OrderedDict
from dataclasses import dataclass, field
import datetime
from loguru import logger
from pathlib import Path, PurePath
import threading
import uuid

import dearpygui.dearpygui as dpg
import numpy as np
from PIL import Image

from myscrcpy.utils import Coordinate, Param
from myscrcpy.gui.dpg.components.component_cls import TempModal


class CPMPreview:
    """
        预览窗口组件
    """
    def __init__(self, win_coord: Coordinate):
        self.coord = win_coord
        self.tag_texture = dpg.generate_uuid()

        self.drawing_image = None

        with dpg.texture_registry():
            dpg.add_raw_texture(
                **win_coord.d, default_value=np.full(win_coord.pixel_n(4), 0.2, np.float32),
                tag=self.tag_texture, format=dpg.mvFormat_Float_rgba
            )

    def draw_image(self, **kwargs):
        """
            绘制 Image 组件
        :param parent:
        :param kwargs:
        :return:
        """
        dpg.add_image(self.tag_texture, **kwargs)

    def draw_dl_image(self, **kwargs):
        """
            绘制 draw_image 组件
        :param parent:
        :param kwargs:
        :return:
        """
        with dpg.drawlist(**self.coord.d) as tag_dl:
            dpg.draw_image(
                self.tag_texture, [0, 0], self.coord,
                **kwargs
            )

        with dpg.item_handler_registry() as handler_registry:
            dpg.add_item_double_clicked_handler(callback=self.show_raw)
        dpg.bind_item_handler_registry(tag_dl, handler_registry)

    def show_raw(self, sender, app_data, user_data):
        """
            双击展示原始图片
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """
        if self.drawing_image is None:
            return

        with dpg.texture_registry():
            tag_pic = dpg.add_static_texture(
                self.drawing_image.width, self.drawing_image.height,
                np.array(self.drawing_image.convert('RGBA'), dtype=np.float32).ravel() / np.float32(255),
            )

        with dpg.window(
            label=f"Image Width:{self.drawing_image.width} Height:{self.drawing_image.height}", no_resize=True,

        ) as tag_win:
            dpg.add_image(tag_pic)
            dpg.add_button(
                label='Close', width=-1, height=35,
                callback=lambda: dpg.delete_item(tag_win) or dpg.delete_item(tag_pic)
            )

    def update(self, image: Image.Image):
        """
            更新画面
        :param image:
        :return:
        """

        self.drawing_image = image

        # 调整至最大显示
        coord = Coordinate(image.width, image.height)
        max_coord = coord.get_max_coordinate(self.coord.width, self.coord.height)
        image = image.resize(max_coord)

        img = Image.new('RGBA', self.coord, color=(0, 0, 0, 0))

        # 居中拷贝
        img.paste(image, ((img.width - image.width) // 2, (img.height - image.height) // 2))

        dpg.set_value(
            self.tag_texture,
            np.array(img.convert('RGBA'), dtype=np.uint8).ravel() / np.float32(255),
        )


@dataclass
class ImageItem:
    """
        图片项
    """

    image: Image.Image
    name: str
    tag_texture: str | int
    image_id: str = field(default_factory=uuid.uuid4)
    selected: bool = True

    @staticmethod
    def init(
            image: Image.Image,
            name: str,
            preview_size: Coordinate = Coordinate(52, 52)
    ) -> 'ImageItem':
        """
            初始化 Image
        :param image:
        :param name:
        :param preview_size:
        :return:
        """
        with dpg.texture_registry():
            tag_texture = dpg.add_static_texture(
                **preview_size.d,
                default_value=np.array(
                    image.resize(preview_size).convert('RGBA'), np.uint8
                ).ravel() / np.float32(255)
            )

        return ImageItem(image=image, name=str(name), tag_texture=tag_texture)


class CPMImages:
    """
        Image 控件
    """

    def __init__(self):

        self.images = OrderedDict()
        self.img_i = 0

        self.tag_collapsing_header = dpg.generate_uuid()
        self.tag_win = dpg.generate_uuid()

        self.save_path = Param.PATH_TEMP

    def create_image_name(self, image: Image.Image) -> str:
        """
            创建 Image Name
        :param image:
        :return:
        """
        self.img_i += 1
        return datetime.datetime.now().strftime(
            f"{str(self.img_i).rjust(4, '0')}_%Y%m%d_%H%M%S"
        )

    def add_image(self, image: Image.Image) -> ImageItem:
        """
            新增 Image
        :param image:
        :return:
        """

        img_item = ImageItem.init(image, self.create_image_name(image))

        self.images[img_item.image_id] = img_item

        self.draw_image_item(img_item)

        dpg.set_item_label(self.tag_collapsing_header, f"Images {len(self.images)}")

        return img_item

    def draw_image_item(self, img_item: ImageItem):
        """
            新增 Image Item
        :param img_item:
        :return:
        """

        # First Bottom Last Top
        items = dpg.get_item_children(self.tag_win, 1)
        if len(items) == 0:
            kwargs = {'parent': self.tag_win}
        else:
            kwargs = {'before': items[0]}

        # Draw Item Group
        with dpg.group(**kwargs) as tag_group:

            with dpg.group(horizontal=True):
                tag_image = dpg.add_image(img_item.tag_texture)

                # Double Click To Open Raw Image
                with dpg.item_handler_registry() as tag_handler_image_dc:
                    dpg.add_item_double_clicked_handler(callback=self.draw_raw, user_data=img_item.image_id)
                dpg.bind_item_handler_registry(tag_image, tag_handler_image_dc)

                with dpg.group():

                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(
                            user_data=img_item.image_id, default_value=img_item.selected,
                            callback=lambda s, a, u: setattr(self.images.get(u), 'selected', a),
                        )
                        dpg.add_text(f"{img_item.name[:4]}")
                        dpg.add_text(f"{img_item.image.width} x {img_item.image.height}")

                        def delete(image_id):
                            dpg.delete_item(tag_group)
                            self.images.pop(image_id)
                            dpg.delete_item(tag_handler_image_dc)
                            dpg.set_item_label(self.tag_collapsing_header, f"Images {len(self.images)}")

                        dpg.add_button(
                            label='X', user_data=img_item.image_id, callback=lambda s, a, u: delete(u), width=20
                        )

                    # File Name
                    # When with .xxx Then Try to Save in .xxx image format
                    dpg.add_input_text(
                        default_value=img_item.name, user_data=img_item.image_id,
                        callback=lambda s, a, u: setattr(self.images.get(u), 'name', a)
                    )

            dpg.add_separator()

    def draw(self):
        """
            绘制控件
        :return:
        """
        with dpg.collapsing_header(label='Images', tag=self.tag_collapsing_header, default_open=True, bullet=True):
            dpg.add_child_window(height=240, tag=self.tag_win)
            with dpg.group(horizontal=True):
                self.tag_save_format = dpg.add_combo(['jpeg', 'png'], default_value='jpeg', width=70)
                dpg.add_button(label='Save', width=94, callback=self.save_images)
                dpg.add_button(label='Clear', width=60, callback=self.clear_images)

    def save_images(self):
        """
            保存图片
        :return:
        """
        if len(self.images) == 0:
            return

        def _save_thread(path: Path):
            """
                保存thread，避免过多文件卡主gui
            :param path:
            :return:
            """
            saved_img_n = 0

            save_format = dpg.get_value(self.tag_save_format)

            for image_item in self.images.values():
                if image_item.selected:
                    pp = PurePath(image_item.name)
                    if pp.suffix == '':
                        # 未定义存储格式，则使用统一选择格式
                        # 使用.jpg 实际上 .jpeg 一样的 ;)
                        save_path = path / f"{image_item.name}.{save_format.replace('jpeg', 'jpg')}"
                    else:
                        save_path = path / pp
                    try:
                        image_item.image.save(save_path)
                        saved_img_n += 1
                    except Exception as e:
                        logger.warning(f"Saving {image_item.name} failed -> {e}")

            logger.info(f"Saved {saved_img_n} images")

        def _save(sender, app_data):

            save_path = Path(app_data['current_path'])
            if save_path.exists() and save_path.is_dir():
                self.save_path = save_path
                threading.Thread(target=_save_thread, args=[save_path]).start()

        dpg.add_file_dialog(
            width=500, height=450, modal=True, directory_selector=True, show=True,
            default_path=self.save_path.__str__(), callback=_save
        )

    def clear_images(self):
        """
            清除全部图片
        :return:
        """
        def _clear():
            dpg.delete_item(self.tag_win, children_only=True)
            self.images.clear()

            dpg.set_item_label(self.tag_collapsing_header, f"Images {len(self.images)}")
            self.img_i = 0

        # Use MYScrcpy provide function to create a confirm modal
        TempModal.draw_confirm(f"Clear All {len(self.images)} Images?", _clear)

    def draw_raw(self, sender, app_data, user_data):
        """
            双击展示原始图片
        :param sender:
        :param app_data:
        :param user_data:
        :return:
        """

        image_item: ImageItem = self.images[user_data]

        with dpg.texture_registry():
            tag_pic = dpg.add_static_texture(
                image_item.image.width, image_item.image.height,
                np.array(image_item.image.convert('RGBA'), dtype=np.float32).ravel() / np.float32(255),
            )

        with dpg.window(
            label=f"Image > {image_item.name} | Width:{image_item.image.width} Height:{image_item.image.height}",
            no_resize=True
        ) as tag_win:
            dpg.add_image(tag_pic)
            dpg.add_button(
                label='Close', width=-1, height=35,
                callback=lambda: dpg.delete_item(tag_win) or dpg.delete_item(tag_pic)
            )
