# module to transform data returned by extract.py into a dataframe
import pandas as pd


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


def prep_eurostat_data(data_path: str, code_path: str) -> pd.DataFrame:
    codes = pd.read_csv(
        code_path, sep="\t", header=None, names=["indic_sb", "indic_sb_name"]
    )
    sbs_stats = pd.read_csv(data_path)
    df = sbs_stats.merge(codes, on="indic_sb", how="left")
    df.drop(columns=["STRUCTURE", "STRUCTURE_ID", "freq"], inplace=True)
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
    prepped_patents = patents_gr_industry_year.groupby(
        by=["query_industry"]
    ).filter(lambda x: len(x) >= 4)
    return prepped_patents


def prep_data(prepped_patents_df, prepped_eurostat_df) -> pd.DataFrame:
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
    # only keep values for each industry and indicator after the first patent was recorded
    df = df[df["cumsum_patents"] > 0]
    # drop NaNs in cumsum_patents to keep only data for each industry and indicator from the year
    # where first patent was retrieved
    df.dropna(subset="cumsum_patents", inplace=True)
    # Calculate the min and max year for each industry
    years_min_max = df.groupby("nace_r2").agg(
        min_year=("document_date_year", "min"), max_year=("document_date_year", "max")
    )
    # Merge the minimum year back to the original dataframe
    prepped_df = df.merge(years_min_max, on="nace_r2")
    # TODO: Drop N/As in OBS_VALUE column??
    return prepped_df
