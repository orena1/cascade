"""Useful lookup dicts for general calculations and plotting ease."""

color_dict = {'plus': [0.46, 0.85, 0.47, 1],
     'minus': [0.84, 0.12, 0.13, 1],
     'neutral': [0.28, 0.68, 0.93, 1],
     'learning': [34/255, 110/255, 54/255, 1],
     'reversal': [173/255, 38/255, 26/255, 1],
     'gray': [163/255, 163/255, 163/255, 1]}

lookup = {'OA27': {'plus': 270, 'minus': 135, 'neutral': 0},
     'VF226': {'plus': 0, 'minus': 270, 'neutral': 135},
     'OA67': {'plus': 0, 'minus': 270, 'neutral': 135},
     'OA32': {'plus': 135, 'minus': 0, 'neutral': 270},
     'OA34': {'plus': 270, 'minus': 135, 'neutral': 0},
     'OA36': {'plus': 0, 'minus': 270, 'neutral': 135},
     'OA26': {'plus': 270, 'minus': 135, 'neutral': 0}}

lookup_ori = {'OA27': {270: 'plus', 135: 'minus', 0: 'neutral'},
     'VF226': {0: 'plus', 270: 'minus', 135: 'neutral'},
     'OA67': {0: 'plus', 270: 'minus', 135: 'neutral'},
     'OA32': {135: 'plus', 0: 'minus', 270: 'neutral'},
     'OA34': {270: 'plus', 135: 'minus', 0: 'neutral'},
     'OA36': {0: 'plus', 270: 'minus', 135: 'neutral'},
     'OA26': {270: 'plus', 135: 'minus', 0: 'neutral'}}