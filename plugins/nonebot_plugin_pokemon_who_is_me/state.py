from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from nonebot.adapters import Event
import time

@dataclass
class GameState:
    """单个游戏状态"""
    is_playing: bool = False
    correct_id: Optional[int] = None
    correct_name: Optional[str] = None
    correct_enname: Optional[str] = None
    answer_image: Optional[str] = None  # base64格式的答案图片
    winner: Optional[str] = None
    start_time: Optional[float] = None

class GameManager:
    """游戏状态管理器"""

    def __init__(self):
        self.games: Dict[str, GameState] = {}  # key: group_id

    def get_state(self, group_id: str) -> GameState:
        """获取或创建游戏状态"""
        if group_id not in self.games:
            self.games[group_id] = GameState()
        return self.games[group_id]

    def start_game(self, group_id: str, chara_id: int, name: str, enname: str):
        """开始新游戏"""
        state = self.get_state(group_id)
        state.is_playing = True
        state.correct_id = chara_id
        state.correct_name = name
        state.correct_enname = enname
        state.winner = None
        state.start_time = time.time()

    def end_game(self, group_id: str):
        """结束游戏"""
        state = self.get_state(group_id)
        state.is_playing = False
        state.correct_id = None
        state.correct_name = None
        state.correct_enname = None
        state.answer_image = None
        state.winner = None
        state.start_time = None

    def set_winner(self, group_id: str, user_id: str):
        """设置获胜者"""
        state = self.get_state(group_id)
        state.winner = user_id

    def set_answer_image(self, group_id: str, image_data: str):
        """保存答案图片"""
        state = self.get_state(group_id)
        state.answer_image = image_data

# 全局游戏管理器实例
game_manager = GameManager()