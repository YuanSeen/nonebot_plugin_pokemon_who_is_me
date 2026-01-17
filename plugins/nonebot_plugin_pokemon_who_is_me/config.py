from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional

class Config(BaseModel):
    """插件配置"""

    # 游戏相关配置
    whois_timeout: int = Field(default=60, description="答题时间（秒）")
    whois_enable_groups: list[str] = Field(default=[], description="启用的群组，空列表表示全部启用")
    whois_disable_groups: list[str] = Field(default=[], description="禁用的群组")

    # 文件路径配置
    whois_icon_path: Path = Field(
        default=Path(__file__).parent / "icon",
        description="宝可梦图标路径"
    )
    whois_bg_path: Path = Field(
        default=Path(__file__).parent / "resource" / "whois_bg.jpg",
        description="背景图片路径"
    )
    whois_font_path: Path = Field(
        default=Path(__file__).parent / "resource" / "sakura.ttf",
        description="字体文件路径"
    )