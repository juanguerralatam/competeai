from dataclasses import dataclass
from typing import Union, List
from concurrent.futures import ThreadPoolExecutor

from .config import SimulConfig
from .message import MessagePool
from .agent import Player
from .scene import load_scene, Scene

from .utils import NAME2PORT


# 该类负责全局的模拟过程
# 并行化运行scene，推进simulation进行.

test_data = {'La Petite Maison': {'today_offering': 'The Restaurant " La Petite Maison "information as below:\n1. Customer Score: NULL\n2. Advertisement\n   Experience the exquisite flavors of France at La Petite Maison! Our culinary masters, Chef Pierre and Chef Marie, create delectable dishes using the finest ingredients. Enjoy our cozy, charming setting while savoring our signature dishes. Don\'t miss our live music evenings and exclusive weekday discounts. Join our loyalty program for exclusive rewards and benefits. Visit La Petite Maison today for an unforgettable dining journey.\n3. Menu \n   [{\'name\': \'Coq au Vin\', \'price\': 40, \'description\': \'Traditional French dish of chicken slow cooked in red wine with mushrooms and onions\'}, {\'name\': \'Bouillabaisse\', \'price\': 40, \'description\': \'Provencal fish stew served with rouille and crusty bread\'}, {\'name\': \'Ratatouille\', \'price\': 30, \'description\': \'Classic vegetable stew with eggplant, zucchini, bell peppers, and tomato\'}, {\'name\': \'Tarte Tatin\', \'price\': 30, \'description\': \'Upside-down caramelized apple tart served with a dollop of cream\'}, {\'name\': \'French Cheese Platter\', \'price\': 30, \'description\': \'Assortment of fine French cheeses served with crackers and fruits\'}, {\'name\': \'Escargot\', \'price\': 20, \'description\': \'Classic French appetizer of snails baked in garlic butter\'}]\n4. Comments\n   []\n\nPlease note that comments are merely expressions of personal opinions and are for reference only. Comments can also be time-sensitive. So, a negative comment of a restaurant does not mean it\'s not suitable for you. If you are drawn to its menu and advertisements, don\'t hesitate to give it a try.', 'dish_score': {'Coq au Vin': 0.69, 'Bouillabaisse': 0.69, 'Ratatouille': 0.72, 'Tarte Tatin': 0.72, 'French Cheese Platter': 0.72, 'Escargot': 0.61}}, 'Le Petit Gourmet': {'today_offering': 'The Restaurant " Le Petit Gourmet "information as below:\n1. Customer Score: NULL\n2. Advertisement\n   Discover the essence of French cuisine at Le Petit Gourmet! Our menu, featuring classics like Coq au Vin and Ratatouille, alongside unique French fusion dishes, promises a culinary journey through France. We use fresh, locally sourced ingredients and offer a cozy, authentic ambiance. Visit us today for an unforgettable dining experience.\n3. Menu \n   [{\'name\': \'Coq au Vin\', \'price\': 25, \'description\': \'Classic French dish of chicken slow cooked with wine, mushrooms, and garlic.\'}, {\'name\': \'Ratatouille\', \'price\': 15, \'description\': \'Traditional French vegetable stew topped with fresh herbs.\'}, {\'name\': \'Tarte Tatin\', \'price\': 10, \'description\': \'Upside-down caramelized apple tart served with whipped cream.\'}, {\'name\': \'French Onion Soup\', \'price\': 12, \'description\': \'Hearty onion soup topped with melted cheese and a toasted slice of bread.\'}, {\'name\': \'Croque Monsieur\', \'price\': 10, \'description\': \'A grilled ham and cheese sandwich with a layer of creamy béchamel sauce.\'}, {\'name\': \'Beef Bourguignon\', \'price\': 28, \'description\': \'Slow-cooked beef stew with red wine, mushrooms, and onions.\'}, {\'name\': \'Quiche Lorraine\', \'price\': 10, \'description\': \'Savory pie filled with bacon, cheese, and a creamy custard.\'}, {\'name\': \'Escargots de Bourgogne\', \'price\': 35, \'description\': \'Snails baked in a buttery garlic-parsley sauce.\'}, {\'name\': \'Salade Niçoise\', \'price\': 14, \'description\': \'Classic French salad with tuna, hard-boiled eggs, tomatoes, and olives.\'}, {\'name\': \'Crème Brûlée\', \'price\': 10, \'description\': \'Rich custard topped with a layer of hard caramel.\'}, {\'name\': \'Cheese Plate\', \'price\': 15, \'description\': \'A selection of fine French cheeses served with fresh bread and fruits.\'}]\n4. Comments\n   []\n\nPlease note that comments are merely expressions of personal opinions and are for reference only. Comments can also be time-sensitive. So, a negative comment of a restaurant does not mean it\'s not suitable for you. If you are drawn to its menu and advertisements, don\'t hesitate to give it a try.', 'dish_score': {'Coq au Vin': 0.45, 'Ratatouille': 0.44, 'Tarte Tatin': 0.46, 'French Onion Soup': 0.46, 'Croque Monsieur': 0.46, 'Beef Bourguignon': 0.46, 'Quiche Lorraine': 0.46, 'Escargots de Bourgogne': 0.51, 'Salade Niçoise': 0.46, 'Crème Brûlée': 0.46, 'Cheese Plate': 0.44}}}

test_data2 = [{'Alice': {'restaurant': 'Le Petit Gourmet', 'score': 5, 'comment': "The dishes at Le Petit Gourmet were quite satisfactory, but didn't quite live up to my expectations. The Coq au Vin and Beef Bourguignon, while flavorful, lacked a certain depth to their sauces. The Ratatouille was fresh and colorful, but could use a bit more seasoning, and the Tarte Tatin was a delightful end to the meal. The French Onion Soup was a highlight with its rich and hearty flavor. The service was efficient and polite but lacked warmth. I appreciate the affordable prices and the variety in the menu, but there's room for improvement in terms of the overall taste and dining experience.", 'dishes': ['Coq au Vin', 'Ratatouille', 'Tarte Tatin', 'French Onion Soup', 'Beef Bourguignon'], 'day': 1}}, {'Bob': {'restaurant': 'Le Petit Gourmet', 'score': 4, 'comment': 'The Ratatouille at Le Petit Gourmet was alright but did not meet my expectations. The vegetables were a bit undercooked and lacked flavor. I also found the service to be slow. Despite the affordable prices and the variety in menu, the overall experience was underwhelming. I hope they can improve in these areas.', 'dishes': ['Ratatouille'], 'day': 1}}, {'Charlie': {'restaurant': 'Le Petit Gourmet', 'score': 4, 'comment': "The Salade Niçoise and Croque Monsieur were mediocre, not living up to my expectations in terms of flavor. The quality of the ingredients was good, but they were poorly executed. The salad was too bland and the sandwich, although well-grilled, lacked a depth of flavor. In terms of service, it was decent but not exceptional. The ambiance of the restaurant was cozy and welcoming. However, I believe there's room for improvement in their culinary skills and service quality. I hope they take this feedback into account and improve for a better dining experience.", 'dishes': ['Salade Niçoise', 'Croque Monsieur'], 'day': 1}}]

class Simulation:
    def __init__(self, scenes: List[Scene]):
        self.scenes = scenes   
        self.curr_scene_idx = 0

    def get_curr_scene(self):
        # TODO: graph search
        return self.scenes[self.curr_scene_idx]
    
    def step(self, data):
        """
        Run one step of the simulation
        """
        current_scene = self.get_curr_scene()
        
        # Parallel run scenes & check if all scenes are finished
        max_number_parallel = 6
        with ThreadPoolExecutor(max_workers=max_number_parallel) as executor:
            futures = [executor.submit(lambda: scene.run(data)) for scene in current_scene]
            # Optionally, wait for all scenes to finish and get their results
            results = [future.result() for future in futures]
            print("debugging-results")
            print(results)
            
        next_scene_data = current_scene[0].action_for_next_scene(results)
        
        # loop the scenes
        self.curr_scene_idx = (self.curr_scene_idx + 1) % len(self.scenes)
        
        return next_scene_data
    
    def run(self):
        """
        Main function, run the simulation
        """
        previous_scene_data = None
        while True:  # TODO
            data = self.step(previous_scene_data)
            previous_scene_data = data
    
    @classmethod
    def from_config(cls, config: Union[str, dict, SimulConfig]):
        """
        create an simul from a config
        """
        # If config is a path, load the config
        if isinstance(config, str):
            config = SimulConfig.load(config)
        if isinstance(config, dict):
            config = SimulConfig(config)

        global_prompt = config.get("global_prompt", None)
        database_port = config.get("database_port_base", None)
        log_path = config.get("log_path", None)

        # fill the port map, not a universal code  
        for scene_config in config.scenes:
            if scene_config['scene_type'] == 'restaurant_design':
                for player in scene_config['players']:
                    NAME2PORT[player] = database_port
                    database_port += 1
        
        # Create the players
        players = []
        for player_config in config.players:
            # Add public_prompt to the player config
            if global_prompt is not None:
                player_config["global_prompt"] = global_prompt

            player = Player.from_config(player_config)
            players.append(player)

        # Check that the player names are unique
        player_names = [player.name for player in players]
        assert len(player_names) == len(set(player_names)), "Player names must be unique"

        # Create scenes and decide their order
        scenes = []
        for scene_config in config.scenes:
            same_scene = []
            scene_config['log_path'] = log_path
            for i, player in enumerate(scene_config['players']):   
                scene_config['id'] = i
                # a single player or a group of players
                if isinstance(player, str):
                    assert player in player_names, f"Player {player} is not defined"
                    scene_config["players"] = [players[player_names.index(player)]]
                    scene = load_scene(scene_config)
                elif isinstance(player, list):
                    assert all(p in player_names for p in player), f"Player {player} is not defined"
                    scene_config["players"] = [players[player_names.index(p)] for p in player]
                    scene = load_scene(scene_config)
                same_scene.append(scene)
            scenes.append(same_scene)

        return cls(scenes)