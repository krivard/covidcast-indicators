"""Utility functions for validation."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import List
import pandas as pd

# Recognized geo types.
GEO_REGEX_DICT = {
    'county': r'^\d{5}$',
    'hrr': r'^\d{1,3}$',
    'hhs': r'^\d{1,2}$',
    'msa': r'^\d{5}$',
    'dma': r'^\d{3}$',
    'state': r'^[a-zA-Z]{2}$',
    'nation': r'^[a-zA-Z]{2}$'
}


@dataclass
class TimeWindow:
    """Object to store a window of time ending on `end_date` and lasting `span_length`."""

    end_date: date
    span_length: timedelta
    start_date: date = field(init=False)
    date_seq: List[date] = field(init=False)

    def __post_init__(self):
        """Derive the start date of this span."""
        self.start_date = self.end_date - self.span_length
        self.date_seq = [self.start_date + timedelta(days=x)
                         for x in range(self.span_length.days + 1)]

    @classmethod
    def from_params(cls, end_date_str: str, span_length_int: int):
        """Create a TimeWindow from param representations of its members."""
        span_length = timedelta(days=span_length_int)
        if end_date_str.startswith("today"):
            if end_date_str == "today":
                days_back = 0
            else:
                assert end_date_str.startswith("today-")
                days_back = int(end_date_str[6:])
            end_date = date.today() - timedelta(days=days_back)
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        return cls(end_date, span_length)


def relative_difference_by_min(x, y):
    """Calculate relative difference between two numbers."""
    return (x - y) / min(x, y)


def aggregate_frames(frames_list):
    """Aggregate a list of data frames into a single frame.

    Parameters
    ----------
    frames_list: List[Tuple(str, re.match, pd.DataFrame)]
        triples of filenames, filename matches with the geo regex, and the data from the file

    Returns
    -------
    A pd.DataFrame concatenation of all data frames in `frames_list` with additional columns for
    geo_type, time_value, and signal derived from the corresponding re.match.
    """
    all_frames = []
    for _, match, data_df in frames_list:
        df = data_df.copy()
        # Get geo_type, date, and signal name as specified by CSV name.
        df['geo_type'] = match.groupdict()['geo_type']
        df['time_value'] = datetime.strptime(
            match.groupdict()['date'], "%Y%m%d").date()
        df['signal'] = match.groupdict()['signal']

        all_frames.append(df)

    return pd.concat(all_frames).reset_index(drop=True)

def lag_converter(lag_dict):
    """Convert a dictionary of lag values into the proper format.
    Parameters
    ----------
    lag_dict: Dict[str, str]
        Keys are either 'all', or signal names
        Values are either numeric or days of the week, represented by
            "Sunday+[0-7],[0-9]", first part represents the day of the week
            the upload happens, while the second number represents lag upon
            upload.
    Returns
    ----------
    Dict[str, int]
        Keys are all active signal names for an indicator, or "all"
        Values are obtained by looking at signal name entries,
            If not present then by the 'all' indicator,
            else 1.
    """
    def value_interpret(value):
        """Convert value from string to numeric, including sunday+m,n."""
        if value.startswith("sunday+"):
            value_num = (date.today().isoweekday() - int(value[7:8]) - 1) % 7 + 1
            assert value[8] == ","
            value_num += int(value[9])
        else:
            value_num = int(value)
        return value_num

    # Add 'all' to lag_dict keys, give it default value of 1
    lag_dict["all"] = lag_dict.get("all", "1")

    # Converting strings to numeric output
    output_dict = {sig:value_interpret(lag_dict.get(
        sig)) for sig in lag_dict.keys()}
    return output_dict
