import base64
import random
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

class ImageProcessor:
    """图片处理器"""

    def __init__(self, config):
        self.config = config
        self._font_cache = {}

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """获取字体（带缓存）"""
        if size not in self._font_cache:
            try:
                font = ImageFont.truetype(str(self.config.whois_font_path), size)
            except:
                # 回退到默认字体
                font = ImageFont.load_default()
            self._font_cache[size] = font
        return self._font_cache[size]

    def _get_text_size(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple:
        """兼容不同 PIL 版本的文本尺寸获取方法"""
        try:
            # PIL < 10.0.0 的方法
            return draw.textsize(text, font=font)
        except AttributeError:
            # PIL >= 10.0.0 的方法
            bbox = draw.textbbox((0, 0), text, font=font)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])

    def generate_puzzle_image(self, pokemon_name: str) -> str:
        """
        生成灰度谜题图片
        返回base64编码的图片数据
        """
        # 1. 创建画布
        im = Image.new("RGB", (640, 464), (255, 255, 255))

        # 2. 添加背景（如果有）
        if self.config.whois_bg_path.exists():
            try:
                bg_img = Image.open(self.config.whois_bg_path)
                im.paste(bg_img, (0, 0))
            except:
                pass

        # 3. 加载并处理宝可梦图标
        icon_path = self.config.whois_icon_path / f"{pokemon_name}.png"
        if not icon_path.exists():
            # 如果找不到图片，生成一个错误占位图
            draw = ImageDraw.Draw(im)
            draw.rectangle([50, 60, 280, 290], fill=(200, 200, 200))
            draw.text((100, 175), "?", fill=(0, 0, 0), font=self._get_font(100))
        else:
            image = Image.open(icon_path).convert('RGBA')
            image = image.resize((230, 230))

            # 4. 像素级灰度二值化处理
            width, height = image.size
            for x in range(width):
                for y in range(height):
                    r, g, b, a = image.getpixel((x, y))
                    if a == 0:  # 透明部分
                        gray = 255
                    else:       # 非透明部分
                        gray = 0
                        a = 255
                    image.putpixel((x, y), (gray, gray, gray, a))

            # 5. 合成到主画布
            im.paste(image, (50, 60), mask=image.split()[3])

        # 6. 添加文字
        draw = ImageDraw.Draw(im)

        # 英文"？？？"
        font = self._get_font(40)
        w, h = self._get_text_size(draw, "???", font)
        draw.text(((926 - w) / 2, 40), "???", font=font, fill=(255, 255, 0))

        # 中文"我是谁"
        font = self._get_font(42)
        w, h = self._get_text_size(draw, "我是谁", font)
        draw.text(((926 - w) / 2, 100), "我是谁", font=font, fill=(255, 255, 0))

        # 7. 编码为Base64
        return self._image_to_base64(im)

    def generate_answer_image(self, pokemon_name: str, enname: str) -> str:
        """
        生成彩色答案图片
        返回base64编码的图片数据
        """
        # 1. 创建画布
        im = Image.new("RGB", (640, 464), (255, 255, 255))

        # 2. 添加背景
        if self.config.whois_bg_path.exists():
            try:
                bg_img = Image.open(self.config.whois_bg_path)
                im.paste(bg_img, (0, 0))
            except:
                pass

        # 3. 加载彩色原图
        icon_path = self.config.whois_icon_path / f"{pokemon_name}.png"
        if icon_path.exists():
            image = Image.open(icon_path).convert('RGBA')
            image = image.resize((230, 230))
            im.paste(image, (50, 60), mask=image.split()[3])

        # 4. 添加文字（显示真实名称）
        draw = ImageDraw.Draw(im)

        # 英文名
        font = self._get_font(40)
        w, h = self._get_text_size(draw, enname, font)
        draw.text(((926 - w) / 2, 40), enname, font=font, fill=(255, 255, 0))

        # 中文名
        font = self._get_font(42)
        w, h = self._get_text_size(draw, pokemon_name, font)
        draw.text(((926 - w) / 2, 100), pokemon_name, font=font, fill=(255, 255, 0))

        # 5. 编码为Base64
        return self._image_to_base64(im)

    def _image_to_base64(self, image: Image.Image) -> str:
        """将PIL图片转换为base64字符串"""
        output = BytesIO()
        image.save(output, format="PNG")
        base64_str = base64.b64encode(output.getvalue()).decode()
        return f"base64://{base64_str}"