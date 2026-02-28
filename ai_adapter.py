# -*- coding: utf-8 -*-

import sys
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
#  Card / Position conversion utilities
# ============================================================

# HappyDouDiZhu Card.rank → DouZero int
RANK_TO_DZ = {
    1: 3, 2: 4, 3: 5, 4: 6, 5: 7, 6: 8, 7: 9,
    8: 10, 9: 11, 10: 12, 11: 13, 12: 14, 13: 17,
    14: 20, 15: 30,
}
DZ_TO_RANK = {v: k for k, v in RANK_TO_DZ.items()}

# DouZero bomb patterns (for bomb counting)
_BOMBS = [[v] * 4 for v in [3,4,5,6,7,8,9,10,11,12,13,14,17]] + [[20, 30]]

# DouZero move type int → our move type string
_DZ_TYPE_TO_OURS = {
    0: "pass", 1: "dan", 2: "dui", 3: "san",
    4: "bomb", 5: "bomb",
    6: "san_dai_yi", 7: "san_dai_er",
    8: "shunzi", 9: "liandui", 10: "feiji",
    11: "feiji_dai_dan", 12: "feiji_dai_dui",
    13: "si_dai_er", 14: "si_dai_er_dui",
}


def _cards_to_dz(cards):
    """Convert Card objects to sorted DouZero int list."""
    return sorted([RANK_TO_DZ[c.rank] for c in cards])


def _get_position(player_id, dizhu_id):
    """Map player_id (1-3) to DouZero position.

    Turn order: landlord → landlord_down → landlord_up
    """
    if player_id == dizhu_id:
        return 'landlord'
    elif player_id == (dizhu_id % 3) + 1:
        return 'landlord_down'
    else:
        return 'landlord_up'


def _dz_action_to_cards(action, cards_left):
    """Convert DouZero action (list of ints) to Card objects from hand."""
    if not action:
        return []
    result = []
    remaining = list(cards_left)
    for dz_int in sorted(action):
        rank = DZ_TO_RANK[dz_int]
        for card in remaining:
            if card.rank == rank:
                result.append(card)
                remaining.remove(card)
                break
    return result


# ============================================================
#  Module loading
# ============================================================

def _clear_douzero_cache():
    """Remove all cached douzero.* modules from sys.modules."""
    to_remove = [k for k in sys.modules
                 if k == 'douzero' or k.startswith('douzero.')]
    for k in to_remove:
        del sys.modules[k]


def _load_repo_modules(repo_name):
    """Load douzero modules from a specific repo.

    Returns (DeepAgent, MovesGener, md, ms).
    """
    _clear_douzero_cache()
    repo_path = os.path.join(BASE_DIR, repo_name)
    # Ensure repo_path is at front of sys.path
    if repo_path in sys.path:
        sys.path.remove(repo_path)
    sys.path.insert(0, repo_path)

    from douzero.env.move_generator import MovesGener
    from douzero.env import move_detector as md
    from douzero.env import move_selector as ms
    from douzero.evaluation.deep_agent import DeepAgent

    return DeepAgent, MovesGener, md, ms


# ============================================================
#  Legal action generation (mirrors DouZero GameEnv logic)
# ============================================================

def _get_legal_actions(hand_cards_dz, rival_move, MovesGener, md, ms):
    """Generate legal DouZero actions given hand cards and rival move.

    Args:
        hand_cards_dz: sorted list of DouZero ints (current player's hand)
        rival_move: list of DouZero ints ([] = new round / pass)
        MovesGener, md, ms: loaded module references
    Returns:
        list of lists (each inner list is a legal action in DouZero ints)
    """
    mg = MovesGener(hand_cards_dz)

    rival_type = md.get_move_type(rival_move)
    rival_move_type = rival_type['type']
    rival_move_len = rival_type.get('len', 1)
    moves = list()

    if rival_move_type == md.TYPE_0_PASS:
        moves = mg.gen_moves()
    elif rival_move_type == md.TYPE_1_SINGLE:
        moves = ms.filter_type_1_single(mg.gen_type_1_single(), rival_move)
    elif rival_move_type == md.TYPE_2_PAIR:
        moves = ms.filter_type_2_pair(mg.gen_type_2_pair(), rival_move)
    elif rival_move_type == md.TYPE_3_TRIPLE:
        moves = ms.filter_type_3_triple(mg.gen_type_3_triple(), rival_move)
    elif rival_move_type == md.TYPE_4_BOMB:
        moves = ms.filter_type_4_bomb(
            mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb(), rival_move)
    elif rival_move_type == md.TYPE_5_KING_BOMB:
        moves = []
    elif rival_move_type == md.TYPE_6_3_1:
        moves = ms.filter_type_6_3_1(mg.gen_type_6_3_1(), rival_move)
    elif rival_move_type == md.TYPE_7_3_2:
        moves = ms.filter_type_7_3_2(mg.gen_type_7_3_2(), rival_move)
    elif rival_move_type == md.TYPE_8_SERIAL_SINGLE:
        moves = ms.filter_type_8_serial_single(
            mg.gen_type_8_serial_single(repeat_num=rival_move_len), rival_move)
    elif rival_move_type == md.TYPE_9_SERIAL_PAIR:
        moves = ms.filter_type_9_serial_pair(
            mg.gen_type_9_serial_pair(repeat_num=rival_move_len), rival_move)
    elif rival_move_type == md.TYPE_10_SERIAL_TRIPLE:
        moves = ms.filter_type_10_serial_triple(
            mg.gen_type_10_serial_triple(repeat_num=rival_move_len), rival_move)
    elif rival_move_type == md.TYPE_11_SERIAL_3_1:
        moves = ms.filter_type_11_serial_3_1(
            mg.gen_type_11_serial_3_1(repeat_num=rival_move_len), rival_move)
    elif rival_move_type == md.TYPE_12_SERIAL_3_2:
        moves = ms.filter_type_12_serial_3_2(
            mg.gen_type_12_serial_3_2(repeat_num=rival_move_len), rival_move)
    elif rival_move_type == md.TYPE_13_4_2:
        moves = ms.filter_type_13_4_2(mg.gen_type_13_4_2(), rival_move)
    elif rival_move_type == md.TYPE_14_4_22:
        moves = ms.filter_type_14_4_22(mg.gen_type_14_4_22(), rival_move)

    # Add bombs (unless rival played bomb or king bomb)
    if rival_move_type not in [md.TYPE_0_PASS,
                               md.TYPE_4_BOMB, md.TYPE_5_KING_BOMB]:
        moves = moves + mg.gen_type_4_bomb() + mg.gen_type_5_king_bomb()

    # Add pass option (only when there's a rival move to beat)
    if len(rival_move) != 0:
        moves = moves + [[]]

    for m in moves:
        m.sort()

    return moves


# ============================================================
#  InfoSet construction from our game state
# ============================================================

def _get_player_id(position, dizhu_id):
    """Map DouZero position string to our player_id (1-3)."""
    if position == 'landlord':
        return dizhu_id
    elif position == 'landlord_down':
        return (dizhu_id % 3) + 1
    else:
        return ((dizhu_id + 1) % 3) + 1


def _build_infoset(player, playrecords, position, dizhu_id, for_alphadou):
    """Build a DouZero-compatible InfoSet from our game state.

    Creates a simple namespace with all fields expected by get_obs().
    """
    class InfoSet:
        pass

    infoset = InfoSet()
    infoset.player_position = position

    # Hand cards
    infoset.player_hand_cards = _cards_to_dz(player.cards_left)

    # Three landlord cards
    infoset.three_landlord_cards = _cards_to_dz(playrecords.dizhu_cards)

    # Cards left per position
    cards_left_by_id = {
        1: playrecords.cards_left1,
        2: playrecords.cards_left2,
        3: playrecords.cards_left3,
    }

    infoset.num_cards_left_dict = {}
    infoset.all_handcards = {}
    for pos in ['landlord', 'landlord_down', 'landlord_up']:
        pid = _get_player_id(pos, dizhu_id)
        infoset.num_cards_left_dict[pos] = len(cards_left_by_id[pid])
        infoset.all_handcards[pos] = _cards_to_dz(cards_left_by_id[pid])

    # Other hand cards (combined hands of other two players)
    infoset.other_hand_cards = []
    for pos in ['landlord', 'landlord_down', 'landlord_up']:
        if pos != position:
            infoset.other_hand_cards += infoset.all_handcards[pos]
    infoset.other_hand_cards.sort()

    # Build play history from records
    action_seq = []
    played_cards = {'landlord': [], 'landlord_down': [], 'landlord_up': []}
    last_move_dict = {'landlord': [], 'landlord_down': [], 'landlord_up': []}
    bomb_num = 0

    for record in playrecords.records:
        rec_pid = record[0]
        rec_move = record[1]
        rec_pos = _get_position(rec_pid, dizhu_id)

        if isinstance(rec_move, str):  # "yaobuqi" / "buyao" → pass
            dz_action = []
        else:
            dz_action = _cards_to_dz(rec_move)

        # Format differs: DouZero uses [action], AlphaDou uses (pos, action)
        if for_alphadou:
            action_seq.append((rec_pos, dz_action))
        else:
            action_seq.append(dz_action)

        if dz_action:
            played_cards[rec_pos] += dz_action
            last_move_dict[rec_pos] = dz_action.copy()
            if dz_action in _BOMBS:
                bomb_num += 1

    infoset.card_play_action_seq = action_seq
    infoset.played_cards = played_cards
    infoset.last_move_dict = last_move_dict
    infoset.bomb_num = bomb_num

    # last_move: most recent non-pass move
    infoset.last_move = []
    if action_seq:
        if for_alphadou:
            last_act = action_seq[-1][1]
            prev_act = action_seq[-2][1] if len(action_seq) >= 2 else []
        else:
            last_act = action_seq[-1]
            prev_act = action_seq[-2] if len(action_seq) >= 2 else []
        infoset.last_move = prev_act if len(last_act) == 0 else last_act

    # last_two_moves
    infoset.last_two_moves = [[], []]
    for entry in action_seq[-2:]:
        act = entry[1] if for_alphadou else entry
        infoset.last_two_moves.insert(0, act)
        infoset.last_two_moves = infoset.last_two_moves[:2]

    # last_pid: position of last player who made a non-pass move
    infoset.last_pid = 'landlord'
    for record in reversed(playrecords.records):
        if not isinstance(record[1], str):
            infoset.last_pid = _get_position(record[0], dizhu_id)
            break

    # AlphaDou-specific fields (needed by env_res.py _get_obs_resnet)
    if for_alphadou:
        infoset.bid_info = [-1, -1, -1]
        infoset.bid_count = 0
        infoset.spring = False
        infoset.bid_over = True

    return infoset


# ============================================================
#  Convert DouZero action back to our format
# ============================================================

def _convert_action(action, player, md):
    """Convert a DouZero action to (move_type_str, [Card])."""
    if len(action) == 0:
        return "buyao", []

    move_info = md.get_move_type(action)
    move_type = _DZ_TYPE_TO_OURS.get(move_info['type'], 'dan')
    cards = _dz_action_to_cards(action, player.cards_left)
    return move_type, cards


# ============================================================
#  DouZero Adapter
# ============================================================

class DouZeroAdapter:
    _instance = None

    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.join(
                BASE_DIR, 'DouZero', 'baselines', 'douzero_ADP')

        DeepAgent, MovesGener, md, ms = _load_repo_modules('DouZero')
        self._MovesGener = MovesGener
        self._md = md
        self._ms = ms

        self._agents = {}
        for pos in ['landlord', 'landlord_up', 'landlord_down']:
            model_path = os.path.join(model_dir, f'{pos}.ckpt')
            self._agents[pos] = DeepAgent(pos, model_path)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def choose(self, next_move_types, next_moves, last_move_type,
               player, playrecords):
        dizhu_id = playrecords.dizhu_id
        position = _get_position(player.player_id, dizhu_id)

        # Build InfoSet
        infoset = _build_infoset(
            player, playrecords, position, dizhu_id, for_alphadou=False)

        # Determine rival move for legal action generation
        if last_move_type == "start":
            rival_move = []
        else:
            rival_move = infoset.last_move

        # Generate legal actions via DouZero's MovesGener
        infoset.legal_actions = _get_legal_actions(
            infoset.player_hand_cards, rival_move,
            self._MovesGener, self._md, self._ms)

        if not infoset.legal_actions:
            return "yaobuqi", []

        # Run the neural network agent
        action = self._agents[position].act(infoset)
        return _convert_action(action, player, self._md)

    def suggest(self, infoset):
        """Get AI action from a pre-built InfoSet (used by assistant/MCP).

        Args:
            infoset: InfoSet with all fields populated EXCEPT legal_actions.
        Returns:
            list of DouZero ints (suggested action).
        """
        rival_move = infoset.last_move if infoset.last_move else []
        infoset.legal_actions = _get_legal_actions(
            infoset.player_hand_cards, rival_move,
            self._MovesGener, self._md, self._ms)
        if not infoset.legal_actions:
            return []
        return self._agents[infoset.player_position].act(infoset)


# ============================================================
#  AlphaDou Adapter
# ============================================================

class AlphaDouAdapter:
    _instance = None

    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.join(
                BASE_DIR, 'AlphaDou', 'baseline', 'best')

        DeepAgent, MovesGener, md, ms = _load_repo_modules('AlphaDou')
        self._MovesGener = MovesGener
        self._md = md
        self._ms = ms

        self._agents = {}
        for pos in ['landlord', 'landlord_up', 'landlord_down']:
            model_path = os.path.join(model_dir, f'{pos}.ckpt')
            self._agents[pos] = DeepAgent(pos, model_path)

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def choose(self, next_move_types, next_moves, last_move_type,
               player, playrecords):
        dizhu_id = playrecords.dizhu_id
        position = _get_position(player.player_id, dizhu_id)

        # Build InfoSet (AlphaDou uses (position, action) tuples in seq)
        infoset = _build_infoset(
            player, playrecords, position, dizhu_id, for_alphadou=True)

        if last_move_type == "start":
            rival_move = []
        else:
            rival_move = infoset.last_move

        infoset.legal_actions = _get_legal_actions(
            infoset.player_hand_cards, rival_move,
            self._MovesGener, self._md, self._ms)

        if not infoset.legal_actions:
            return "yaobuqi", []

        action = self._agents[position].act(infoset)
        return _convert_action(action, player, self._md)

    def suggest(self, infoset):
        """Get AI action from a pre-built InfoSet (used by MCP server).

        Args:
            infoset: AlphaDou InfoSet with all fields EXCEPT legal_actions.
        Returns:
            list of DouZero ints (suggested action).
        """
        rival_move = infoset.last_move if infoset.last_move else []
        infoset.legal_actions = _get_legal_actions(
            infoset.player_hand_cards, rival_move,
            self._MovesGener, self._md, self._ms)
        if not infoset.legal_actions:
            return []
        return self._agents[infoset.player_position].act(infoset)
