import random
import asyncio
import time  # 添加这行
from pathlib import Path
from typing import Optional

from nonebot import get_driver, on_command, on_message, logger
from nonebot.adapters import Event, Message
from nonebot.adapters.onebot.v11 import MessageSegment  # 添加这行
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .config import Config
from .state import game_manager
from .image_processor import ImageProcessor
from .poke_data import CHARA_NAME

# 插件元信息
__plugin_meta__ = PluginMetadata(
    name="猜猜我是谁",
    description="宝可梦猜谜游戏",
    usage="""
    命令列表：
    /whois - 开始游戏
    /whois stop - 强制结束游戏（管理员）
    /whois list - 查看当前游戏状态
    """,
    config=Config,
    type="application",
    homepage="https://github.com/yourname/nonebot-plugin-whois",
    supported_adapters={
        "nonebot.adapters.onebot.v11",
        "nonebot.adapters.onebot.v12"
    },
)

# 获取配置
driver = get_driver()
global_config = driver.config
config = Config.parse_obj(global_config.dict())

# 初始化图片处理器
image_processor = ImageProcessor(config)

# 创建事件处理器
whois_cmd = on_command("whois", aliases={"猜猜我是谁", "猜宝可梦"}, priority=10, block=True)
whois_answer = on_message(priority=20, block=False)

async def check_admin(bot, event) -> bool:
    """检查是否是管理员"""
    # 检查超级用户
    if await SUPERUSER(bot, event):
        return True

    # 对于 OneBot V11，检查群管理权限
    try:
        from nonebot.adapters.onebot.v11 import GroupMessageEvent
        if isinstance(event, GroupMessageEvent):
            # 检查是否是群主或管理员
            if event.sender.role in ["owner", "admin"]:
                return True
    except:
        pass

    return False

@whois_cmd.handle()
async def handle_whois(event: Event, args: Message = CommandArg()):
    """处理/whois命令"""
    # 获取群组ID
    group_id = getattr(event, "group_id", None)
    if not group_id:
        await whois_cmd.finish("请在群聊中使用此命令")

    group_id = str(group_id)

    # 检查子命令
    arg_text = args.extract_plain_text().strip()
    if arg_text == "stop":
        # 强制结束游戏（需要管理员权限）
        from nonebot import get_bot
        bot = get_bot()

        if not await check_admin(bot, event):
            await whois_cmd.finish("只有管理员可以强制结束游戏")

        game_manager.end_game(group_id)
        await whois_cmd.finish("游戏已强制结束")

    elif arg_text == "list" or arg_text == "status":
        # 显示游戏状态
        state = game_manager.get_state(group_id)
        if state.is_playing:
            remaining = config.whois_timeout - (time.time() - state.start_time)
            await whois_cmd.finish(
                f"游戏中...\n"
                f"剩余时间: {max(0, int(remaining))}秒\n"
                f"当前状态: {'已有人答对' if state.winner else '等待答案中'}"
            )
        else:
            await whois_cmd.finish("当前没有进行中的游戏")

    else:
        # 开始新游戏
        await start_new_game(event, group_id)

async def start_new_game(event: Event, group_id: str):
    """开始新游戏"""
    state = game_manager.get_state(group_id)

    # 检查游戏是否已在进行中
    if state.is_playing:
        await whois_cmd.finish("游戏正在进行中，请等待当前游戏结束")

    try:
        # 随机选择宝可梦
        chara_id_list = list(CHARA_NAME.keys())
        random.shuffle(chara_id_list)
        # correct_id = chara_id_list[0]
        correct_id = 25
        # 获取角色信息
        chara_info = CHARA_NAME[correct_id]
        name = chara_info[0]
        enname = chara_info[1] if len(chara_info) > 1 else "Unknown"


        # 预生成答案图片
        answer_image = image_processor.generate_answer_image(name, enname)

        # 开始游戏
        game_manager.start_game(group_id, correct_id, name, enname)
        game_manager.set_answer_image(group_id, answer_image)

        # 生成谜题图片
        puzzle_image = image_processor.generate_puzzle_image(name)

        # 发送题目（使用 MessageSegment）
        msg = MessageSegment.text(f"猜猜我是谁？ ({config.whois_timeout}秒后公布答案)\n")
        msg += MessageSegment.image(puzzle_image)
        await whois_cmd.send(msg)

        # 启动倒计时
        asyncio.create_task(game_timer(group_id, event))

    except Exception as e:
        logger.error(f"开始游戏时出错: {e}")
        await whois_cmd.finish("游戏开始失败，请稍后重试")
        game_manager.end_game(group_id)  # 清理状态


async def game_timer(group_id: str, event: Event):
    """游戏倒计时"""
    await asyncio.sleep(config.whois_timeout)

    state = game_manager.get_state(group_id)
    if state.is_playing and not state.winner:
        # 无人答对，公布答案
        try:
            msg = MessageSegment.text(f"时间到！正确答案是：{state.correct_name}\n")
            msg += MessageSegment.text("很遗憾，没有人答对~\n")
            msg += MessageSegment.image(state.answer_image)
            await whois_cmd.send(msg)
        except Exception as e:
            logger.error(f"发送答案时出错: {e}")
            await whois_cmd.send(f"时间到！正确答案是：{state.correct_name}")

        game_manager.end_game(group_id)

@whois_answer.handle()
async def handle_answer(event: Event):
    """处理用户答案"""
    # 获取群组ID和用户ID
    group_id = getattr(event, "group_id", None)
    user_id = getattr(event, "user_id", None)

    if not group_id or not user_id:
        return

    group_id = str(group_id)
    user_id = str(user_id)

    state = game_manager.get_state(group_id)
    if not state.is_playing or state.winner:
        return

    # 获取用户消息
    message = event.get_plaintext().strip()
    if not message:
        return

    # 检查答案
    is_correct = await check_answer(message, state.correct_id, state.correct_name)

    if is_correct:
        # 记录获胜者
        game_manager.set_winner(group_id, user_id)

        # 发送正确答案（使用 MessageSegment）
        user_nickname = getattr(event.sender, "nickname", "神秘人") if event.sender else "神秘人"
        try:
            msg = MessageSegment.text(f"恭喜 {user_nickname} 答对了！\n")
            msg += MessageSegment.text(f"正确答案是：{state.correct_name}\n")
            msg += MessageSegment.image(state.answer_image)
            await whois_answer.send(msg)
        except Exception as e:
            logger.error(f"发送胜利消息时出错: {e}")
            await whois_answer.send(
                f"恭喜 {user_nickname} 答对了！\n"
                f"正确答案是：{state.correct_name}"
            )

        # 结束游戏
        game_manager.end_game(group_id)

async def check_answer(user_answer: str, correct_id: int, correct_name: str) -> bool:
    """
    检查用户答案是否正确
    支持多种答案格式：ID、中文名、英文名、别名等
    """
    # 去除空格和特殊字符
    user_answer = user_answer.strip().lower()

    # 检查是否是ID
    try:
        if int(user_answer) == correct_id:
            return True
    except ValueError:
        pass

    # 检查是否是中文名
    if user_answer == correct_name.lower():
        return True

    # 检查所有可能的名称
    chara_info = CHARA_NAME.get(correct_id, [])
    for name_variant in chara_info:
        if isinstance(name_variant, str) and user_answer == name_variant.lower():
            return True

    return False

# 定时清理过期游戏状态
@driver.on_startup
async def _():
    """启动时初始化"""
    pass

@driver.on_shutdown
async def _():
    """关闭时清理"""
    pass