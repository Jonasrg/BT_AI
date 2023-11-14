# module to transform data returned by extract.py into a dataframe
import pandas as pd

def tf_search_biblio(ls:list)->pd.DataFrame:
    df = pd.DataFrame(ls)
    # set date columns to datetime
    df["document_date"] = pd.to_datetime(df["document_date"])
    # Add year and month columns
    df["document_date_year"] = df["document_date"].dt.year
    df["document_date_month"] = df["document_date"].dt.month
    # create full document id (publication number)
    df["document_id"] = df["document_country"] + df["document_doc-number"] + df["document_kind"]
    return df

def prep_eurostat_data(data_path:str, code_path:str)->pd.DataFrame:
    codes = pd.read_csv(code_path, sep='\t', header=None, names=["indic_sb", "indic_sb_name"])
    sbs_stats = pd.read_csv(data_path)
    df =  sbs_stats.merge(codes, on="indic_sb", how="left")
    df.drop(columns=["STRUCTURE","STRUCTURE_ID", "freq" ], inplace=True)
    return df