import json
import requests
from flaskr.util_nanni import *
from types import SimpleNamespace
import random 
import numpy as np
import pickle
from tqdm import tqdm
## This is a very(!) simple client that simply draws 3 Ingredients
#  and then stops. With 3 Chips it is impossible to explode (draw
#  3 + 2 + 2 <= 7 is worst case).

url = 'http://127.0.0.1:5000/'
EXPLODE_THRESHOLD = 7
NUM_ROUNDS = 9

#Probleme: 2 Rubies werden immer erst einen Zug später ausgegeben. In turn 9macht Drop verschieben keinen Sinn mehr, macht er aber


class SimpleAgent:

    # Different Strategies -> Always buys 2 or most expensive, which color, how risky
    def __init__(self, risk_threshold, favorite_color, ruby_strategy):
        self.risk_threshold = risk_threshold
        if favorite_color == 'red':
            self.price_chart = prices_orange_red
        if favorite_color == 'green':
            self.price_chart = prices_orange_green
        if favorite_color == 'blue':
            self.price_chart = prices_orange_blue
        if favorite_color == 'yellow':
            self.price_chart = prices_orange_yellow
        if favorite_color == 'purple':
            self.price_chart = prices_orange_purple
        if favorite_color == 'all':
            self.price_chart = prices

    def brewing(self):
        global gamestate
        exploded = False
        chance_to_explode = 0
        while (not exploded) and chance_to_explode < self.risk_threshold:
            # print(str(draw()))
            state = draw()
            gamestate = json.loads(json.dumps(state["player_info"]), object_hook=lambda d: SimpleNamespace(**d))
            bag = gamestate.bag
            exploded = gamestate.exploded
            pot = state["player_info"]["pot"]
            white_sum = sum(list(map(lambda white: white[1], list(filter(lambda ingredient: ingredient[0] == "white", pot)))))
            whites_allowed = EXPLODE_THRESHOLD - white_sum
            whites_that_would_explode = len(list(filter(lambda ingredient: ingredient[0] == "white" and ingredient[1] > whites_allowed, bag)))
            chance_to_explode = 0 if whites_that_would_explode == 0 else whites_that_would_explode / len(bag) 
            # print("chance to explode = " + str(chance_to_explode))
            # print(f"droplet position: {gamestate.drop_position}")
        #print("I'm done brewing. ", get_state())
        stop_brewing()
        return exploded

    def buying(self, turn):
        affordable = list(filter(lambda ingredient: ingredient[2] <= gamestate.money, self.price_chart))
        if turn == 1:
            affordable = list(filter(lambda x: x[0] != 'yellow', affordable))
            affordable = list(filter(lambda x: x[0] != 'purple', affordable))
        if turn == 2:
            affordable = list(filter(lambda x: x[0] != 'purple', affordable))
        most_expensive = max(affordable, key = lambda ingredient: ingredient[2])
        buy_one(*most_expensive)
        money_left = gamestate.money - most_expensive[2]
        if money_left >= 3:
            #buy_one("orange", 1, 1)
            # Added for picking sth other than Orange
            left_to_buy = list(filter(lambda ingredient: ingredient[2] <= money_left, self.price_chart))
            second_most_expansive = max(left_to_buy, key = lambda ingredient: ingredient[2])
            buy_one(*second_most_expansive)
        if turn < 9:
            for i in range(get_state()["player_info"]["rubies"] // 2):
                use_rubies()
        if turn != 9:
            end_turn()

        #print("Turn ", turn, " ended - ", get_state())
        return get_state()

    def run(self):
        num_exploded = 0
        for i in range(1, NUM_ROUNDS + 1):
            exploded = self.brewing()
            # Always buy chips till turn 7
            if exploded and i <= 9:
                num_exploded += 1
                #print("I exploded in turn", i)
                #if i < 7:
                #    decision("buy")
                #    re = self.buying(i)
                #else:
                #    decision("vp")
                #    if i != NUM_ROUNDS:
                #        end_turn()
                #    re = get_state()
                decision("vp")
                if i != NUM_ROUNDS:
                    end_turn()
                re = get_state()
            else:
                re = self.buying(i)
        return re, num_exploded


def main():
    vps = []
    exploded = 0
    num_games = 1000
    color = 'all'
    risk = 0.3

    for i in tqdm(range(0, num_games)):
        random.seed(i)
        set_random_seed(i)
        #print(f"Playing game {i}. ", end="") 
        #start game with one player
        start_game()

        agent = SimpleAgent(risk, color, 'allin')
        #print(r.status_code, r.reason, r.text)
        final_result, num_exploded = agent.run()
        vp = final_result["player_info"]["total_vp"]
        vps.append(vp)
        exploded += num_exploded
        exploded_avg = exploded / num_games
        #print(f"Received {vp} victory points.")
    avg_vp = sum(vps)/len(vps)
    max_vp = max(vps)
    min_vp = min(vps)
    median_vp = np.median(vps)

    pickle.dump(vps, open('./simple_all_colors.pkl', 'wb'))
    print(f"You are playing with orange and {color} chips and risk factor {risk}")
    print(f"Over {num_games} games the agent received {avg_vp} VP on average")
    print(f"The best game scored with {max_vp} VP, the worst game only {min_vp} VP. The median is {median_vp}")
    print(f"You have exploded {exploded_avg} times on average")
    print(vps)


def hpo():
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    colors = ['red', 'green', 'blue']
    results = []

    for threshold in thresholds:
        for color in colors:
            vps = []
            for i in tqdm(range(0, 1000)):
                random.seed(i)
                set_random_seed(i)
                #print(f"Playing game {i}. ", end="") 
                #start game with one player
                start_game()

                agent = SimpleAgent(threshold, color, 'allin')
                #print(r.status_code, r.reason, r.text)
                final_result = agent.run()
                vp = final_result["player_info"]["total_vp"]
                vps.append(vp)
                #print(f"Received {vp} victory points.")
            avg_vp = np.mean(vps)
            std_vp = np.std(vps)
            max_vp = np.max(vps)
            min_vp = np.min(vps)
            
            result = {}
            result['color'] = color
            result['threshold'] = threshold
            result['avg_vp'] = avg_vp
            result['std_vp'] = std_vp
            result['max_vp'] = max_vp
            result['min_vp'] = min_vp

            results.append(result)

            #print(f"With threshold {threshold} and color {color}: Over 100 games the agent received {avg_vp} on average")

    print(results)
    pickle.dump(results, open('simple_hpo_result.pkl', 'wb'))


if __name__ == "__main__":
    main()
