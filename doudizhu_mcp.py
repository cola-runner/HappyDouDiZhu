# -*- coding: utf-8 -*-
"""
MCP server for Dou Di Zhu assistant.

Usage:
    python doudizhu_mcp.py          # stdio transport (for MCP clients)
    python doudizhu_mcp.py --sse    # SSE transport (for web clients)
"""

import os
import sys

# Ensure project dir is on path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from game_state import (
    GameState, parse_cards, format_cards,
    POSITION_ALIASES, POSITION_CN, TURN_ORDER,
)

# ---------------------------------------------------------------------------
#  MCP Server
# ---------------------------------------------------------------------------

INSTRUCTIONS = """\
你是一个全自动斗地主AI。用户只负责登录游戏，之后由你完全接管，自主完成整局斗地主。

你有两套工具:
- Playwright: 看网页截图 + 点击操作
- 斗地主工具(本服务): AI大脑 + 游戏状态追踪

## 全自动打牌流程

### 第一步: 观察游戏界面
用 Playwright 对游戏页面做 snapshot/screenshot，识别:
- 当前处于什么阶段(等待开局/叫地主/出牌中)
- 界面上的按钮和可交互元素

### 第二步: 叫地主阶段
- 看到"叫地主"/"抢地主"按钮时，一般选择叫地主(手牌好时)
- 看到底牌翻开后，识别3张底牌
- 识别完整手牌(底部一排)和你的位置

### 第三步: 初始化游戏
识别出手牌、底牌、位置后，调用 new_game:
- my_position: "地主"/"下家"/"上家"
- my_hand: 所有手牌，空格分隔
- dizhu_cards: 3张底牌

### 第四步: 主循环 (反复执行直到游戏结束)
1. 用 Playwright 截图/snapshot 观察当前状态
2. 判断现在轮到谁:
   - 轮到对手 → 等待，再次截图看对手出了什么 → 调用 record_move
   - 轮到自己 → 调用 get_suggestion 获取AI建议
3. 如果是自己出牌:
   - AI说出什么牌，就用 Playwright 点选对应的牌
   - 点击"出牌"按钮
   - 调用 record_move 记录自己出的牌
4. 如果对手出牌:
   - 从画面识别对手出了什么牌
   - 调用 record_move 记录
   - 如果两个对手都pass了，轮到自己，回到步骤3
5. 如果AI建议"不出(PASS)"，点击"不出/要不起"按钮，record_move("pass")

### 第五步: 游戏结束
- 看到胜利/失败画面，报告结果
- 如果用户想继续，点击"再来一局"

## 牌面名称格式
- 数字: 3 4 5 6 7 8 9 10
- 字母: J Q K A
- 2 就是 2
- 小王: X    大王: D
- 多张用空格分隔: "3 3 3 4"
- 不出: "pass"

## 位置说明
- 地主: 拿底牌的人，共20张牌，先出
- 下家: 地主之后出牌的人
- 上家: 地主之前出牌的人
- 出牌顺序: 地主 → 下家 → 上家 → 地主 → ...

## 截图识别要点
- 屏幕底部一排: 你的手牌
- 桌面中央: 刚出的牌
- 头像旁"地主"标志: 谁是地主
- 头像旁数字: 剩余牌数
- 注意10是两位数，不要看成1和0
- 小王(黑色)和大王(红色)要区分

## 出牌操作要点
- 点击牌会让它弹起(选中)，再点一次取消选中
- 选好所有要出的牌后，点"出牌"按钮
- 要不起时点"不出"或"要不起"按钮
- 确保选中的牌和AI建议一致
"""

mcp = FastMCP("斗地主AI助手", instructions=INSTRUCTIONS)

# Global game state (single session)
_game: GameState | None = None
_adapter = None


def _get_adapter():
    global _adapter
    if _adapter is None:
        from ai_adapter import AlphaDouAdapter
        _adapter = AlphaDouAdapter.instance()
    return _adapter


@mcp.tool()
def new_game(my_position: str, my_hand: str, dizhu_cards: str) -> str:
    """开始新一局斗地主。

    Args:
        my_position: 用户位置 — "地主" / "下家" / "上家"
        my_hand: 手牌，空格分隔，如 "3 4 5 6 7 8 9 10 J Q K A A 2 2 X D"
        dizhu_cards: 3张底牌，空格分隔，如 "J Q K"
    """
    global _game

    pos = POSITION_ALIASES.get(my_position)
    if pos is None:
        return f"无效位置: '{my_position}'。请用: 地主 / 下家 / 上家"

    try:
        hand = parse_cards(my_hand)
        dizhu = parse_cards(dizhu_cards)
    except ValueError as e:
        return str(e)

    expected = 20 if pos == 'landlord' else 17
    if len(hand) != expected:
        return f"{POSITION_CN[pos]}应该有{expected}张牌，输入了{len(hand)}张"
    if len(dizhu) != 3:
        return f"底牌应该3张，输入了{len(dizhu)}张"

    _game = GameState(pos, hand, dizhu)
    return f"新局已开始!\n\n{_game.status_text()}"


@mcp.tool()
def record_move(cards: str) -> str:
    """记录当前轮到的玩家出的牌。按出牌顺序依次调用此工具。

    Args:
        cards: 出的牌(空格分隔)，不出写 "pass"。例: "3 3 3 4" 或 "pass"
    """
    if _game is None:
        return "还没开始游戏，请先调用 new_game"
    if _game.game_over:
        return f"游戏已结束! {POSITION_CN[_game.winner]}获胜!"

    try:
        action = parse_cards(cards)
    except ValueError as e:
        return str(e)

    pos = _game.current_turn
    try:
        _game.apply_move(pos, action)
    except ValueError as e:
        return str(e)

    return f"{POSITION_CN[pos]}出牌: {format_cards(action)}\n\n{_game.status_text()}"


@mcp.tool()
def get_suggestion() -> str:
    """获取AI出牌建议。必须在轮到用户时调用。"""
    if _game is None:
        return "还没开始游戏，请先调用 new_game"
    if _game.game_over:
        return f"游戏已结束! {POSITION_CN[_game.winner]}获胜!"
    if _game.current_turn != _game.my_position:
        return (f"现在轮到{POSITION_CN[_game.current_turn]}，"
                "还没到你的回合。先用 record_move 记录对手出牌。")

    try:
        adapter = _get_adapter()
        infoset = _game.build_infoset()
        action = adapter.suggest(infoset)
        return f"AI建议出: {format_cards(action)}\n\n{_game.status_text()}"
    except Exception as e:
        return f"AI推理出错: {e}"


@mcp.tool()
def get_status() -> str:
    """查看当前游戏状态（手牌、出牌记录、轮次等）。"""
    if _game is None:
        return "还没开始游戏，请先调用 new_game"
    return _game.status_text()


@mcp.tool()
def undo_move() -> str:
    """撤销上一步出牌记录（输错时使用）。"""
    if _game is None:
        return "还没开始游戏"
    try:
        _game.undo_last_move()
        return f"已撤销\n\n{_game.status_text()}"
    except ValueError as e:
        return str(e)


if __name__ == "__main__":
    transport = "sse" if "--sse" in sys.argv else "stdio"
    mcp.run(transport=transport)
