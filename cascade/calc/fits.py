"""Calculations to be saved to mongoDB database"""
from pool.database import memoize
import numpy as np
import scipy as sci
import pandas as pd
import os
import flow
from .. import load
from copy import deepcopy
from scipy import linalg
from tensortools.operations import unfold, khatri_rao
from tensortools.tensors import KTensor
from tensortools.optimize import FitResult, optim_utils
try:
    # this only works for python 36
    from tensortools._hals_update import _hals_update
except ModuleNotFoundError:
    print('_hals_update for python 3.6 not loaded in cascade.calc.fits')


@memoize(across='mouse', updated=190709, returns='other', large_output=False)
def fit_disengaged_sated(
        mouse,
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=None,
        random_state=None,
        init='rand',
        rank=18,
        verbose=False):

    """
    Use an existing TCA decomposition to fit trials from disengaged and sated
    days. Compare ratio of trials disengaged vs engaged using a ramp index.

    dis_index:
        log2(mean(disengaged trials)/mean(engaged trials))
    """

    # load full-size TCA results
    mouse = mouse.mouse
    load_kwargs = {'mouse': mouse,
                   'method': method,
                   'cs': cs,
                   'warp': warp,
                   'word': word,
                   'group_by': group_by,
                   'nan_thresh': nan_thresh,
                   'score_threshold': score_threshold,
                   'rank': rank}
    ensemble, ids2, clus = load.groupday_tca_model(**load_kwargs)

    # get all days with disengaged or sated trials
    dis_dates = flow.DateSorter.frommeta(
        mice=[mouse], tags='disengaged', exclude_tags=['bad'])
    sated_dates = flow.DateSorter.frommeta(
        mice=[mouse], tags='sated', exclude_tags=['bad'])
    all_dates = []
    day_type = []
    for day in dis_dates:
        all_dates.append(day)
        day_type.append('disengaged')
    for day in sated_dates:
        all_dates.append(day)
        day_type.append('sated')

    # preallocate
    fits_vec = []
    ratios_vec = []
    comp_vec = []
    day_vec = []
    day_type_vec = []

    for c, day in enumerate(all_dates):

        # load single day tensor with dis trials
        X, meta, ids = load.singleday_tensor(mouse, day.date)

        # only include matched cells, no empties
        good_ids = ids[np.isin(ids, ids2)]
        X_indexer = np.isin(ids, good_ids)
        X = X[X_indexer, :, :]

        # only keep indices that exist in the single day tensor
        A_indexer = np.isin(ids2, good_ids)
        A = ensemble.results[rank][0].factors[0][A_indexer, :]
        B = ensemble.results[rank][0].factors[1]
        C = ensemble.results[rank][0].factors[2]

        # make sure X is in the order of the sorted TCA results
        X_sorter = [np.where(ids[X_indexer] == s)[0][0] for s in ids2[A_indexer]]
        X = X[X_sorter, :, :]

        # create a mask for TCA
        # (not actually used here since there are no empties)
        mask = np.ones(np.shape(X)) == 1

        # Check inputs.
        optim_utils._check_cpd_inputs(X, rank)

        # Initialize problem.
        U, _ = optim_utils._get_initial_ktensor(
            init, X, rank, random_state, scale_norm=False)
        result = FitResult(
            U, 'NCP_HALS', tol=0.000001, max_iter=500, verbose=True)

        # Store problem dimensions.
        normX = linalg.norm(X[mask].ravel())

        # fit a single iteration of HALS for the trial dimension
        for i in range(1):

            # First, HALS update. Fit only trials (dim = 2)
            n = 2

            # add in known dimensions to Ktensor
            U[0] = np.ascontiguousarray(A)
            U[1] = np.ascontiguousarray(B)

            # Select all components, but U_n
            components = [U[j] for j in range(X.ndim) if j != n]

            # i) compute the N-1 gram matrices
            grams = sci.multiply.reduce([arr.T.dot(arr) for arr in components])

            # ii)  Compute Khatri-Rao product
            kr = khatri_rao(components)
            p = unfold(X, n).dot(kr)

            # iii) Update component U_n
            _hals_update(U[n], grams, p)

            # Then, update masked elements.
            pred = U.full()
            X[~mask] = pred[~mask]

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # Update the optimization result, checks for convergence.
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # Compute objective function
            # grams *= U[X.ndim - 1].T.dot(U[X.ndim - 1])
            # obj = np.sqrt( (sci.sum(grams) - 2 * sci.sum(U[X.ndim - 1] * p)
            # +normX**2)) / normX
            resid = X - pred
            result.update(linalg.norm(resid.ravel()) / normX)

        # calculate ramp index for each component
        test = deepcopy(U[2])
        # dis_ri = []
        # dis_rat = []
    #     test[test == 0] = np.nan
        if day_type[c] == 'disengaged':
            notdise = ~meta['tag'].isin(['disengaged']).values
            dise = meta['tag'].isin(['disengaged']).values
        elif day_type[c] == 'sated':
            notdise = ~meta['hunger'].isin(['sated']).values
            dise = meta['hunger'].isin(['sated']).values
        for i in range(rank):
            ri = np.log2(np.nanmean(test[dise, i])/np.nanmean(test[notdise, i]))
            # ratio = np.nanmean(test[dise, i])/np.nanmean(test[:, i])
            # dis_ri.append(ri)
            # dis_rat.append(ratio)
            fits_vec.append(ri)
            comp_vec.append(i+1)
            day_vec.append(day.date)
            day_type_vec.append(day_type[c])

        # save ramp indices for each day
        # fits_vec.append(dis_ri)
        # ratios_vec.append(dis_rat)

    # make dataframe of data
    # create your index out of relevant variables
    index = pd.MultiIndex.from_arrays(
        [[mouse] * len(fits_vec)],
        names=['mouse'])

    data = {'rank': [rank] * len(fits_vec),
            'date': day_vec,
            'component': comp_vec,
            'day_type': day_type_vec,
            'dis_index': fits_vec}

    dfdis = pd.DataFrame(data, index=index)

    return dfdis


@memoize(across='mouse', updated=190710, returns='other', large_output=False)
def fit_disengaged_sated_mean_per_comp(
        mouse,
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        word=None,
        group_by='all',
        nan_thresh=0.85,
        score_threshold=None,
        random_state=None,
        init='rand',
        rank=18,
        verbose=False):

    """
    Use an existing TCA decomposition to fit trials from disengaged and sated
    days. Compare ratio of trials disengaged vs engaged using a ramp index.

    dis_index:
        log2(mean(disengaged trials)/mean(engaged trials))
    """

    # load full-size TCA results
    mouse = mouse.mouse
    load_kwargs = {'mouse': mouse,
                   'method': method,
                   'cs': cs,
                   'warp': warp,
                   'word': word,
                   'group_by': group_by,
                   'nan_thresh': nan_thresh,
                   'score_threshold': score_threshold,
                   'rank': rank}
    ensemble, ids2, clus = load.groupday_tca_model(**load_kwargs)

    # get all days with disengaged or sated trials
    dis_dates = flow.DateSorter.frommeta(
        mice=[mouse], tags='disengaged', exclude_tags=['bad'])
    sated_dates = flow.DateSorter.frommeta(
        mice=[mouse], tags='sated', exclude_tags=['bad'])
    all_dates = []
    day_type = []
    for day in dis_dates:
        all_dates.append(day)
        day_type.append('disengaged')
    for day in sated_dates:
        all_dates.append(day)
        day_type.append('sated')

    # preallocate
    fits = {}

    for c, day in enumerate(all_dates):

        # load single day tensor with dis trials
        X, meta, ids = load.singleday_tensor(mouse, day.date)

        # only include matched cells, no empties
        good_ids = ids[np.isin(ids, ids2)]
        X_indexer = np.isin(ids, good_ids)
        X = X[X_indexer, :, :]

        # only keep indices that exist in the single day tensor
        A_indexer = np.isin(ids2, good_ids)
        A = ensemble.results[rank][0].factors[0][A_indexer, :]
        B = ensemble.results[rank][0].factors[1]
        C = ensemble.results[rank][0].factors[2]

        # make sure X is in the order of the sorted TCA results
        X_sorter = [np.where(ids[X_indexer] == s)[0][0] for s in ids2[A_indexer]]
        X = X[X_sorter, :, :]

        # create a mask for TCA
        # (not actually used here since there are no empties)
        mask = np.ones(np.shape(X)) == 1

        # Check inputs.
        optim_utils._check_cpd_inputs(X, rank)

        # Initialize problem.
        U, _ = optim_utils._get_initial_ktensor(
            init, X, rank, random_state, scale_norm=False)
        result = FitResult(
            U, 'NCP_HALS', tol=0.000001, max_iter=500, verbose=True)

        # Store problem dimensions.
        normX = linalg.norm(X[mask].ravel())

        # fit a single iteration of HALS for the trial dimension
        for i in range(1):

            # First, HALS update. Fit only trials (dim = 2)
            n = 2

            # add in known dimensions to Ktensor
            U[0] = np.ascontiguousarray(A)
            U[1] = np.ascontiguousarray(B)

            # Select all components, but U_n
            components = [U[j] for j in range(X.ndim) if j != n]

            # i) compute the N-1 gram matrices
            grams = sci.multiply.reduce([arr.T.dot(arr) for arr in components])

            # ii)  Compute Khatri-Rao product
            kr = khatri_rao(components)
            p = unfold(X, n).dot(kr)

            # iii) Update component U_n
            _hals_update(U[n], grams, p)

            # Then, update masked elements.
            pred = U.full()
            X[~mask] = pred[~mask]

            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # Update the optimization result, checks for convergence.
            # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
            # Compute objective function
            # grams *= U[X.ndim - 1].T.dot(U[X.ndim - 1])
            # obj = np.sqrt( (sci.sum(grams) - 2 * sci.sum(U[X.ndim - 1] * p)
            # +normX**2)) / normX
            resid = X - pred
            result.update(linalg.norm(resid.ravel()) / normX)

        # calculate ramp index for each component
        test = deepcopy(U[2])
        dis_ri = []
        # dis_rat = []
    #     test[test == 0] = np.nan
        if day_type[c] == 'disengaged':
            notdise = ~meta['tag'].isin(['disengaged']).values
            dise = meta['tag'].isin(['disengaged']).values
        elif day_type[c] == 'sated':
            notdise = ~meta['hunger'].isin(['sated']).values
            dise = meta['hunger'].isin(['sated']).values
        for i in range(rank):
            ri = np.log2(np.nanmean(test[dise, i])/np.nanmean(test[notdise, i]))
            # ratio = np.nanmean(test[dise, i])/np.nanmean(test[:, i])
            dis_ri.append(ri)
            # dis_rat.append(ratio)

        # save ramp indices for each day
        fits[day.date] = dis_ri

    # Get mean disengagement index across days
    mat = np.zeros((len(fits.keys()), rank))
    for c, V in enumerate(fits.keys()):
        mat[c, :] = fits[V]
    # deal with divide by zeros etc
    mat[~np.isfinite(mat)] = np.nan
    # if a day is mostly nans, skip whole day
    nan_vec = np.sum(np.isnan(mat), axis=1)
    mean_fits = np.nanmean(mat[nan_vec <= rank/2, :], axis=0)

    # make dataframe of data
    # create your index out of relevant variables
    index = pd.MultiIndex.from_arrays(
        [[mouse] * len(mean_fits)],
        names=['mouse'])

    data = {'rank': [rank] * len(mean_fits),
            'component': np.arange(1, rank + 1, 1),
            'dis_index': mean_fits}

    dfdis = pd.DataFrame(data, index=index)

    return dfdis


def groupmouse_fit_disengaged_sated_mean_per_comp(
        mice=['OA27', 'OA26', 'OA67', 'VF226', 'CC175'],
        trace_type='zscore_day',
        method='mncp_hals',
        cs='',
        warp=False,
        words=['orlando', 'already', 'already', 'already', 'already'],
        group_by='all',
        nan_thresh=0.85,
        score_threshold=None,
        random_state=None,
        init='rand',
        rank=18,
        verbose=False):

    """
    Wrapper function for fit_disengaged_sated_mean_per_comp. Gets a dataframe
    of all mice.
    """

    mouse_list = []
    for m, w in zip(mice, words):
        mouse = flow.Mouse(mouse=m)
        mouse_list.append(
            fit_disengaged_sated_mean_per_comp(
                mouse, word=w, rank=rank, nan_thresh=nan_thresh,
                score_threshold=score_threshold,
                method=method, cs=cs, warp=warp, group_by=group_by,
                trace_type=trace_type, random_state=random_state, init=init,
                verbose=verbose))

    dfmouse = pd.concat(mouse_list, axis=0)

    return dfmouse
