# -*- coding: utf-8 -*-

from myclass import Cards, Player, PlayRecords, WebShow
from myutil import game_init
import jsonpickle
import time
import copy

class Game(object):

    def __init__(self, model):
        #初始化一副扑克牌类
        self.cards = Cards()

        #play相关参数
        self.end = False
        self.last_move_type = self.last_move = "start"
        self.playround = 1
        self.i = 0
        self.yaobuqis = []

        #choose模型 — 支持字符串或字典 {"dizhu": model, "nongmin": model}
        if isinstance(model, dict):
            self.model_dict = model
        else:
            self.model_dict = {"dizhu": model, "nongmin": model}

    #发牌
    def game_start(self):

        #初始化players
        self.players = []
        for i in range(1,4):
            self.players.append(Player(i))

        #初始化扑克牌记录类
        self.playrecords = PlayRecords()

        #发牌 (标准规则: 17+3底牌, 地主先出)
        dizhu_id = game_init(self.players, self.playrecords, self.cards)

        #地主先出牌
        self.i = dizhu_id - 1  # 0-indexed


    #返回扑克牌记录类
    def get_record(self):
        web_show = WebShow(self.playrecords)
        return jsonpickle.encode(web_show, unpicklable=False)

    #游戏进行
    def next_move(self):
        role = self.players[self.i].role
        model = self.model_dict.get(role, self.model_dict.get("nongmin", "random"))

        self.last_move_type, self.last_move, self.end, self.yaobuqi = self.players[self.i].go(self.last_move_type, self.last_move, self.playrecords, model)
        if self.yaobuqi:
            self.yaobuqis.append(self.i)
        else:
            self.yaobuqis = []
        #都要不起
        if len(self.yaobuqis) == 2:
            self.yaobuqis = []
            self.last_move_type = self.last_move = "start"
        if self.end:
            self.playrecords.winner = self.i+1
        self.i = (self.i + 1) % 3
        #一轮结束
        if self.i == (self.playrecords.dizhu_id - 1):
            self.playround = self.playround + 1


if __name__=="__main__":

    begin = time.time()

    # 统计胜率
    # model 可以是字符串 "random"/"douzero"/"alphadou"
    # 也可以是字典指定混合模型: {"dizhu": "alphadou", "nongmin": "random"}
    model = "random"
    total_games = 1000
    dizhu_wins = 0
    nongmin_wins = 0

    for j in range(total_games):
        game_ddz = Game(model)
        game_ddz.game_start()

        step = 0
        while(game_ddz.playrecords.winner == 0):
            game_ddz.next_move()
            step += 1

        # 判断地主还是农民赢
        winner_id = game_ddz.playrecords.winner
        dizhu_id = game_ddz.playrecords.dizhu_id
        if winner_id == dizhu_id:
            dizhu_wins += 1
        else:
            nongmin_wins += 1

    print(f"Total games: {total_games}")
    print(f"Dizhu wins: {dizhu_wins} ({dizhu_wins/total_games*100:.1f}%)")
    print(f"Nongmin wins: {nongmin_wins} ({nongmin_wins/total_games*100:.1f}%)")
    print(f"Time: {time.time()-begin:.2f}s")
