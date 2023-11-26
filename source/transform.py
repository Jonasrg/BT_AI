# module to transform data returned by extract.py into a dataframe
import pandas as pd
from scipy.signal import detrend


def tf_search_biblio(ls: list) -> pd.DataFrame:
    df = pd.DataFrame(ls)
    # set date columns to datetime
    df["document_date"] = pd.to_datetime(df["document_date"])
    # Add year and month columns
    df["document_date_year"] = df["document_date"].dt.year
    df["document_date_month"] = df["document_date"].dt.month
    # create full document id (publication number)
    df["document_id"] = (
        df["document_country"] + df["document_doc-number"] + df["document_kind"]
    )
    return df


def prep_eurostat_data(
    data_path: str, indic_sb_codes: str, nace_codes: str
) -> pd.DataFrame:
    rename = {
        "Enterprises - number": "Enterprises (n)",
        "Persons employed - number": "Employees (n)",
        "Wage adjusted labour productivity (Apparent labour productivity by average personnel costs) - percentage": "Labor prod. (%)",
        "Gross value added per employee - thousand euro": "GVA/employee (€)",
        "Share of personnel costs in production - percentage": "Personnel costs (%)",
    }
    indic_sb_codes = pd.read_csv(
        indic_sb_codes, sep="\t", header=None, names=["indic_sb", "indic_sb_name"]
    )
    nace_codes = pd.read_csv(
        nace_codes, sep="\t", header=None, names=["nace_r2", "Industry"]
    )
    sbs_stats = pd.read_csv(data_path)
    df = sbs_stats.merge(indic_sb_codes, on="indic_sb", how="left")
    df = df.merge(nace_codes, on="nace_r2", how="left")
    df.drop(columns=["STRUCTURE", "STRUCTURE_ID", "freq"], inplace=True)
    df["indic_sb_name"] = df["indic_sb_name"].apply(lambda x: rename[x])
    # scale gross value added per employee
    df.loc[df["indic_sb_name"] == "GVA/employee (€)", "OBS_VALUE"] = df.loc[df["indic_sb_name"] == "GVA/employee (€)", "OBS_VALUE"] * 1000
    df.loc[df["indic_sb_name"] == "Employees (n)", "OBS_VALUE"] = df.loc[df["indic_sb_name"] == "Employees (n)", "OBS_VALUE"] / 1000
    return df


def prep_patents(patents_df) -> pd.DataFrame:
    # drop duplicates in each indsurty
    patents_df.drop_duplicates(subset=["query_industry", "document_id"], inplace=True)
    # keep only patents extracted for years in which eurostat data is available (2011-2020)
    patents_df = patents_df[
        (patents_df["document_date_year"] >= 2011)
        & (patents_df["document_date_year"] <= 2020)
    ]
    # get number of patents by industry and year
    patents_gr_industry_year = (
        patents_df.groupby(["query_industry", "document_date_year"])
        .size()
        .reset_index(name="sum_patents")
    )
    # sort patents
    patents_gr_industry_year.sort_values(by="sum_patents", ascending=False)
    # keep only patents that have at least four years of data
    prepped_patents = patents_gr_industry_year.groupby(by=["query_industry"]).filter(
        lambda x: len(x) >= 4
    )
    return prepped_patents


def prep_data(
    prepped_patents_df: pd.DataFrame,
    prepped_eurostat_df: pd.DataFrame,
    time_all: bool = False,
    detrended: bool = False
) -> pd.DataFrame:
    # merge eurostat data with patent data
    df = pd.merge(
        prepped_eurostat_df,
        prepped_patents_df,
        how="left",
        left_on=["nace_r2", "TIME_PERIOD"],
        right_on=["query_industry", "document_date_year"],
    )
    # sort dataframe
    df.sort_values(
        by=["nace_r2", "indic_sb", "TIME_PERIOD"], inplace=True, ascending=True
    )
    # account for NaN values within each industry and indicator
    # e.g., patents for an industry were only retrieved for the years [2016, 2018, 2019, 2020]
    # year 2017 is now NaN but actually 0 patents were retrieved for that year
    # fill missing years with zeros, but keep only data from the first year on where a patent was retrieved
    # i.e., where the cumulative sum of patents per industry and indicator is not 0 anymore
    # fill years column
    df["document_date_year"] = df["TIME_PERIOD"]
    # fill indsutry column
    df["query_industry"] = df["nace_r2"]
    # assign 0 patent retrievals to NaN values
    df["sum_patents"] = df["sum_patents"].fillna(0)
    # get cumulative sum of patents per industry and indicator
    df["cumsum_patents"] = df.groupby(["nace_r2", "indic_sb"])["sum_patents"].cumsum()
    # Calculate the min and max year for each industry
    years_min_max = (
        df[df["sum_patents"] != 0]
        .groupby("nace_r2")
        .agg(
            min_year=("document_date_year", "min"),
            max_year=("document_date_year", "max"),
        )
    )
    # Merge the minimum year back to the original dataframe
    prepped_df = df.merge(years_min_max, on="nace_r2")
    if time_all is False:
        # Keep only values in min_max time span for each industry
        prepped_df = prepped_df[
            (prepped_df["TIME_PERIOD"] >= prepped_df["min_year"])
            & (prepped_df["TIME_PERIOD"] <= prepped_df["max_year"])
        ]
    # Drop N/As in OBS_VALUE column
    # Cannot have N/A for regression. Replacing with 0 would be misleading
    prepped_df = prepped_df.dropna(subset="OBS_VALUE")
    # detrend "OBS_VALUE" and "sum patents"
    if detrended is True:
        for industry in prepped_df["nace_r2"].unique():
            for indicator in prepped_df["indic_sb_name"].unique():
                # There probably is a nicer way to do this. But it works.
                # create copy of df
                tmp_df = prepped_df.loc[(prepped_df["nace_r2"] == industry) & (prepped_df["indic_sb_name"] == indicator)]
                # loc group and replace values with detrended series
                prepped_df.loc[(prepped_df["nace_r2"] == industry)
                               & (prepped_df["indic_sb_name"] == indicator), "OBS_VALUE"] = detrend(tmp_df["OBS_VALUE"])
                prepped_df.loc[(prepped_df["nace_r2"] == industry)
                               & (prepped_df["indic_sb_name"] == indicator), "sum_patents"] = detrend(tmp_df["sum_patents"])
    prepped_df.rename(
        columns={
            "sum_patents": "Sum patents",
            "document_date_year": "Year",
            "nace_r2": "NACE",
            "indic_sb_name": "Indicator",
        },
        inplace=True,
    )
    prepped_df["Year (dummy)"] = prepped_df["Year"] - prepped_df["min_year"]
    return prepped_df
