# Function to extract the content from the response
def extract_search(
    response, country, industry, division, query, range_begin, range_end
) -> list:
    # # Check if the response is empty
    # if "<code>SERVER.EntityNotFound</code>" in response.text:
    #     return None

    # # Extract the content from the response
    results = response.json()["ops:world-patent-data"]["ops:biblio-search"]["ops:search-result"]["ops:publication-reference"]
    # TODO: Add new fields
    ls = []
    # Check if the response is a list or a dictionary (single result)
    if isinstance(results, list):
        for i in results:
            data = {
                "header": dict(response.headers),
                "country": country,
                "industry": industry,
                "division": division,
                "query": query,
                "total_results": response.json()["ops:world-patent-data"][
                    "ops:biblio-search"
                ]["@total-result-count"],
                "range_begin": range_begin,
                "range_end": range_end,
                "family_id": i["@family-id"],
                "document_id_type": i["document-id"]["@document-id-type"],
                "document-id_country": i["document-id"]["country"]["$"],
                "document-id_doc-number": i["document-id"]["doc-number"]["$"],
                "document-id_kind": i["document-id"]["kind"]["$"],
                "publication_number": i["document-id"]["country"]["$"]
                + i["document-id"]["doc-number"]["$"]
                + i["document-id"]["kind"]["$"],
            }
            ls.append(data)
    elif isinstance(results, dict):
        data = {
            "header": dict(response.headers),
            "country": country,
            "industry": industry,
            "division": division,
            "query": query,
            "total_results": response.json()["ops:world-patent-data"][
                "ops:biblio-search"
            ]["@total-result-count"],
            "range_begin": range_begin,
            "range_end": range_end,
            "family_id": results["@family-id"],
            "document_id_type": results["document-id"]["@document-id-type"],
            "document-id_country": results["document-id"]["country"]["$"],
            "document-id_doc-number": results["document-id"]["doc-number"]["$"],
            "document-id_kind": results["document-id"]["kind"]["$"],
            "publication_number": results["document-id"]["country"]["$"]
            + results["document-id"]["doc-number"]["$"]
            + results["document-id"]["kind"]["$"],
        }
        ls.append(data)
    else:
        return None
    return ls


# Function to extract the content from the response
def extract_biblio(json_object) -> list:
    ls = []
    for li in json_object:
        documents = li["response"]["ops:world-patent-data"]["ops:biblio-search"][
            "ops:search-result"
        ]["exchange-documents"]
        # check if documents is a list or a dictionary (only one result)
        if isinstance(documents, dict):
            documents = [documents]
        for i in documents:
            data = dict()
            data["query_country"] = li["country"]
            data["query_industry"] = li["industry"]
            data["query_division"] = li["division"]

            # get individual patent document
            element = i["exchange-document"]
            data["document_system"] = element["@system"]
            data["document_family_id"] = element["@family-id"]
            data["document_country"] = element["@country"]
            data["document_doc-number"] = element["@doc-number"]
            data["document_kind"] = element["@kind"]
            data["document_date"] = element["bibliographic-data"][
                "publication-reference"
            ]["document-id"][0]["date"]["$"]

            # get list of classifications for each patent
            if isinstance(
                element["bibliographic-data"]["patent-classifications"][
                    "patent-classification"
                ],
                list,
            ):
                data["patent_classifications"] = [
                    {
                        i["classification-scheme"]["@office"]: [
                            i["section"]["$"],
                            i["class"]["$"],
                            i["subclass"]["$"],
                            i["main-group"]["$"],
                            i["subgroup"]["$"],
                            i["classification-value"]["$"],
                            i["generating-office"]["$"],
                        ]
                    }
                    for i in element["bibliographic-data"]["patent-classifications"][
                        "patent-classification"
                    ]
                ]
            else:
                i = element["bibliographic-data"]["patent-classifications"][
                    "patent-classification"
                ]
                data["patent_classifications"] = [
                    {
                        i["classification-scheme"]["@office"]: [
                            i["section"]["$"],
                            i["class"]["$"],
                            i["subclass"]["$"],
                            i["main-group"]["$"],
                            i["subgroup"]["$"],
                            i["classification-value"]["$"],
                            i["generating-office"]["$"],
                        ]
                    }
                ]

            data["application-reference"] = element["bibliographic-data"][
                "application-reference"
            ]
            data["priority-claims"] = element["bibliographic-data"]["priority-claims"]

            # get applicants in original format (not in epodoc format)
            data["applicants"] = [
                i["applicant-name"]["name"]["$"]
                for i in element["bibliographic-data"]["parties"]["applicants"][
                    "applicant"
                ]
                if i["@data-format"] == "original"
            ]
            # get inventors in original format (not in epodoc format)
            # check if inventors exist
            if "inventors" in element["bibliographic-data"]["parties"].keys():
                data["inventors"] = [
                    i["inventor-name"]["name"]["$"]
                    for i in element["bibliographic-data"]["parties"]["inventors"][
                        "inventor"
                    ]
                    if i["@data-format"] == "original"
                ]
            else:
                data["inventors"] = None
            data["invention-title"] = [
                {i["@lang"]: i["$"]}
                for i in element["bibliographic-data"]["invention-title"]
                if i["@lang"] == "en" or i["@lang"] == "de"
            ]

            # check if citation exists
            if "references-cited" in element["bibliographic-data"].keys():
                # check for single citation
                if isinstance(
                    element["bibliographic-data"]["references-cited"]["citation"], dict
                ):
                    element["bibliographic-data"]["references-cited"]["citation"] = [
                        element["bibliographic-data"]["references-cited"]["citation"]
                    ]
                # create list of citations with tuples (document-id, name, date);
                # if name and date are unavailable:  name/date = ""
                data["references_cited"] = [
                    (
                        j["doc-number"]["$"],
                        (j["name"]["$"] if "name" in j.keys() else ""),
                        (j["date"]["$"] if "date" in j.keys() else ""),
                    )
                    for i in element["bibliographic-data"]["references-cited"][
                        "citation"
                    ]
                    if "patcit"
                    in i.keys()  # patcit = patent citation, sometimes there are other citations
                    for j in i["patcit"]["document-id"]
                    if j["@document-id-type"] == "epodoc"
                ]

            else:
                data["references_cited"] = None

            # check if abstract exists
            if "abstract" in element.keys():
                if isinstance(element["abstract"], dict):
                    element["abstract"] = [element["abstract"]]
                for i in element["abstract"]:
                    data["abstract"] = i["p"]["$"] if i["@lang"] == "en" else None
            else:
                data["abstract"] = None
            ls.append(data)
    return ls
