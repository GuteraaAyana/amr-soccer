from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
import random, json, tqdm, os
from operator import itemgetter

def read_game_file(name):
    """params: name - name of the file to open, do not include .json

    returns text of game data file"""
    if 'json' in name:
        with open(f"../data/events/{name}") as f:
                    return json.load(f)
    else:
        with open(f"../data/events/{name}.json") as f:
            return json.load(f)

def extract_intervals(match_ids):
    tb = {'same_team': [],
        'opposing_team': [],
        'time_left': []}

    for file in tqdm.tqdm(match_ids):
        f = get_time_between(file)
        tb['same_team'].extend(f['same_team'])
        tb['opposing_team'].extend(f['opposing_team'])
        if f['time_left'] is not None:
            tb['time_left'].append(f['time_left'])


    return tb


def display_figure(tb: dict, freq: bool = True, st: bool = True, ot: bool = True, tl: bool = True):
    """
    Display a stacked bar chart based on the counts of events (same_team, opposing_team, and time_left) 
    present in the given dictionary. Each of these categories can be toggled on or off via boolean flags.

    Parameters
    ----------
    tb : dict
        A dictionary expected to have the keys 'same_team', 'opposing_team', and 'time_left'. Each key 
        should map to an iterable (e.g., list) of timestamps or indices that can be counted.
    freq : bool, optional
        Whether to display as a relative frequency bar chart (True) or direct counts (False). Default is True.
    st : bool, optional
        Whether to include the same_team data in the bar chart. Default is True.
    ot : bool, optional
        Whether to include the opposing_team data in the bar chart. Default is True.
    tl : bool, optional
        Whether to include the time_left data in the bar chart. Default is True.

    Returns
    -------
    None
        This function displays a matplotlib figure with a stacked bar chart and does not return anything.

    Notes
    -----
    - The bars are stacked in the following order from the bottom:
        1. time_left (cyan)
        2. same_team (blue)
        3. opposing_team (red)
    - The x-axis spans from 0 up to the maximum timestamp found in any of the three categories, plus 1.
    - The heights for each bar segment are counted via `collections.Counter`.
"""
    same_team = Counter(tb['same_team'])
    opposing_team = Counter(tb['opposing_team'])
    time_left = Counter(tb['time_left'])
    plt.figure(figsize=(10,6))

    # x = sorted(set(same_team.keys()).union(opposing_team.keys()).union(time_left.keys()))
    x = np.arange(0, max(list(same_team.keys())+list(opposing_team.keys())+list(time_left.keys()))+1)

    def get_heights(counter, b):
        if b:
            heights = np.array([counter.get(timestamp, 0) for timestamp in x])
        else:
            heights = np.array([0 for _ in x])

        return heights


    same_team_heights = get_heights(same_team, st)
    opposing_team_heights = get_heights(opposing_team, ot)
    time_left_heights = get_heights(time_left, tl)
    
    ylabel = 'Number of Goals'
    total_height = sum(same_team_heights+opposing_team_heights+time_left_heights)
    print(total_height)
    
    if freq:
        same_team_heights = same_team_heights / total_height
        opposing_team_heights = opposing_team_heights / total_height
        time_left_heights = time_left_heights / total_height
        ylabel = 'Relative Frequency'


    if tl:
        plt.plot([x[index] for (index, time) in enumerate(time_left_heights) if time != 0], [time for time in time_left_heights if time != 0], color='#2E8B57', label='Remaining Match Time at Last Goal') # shorten name
    if st:
        plt.plot([x[index] for (index, time) in enumerate(same_team_heights) if time != 0], [time for time in same_team_heights if time != 0],  color='#6A5ACD', label='Same Team Scored') # bottom=time_left_heights,
    if ot:
        plt.plot([x[index] for (index, time) in enumerate(opposing_team_heights) if time != 0], [time for time in opposing_team_heights if time != 0], color='#FF7F50', label='Opposing Team Scored') # bottom=(time_left_heights+same_team_heights),

    plt.title("Time Intervals Between Goals and Remaining Match Time")

    plt.legend()
    plt.xlabel('Time Interval (minutes)')
    
    plt.ylabel(ylabel)

    # plt.yscale('log')
    
    return same_team_heights, opposing_team_heights, time_left_heights, total_height


def get_simulated_time_between(game):
    same_team_intervals = []
    opposing_team_intervals = []

    all_goals = game['all_goals']
    team1_goals = game['team1']
    team2_goals = game['team2']

    for i in range(1, len(all_goals)):
        cg = all_goals[i]
        pg = all_goals[i-1]
        interval = cg[0] - pg[0]
        
        if cg in team1_goals and pg in team1_goals or cg in team2_goals and pg in team2_goals:
            same_team_intervals.append(interval)
        
        else:
            opposing_team_intervals.append(interval)


    if len(all_goals) > 0:
        length_of_match = 90

        time_left = length_of_match - game['all_goals'][-1][0]
    
    else:
        time_left = None


    return {'same_team': same_team_intervals, 
            'opposing_team': opposing_team_intervals,
            'time_left': time_left} 


def create_null_model(persec, num_games=100):
    simulated_goal_data = []

    for _ in tqdm.tqdm(range(num_games)):
        game = {'team1': [], 'team2': [], 'all_goals': []}
        for minute in range(1, 91):
            count = 0
            for _ in range(0, 60):
                r2 = random.random()
                if r2 <= persec:
                    r1 = random.random()
                    if r1 < 0.5:
                        game['team1'].append((minute, count))
                    
                    else:
                        game['team2'].append((minute, count))
                    
                    game['all_goals'].append((minute, count))
                    count += 1

        simulated_goal_data.append(game)



    tb_sim = {'same_team': [],
            'opposing_team': [],
            'time_left': []}

    for game in simulated_goal_data:
        between = get_simulated_time_between(game)
        tb_sim['same_team'].extend(between['same_team'])
        tb_sim['opposing_team'].extend(between['opposing_team'])
        if between['time_left'] is not None:
            tb_sim['time_left'].append(between['time_left'])

    return tb_sim

def get_time_between(file):
    if type(file) is str:
        fname = file
        file = read_game_file(file)

    goal_data = {'team1' : file[0]['team']['name'], 'team2' : file[1]['team']['name']}
    team1_goals = [] # {"timestamp" : time, "restart" : timestamp of restart}
    team2_goals = []

    stoppage_time = 0
    for i in range(len(file)):
        event = file[i]
        if event['period'] in (1, 2): # only first and second half goals

            # if event['period'] == 1:
            #     if event['minute'] > first_half_end_time:
            #         first_half_end_time = event['minute']

            if not stoppage_time and event['period'] == 2: # add to timestamp
                stoppage_time = file[i-1]['minute'] - 44

            if event['type']['name'] == 'Shot':
                if event['shot']['outcome']['name'] == 'Goal':
                    timestamp = event['minute'] + 1 + stoppage_time
                    restart = file[i+2]['minute'] + 1 + stoppage_time
                    
                    d = {'timestamp' : timestamp, 'restart' : restart}

                    if goal_data['team1'] == event['team']['name']:
                        team1_goals.append(d)

                    else:
                        team2_goals.append(d)


    goal_data['team1_goals'] = team1_goals
    goal_data['team2_goals'] = team2_goals
    all_goals = sorted(team1_goals + team2_goals, key=itemgetter('timestamp'))
    goal_data['all_goals'] = all_goals

    same_team_intervals = []
    opposing_team_intervals = []

    if len(all_goals) > 0:
        length_of_match = file[-1]['minute'] + 2 + stoppage_time

        time_left = length_of_match - goal_data['all_goals'][-1]['restart']
    
    else:
        time_left = None

    try:
        if len(all_goals) > 1:
            for i in range(1, len(all_goals)):
                cg = all_goals[i]
                pg = all_goals[i-1]
                interval = cg['timestamp'] - pg['restart']

                if cg in team1_goals and pg in team1_goals or cg in team2_goals and pg in team2_goals:
                    same_team_intervals.append(interval)
                
                else:
                    opposing_team_intervals.append(interval)

    except TypeError:
        print(cg, pg, fname)
        raise Exception

    
    return {'goal_data': goal_data, 
            'same_team': same_team_intervals, 
            'opposing_team': opposing_team_intervals,
            'time_left': time_left}

def get_file_names(competition_id=None, season_id=None, directory_path='../data/events'):

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

def extract_goal_data(match_ids):
    goal_timestamps = []
    for match_id in tqdm.tqdm(match_ids):
        game = read_game_file(match_id)
        stoppage_time = 0
        for i in range(len(game)):
            event = game[i]
            if event['period'] in (1, 2): # only first and second half goals

                # if event['period'] == 1:
                #     if event['minute'] > first_half_end_time:
                #         first_half_end_time = event['minute']

                if not stoppage_time and event['period'] == 2: # add to timestamp
                    stoppage_time = game[i-1]['minute'] - 44

                if event['type']['name'] == 'Shot':
                    if event['shot']['outcome']['name'] == 'Goal':
                        timestamp = event['minute'] + 1 + stoppage_time

                        goal_timestamps.append(timestamp)


    return goal_timestamps


def display_goal_freq(goal_timestamps, freq=True):

    height = Counter(goal_timestamps)
    x = np.arange(1, max(list(height.keys()))+1)
    height = np.array([height.get(timestamp, 0) for timestamp in x])
    if freq:
        height = height / sum(height)
        l = 'Relative Frequency of Goals'
    else:

        l = 'Number of Goals'
    

    plt.figure(figsize=(10, 6))


    plt.xticks(np.arange(0, x[-1]+1, 10))
    plt.plot(x, height, label=f'{l} vs Timestamp')
    plt.xlabel('Timestamp (minute)')
    plt.ylabel(l)
    plt.title(f'{l} vs Timestamp (minutes)')


if __name__ == "__main__":
    # tb = extract_intervals(get_file_names())
    # same_team_heights, opposing_team_heights, time_left_heights, total_height = display_figure(tb)
    # persec = total_height / 3433 / 90 / 60
    # display_figure(create_null_model(persec, 100000))
    display_goal_freq(extract_goal_data(get_file_names()))
    plt.show()