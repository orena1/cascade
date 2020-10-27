"""Functions for analyzing tuning of neurons and TCA components."""
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import numpy as np
import os
from . import load, paths, utils, lookups, bias
from copy import deepcopy
import scipy as sp


def cell_tuning(meta, tensor, model, rank, by_stage=False, by_reversal=False, nan_lick=False,
                staging='parsed_11stage', tuning_type='initial', force_stim_avg=False):
    """
    Function for calculating tuning for different stages of learning for the components
    from TCA.

    If you want it mean "projected" for a component just group the return by 'best component'

    :param meta: pandas.DataFrame, trial metadata
    :param model: tensortools.ensemble, TCA results
    :param rank: int, rank of TCA model to use for components
    :param by_stage: boolean, choose to use stages or simply calculate tuning over all time
    :param by_reversal: boolean, instead of tuning over all time can also split and get two values pre and post reversal
    :param nan_lick: boolean, choose to nan periods of licking (and baseline)
    :param staging: str, binning used to define stages of learning
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: stage_tuning_df: pandas.DataFrame, columns are stages
    """

    # meta can only be a DataFrame of a single mouse
    assert len(meta.reset_index()['mouse'].unique()) == 1
    mouse = meta.reset_index()['mouse'].unique()[0]

    # get tensor-shaped mask of values that exclude licking
    # this accounts for differences in stimulus length between mice
    # baseline is also set to false
    if nan_lick:
        mask = bias.get_lick_mask(meta, tensor)
        ablated_tensor = deepcopy(tensor)
        ablated_tensor[~mask] = np.nan  # this sets baseline to NaN as well
    else:
        ablated_tensor = tensor

    # select rank of model to use
    best_components = utils.define_high_weight_cell_factors(model, rank, threshold=1)
    num_components = utils.count_high_weight_cell_factors(model, rank, threshold=1)
    any_offset_activity = utils.does_cell_participate_in_offset_component(model, rank, mouse, threshold=1)
    offset = np.argmax(model.results[rank][0].factors[1][:, :], axis=0) > 15.5 * (1 + lookups.stim_length[mouse])
    offset_cells = np.isin(best_components, np.where(offset)[0] + 1)  # + 1 to match component number

    df_list = []
    for cell_n in range(tensor.shape[0]):

        if offset_cells[cell_n]:
            if not force_stim_avg:
                # response window
                mean_window = np.arange(np.floor(15.5 * (1 + lookups.stim_length[mouse])),
                                        np.floor(15.5 * (3 + lookups.stim_length[mouse])), dtype='int')
            else:
                # stimulus window
                mean_window = np.arange(16, np.floor(15.5 * (1 + lookups.stim_length[mouse])), dtype='int')
        else:
            # stimulus window
            mean_window = np.arange(16, np.floor(15.5 * (1 + lookups.stim_length[mouse])), dtype='int')

        # take mean of either the stimulus or the response window depending on offset component affiliation
        cell_mat = ablated_tensor[cell_n, mean_window, :]
        trial_avg_vec = np.nanmean(cell_mat, axis=0)

        # calculate tuning either for stages or whole component
        if by_stage:
            tuning_df = tuning_by_stage(meta, trial_avg_vec, staging=staging, tuning_type=tuning_type)
        else:
            if by_reversal:
                tuning_df = tuning_by_reversal(meta, trial_avg_vec, tuning_type=tuning_type)
            else:
                tuning_df = tuning_not_by_stage(meta, trial_avg_vec, tuning_type=tuning_type)

        # add component to index
        tuning_df['best component'] = best_components[cell_n]
        if np.isnan(best_components[cell_n]):
            tuning_df['offset component'] = np.nan
        else:
            tuning_df['offset component'] = offset[int(best_components[cell_n]) - 1]  # bool, nan above makes it float
        tuning_df['offset cell'] = offset_cells[cell_n]
        tuning_df['component participation'] = num_components[cell_n]
        tuning_df['offset participation'] = any_offset_activity[cell_n]
        tuning_df['cell_n'] = cell_n + 1
        tuning_df.reset_index(inplace=True)
        tuning_df.set_index(['mouse', 'cell_n'], inplace=True)
        df_list.append(tuning_df)

    # create final df for return
    tuning_df_all_cells = pd.concat(df_list, axis=0)

    return tuning_df_all_cells


def component_tuning(meta, model, rank, by_stage=False, by_reversal=False, staging='parsed_11stage',
                     tuning_type='initial'):
    """
    Function for calculating tuning for different stages of learning for the components
    from TCA.

    :param meta: pandas.DataFrame, trial metadata
    :param model: tensortools.ensemble, TCA results
    :param rank: int, rank of TCA model to use for components
    :param by_stage: boolean, choose to use stages or simply calculate tuning over all time
    :param by_reversal: boolean, instead of tuning over all time can also split and get two values pre and post reversal
    :param staging: str, binning used to define stages of learning
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: stage_tuning_df: pandas.DataFrame, columns are stages
    """
    # meta can only be a DataFrame of a single mouse
    assert len(meta.reset_index()['mouse'].unique()) == 1
    mouse = meta.reset_index()['mouse'].unique()[0]

    # select rank of model to use
    trial_factors = model.results[rank][0].factors[2]
    offset = np.argmax(model.results[rank][0].factors[1][:, :], axis=0) > 15.5 * (1 + lookups.stim_length[mouse])

    df_list = []
    for comp_n in range(trial_factors.shape[1]):

        # calculate tuning either for stages or whole component
        trial_avg_vec = trial_factors[:, comp_n]
        if by_stage:
            tuning_df = tuning_by_stage(meta, trial_avg_vec, staging=staging, tuning_type=tuning_type)
        else:
            if by_reversal:
                tuning_df = tuning_by_reversal(meta, trial_avg_vec, tuning_type=tuning_type)
            else:
                tuning_df = tuning_not_by_stage(meta, trial_avg_vec, tuning_type=tuning_type)

        # add component to index
        tuning_df['offset component'] = offset[comp_n]
        tuning_df['component'] = comp_n + 1
        tuning_df.reset_index(inplace=True)
        tuning_df.set_index(['mouse', 'component'], inplace=True)
        df_list.append(tuning_df)

    # create final df for return
    tuning_df_all_comps = pd.concat(df_list, axis=0)

    return tuning_df_all_comps


def tuning_by_stage(meta, trial_avg_vec, staging='parsed_11stage', tuning_type='initial'):
    """
    Function for calculating tuning for different stages of learning for the same cell or
    component.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param staging: str, binning used to define stages of learning
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: stage_tuning_df: pandas.DataFrame, columns are stages
    """
    # meta can only be a DataFrame of a single mouse
    assert len(meta.reset_index()['mouse'].unique()) == 1

    # make sure parsed stage exists
    meta = utils.add_stages_to_meta(meta, staging)

    # split meta and trial avg vec by stage
    temp_meta = deepcopy(meta)
    temp_meta['responses for tuning calc'] = trial_avg_vec

    # loop over groupings
    tuning_words = []
    tuning_vecs = []
    response_vecs = []
    stage_words = []
    groupings = temp_meta.groupby(staging)
    for name, gri in groupings:
        stage_vec = gri['responses for tuning calc'].values

        # pass split meta and trial averages to tuning calculations
        tuning_words.append(calc_tuning_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        tuning_vecs.append(cosine_distance_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        response_vecs.append(mean_response_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        stage_words.append(name)

    # create a DataFrame for output
    data = {staging: stage_words, 'preferred tuning': tuning_words, 'cosine tuning': tuning_vecs,
            'mean response': response_vecs}
    stage_tuning_df = pd.DataFrame(data=data)
    stage_tuning_df['mouse'] = meta.reset_index()['mouse'].unique()[0]
    stage_tuning_df.set_index(['mouse'], inplace=True)

    return stage_tuning_df


def tuning_by_reversal(meta, trial_avg_vec, tuning_type='initial'):
    """
    Function for calculating tuning for different stages of learning for the same cell or
    component.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: stage_tuning_df: pandas.DataFrame, columns are stages
    """
    # meta can only be a DataFrame of a single mouse
    assert len(meta.reset_index()['mouse'].unique()) == 1

    # make sure parsed stage still exists, this will be used to find reversal
    meta = utils.add_stages_to_meta(meta, 'parsed_11stage')

    # split meta and trial avg vec by stage
    temp_meta = deepcopy(meta)
    temp_meta['responses for tuning calc'] = trial_avg_vec

    # make learning/reversal1 vec
    temp_meta['learning_reversal1_vec'] = 'learning'
    lr_boolean = temp_meta['parsed_11stage'].apply(lambda x: 'reversal' in x)
    temp_meta.loc[lr_boolean, 'learning_reversal1_vec'] = 'reversal1'

    # loop over groupings
    tuning_words = []
    tuning_vecs = []
    response_vecs = []
    stage_words = []
    groupings = temp_meta.groupby('learning_reversal1_vec')
    for name, gri in groupings:
        stage_vec = gri['responses for tuning calc'].values

        # pass split meta and trial averages to tuning calculations
        tuning_words.append(calc_tuning_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        tuning_vecs.append(cosine_distance_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        response_vecs.append(mean_response_from_meta_and_vec(gri, stage_vec, tuning_type=tuning_type))
        stage_words.append(name)

    # create a DataFrame for output
    data = {'staging_LR': stage_words, 'preferred tuning': tuning_words, 'cosine tuning': tuning_vecs,
            'mean response': response_vecs}
    stage_tuning_df = pd.DataFrame(data=data)
    stage_tuning_df['mouse'] = meta.reset_index()['mouse'].unique()[0]
    stage_tuning_df.set_index(['mouse'], inplace=True)

    return stage_tuning_df


def tuning_not_by_stage(meta, trial_avg_vec, tuning_type='initial'):
    """
    Function for calculating tuning not accounting for stages of learning for the same cell or
    component.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: stage_tuning_df: pandas.DataFrame, columns are stages
    """
    # meta can only be a DataFrame of a single mouse
    assert len(meta.reset_index()['mouse'].unique()) == 1

    # pass split meta and trial averages to tuning calculations
    tuning_words = calc_tuning_from_meta_and_vec(meta, trial_avg_vec, tuning_type=tuning_type)
    tuning_vecs = cosine_distance_from_meta_and_vec(meta, trial_avg_vec, tuning_type=tuning_type)
    response_vecs = mean_response_from_meta_and_vec(meta, trial_avg_vec, tuning_type=tuning_type)

    # create a DataFrame for output
    data = {'preferred tuning': tuning_words, 'cosine tuning': tuning_vecs, 'mean response': response_vecs}
    stage_tuning_df = pd.DataFrame(data=data)
    stage_tuning_df['mouse'] = meta.reset_index()['mouse'].unique()[0]
    stage_tuning_df.set_index(['mouse'], inplace=True)

    return stage_tuning_df


def calc_tuning_from_meta_and_vec(meta, trial_avg_vec, tuning_type='initial'):
    """
    Helper function for calculating the preferred tuning of any vector (trial averaged responses)
    and metadata DataFrame (subset to match vector of responses). Based on initial CS values.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: preferred_tuning: str, string of preferred tuning of this vector
    """

    # calculate cosine distances for respones to each cue compared to canonical basis set of tuning
    distances = cosine_distance_from_meta_and_vec(meta, trial_avg_vec, tuning_type=tuning_type)

    # get conditions
    if 'initial' in tuning_type:
        cond_type = 'initial_condition'
    elif 'ori' in tuning_type:
        cond_type = 'orientation'
    elif tuning_type.lower() == 'cond' or tuning_type.lower() == 'condition':
        cond_type = 'condition'
    else:
        raise NotImplementedError

    u_conds = sorted(meta[cond_type].unique())

    # assume you are getting 3 cues
    assert len(u_conds) == 3

    # pick tuning type
    if np.sum(distances < 0.6) == 1:  # ~ cosine_dist([1, 0], [0.85, 1]) to allow for joint tuning
        preferred_tuning = f'{u_conds[np.argsort(distances)[0]]}'
    elif np.sum(distances < 0.6) == 2:
        preferred_tuning = f'{u_conds[np.argsort(distances)[0]]}-{u_conds[np.argsort(distances)[1]]}'
    elif np.sum(distances == 0) == 3 or np.sum(~np.isfinite(distances)) == 3:
        preferred_tuning = 'none'
    else:
        preferred_tuning = 'broad'

    return preferred_tuning


def cosine_distance_from_meta_and_vec(meta, trial_avg_vec, tuning_type='initial'):
    """
    Helper function for calculating cosine distances
    and metadata DataFrame (subset to match vector of responses). Based on initial CS values.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :return: distances: [float float float], cosine distances
    """

    # get initial conditions
    if 'initial' in tuning_type:
        cond_type = 'initial_condition'
    elif 'ori' in tuning_type:
        cond_type = 'orientation'
    elif tuning_type.lower() == 'cond' or tuning_type.lower() == 'condition':
        cond_type = 'condition'
    else:
        raise NotImplementedError
    u_conds = sorted(meta[cond_type].unique())

    # assume you are getting 3 cues
    assert len(u_conds) == 3

    # rectify vector
    rect_trial_avg_vec = deepcopy(trial_avg_vec)
    rect_trial_avg_vec[rect_trial_avg_vec < 0] = 0

    # get mean response per cue across all trials provided as a single tuning vector
    mean_cue = []
    for cue in u_conds:
        cue_boo = meta[cond_type].isin([cue])
        mean_cue.append(np.nanmean(rect_trial_avg_vec[cue_boo]))

    # get unit vector for tuning vector
    unit_vec_tuning = mean_cue / np.linalg.norm(mean_cue)

    # compare tuning standards for perfect tuning to one of the three cues to tuning vector
    standard_vecs = [np.array([1, 0, 0]), np.array([0, 1, 0]), np.array([0, 0, 1])]
    distances = []
    for standi in standard_vecs:
        # calculate cosine distance by hand (for unit vectors this is just 1 - inner prod)
        distances.append(1 - np.inner(standi, unit_vec_tuning))
    distances = np.array(distances)

    return distances


def mean_response_from_meta_and_vec(meta, trial_avg_vec, tuning_type='initial', rectify=False):
    """
    Helper function for calculating mean response per cue type.

    :param meta: pandas.DataFrame, trial metadata
    :param trial_avg_vec: vector of responses, one per trial, must be same length as meta
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'
    :param rectify: boolean, optionally rectify trace (i.e., negative values set to 0)
    :return: mean_response_vec: [float float float], mean response
    """

    # get initial conditions
    if 'initial' in tuning_type:
        cond_type = 'initial_condition'
    elif 'ori' in tuning_type:
        cond_type = 'orientation'
    elif tuning_type.lower() == 'cond' or tuning_type.lower() == 'condition':
        cond_type = 'condition'
    else:
        raise NotImplementedError
    u_conds = sorted(meta[cond_type].unique())

    # assume you are getting 3 cues
    assert len(u_conds) == 3

    # rectify vector
    if rectify:
        rect_trial_avg_vec = deepcopy(trial_avg_vec)
        rect_trial_avg_vec[rect_trial_avg_vec < 0] = 0
    else:
        rect_trial_avg_vec = trial_avg_vec

    # get mean response per cue across all trials provided as a single tuning vector
    mean_cue = []
    for cue in u_conds:
        cue_boo = meta[cond_type].isin([cue])
        mean_cue.append(np.nanmean(rect_trial_avg_vec[cue_boo]))
    mean_response_vec = np.array(mean_cue)

    return mean_response_vec


def mean_stage_response_preferred_tuning(meta, tensor, tuning_df, staging='parsed_11stage',
                                         tune_staging='parsed_11stage', tuning_type='initial',
                                         filter=False, filter_on=None):
    """

    :param meta: pandas.DataFrame, DataFrame of trial metadata
    :param tensor: numpy.ndarray, a cells x times X trials
    :param tuning_df: pandas.DataFrame, tuning.cell_tuning() output df
    :param staging: str, way to bin stages of learning
    :param tune_staging: str --> 'parsed_11stage' or 'staging_LR'
        Determine how to pick preferred tuning, as only the preferred responses of cells are returned. By default this
        will be evaluate for each stage, but you can also pass a tuning_df that had other tuning calculations.
        For example, 'staging_LR' in tuning_df calculates preferred tuning only for pre and post reversal (not by
        dprime bin).
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'

    # TODO add filtering on running speed, hit miss FA, etc

    :return:
        mouse_stage_responses, numpy.ndarray
            4D matrix (cells, times, stages, cues). Last level of cue is the response for the preferred cue.
        flattened_pref_tuning_mat, numpy.ndarray
            2D matrix (cells, times-x-stages) for preferred cue tuning
        tuning_matrix
            2D matrix of preferred tuning values
    """

    # make sure that you tuning df has the necessary columns
    assert tune_staging in tuning_df.columns

    # get conditions
    if 'initial' in tuning_type:
        cond_type = 'initial_condition'
    elif 'ori' in tuning_type:
        raise NotImplementedError
        # cond_type = 'orientation'
    elif tuning_type.lower() == 'cond' or tuning_type.lower() == 'condition':
        cond_type = 'condition'
    else:
        raise NotImplementedError

    # get the stage order (order of the x axis)
    xorder = utils.lookups.staging[staging]

    # preallocate 4D matrix (cells, times, stages, cues)
    mouse_stage_responses = np.zeros((tensor.shape[0], tensor.shape[1], len(xorder), 4))
    mouse_stage_responses[:] = np.nan

    # get mean of pmn trials for each stage
    for cs, s in enumerate(xorder):
        for cc, icue in enumerate(['plus', 'minus', 'neutral']):
            meta_bool = meta.parsed_11stage.isin([s]) & meta[cond_type].isin([icue])
            cue_stage_tensor = tensor[:, :, meta_bool]
            cue_stage_mean = np.nanmean(cue_stage_tensor, axis=2)
            mouse_stage_responses[:, :, cs, cc] = cue_stage_mean

    # add in a 4th z slice of preferred tuning responses
    tune_up = tuning_df.reset_index()
    for cs, s in enumerate(xorder):
        for cell_n in range(tensor.shape[0]):

            if tune_staging == 'staging_LR':
                # matching parse_11stage entries to learning reversal
                ss = 'reversal1' if 'reversal' in s else 'learning'
                pref_bool = tune_up[tune_staging].isin([ss])
            else:
                # or just parse_11stage entries (effectively allows preferred tuning recalc at each stage of learning)
                pref_bool = tune_up[tune_staging].isin([s])

            pref = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'preferred tuning']

            if len(pref) == 1:
                preferred_tuning = pref.item()
                if preferred_tuning == 'broad':
                    # average across cues for broadly tuned cells
                    mean_resp = np.nanmean(mouse_stage_responses[cell_n, :, cs, :], axis=1)
                    mouse_stage_responses[cell_n, :, cs, 3] = mean_resp
                else:
                    # take single preferred tuning or average across joint tuned cells
                    tuning_levels = np.where([s in preferred_tuning for s in ['plus', 'minus', 'neutral']])[0]
                    tuned_response = np.nanmean(mouse_stage_responses[cell_n, :, cs, tuning_levels], axis=0)
                    mouse_stage_responses[cell_n, :, cs, 3] = tuned_response

    # flatten your preferred stages
    stage_list = []
    for cs, s in enumerate(xorder):
        stage_list.append(mouse_stage_responses[:, :, cs, 3])
    flattened_pref_tuning_mat = np.hstack(stage_list)

    # loop and create vectors of preferred tuning (as test) matiching your flattened preferred tuning matrix
    tune_up = tuning_df.reset_index()
    if tune_staging == 'staging_LR':
        torder = ['learning', 'reversal1']
    else:
        torder = xorder

    tuning_matrix = []
    cosine_matrix = []
    for cs, s in enumerate(torder):

        stage_tune_vec = []
        stage_cos_vec = []
        for cell_n in range(tensor.shape[0]):

            if tune_staging == 'staging_LR':
                # matching parse_11stage entries to learning reversal
                ss = 'reversal1' if 'reversal' in s else 'learning'
                pref_bool = tune_up[tune_staging].isin([ss])
            else:
                # or just parse_11stage entries (effectively allows preferred tuning recalc at each stage of learning)
                pref_bool = tune_up[tune_staging].isin([s])

            pref = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'preferred tuning']
            cos = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'cosine tuning']

            if len(pref) == 1:
                stage_tune_vec.append(pref.iloc[0])
            else:
                stage_tune_vec.append('none')
            if len(pref) == 1:
                stage_cos_vec.append(cos.iloc[0])
            else:
                stage_cos_vec.append(np.array([np.nan, np.nan, np.nan]))

        tuning_matrix.append(stage_tune_vec)
        cosine_matrix.append(np.vstack(stage_cos_vec))

    return mouse_stage_responses, flattened_pref_tuning_mat, tuning_matrix, cosine_matrix


def mean_day_response_preferred_tuning(meta, tensor, tuning_df, staging='parsed_11stage',
                                       tune_staging='parsed_11stage', tuning_type='initial',
                                       filter=False, filter_on=None):
    """
    Create a mean tensor with the preferred responses of each cell by day.

    :param meta: pandas.DataFrame, DataFrame of trial metadata
    :param tensor: numpy.ndarray, a cells x times X trials
    :param tuning_df: pandas.DataFrame, tuning.cell_tuning() output df
    :param staging: str, way to bin stages of learning
    :param tune_staging: str --> 'parsed_11stage' or 'staging_LR'
        Determine how to pick preferred tuning, as only the preferred responses of cells are returned. By default this
        will be evaluate for each stage, but you can also pass a tuning_df that had other tuning calculations.
        For example, 'staging_LR' in tuning_df calculates preferred tuning only for pre and post reversal (not by
        dprime bin).
    :param tuning_type: str, way to define stimulus type. 'initial', 'orientation', or defaults to 'condition'

    # TODO add filtering on running speed, hit miss FA, etc

    :return:
        mouse_stage_responses, numpy.ndarray
            4D matrix (cells, times, stages, cues). Last level of cue is the response for the preferred cue.
        flattened_pref_tuning_mat, numpy.ndarray
            2D matrix (cells, times-x-stages) for preferred cue tuning
        tuning_matrix
            2D matrix of preferred tuning values
    """

    # make sure that you tuning df has the necessary columns
    assert tune_staging in tuning_df.columns

    # get conditions
    if 'initial' in tuning_type:
        cond_type = 'initial_condition'
    elif 'ori' in tuning_type:
        raise NotImplementedError
        # cond_type = 'orientation'
    elif tuning_type.lower() == 'cond' or tuning_type.lower() == 'condition':
        cond_type = 'condition'
    else:
        raise NotImplementedError

    # get the stage order (order of the x axis)
    xorder = utils.lookups.staging[staging]

    # preallocate 4D matrix (cells, times, stages, cues)
    mouse_stage_responses = np.zeros((tensor.shape[0], tensor.shape[1], len(meta.reset_index()['date'].unique()), 4))
    mouse_stage_responses[:] = np.nan

    # get mean of pmn trials for each stage
    days = meta.reset_index()['date'].unique()
    for cs, s in enumerate(days):
        day_boo = meta.reset_index()['date'].isin([s]).values
        for cc, icue in enumerate(['plus', 'minus', 'neutral']):
            meta_bool = day_boo & meta[cond_type].isin([icue]).values
            cue_stage_tensor = tensor[:, :, meta_bool]
            cue_stage_mean = np.nanmean(cue_stage_tensor, axis=2)
            mouse_stage_responses[:, :, cs, cc] = cue_stage_mean

    # add in a 4th z slice of preferred tuning responses
    tune_up = tuning_df.reset_index()
    days = meta.reset_index()['date'].unique()
    for cs, s in enumerate(days):
        # day_boo = meta.reset_index()['date'].isin([s]).values
        for cell_n in range(tensor.shape[0]):

            meta_check = meta.reset_index()['date'].isin([s]).values
            todays_stage = meta.loc[meta_check, staging].unique()[0]
            if tune_staging == 'staging_LR':
                # matching parse_11stage entries to learning reversal
                ss = 'reversal1' if 'reversal' in todays_stage else 'learning'
                pref_bool = tune_up[tune_staging].isin([ss])
            else:
                # or just parse_11stage entries (effectively allows preferred tuning recalc at each stage of learning)
                pref_bool = tune_up[tune_staging].isin([todays_stage])

            pref = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'preferred tuning']

            if len(pref) == 1:
                preferred_tuning = pref.item()
                if preferred_tuning == 'broad':
                    # average across cues for broadly tuned cells
                    mean_resp = np.nanmean(mouse_stage_responses[cell_n, :, cs, :], axis=1)
                    mouse_stage_responses[cell_n, :, cs, 3] = mean_resp
                else:
                    # take single preferred tuning or average across joint tuned cells
                    tuning_levels = np.where([s in preferred_tuning for s in ['plus', 'minus', 'neutral']])[0]
                    tuned_response = np.nanmean(mouse_stage_responses[cell_n, :, cs, tuning_levels], axis=0)
                    mouse_stage_responses[cell_n, :, cs, 3] = tuned_response

    # flatten your preferred stages
    stage_list = []
    for cs, s in enumerate(days):
        stage_list.append(mouse_stage_responses[:, :, cs, 3])
    flattened_pref_tuning_mat = np.hstack(stage_list)

    # loop and create vectors of preferred tuning (as test) matiching your flattened preferred tuning matrix
    tune_up = tuning_df.reset_index()
    if tune_staging == 'staging_LR':
        torder = ['learning', 'reversal1']
    else:
        torder = xorder

    tuning_matrix = []
    cosine_matrix = []
    for cs, s in enumerate(torder):

        stage_tune_vec = []
        stage_cos_vec = []
        for cell_n in range(tensor.shape[0]):

            if tune_staging == 'staging_LR':
                # matching parse_11stage entries to learning reversal
                ss = 'reversal1' if 'reversal' in s else 'learning'
                pref_bool = tune_up[tune_staging].isin([ss])
            else:
                # or just parse_11stage entries (effectively allows preferred tuning recalc at each stage of learning)
                pref_bool = tune_up[tune_staging].isin([s])

            pref = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'preferred tuning']
            cos = tune_up.loc[tune_up.cell_n.isin([cell_n + 1]) & pref_bool, 'cosine tuning']

            if len(pref) == 1:
                stage_tune_vec.append(pref.iloc[0])
            else:
                stage_tune_vec.append('none')
            if len(pref) == 1:
                stage_cos_vec.append(cos.iloc[0])
            else:
                stage_cos_vec.append(np.array([np.nan, np.nan, np.nan]))

        tuning_matrix.append(stage_tune_vec)
        cosine_matrix.append(np.vstack(stage_cos_vec))

    return mouse_stage_responses, flattened_pref_tuning_mat, tuning_matrix, cosine_matrix
