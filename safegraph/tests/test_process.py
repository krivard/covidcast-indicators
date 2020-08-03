import pytest

from os import listdir
from os.path import join

import numpy as np
import pandas as pd
from delphi_safegraph.process import (
    construct_signals,
    aggregate,
    signal_name
)
from delphi_safegraph.run import SIGNALS
from delphi_utils import read_params
signal_names = SIGNALS


class TestProcess:
    def test_construct_signals_present(self):
        cbg_df = construct_signals(pd.read_csv('raw_data/sample_raw_data.csv'),
                                   signal_names)
        assert 'completely_home_prop' in set(cbg_df.columns)
        assert 'full_time_work_prop' in set(cbg_df.columns)
        assert 'part_time_work_prop' in set(cbg_df.columns)
        assert 'median_home_dwell_time' in set(cbg_df.columns)

    def test_construct_signals_proportions(self):
        cbg_df = construct_signals(pd.read_csv('raw_data/sample_raw_data.csv'),
                                   signal_names)
        assert np.all(cbg_df['completely_home_prop'].values <= 1)
        assert np.all(cbg_df['full_time_work_prop'].values <= 1)
        assert np.all(cbg_df['part_time_work_prop'].values <= 1)

    def test_aggregate_county(self):
        cbg_df = construct_signals(pd.read_csv('raw_data/sample_raw_data.csv'),
                                   signal_names)
        df = aggregate(cbg_df, signal_names, 'county')

        assert np.all(df[f'{signal_names[0]}_n'].values > 0)
        x = df[f'{signal_names[0]}_se'].values
        assert np.all(x[~np.isnan(x)] >= 0)

    def test_aggregate_state(self):
        cbg_df = construct_signals(pd.read_csv('raw_data/sample_raw_data.csv'),
                                   signal_names)
        df = aggregate(cbg_df, signal_names, 'state')

        assert np.all(df[f'{signal_names[0]}_n'].values > 0)
        x = df[f'{signal_names[0]}_se'].values
        assert np.all(x[~np.isnan(x)] >= 0)

    def test_signal_name(self):
        assert read_params()["wip_signal"] is not None, "supply value in params"
        assert type(read_params()["wip_signal"]) == list or type(read_params()["wip_signal"]) == bool, "Supply True|False|list()"
        signals = signal_name(signal_names, wip_signal=read_params()['wip_signal'],prefix='wip_')
        assert (len(signals) >= len(signal_names))



