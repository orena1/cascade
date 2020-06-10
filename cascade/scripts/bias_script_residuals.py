import cascade as cas
import seaborn as sns
import matplotlib.pyplot as plt
import os

# script to create simple bias plots for all mice
mice = cas.lookups.mice['all15']
words = ['bookmarks' if m in 'OA27' else 'horrible' for m in mice]
rank_num = 15

save_folder = cas.paths.save_dir_groupmouse(
        mice,
        'FC bias and mean across learning all mice',
        method='ncp_hals',
        nan_thresh=0.95,
        score_threshold=0.8,
        pars=None,  # should be able to leave as default
        words=words,
        rank_num=rank_num,
        grouping='group',
        group_pars={'group_by': 'all3'})

for mi, wi in zip(mice, words):

    model, ids, tensor, meta, bhv, sorts = cas.load.load_all_groupday(
        mouse=mi,
        trace_type='zscore_day',
        method='ncp_hals',
        cs='',
        warp=False,
        word=wi,
        rank=rank_num,
        group_by='all3',
        nan_thresh=0.95,
        score_threshold=0.8,
        full_output=False,
        unsorted=True,
        with_model=True,
        verbose=False)

    bias_df = cas.bias.get_bias_from_ablated_data_simple(meta, tensor, model, model_rank=rank_num,
                                                  save_folder=save_folder, staging='parsed_10stage')

    plt.figure()
    sns.barplot(data=bias_df, x='learning stage', y='mean response', hue='cue', palette=cas.lookups.color_dict)
    sns.despine()
    plt.xticks(rotation=45, ha='right')
    plt.xlabel('learning stage', size=14)
    plt.ylabel('mean cue response\n(normalized)', size=14)
    plt.title(f'{mi} residuals: mean cue response', size=16)
    plt.legend(bbox_to_anchor=(1.05, 1))
    plt.savefig(os.path.join(save_folder, f'{mi}_rank_{rank_num}_residuals_mean_cue_response.pdf'), bbox_inches='tight')

    plt.figure()
    sns.barplot(data=bias_df, x='learning stage', y='mean response raw', hue='cue', palette=cas.lookups.color_dict)
    sns.despine()
    plt.xticks(rotation=45, ha='right')
    plt.xlabel('learning stage', size=14)
    plt.ylabel('mean cue response\n(zscore \u0394F/F\u2080)', size=14)
    plt.title(f'{mi} residuals: mean cue response raw', size=16)
    plt.legend(bbox_to_anchor=(1.05, 1))
    plt.savefig(os.path.join(save_folder, f'{mi}_rank_{rank_num}_residuals_mean_cue_response_raw.pdf'), bbox_inches='tight')

    plt.figure()
    sns.barplot(data=bias_df.loc[bias_df['cue'].isin(['plus']), :], x='learning stage', y='bias', hue='cue', palette=cas.lookups.color_dict)
    sns.despine()
    plt.xticks(rotation=45, ha='right')
    plt.xlabel('learning stage', size=14)
    plt.ylabel('Food cue bias index\nFC / (FC+QC+NC)', size=14)
    plt.title(f'{mi} residuals: Food cue bias', size=16)
    plt.legend(bbox_to_anchor=(1.05, 1))
    plt.savefig(os.path.join(save_folder, f'{mi}_rank_{rank_num}_residuals_FC_bias.pdf'), bbox_inches='tight')
