import itertools
import pandas as pd
from collections import Counter
import yaml
import json
from datetime import datetime

# with open("config.yaml", "r") as stream:
#         config = yaml.safe_load(stream)


def get_keywords(config: dict) -> dict:
    """
    Get keywords for each NACE code.
    NACE Codes provided by https://github.com/jnsprnw/nace-codes/blob/master/codes.csv

    Parameters
    ----------
    nace_codes : str
        NACE codes separated by comma

    """
    to_replace = [
        "(",
        ")",
        ", ",
        ". ",
        "? ",
        " of ",
        " and ",
        "/",
        " to ",
        " in ",
        " other ",
        "; ",
        " for ",
        " - ",
        " as ",
        " own ",
        " use ",
        "n.e.c.",
        "  ",
    ]
    nace_codes = pd.read_csv(config["paths"]["nace_codes_csv"])
    nace_codes.fillna(method="ffill", inplace=True)

    # create dictionary of main (mandatory) keywords for each industry
    # keywords are taken from the NACE code descriptions
    # keywords are lower case and special characters are removed
    industry_keywords = dict()
    for key in config["NACE_INDSUTRIES_LV_1"].keys():
        industry_keywords[key] = list()
        for item in config["NACE_INDSUTRIES_LV_1"][key]:
            element = item.lower()
            for char in to_replace:
                element = element.replace(char, " ")
            industry_keywords[key].append(element.strip())

    # create dictionary of keywords for each NACE code
    # these keywords are part of the search query along with the mandatory keywords for each industry
    # keywords are lower case and special characters are removed
    keywords = dict()
    for i in nace_codes["Division"].dropna().unique():
        tmp_df = nace_codes[nace_codes["Division"] == i]
        activities = " ".join(tmp_df["Activity"].tolist())
        for char in to_replace:
            activities = activities.lower().replace(char, " ")

        words = activities.split(" ")
        for index, word in enumerate(words):
            words[index] = word.strip()
        words = list(set(words))
        # remove empty strings
        words = list(filter(None, words))
        keywords[i] = words

    # map Division to Industry
    # this is needed to create the keyword strings for each industry
    Div_Ind_dict = dict()
    for i in nace_codes["Division"].dropna().unique():
        tmp_df = nace_codes[nace_codes["Division"] == i]
        Div_Ind_dict[i] = tmp_df["Section"].unique().tolist()[0]

    # return dictionaries mapped by Section and Division
    return keywords, industry_keywords, Div_Ind_dict


def construct_query(config: dict, save_to_path: str | bool = "data/") -> dict:
    """
    construct query for each country and industry
    Returns a dictionary of dictionaries with structure {country:{industry:query}}

    Parameters
    ----------
    config : dict
        Configuration dictionary

    include : str
        'ANY', 'ALL' or '='

    """
    # get keywords, main keywords, and mapping between division and industry for each NACE code
    keywords, industry_keywords, Div_Ind_dict = get_keywords(config=config)

    # create keyword strings that contain a maximum of 10 keywords per string to be used as "OR" statements in the query
    industry_keyword_strings = create_industry_string(
        industry_keywords=industry_keywords
    )
    keyword_strings = create_keyword_strings(
        config=config, industry_keyword_strings=industry_keyword_strings
    )
    ls = list(config["CPC_Schemes"].values())  # list of lists
    ls = list(itertools.chain.from_iterable(ls))  # flatten list
    cpc_scheme_count = len(ls)  # number of CPC schemes
    query_terms_count = cpc_scheme_count + 1  # for country
    q_cpc_schemes = " ".join(ls)

    # reverse dictionary
    Ind_Div_dict = reverse_dict(dictionary=Div_Ind_dict)

    # create query dictionary
    # iterate over countries, industries, and divisions
    # create query for each division
    # query is a string that contains the main keywords for the industry, the keywords for the division, the CPC schemes, and the country
    query_dict = {}
    # iterate over countries
    for country in config["EU_COUNTRY_CODES"].keys():
        query_dict[country] = dict()
        # iterate over industries
        for industry in sorted(set(Div_Ind_dict.values())):
            query_dict[country][industry] = dict()
            # iterate over divisions
            for division in Ind_Div_dict[industry]:
                query_list = []
                # iterate over list of keyword strings
                if len(keyword_strings[division]) == 0:
                    continue
                else:
                    for string in keyword_strings[division]:
                        tmp_query = (
                            industry_keyword_strings[Div_Ind_dict[division]]
                            + " AND ("
                            + string
                            + " ) "
                            + "AND cpc any "
                            + '"'
                            + q_cpc_schemes
                            + '"'
                            + " AND AP="
                            + '"'
                            + country
                            + '"'
                        )
                        query_list.append(tmp_query)
                query_dict[country][industry][division] = query_list
    # save query dictionary to file
    if save_to_path != False:
        filename = datetime.today().strftime("%Y-%m-%d") + "_ops_search_queries.json"
        save_to_path = save_to_path + filename
        with open(save_to_path, "w") as f:
            json.dump(query_dict, f, indent=4)
    return query_dict


# creates keyword string to identify activities (NACE Lv 4) for each Division
# this string contains the OR statements of the keywords for each activity
# string is in the format: (ta = "keyword1" OR ta = "keyword2" OR ta = "keyword3")
def create_keyword_strings(config: dict, industry_keyword_strings: dict) -> dict:
    """
    Create a dictionary of keyword strings for each division with a maximum number of 10 keywords per string.
    PARAMETERS
    ----------
    keywords: dict
        Dictionary of keywords for each division.
    RETURNS
    -------
    keyword_strings: dict
        Dictionary of keyword strings for each division.
    """
    # max 20 terms in query and max 10 identical identifiers (e.g., "ta =") per query
    keywords, industry_keywords, Div_Ind_dict = get_keywords(config=config)

    # get length of cpc scheme
    ls = list(config["CPC_Schemes"].values())  # list of lists
    ls = list(itertools.chain.from_iterable(ls))  # flatten list
    cpc_scheme_count = len(ls)  # number of CPC schemes
    query_terms_count = cpc_scheme_count + 1  # for country

    keyword_strings = dict()
    for key in keywords.keys():
        # get length of keyword strings
        industry_keyword_len = len(
            " ".join(industry_keywords[Div_Ind_dict[key]]).split(" ")
        )

        # max 10 keywords per identifier
        step_identifier = 10 - industry_keyword_strings[Div_Ind_dict[key]].count(
            "ta ALL"
        )
        # max 20 words per query -> buffer of 2 words
        step_terms = 19 - industry_keyword_len - query_terms_count
        step = min(step_identifier, step_terms)
        string_lists = []
        for i in range(0, len(keywords[key]), step):
            tmp_list = keywords[key][i : i + step]
            string_lists.append("ta = " + " OR ta = ".join(f'"{w}"' for w in tmp_list))
        keyword_strings[key] = string_lists
    return keyword_strings


# creates keyword string to identify industries (NACE Lv 1)
# this string is used as a mandatory keyword in the query
# the string contains all keywords for the industry separated by "OR"
# string is in the format: (ta ALL "keyword1" OR ta ALL "keyword2" OR ta ALL "keyword3")
def create_industry_string(industry_keywords) -> dict:
    industry_string = {}
    for i in industry_keywords.keys():
        industry_string[i] = (
            "("
            + "ta ALL "
            + " OR ta ALL ".join(f'"{j}"' for j in industry_keywords[i])
            + ")"
        )
    return industry_string


# reverse dictionary
def reverse_dict(dictionary):
    new_dictionary = {k: [] for k in sorted(set(dictionary.values()))}
    for i in dictionary.keys():
        new_dictionary[dictionary[i]].append(i)
    return new_dictionary


# return all constructed queries in a single list
def return_all_queries(queries) -> list:
    all_queries = []
    for h in queries.keys():
        for i in queries[h].keys():
            for j in queries[h][i].keys():
                for string in queries[h][i][j]:
                    all_queries.append(string)
    return all_queries
