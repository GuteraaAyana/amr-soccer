import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
import tqdm
import networkx as nx
from collections import defaultdict

# import utils

def read_game_file(name):
    """params: name - name of the file to open, do not include .json

    returns text of game data file"""
    if 'json' in name:
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
            'posession_team': goal_team,
            'team': team,
            'scorer': goal_scorer,
            'minute': goal_minute,
            'events_before_goal': events_before_goal
        }

    return goal_details


def get_goal_details_for_matches(match_ids, n_events=5):
    """
    Get goal details for a list of matches.
    
    Args:
        match_ids (list): A list of match ids.
        n_events (int): The number of events to include before each goal.
        
    Returns:
        dict: A dictionary where the keys are match ids and the values are dictionaries of goal details for each match.
    """
    goal_details_all_matches = {}

    for match_id in tqdm.tqdm(match_ids):
        game = read_game_file(str(match_id))
        goal_details = get_goal_details(game, n_events)
        goal_details_all_matches[match_id] = goal_details

    return goal_details_all_matches

def create_event_network(goal_details_all_matches):
    """
    Create a directed network of events leading to goals.

    Args:
        goal_details_all_matches (dict): A dictionary where the keys are match ids and the values are dictionaries of goal details for each match.

    Returns:
        nx.DiGraph: A directed network where the nodes are event types and the edges are the transitions between event types leading to goals.
    """
    event_network = nx.DiGraph()
    event_pairs = defaultdict(int)

    for match_id in goal_details_all_matches.keys():
        for goal in goal_details_all_matches[match_id].values():
            events = goal['events_before_goal']
            scoring_team = goal['team']
            for i in range(len(events) - 1):
                event_type_1 = f"{events[i]['team']['name'] == scoring_team}_{events[i]['type']['name']}"
                event_type_2 = f"{events[i + 1]['team']['name'] == scoring_team}_{events[i + 1]['type']['name']}"
                event_pairs[(event_type_1, event_type_2)] += 1

    for (event_type_1, event_type_2), weight in event_pairs.items():
        event_network.add_edge(event_type_1, event_type_2, weight=weight)

    return event_network

def get_event_occurrences(goal_details_all_matches):
    """
    Get the occurrences of each event type before a goal.

    Args:
        goal_details_all_matches (dict): A dictionary where the keys are match ids and the values are dictionaries of goal details for each match.

    Returns:
        dict: A dictionary where the keys are event types and the values are the number of times that event occurred before a goal.
    """
    event_occurrences = defaultdict(int)
    for match_id in goal_details_all_matches.keys():
        for goal in goal_details_all_matches[match_id].values():
            events = goal['events_before_goal']
            scoring_team = goal['team']
            for event in events:
                event_type = f"{event['team']['name'] == scoring_team}_{event['type']['name']}"
                event_occurrences[event_type] += 1
    return event_occurrences


def main():
    # read in competitions
    print('reading in competitions')
    with open(f'../data/competitions.json') as f:
        competitions = json.load(f)

    # find all Premier League
    prem_id = [c for c in competitions if c['competition_name'] == 'Premier League'][0]['competition_id']
    # get the 2015/2016 season
    prem_2015_2016 = [c for c in competitions if c['competition_id'] == prem_id and c['season_name'] == '2015/2016'][0]['season_id']

    # read in all the matches from the 2015/2016 season
    with open(f'../data/matches/{prem_id}/{prem_2015_2016}.json') as f:
        matches = json.load(f)
    matches = pd.DataFrame(matches)

    # get all the match ids
    match_ids =  matches.match_id.values 
    print('getting goal details for selected matches')
    goal_details_all_matches = get_goal_details_for_matches(match_ids)

    print('Making event network')
    event_network = create_event_network(goal_details_all_matches)

    event_occurrences = get_event_occurrences(goal_details_all_matches)

    # Add occurrences as node attributes
    for event_type, occurrence in event_occurrences.items():
        event_network.nodes[event_type]['occurrence'] = occurrence

    # run page rank on the network
    event_page_rank = nx.pagerank(event_network, weight='weight')
    # sort the page rank
    sorted_event_page_rank = sorted(event_page_rank.items(), key=lambda x: x[1], reverse=True)
    # Create a horizontal bar chart of the sorted page rank
    event_types = [event[0] for event in sorted_event_page_rank]
    page_ranks = [event[1] for event in sorted_event_page_rank]
    colors = ['skyblue' if event.split('_')[0] == 'True' else 'salmon' for event in event_types]


    plt.figure(figsize=(10, 8))
    plt.barh(event_types, page_ranks, color=colors)
    plt.xlabel('Page Rank')
    plt.ylabel('Event Type')
    plt.title('Page Rank of Event Types Leading to Goals')
    plt.gca().invert_yaxis()  # Highest page rank on top
    plt.tight_layout()
    plt.show()

    # print(sorted_event_page_rank)

    # Draw the network
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(event_network, seed=42)
    # plot with node size proportional to occurrence
    nx.draw(event_network, pos, with_labels=True, node_color='skyblue', font_size=10, font_weight='bold', edge_color='gray', node_size=100)
    edge_labels = nx.get_edge_attributes(event_network, 'weight')
    nx.draw_networkx_edge_labels(event_network, pos, edge_labels=edge_labels)
    plt.title('Event Network Leading to Goals')
    plt.show()


if __name__ == '__main__':
    main()