# -*- coding: utf-8 -*-
"""Game state management for the Dou Di Zhu assistant."""

# Card name → DouZero int
CARD_TO_DZ = {
    '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14, '2': 17,
    '小王': 20, '大王': 30,
    # aliases
    'j': 11, 'q': 12, 'k': 13, 'a': 14,
    'X': 20, 'D': 30, 'x': 20, 'd': 30,
}

DZ_TO_CARD = {
    3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A', 17: '2',
    20: '小王', 30: '大王',
}

POSITION_CN = {
    'landlord': '地主',
    'landlord_down': '下家',
    'landlord_up': '上家',
}

POSITION_ALIASES = {
    '地主': 'landlord',
    '下家': 'landlord_down', '农民下家': 'landlord_down',
    '上家': 'landlord_up', '农民上家': 'landlord_up',
    'landlord': 'landlord',
    'landlord_down': 'landlord_down',
    'landlord_up': 'landlord_up',
}

TURN_ORDER = ['landlord', 'landlord_down', 'landlord_up']

ALL_CARDS = (
    [3]*4 + [4]*4 + [5]*4 + [6]*4 + [7]*4 + [8]*4 + [9]*4 +
    [10]*4 + [11]*4 + [12]*4 + [13]*4 + [14]*4 + [17]*4 +
    [20, 30]
)

_BOMBS = [sorted([v]*4) for v in
          [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17]] + [[20, 30]]


def parse_cards(text):
    """Parse '3 3 3 4' or 'pass' into sorted DouZero int list."""
    text = text.strip()
    if not text or text.lower() in ('pass', '不要', '要不起', 'p', '不出'):
        return []
    tokens = text.replace(',', ' ').replace('，', ' ').split()
    result = []
    for t in tokens:
        t = t.strip()
        if not t:
            continue
        if t in CARD_TO_DZ:
            result.append(CARD_TO_DZ[t])
        else:
            raise ValueError(
                f"无法识别: '{t}'。有效值: 3-10, J, Q, K, A, 2, 小王/X, 大王/D")
    return sorted(result)


def format_cards(dz_cards):
    """DouZero ints → '3 3 3 4'."""
    if not dz_cards:
        return '不出(PASS)'
    return ' '.join(DZ_TO_CARD[c] for c in sorted(dz_cards))


class GameState:
    """Tracks a Dou Di Zhu game for the assistant."""

    def __init__(self, my_position, my_hand, dizhu_cards):
        self.my_position = my_position
        self.my_hand = sorted(my_hand)
        self.dizhu_cards = sorted(dizhu_cards)
        self.play_history = []          # [(position, [dz_ints]), ...]
        self.played_cards = {p: [] for p in TURN_ORDER}
        self.cards_left = {
            'landlord': 20, 'landlord_down': 17, 'landlord_up': 17}
        self.bomb_num = 0
        self.game_over = False
        self.winner = None
        self.current_turn = 'landlord'

    def get_other_hand_cards(self):
        remaining = list(ALL_CARDS)
        for c in self.my_hand:
            remaining.remove(c)
        for cards in self.played_cards.values():
            for c in cards:
                remaining.remove(c)
        return sorted(remaining)

    def get_rival_move(self):
        """The move current player must beat. Empty list = free play."""
        if not self.play_history:
            return []
        _, last_act = self.play_history[-1]
        if last_act:
            return last_act
        if len(self.play_history) >= 2:
            _, prev_act = self.play_history[-2]
            return prev_act
        return []

    def apply_move(self, position, action):
        if self.game_over:
            raise ValueError("游戏已结束!")
        if position != self.current_turn:
            raise ValueError(
                f"当前轮到{POSITION_CN[self.current_turn]}，"
                f"不是{POSITION_CN[position]}")
        self.play_history.append((position, list(action)))
        if action:
            self.played_cards[position] += action
            self.cards_left[position] -= len(action)
            if position == self.my_position:
                for c in action:
                    self.my_hand.remove(c)
            if sorted(action) in _BOMBS:
                self.bomb_num += 1
            if self.cards_left[position] <= 0:
                self.game_over = True
                self.winner = position
        idx = TURN_ORDER.index(self.current_turn)
        self.current_turn = TURN_ORDER[(idx + 1) % 3]

    def undo_last_move(self):
        if not self.play_history:
            raise ValueError("没有可撤销的操作!")
        pos, action = self.play_history.pop()
        if action:
            for c in action:
                self.played_cards[pos].remove(c)
            self.cards_left[pos] += len(action)
            if pos == self.my_position:
                self.my_hand += action
                self.my_hand.sort()
            if sorted(action) in _BOMBS:
                self.bomb_num -= 1
        self.game_over = False
        self.winner = None
        idx = TURN_ORDER.index(self.current_turn)
        self.current_turn = TURN_ORDER[(idx - 1) % 3]

    def build_infoset(self):
        """Build AlphaDou-compatible InfoSet for AI inference."""
        class InfoSet:
            pass
        info = InfoSet()
        info.player_position = self.my_position
        info.player_hand_cards = list(self.my_hand)
        info.three_landlord_cards = list(self.dizhu_cards)
        info.num_cards_left_dict = dict(self.cards_left)
        info.other_hand_cards = self.get_other_hand_cards()

        # Distribute unknown cards to other positions (approximation)
        info.all_handcards = {p: [] for p in TURN_ORDER}
        info.all_handcards[self.my_position] = list(self.my_hand)
        other = list(info.other_hand_cards)
        for p in TURN_ORDER:
            if p != self.my_position:
                n = self.cards_left[p]
                info.all_handcards[p] = other[:n]
                other = other[n:]

        info.card_play_action_seq = list(self.play_history)
        info.played_cards = {p: list(c) for p, c in self.played_cards.items()}

        info.last_move_dict = {p: [] for p in TURN_ORDER}
        for pos, act in self.play_history:
            if act:
                info.last_move_dict[pos] = list(act)

        info.bomb_num = self.bomb_num
        info.last_move = self.get_rival_move()

        info.last_two_moves = [[], []]
        for entry in self.play_history[-2:]:
            info.last_two_moves.insert(0, entry[1])
            info.last_two_moves = info.last_two_moves[:2]

        info.last_pid = 'landlord'
        for pos, act in reversed(self.play_history):
            if act:
                info.last_pid = pos
                break

        info.bid_info = [-1, -1, -1]
        info.bid_count = 0
        info.spring = False
        info.bid_over = True
        return info

    def status_text(self):
        lines = [
            f"你的位置: {POSITION_CN[self.my_position]}",
            f"你的手牌({len(self.my_hand)}张): {format_cards(self.my_hand)}",
            f"底牌: {format_cards(self.dizhu_cards)}",
            "",
        ]
        for p in TURN_ORDER:
            tag = " <-- 你" if p == self.my_position else ""
            lines.append(
                f"  {POSITION_CN[p]}: {self.cards_left[p]}张{tag}")
        lines.append(f"\n轮到: {POSITION_CN[self.current_turn]}")
        rival = self.get_rival_move()
        lines.append(
            f"需要压过: {format_cards(rival)}" if rival else "自由出牌(新一轮)")
        if self.play_history:
            lines.append("\n最近出牌:")
            for pos, act in self.play_history[-8:]:
                lines.append(f"  {POSITION_CN[pos]}: {format_cards(act)}")
        if self.game_over:
            lines.append(f"\n游戏结束! {POSITION_CN[self.winner]}获胜!")
        return '\n'.join(lines)
