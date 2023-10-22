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
    