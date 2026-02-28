# -*- coding: utf-8 -*-

import numpy as np


#展示扑克函数
def card_show(cards, info, n):

    #扑克牌记录类展示
    if n == 1:
        print(info)
        names = []
        for i in cards:
            names.append(i.name+i.color)
        print(names)
    #Moves展示
    elif n == 2:
        if len(cards) == 0:
            return 0
        print(info)
        moves = []
        for i in cards:
            names = []
            for j in i:
                names.append(j.name+j.color)
            moves.append(names)
        print(moves)
    #record展示
    elif n == 3:
        print(info)
        names = []
        for i in cards:
            tmp = []
            tmp.append(i[0])
            tmp_name = []
            #处理要不起
            try:
                for j in i[1]:
                    tmp_name.append(j.name+j.color)
                tmp.append(tmp_name)
            except:
                tmp.append(i[1])
            names.append(tmp)
        print(names)


#在Player的next_moves中选择出牌方法
def choose(next_move_types, next_moves, last_move_type, model, player=None, playrecords=None):

    if model == "random":
        return choose_random(next_move_types, next_moves, last_move_type)
    elif model == "douzero":
        from ai_adapter import DouZeroAdapter
        return DouZeroAdapter.instance().choose(
            next_move_types, next_moves, last_move_type, player, playrecords
        )
    elif model == "alphadou":
        from ai_adapter import AlphaDouAdapter
        return AlphaDouAdapter.instance().choose(
            next_move_types, next_moves, last_move_type, player, playrecords
        )

#random
def choose_random(next_move_types, next_moves, last_move_type):
    #要不起
    if len(next_moves) == 0:
        return "yaobuqi", []
    else:
        #start不能不要
        if last_move_type == "start":
            r_max = len(next_moves)
        else:
            r_max = len(next_moves)+1
        r = np.random.randint(0,r_max)
        #添加不要
        if r == len(next_moves):
            return "buyao", []

    return next_move_types[r], next_moves[r]

#发牌 (标准斗地主规则: 17+17+17+3底牌)
def game_init(players, playrecords, cards):

    #洗牌
    np.random.shuffle(cards.cards)

    #每人17张
    p1_cards = list(cards.cards[:17])
    p2_cards = list(cards.cards[17:34])
    p3_cards = list(cards.cards[34:51])
    dizhu_cards = list(cards.cards[51:])  # 3张底牌

    #随机选地主
    dizhu_id = np.random.randint(1, 4)  # 1, 2, 或 3

    #底牌给地主 (地主共20张)
    if dizhu_id == 1:
        p1_cards.extend(dizhu_cards)
    elif dizhu_id == 2:
        p2_cards.extend(dizhu_cards)
    else:
        p3_cards.extend(dizhu_cards)

    #排序
    p1_cards.sort(key=lambda x: x.rank)
    p2_cards.sort(key=lambda x: x.rank)
    p3_cards.sort(key=lambda x: x.rank)

    #设置手牌
    players[0].cards_left = playrecords.cards_left1 = p1_cards
    players[1].cards_left = playrecords.cards_left2 = p2_cards
    players[2].cards_left = playrecords.cards_left3 = p3_cards

    #设置角色
    for i, player in enumerate(players):
        if i + 1 == dizhu_id:
            player.role = "dizhu"
        else:
            player.role = "nongmin"

    #记录地主信息
    playrecords.dizhu_id = dizhu_id
    playrecords.dizhu_cards = dizhu_cards

    return dizhu_id


