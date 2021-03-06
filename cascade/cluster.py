"""Functions for stitching tca factors together across days."""
import random
import numpy as np
import os
import flow
import pool
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from copy import deepcopy
from scipy.cluster import hierarchy
from . import tca, paths, utils, load
from .plotting import cluster


def get_groupday_stage_clusters(clustering_df, cluster_number, method='ward'):
    """
    Get clustering df and annotated clusters for hierclus groupday df.
    """

    # create df only early and high dp learning stages
    keep_cols = [
        'plus_high_dp_learning', 'neutral_high_dp_learning',
        'minus_high_dp_learning', 'plus_high_dp_rev1',
        'minus_high_dp_rev1', 'neutral_high_dp_rev1',
        'plus_naive', 'minus_naive', 'neutral_naive']
    drop_inds = ~clustering_df.columns.isin(keep_cols)
    drop_cols = clustering_df.columns[drop_inds]
    clustering_df = clustering_df.drop(columns=drop_cols)
    nan_indexer = clustering_df.isna().any(axis=1)  # this has to be here
    clustering_df = clustering_df.dropna(axis='rows')
    g = sns.clustermap(clustering_df, method=method)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    plt.close('all')
    clustering_df['cluster'] = pd.Series(
        clusters, index=clustering_df.index)

    return clustering_df


def get_component_clusters(clustering_df, cluster_number):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """
    clustering_df = deepcopy(
        clustering_df.loc[:, ('plus', 'minus', 'neutral', 'hit',
                          'miss', 'false_alarm', 'correct_reject')])
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    plt.close('all')
    clustering_df['cluster'] = pd.Series(
        clusters, index=clustering_df.index)

    return clustering_df


def find_cluster_number(clustering_df, cluster_number, col_cluster=True):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """
    clustering_df = deepcopy(
        clustering_df.loc[:, ('plus', 'minus', 'neutral', 'hit',
                          'miss', 'false_alarm', 'correct_reject')])
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    cluster_color_options = sns.color_palette('hls', cluster_number)
    cluster_colors = [cluster_color_options[i-1] for i in clusters]

    mouse_list = clustering_df.reset_index().loc[:, 'mouse']
    mouse_color_options = sns.light_palette('navy', len(mouse_list.unique()))
    mouse_color_dict = {k: v for k, v in zip(mouse_list.unique(),
                                             mouse_color_options)}
    mouse_colors = [mouse_color_dict[m] for m in mouse_list]

    plt.close('all')
    plt.figure(figsize=(15, 15))
    sns.clustermap(clustering_df, row_colors=cluster_colors,
                   xticklabels=True, yticklabels=True, col_cluster=col_cluster)


def get_component_clusters_ori(clustering_df, cluster_number):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """
    clustering_df = deepcopy(clustering_df)
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    cluster_color_options = sns.color_palette('hls', cluster_number)
    cluster_colors = [cluster_color_options[i-1] for i in clusters]
    plt.close('all')
    clustering_df['cluster'] = pd.Series(
        clusters, index=clustering_df.index)

    return clustering_df


def find_cluster_number_remove_indices(
        clustering_df,
        cluster_number,
        col_cluster=True,
        expected_size_colors=0.5,
        auto_drop=True):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """

    # if running mod, center of mass, or ramp index are included, remove
    # from columns and make a color vector for each
    # learning_stages = [
    #         'naive', 'low_dp_learning', 'high_dp_learning', 'low_dp_rev1',
    #         'high_dp_rev1']
    learning_stages = [
            'pre_rev1']
    run_stage = ['running_modulation_' + stage for stage in learning_stages]
    ramp_stage = ['ramp_index_trials_' + stage for stage in learning_stages]
    mean_running_mod = clustering_df.loc[:, run_stage].mean(axis=1)
    ri_trials = clustering_df.loc[:, ramp_stage].mean(axis=1)
    ri_learning = clustering_df.loc[:, 'ramp_index_learning']
    ri_trace = clustering_df.loc[:, 'ramp_index_trace']
    ri_offset = clustering_df.loc[:, 'ramp_index_trace_offset']
    center_of_mass = clustering_df.loc[:, 'center_of_mass']

    # drop columns you don't want to affect clustering (i.e. nans)
    clustering_df = clustering_df.drop(columns=run_stage)
    clustering_df = clustering_df.drop(columns=ramp_stage)
    clustering_df = clustering_df.drop(
        columns=['ramp_index_learning'])
    clustering_df = clustering_df.drop(
        columns=['ramp_index_trace'])
    clustering_df = clustering_df.drop(
        columns=['ramp_index_trace_offset'])
    clustering_df = clustering_df.drop(columns=['center_of_mass'])

    if auto_drop:
        keep_cols = ['plus_high_dp_learning', 'neutral_high_dp_learning',
                     'minus_high_dp_learning', 'plus_high_dp_rev1',
                     'minus_high_dp_rev1', 'neutral_high_dp_rev1']
        drop_inds = ~clustering_df.columns.isin(keep_cols)
        drop_cols = clustering_df.columns[drop_inds]
        clustering_df = clustering_df.drop(columns=drop_cols)
        nan_indexer = clustering_df.isna().any(axis=1)
        clustering_df = clustering_df.dropna(axis='rows')
        mean_running_mod = mean_running_mod.loc[~nan_indexer, :]
        ri_trials = ri_trials.loc[~nan_indexer, :]
        ri_learning = ri_learning.loc[~nan_indexer, :]
        ri_trace = ri_trace.loc[~nan_indexer, :]
        ri_offset = ri_offset.loc[~nan_indexer, :]
        center_of_mass = center_of_mass.loc[~nan_indexer, :]
        # cm_learning = cm_learning.loc[~nan_indexer, :]

    # cluster to get cluster color labels for each component
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    cluster_color_options = sns.color_palette('hls', cluster_number)
    cluster_colors = [cluster_color_options[i-1] for i in clusters]

    # create mouse color labels
    mouse_list = clustering_df.reset_index().loc[:, 'mouse']
    mouse_color_options = sns.light_palette('navy', len(mouse_list.unique()))
    mouse_color_dict = {k: v for k, v in zip(mouse_list.unique(),
                                             mouse_color_options)}
    mouse_colors = [mouse_color_dict[m] for m in mouse_list]

    # create center of mass trials during learning color labels
    # binned_cml = pd.cut(cm_learning, 10, labels=range(0, 10))
    # cml_color_options = sns.light_palette('red', 10)
    # cml_color_dict = {k: v for k, v in zip(np.unique(binned_cml),
    #                                       cml_color_options)}
    # cml_colors = [cml_color_dict[m] for m in binned_cml]

    # create center of mass color labels
    binned_cm = pd.cut(center_of_mass, 10, labels=range(0, 10))
    cm_color_options = sns.light_palette('red', 10)
    cm_color_dict = {k: v for k, v in zip(np.unique(binned_cm),
                                          cm_color_options)}
    cm_colors = [cm_color_dict[m] for m in binned_cm]

    # create running mod color labels
    bins =[-np.inf, -1, -0.8, -0.6, -0.4, -0.2, 0,
           0.2, 0.4, 0.6, 0.8, 1, np.inf]
    binned_run = pd.cut(mean_running_mod, bins, labels=range(0, 12))
    run_color_options = sns.diverging_palette(220, 10, n=12)
    run_color_dict = {k: v for k, v in zip(np.unique(binned_run),
                                           run_color_options)}
    run_colors = [run_color_dict[m] for m in binned_run]

    # create trial ramp index color labels
    bins =[-np.inf, -1, -0.8, -0.6, -0.4, -0.2, 0,
           0.2, 0.4, 0.6, 0.8, 1, np.inf]
    binned_ramp = pd.cut(ri_trials, bins, labels=range(0, 12))
    ramp_color_options = sns.diverging_palette(220, 10, n=12)
    ramp_color_dict = {k: v for k, v in zip(np.unique(binned_ramp),
                                            ramp_color_options)}
    trial_ramp_colors = [ramp_color_dict[m] for m in binned_ramp]

    # create learning ramp index color labels
    bins =[-np.inf, -1, -0.8, -0.6, -0.4, -0.2, 0,
           0.2, 0.4, 0.6, 0.8, 1, np.inf]
    binned_ramp = pd.cut(ri_learning, bins, labels=range(0, 12))
    ramp_color_options = sns.diverging_palette(220, 10, n=12)
    ramp_color_dict = {k: v for k, v in zip(np.unique(binned_ramp),
                                            ramp_color_options)}
    learning_ramp_colors = [ramp_color_dict[m] for m in binned_ramp]

    # create trace ramp index color labels
    bins =[-np.inf, -1, -0.8, -0.6, -0.4, -0.2, 0,
           0.2, 0.4, 0.6, 0.8, 1, np.inf]
    binned_ramp = pd.cut(ri_trace, bins, labels=range(0, 12))
    ramp_color_options = sns.diverging_palette(220, 10, n=12)
    ramp_color_dict = {k: v for k, v in zip(np.unique(binned_ramp),
                       ramp_color_options)}
    trace_ramp_colors = [ramp_color_dict[m] if ~np.isnan(m) else [.5, .5, .5, 1.] for m in binned_ramp]

    # create trace ramp index color labels
    bins =[-np.inf, -1, -0.8, -0.6, -0.4, -0.2, 0,
           0.2, 0.4, 0.6, 0.8, 1, np.inf]
    binned_ramp = pd.cut(ri_offset, bins, labels=range(0, 12))
    ramp_color_options = sns.diverging_palette(220, 10, n=12)
    ramp_color_dict = {k: v for k, v in zip(np.unique(binned_ramp),
                                            ramp_color_options)}
    offset_ramp_colors = [ramp_color_dict[m] if ~np.isnan(m) else [.5, .5, .5, 1.] for m in binned_ramp]

    # create df of running colors for row colors
    data = {'mouse': mouse_colors,
            'running-modulation': run_colors,
            'ramp-index-learning': learning_ramp_colors,
            'ramp-index-daily-trials': trial_ramp_colors,
            'ramp-index-trace': trace_ramp_colors,
            'ramp-index-trace-offset': offset_ramp_colors,
            'center-of-mass-trace': cm_colors,
            'cluster': cluster_colors}
    color_df = pd.DataFrame(data=data, index=clustering_df.index)
# [mouse_colors, cm_colors, ramp_colors, run_colors, cluster_colors]
    plt.close('all')
    fig = cluster.clustermap(
        clustering_df, row_colors=color_df, figsize=(13, 13),
        xticklabels=True, yticklabels=True, col_cluster=col_cluster,
        expected_size_colors=expected_size_colors)

    return fig


def find_cluster_number_tempo(clustering_df, cluster_number, col_cluster=False):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    cluster_color_options = sns.color_palette('hls', cluster_number)
    cluster_colors = [cluster_color_options[i-1] for i in clusters]

    mouse_list = clustering_df.reset_index().loc[:, 'mouse']
    mouse_color_options = sns.light_palette('navy', len(mouse_list.unique()))
    mouse_color_dict = {k: v for k, v in zip(mouse_list.unique(),
                                             mouse_color_options)}
    mouse_colors = [mouse_color_dict[m] for m in mouse_list]

    plt.close('all')
    sns.clustermap(clustering_df, row_colors=[mouse_colors, cluster_colors],
                   col_cluster=col_cluster, figsize=(15, 15), yticklabels=True)


def get_component_clusters_tempo(clustering_df, cluster_number):
    """
    Plot your clustering df and annotated clusters for help choosing
    a reasonable number of clusters.
    """
    clustering_df = deepcopy(clustering_df)
    g = sns.clustermap(clustering_df)
    row_sorter = g.dendrogram_row.reordered_ind
    clusters = hierarchy.fcluster(
        g.dendrogram_row.linkage, cluster_number, criterion='maxclust')
    cluster_color_options = sns.color_palette('hls', cluster_number)
    cluster_colors = [cluster_color_options[i-1] for i in clusters]
    plt.close('all')
    clustering_df['temporal_cluster'] = pd.Series(
        clusters, index=clustering_df.index)

    return clustering_df


def trial_factors_across_mice(
        mice=['OA27', 'OA26', 'OA67', 'VF226', 'CC175'],
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        words=['rochester', 'convinced', 'convinced', 'convinced', 'convinced'],
        group_by='all',
        nan_thresh=0.85,
        score_threshold=None,
        verbose=False,
        rank_num=14):

    """
    Cluster tca trial factors based on tuning to different oris, conditions,
    and trialerror values.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools

    Returns:
    --------
    Saves figures to .../analysis folder  .../qc
    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}
    group_pars = {'group_by': group_by}

    # if cells were removed with too many nan trials
    if nan_thresh:
        nt_tag = '_nantrial' + str(nan_thresh)
        nt_save_tag = ' nantrial ' + str(nan_thresh)
    else:
        nt_tag = ''
        nt_save_tag = ''

    # save dir
    group_word = paths.groupmouse_word({'mice': mice})
    mouse = 'Group-' + group_word
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=words[0], group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'qc' + nt_save_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    var_path = os.path.join(
        save_dir, str(mouse) + '_hierarchical_clustering_n' + str(len(mice))
        + '.pdf')

    conds_by_day = []
    oris_by_day = []
    trialerr_by_day = []
    # neuron_ids_by_day = []
    # neuron_clusters_by_day = []
    # factors_by_day = []
    day_list = []
    df_list_tempo = []
    df_list_tuning = []
    df_list_conds = []
    df_list_error = []
    df_list_index = []
    for mnum, mouse in enumerate(mice):
        # load dir
        load_dir = paths.tca_path(
            mouse, 'group', pars=pars, word=words[mnum], group_pars=group_pars)
        tensor_path = os.path.join(
            load_dir, str(mouse) + '_' + str(group_by) + nt_tag
            + '_group_decomp_' + str(trace_type) + '.npy')
        ids_path = os.path.join(
            load_dir, str(mouse) + '_' + str(group_by) + nt_tag
            + '_group_ids_' + str(trace_type) + '.npy')
        input_tensor_path = os.path.join(
            load_dir, str(mouse) + '_' + str(group_by) + nt_tag
            + '_group_tensor_' + str(trace_type) + '.npy')
        meta_path = os.path.join(
            load_dir, str(mouse) + '_' + str(group_by) + nt_tag
            + '_df_group_meta.pkl')

        # load your data
        ensemble = np.load(tensor_path, allow_pickle=True)
        ensemble = ensemble.item()
        meta = pd.read_pickle(meta_path)
        meta = utils.update_naive_cs(meta)
        ids = np.load(ids_path)
        orientation = meta['orientation']
        condition = meta['condition']
        trialerror = meta['trialerror']
        hunger = deepcopy(meta['hunger'])
        speed = meta['speed']
        dates = meta.reset_index()['date']
        learning_state = meta['learning_state']

        # sort neuron factors by component they belong to most
        sort_ensemble, my_sorts = tca._sortfactors(ensemble[method])

        cell_ids = {}  # keys are rank
        cell_clusters = {}
        itr_num = 0  # use only best iteration of TCA, index 0
        for k in sort_ensemble.results.keys():
            # factors are already sorted, so these will define
            # clusters, no need to sort again
            factors = sort_ensemble.results[k][itr_num].factors[0]
            max_fac = np.argmax(factors, axis=1)
            cell_clusters[k] = max_fac
            cell_ids[k] = ids[my_sorts[k-1]]

        # ------------- GET TUNING

        trial_weights = sort_ensemble.results[rank_num][0].factors[2][:, :]
        tuning_weights = np.zeros((3, rank_num))
        oris_to_check = [0, 135, 270]
        for c, ori in enumerate(oris_to_check):
            tuning_weights[c, :] = np.nanmean(
                trial_weights[orientation == ori, :], axis=0)
        # normalize using summed mean response to all three
        tuning_total = np.nansum(tuning_weights, axis=0)
        for c in range(len(oris_to_check)):
            tuning_weights[c, :] = np.divide(
                tuning_weights[c, :], tuning_total)
        # dict for creating dataframe
        tuning_data = {}
        for c, errset in enumerate(oris_to_check):
            tuning_data['t' + str(errset)] = tuning_weights[c, :]

        # ------------- GET Condition TUNING

        trial_weights = sort_ensemble.results[rank_num][0].factors[2][:, :]
        conds_to_check = ['plus', 'minus', 'neutral']
        conds_weights = np.zeros((len(conds_to_check), rank_num))
        for c, conds in enumerate(conds_to_check):
            conds_weights[c, :] = np.nanmean(
                trial_weights[condition == conds, :], axis=0)
        # normalize using summed mean response to all three
        conds_total = np.nansum(conds_weights, axis=0)
        for c in range(len(conds_to_check)):
            conds_weights[c, :] = np.divide(conds_weights[c, :], conds_total)
        # dict for creating dataframe
        conds_data = {}
        for c, errset in enumerate(conds_to_check):
            conds_data[errset] = conds_weights[c, :]

        # ------------- GET Trialerror TUNING

        trial_weights = sort_ensemble.results[rank_num][0].factors[2][:, :]
        err_to_check = [[0], [1], [2, 4], [3, 5]]  # hit, miss, CR, FA
        err_val = ['hit', 'miss', 'correct_reject', 'false_alarm']
        error_weights = np.zeros((len(err_to_check), rank_num))
        for c, errset in enumerate(err_to_check):
            error_weights[c, :] = np.nanmean(
                trial_weights[trialerror.isin(errset), :], axis=0)
        # normalize using summed mean response to all three
        error_total = np.nansum(error_weights, axis=0)
        for c in range(len(err_to_check)):
            error_weights[c, :] = np.divide(error_weights[c, :], error_total)
        # dict for creating dataframe
        error_data = {}
        for c, errset in enumerate(err_val):
            error_data[errset] = error_weights[c, :]

        # ------------ CREATE PANDAS DF

        index = pd.MultiIndex.from_arrays([
            [mouse] * rank_num,
    #         [day1.date] * rank_num,
            range(1, rank_num+1)
            ],
            names=['mouse', 'component'])
        tempo_df = pd.DataFrame(
            sort_ensemble.results[rank_num][0].factors[1][:, :].T, index=index)
        tuning_df = pd.DataFrame(tuning_data, index=index)
        conds_df = pd.DataFrame(conds_data, index=index)
        error_df = pd.DataFrame(error_data, index=index)
        df_list_tempo.append(tempo_df)
        df_list_tuning.append(tuning_df)
        df_list_conds.append(conds_df)
        df_list_error.append(error_df)
        df_list_index.append(pd.DataFrame(index=index))

    #     factors_by_day.append(sort_ensemble.results[rank_num][0])
        conds_by_day.append(condition)
        oris_by_day.append(orientation)
        trialerr_by_day.append(trialerror)

    # concatenate all runs together in final dataframe
    all_tempo_df = pd.concat(df_list_tempo, axis=0)
    all_tuning_df = pd.concat(df_list_tuning, axis=0)
    all_conds_df = pd.concat(df_list_conds, axis=0)
    all_error_df = pd.concat(df_list_error, axis=0)
    all_index_df = pd.concat(df_list_index, axis=0)

    trial_factor_df = pd.concat([all_conds_df, all_tuning_df, all_error_df],
                                axis=1)
    temporal_factor_df = all_tempo_df

    return trial_factor_df, temporal_factor_df
