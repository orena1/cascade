"""Functions for plotting tca decomp."""
import os
import flow
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import tensortools as tt
import seaborn as sns
import pandas as pd
from copy import deepcopy
from .. import tca
from .. import paths
from . import plot_utils
from .. import load
from .. import lookups
from cascade.calc import var


"""
----------------------------- SETS OF PLOTS -----------------------------
"""


def groupday_shortlist(
        mouse,
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=0.8,
        verbose=False):
    groupday_factors_annotated(
        mouse, trace_type=trace_type, method=method, cs=cs, warp=warp,
        word=word, group_by=group_by, nan_thresh=nan_thresh,
        score_threshold=score_threshold, verbose=verbose)
    groupday_longform_factors_annotated(
        mouse, trace_type=trace_type, method=method, cs=cs, warp=warp,
        word=word, group_by=group_by, nan_thresh=nan_thresh,
        score_threshold=score_threshold, verbose=verbose)
    groupday_varex_summary(
        mouse, trace_type=trace_type, method=method, cs=cs, warp=warp,
        word=word, group_by=group_by, nan_thresh=nan_thresh,
        score_threshold=score_threshold, verbose=verbose)


def pairday_shortlist(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    pairday_varex_summary(mouse, trace_type=trace_type, method=method, cs=cs,
                          warp=warp, word=word, verbose=verbose)
    pairday_factors_annotated(mouse, trace_type=trace_type, method=method,
                              cs=cs, warp=warp, word=word, verbose=verbose)
    pairday_varex_percell(mouse, method=method, trace_type=trace_type, cs=cs,
                          warp=warp, ve_min=0.05, word=word)


def singleday_shortlist(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    singleday_varex_summary(mouse, trace_type=trace_type, method=method, cs=cs,
                            warp=warp, word=word, verbose=verbose)
    singleday_factors_annotated(mouse, trace_type=trace_type, method=method,
                                cs=cs, warp=warp, word=word, verbose=verbose)
    singleday_varex_percell(mouse, method=method, trace_type=trace_type, cs=cs,
                            warp=warp, ve_min=0.05, word=word)


"""
--------------------------- ACROSS ANIMAL PLOTS ---------------------------
"""


def groupmouse_varex_summary(
        mice=['OA27', 'OA67', 'OA32', 'OA34', 'CC175', 'OA36', 'OA26',
              'VF226'],
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        words=['determine', 'pharmacology', 'pharmacology', 'pharmacology',
               'pharmacology', 'pharmacology', 'pharmacology', 'pharmacology'],
        group_by='all2',
        nan_thresh=0.85,
        score_threshold=0.8,
        add_dropout_line=False,
        rectified=False,
        verbose=False):
    """
    Plot reconstruction error as variance explained across all whole groupday
    TCA decomposition ensemble.

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
        file_tag = '_nantrial' + str(nan_thresh)
        dir_tag = ' nantrial ' + str(nan_thresh)
    else:
        file_tag = ''
        dir_tag = ' nantrial ' + str(nan_thresh)

    # update saving tag if you used a cell score threshold
    if score_threshold:
        file_tag = '_score' + str(score_threshold) + file_tag
        dir_tag = ' score' + str(score_threshold) + dir_tag

    # save tag for rectification
    if rectified:
        r_tag = ' rectified'
        file_tag = file_tag + '_rectified'
        dir_tag = dir_tag + r_tag
    else:
        r_tag = ''

    # save dir
    group_word = paths.groupmouse_word({'mice': mice})
    mouse = 'Group-' + group_word
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=words[0], group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'qc' + dir_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    var_path = os.path.join(
        save_dir, str(mouse) + '_summary_variance_explained' + file_tag
                  + '_n' + str(len(mice)) + '.pdf')

    # create figure and axes
    buffer = 5
    right_pad = 5
    fig = plt.figure(figsize=(10, 8))
    gs = GridSpec(
        100, 100, figure=fig, left=0.05, right=.95, top=.95, bottom=0.05)
    ax = fig.add_subplot(gs[10:90 - buffer, :90 - right_pad])
    if add_dropout_line:
        cmap = sns.color_palette('Paired', len(mice) * 2)
    else:
        cmap = sns.color_palette('hls', len(mice) * 2)

    for c, mouse in enumerate(mice):

        # load your data
        load_kwargs = {'mouse': mouse,
                       'method': method,
                       'cs': cs,
                       'warp': warp,
                       'word': words[c],
                       'trace_type': trace_type,
                       'group_by': group_by,
                       'nan_thresh': nan_thresh,
                       'score_threshold': score_threshold}
        V, _, _ = load.groupday_tca_model(**load_kwargs, full_output=True)

        # get reconstruction error as variance explained
        df_var = var.groupday_varex(
            flow.Mouse(mouse=mouse),
            trace_type=trace_type,
            method=method,
            cs=cs,
            warp=warp,
            word=words[c],
            group_by=group_by,
            nan_thresh=nan_thresh,
            score_threshold=score_threshold,
            rectified=rectified,
            verbose=verbose)
        if add_dropout_line:
            df_var_drop = var.groupday_varex_drop_worst_comp(
                flow.Mouse(mouse=mouse),
                trace_type=trace_type,
                method=method,
                cs=cs,
                warp=warp,
                word=words[c],
                group_by=group_by,
                nan_thresh=nan_thresh,
                score_threshold=score_threshold,
                rectified=rectified,
                verbose=verbose)
        x_s = df_var['rank'].values
        var_s = df_var['variance_explained_tcamodel'].values
        if add_dropout_line:
            x_drop = df_var_drop['rank'].values
            var_drop = df_var_drop['variance_explained_dropping_worst_comp'].values
        x0 = x_s[df_var['iteration'].values == 0]
        var0 = var_s[df_var['iteration'].values == 0]
        var_mean = df_var['variance_explained_meanmodel'].values[0]
        if 'variance_explained_meandailymodel' in df_var.columns:
            var_mean_daily = df_var['variance_explained_meandailymodel'].values[0]
        var_smooth = df_var['variance_explained_smoothmodel'].values[0]
        var_PCA = df_var['variance_explained_PCA'].values[0]

        # plot
        R = np.max([r for r in V.results.keys()])
        ax.scatter(x_s, var_s, color=cmap[c * 2], alpha=0.5)
        if add_dropout_line:
            ax.scatter(x_drop, var_drop, color=cmap[c * 2 + 1], alpha=0.5)
        ax.scatter([R + 2], var_mean, color=cmap[c * 2], alpha=0.5)
        ax.scatter([R + 4], var_mean_daily, color=cmap[c * 2], alpha=0.5)
        ax.scatter([R + 6], var_PCA, color=cmap[c * 2], alpha=0.5)
        ax.plot(x0, var0, label=('mouse ' + mouse), color=cmap[c * 2])
        if add_dropout_line:
            ax.plot(x_drop, var_drop, label=(r'$mouse_-$ ' + mouse), color=cmap[c * 2 + 1])
        ax.plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c * 2])
        ax.plot([R + 3.5, R + 4.5], [var_mean_daily, var_mean_daily], color=cmap[c * 2])
        ax.plot([R + 5.5, R + 6.5], [var_PCA, var_PCA], color=cmap[c * 2])

    # add labels/titles
    x_labels = [str(R) for R in V.results]
    x_labels.extend(
        ['', 'mean\ncell\nresp.',
         '', 'daily\nmean\ncell\nresp.',
         '', 'PCA$_{20}$'])
    ax.set_xticks(range(1, len(V.results) + 7))
    ax.set_xticklabels(x_labels, size=12)
    ax.set_yticklabels([round(s, 2) for s in ax.get_yticks()], size=14)
    ax.set_xlabel('model rank', size=18)
    ax.set_ylabel('variance explained', size=18)
    ax.set_title(
        'Variance Explained: ' + str(method) + r_tag + ', ' + str(mice))
    ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    fig.savefig(var_path, bbox_inches='tight')


def groupmouse_varex_summary_cv(
        mice=lookups.mice['all15'],
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        words=None,
        group_by='all3',
        nan_thresh=0.95,
        score_threshold=0.8,
        train_test_split=0.8,
        rectified=True,
        verbose=False):
    """
    Plot reconstruction error as variance explained with cross validation across group of mice.

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
        file_tag = '_nantrial' + str(nan_thresh)
        dir_tag = ' nantrial ' + str(nan_thresh)
    else:
        file_tag = ''
        dir_tag = ' nantrial ' + str(nan_thresh)

    # update saving tag if you used a cell score threshold
    if score_threshold:
        file_tag = '_score' + str(score_threshold) + file_tag
        dir_tag = ' score' + str(score_threshold) + dir_tag

    # update saving tag if you used a cell score threshold
    if score_threshold:
        file_tag = file_tag + '_cv' + str(train_test_split)
        dir_tag = dir_tag + ' cv' + str(train_test_split)

    # save tag for rectification
    if rectified:
        r_tag = ' rectified'
        file_tag = file_tag + '_rectified'
        dir_tag = dir_tag + r_tag
    else:
        r_tag = ''

    # save dir
    group_word = paths.groupmouse_word({'mice': mice})
    mouse = 'Group-' + group_word
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=words[0], group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'qc' + dir_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    var_path = os.path.join(
        save_dir, str(mouse) + '_summary_variance_explained' + file_tag
                  + '_n' + str(len(mice)) + '.pdf')

    # create figure and axes
    fig, ax = plt.subplots(1, 2, figsize=(20, 8), sharey=True)
    cmap = sns.color_palette('hls', len(mice) * 2)
    for c, mouse in enumerate(mice):

        # load your data
        load_kwargs = {'mouse': mouse,
                       'method': method,
                       'cs': cs,
                       'warp': warp,
                       'word': words[c],
                       'trace_type': trace_type,
                       'group_by': group_by,
                       'nan_thresh': nan_thresh,
                       'score_threshold': score_threshold}
        V, _, _ = load.groupday_tca_model(**load_kwargs, full_output=True, cv=True, train_test_split=train_test_split)

        # get reconstruction error as variance explained
        df_var = var.groupday_varex_cv_train_set(
            flow.Mouse(mouse=mouse),
            trace_type=trace_type,
            method=method,
            cs=cs,
            warp=warp,
            word=word,
            group_by=group_by,
            nan_thresh=nan_thresh,
            score_threshold=score_threshold,
            train_test_split=train_test_split,
            rectified=rectified,
            verbose=verbose)
        df_var_cv = var.groupday_varex_cv_test_set(
            flow.Mouse(mouse=mouse),
            trace_type=trace_type,
            method=method,
            cs=cs,
            warp=warp,
            word=word,
            group_by=group_by,
            nan_thresh=nan_thresh,
            score_threshold=score_threshold,
            train_test_split=train_test_split,
            rectified=rectified,
            verbose=verbose)

        for axc, train_test in enumerate([df_var, df_var_cv]):

            # training set
            x_s = train_test['rank'].values
            var_s = train_test['variance_explained_tcamodel'].values
            x0 = x_s[train_test['iteration'].values == 0]
            var0 = var_s[train_test['iteration'].values == 0]
            var_mean = train_test['variance_explained_meanmodel'].values[0]
            if 'variance_explained_PCA' in train_test.columns:
                var_PCA = train_test['variance_explained_PCA'].values[0]
            else:
                var_PCA = []
            if 'variance_explained_meandailymodel' in train_test.columns:
                var_mean_daily = train_test['variance_explained_meandailymodel'].values[0]
            else:
                var_mean_daily = []

            # plot
            R = np.max([r for r in V.results.keys()])
            ax[axc].scatter(x_s, var_s, color=cmap[c * 2], alpha=0.5)
            ax[axc].plot(x0, var0, label=('mouse ' + mouse), color=cmap[c * 2])
            if axc == 0:
                ax[axc].scatter([R + 2], var_mean, color=cmap[c * 2], alpha=0.5)
                ax[axc].scatter([R + 4], var_mean_daily, color=cmap[c * 2], alpha=0.5)
                ax[axc].plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c * 2])
                ax[axc].plot([R + 3.5, R + 4.5], [var_mean_daily, var_mean_daily], color=cmap[c * 2])
                ax[axc].scatter([R + 6], var_PCA, color=cmap[c * 2], alpha=0.5)
                ax[axc].plot([R + 5.5, R + 6.5], [var_PCA, var_PCA], color=cmap[c * 2])

        # add labels/titles
        x_labels = [str(R) for R in V.results]
        x_labels.extend(
            ['', 'mean\ncell\nresp.',
             '', 'daily\nmean\ncell\nresp.',
             '', 'PCA$_{20}$'])
        ax[0].set_xticks(range(1, len(V.results) + 7))
        ax[1].set_xticks(range(1, len(V.results)))
        ax[0].set_xticklabels(x_labels, size=12)
        ax[1].set_xticklabels([str(R) for R in V.results], size=12)
        ax[0].set_yticklabels([round(s, 2) for s in ax[0].get_yticks()], size=14)
        ax[0].set_xlabel('model rank', size=18)
        ax[1].set_xlabel('model rank', size=18)
        ax[0].set_ylabel('variance explained', size=18)
        ax[0].set_title(f'Variance explained training set: {round(train_test_split, 2)}')
        ax[1].set_title(f'Variance explained test set: {round(1-train_test_split, 2)}')
        ax[1].legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    plt.suptitle(f'{mice}', y=1.05, size=18)
    fig.savefig(var_path, bbox_inches='tight')


"""
----------------------------- GROUP DAY PLOTS -----------------------------
"""


def groupday_longform_factors_annotated(
        mouse,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=0.8,
        negative_modes=[],
        extra_col=1,
        alpha=0.6,
        plot_running=True,
        filetype='png',
        scale_y=False,
        hmm_engaged=True,
        add_prev_cols=True,
        cv=False,
        train_test_split=0.8,
        verbose=False):
    """
    Plot TCA factors with trial metadata annotations for all days
    and ranks/componenets for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str
        Mouse name.
    trace_type : str
        dff, zscore, zscore_iti, zscore_day, deconvolved
    method : str
        TCA fit method from tensortools
    cs : str
        Cs stimuli to include, plus/minus/neutral, 0/135/270, etc. '' empty
        includes all stimuli
    warp : bool
        Use traces with time-warped outcome.
    extra_col : int
        Number of columns to add to the original three factor columns
    alpha : float
        Value between 0 and 1 for transparency of markers
    plot_running : bool
        Include trace of scaled (to plot max) average running speed during trial
    verbose : bool
        Show plots as they are made.

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors annotated
    """

    # use matplotlib plotting defaults
    mpl.rcParams.update(mpl.rcParamsDefault)

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}
    group_pars = {'group_by': group_by}

    # if cells were removed with too many nan trials
    if nan_thresh:
        save_tag = ' nantrial ' + str(nan_thresh)
    else:
        save_tag = ''

    # update saving tag if you used a cell score threshold
    if score_threshold:
        save_tag = ' score ' + str(score_threshold) + save_tag

    # update saving tag if for cv traing set
    if cv:
        save_tag = save_tag + ' cv' + str(train_test_split)

    # update saving tag if you used a cell score threshold
    if scale_y:
        save_tag = ' scaley' + save_tag

    # save dir
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'factors annotated long-form' + save_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    date_dir = os.path.join(save_dir, str(group_by) + ' ' + method)
    if not os.path.isdir(date_dir): os.mkdir(date_dir)

    # load your data
    load_kwargs = {'mouse': mouse,
                   'method': method,
                   'cs': cs,
                   'warp': warp,
                   'word': word,
                   'trace_type': trace_type,
                   'group_by': group_by,
                   'nan_thresh': nan_thresh,
                   'score_threshold': score_threshold}
    sort_ensemble, _, _ = load.groupday_tca_model(
        **load_kwargs, full_output=True, cv=cv, train_test_split=train_test_split)
    sort_ensemble = plot_utils.choose_negative_modes(sort_ensemble, negative_modes=negative_modes)
    meta = load.groupday_tca_meta(**load_kwargs)
    orientation = meta['orientation']
    trial_num = np.arange(0, len(orientation))
    condition = meta['condition']
    trialerror = meta['trialerror']
    hunger = deepcopy(meta['hunger'])
    speed = meta['speed']
    dates = meta.reset_index()['date']
    learning_state = meta['learning_state']
    if hmm_engaged and 'hmm_engaged' in meta.columns:
        hmm = meta['hmm_engaged']
    else:
        if verbose:
            print('hmm_engaged not in columns: Final row removed.')

    # calculate change indices for days and reversal/learning
    udays = {d: c for c, d in enumerate(np.unique(dates))}
    ndays = np.diff([udays[i] for i in dates])
    day_x = np.where(ndays)[0] + 0.5
    ustate = {d: c for c, d in enumerate(np.unique(learning_state))}
    nstate = np.diff([ustate[i] for i in learning_state])
    lstate_x = np.where(nstate)[0] + 0.5

    # merge hunger and tag info for plotting hunger
    tags = meta['tag']
    hunger[tags == 'disengaged'] = 'disengaged'

    # plot
    if hmm_engaged:
        rows = 7
    else:
        rows = 6
    if add_prev_cols:
        rows += 6

    cols = 3
    for r in sort_ensemble.results:

        U = sort_ensemble.results[r][0].factors

        for comp in range(U.rank):
            fig, axes = plt.subplots(
                rows, cols, figsize=(17, rows),
                gridspec_kw={'width_ratios': [2, 2, 17]})

            # reset previous col (trial history variables) counter
            prev_col_counter = 0

            # reshape for easier indexing
            ax = np.array(axes).reshape((rows, -1))
            ax[0, 0].set_title('Neuron factors')
            ax[0, 1].set_title('Temporal factors')
            ax[0, 2].set_title('Trial factors')

            # add title to whole figure
            ax[0, 0].text(-1.2, 4, '\n ' + mouse + ':\n\n rank: ' + str(int(r))
                          + '\n method: ' + method + '\n group_by: '
                          + group_by + '\n word: ' + word, fontsize=12,
                          transform=ax[0, 0].transAxes, color='#969696')

            # plot cell factors
            ax[0, 0].plot(
                np.arange(0, len(U.factors[0][:, comp])),
                U.factors[0][:, comp], '.', color='b', alpha=0.7)
            ax[0, 0].autoscale(enable=True, axis='both', tight=True)

            # plot temporal factors
            ax[0, 1].plot(U.factors[1][:, comp], color='r', linewidth=1.5)
            ax[0, 1].autoscale(enable=True, axis='both', tight=True)

            # add a line for stim onset and offset
            # NOTE: assumes downsample, 1 sec before onset, default is 15.5 Hz
            if '_bin' in trace_type.lower():
                one_sec = 3.9  # 27 frames for 7 sec, 1 pre, 6, post
            else:
                one_sec = 15.5
            off_time = lookups.stim_length[mouse]
            y_lim = ax[0, 1].get_ylim()
            ons = one_sec * 1
            offs = ons + one_sec * off_time
            ax[0, 1].plot([ons, ons], y_lim, ':k')
            if '_onset' not in trace_type.lower():
                ax[0, 1].plot([offs, offs], y_lim, ':k')

            col = cols - 1
            for i in range(rows):

                # get axis values
                if i == 0:
                    y_sc_factor = 4
                    if scale_y:
                        ystd3 = np.nanstd(U.factors[2][:, comp]) * y_sc_factor
                        ymax = np.nanmax(U.factors[2][:, comp])
                        if ystd3 < ymax:
                            y_lim = [0, ystd3]
                        else:
                            y_lim = [0, ymax]
                    else:
                        y_lim = [0, np.nanmax(U.factors[2][:, comp])]

                # running
                if plot_running:
                    scale_by = np.nanmax(speed) / y_lim[1]
                    if not np.isnan(scale_by):
                        ax[i, col].plot(
                            np.array(speed.tolist()) / scale_by,
                            color=[1, 0.1, 0.6, 0.2])
                        # , label='speed')

                # Orientation - main variable to plot
                if i == 0:
                    ori_vals = [0, 135, 270]
                    # color_vals = [[0.28, 0.68, 0.93, alpha],
                    #               [0.84, 0.12, 0.13, alpha],
                    #               [0.46, 0.85, 0.47, alpha]]
                    color_vals = sns.color_palette('BuPu', 3)
                    for k in range(0, 3):
                        ax[i, col].plot(
                            trial_num[orientation == ori_vals[k]],
                            U.factors[2][orientation == ori_vals[k], comp],
                            'o', label=str(ori_vals[k]), color=color_vals[k],
                            markersize=2, alpha=alpha)

                    ax[i, col].set_title(
                        'Component ' + str(comp + 1) + '\n\n\nTrial factors')
                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='Orientation', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    ax[i, col].set_xticklabels([])

                # Condition - main variable to plot
                elif i == 1:
                    cs_vals = ['plus', 'minus', 'neutral']
                    cs_labels = ['plus', 'minus', 'neutral']
                    color_vals = [[0.46, 0.85, 0.47, alpha],
                                  [0.84, 0.12, 0.13, alpha],
                                  [0.28, 0.68, 0.93, alpha]]
                    for k in range(0, 3):
                        ax[i, col].plot(
                            trial_num[condition == cs_vals[k]],
                            U.factors[2][condition == cs_vals[k], comp], 'o',
                            label=str(cs_labels[k]), color=color_vals[k],
                            markersize=2)

                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='Condition', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    ax[i, col].set_xticklabels([])

                # Trial error - main variable to plot
                elif i == 2:
                    color_counter = 0
                    error_colors = sns.color_palette(
                        palette='muted', n_colors=10)
                    trialerror_vals = [0, 1]  # 2, 3, 4, 5,] # 6, 7, 8, 9]
                    trialerror_labels = ['hit',
                                         'miss',
                                         'neutral correct reject',
                                         'neutral false alarm',
                                         'minus correct reject',
                                         'minus false alarm',
                                         'blank correct reject',
                                         'blank false alarm',
                                         'pav early licking',
                                         'pav late licking']
                    for k in range(len(trialerror_vals)):
                        ax[i, col].plot(
                            trial_num[trialerror == trialerror_vals[k]],
                            U.factors[2][trialerror == trialerror_vals[k], comp],
                            'o', label=str(trialerror_labels[k]), alpha=alpha,
                            markersize=2, color=error_colors[color_counter])
                        color_counter = color_counter + 1

                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='Trialerror', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    ax[i, col].set_xticklabels([])

                # Trial error 2.0 - main variable to plot
                elif i == 3:
                    trialerror_vals = [2, 3]
                    trialerror_labels = ['neutral correct reject',
                                         'neutral false alarm']
                    for k in range(len(trialerror_vals)):
                        ax[i, col].plot(
                            trial_num[trialerror == trialerror_vals[k]],
                            U.factors[2][trialerror == trialerror_vals[k], comp],
                            'o', label=str(trialerror_labels[k]), alpha=alpha,
                            markersize=2, color=error_colors[color_counter])
                        color_counter = color_counter + 1

                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='Trialerror', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    ax[i, col].set_xticklabels([])

                # Trial error 3.0 - main variable to plot
                elif i == 4:
                    trialerror_vals = [4, 5]
                    trialerror_labels = ['minus correct reject',
                                         'minus false alarm']
                    for k in range(len(trialerror_vals)):
                        ax[i, col].plot(
                            trial_num[trialerror == trialerror_vals[k]],
                            U.factors[2][trialerror == trialerror_vals[k], comp],
                            'o', label=str(trialerror_labels[k]), alpha=alpha,
                            markersize=2, color=error_colors[color_counter])
                        color_counter = color_counter + 1

                        ax[i, col].legend(
                            bbox_to_anchor=(1.02, 1), loc='upper left',
                            borderaxespad=0, title='Trialerror', markerscale=2,
                            prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    ax[i, col].set_xticklabels([])

                # High/low speed 5 cm/s threshold - main variable to plot
                elif i == 5:
                    speed_bool = speed.values > 4
                    color_vals = sns.color_palette("hls", 2)

                    ax[i, col].plot(trial_num[~speed_bool],
                                    U.factors[2][~speed_bool, comp], 'o',
                                    label='stationary',
                                    color=color_vals[1],
                                    alpha=0.3,
                                    markersize=2)
                    ax[i, col].plot(trial_num[speed_bool],
                                    U.factors[2][speed_bool, comp], 'o',
                                    label='running',
                                    color=color_vals[0],
                                    alpha=0.3,
                                    markersize=2)

                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='Running', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)

                    if hmm_engaged or add_prev_cols:
                        ax[i, col].set_xticklabels([])

                # HMM engagement - main variable to plot
                elif i == 6:
                    h_vals = ['engaged', 'disengaged']
                    h_labels = ['engaged', 'disengaged']
                    color_vals = [[1, 0.6, 0.3, alpha],
                                  [0.7, 0.9, 0.4, alpha]]

                    ax[i, col].plot(trial_num[hmm],
                                    U.factors[2][hmm, comp], 'o',
                                    label=str(h_labels[0]),
                                    color=color_vals[0],
                                    markersize=2)
                    ax[i, col].plot(trial_num[~hmm],
                                    U.factors[2][~hmm, comp], 'o',
                                    label=str(h_labels[1]),
                                    color=color_vals[1],
                                    markersize=2)
                    ax[i, col].legend(
                        bbox_to_anchor=(1.02, 1), loc='upper left',
                        borderaxespad=0, title='HMM engaged', markerscale=2,
                        prop={'size': 8})
                    ax[i, col].autoscale(enable=True, axis='both', tight=True)
                    if add_prev_cols:
                        ax[i, col].set_xticklabels([])

                if add_prev_cols:
                    # Trial history in some form - main variable to plot
                    if i >= 7:
                        on_color = ['#9fff73', '#ff663c', '#a5ff89', '#63e5ff', '#ff5249', '#6b54ff']
                        off_color = ['#ff739f', '#3cffec', '#ff89a5', '#ff8f63', '#49ff6a', '#ffb554']
                        # here CS is for the initial learning period
                        prev_col_list = [
                            'prev_reward',
                            'prev_punish',
                            'prev_same_plus',
                            'prev_same_neutral',
                            'prev_same_minus',
                            'prev_blank']
                        prev_col_titles = [
                            'Prev Reward',
                            'Prev Punishment',
                            'Prev Same Cue: initial plus',
                            'Prev Same Cue: initial neutral',
                            'Prev Same Cue: initial minus',
                            'Prev Blank']
                        prev_col_labels = [
                            'rewarded [-1]',
                            'punishment [-1]',
                            'initial plus [-1]',
                            'initial neutral [-1]',
                            'initial minus [-1]',
                            'blank [-1]']
                        current_col = prev_col_list[prev_col_counter]

                        # skip column if it is not in metadata (will result
                        # in blank axes at end)
                        if current_col not in meta.columns:
                            continue

                        # boolean of trial history
                        prev_same_bool = meta[current_col].values
                        if 'plus' in current_col:
                            matched_ori = [lookups.lookup[mouse]['plus']]
                        elif 'minus' in current_col:
                            matched_ori = [lookups.lookup[mouse]['minus']]
                        elif 'neutral' in current_col:
                            matched_ori = [lookups.lookup[mouse]['neutral']]
                        else:
                            matched_ori = [0, 135, 270]
                        same_ori_bool = meta['orientation'].isin(matched_ori).values

                        ax[i, col].plot(
                            trial_num[~prev_same_bool & same_ori_bool],
                            U.factors[2][~prev_same_bool & same_ori_bool, comp],
                            'o',
                            label='not {}'.format(prev_col_labels[prev_col_counter]),
                            color=off_color[prev_col_counter],
                            alpha=alpha,
                            markersize=2)

                        ax[i, col].plot(
                            trial_num[prev_same_bool & same_ori_bool],
                            U.factors[2][prev_same_bool & same_ori_bool, comp],
                            'o',
                            label=prev_col_labels[prev_col_counter],
                            color=on_color[prev_col_counter],
                            alpha=alpha,
                            markersize=2)

                        ax[i, col].legend(
                            bbox_to_anchor=(1.02, 1), loc='upper left',
                            borderaxespad=0,
                            title=prev_col_titles[prev_col_counter],
                            markerscale=2,
                            prop={'size': 8})
                        ax[i, col].autoscale(enable=True, axis='both', tight=True)

                        # if i is less than the last row
                        if i < rows - 1:
                            ax[i, col].set_xticklabels([])

                        # increment counter
                        prev_col_counter += 1

                # plot days, reversal, or learning lines if there are any
                if col >= 1:
                    # y_lim = ax[i, col].get_ylim()
                    if len(day_x) > 0:
                        for k in day_x:
                            ax[i, col].plot(
                                [k, k], y_lim, color='#969696', linewidth=1)
                    if len(lstate_x) > 0:
                        ls_vals = ['naive', 'learning', 'reversal1']
                        ls_colors = ['#66bd63', '#d73027', '#a50026']
                        for k in lstate_x:
                            ls = learning_state[int(k - 0.5)]
                            ax[i, col].plot(
                                [k, k], y_lim,
                                color=ls_colors[ls_vals.index(ls)],
                                linewidth=1.5)

                # hide subplots that won't be used
                if i > 0:
                    ax[i, 0].axis('off')
                    ax[i, 1].axis('off')

                # despine plots to look like sns defaults
                sns.despine()

                # rescale the y-axis for trial factors if you
                if i == 0 and scale_y:
                    ystd3 = np.nanstd(U.factors[2][:, comp]) * y_sc_factor
                    ymax = np.nanmax(U.factors[2][:, comp])
                if scale_y:
                    if ystd3 < ymax:
                        y_ticks = np.round([0, ystd3 / 2, ystd3], 2)
                        ax[i, 2].set_ylim([0, ystd3])
                        ax[i, 2].set_yticks(y_ticks)
                        ax[i, 2].set_yticklabels(y_ticks)
                    else:
                        y_ticks = np.round([0, ymax / 2, ymax], 2)
                        ax[i, 2].set_ylim([0, ymax])
                        ax[i, 2].set_yticks(y_ticks)
                        ax[i, 2].set_yticklabels(y_ticks)

            # save
            if filetype.lower() == 'pdf':
                suffix = '.pdf'
            elif filetype.lower() == 'eps':
                suffix = '.eps'
            else:
                suffix = '.png'
            plt.savefig(os.path.join(date_dir, '{}_rank_{}_component_{}{}'.format(mouse, r, comp + 1, suffix)),
                        bbox_inches='tight')
            if verbose:
                plt.show()
            plt.close('all')


def groupday_factors_annotated(
        mouse,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all3',
        nan_thresh=0.85,
        score_threshold=0.8,
        negative_modes = [],
        extra_col=5,
        alpha=0.6,
        plot_running=True,
        filetype='png',
        scale_y=False,
        hunger_or_hmm='hmm',
        add_prev_cols=False,
        cv=False,
        train_test_split=0.8,
        verbose=False):
    """
    Plot TCA factors with trial metadata annotations for all days
    and ranks/componenets for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str
        Mouse name.
    trace_type : str
        dff, zscore, zscore_iti, zscore_day, deconvolved
    method : str
        TCA fit method from tensortools
    cs : str
        Cs stimuli to include, plus/minus/neutral, 0/135/270, etc. '' empty
        includes all stimuli
    warp : bool
        Use traces with time-warped outcome.
    extra_col : int
        Number of columns to add to the original three factor columns
    alpha : float
        Value between 0 and 1 for transparency of markers
    plot_running : bool
        Include trace of scaled (to plot max) average running speed during trial
    verbose : bool
        Show plots as they are made.

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors annotated
    """

    # use matplotlib plotting defaults
    mpl.rcParams.update(mpl.rcParamsDefault)

    # plotting options for the unconstrained and nonnegative models.
    plot_options = lookups.tt_plot_options

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}
    group_pars = {'group_by': group_by}

    # if cells were removed with too many nan trials
    if nan_thresh:
        save_tag = ' nantrial ' + str(nan_thresh)
    else:
        save_tag = ''

    # update saving tag if you used a cell score threshold
    if score_threshold:
        save_tag = ' score ' + str(score_threshold) + save_tag

    # update saving tag are using the cv training set
    if cv:
        save_tag = save_tag + ' cv' + str(train_test_split)

    # save dir
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    if scale_y:
        save_tag = save_tag + ' scaled-y'
    else:
        save_tag = save_tag + ''
    save_dir = os.path.join(save_dir, 'factors annotated' + save_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    date_dir = os.path.join(save_dir, str(group_by) + ' ' + method)
    if not os.path.isdir(date_dir): os.mkdir(date_dir)

    # load your data
    load_kwargs = {'mouse': mouse,
                   'method': method,
                   'cs': cs,
                   'warp': warp,
                   'word': word,
                   'trace_type': trace_type,
                   'group_by': group_by,
                   'nan_thresh': nan_thresh,
                   'score_threshold': score_threshold}
    sort_ensemble, _, _ = load.groupday_tca_model(
        **load_kwargs, full_output=True, cv=cv, train_test_split=train_test_split)
    sort_ensemble = plot_utils.choose_negative_modes(sort_ensemble, negative_modes=negative_modes)
    meta = load.groupday_tca_meta(**load_kwargs)
    orientation = meta['orientation']
    trial_num = np.arange(0, len(orientation))
    condition = meta['condition']
    trialerror = meta['trialerror']
    hunger = deepcopy(meta['hunger'])
    speed = meta['speed']
    dates = meta.reset_index()['date']
    learning_state = meta['learning_state']
    if hunger_or_hmm == 'hmm' and 'hmm_engaged' in meta.columns:
        hmm = meta['hmm_engaged']
    else:
        hunger_or_hmm = False
        if verbose:
            print('hmm_engaged not in columns: Final column set to hunger state.')

    # calculate change indices for days and reversal/learning
    udays = {d: c for c, d in enumerate(np.unique(dates))}
    ndays = np.diff([udays[i] for i in dates])
    day_x = np.where(ndays)[0] + 0.5
    ustate = {d: c for c, d in enumerate(np.unique(learning_state))}
    nstate = np.diff([ustate[i] for i in learning_state])
    lstate_x = np.where(nstate)[0] + 0.5

    # merge hunger and tag info for plotting hunger
    tags = meta['tag']
    hunger[tags == 'disengaged'] = 'disengaged'

    # add columns to plot conditionally for previous trial info
    if add_prev_cols:
        extra_col += 6

    # plot
    for r in sort_ensemble.results:

        U = sort_ensemble.results[r][0].factors

        fig, axes = plt.subplots(U.rank, U.ndim + extra_col, figsize=(9 + extra_col * 2, U.rank))
        figt = tt.plot_factors(U, plots=['scatter', 'line', 'scatter'],
                               axes=None,
                               fig=fig,
                               scatter_kw=plot_options[method]['scatter_kw'],
                               line_kw=plot_options[method]['line_kw'],
                               bar_kw=plot_options[method]['bar_kw'])
        ax = figt[0].axes
        ax[0].set_title('Neuron factors')
        ax[1].set_title('Temporal factors')
        ax[2].set_title('Trial factors')

        # add title to whole figure
        ax[0].text(-1.2, 4, '\n ' + mouse + ':\n\n rank: ' + str(int(r)) +
                   '\n method: ' + method + '\n group_by: '
                   + group_by + '\n word: ' + word,
                   fontsize=12, transform=ax[0].transAxes,
                   color='#969696')

        # reshape for easier indexing
        ax = np.array(ax).reshape((U.rank, -1))

        # change color of cell factors to blue
        for i in range(U.rank):
            ax[i, 0].collections[0].set_color('blue')

        # rescale the y-axis for trials
        if scale_y:
            for i in range(U.rank):
                y_lim = np.array(ax[i, 2].get_ylim()) * 0.8
                y_ticks = ax[i, 2].get_yticks()
                y_ticks[-1] = y_lim[-1]
                y_ticks = np.round(y_ticks, 2)
                # y_tickl = [str(y) for y in y_ticks]
                ax[i, 2].set_ylim(y_lim)
                ax[i, 2].set_yticks(y_ticks)
                ax[i, 2].set_yticklabels(y_ticks)

        # add a line for stim onset and offset
        # NOTE: assumes downsample, 1 sec before onset, 3 sec stim
        if '_bin' in trace_type.lower():
            one_sec = 3.9  # 27 frames for 7 sec, 1 pre, 6, post
        else:
            one_sec = 15.5
        off_time = lookups.stim_length[mouse]
        for i in range(U.rank):
            y_lim = ax[i, 1].get_ylim()
            ons = one_sec * 1
            offs = ons + one_sec * off_time
            ax[i, 1].plot([ons, ons], y_lim, ':k')
            if '_onset' not in trace_type.lower():
                ax[i, 1].plot([offs, offs], y_lim, ':k')

        # reset counter
        if add_prev_cols:
            prev_col_counter = 0

        for col in range(3, 3 + extra_col):
            for i in range(U.rank):

                # get axis values
                y_lim = ax[i, 2].get_ylim()
                x_lim = ax[i, 2].get_xlim()
                y_ticks = ax[i, 2].get_yticks()
                y_tickl = ax[i, 2].get_yticklabels()
                x_ticks = ax[i, 2].get_xticks()
                x_tickl = ax[i, 2].get_xticklabels()

                # running
                if plot_running:
                    scale_by = np.nanmax(speed) / y_lim[1]
                    if not np.isnan(scale_by):
                        ax[i, col].plot(np.array(speed.tolist()) / scale_by, color=[1, 0.1, 0.6, 0.2])
                        # , label='speed')

                # Orientation - main variable to plot
                if col == 3:
                    ori_vals = [0, 135, 270]
                    color_vals = [[0.28, 0.68, 0.93, alpha], [0.84, 0.12, 0.13, alpha],
                                  [0.46, 0.85, 0.47, alpha]]
                    for k in range(0, 3):
                        ax[i, col].plot(trial_num[orientation == ori_vals[k]],
                                        U.factors[2][orientation == ori_vals[k], i], 'o',
                                        label=str(ori_vals[k]), color=color_vals[k], markersize=2)
                    if i == 0:
                        ax[i, col].set_title('Orientation')
                        ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                          borderaxespad=2.5)
                # Condition - main variable to plot
                elif col == 4:
                    cs_vals = ['plus', 'minus', 'neutral']
                    cs_labels = ['plus', 'minus', 'neutral']
                    color_vals = [[0.46, 0.85, 0.47, alpha], [0.84, 0.12, 0.13, alpha],
                                  [0.28, 0.68, 0.93, alpha]]
                    col = 4
                    for k in range(0, 3):
                        ax[i, col].plot(trial_num[condition == cs_vals[k]],
                                        U.factors[2][condition == cs_vals[k], i], 'o',
                                        label=str(cs_labels[k]), color=color_vals[k], markersize=2)
                    if i == 0:
                        ax[i, col].set_title('Condition')
                        ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                          borderaxespad=2.5)
                # Trial error - main variable to plot
                elif col == 5:
                    trialerror_vals = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                    trialerror_labels = ['hit',
                                         'miss',
                                         'neutral correct reject',
                                         'neutral false alarm',
                                         'minus correct reject',
                                         'minus false alarm',
                                         'blank correct reject',
                                         'blank false alarm',
                                         'pav early licking',
                                         'pav late licking']
                    for k in trialerror_vals:
                        ax[i, col].plot(trial_num[trialerror == trialerror_vals[k]],
                                        U.factors[2][trialerror == trialerror_vals[k], i], 'o',
                                        label=str(trialerror_labels[k]), alpha=0.8, markersize=2)
                    if i == 0:
                        ax[i, col].set_title('Trialerror')
                        ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                          borderaxespad=2.5)
                # State or HMM engagement - main variable to plot
                elif col == 6:
                    if hunger_or_hmm == 'hunger':
                        h_vals = ['hungry', 'sated', 'disengaged']
                        h_labels = ['hungry', 'sated', 'disengaged']
                        color_vals = [[1, 0.6, 0.3, alpha], [0.7, 0.9, 0.4, alpha],
                                      [0.6, 0.5, 0.6, alpha], [0.0, 0.9, 0.4, alpha]]
                        for k in range(0, 3):
                            ax[i, col].plot(trial_num[hunger == h_vals[k]],
                                            U.factors[2][hunger == h_vals[k], i], 'o',
                                            label=str(h_labels[k]), color=color_vals[k], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('State')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)
                    elif hunger_or_hmm == 'hmm':
                        h_vals = ['engaged', 'disengaged']
                        h_labels = ['engaged', 'disengaged']
                        color_vals = [[1, 0.6, 0.3, alpha],
                                      [0.7, 0.9, 0.4, alpha]]

                        ax[i, col].plot(trial_num[hmm],
                                        U.factors[2][hmm, i], 'o',
                                        label=str(h_labels[0]), color=color_vals[0], markersize=2)
                        ax[i, col].plot(trial_num[~hmm],
                                        U.factors[2][~hmm, i], 'o',
                                        label=str(h_labels[1]), color=color_vals[1], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('HMM engaged')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)

                # Running thresholded at 5 cm/s - main variable to plot
                elif col == 7:
                    speed_bool = speed.values > 4
                    color_vals = sns.color_palette("hls", 2)

                    ax[i, col].plot(trial_num[~speed_bool],
                                    U.factors[2][~speed_bool, i], 'o',
                                    label='stationary',
                                    color=color_vals[1],
                                    alpha=0.3,
                                    markersize=2)

                    ax[i, col].plot(trial_num[speed_bool],
                                    U.factors[2][speed_bool, i], 'o',
                                    label='running',
                                    color=color_vals[0],
                                    alpha=0.3,
                                    markersize=2)
                    if i == 0:
                        ax[i, col].set_title('Running')
                        ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                          borderaxespad=2.5)

                if add_prev_cols:
                    # Trial history in some form - main variable to plot
                    if col >= 8:
                        on_color = ['#9fff73', '#ff663c', '#a5ff89', '#63e5ff', '#ff5249', '#6b54ff']
                        off_color = ['#ff739f', '#3cffec', '#ff89a5', '#ff8f63', '#49ff6a', '#ffb554']
                        # here CS is for the initial learning period
                        prev_col_list = [
                            'prev_reward',
                            'prev_punish',
                            'prev_same_plus',
                            'prev_same_neutral',
                            'prev_same_minus',
                            'prev_blank']
                        prev_col_titles = [
                            'Prev Reward',
                            'Prev Punishment',
                            'Prev Same Cue: initial plus',
                            'Prev Same Cue: initial neutral',
                            'Prev Same Cue: initial minus',
                            'Prev Blank']
                        prev_col_labels = [
                            'rewarded [-1]',
                            'punishment [-1]',
                            'initial plus [-1]',
                            'initial neutral [-1]',
                            'initial minus [-1]',
                            'blank [-1]']
                        current_col = prev_col_list[prev_col_counter]

                        # skip column if it is not in metadata (will result
                        # in blank axes at end)
                        if current_col not in meta.columns:
                            continue

                        # boolean of trial history
                        prev_same_bool = meta[current_col].values
                        if 'plus' in current_col:
                            matched_ori = [lookups.lookup[mouse]['plus']]
                        elif 'minus' in current_col:
                            matched_ori = [lookups.lookup[mouse]['minus']]
                        elif 'neutral' in current_col:
                            matched_ori = [lookups.lookup[mouse]['neutral']]
                        else:
                            matched_ori = [0, 135, 270]
                        same_ori_bool = meta['orientation'].isin(matched_ori).values

                        ax[i, col].plot(
                            trial_num[~prev_same_bool & same_ori_bool],
                            U.factors[2][~prev_same_bool & same_ori_bool, i],
                            'o',
                            label='not {}'.format(prev_col_labels[prev_col_counter]),
                            color=off_color[prev_col_counter],
                            alpha=alpha,
                            markersize=2)

                        ax[i, col].plot(
                            trial_num[prev_same_bool & same_ori_bool],
                            U.factors[2][prev_same_bool & same_ori_bool, i],
                            'o',
                            label=prev_col_labels[prev_col_counter],
                            color=on_color[prev_col_counter],
                            alpha=alpha,
                            markersize=2)

                        if i == 0:
                            ax[i, col].set_title(prev_col_titles[prev_col_counter])
                            ax[i, col].legend(
                                bbox_to_anchor=(0.5, 1.1),
                                loc='lower center',
                                borderaxespad=2.5)

                        # move onto next column
                        if i == U.rank - 1:
                            prev_col_counter += 1

                # plot days, reversal, or learning lines if there are any
                if col >= 2:
                    y_lim = ax[i, col].get_ylim()
                    if len(day_x) > 0:
                        for k in day_x:
                            ax[i, col].plot(
                                [k, k], y_lim, color='#969696', linewidth=1)
                    if len(lstate_x) > 0:
                        ls_vals = ['naive', 'learning', 'reversal1']
                        ls_colors = ['#66bd63', '#d73027', '#a50026']
                        for k in lstate_x:
                            ls = learning_state[int(k - 0.5)]
                            ax[i, col].plot(
                                [k, k], y_lim, color=ls_colors[ls_vals.index(ls)],
                                linewidth=1.5)

                # set axes labels
                ax[i, col].set_yticks(y_ticks)
                ax[i, col].set_yticklabels(y_tickl)
                ax[i, col].set_ylim(y_lim)
                ax[i, col].set_xlim(x_lim)

                # format axes
                ax[i, col].locator_params(nbins=4)
                ax[i, col].spines['top'].set_visible(False)
                ax[i, col].spines['right'].set_visible(False)
                ax[i, col].xaxis.set_tick_params(direction='out')
                ax[i, col].yaxis.set_tick_params(direction='out')
                ax[i, col].yaxis.set_ticks_position('left')
                ax[i, col].xaxis.set_ticks_position('bottom')

                # remove xticks on all but bottom row
                if i + 1 != U.rank:
                    plt.setp(ax[i, col].get_xticklabels(), visible=False)

                if col == 3:
                    ax[i, 0].set_ylabel('Component #' + str(i + 1), rotation=0,
                                        labelpad=45, verticalalignment='center',
                                        fontstyle='oblique')

        if filetype.lower() == 'pdf':
            suffix = '.pdf'
        elif filetype.lower() == 'eps':
            suffix = '.eps'
        else:
            suffix = '.png'
        plt.savefig(os.path.join(date_dir, '{}_rank_{}{}'.format(mouse, r, suffix)),
                    bbox_inches='tight')
        if verbose:
            plt.show()
        plt.close()


def groupday_varex_summary(
        mouse,
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=0.8,
        rectified=True,
        add_dropout_line=True,
        verbose=False):
    """
    Plot reconstruction error as variance explained across all whole groupday
    TCA decomposition ensemble.

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
        load_tag = '_nantrial' + str(nan_thresh)
        save_tag = ' nantrial ' + str(nan_thresh)
    else:
        load_tag = ''
        save_tag = ''

    # update saving tag if you used a cell score threshold
    if score_threshold:
        load_tag = '_score0pt' + str(int(score_threshold * 10)) + load_tag
        save_tag = ' score ' + str(score_threshold) + save_tag

    # title tag for rectification
    if rectified:
        r_tag = ' rectified'
        save_tag = save_tag + '_rectified'
    else:
        r_tag = ''

    # load dir
    load_dir = paths.tca_path(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    tensor_path = os.path.join(
        load_dir, str(mouse) + '_' + str(group_by) + load_tag
                  + '_group_decomp_' + str(trace_type) + '.npy')
    input_tensor_path = os.path.join(
        load_dir, str(mouse) + '_' + str(group_by) + load_tag
                  + '_group_tensor_' + str(trace_type) + '.npy')
    meta_path = os.path.join(
        load_dir, str(mouse) + '_' + str(group_by) + load_tag
                  + '_df_group_meta.pkl')

    # save dir
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'qc' + save_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    var_path = os.path.join(
        save_dir, str(mouse) + '_summary_variance_explained.pdf')

    # load your data
    ensemble = np.load(tensor_path)
    ensemble = ensemble.item()
    V = ensemble[method]
    X = np.load(input_tensor_path)

    # get reconstruction error as variance explained
    df_var = var.groupday_varex(
        flow.Mouse(mouse=mouse),
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold,
        rectified=rectified,
        verbose=verbose)
    df_var_drop = var.groupday_varex_drop_worst_comp(
        flow.Mouse(mouse=mouse),
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold,
        rectified=rectified,
        verbose=verbose)

    x_s = df_var['rank'].values
    var_s = df_var['variance_explained_tcamodel'].values
    x_drop = df_var_drop['rank'].values
    var_drop = df_var_drop['variance_explained_dropping_worst_comp'].values
    x0 = x_s[df_var['iteration'].values == 0]
    var0 = var_s[df_var['iteration'].values == 0]
    var_mean = df_var['variance_explained_meanmodel'].values[0]
    var_smooth = df_var['variance_explained_smoothmodel'].values[0]
    var_PCA = df_var['variance_explained_PCA'].values[0]
    if 'variance_explained_meandailymodel' in df_var.columns:
        var_mean_daily = df_var['variance_explained_meandailymodel'].values[0]
    else:
        var_mean_daily = []
    if 'variance_explained_tcamodel_utilized' in df_var.columns:
        var_util = df_var['variance_explained_tcamodel_utilized'].values
    else:
        var_util = []

    # create figure and axes
    buffer = 5
    right_pad = 5
    fig = plt.figure(figsize=(10, 8))
    gs = GridSpec(
        100, 100, figure=fig, left=0.05, right=.95, top=.95, bottom=0.05)
    ax = fig.add_subplot(gs[10:90 - buffer, :90 - right_pad])
    c = 0
    cmap = sns.color_palette('Paired', 6)

    # plot
    R = np.max([r for r in V.results.keys()])
    ax.scatter(x_s, var_s, color=cmap[c * 2], alpha=0.5)
    if add_dropout_line:
        ax.scatter(x_drop, var_drop, color=cmap[c * 2 + 1], alpha=0.5)
        if len(var_util) > 0:
            ax.scatter(x_s, var_util, color=cmap[c * 2 + 4], alpha=0.5)
    ax.scatter([R + 2], var_mean, color=cmap[c * 2], alpha=0.5)
    ax.scatter([R + 4], var_mean_daily, color=cmap[c * 2], alpha=0.5)
    ax.scatter([R + 6], var_PCA, color=cmap[c * 2], alpha=0.5)
    ax.plot(x0, var0, label=('mouse ' + mouse), color=cmap[c * 2])
    if add_dropout_line:
        ax.plot(x_drop, var_drop, label=('$mouse_-$ ' + mouse), color=cmap[c * 2 + 1])
        if len(var_util) > 0:
            ax.plot(x_s, var_util, label=('$mouse_-$ useful ' + mouse), color=cmap[c * 2 + 4])
    ax.plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c * 2])
    ax.plot([R + 3.5, R + 4.5], [var_mean_daily, var_mean_daily], color=cmap[c * 2])
    ax.plot([R + 5.5, R + 6.5], [var_PCA, var_PCA], color=cmap[c * 2])

    # add labels/titles
    biggest_rank = max(V.results.keys())
    x_labels = ['' for _ in range(biggest_rank)]
    for R in V.results:
        x_labels[R - 1] = str(R)
    # x_labels = [str(R) for R in V.results]
    x_labels.extend(
        ['', 'mean\ncell\nresp.',
         '', 'daily\nmean\ncell\nresp.',
         '', 'PCA$_{20}$'])
    ax.set_xticks(range(1, biggest_rank + 7))
    ax.set_xticklabels(x_labels, size=12)
    ax.set_yticklabels([round(s, 2) for s in ax.get_yticks()], size=14)
    ax.set_xlabel('model rank', size=18)
    ax.set_ylabel('variance explained', size=18)
    ax.set_title(
        'Variance Explained: ' + str(method) + r_tag + ', ' + str(mouse))
    ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    fig.savefig(var_path, bbox_inches='tight')


def groupday_varex_summary_cv(
        mouse,
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=0.8,
        train_test_split=0.8,
        rectified=True,
        verbose=False):
    """
    Plot reconstruction error as variance explained across all whole groupday
    TCA decomposition ensemble.

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
        load_tag = '_nantrial' + str(nan_thresh)
        save_tag = ' nantrial ' + str(nan_thresh)
    else:
        load_tag = ''
        save_tag = ''

    # update saving tag if you used a cell score threshold
    if score_threshold:
        load_tag = '_score' + str(score_threshold) + load_tag
        save_tag = ' score ' + str(score_threshold) + save_tag

    # update saving tag if you used a cell score threshold
    load_tag = load_tag + '_cv' + str(train_test_split)
    save_tag = save_tag + ' cv ' + str(train_test_split)

    # title tag for rectification
    if rectified:
        r_tag = ' rectified'
        save_tag = save_tag + '_rectified'
    else:
        r_tag = ''

    # load dir
    load_dir = paths.tca_path(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    tensor_path = os.path.join(
        load_dir, str(mouse) + '_' + str(group_by) + load_tag
                  + '_group_decomp_' + str(trace_type) + '.npy')

    # save dir
    save_dir = paths.tca_plots(
        mouse, 'group', pars=pars, word=word, group_pars=group_pars)
    save_dir = os.path.join(save_dir, 'qc' + save_tag)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    var_path = os.path.join(
        save_dir, str(mouse) + '_summary_variance_explained.pdf')

    # load your data
    ensemble = np.load(tensor_path)
    ensemble = ensemble.item()
    V = ensemble[method]

    # get reconstruction error as variance explained
    df_var = var.groupday_varex_cv_train_set(
        flow.Mouse(mouse=mouse),
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold,
        train_test_split=train_test_split,
        rectified=rectified,
        verbose=verbose)
    df_var_cv = var.groupday_varex_cv_test_set(
        flow.Mouse(mouse=mouse),
        trace_type=trace_type,
        method=method,
        cs=cs,
        warp=warp,
        word=word,
        group_by=group_by,
        nan_thresh=nan_thresh,
        score_threshold=score_threshold,
        train_test_split=train_test_split,
        rectified=rectified,
        verbose=verbose)

    # create figure and axes
    fig, ax = plt.subplots(1, 2, figsize=(20, 8), sharey=True)
    c = 0
    cmap = sns.color_palette('Paired', 2)
    for axc, train_test in enumerate([df_var, df_var_cv]):

        # training set
        x_s = train_test['rank'].values
        var_s = train_test['variance_explained_tcamodel'].values
        x0 = x_s[train_test['iteration'].values == 0]
        var0 = var_s[train_test['iteration'].values == 0]
        var_mean = train_test['variance_explained_meanmodel'].values[0]
        if 'variance_explained_PCA' in train_test.columns:
            var_PCA = train_test['variance_explained_PCA'].values[0]
        else:
            var_PCA = []
        if 'variance_explained_meandailymodel' in train_test.columns:
            var_mean_daily = train_test['variance_explained_meandailymodel'].values[0]
        else:
            var_mean_daily = []

        # plot
        R = np.max([r for r in V.results.keys()])
        ax[axc].scatter(x_s, var_s, color=cmap[c * 2], alpha=0.5)
        ax[axc].scatter([R + 2], var_mean, color=cmap[c * 2], alpha=0.5)
        ax[axc].scatter([R + 4], var_mean_daily, color=cmap[c * 2], alpha=0.5)
        ax[axc].plot(x0, var0, label=('mouse ' + mouse), color=cmap[c * 2])
        ax[axc].plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c * 2])
        ax[axc].plot([R + 3.5, R + 4.5], [var_mean_daily, var_mean_daily], color=cmap[c * 2])
        if axc == 0:
            ax[axc].scatter([R + 6], var_PCA, color=cmap[c * 2], alpha=0.5)
            ax[axc].plot([R + 5.5, R + 6.5], [var_PCA, var_PCA], color=cmap[c * 2])

    # add labels/titles
    x_labels = [str(R) for R in V.results]
    x_labels.extend(
        ['', 'mean\ncell\nresp.',
         '', 'daily\nmean\ncell\nresp.',
         '', 'PCA$_{20}$'])
    ax[0].set_xticks(range(1, len(V.results) + 7))
    ax[1].set_xticks(range(1, len(V.results) + 7))
    ax[0].set_xticklabels(x_labels, size=12)
    ax[1].set_xticklabels(x_labels, size=12)
    ax[0].set_yticklabels([round(s, 2) for s in ax[0].get_yticks()], size=14)
    ax[0].set_xlabel('model rank', size=18)
    ax[1].set_xlabel('model rank', size=18)
    ax[0].set_ylabel('variance explained', size=18)
    ax[0].set_title(
        'Variance explained training set: ' + str(method) + r_tag + ', ' + str(mouse))
    ax[1].set_title(
        'Variance explained test set: ' + str(method) + r_tag + ', ' + str(mouse))
    ax[1].legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    fig.savefig(var_path, bbox_inches='tight')


def groupday_varex_percell(  # TODO MAKE THIS WORK FOR GROUPDAY
        mouse,
        method='ncp_bcd',
        trace_type='zscore_day',
        cs='',
        warp=False,
        word=None,
        group_by=None,
        nan_thresh=None,
        ve_min=0.05,
        filetype='pdf'):
    """
    Plot TCA reconstruction error as variance explained per cell
    for TCA decomposition. Create folder of variance explained per cell
    swarm plots. Calculate summary plots of 'fraction of maximum variance
    explained' per cell by rank for all cells given a certain (ve_min) threshold
    for maximum variance explained

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools
    ve_min: float; minimum variance explained for best rank per cell
                   to be included in summary of fraction of maximum variance
                   explained

    Returns:
    --------
    Saves figures to .../analysis folder/ .../qc
                                             .../variance explained per cell

    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    # create folder structure if needed
    cs_tag = '' if len(cs) == 0 else ' ' + str(cs)
    warp_tag = '' if warp is False else ' warp'
    folder_name = 'tensors single ' + str(trace_type) + cs_tag + warp_tag

    ve, ve_max, ve_frac, rank_num, day_num, cell_num = [], [], [], [], [], []
    for c, day1 in enumerate(days, 0):

        # get dirs for loading
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        if not os.path.isdir(load_dir): os.mkdir(load_dir)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_single_decomp_'
                                   + str(trace_type) + '.npy')
        input_tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                         + str(day1.date) + '_single_tensor_'
                                         + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(input_tensor_path): continue

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        V = ensemble[method]
        X = np.load(input_tensor_path)

        # get reconstruction error as variance explained per cell
        for cell in range(0, np.shape(X)[0]):
            rank_ve_vec = []
            rank_vec = []
            for r in V.results:
                U = V.results[r][0].factors.full()
                Usub = X - U
                rank_ve = (np.var(X[cell, :, :]) - np.var(Usub[cell, :, :])) / np.var(X[cell, :, :])
                rank_ve_vec.append(rank_ve)
                rank_vec.append(r)
            max_ve = np.max(rank_ve_vec)
            ve.extend(rank_ve_vec)
            ve_max.extend([max_ve for s in rank_ve_vec])
            ve_frac.extend(rank_ve_vec / max_ve)
            rank_num.extend(rank_vec)
            day_num.extend([c + 1 for s in rank_ve_vec])
            cell_num.extend([cell for s in rank_ve_vec])

    # build pd dataframe of all variance measures
    index = pd.MultiIndex.from_arrays([
        day_num,
        rank_num,
        ve,
        ve_max,
        ve_frac,
        cell_num,
    ],
        names=['day', 'rank', 'variance_explained', 'max_ve', 'frac_ve', 'cell'])
    df = pd.DataFrame(index=index)
    df = df.reset_index()

    # make a rainbow colormap, HUSL space but does not circle back on itself
    cmap = sns.color_palette('hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
    cmap = cmap[0:np.unique(df['rank'])[-1]]

    # Part 1
    # slice df, only look at cells with a max variance >5%
    sliced_df2 = df.loc[(df['day']) & (df['max_ve'] >= ve_min), :]

    # CDF plot
    fig1 = plt.figure(figsize=(15, 9))
    for i in np.unique(sliced_df2['rank']):
        input_ve = sliced_df2.loc[(sliced_df2['rank'] == i), 'frac_ve']
        ax = sns.distplot(input_ve, kde_kws={'cumulative': True, 'lw': 2, 'color': cmap[i - 1], 'label': str(i)},
                          hist=False)
        lg = ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax.set_title(mouse + ', Fraction of maximum variance explained per cell, CDF')
        ax.set_xlabel('Fraction of maximum variance explained')

    # swarm plot
    fig2 = plt.figure(figsize=(18, 6))
    ax2 = sns.violinplot(x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=3, alpha=1, inner=None, palette=cmap)
    ax2.set_title(mouse + ', Fraction of maximum variance explained per cell, violin')
    ax2.set_ylabel('Fraction of maximum variance explained')

    # swarm plot
    fig3 = plt.figure(figsize=(18, 6))
    ax3 = sns.swarmplot(x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=2, alpha=1, palette=cmap)
    ax3.set_title(mouse + ', Fraction of maximum variance explained per cell, swarm')
    ax3.set_ylabel('Fraction of maximum variance explained')

    # set up saving paths/dir
    save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
    save_dir = os.path.join(save_dir, 'qc')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_singleday_frac_max_var_expl_' + trace_type

    # save
    if filetype.lower() == 'pdf':
        suffix = '.pdf'
    elif filetype.lower() == 'eps':
        suffix = '.eps'
    else:
        suffix = '.png'
    fig1.savefig(os.path.join(save_dir, save_file_base + '_CDF' + suffix), bbox_inches='tight')
    fig2.savefig(os.path.join(save_dir, save_file_base + '_violin' + suffix), bbox_inches='tight')
    fig3.savefig(os.path.join(save_dir, save_file_base + '_swarm.png'), bbox_inches='tight')

    # Part 2
    # plot sorted per "cell" varienace explained (approximate, this is by unique max_ve not cells per se)
    # set up saving paths/dir
    save_dir = os.path.join(save_dir, 'variance explained per cell')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_singleday_var_expl_' + trace_type

    for d in np.unique(df['day']):
        sliced_df = df.loc[(df['day'] == d), :]

        # make a rainbow colormap, HUSL space but does not circle back on itself
        cmap = sns.color_palette('hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
        cmap = cmap[0:np.unique(df['rank'])[-1]]

        fig0 = plt.figure(figsize=(20, 6))
        ax0 = sns.swarmplot(x=sliced_df['max_ve'], y=sliced_df['variance_explained'],
                            hue=sliced_df['rank'], palette=cmap)
        lg = ax0.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax0.set_xlabel('cell count')
        x_lim = ax0.get_xlim()
        ticks = ax0.get_xticks()
        new_ticks = [t for t in ticks[10::10]]
        ax0.set_xticks(new_ticks)
        ax0.set_xticklabels(np.arange(10, len(ticks), 10))
        ax0.set_title(mouse + ', Variance explained per cell, day ' + str(d))

        fig0.savefig(os.path.join(save_dir, save_file_base + '_day_' + str(d)
                                  + suffix), bbox_inches='tight')
        plt.close()


"""
----------------------------- PAIR DAY PLOTS -----------------------------
"""


def pairday_qc(
        mouse,
        trace_type='zscore',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot similarity and error plots for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved

    Returns:
    --------
    Saves figures to .../analysis folder  .../qc
    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'green',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'blue',
                'alpha': 0.5,
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'alpha': 0.5,
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'red',
                'alpha': 0.5,
            },
        },
    }

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # load
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                   + '_' + str(day2.date) + '_pair_decomp_' + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save
        save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        error_path = os.path.join(save_dir, str(day1.mouse) + '_' + str(day1.date)
                                  + '_' + str(day2.date) + '_objective.pdf')
        sim_path = os.path.join(save_dir, str(day1.mouse) + '_' + str(day1.date)
                                + '_' + str(day2.date) + '_similarity.pdf')

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # plot error and similarity plots across rank number
        plt.figure()
        for m in ensemble:
            tt.plot_objective(ensemble[m], **plot_options[m])  # ax=ax[0])
        plt.legend()
        plt.title('Objective Function')
        plt.savefig(error_path)
        if verbose:
            plt.show()
        plt.clf()

        for m in ensemble:
            tt.plot_similarity(ensemble[m], **plot_options[m])  # ax=ax[1])
        plt.legend()
        plt.title('Iteration Similarity')
        plt.savefig(sim_path)
        if verbose:
            plt.show()
        plt.close()


def pairday_factors(
        mouse,
        trace_type='zscore',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot TCA factors for all days and ranks/components for
    TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors
    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'red',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
    }

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # load
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_' + str(day2.date)
                                   + '_pair_decomp_' + str(trace_type)
                                   + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save
        save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'factors')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # make necessary dirs
        date_dir = os.path.join(
            save_dir, str(day1.date) + '_' + str(day2.date) + ' ' + method)
        if not os.path.isdir(date_dir):
            os.mkdir(date_dir)

        # sort neuron factors by component they belong to most
        sort_ensemble, my_sorts = tca._sortfactors(ensemble[method])

        for r in sort_ensemble.results:

            fig = tt.plot_factors(sort_ensemble.results[r][0].factors,
                                  plots=['bar', 'line', 'scatter'],
                                  axes=None,
                                  scatter_kw=plot_options[method]['scatter_kw'],
                                  line_kw=plot_options[method]['line_kw'],
                                  bar_kw=plot_options[method]['bar_kw'])

            ax = fig[0].axes
            ax[0].set_title('Neuron factors')
            ax[1].set_title('Temporal factors')
            ax[2].set_title('Trial factors')

            count = 1
            for k in range(0, len(ax)):
                if np.mod(k + 1, 3) == 1:
                    ax[k].set_ylabel('Component #' + str(count), rotation=0,
                                     labelpad=45, verticalalignment='center',
                                     fontstyle='oblique')
                    count = count + 1

            # Show plots.
            plt.savefig(
                os.path.join(date_dir, 'rank_' + str(int(r)) + '.png'),
                bbox_inches='tight')
            if verbose:
                plt.show()
            plt.close()


def pairday_factors_annotated(
        mouse,
        trace_type='zscore_day',
        cs='',
        warp=False,
        word=None,
        method='ncp_bcd',
        extra_col=4,
        alpha=0.6,
        plot_running=True,
        scale_y=False,
        filetype='pdf',
        verbose=False):
    """
    Plot TCA factors with trial metadata annotations for all days
    and ranks/components for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str
        Mouse name.
    trace_type : str
        dff, zscore, zscore_iti, zscore_day, deconvolved
    method : str
        TCA fit method from tensortools
    cs : str
        Cs stimuli to include, plus/minus/neutral, 0/135/270, etc. '' empty
        includes all stimuli
    warp : bool
        Use traces with time-warped outcome.
    extra_col : int
        Number of columns to add to the original three factor columns
    alpha : float
        Value between 0 and 1 for transparency of markers
    plot_running : bool
        Include trace of scaled (to plot max) average running speed during trial
    verbose : bool
        Show plots as they are made.

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors annotated
    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    # use matplotlib plotting defaults
    mpl.rcParams.update(mpl.rcParamsDefault)

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'red',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
    }

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # load dirs
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_' + str(day2.date)
                                   + '_pair_decomp_' + str(trace_type)
                                   + '.npy')
        meta_path = os.path.join(load_dir, str(day1.mouse) + '_' +
                                 str(day1.date) + '_' + str(day2.date)
                                 + '_df_pair_meta.pkl')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(meta_path): continue

        # save dirs
        save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'factors annotated')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        date_dir = os.path.join(save_dir, str(day1.date) + '_' + str(day2.date)
                                + ' ' + method)
        if not os.path.isdir(date_dir): os.mkdir(date_dir)

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        meta = pd.read_pickle(meta_path)
        orientation = meta['orientation']
        trial_num = np.arange(0, len(orientation))
        condition = meta['condition']
        trialerror = meta['trialerror']
        hunger = deepcopy(meta['hunger'])
        speed = meta['speed']
        dates = meta.reset_index()['date']
        learning_state = meta['learning_state']

        # calculate change indices for days and reversal/learning
        udays = {d: c for c, d in enumerate(np.unique(dates))}
        ndays = np.diff([udays[i] for i in dates])
        day_x = np.where(ndays)[0] + 0.5
        ustate = {d: c for c, d in enumerate(np.unique(learning_state))}
        nstate = np.diff([ustate[i] for i in learning_state])
        lstate_x = np.where(nstate)[0] + 0.5

        # merge hunger and tag info for plotting hunger
        tags = meta['tag']
        hunger[tags == 'disengaged'] = 'disengaged'

        # sort neuron factors by component they belong to most
        sort_ensemble, my_sorts = tca._sortfactors(ensemble[method])

        for r in sort_ensemble.results:

            U = sort_ensemble.results[r][0].factors

            fig, axes = plt.subplots(U.rank, U.ndim + extra_col,
                                     figsize=(9 + extra_col, U.rank))
            figt = tt.plot_factors(
                U, plots=['bar', 'line', 'scatter'],
                axes=None,
                fig=fig,
                scatter_kw=plot_options[method]['scatter_kw'],
                line_kw=plot_options[method]['line_kw'],
                bar_kw=plot_options[method]['bar_kw'])
            ax = figt[0].axes
            ax[0].set_title('Neuron factors')
            ax[1].set_title('Temporal factors')
            ax[2].set_title('Trial factors')

            # add title to whole figure
            ax[0].text(-1.2, 4, '\n' + mouse + ': \n\nrank: ' + str(int(r))
                       + '\nmethod: ' + method + ' \ndates: '
                       + str(day1.date) + ' - ' + str(day2.date),
                       fontsize=12, transform=ax[0].transAxes,
                       color='#969696')

            # reshape for easier indexing
            ax = np.array(ax).reshape((U.rank, -1))

            # rescale the y-axis for trials
            if scale_y:
                for i in range(U.rank):
                    y_lim = np.array(ax[i, 2].get_ylim()) * 0.8
                    y_ticks = ax[i, 2].get_yticks()
                    y_ticks[-1] = y_lim[-1]
                    y_ticks = np.round(y_ticks, 2)
                    # y_tickl = [str(y) for y in y_ticks]
                    ax[i, 2].set_ylim(y_lim)
                    ax[i, 2].set_yticks(y_ticks)
                    ax[i, 2].set_yticklabels(y_ticks)

            # add a line for stim onset and offset
            # NOTE: assumes downsample, 1 sec before onset, 3 sec stim
            for i in range(U.rank):
                y_lim = ax[i, 1].get_ylim()
                ons = 15.5 * 1
                offs = ons + 15.5 * 3
                ax[i, 1].plot([ons, ons], y_lim, ':k')
                ax[i, 1].plot([offs, offs], y_lim, ':k')

            for col in range(3, 3 + extra_col):
                for i in range(U.rank):

                    # get axis values
                    y_lim = ax[i, 2].get_ylim()
                    x_lim = ax[i, 2].get_xlim()
                    y_ticks = ax[i, 2].get_yticks()
                    y_tickl = ax[i, 2].get_yticklabels()
                    x_ticks = ax[i, 2].get_xticks()
                    x_tickl = ax[i, 2].get_xticklabels()

                    # running
                    if plot_running:
                        scale_by = np.nanmax(speed) / y_lim[1]
                        if not np.isnan(scale_by):
                            ax[i, col].plot(
                                np.array(speed.tolist()) / scale_by,
                                color=[1, 0.1, 0.6, 0.2])
                            # , label='speed')

                    # Orientation - main variable to plot
                    if col == 3:
                        ori_vals = [0, 135, 270]
                        color_vals = [[0.28, 0.68, 0.93, alpha],
                                      [0.84, 0.12, 0.13, alpha],
                                      [0.46, 0.85, 0.47, alpha]]
                        for k in range(0, 3):
                            ax[i, col].plot(
                                trial_num[orientation == ori_vals[k]],
                                U.factors[2][orientation == ori_vals[k], i], 'o',
                                label=str(ori_vals[k]), color=color_vals[k],
                                markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Orientation')
                            ax[i, col].legend(
                                bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                borderaxespad=2.5)
                    elif col == 4:
                        cs_vals = ['plus', 'minus', 'neutral']
                        cs_labels = ['plus', 'minus', 'neutral']
                        color_vals = [[0.46, 0.85, 0.47, alpha],
                                      [0.84, 0.12, 0.13, alpha],
                                      [0.28, 0.68, 0.93, alpha]]
                        col = 4
                        for k in range(0, 3):
                            ax[i, col].plot(
                                trial_num[condition == cs_vals[k]],
                                U.factors[2][condition == cs_vals[k], i], 'o',
                                label=str(cs_labels[k]), color=color_vals[k],
                                markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Condition')
                            ax[i, col].legend(
                                bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                borderaxespad=2.5)
                    elif col == 5:
                        trialerror_vals = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                        trialerror_labels = ['hit',
                                             'miss',
                                             'neutral correct reject',
                                             'neutral false alarm',
                                             'minus correct reject',
                                             'minus false alarm',
                                             'blank correct reject',
                                             'blank false alarm',
                                             'pav early licking',
                                             'pav late licking', ]
                        for k in trialerror_vals:
                            ax[i, col].plot(
                                trial_num[trialerror == trialerror_vals[k]],
                                U.factors[2][trialerror == trialerror_vals[k], i],
                                'o', label=str(trialerror_labels[k]), alpha=0.8,
                                markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Trialerror')
                            ax[i, col].legend(
                                bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                borderaxespad=2.5)

                    elif col == 6:
                        h_vals = ['hungry', 'sated', 'disengaged']
                        h_labels = ['hungry', 'sated', 'disengaged']
                        color_vals = [[1, 0.6, 0.3, alpha],
                                      [0.7, 0.9, 0.4, alpha],
                                      [0.6, 0.5, 0.6, alpha],
                                      [0.0, 0.9, 0.4, alpha]]
                        for k in range(0, 3):
                            ax[i, col].plot(
                                trial_num[hunger == h_vals[k]],
                                U.factors[2][hunger == h_vals[k], i],
                                'o', label=str(h_labels[k]),
                                color=color_vals[k], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('State')
                            ax[i, col].legend(
                                bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                borderaxespad=2.5)

                    # plot days, reversal, or learning lines if there are any
                    if col >= 2:
                        y_lim = ax[i, col].get_ylim()
                        if len(day_x) > 0:
                            for k in day_x:
                                ax[i, col].plot(
                                    [k, k], y_lim, color='#969696',
                                    linewidth=1)
                        if len(lstate_x) > 0:
                            ls_vals = ['naive', 'learning', 'reversal1']
                            ls_colors = ['#66bd63', '#d73027', '#a50026']
                            for k in lstate_x:
                                ls = learning_state[int(k - 0.5)]
                                ax[i, col].plot(
                                    [k, k], y_lim,
                                    color=ls_colors[ls_vals.index(ls)],
                                    linewidth=1.5)

                    # set axes labels
                    ax[i, col].set_yticks(y_ticks)
                    ax[i, col].set_yticklabels(y_tickl)
                    ax[i, col].set_ylim(y_lim)
                    ax[i, col].set_xlim(x_lim)

                    # format axes
                    ax[i, col].locator_params(nbins=4)
                    ax[i, col].spines['top'].set_visible(False)
                    ax[i, col].spines['right'].set_visible(False)
                    ax[i, col].xaxis.set_tick_params(direction='out')
                    ax[i, col].yaxis.set_tick_params(direction='out')
                    ax[i, col].yaxis.set_ticks_position('left')
                    ax[i, col].xaxis.set_ticks_position('bottom')

                    # remove xticks on all but bottom row
                    if i + 1 != U.rank:
                        plt.setp(ax[i, col].get_xticklabels(), visible=False)

                    if col == 3:
                        ax[i, 0].set_ylabel('Component #' + str(i + 1), rotation=0,
                                            labelpad=45, verticalalignment='center', fontstyle='oblique')

            if filetype.lower() == 'pdf':
                suffix = '.pdf'
            elif filetype.lower() == 'eps':
                suffix = '.eps'
            else:
                suffix = '.png'
            plt.savefig(os.path.join(date_dir, 'rank_' + str(int(r)) + suffix),
                        bbox_inches='tight')
            if verbose:
                plt.show()
            plt.close()


def pairday_qc_summary(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot similarity and objective (measure of reconstruction error) plots
    across all days for TCA decomposition ensembles.

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

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    cmap = sns.color_palette('hls', n_colors=len(days))

    # create figure and axes
    buffer = 5
    right_pad = 5

    fig0 = plt.figure(figsize=(10, 8))
    gs0 = GridSpec(100, 100, figure=fig0, left=0.05, right=.95, top=.95, bottom=0.05)
    ax0 = fig0.add_subplot(gs0[10:90 - buffer, :90 - right_pad])

    fig1 = plt.figure(figsize=(10, 8))
    gs1 = GridSpec(100, 100, figure=fig1, left=0.05, right=.95, top=.95, bottom=0.05)
    ax1 = fig1.add_subplot(gs1[10:90 - buffer, :90 - right_pad])

    # plt.figure()
    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # load dirs
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_' + str(day2.date)
                                   + '_pair_decomp_' + str(trace_type)
                                   + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save dirs
        save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        error_path = os.path.join(save_dir, str(day1.mouse) + '_summary_objective.pdf')
        sim_path = os.path.join(save_dir, str(day1.mouse) + '_summary_similarity.pdf')

        # plotting options for the unconstrained and nonnegative models.
        plot_options = {
            'cp_als': {
                'line_kw': {
                    'color': cmap[c],
                    'label': 'pair ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
            'ncp_hals': {
                'line_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                    'label': 'pair ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
            'ncp_bcd': {
                'line_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                    'label': 'pair ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
        }

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # plot error and similarity plots across rank number
        tt.plot_objective(ensemble[method], **plot_options[method], ax=ax0)
        tt.plot_similarity(ensemble[method], **plot_options[method], ax=ax1)

    # add legend, title
    ax0.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
    ax0.set_title('Objective Function: ' + str(method) + ', ' + mouse)
    ax1.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
    ax1.set_title('Iteration Similarity: ' + str(method) + ', ' + mouse)

    # save figs
    fig0.savefig(error_path, bbox_inches='tight')
    fig1.savefig(sim_path, bbox_inches='tight')

    if verbose:
        fig0.show()
        fig1.show()


def pairday_varex_summary(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        verbose=False):
    """
    Plot reconstruction error as variance explained across all days for
    TCA decomposition ensembles.

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

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    cmap = sns.color_palette(sns.cubehelix_palette(len(days)))

    # create figure and axes
    buffer = 5
    right_pad = 5
    fig = plt.figure(figsize=(10, 8))
    gs = GridSpec(100, 100, figure=fig, left=0.05, right=.95, top=.95, bottom=0.05)
    ax = fig.add_subplot(gs[10:90 - buffer, :90 - right_pad])

    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # load dirs
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_' + str(day2.date)
                                   + '_pair_decomp_' + str(trace_type)
                                   + '.npy')
        input_tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                         + str(day1.date) + '_' + str(day2.date)
                                         + '_pair_tensor_' + str(trace_type)
                                         + '.npy')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(input_tensor_path): continue

        # save dirs
        save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        var_path = os.path.join(save_dir, str(day1.mouse)
                                + '_summary_variance_cubehelix.pdf')

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        V = ensemble[method]
        X = np.load(input_tensor_path)

        # get reconstruction error as variance explained
        var, var_s, x, x_s = [], [], [], []
        for r in V.results:
            bU = V.results[r][0].factors.full()
            var.append((np.var(X) - np.var(X - bU)) / np.var(X))
            x.append(r)
            for it in range(0, len(V.results[r])):
                U = V.results[r][it].factors.full()
                var_s.extend([(np.var(X) - np.var(X - U)) / np.var(X)])
                x_s.extend([r])

        # mean response of neuron across trials
        mU = np.mean(X, axis=2, keepdims=True) * np.ones((1, 1, np.shape(X)[2]))
        var_mean = (np.var(X) - np.var(X - mU)) / np.var(X)

        # smoothed response of neuron across time
        smU = np.convolve(X.reshape((X.size)), np.ones(5, dtype=np.float64) / 5, 'same').reshape(np.shape(X))
        var_smooth = (np.var(X) - np.var(X - smU)) / np.var(X)

        # plot
        R = np.max([r for r in V.results.keys()])
        ax.scatter(x_s, var_s, color=cmap[c], alpha=0.5)
        ax.scatter([R + 2], var_mean, color=cmap[c], alpha=0.5)
        ax.scatter([R + 4], var_smooth, color=cmap[c], alpha=0.5)
        ax.plot(x, var, label=('pair ' + str(c)), color=cmap[c])
        ax.plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c])
        ax.plot([R + 3.5, R + 4.5], [var_smooth, var_smooth], color=cmap[c])

    # add labels/titles
    x_labels = [str(R) for R in V.results]
    x_labels.extend(['', 'mean\n cell\n response', '', 'smooth\n response\n (0.3s)'])
    ax.set_xticks(range(1, len(V.results) + 5))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel('model rank')
    ax.set_ylabel('fractional variance explained')
    ax.set_title('Variance Explained: ' + str(method) + ', ' + mouse)
    ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    fig.savefig(var_path, bbox_inches='tight')


def pairday_varex_percell(
        mouse,
        method='ncp_bcd',
        trace_type='zscore_day',
        cs='',
        warp=False,
        word=None,
        ve_min=0.05):
    """
    Plot TCA reconstruction error as variance explained per cell
    for TCA decomposition. Create folder of variance explained per cell
    swarm plots. Calculate summary plots of 'fraction of maximum variance
    explained' per cell by rank for all cells given a certain (ve_min) threshold
    for maximum variance explained

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools
    ve_min: float; minimum variance explained for best rank per cell
                   to be included in summary of fraction of maximum variance
                   explained

    Returns:
    --------
    Saves figures to .../analysis folder/ .../qc
                                             .../variance explained per cell

    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    ve, ve_max, ve_frac, rank_num, day_num, cell_num = [], [], [], [], [], []
    for c, day1 in enumerate(days, 0):
        try:
            day2 = days[c + 1]
        except IndexError:
            print('done.')
            break

        # get dirs for loading
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_' + str(day2.date)
                                   + '_pair_decomp_' + str(trace_type)
                                   + '.npy')
        input_tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                         + str(day1.date) + '_' + str(day2.date)
                                         + '_pair_tensor_' + str(trace_type)
                                         + '.npy')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(input_tensor_path): continue

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        V = ensemble[method]
        X = np.load(input_tensor_path)

        # get reconstruction error as variance explained per cell
        for cell in range(0, np.shape(X)[0]):
            rank_ve_vec = []
            rank_vec = []
            for r in V.results:
                U = V.results[r][0].factors.full()
                Usub = X - U
                rank_ve = (np.var(X[cell, :, :]) - np.var(Usub[cell, :, :])) / np.var(X[cell, :, :])
                rank_ve_vec.append(rank_ve)
                rank_vec.append(r)
            max_ve = np.max(rank_ve_vec)
            ve.extend(rank_ve_vec)
            ve_max.extend([max_ve for s in rank_ve_vec])
            ve_frac.extend(rank_ve_vec / max_ve)
            rank_num.extend(rank_vec)
            day_num.extend([c + 1 for s in rank_ve_vec])
            cell_num.extend([cell for s in rank_ve_vec])

    # build pd dataframe of all variance measures
    index = pd.MultiIndex.from_arrays([
        day_num,
        rank_num,
        ve,
        ve_max,
        ve_frac,
        cell_num,
    ],
        names=['day', 'rank', 'variance_explained', 'max_ve', 'frac_ve', 'cell'])
    df = pd.DataFrame(index=index)
    df = df.reset_index()

    # make a rainbow colormap, HUSL space but does not circle back on itself
    cmap = sns.color_palette('hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
    cmap = cmap[0:np.unique(df['rank'])[-1]]

    # Part 1
    # slice df, only look at cells with a max variance >5%
    sliced_df2 = df.loc[(df['day']) & (df['max_ve'] >= ve_min), :]

    # CDF plot
    fig1 = plt.figure(figsize=(15, 9))
    for i in np.unique(sliced_df2['rank']):
        input_ve = sliced_df2.loc[(sliced_df2['rank'] == i), 'frac_ve']
        ax = sns.distplot(
            input_ve, kde_kws={'cumulative': True, 'lw': 2, 'color': cmap[i - 1],
                               'label': str(i)}, hist=False)
        lg = ax.legend(
            bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax.set_title(
            mouse + ', Fraction of maximum variance explained per cell, CDF')
        ax.set_xlabel('Fraction of maximum variance explained')

    # swarm plot
    fig2 = plt.figure(figsize=(18, 6))
    ax2 = sns.violinplot(
        x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=3, alpha=1,
        inner=None, palette=cmap)
    ax2.set_title(
        mouse + ', Fraction of maximum variance explained per cell, violin')
    ax2.set_ylabel('Fraction of maximum variance explained')

    # swarm plot
    fig3 = plt.figure(figsize=(18, 6))
    ax3 = sns.swarmplot(
        x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=2, alpha=1,
        palette=cmap)
    ax3.set_title(
        mouse + ', Fraction of maximum variance explained per cell, swarm')
    ax3.set_ylabel('Fraction of maximum variance explained')

    # set up saving paths/dir
    save_dir = paths.tca_plots(mouse, 'pair', pars=pars, word=word)
    save_dir = os.path.join(save_dir, 'qc')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_pairday_frac_max_var_expl_' + trace_type

    # save
    fig1.savefig(
        os.path.join(save_dir, save_file_base + '_CDF.pdf'),
        bbox_inches='tight')
    fig2.savefig(
        os.path.join(save_dir, save_file_base + '_violin.pdf'),
        bbox_inches='tight')
    fig3.savefig(
        os.path.join(save_dir, save_file_base + '_swarm.pdf'),
        bbox_inches='tight')

    # Part 2
    # plot sorted per "cell" varienace explained (approximate, this is by
    # unique max_ve not cells per se)
    # set up saving paths/dir
    save_dir = os.path.join(save_dir, 'variance explained per cell')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_pairday_var_expl_' + trace_type

    for d in np.unique(df['day']):
        sliced_df = df.loc[(df['day'] == d), :]

        # make a rainbow colormap, HUSL space but does not circle back on itself
        cmap = sns.color_palette(
            'hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
        cmap = cmap[0:np.unique(df['rank'])[-1]]

        fig0 = plt.figure(figsize=(20, 6))
        ax0 = sns.swarmplot(
            x=sliced_df['max_ve'], y=sliced_df['variance_explained'],
            hue=sliced_df['rank'], palette=cmap)
        lg = ax0.legend(
            bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax0.set_xlabel('cell count')
        x_lim = ax0.get_xlim()
        ticks = ax0.get_xticks()
        new_ticks = [t for t in ticks[10::10]]
        ax0.set_xticks(new_ticks)
        ax0.set_xticklabels(np.arange(10, len(ticks), 10))
        ax0.set_title(mouse + ', Variance explained per cell, day ' + str(d))

        fig0.savefig(os.path.join(save_dir, save_file_base + '_day_' + str(d)
                                  + '.png'), bbox_inches='tight')
        plt.close()


"""
----------------------------- SINGLE DAY PLOTS -----------------------------
"""


def singleday_qc(
        mouse,
        trace_type='zscore_day',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot similarity and error plots for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved

    Returns:
    --------
    Saves figures to .../analysis folder  .../qc
    """

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'green',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'blue',
                'alpha': 0.5,
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'alpha': 0.5,
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'red',
                'alpha': 0.5,
            },
        },
    }

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for day1 in days:

        # load dir
        load_dir = paths.tca_path(mouse, 'pair', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                   + '_single_decomp_' + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save dir
        save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        error_path = os.path.join(save_dir, str(day1.mouse) + '_' + str(day1.date)
                                  + '_objective.pdf')
        sim_path = os.path.join(save_dir, str(day1.mouse) + '_' + str(day1.date)
                                + '_similarity.pdf')

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # plot error and similarity plots across rank number
        plt.figure()
        for m in ensemble:
            tt.plot_objective(ensemble[m], **plot_options[m])  # ax=ax[0])
        plt.legend()
        plt.title('Objective Function')
        plt.savefig(error_path)
        if verbose:
            plt.show()
        plt.clf()

        for m in ensemble:
            tt.plot_similarity(ensemble[m], **plot_options[m])  # ax=ax[1])
        plt.legend()
        plt.title('Iteration Similarity')
        plt.savefig(sim_path)
        if verbose:
            plt.show()
        plt.close()


def singleday_factors(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot TCA factors for all days and ranks/components for
    TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors
    """

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'red',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
    }

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for day1 in days:

        # load dir
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                   + '_single_decomp_' + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save dir
        save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'factors')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        date_dir = os.path.join(save_dir, str(day1.date) + ' ' + method)
        if not os.path.isdir(date_dir): os.mkdir(date_dir)

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # sort neuron factors by component they belong to most
        sort_ensemble, my_sorts = tca._sortfactors(ensemble[method])

        for r in sort_ensemble.results:

            fig = tt.plot_factors(sort_ensemble.results[r][0].factors, plots=['bar', 'line', 'scatter'],
                                  axes=None,
                                  scatter_kw=plot_options[method]['scatter_kw'],
                                  line_kw=plot_options[method]['line_kw'],
                                  bar_kw=plot_options[method]['bar_kw'])

            ax = fig[0].axes
            ax[0].set_title('Neuron factors')
            ax[1].set_title('Temporal factors')
            ax[2].set_title('Trial factors')

            count = 1
            for k in range(0, len(ax)):
                if np.mod(k + 1, 3) == 1:
                    ax[k].set_ylabel('Component #' + str(count), rotation=0,
                                     labelpad=45, verticalalignment='center', fontstyle='oblique')
                    count = count + 1

            # Show plots.
            plt.savefig(os.path.join(date_dir, 'rank_' + str(int(r)) + '.png'), bbox_inches='tight')
            if verbose:
                plt.show()
            plt.close()


def singleday_factors_annotated(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        extra_col=4,
        alpha=0.6,
        plot_running=True,
        filetype='pdf',
        scale_y=False,
        verbose=False):
    """
    Plot TCA factors with trial metadata annotations for all days
    and ranks/components for TCA decomposition ensembles.

    Parameters:
    -----------
    mouse : str
        Mouse name.
    trace_type : str
        dff, zscore, zscore_iti, zscore_day, deconvolved
    method : str
        TCA fit method from tensortools
    cs : str
        Cs stimuli to include, plus/minus/neutral, 0/135/270, etc. '' empty
        includes all stimuli
    warp : bool
        Use traces with time-warped outcome.
    extra_col : int
        Number of columns to add to the original three factor columns
    alpha : float
        Value between 0 and 1 for transparency of markers
    plot_running : bool
        Include trace of scaled (to plot max) average running speed during trial
    verbose : bool
        Show plots as they are made.

    Returns:
    --------
    Saves figures to .../analysis folder  .../factors annotated
    """

    # plotting options for the unconstrained and nonnegative models.
    plot_options = {
        'cp_als': {
            'line_kw': {
                'color': 'red',
                'label': 'cp_als',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_hals': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_hals',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
        'ncp_bcd': {
            'line_kw': {
                'color': 'red',
                'label': 'ncp_bcd',
            },
            'scatter_kw': {
                'color': 'green',
                'alpha': 0.5,
            },
            'bar_kw': {
                'color': 'blue',
                'alpha': 0.5,
            },
        },
    }

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    for day1 in days:

        # load dir
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                   + '_single_decomp_' + str(trace_type) + '.npy')
        meta_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                 + '_df_single_meta.pkl')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(meta_path): continue

        # save dir
        save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
        if scale_y:
            save_tag = ' scaled-y'
        else:
            save_tag = ''
        save_dir = os.path.join(save_dir, 'factors annotated' + save_tag)
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        date_dir = os.path.join(save_dir, str(day1.date) + ' ' + method)
        if not os.path.isdir(date_dir): os.mkdir(date_dir)

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        meta = pd.read_pickle(meta_path)
        orientation = meta['orientation']
        trial_num = np.arange(0, len(orientation))
        condition = meta['condition']
        trialerror = meta['trialerror']
        hunger = deepcopy(meta['hunger'])
        speed = meta['speed']
        dates = meta.reset_index()['date']
        learning_state = meta['learning_state']

        # calculate change indices for days and reversal/learning
        udays = {d: c for c, d in enumerate(np.unique(dates))}
        ndays = np.diff([udays[i] for i in dates])
        day_x = np.where(ndays)[0] + 0.5
        ustate = {d: c for c, d in enumerate(np.unique(learning_state))}
        nstate = np.diff([ustate[i] for i in learning_state])
        lstate_x = np.where(nstate)[0] + 0.5

        # merge hunger and tag info for plotting hunger
        tags = meta['tag']
        hunger[tags == 'disengaged'] = 'disengaged'

        # sort neuron factors by component they belong to most
        sort_ensemble, my_sorts = tca._sortfactors(ensemble[method])

        for r in sort_ensemble.results:

            U = sort_ensemble.results[r][0].factors

            fig, axes = plt.subplots(U.rank, U.ndim + extra_col, figsize=(9 + extra_col, U.rank))
            figt = tt.plot_factors(U, plots=['bar', 'line', 'scatter'],
                                   axes=None,
                                   fig=fig,
                                   scatter_kw=plot_options[method]['scatter_kw'],
                                   line_kw=plot_options[method]['line_kw'],
                                   bar_kw=plot_options[method]['bar_kw'])
            ax = figt[0].axes
            ax[0].set_title('Neuron factors')
            ax[1].set_title('Temporal factors')
            ax[2].set_title('Trial factors')

            # add title to whole figure
            ax[0].text(-1.2, 4, '\n' + mouse + ': \n\nrank: ' + str(int(r))
                       + '\nmethod: ' + method + ' \ndate: '
                       + str(day1.date),
                       fontsize=12, transform=ax[0].transAxes,
                       color='#969696')

            # reshape for easier indexing
            ax = np.array(ax).reshape((U.rank, -1))

            # rescale the y-axis for trials
            if scale_y:
                for i in range(U.rank):
                    y_lim = np.array(ax[i, 2].get_ylim()) * 0.8
                    y_ticks = ax[i, 2].get_yticks()
                    y_ticks[-1] = y_lim[-1]
                    y_ticks = np.round(y_ticks, 2)
                    # y_tickl = [str(y) for y in y_ticks]
                    ax[i, 2].set_ylim(y_lim)
                    ax[i, 2].set_yticks(y_ticks)
                    ax[i, 2].set_yticklabels(y_ticks)

            # add a line for stim onset and offset
            # NOTE: assumes downsample, 1 sec before onset, 3 sec stim
            for i in range(U.rank):
                y_lim = ax[i, 1].get_ylim()
                ons = 15.5 * 1
                offs = ons + 15.5 * 3
                ax[i, 1].plot([ons, ons], y_lim, ':k')
                ax[i, 1].plot([offs, offs], y_lim, ':k')

            for col in range(3, 3 + extra_col):
                for i in range(U.rank):

                    # get axis values
                    y_lim = ax[i, 2].get_ylim()
                    x_lim = ax[i, 2].get_xlim()
                    y_ticks = ax[i, 2].get_yticks()
                    y_tickl = ax[i, 2].get_yticklabels()
                    x_ticks = ax[i, 2].get_xticks()
                    x_tickl = ax[i, 2].get_xticklabels()

                    # running
                    if plot_running:
                        scale_by = np.nanmax(speed) / y_lim[1]
                        if not np.isnan(scale_by):
                            ax[i, col].plot(np.array(speed.tolist()) / scale_by, color=[1, 0.1, 0.6, 0.2])
                            # , label='speed')

                    # Orientation - main variable to plot
                    if col == 3:
                        ori_vals = [0, 135, 270]
                        color_vals = [[0.28, 0.68, 0.93, alpha], [0.84, 0.12, 0.13, alpha],
                                      [0.46, 0.85, 0.47, alpha]]
                        for k in range(0, 3):
                            ax[i, col].plot(trial_num[orientation == ori_vals[k]],
                                            U.factors[2][orientation == ori_vals[k], i], 'o',
                                            label=str(ori_vals[k]), color=color_vals[k], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Orientation')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)
                    elif col == 4:
                        cs_vals = ['plus', 'minus', 'neutral']
                        cs_labels = ['plus', 'minus', 'neutral']
                        color_vals = [[0.46, 0.85, 0.47, alpha], [0.84, 0.12, 0.13, alpha],
                                      [0.28, 0.68, 0.93, alpha]]
                        col = 4
                        for k in range(0, 3):
                            ax[i, col].plot(trial_num[condition == cs_vals[k]],
                                            U.factors[2][condition == cs_vals[k], i], 'o',
                                            label=str(cs_labels[k]), color=color_vals[k], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Condition')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)
                    elif col == 5:
                        trialerror_vals = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
                        trialerror_labels = ['hit',
                                             'miss',
                                             'neutral correct reject',
                                             'neutral false alarm',
                                             'minus correct reject',
                                             'minus false alarm',
                                             'blank correct reject',
                                             'blank false alarm',
                                             'pav early licking',
                                             'pav late licking', ]
                        for k in trialerror_vals:
                            ax[i, col].plot(trial_num[trialerror == trialerror_vals[k]],
                                            U.factors[2][trialerror == trialerror_vals[k], i], 'o',
                                            label=str(trialerror_labels[k]), alpha=0.8, markersize=2)
                        if i == 0:
                            ax[i, col].set_title('Trialerror')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)

                    elif col == 6:
                        h_vals = ['hungry', 'sated', 'disengaged']
                        h_labels = ['hungry', 'sated', 'disengaged']
                        color_vals = [[1, 0.6, 0.3, alpha], [0.7, 0.9, 0.4, alpha],
                                      [0.6, 0.5, 0.6, alpha], [0.0, 0.9, 0.4, alpha]]
                        for k in range(0, 3):
                            ax[i, col].plot(trial_num[hunger == h_vals[k]],
                                            U.factors[2][hunger == h_vals[k], i], 'o',
                                            label=str(h_labels[k]), color=color_vals[k], markersize=2)
                        if i == 0:
                            ax[i, col].set_title('State')
                            ax[i, col].legend(bbox_to_anchor=(0.5, 1.02), loc='lower center',
                                              borderaxespad=2.5)

                    # plot days, reversal, or learning lines if there are any
                    if col >= 2:
                        y_lim = ax[i, col].get_ylim()
                        if len(day_x) > 0:
                            for k in day_x:
                                ax[i, col].plot(
                                    [k, k], y_lim, color='#969696', linewidth=1)
                        if len(lstate_x) > 0:
                            ls_vals = ['naive', 'learning', 'reversal1']
                            ls_colors = ['#66bd63', '#d73027', '#a50026']
                            for k in lstate_x:
                                ls = learning_state[int(k - 0.5)]
                                ax[i, col].plot(
                                    [k, k], y_lim, color=ls_colors[ls_vals.index(ls)],
                                    linewidth=1.5)

                    # set axes labels
                    ax[i, col].set_yticks(y_ticks)
                    ax[i, col].set_yticklabels(y_tickl)
                    ax[i, col].set_ylim(y_lim)
                    ax[i, col].set_xlim(x_lim)

                    # format axes
                    ax[i, col].locator_params(nbins=4)
                    ax[i, col].spines['top'].set_visible(False)
                    ax[i, col].spines['right'].set_visible(False)
                    ax[i, col].xaxis.set_tick_params(direction='out')
                    ax[i, col].yaxis.set_tick_params(direction='out')
                    ax[i, col].yaxis.set_ticks_position('left')
                    ax[i, col].xaxis.set_ticks_position('bottom')

                    # remove xticks on all but bottom row
                    if i + 1 != U.rank:
                        plt.setp(ax[i, col].get_xticklabels(), visible=False)

                    if col == 3:
                        ax[i, 0].set_ylabel('Component #' + str(i + 1), rotation=0,
                                            labelpad=45, verticalalignment='center',
                                            fontstyle='oblique')

            if filetype.lower() == 'pdf':
                suffix = '.pdf'
            elif filetype.lower() == 'eps':
                suffix = '.eps'
            else:
                suffix = '.png'
            plt.savefig(os.path.join(date_dir, 'rank_' + str(int(r)) + suffix),
                        bbox_inches='tight')
            if verbose:
                plt.show()
            plt.close()


def singleday_qc_summary(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot similarity and objective (measure of reconstruction error) plots
    across all days for TCA decomposition ensembles.

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

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    cmap = sns.color_palette('hls', n_colors=len(days))

    # create figure and axes
    buffer = 5
    right_pad = 5

    fig0 = plt.figure(figsize=(10, 8))
    gs0 = GridSpec(100, 100, figure=fig0, left=0.05, right=.95, top=.95, bottom=0.05)
    ax0 = fig0.add_subplot(gs0[10:90 - buffer, :90 - right_pad])

    fig1 = plt.figure(figsize=(10, 8))
    gs1 = GridSpec(100, 100, figure=fig1, left=0.05, right=.95, top=.95, bottom=0.05)
    ax1 = fig1.add_subplot(gs1[10:90 - buffer, :90 - right_pad])

    # plt.figure()
    for c, day1 in enumerate(days, 0):

        # load paths
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_' + str(day1.date)
                                   + '_single_decomp_' + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue

        # save paths
        save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        error_path = os.path.join(save_dir, str(day1.mouse) + '_summary_objective.pdf')
        sim_path = os.path.join(save_dir, str(day1.mouse) + '_summary_similarity.pdf')

        # plotting options for the unconstrained and nonnegative models.
        plot_options = {
            'cp_als': {
                'line_kw': {
                    'color': cmap[c],
                    'label': 'single ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
            'ncp_hals': {
                'line_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                    'label': 'single ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
            'ncp_bcd': {
                'line_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                    'label': 'single ' + str(c),
                },
                'scatter_kw': {
                    'color': cmap[c],
                    'alpha': 0.5,
                },
            },
        }

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()

        # plot error and similarity plots across rank number
        tt.plot_objective(ensemble[method], **plot_options[method], ax=ax0)
        tt.plot_similarity(ensemble[method], **plot_options[method], ax=ax1)

    # add legend, title
    ax0.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
    ax0.set_title('Objective Function: ' + str(method) + ', ' + mouse)
    ax1.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
    ax1.set_title('Iteration Similarity: ' + str(method) + ', ' + mouse)

    # save figs
    fig0.savefig(error_path, bbox_inches='tight')
    fig1.savefig(sim_path, bbox_inches='tight')

    if verbose:
        fig0.show()
        fig1.show()


def singleday_varex_summary(
        mouse,
        trace_type='zscore_day',
        method='ncp_bcd',
        cs='',
        warp=False,
        word=None,
        verbose=False):
    """
    Plot reconstruction error as variance explained across all days for
    TCA decomposition ensembles.

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

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    cmap = sns.color_palette(sns.cubehelix_palette(len(days)))

    # create figure and axes
    buffer = 5
    right_pad = 5
    fig = plt.figure(figsize=(10, 8))
    gs = GridSpec(100, 100, figure=fig, left=0.05, right=.95, top=.95, bottom=0.05)
    ax = fig.add_subplot(gs[10:90 - buffer, :90 - right_pad])

    for c, day1 in enumerate(days, 0):

        # load dirs
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_single_decomp_'
                                   + str(trace_type) + '.npy')
        input_tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                         + str(day1.date) + '_single_tensor_'
                                         + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(input_tensor_path): continue

        # save dirs
        save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
        save_dir = os.path.join(save_dir, 'qc')
        if not os.path.isdir(save_dir): os.mkdir(save_dir)
        var_path = os.path.join(save_dir, str(day1.mouse) + '_summary_variance_cubehelix.pdf')

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        V = ensemble[method]
        X = np.load(input_tensor_path)

        # get reconstruction error as variance explained
        var, var_s, x, x_s = [], [], [], []
        for r in V.results:
            bU = V.results[r][0].factors.full()
            var.append((np.var(X) - np.var(X - bU)) / np.var(X))
            x.append(r)
            for it in range(0, len(V.results[r])):
                U = V.results[r][it].factors.full()
                var_s.extend([(np.var(X) - np.var(X - U)) / np.var(X)])
                x_s.extend([r])

        # mean response of neuron across trials
        mU = np.mean(X, axis=2, keepdims=True) * np.ones((1, 1, np.shape(X)[2]))
        var_mean = (np.var(X) - np.var(X - mU)) / np.var(X)

        # smoothed response of neuron across time
        smU = np.convolve(X.reshape((X.size)), np.ones(5, dtype=np.float64) / 5, 'same').reshape(np.shape(X))
        var_smooth = (np.var(X) - np.var(X - smU)) / np.var(X)

        # plot
        R = np.max([r for r in V.results.keys()])
        ax.scatter(x_s, var_s, color=cmap[c], alpha=0.5)
        ax.scatter([R + 2], var_mean, color=cmap[c], alpha=0.5)
        ax.scatter([R + 4], var_smooth, color=cmap[c], alpha=0.5)
        ax.plot(x, var, label=('single ' + str(c)), color=cmap[c])
        ax.plot([R + 1.5, R + 2.5], [var_mean, var_mean], color=cmap[c])
        ax.plot([R + 3.5, R + 4.5], [var_smooth, var_smooth], color=cmap[c])

    # add labels/titles
    x_labels = [str(R) for R in V.results]
    x_labels.extend(['', 'mean\n cell\n response', '', 'smooth\n response\n (0.3s)'])
    ax.set_xticks(range(1, len(V.results) + 5))
    ax.set_xticklabels(x_labels)
    ax.set_xlabel('model rank')
    ax.set_ylabel('fractional variance explained')
    ax.set_title('Variance Explained: ' + str(method) + ', ' + mouse)
    ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)

    fig.savefig(var_path, bbox_inches='tight')


def singleday_varex_percell(
        mouse,
        method='ncp_bcd',
        trace_type='zscore_day',
        cs='',
        warp=False,
        word=None,
        ve_min=0.05,
        filetype='pdf'):
    """
    Plot TCA reconstruction error as variance explained per cell
    for TCA decomposition. Create folder of variance explained per cell
    swarm plots. Calculate summary plots of 'fraction of maximum variance
    explained' per cell by rank for all cells given a certain (ve_min)
    threshold for maximum variance explained.

    Parameters:
    -----------
    mouse : str; mouse name
    trace_type : str; dff, zscore, deconvolved
    method : str; TCA fit method from tensortools
    ve_min: float; minimum variance explained for best rank per cell
                   to be included in summary of fraction of maximum variance
                   explained

    Returns:
    --------
    Saves figures to .../analysis folder/ .../qc
                                             .../variance explained per cell

    """

    pars = {'trace_type': trace_type, 'cs': cs, 'warp': warp}

    days = flow.DateSorter.frommeta(
        mice=[mouse], tags=None, exclude_tags=['bad'])

    # create folder structure if needed
    cs_tag = '' if len(cs) == 0 else ' ' + str(cs)
    warp_tag = '' if warp is False else ' warp'
    folder_name = 'tensors single ' + str(trace_type) + cs_tag + warp_tag

    ve, ve_max, ve_frac, rank_num, day_num, cell_num = [], [], [], [], [], []
    for c, day1 in enumerate(days, 0):

        # get dirs for loading
        load_dir = paths.tca_path(mouse, 'single', pars=pars, word=word)
        if not os.path.isdir(load_dir): os.mkdir(load_dir)
        tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                   + str(day1.date) + '_single_decomp_'
                                   + str(trace_type) + '.npy')
        input_tensor_path = os.path.join(load_dir, str(day1.mouse) + '_'
                                         + str(day1.date) + '_single_tensor_'
                                         + str(trace_type) + '.npy')
        if not os.path.isfile(tensor_path): continue
        if not os.path.isfile(input_tensor_path): continue

        # load your data
        ensemble = np.load(tensor_path)
        ensemble = ensemble.item()
        V = ensemble[method]
        X = np.load(input_tensor_path)

        # get reconstruction error as variance explained per cell
        for cell in range(0, np.shape(X)[0]):
            rank_ve_vec = []
            rank_vec = []
            for r in V.results:
                U = V.results[r][0].factors.full()
                Usub = X - U
                rank_ve = (np.var(X[cell, :, :]) - np.var(Usub[cell, :, :])) / np.var(X[cell, :, :])
                rank_ve_vec.append(rank_ve)
                rank_vec.append(r)
            max_ve = np.max(rank_ve_vec)
            ve.extend(rank_ve_vec)
            ve_max.extend([max_ve for s in rank_ve_vec])
            ve_frac.extend(rank_ve_vec / max_ve)
            rank_num.extend(rank_vec)
            day_num.extend([c + 1 for s in rank_ve_vec])
            cell_num.extend([cell for s in rank_ve_vec])

    # build pd dataframe of all variance measures
    index = pd.MultiIndex.from_arrays([
        day_num,
        rank_num,
        ve,
        ve_max,
        ve_frac,
        cell_num,
    ],
        names=['day', 'rank', 'variance_explained', 'max_ve', 'frac_ve', 'cell'])
    df = pd.DataFrame(index=index)
    df = df.reset_index()

    # make a rainbow colormap, HUSL space but does not circle back on itself
    cmap = sns.color_palette('hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
    cmap = cmap[0:np.unique(df['rank'])[-1]]

    # Part 1
    # slice df, only look at cells with a max variance >5%
    sliced_df2 = df.loc[(df['day']) & (df['max_ve'] >= ve_min), :]

    # CDF plot
    fig1 = plt.figure(figsize=(15, 9))
    for i in np.unique(sliced_df2['rank']):
        input_ve = sliced_df2.loc[(sliced_df2['rank'] == i), 'frac_ve']
        ax = sns.distplot(input_ve, kde_kws={'cumulative': True, 'lw': 2, 'color': cmap[i - 1], 'label': str(i)},
                          hist=False)
        lg = ax.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax.set_title(mouse + ', Fraction of maximum variance explained per cell, CDF')
        ax.set_xlabel('Fraction of maximum variance explained')

    # swarm plot
    fig2 = plt.figure(figsize=(18, 6))
    ax2 = sns.violinplot(x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=3, alpha=1, inner=None, palette=cmap)
    ax2.set_title(mouse + ', Fraction of maximum variance explained per cell, violin')
    ax2.set_ylabel('Fraction of maximum variance explained')

    # swarm plot
    fig3 = plt.figure(figsize=(18, 6))
    ax3 = sns.swarmplot(x=sliced_df2['rank'], y=sliced_df2['frac_ve'], size=2, alpha=1, palette=cmap)
    ax3.set_title(mouse + ', Fraction of maximum variance explained per cell, swarm')
    ax3.set_ylabel('Fraction of maximum variance explained')

    # set up saving paths/dir
    save_dir = paths.tca_plots(mouse, 'single', pars=pars, word=word)
    save_dir = os.path.join(save_dir, 'qc')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_singleday_frac_max_var_expl_' + trace_type

    # save
    if filetype.lower() == 'pdf':
        suffix = '.pdf'
    elif filetype.lower() == 'eps':
        suffix = '.eps'
    else:
        suffix = '.png'
    fig1.savefig(os.path.join(save_dir, save_file_base + '_CDF' + suffix), bbox_inches='tight')
    fig2.savefig(os.path.join(save_dir, save_file_base + '_violin' + suffix), bbox_inches='tight')
    fig3.savefig(os.path.join(save_dir, save_file_base + '_swarm.png'), bbox_inches='tight')

    # Part 2
    # plot sorted per "cell" variance explained (approximate, this is by unique
    # max_ve not cells per se)
    # set up saving paths/dir
    save_dir = os.path.join(save_dir, 'variance explained per cell')
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    save_file_base = mouse + '_singleday_var_expl_' + trace_type

    for d in np.unique(df['day']):
        sliced_df = df.loc[(df['day'] == d), :]

        # make a rainbow colormap, HUSL space but does not circle back on itself
        cmap = sns.color_palette('hls', int(np.ceil(1.5 * np.unique(df['rank'])[-1])))
        cmap = cmap[0:np.unique(df['rank'])[-1]]

        fig0 = plt.figure(figsize=(20, 6))
        ax0 = sns.swarmplot(x=sliced_df['max_ve'], y=sliced_df['variance_explained'],
                            hue=sliced_df['rank'], palette=cmap)
        lg = ax0.legend(bbox_to_anchor=(1.03, 1), loc='upper left', borderaxespad=0.)
        lg.set_title('rank')
        ax0.set_xlabel('cell count')
        x_lim = ax0.get_xlim()
        ticks = ax0.get_xticks()
        new_ticks = [t for t in ticks[10::10]]
        ax0.set_xticks(new_ticks)
        ax0.set_xticklabels(np.arange(10, len(ticks), 10))
        ax0.set_title(mouse + ', Variance explained per cell, day ' + str(d))

        fig0.savefig(os.path.join(save_dir, save_file_base + '_day_' + str(d)
                                  + suffix), bbox_inches='tight')
        plt.close()
