import json, os, sys, math
import matplotlib.pyplot as plt
import numpy as np
from pprint import pp
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
        
def get_goal_data(file):
    """
    """
    if type(file) is str:
        file = read_game_file(file)
        
    goal_data = {'team1' : file[0]['team']['name'], 'team2' : file[1]['team']['name']}
    team1_goals = [] # {"timestamp" : time, "id" : id}
    team2_goals = []
    
    for event in file:
        if event['type']['name'] == 'Shot':
            if event['shot']['outcome']['name'] == 'Goal':
                timestamp = event['minute'] + 1
                id = event['id']
                d = {'timestamp' : timestamp, 'id' : id}

                if goal_data['team1'] == event['team']['name']:
                    team1_goals.append(d)

                else:
                    team2_goals.append(d)


    goal_data['team1_goals'] = team1_goals
    goal_data['team2_goals'] = team2_goals
    goal_data['all_goals'] = team1_goals + team2_goals

    return goal_data

def get_pass_data(file):
    """params: enter file name w/o extensions, team1 is the first team on the file, team2 is the second team on the file
        
    returns pass data as keyed dictionary (#total passes, #ground passes, #low passes, #high passes, aver pass length)"""
    try:
        game = read_game_file(file)
    except FileNotFoundError:
        return "File not found. Ensure you typed a string and not a integer"
    
    pass_count,av_leng,ground_pass_count,low_pass_count,high_pass_count,team1_passes,team2_passes = (0 for _ in range(7))
    team1, team2 = get_teams(file)

    for event in game:
        if event['type']['id'] == 30:
            pass_count += 1
            av_leng += event['pass']['length']
            if event['possession_team']['name'] == team1:
                team1_passes += 1
            else:
                team2_passes += 1

            if event['pass']['height']['id'] == 1:
                ground_pass_count += 1
            elif event['pass']['height']['id'] == 2:
                low_pass_count += 1
            else:
                high_pass_count += 1

    av_leng = round(av_leng/pass_count, 2)
    pass_data = {"Total Passes" : pass_count, f"{team1} Passes" : team1_passes, f"{team2} Passes" : team2_passes, "Ground Passes" : ground_pass_count, "Low Passes" : low_pass_count, "High Passes" : high_pass_count, "Average Pass Length" : av_leng}
    return pass_data

def get_shot_map(file, display=True):
    """
    returns two plot maps showing start and end locations of shot attempts made by each team 
    attacking goal to the right, defending goal to the left
    green = goal read = saved/blocked/missed/anything that is not a goal
    """

    game = read_game_file(file)
    team1, team2 = get_teams(file)
    shot_locs = {'start' : {team1 : [], team2 : []}, 'end' : {team1 : [], team2 : []}}
    outcomes = {team1 : [], team2 : []}

    for event in game:
        if event['type']['id'] == 16:
            team = event['possession_team']['name']
            shot_locs['start'][team].append(event['location'])
            shot_locs['end'][team].append(event['shot']['end_location'])
            outcomes[team].append(event['shot']['outcome']['id'])

    if display:
        _, axs_team1 = plt.subplots(figsize=(10,6)) 
        _, axs_team2 = plt.subplots(figsize=(10,6)) 
        axs_team1.set_xlim(0,120)
        axs_team1.set_ylim(80,0)
        axs_team2.set_xlim(0,120)
        axs_team2.set_ylim(80,0)
        axs_team1.set_title(f"{team1} Shot Map ")
        axs_team2.set_title(f"{team2} Shot Map ")

        for i in range(len(shot_locs['start'][team1])):
            col = 'green' if outcomes[team1][i] == 97 else 'red'
            axs_team1.plot([shot_locs['start'][team1][i][0], shot_locs['end'][team1][i][0]], [shot_locs['start'][team1][i][1], shot_locs['end'][team1][i][1]], color=col)
        for j in range(len(shot_locs['start'][team2])):
            col = 'green' if outcomes[team2][j] == 97 else 'red'
            axs_team2.plot([shot_locs['start'][team2][j][0], shot_locs['end'][team2][j][0]], [shot_locs['start'][team2][j][1], shot_locs['end'][team2][j][1]], color=col)
        plt.show()
    return shot_locs

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

def get_passing_map(file, display=True):
    """
    returns two plot maps showing start and end locations of passes made by each team 
    attacking goal to the right, defending goal to the left
    currently, no distiction between start point and end point, in the works
    currently, passes are NOT seperated by half, in the works
    """
    game = read_game_file(file)
    team1,team2 = get_teams(file)

    start_locs_x, start_locs_y, end_locs_x, end_locs_y = ({'team1' : [], 'team2' : []} for _ in range(4))

    for event in game:
        if event['type']['id'] == 30:
            if event['possession_team']['name'] == team1:
                start_locs_x['team1'].append(event['location'][0])
                start_locs_y['team1'].append(-(event['location'][1]))
                end_locs_x['team1'].append(event['pass']['end_location'][0])
                end_locs_y['team1'].append(-(event['pass']['end_location'][1]))
            else:
                start_locs_x['team2'].append(event['location'][0])
                start_locs_y['team2'].append(-(event['location'][1]))
                end_locs_x['team2'].append(event['pass']['end_location'][0])
                end_locs_y['team2'].append(-(event['pass']['end_location'][1]))

    if display:
        _, axs_team1 = plt.subplots(figsize=(10,6)) 
        _, axs_team2 = plt.subplots(figsize=(10,6)) 

        axs_team1.set_xlim(0,120)
        axs_team1.set_ylim(-80,0)
        axs_team2.set_xlim(0,120)
        axs_team2.set_ylim(-80,0)

        for i in range(len(start_locs_x['team1'])):
            axs_team1.plot([start_locs_x['team1'][i], end_locs_x['team1'][i]], [start_locs_y['team1'][i], end_locs_y['team1'][i]], color='blue')
        for j in range(len(start_locs_x['team2'])):
            axs_team2.plot([start_locs_x['team2'][j], end_locs_x['team2'][j]], [start_locs_y['team2'][j], end_locs_y['team2'][j]], color= 'red')

        axs_team1.set_title(f"{team1} Passing Graph")
        axs_team2.set_title(f"{team2} Passing Graph")

        plt.show()

    return start_locs_x, start_locs_y, end_locs_x, end_locs_y

def get_teams(file):
    game = read_game_file(file)
    team1 = game[0]['team']['name']
    team2 = game[1]['team']['name']
    return team1,team2

def distance(x1, y1, x2, y2, z1=0, z2=0):
    return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)

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


def get_simulated_time_between(game):
    same_team_intervals = []
    opposing_team_intervals = []

    all_goals = game['all_goals']
    team1_goals = game['team1']
    team2_goals = game['team2']

    for i in range(1, len(all_goals)):
        cg = all_goals[i]
        pg = all_goals[i-1]
        interval = cg - pg
        if cg in team1_goals and pg in team1_goals or cg in team2_goals and pg in team2_goals:
            same_team_intervals.append(interval)
        
        else:
            opposing_team_intervals.append(interval)


    if len(all_goals) > 0:
        length_of_match = 90

        time_left = length_of_match - game['all_goals'][-1]
    
    else:
        time_left = None


    return {'same_team': same_team_intervals, 
            'opposing_team': opposing_team_intervals,
            'time_left': time_left} 

    

if __name__ == "__main__":
    # print(read_game_file("7298"))
    # print(get_goal_data("7298.json"))
    # print(get_goal_data(read_game_file("7298")))
    #print(get_file_names(competition_id=37, season_id=4))
    #get_passing_map('7298')
    # print(get_pass_data('7298'))
    # get_shot_map('7298')
    pp(get_time_between("7298"))
