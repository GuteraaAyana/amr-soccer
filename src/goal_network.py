import json, os, tqdm
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout
import numpy as np
from matplotlib.lines import Line2D
from pprint import pprint


class TrieNode:
    def __init__(self, event_name, team_label):
        self.event_name = event_name
        self.team_label = team_label
        self.children = {}  # (event_name, team_label) -> TrieNode
        self.frequency = 0  # how many paths pass through this node



def get_file_names(competition_id=None, season_id=None, directory_path='../data/events'):
    print('getting file names')
    file_names = []

    if competition_id and not season_id:
        directory_path = f'../data/matches/{competition_id}'
        for file_name in [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]:
            with open(f'../data/matches/{competition_id}/{file_name}') as f:
                for item in json.load(f):
                    file_names.append(str(item['match_id']))

    elif not competition_id and season_id:
        directory_path = f'../data/matches'
        for folder in [f for f in os.listdir(directory_path)]:
            try:    
                with open(f'../data/matches/{folder}/{season_id}.json') as f:
                    for item in json.load(f):
                        file_names.append(str(item['match_id']))

            except FileNotFoundError:
                continue

    elif competition_id and season_id:
        directory_path = f'../data/matches/{competition_id}/{season_id}.json'
        with open(directory_path) as f:
            for item in json.load(f):
                file_names.append(str(item['match_id']))
        

    else:
        full_file_names = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        file_names = [f.split('.')[0] for f in full_file_names]


    return file_names

def read_game_file(name):
    """params: name - name of the file to open

    returns text of game data file"""
    if 'json' in str(name):
        with open(f"../data/events/{name}") as f:
                    return json.load(f)
    else:
        with open(f"../data/events/{name}.json") as f:
            return json.load(f)
        

def find_goal_indices(game):
    """
    Find the indices of all goal events in a game.

    Args:
        game (list): A list of event dictionaries representing the game.

    Returns:
        list: A list of indices where goals occurred in the game.
    """
    goal_indices = [event['index'] for event in game if event['type']['name'] == 'Shot' and event['shot']['outcome']['name'] == 'Goal']
    return goal_indices

def get_goal_details(game, n_events):
    """
    Get details about each goal in a game.

    Args:
        game (list): A list of event dictionaries representing the game.
        n_events (int): The number of events to include before each goal.

    Returns:
        dict: A dictionary where the keys are the indices of goals and the values are dictionaries with details about each goal.
    """
    game = read_game_file(game)
    goal_indices = find_goal_indices(game)
    goal_details = {}

    for goal_index in goal_indices:
        goal_event = [event for event in game if event['index'] == goal_index][0]
        goal_team = goal_event['possession_team']['name']
        team = goal_event['team']['name']
        goal_scorer = goal_event['player']['name']
        goal_minute = goal_event['minute']
        events_before_goal = game[max(0, goal_index - n_events):goal_index]


        goal_details[goal_index] = {
            'possession_team': goal_team,
            'team': team,
            'scorer': goal_scorer,
            'minute': goal_minute,
            'events_before_goal': events_before_goal
        }

    return goal_details


def extract_paths(match_ids, n_events):
    paths = []
    print("extracting paths")
    for match_id in tqdm.tqdm(match_ids):
        goal_details = get_goal_details(match_id, n_events)
        for goal in goal_details:
            goal_data = goal_details[goal]
            temp = [("Goal", True)]
            scoring_team = goal_data['team']
            for i in range(len(goal_data['events_before_goal'])-1, -1, -1):
                event = goal_data['events_before_goal'][i]
                event_name = event['type']['name']
                same_team = scoring_team == event['team']['name']
                temp.append((event_name, same_team))

            paths.append(temp)

    return paths

def get_goal_details_possesion(game, max_steps):
    game = read_game_file(game)
    goal_indices = find_goal_indices(game)
    goal_details = {}

    for goal_index in goal_indices:
        goal_event = [event for event in game if event['index'] == goal_index][0]
        possession_team = goal_event['possession_team']['name']
        team = goal_event['team']['name']
        goal_scorer = goal_event['player']['name']
        goal_minute = goal_event['minute']

        possession_number = goal_event['possession']


        events_before_goal = []
        index = goal_index-1
        current_event = game[index]
        while possession_number == current_event['possession']:
            events_before_goal.insert(0, current_event)
            index -= 1
            current_event = game[index] 
            if max_steps != 0:
                if goal_index - index > max_steps:
                    break



        goal_details[goal_index] = {
            'possession_team': possession_team,
            'team': team,
            'scorer': goal_scorer,
            'minute': goal_minute,
            'events_before_goal': events_before_goal
        }

    return goal_details

def extract_paths_possession(match_ids, max_steps=15):
    paths = []
    print("extracting paths")
    for match_id in tqdm.tqdm(match_ids):
        goal_details = get_goal_details_possesion(match_id, max_steps)
        for goal in goal_details:
            goal_data = goal_details[goal]
            temp = [("Goal", True)]
            scoring_team = goal_data['team']
            for i in range(len(goal_data['events_before_goal'])-1, -1, -1):
                event = goal_data['events_before_goal'][i]
                event_name = event['type']['name']
                same_team = scoring_team == event['team']['name']
                temp.append((event_name, same_team))

            paths.append(temp)

    return paths

def create_event_network_trie(all_path_details, root_node=TrieNode("Goal", True)):
    event_network = nx.DiGraph()

    print("creating network")
    for path_to_goal in tqdm.tqdm(all_path_details):
        current_node = root_node 
        current_node.frequency += 1 # root node frequency goes up by 1
        for (event_name, same_team) in path_to_goal[1:]: # same team is boolean
            key = (event_name, same_team) # to add to the current node's children dictionary
            if key not in current_node.children: # if the child node doesnt exist yet, add it
                current_node.children[key] = TrieNode(event_name, same_team)
            
            current_node = current_node.children[key]
            current_node.frequency += 1

    node_id_counter = [0]  # use list to avoid nonlocal/global issues

    def build_graph(current):
        current_id = node_id_counter[0]
        node_id_counter[0] += 1
        # Store event name, team, and frequency in node attributes
        event_network.add_node(current_id, event=current.event_name, team=current.team_label, freq=current.frequency)
        for (_, _), child in current.children.items():
            child_id = build_graph(child)
            # current -> child
            event_network.add_edge(current_id, child_id)
 
        return current_id
    
    root_id = build_graph(root_node)

    return event_network, root_id

    
def display_network(event_network, MIN_NODE_SIZE=20, node_size_factor=10000, display_labels=True, trie=True):
    print("displaying network")
    if trie:
        pos = graphviz_layout(event_network, prog="twopi", root=0)
    else:
        pos = nx.circular_layout(event_network)


    generic_node = event_network.nodes[list(event_network.nodes.keys())[0]]
    if 'team' in generic_node:
        node_colors = []

        for node, data in event_network.nodes(data=True):
            team_label = data['team']
            if team_label: # same team
                c = 'teal'
            else:           # dif team
                c = 'crimson'

            if data['event'] == 'Goal':
                c = 'gold'

            elif data['event'] == 'Possession End':
                c = 'magenta'

            node_colors.append(c)

    else:
        node_colors = 'lightblue'

    labels = {}
    for node, data in event_network.nodes(data=True):
        if 'event' in data:
            labels[node] = data['event']
        else:
            # Use the node's name if 'event' doesn't exist
            labels[node] = str(node)

    if 'freq' in generic_node:
        node_sizes = []
        for node, data in event_network.nodes(data=True):
            freq = data.get('freq', 1)
            size = max(MIN_NODE_SIZE, freq)
            node_sizes.append(size)

        m = max(node_sizes)
        for i, size in enumerate(node_sizes):
            node_sizes[i] = max(MIN_NODE_SIZE, size / m * node_size_factor) 

    elif 'weight' in generic_node:
        node_sizes = []
        for node, data in event_network.nodes(data=True):
            weight = data.get('weight', 1) 
            size = max(MIN_NODE_SIZE, weight)
            node_sizes.append(size)

        m = max(node_sizes)
        for i, size in enumerate(node_sizes):
            node_sizes[i] = max(MIN_NODE_SIZE, size / m * node_size_factor) 

    else:
        node_sizes = MIN_NODE_SIZE

    print(max(node_sizes))
    plt.figure(figsize=(10, 10))

    # Draw the nodes and edges
    nx.draw_networkx_nodes(event_network, pos, node_size=node_sizes, node_color=node_colors, alpha=0.8)
    nx.draw_networkx_edges(event_network, pos, arrowstyle="<-", arrowsize=15, edge_color="slategray", node_size=node_sizes, alpha=0.7,
                       connectionstyle='arc3,rad=0.2')
    
    if display_labels:
        
        for (i, (node, data)) in enumerate(event_network.nodes(data=True)):
            x, y = pos[node]
            # label text
            label_text = labels[node] if node in labels else str(node)
            # scale font size with node size
            current_node_size = node_sizes[i] if isinstance(node_sizes, list) else node_sizes
            font_size = min(current_node_size/4, 12)

            # Manually place label
            plt.text(
                x, y,
                label_text,
                fontsize=font_size,
                ha='center', va='center',
                color='black'
            )

    # Remove the axis for a cleaner look
    plt.axis("off")
    plt.tight_layout()



def pagerank(event_network, merge=True):
    pr_scores = nx.pagerank(event_network)

    if merge:
        merged_scores = {}
        for node, score in pr_scores.items():
            event = event_network.nodes[node]['event']
            team = event_network.nodes[node]['team']

            if event not in merged_scores:
                merged_scores[event] = {True: 0.0, False: 0.0}

            # Accumulate the PageRank score for this (event, team) pair
            merged_scores[event][team] += score

        return merged_scores
    
    else:
        return pr_scores


def pagerank_barchart(pagerank_scores, number_to_display=10, group_teams=False, title="PageRank Scores of Events Leading to Goals"):
    """
    Displays a vertical bar chart of the PageRank scores, grouped by 'event' 
    and 'team'. 

    Coloring scheme:
        - if team == True, color = teal
        - Else if team == False, color = crimson

    Parameters
    ----------
    pagerank_scores : dict
        Nested dictionary in the form:
            {
                event_value_1: {True: total_score, False: total_score},
                event_value_2: {True: total_score, False: total_score},
                ...
            }
    """
    data = []
    found_team = False  # track if we ever see a dict with True/False

    for event, value in pagerank_scores.items():
        if isinstance(value, dict):
            # We have {True: score, False: score}
            # Add each (event, team_bool, score)
            if not group_teams:
                for team_bool, score in value.items():
                    data.append((event, team_bool, score))
                found_team = True
            else:
                data.append((event, None, value[True]+value[False]))
        else:
            # Single numeric score => (event, None, score)
            data.append((event, None, value))

    # 2. Sort by score in descending order
    data.sort(key=lambda x: x[2], reverse=True)

    # 3. Take the top 10
    top_10_data = data[:number_to_display]

    # Prepare lists for plotting
    labels = []
    scores = []
    colors = []
    for event, team, score in top_10_data:

        labels.append(event)
        scores.append(score)
        if found_team:
            colors.append("teal" if team else "crimson")
        
        else:
            colors.append('lightblue')

    # 4. Create a horizontal bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    y_positions = range(len(top_10_data))

    # Horizontal bar chart
    ax.barh(y_positions, scores, color=colors)
    
    # Make sure the y-axis has the labels we constructed
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    
    # Invert y-axis so the highest value is at the top (optional)
    ax.invert_yaxis()

    # 5. Add a legend
    if 'teal' in colors or 'crimson' in colors:
        legend_elements = [
            Line2D([0], [0], color='teal', lw=6, label='Scoring Team'),
            Line2D([0], [0], color='crimson', lw=6, label='Conceding Team')
        ]
        ax.legend(handles=legend_elements, loc='best')

    # 6. Label axes and add a title
    ax.set_xlabel("PageRank Score")
    ax.set_ylabel("Events")
    ax.set_title(title)

    # Improve layout and show
    plt.tight_layout()


def extract_all_events_paths(match_ids):
    paths = []
    print('extracting all paths')
    for match_id in tqdm.tqdm(match_ids):
        game = read_game_file(match_id)
        paths.append([event['type']['name'] for event in game])


    return paths
            


def create_all_events_network(all_path_details):
    event_network = nx.DiGraph()

    print('creating network')

    for path in tqdm.tqdm(all_path_details):
        for i in range(len(path) - 1):
            event1 = path[i]
            event2 = path[i + 1]
            
            # Add / update edge weight
            if event_network.has_edge(event1, event2):
                event_network[event1][event2]['weight'] += 1
            else:
                event_network.add_edge(event1, event2, weight=1)
            
            # Increment node weight for 'event2'
            if 'weight' not in event_network.nodes[event2]:
                event_network.nodes[event2]['weight'] = 0
            event_network.nodes[event2]['weight'] += 1

            # Increment node weight for 'event1'
            if 'weight' not in event_network.nodes[event1]:
                event_network.nodes[event1]['weight'] = 0
            event_network.nodes[event1]['weight'] += 1

    return event_network

def extract_all_trie(match_ids, max_steps=3):
    paths = []
    print('extracting all paths')
    for match_id in tqdm.tqdm(match_ids):
        file = read_game_file(match_id)
        temp = []
        current_possession = -1


        for event in file:
            event_possession = event['possession']

            if len(temp) > 0 and current_possession != event_possession:
                current_possession = event_possession
                temp.append(('Possession End', None))
                if len(temp) > max_steps:
                    temp = temp[-max_steps:]
                paths.append(list(reversed(temp)))
                temp = []

            if event['team']['name'] == event['possession_team']['name']:
                team = True
            else:
                team = False
            temp.append((event['type']['name'], team))

    return paths






if __name__ == "__main__":
    bundesliga2324 = get_file_names(9, 281)
    all_games = get_file_names()

    files = bundesliga2324
    # event_network, _ = create_event_network_trie(extract_paths_possession(files, max_steps=0))
    # all_events_network = create_all_events_network(extract_all_events_paths(files))

    # pagerank_barchart(pagerank(event_network), title="PageRank Scores of Events Leading to Goals, Teams Combined", group_teams=True)
    # pagerank_barchart(pagerank(all_events_network, merge=False), title="Events in a Game")


    # network_to_display, _ = create_event_network_trie(extract_paths_possession(files, max_steps=3))
    # display_network(network_to_display)
    # display_network(all_events_network, trie=False)

    print(extract_all_trie(files))
    display_network(create_event_network_trie(extract_all_trie(files), TrieNode("Possession End", None))[0])

    plt.show()









# is the event or the sequence more important?