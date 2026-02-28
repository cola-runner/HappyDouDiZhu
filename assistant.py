# -*- coding: utf-8 -*-
"""
CLI for Dou Di Zhu AI assistant.
Used by Claude Code to interact with AlphaDou AI via Bash.

Usage:
    python assistant.py new     <position> <hand> <dizhu_cards>
    python assistant.py move    <cards>
    python assistant.py suggest
    python assistant.py status
    python assistant.py undo

Examples:
    python assistant.py new 地主 "3 3 4 4 5 5 6 7 8 9 10 J Q K A 2 2 X D 大王" "X D 大王"
    python assistant.py move "3 3 3 4"
    python assistant.py move pass
    python assistant.py suggest
    python assistant.py undo
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_state import GameState, parse_cards, format_cards, POSITION_ALIASES, POSITION_CN

# Persist game state to a JSON file so it survives between CLI calls
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.game_state.json')


def save_state(gs):
    data = {
        'my_position': gs.my_position,
        'my_hand': gs.my_hand,
        'dizhu_cards': gs.dizhu_cards,
        'play_history': gs.play_history,
        'played_cards': gs.played_cards,
        'cards_left': gs.cards_left,
        'bomb_num': gs.bomb_num,
        'game_over': gs.game_over,
        'winner': gs.winner,
        'current_turn': gs.current_turn,
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(data, f)


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        data = json.load(f)
    gs = GameState.__new__(GameState)
    for k, v in data.items():
        if k == 'play_history':
            gs.play_history = [(pos, act) for pos, act in v]
        else:
            setattr(gs, k, v)
    return gs


def cmd_new(args):
    if len(args) < 3:
        print("用法: python assistant.py new <位置> <手牌> <底牌>")
        print('例: python assistant.py new 地主 "3 4 5 6 7 8 9 10 J Q K A A 2 2 X D 3 4 5" "3 4 5"')
        sys.exit(1)
    position_str, hand_str, dizhu_str = args[0], args[1], args[2]
    pos = POSITION_ALIASES.get(position_str)
    if pos is None:
        print(f"无效位置: '{position_str}'。用: 地主/下家/上家")
        sys.exit(1)
    hand = parse_cards(hand_str)
    dizhu = parse_cards(dizhu_str)
    expected = 20 if pos == 'landlord' else 17
    if len(hand) != expected:
        print(f"{POSITION_CN[pos]}应该{expected}张牌，输入了{len(hand)}张")
        sys.exit(1)
    if len(dizhu) != 3:
        print(f"底牌应该3张，输入了{len(dizhu)}张")
        sys.exit(1)
    gs = GameState(pos, hand, dizhu)
    save_state(gs)
    print("新局已开始!")
    print(gs.status_text())


def cmd_move(args):
    gs = load_state()
    if gs is None:
        print("还没开始游戏，先用 new 命令")
        sys.exit(1)
    cards_str = args[0] if args else "pass"
    action = parse_cards(cards_str)
    pos = gs.current_turn
    gs.apply_move(pos, action)
    save_state(gs)
    print(f"{POSITION_CN[pos]}出牌: {format_cards(action)}")
    print(gs.status_text())


def cmd_suggest(_args):
    gs = load_state()
    if gs is None:
        print("还没开始游戏，先用 new 命令")
        sys.exit(1)
    if gs.current_turn != gs.my_position:
        print(f"现在轮到{POSITION_CN[gs.current_turn]}，还没到你")
        sys.exit(1)
    from ai_adapter import AlphaDouAdapter
    adapter = AlphaDouAdapter.instance()
    infoset = gs.build_infoset()
    action = adapter.suggest(infoset)
    print(f"AI建议: {format_cards(action)}")


def cmd_status(_args):
    gs = load_state()
    if gs is None:
        print("还没开始游戏")
        sys.exit(1)
    print(gs.status_text())


def cmd_undo(_args):
    gs = load_state()
    if gs is None:
        print("还没开始游戏")
        sys.exit(1)
    gs.undo_last_move()
    save_state(gs)
    print("已撤销")
    print(gs.status_text())


COMMANDS = {
    'new': cmd_new,
    'move': cmd_move,
    'suggest': cmd_suggest,
    'status': cmd_status,
    'undo': cmd_undo,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("斗地主AI助手")
        print("命令: new / move / suggest / status / undo")
        print('详细用法见 python assistant.py <命令> --help')
        sys.exit(0)
    cmd = sys.argv[1]
    COMMANDS[cmd](sys.argv[2:])
