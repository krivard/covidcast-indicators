# -*- coding: utf-8 -*-
"""Functions to call when downloading data."""
from dataclasses import dataclass
import datetime
import os
import re
from urllib.parse import quote_plus as quote_as_url

import pandas as pd
import requests

from delphi_utils.geomap import GeoMapper

from .constants import TRANSFORMS, SIGNALS, NEWLINE
from .constants import DOWNLOAD_ATTACHMENT, DOWNLOAD_LISTING

# YYYYMMDD
# example: "Community Profile Report 20211104.xlsx"
RE_DATE_FROM_FILENAME = re.compile(r'.*([0-9]{4})([0-9]{2})([0-9]{2}).*xlsx')

# example: "TESTING: LAST WEEK (October 24-30, Test Volume October 20-26)"
# example: "TESTING: PREVIOUS WEEK (October 17-23, Test Volume October 13-19)"
DATE_EXP = r'(?:([A-Za-z]*) )?([0-9]{1,2})'
DATE_RANGE_EXP = f"{DATE_EXP}-{DATE_EXP}"
RE_DATE_FROM_HEADER = re.compile(
    rf'.*TESTING: (.*) WEEK \({DATE_RANGE_EXP}(?:, Test Volume ({DATE_RANGE_EXP}))? *\)'
)

# example: "NAAT positivity rate - last 7 days (may be an underestimate due to delayed reporting)"
# example: "Total NAATs - last 7 days (may be an underestimate due to delayed reporting)"
RE_COLUMN_FROM_HEADER = re.compile('- (.*) 7 days')

@dataclass
class DatasetTimes:
    """Collect reference dates for a column."""

    column: str
    positivity_reference_date: datetime.date
    total_reference_date: datetime.date

    @staticmethod
    def from_header(header, publish_date):
        """Convert reference dates in overheader to DatasetTimes."""
        assert RE_DATE_FROM_HEADER.match(header), \
            f"Couldn't find reference date in header '{header}'"
        findall_result = RE_DATE_FROM_HEADER.findall(header)[0]
        def as_date(sub_result):
            month = sub_result[2] if sub_result[2] else sub_result[0]
            assert month, f"Bad month in header: {header}\nsub_result: {sub_result}"
            month_numeric = datetime.datetime.strptime(month, "%B").month
            day = sub_result[3]
            year = publish_date.year
            # year boundary
            if month_numeric > publish_date.month:
                year -= 1
            return datetime.datetime.strptime(f"{year}-{month}-{day}", "%Y-%B-%d").date()

        column = findall_result[0].lower()
        positivity_reference_date = as_date(findall_result[1:5])
        if findall_result[6]:
            # Reports published starting 2021-03-17 specify different reference
            # dates for positivity and total test volume
            total_reference_date = as_date(findall_result[6:10])
        else:
            total_reference_date = positivity_reference_date
        return DatasetTimes(column, positivity_reference_date, total_reference_date)
    def __getitem__(self, key):
        """Use DatasetTimes like a dictionary."""
        if key.lower()=="positivity":
            return self.positivity_reference_date
        if key.lower()=="total":
            return self.total_reference_date
        raise ValueError(
            f"Bad reference date type request '{key}'; need 'total' or 'positivity'"
        )
    def __eq__(self, other):
        """Check equality by value."""
        return isinstance(other, DatasetTimes) and \
            other.column == self.column and \
            other.positivity_reference_date == self.positivity_reference_date and \
            other.total_reference_date == self.total_reference_date

class Dataset:
    """All data extracted from a single report file."""

    def __init__(self, config, sheets=TRANSFORMS.keys(), logger=None):
        """Create a new Dataset instance.

        Download and cache the requested report file.

        Parse the file into data frames at multiple geo levels.
        """
        self.publish_date = self.parse_publish_date(config['filename'])
        self.url = DOWNLOAD_ATTACHMENT.format(
            assetId=config['assetId'],
            filename=quote_as_url(config['filename'])
        )
        if not os.path.exists(config['cached_filename']):
            if logger:
                logger.info("Downloading file", filename=config['cached_filename'])
            resp = requests.get(self.url)
            with open(config['cached_filename'], 'wb') as f:
                f.write(resp.content)

        self.workbook = pd.ExcelFile(config['cached_filename'])

        self.dfs = {}
        self.times = {}
        for si in sheets:
            assert si in TRANSFORMS, f"Bad sheet requested: {si}"
            if logger:
                logger.info("Building dfs",
                            sheet=f"{si}",
                            filename=config['cached_filename'])
            sheet = TRANSFORMS[si]
            self._parse_times_for_sheet(sheet)
            self._parse_sheet(sheet)

    @staticmethod
    def parse_publish_date(report_filename):
        """Extract publish date from filename."""
        return datetime.date(
            *[int(x) for x in RE_DATE_FROM_FILENAME.findall(report_filename)[0]]
        )
    @staticmethod
    def skip_overheader(header):
        """Ignore irrelevant overheaders."""
        # include "TESTING: [LAST|PREVIOUS] WEEK (October 24-30, Test Volume October 20-26)"
        # include "VIRAL (RT-PCR) LAB TESTING: [LAST|PREVIOUS] WEEK (August 24-30, ..."
        return not (isinstance(header, str) and \
                    (header.startswith("TESTING:") or \
                     header.startswith("VIRAL (RT-PCR) LAB TESTING:")) and \
                    # exclude "TESTING: % CHANGE FROM PREVIOUS WEEK" \
                    # exclude "TESTING: DEMOGRAPHIC DATA" \
                    header.find("WEEK (") > 0)
    def _parse_times_for_sheet(self, sheet):
        """Record reference dates for this sheet."""
        # grab reference dates from overheaders
        overheaders = pd.read_excel(
                self.workbook, sheet_name=sheet.name,
                header=None,
                nrows=1
        ).values.flatten().tolist()
        for h in overheaders:
            if self.skip_overheader(h):
                continue

            dt = DatasetTimes.from_header(h, self.publish_date)
            if dt.column in self.times:
                assert self.times[dt.column] == dt, \
                    f"Conflicting reference date from {sheet.name} {dt}" + \
                    f"vs previous {self.times[dt.column]}"
            else:
                self.times[dt.column] = dt
        assert len(self.times) == 2, \
            f"No times extracted from overheaders:\n{NEWLINE.join(str(s) for s in overheaders)}"

    @staticmethod
    def retain_header(header):
        """Ignore irrelevant headers."""
        return all([
            # include "Total NAATs - [last|previous] 7 days ..."
            # include "Total RT-PCR diagnostic tests - [last|previous] 7 days ..."
            # include "NAAT positivity rate - [last|previous] 7 days ..."
            # include "Viral (RT-PCR) lab test positivity rate - [last|previous] 7 days ..."
            (header.startswith("Total NAATs") or
             header.startswith("NAAT positivity rate") or
             header.startswith("Total RT-PCR") or
             header.startswith("Viral (RT-PCR)")),
            # exclude "NAAT positivity rate - absolute change ..."
            header.find("7 days") > 0,
            # exclude "NAAT positivity rate - last 7 days - ages <5"
            header.find(" ages") < 0,
        ])
    def _parse_sheet(self, sheet):
        """Extract data frame for this sheet."""
        df = pd.read_excel(
            self.workbook,
            sheet_name=sheet.name,
            header=1,
            index_col=0,
        )
        if sheet.row_filter:
            df = df.loc[sheet.row_filter(df)]
        select = [
            (RE_COLUMN_FROM_HEADER.findall(h)[0], h, h.lower())
            for h in list(df.columns)
            if self.retain_header(h)
        ]

        for sig in SIGNALS:
            sig_select = [s for s in select if s[-1].find(sig) >= 0]
            assert len(sig_select) > 0, \
                f"No {sig} in any of {select}\n\nAll headers:\n{NEWLINE.join(list(df.columns))}"
            self.dfs[(sheet.level, sig)] = pd.concat([
                pd.DataFrame({
                    "geo_id": sheet.geo_id_select(df).apply(sheet.geo_id_apply),
                    "timestamp": pd.to_datetime(self.times[si[0]][sig]),
                    "val": df[si[-2]],
                    "se": None,
                    "sample_size": None
                })
                for si in sig_select
            ])
        self.dfs[(sheet.level, "total")]["val"] /= 7 # 7-day total -> 7-day average


def as_cached_filename(params, config):
    """Formulate a filename to uniquely identify this report in the input cache."""
    return os.path.join(
        params['indicator']['input_cache'],
        f"{config['assetId']}--{config['filename']}"
    )

def fetch_listing(params):
    """Generate the list of report files to process."""
    listing = requests.get(DOWNLOAD_LISTING).json()['metadata']['attachments']

    # drop the pdf files
    listing = [
        dict(
            el,
            cached_filename=as_cached_filename(params, el),
            publish_date=Dataset.parse_publish_date(el['filename'])
        )
        for el in listing if el['filename'].endswith("xlsx")
    ]

    if params['indicator']['reports'] == 'new':
        # drop files we already have in the input cache
        listing = [el for el in listing if not os.path.exists(el['cached_filename'])]
    elif params['indicator']['reports'].find("--") > 0:
        # drop files outside the specified publish-date range
        start_str, _, end_str = params['indicator']['reports'].partition("--")
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()
        listing = [
            el for el in listing
            if start_date <= el['publish_date'] <= end_date
        ]
    # reference date is guaranteed to be before publish date, so we can trim
    # reports that are too early
    if 'export_start_date' in params['indicator']:
        listing = [
            el for el in listing
            if params['indicator']['export_start_date'] < el['publish_date']
        ]
    # can't do the same for export_end_date
    return listing

def download_and_parse(listing, logger):
    """Convert a list of report files into Dataset instances."""
    datasets = {}
    for item in listing:
        d = Dataset(item, logger=logger)
        for sig, df in d.dfs.items():
            if sig not in datasets:
                datasets[sig] = []
            datasets[sig].append(df)
    return datasets

def fetch_new_reports(params, logger=None):
    """Retrieve, compute, and collate all data we haven't seen yet."""
    listing = fetch_listing(params)

    # download and parse individual reports
    datasets = download_and_parse(listing, logger)

    # collect like signals together
    ret = {}
    for sig, lst in datasets.items():
        ret[sig] = pd.concat(lst)

    # add nation from state
    geomapper = GeoMapper()
    for sig in SIGNALS:
        df = geomapper.replace_geocode(
            ret[("state", sig)].rename(columns={"geo_id":"state_code"}),
            'state_code',
            'nation',
            new_col="geo_id"
        )
        ret[("nation", sig)] = df

    return ret
