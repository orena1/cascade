"""
Functions for making simple calculations on tensortools TCA results.
Saves into MongoDB database for quick retrieval.
"""
from pool.database import memoize
import flow
import pool
import pandas as pd
import numpy as np
import os
import bottleneck as bt
from copy import deepcopy
from .. import load, utils
import scipy as sp


def trialbytrial_drive(
        mouse,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word='tray',
        group_by='all2',
        nan_thresh=0.85,
        score_threshold=0.8,
        drive_type='visual'):
    """
    Create a cells x trials array that contains the log inverse p-values
    of each trial compared to the distributions of the baseline response
    for each cell. Stats us a two tailed KS test.

    This is a wrapped function so that a flow Mouse object is correctly
    passed to the memoizer and MongoDB database. 
    """

    drive_mat = trialbytrial_drive_sub(
        flow.Mouse(mouse=mouse),
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold,
        drive_type=drive_type)

    return drive_mat


@memoize(across='mouse', updated=200120, returns='other', large_output=True)
def trialbytrial_drive_sub(
        mouse,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word='tray',
        group_by='all2',
        nan_thresh=0.85,
        score_threshold=0.8,
        drive_type='visual'):
    """
    Create a cells x trials array that contains the log inverse p-values
    of each trial compared to the distributions of the baseline response
    for each cell. Stats us a two tailed KS test. 
    """

    # get the mouse as a string
    mouse = mouse.mouse

    # load your tensor
    tensor = load.groupday_tca_input_tensor(
        mouse=mouse,
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold)

    if drive_type == 'visual':
        drive_mat = _trial_driven_visually(tensor, mouse, sec=15.5)
    elif drive_type == 'trial':
        drive_mat = _trial_driven_trial(tensor, mouse, sec=15.5)
    else:
        print('{}: requested {}: drive_type not recognized.'.format(
            mouse, drive_type))

    return drive_mat


@memoize(across='mouse', updated=191003, returns='other', large_output=False)
def trial_factor_tuning(
        mouse,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all2',
        nan_thresh=0.85,
        score_threshold=0.8,
        rank_num=18,
        verbose=True):
    """
    Create a pandas dataframe of trial factor tuning for one
    mouse. Only looks at initial learning stage. I repeat, this is
    only calculated on initial learning!!!
    """

    # default TCA params to use
    if not word:
        if mouse.mouse == 'OA27':
            word = 'restaurant'
        else:
            word = 'whale'
        if verbose:
            print('Creating dataframe for ' + mouse.mouse + '-' + word)

    ms = deepcopy(mouse)
    mouse = mouse.mouse
    psy = ms.psytracker(verbose=True)
    dateRuns = psy.data['dateRuns']
    trialRuns = psy.data['runLength']

    # create your trial indices per day and run
    trial_idx = []
    for i in trialRuns:
        trial_idx.extend(range(i))

    # get date and run vectors
    date_vec = []
    run_vec = []
    for c, i in enumerate(dateRuns):
        date_vec.extend([i[0]]*trialRuns[c])
        run_vec.extend([i[1]]*trialRuns[c])

    # create your data dict, transform from log odds to odds ratio
    data = {}
    for c, i in enumerate(psy.weight_labels):
        # adding multiplication step here with binary vector !!!!!!
        data[i] = np.exp(psy.fits[c, :])*psy.inputs[:, c].T
    ori_0_in = [i[0] for i in psy.data['inputs']['ori_0']]
    ori_135_in = [i[0] for i in psy.data['inputs']['ori_135']]
    ori_270_in = [i[0] for i in psy.data['inputs']['ori_270']]
    blank_in = [
        0 if i == 1 else 1 for i in
        np.sum((ori_0_in, ori_135_in, ori_270_in), axis=0)]

    # loop through psy data create a binary vectors for trial history
    binary_cat = ['ori_0', 'ori_135', 'ori_270', 'prev_reward']
    for cat in binary_cat:
        data[cat + '_th'] = [i[0] for i in psy.data['inputs'][cat]]
        data[cat + '_th_prev'] = [i[1] for i in psy.data['inputs'][cat]]

    # create a single list of orientations to match format of meta
    ori_order = [0, 135, 270, -1]
    data['orientation'] = [
        ori_order[np.where(np.isin(i, 1))[0][0]]
        for i in zip(ori_0_in, ori_135_in, ori_270_in, blank_in)]

    # create your index out of relevant variables
    index = pd.MultiIndex.from_arrays([
                [mouse]*len(trial_idx),
                date_vec,
                run_vec,
                trial_idx
                ],
                names=['mouse', 'date', 'run', 'trial_idx'])

    # make master dataframe
    dfr = pd.DataFrame(data, index=index)

    # load TCA data
    load_kwargs = {'mouse': mouse,
                   'method': method,
                   'cs': cs,
                   'warp': warp,
                   'word': word,
                   'group_by': group_by,
                   'nan_thresh': nan_thresh,
                   'score_threshold': score_threshold,
                   'rank': rank_num}
    tensor, _, _ = load.groupday_tca_model(**load_kwargs)
    meta = load.groupday_tca_meta(**load_kwargs)

    # add in continuous dprime
    dp = pool.calc.psytrack.dprime(ms)
    dfr['dprime'] = dp

    # filter out blank trials
    psy_df = dfr.loc[(dfr['orientation'] >= 0), :]

    # check that all runs have matched trial orienations
    new_psy_df_list = []
    new_meta_df_list = []
    dates = meta.reset_index()['date'].unique()
    for d in dates:
        psy_day_bool = psy_df.reset_index()['date'].isin([d]).values
        meta_day_bool = meta.reset_index()['date'].isin([d]).values
        psy_day_df = psy_df.iloc[psy_day_bool, :]
        meta_day_df = meta.iloc[meta_day_bool, :]
        runs = meta_day_df.reset_index()['run'].unique()
        for r in runs:
            psy_run_bool = psy_day_df.reset_index()['run'].isin([r]).values
            meta_run_bool = meta_day_df.reset_index()['run'].isin([r]).values
            psy_run_df = psy_day_df.iloc[psy_run_bool, :]
            meta_run_df = meta_day_df.iloc[meta_run_bool, :]
            psy_run_idx = psy_run_df.reset_index()['trial_idx'].values
            meta_run_idx = meta_run_df.reset_index()['trial_idx'].values

            # drop extra trials from trace2P that don't have associated imaging
            max_trials = np.min([len(psy_run_idx), len(meta_run_idx)])

            # get just your orientations for checking that trials are matched
            meta_ori = meta_run_df['orientation'].iloc[:max_trials]
            psy_ori = psy_run_df['orientation'].iloc[:max_trials]

            # make sure all oris match between vectors of the same length each day
            assert np.all(psy_ori.values == meta_ori.values)

            # if everything looks good, copy meta index into psy
            meta_new = meta_run_df.iloc[:max_trials]
            psy_new = psy_run_df.iloc[:max_trials]
            data = {}
            for i in psy_new.columns:
                data[i] = psy_new[i].values
            new_psy_df_list.append(pd.DataFrame(data=data, index=meta_new.index))
            new_meta_df_list.append(meta_new)

    meta1 = pd.concat(new_meta_df_list, axis=0)
    psy1 = pd.concat(new_psy_df_list, axis=0)

    iteration = 0
    ori_to_check = [0, 135, 270]
    cs_to_check = ['plus', 'minus', 'neutral']
    ori_vec, cond_vec, comp_vec = [], [], []
    df_data = {}
    mean_response_mat = np.zeros((rank_num, 3))
    for c, ori in enumerate(ori_to_check):
        for rank in [rank_num]:
            data = {}
            for i in range(rank):
                fac = tensor.results[rank][iteration].factors[2][:,i]
                data['factor_' + str(i+1)] = fac
            fac_df = pd.DataFrame(data=data, index=meta1.index)

            # loop over single oris
            psy_fac = pd.concat([psy1, fac_df], axis=1).drop(columns='orientation')
            ori_bool = (meta1['orientation'] == ori)  & (meta1['learning_state'] == 'learning')  # only look during initial learning
            single_psy = psy_fac.loc[ori_bool]

            # check the condition for this ori
            single_meta = meta1.loc[ori_bool]
            cond = single_meta['condition'].unique()
            if len(cond) > 1:
                multi_ori = []
                for ics in cs_to_check:
                    multi_ori.append(ics in cond)
                assert np.sum(multi_ori) == 1
                cond = cs_to_check[np.where(multi_ori)[0][0]]
            else:
                # assert len(cond) == 1
                cond = cond[0]

            # get means for each factor for each type of trial history
            for i in range(rank):
                single_factor = single_psy['factor_' + str(i+1)].values
                mean_response = np.nanmean(single_factor)
                mean_response_mat[i, c] = mean_response

        # save mean per ori
        df_data['mean_' + str(ori) + '_response'] = mean_response_mat[:, c]

    # get the mean response of the whole trial factor for across learning
    total_bool = (meta1['learning_state'] == 'learning')
    total_df = psy_fac.loc[total_bool]
    total_mean_list = []
    data = {}
    for i in range(rank):
        single_factor = total_df['factor_' + str(i+1)].values
        total_mean_list.append(np.nanmean(single_factor))
    df_data['mean_total_response'] = total_mean_list

    # bootstrap to check for significant tuning compared to mean response
    boot_num = 1000
    boot_means_per_comp = np.zeros((rank_num, boot_num))
    for bi in range(boot_num):
        for ri in range(rank):
            single_factor = total_df['factor_' + str(i+1)].values
            rand_samp = np.random.choice(
                single_factor, size=int(np.round(len(single_factor)/3)),
                replace=False)
            boot_means_per_comp[ri, bi] = np.nanmean(rand_samp)

    # test tuning
    bonferonni_correction = len(cs_to_check)
    tuning = []
    for i in range(rank_num):
        a = np.sum(boot_means_per_comp[i, :] >= mean_response_mat[i, 0])/1000 < 0.05/bonferonni_correction
        b = np.sum(boot_means_per_comp[i, :] >= mean_response_mat[i, 1])/1000 < 0.05/bonferonni_correction
        c = np.sum(boot_means_per_comp[i, :] >= mean_response_mat[i, 2])/1000 < 0.05/bonferonni_correction
        d = np.where([a, b, c])[0]

        if len(d) > 1 or len(d) == 0:
            tuning.append('broad')
        else:
            tuning.append(str(ori_to_check[d[0]]))

    # get tuning in terms of CS
    tuning_cs = []
    learning_meta = meta1.loc[total_bool]
    for ti in tuning:
        if ti == 'broad':
            tuning_cs.append('broad')
        else:
            tuning_cs.append(
                    learning_meta['condition']
                    .loc[learning_meta['orientation'].isin([int(ti)]), :]
                    .unique()[0])

    # save tuning into dict
    df_data['preferred_tuning'] = tuning
    df_data['preferred_tuning_cs'] = tuning_cs

    # make final df
    index = pd.MultiIndex.from_arrays([
                [mouse]*rank_num,
                list(np.arange(1, rank_num + 1))
                ],
                names=['mouse', 'component'])

    # make master dataframe
    tuning_df = pd.DataFrame(df_data, index=index)

    return tuning_df


def _trial_driven_visually(tensor, mouse, sec=15.5):
    """
    Calculate the probability of being visually driven for each cell
    per trial.

    Parameters:
    -----------
    tensor : np.ndarray
        cells x time x trials
    mouse : str
        The mouse name.
    sec : float
        How many samples per second in the input data?

    Returns:
    --------
    np.ndarray
        An array of length equal to the number cells x trial number,
        values are the log inverse p-value of that cell responding to
        the particular cs.

    """

    # Baseline is mean across frames, now ncells x nonsets
    stim_length = [2 if mouse in ['OA32', 'OA34', 'OA36'] else 3][0]
    baselines = np.nanmean(tensor[:, :int(np.floor(sec)), :], axis=1)
    full_baselines = tensor[:, :int(np.floor(sec)), :]
    stimuli = tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+1)*sec)), :]

    # Per-cell value
    meanbl = np.nanmean(baselines, axis=1)
    ncells = tensor.shape[0]

    # We will save the maximum inverse p values
    maxinvps = np.zeros((ncells, tensor.shape[2]), dtype=np.float64)

    for c in range(ncells):
        cell_baseline_vec = full_baselines[c, :, :].flatten()
        cell_baseline_vec = cell_baseline_vec[~np.isnan(cell_baseline_vec)]
        ntrials = np.sum(~np.isnan(baselines[c,:]).flatten())
        bonferroni_n = ncells*ntrials
        
        for trial in range(tensor.shape[2]):
            # skip nans
            if np.isnan(stimuli[c, 0, trial]):
                continue
            # don't test a cell if it is negative on average
            if np.nanmean(stimuli[c, :, trial]) > meanbl[c]:
                pv = sp.stats.ks_2samp(cell_baseline_vec, stimuli[c, :, trial])
                logpv = -1*np.log(pv[1]*bonferroni_n)
                if logpv > maxinvps[c, trial]:
                    maxinvps[c, trial] = logpv

    return maxinvps


def _trial_driven_visually_bins(tensor, mouse, sec=15.5, bins_per_sec=2):
    """
    Calculate the probability of being visually driven for each cell
    per trial across multiple bins with Bonferroni correction.

    Parameters:
    -----------
    tensor : np.ndarray
        cells x time x trials
    mouse : str
        The mouse name.
    sec : float
        How many samples per second in the input data?

    Returns:
    --------
    np.ndarray
        An array of length equal to the number cells x trial number,
        values are the log inverse p-value of that cell responding to
        the particular cs.

    """

    # Baseline is mean across frames, now ncells x nonsets
    stim_length = [2 if mouse in ['OA32', 'OA34', 'OA36'] else 3][0]
    baselines = bt.nanmean(tensor[:, :int(np.floor(sec)), :], axis=1)
    full_baselines = tensor[:, :int(np.floor(sec)), :]
    stimuli = tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+1)*sec)), :]

    # get bins to test
    stim_datapoints = stimuli.shape[1]
    bin_length = np.floor(sec/bins_per_sec)
    bin_starts = np.arange(0, stim_datapoints, bin_length)
    bin_ends = np.arange(bin_length, stim_datapoints, bin_length)
    bin_starts = bin_starts[:len(bin_ends)]
    bin_ends = [int(s) for s in bin_ends]
    bin_starts = [int(s) for s in bin_starts]
    nbins = len(bin_ends)

    # Per-cell value
    meanbl = bt.nanmean(baselines, axis=1)
    ncells = tensor.shape[0]

    # We will save the maximum inverse p values
    maxinvps = np.zeros((ncells, tensor.shape[2]), dtype=np.float64)

    for c in range(ncells):
        cell_baseline_vec = full_baselines[c, :, :].flatten()
        cell_baseline_vec = cell_baseline_vec[~np.isnan(cell_baseline_vec)]
        ntrials = np.sum(~np.isnan(baselines[c,:]).flatten())
        bonferroni_n = ncells*ntrials*nbins
        
        for trial in range(tensor.shape[2]):

            # skip nans
            if np.isnan(stimuli[c, 0, trial]):
                continue

            bin_pvs = []

            for bin_s, bin_e in zip(bin_starts, bin_ends):

                # get your bin and mean of that bin once
                this_bin = stimuli[c, bin_s:bin_e, trial]
                bin_mean = bt.nanmean(this_bin)

                # don't test a bin if it is negative on average
                if bin_mean > meanbl[c]:
                    pv = sp.stats.ks_2samp(cell_baseline_vec, this_bin)
                    bin_pvs.append(pv[1])

            # if no values were above zero skip cell
            if len(bin_pvs) > 0:
                best_pv = np.min(bin_pvs)
                logpv = -1*np.log10(best_pv*bonferroni_n)
                if logpv > maxinvps[c, trial]:
                    maxinvps[c, trial] = logpv

    return maxinvps


def _trial_driven_visually_fast_levene(tensor, mouse, sec=15.5):
    """
    Calculate the probability of being visually driven for each cell
    per trial across multiple bins with Bonferroni correction. Baseline
    here is the distribution in the 1 second before stimulus onset w/o
    pooling across multiple trials.

    Parameters:
    -----------
    tensor : np.ndarray
        cells x time x trials
    mouse : str
        The mouse name.
    sec : float
        How many samples per second in the input data?

    Returns:
    --------
    np.ndarray
        An array of length equal to the number cells x trial number,
        values are the log10 inverse p-value of that cell responding to
        the particular cs.

    """

    # Baseline is mean across frames, now ncells x nonsets
    stim_length = [2 if mouse in ['OA32', 'OA34', 'OA36'] else 3][0]
    baselines = bt.nanmean(tensor[:, :int(np.floor(sec)), :], axis=1)
    full_baselines = tensor[:, :int(np.floor(sec)), :]
    stimuli = tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+1)*sec)), :]

    # get log bins to test
    bins = np.round(np.logspace(np.log10(0.1), np.log10(stim_length), 4)*sec)
    bins[0] = 0
    bin_ends = bins[1:]
    bin_starts = bins[:-1]
    bin_ends = [int(s) for s in bin_ends]
    bin_starts = [int(s) for s in bin_starts]
    nbins = len(bin_ends)
    
    # bin stimulus
    binned_stimuli = np.zeros((stimuli.shape[0], nbins, stimuli.shape[2]))
    binned_stimuli[:] = np.nan
    bin_count = 0
    for bin_s, bin_e in zip(bin_starts, bin_ends):
        this_bin = stimuli[:, bin_s:bin_e, :]
        binned_stimuli[:, bin_count,:] = bt.nanmean(this_bin, axis=1)
        bin_count += 1
        
    # bin baselines
    binned_baselines = np.zeros((stimuli.shape[0], nbins, stimuli.shape[2]))
    binned_baselines[:] = np.nan
    bin_count = 0
    baseline_length = full_baselines.shape[1]
    for bin_s, bin_e in zip(bin_starts, bin_ends):
        bin_length = bin_e-bin_s
        if bin_length > baseline_length:
            bin_length = baseline_length
        this_bin = full_baselines[:, -bin_length:, :]
        binned_baselines[:, bin_count,:] = bt.nanmean(this_bin, axis=1)
        bin_count += 1
    
    # cell count for Bonferroni correction
    ncells = tensor.shape[0]

    # We will save the maximum inverse p values
    maxinvps = np.zeros((ncells, tensor.shape[2]), dtype=np.float64)

    for c in range(ncells):
        cell_baseline_vec = binned_baselines[c, :, :].flatten()
        cell_baseline_vec = cell_baseline_vec[~np.isnan(cell_baseline_vec)]
        
        ntrials = np.sum(~np.isnan(baselines[c,:]).flatten())
        bonferroni_n = ncells*ntrials
        
        for trial in range(tensor.shape[2]):

            # skip nans
            if np.isnan(stimuli[c, 0, trial]):
                continue

            # don't test a bin if it is negative on average
            if bt.nanmean(binned_stimuli[c, :, trial]) > 0:
                pv = sp.stats.levene(cell_baseline_vec, binned_stimuli[c, :, trial])
                logpv = -1*np.log10(pv[1]*bonferroni_n)
                if logpv > 0:
                    maxinvps[c, trial] = logpv

    return maxinvps

def _trial_driven_visually_bins_local(tensor, mouse, sec=15.5, bins_per_sec=2):
    """
    Calculate the probability of being visually driven for each cell
    per trial across multiple bins with Bonferroni correction. Baseline
    here is the distribution in the 1 second before stimulus onset w/o
    pooling across multiple trials.

    Parameters:
    -----------
    tensor : np.ndarray
        cells x time x trials
    mouse : str
        The mouse name.
    sec : float
        How many samples per second in the input data?

    Returns:
    --------
    np.ndarray
        An array of length equal to the number cells x trial number,
        values are the log10 inverse p-value of that cell responding to
        the particular cs.

    """

    # Baseline is mean across frames, now ncells x nonsets
    stim_length = [2 if mouse in ['OA32', 'OA34', 'OA36'] else 3][0]
    baselines = bt.nanmean(tensor[:, :int(np.floor(sec)), :], axis=1)
    full_baselines = tensor[:, :int(np.floor(sec)), :]
    stimuli = tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+1)*sec)), :]

    # get bins to test
    stim_datapoints = stimuli.shape[1]
    bin_length = np.floor(sec/bins_per_sec)
    bin_starts = np.arange(0, stim_datapoints, bin_length)
    bin_ends = np.arange(bin_length, stim_datapoints, bin_length)
    bin_starts = bin_starts[:len(bin_ends)]
    bin_ends = [int(s) for s in bin_ends]
    bin_starts = [int(s) for s in bin_starts]
    nbins = len(bin_ends)

    # Per-cell value
    meanbl = bt.nanmean(baselines, axis=1)
    ncells = tensor.shape[0]

    # We will save the maximum inverse p values
    maxinvps = np.zeros((ncells, tensor.shape[2]), dtype=np.float64)

    for c in range(ncells):
        cell_baseline_vec = full_baselines[c, :, :].flatten()
        cell_baseline_vec = cell_baseline_vec[~np.isnan(cell_baseline_vec)]
        ntrials = np.sum(~np.isnan(baselines[c,:]).flatten())
        bonferroni_n = ncells*ntrials*nbins
        
        for trial in range(tensor.shape[2]):

            # skip nans
            if np.isnan(stimuli[c, 0, trial]):
                continue

            bin_pvs = []

            # get the vector that is the baseline response for the trial
            local_baseline_vec = full_baselines[c, :, trial]

            for bin_s, bin_e in zip(bin_starts, bin_ends):

                # get your bin and mean of that bin once
                this_bin = stimuli[c, bin_s:bin_e, trial]
                bin_mean = bt.nanmean(this_bin)

                # don't test a bin if it is negative on average
                if bin_mean > 0:
                    pv = sp.stats.ks_2samp(local_baseline_vec, this_bin)
                    bin_pvs.append(pv[1])

            # if no values were above zero skip cell
            if len(bin_pvs) > 0:
                best_pv = np.min(bin_pvs)
                logpv = -1*np.log10(best_pv*bonferroni_n)
                if logpv > 0:
                    maxinvps[c, trial] = logpv

    return maxinvps


def _trial_driven_trial(tensor, mouse, sec=15.5):
    """
    Calculate the probability of being visually driven for each cell
    per trial.                                           |
    tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+3)*sec)), :]

    Parameters:
    -----------
    tensor : np.ndarray
        cells x time x trials
    mouse : str
        The mouse name.
    sec : float
        How many samples per second in the input data?

    Returns:
    --------
    np.ndarray
        An array of length equal to the number cells x trial number,
        values are the log inverse p-value of that cell responding to
        the particular cs.

    """

    # Baseline is mean across frames, now ncells x nonsets
    stim_length = [2 if mouse in ['OA32', 'OA34', 'OA36'] else 3][0]
    baselines = np.nanmean(tensor[:, :int(np.floor(sec)), :], axis=1)
    full_baselines = tensor[:, :int(np.floor(sec)), :]
    stimuli = tensor[:, int(np.ceil(sec)):int(np.ceil((stim_length+3)*sec)), :]

    # Per-cell value
    meanbl = np.nanmean(baselines, axis=1)
    ncells = tensor.shape[0]

    # We will save the maximum inverse p values
    maxinvps = np.zeros((ncells, tensor.shape[2]), dtype=np.float64)

    for c in range(ncells):
        cell_baseline_vec = full_baselines[c, :, :].flatten()
        cell_baseline_vec = cell_baseline_vec[~np.isnan(cell_baseline_vec)]
        ntrials = np.sum(~np.isnan(baselines[c,:]).flatten())
        bonferroni_n = ncells*ntrials
        std = np.std(cell_baseline_vec)
        
        for trial in range(tensor.shape[2]):
            if np.nanmean(stimuli[c, :, trial]) > meanbl[c]: # don't test a cell if it is negative on average
                pv = sp.stats.ks_2samp(cell_baseline_vec, stimuli[c, :, trial])
                logpv = -1*np.log(pv[1]*bonferroni_n)
                if logpv > maxinvps[c, trial]:
                    maxinvps[c, trial] = logpv

    return maxinvps
