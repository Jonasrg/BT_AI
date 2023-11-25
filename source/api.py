import numpy as np
from base64 import b64encode
import os
import requests
import logging
from time import sleep

# Set up logging
logger = logging.getLogger(__name__)

# # Function to extract the content from the response
# def extract_content(response, country, industry, division, query, range_begin, range_end) -> list:
#     # Check if the response is empty
#     if "<code>SERVER.EntityNotFound</code>" in response.text:
#         return None

#     # Extract the content from the response
#     results = response.json()["ops:world-patent-data"]["ops:biblio-search"]["ops:search-result"]["ops:publication-reference"]
#     ls = []
#     # Check if the response is a list or a dictionary (single result)
#     if type(results) == list:
#         for i in results:
#                 data = {
#                     "header": dict(response.headers),
#                     "country" : country,
#                     "industry" : industry,
#                     "division" : division,
#                     "query" : query,
#                     "total_results": response.json()["ops:world-patent-data"]["ops:biblio-search"]["@total-result-count"],
#                     "range_begin" : range_begin,
#                     "range_end" : range_end,
#                     "family_id" : i['@family-id'],
#                     "document_id_type" : i["document-id"]['@document-id-type'],
#                     "document-id_country" : i["document-id"]['country']["$"],
#                     "document-id_doc-number" : i["document-id"]['doc-number']["$"],
#                     "document-id_kind" : i["document-id"]['kind']["$"],
#                     "publication_number" : i["document-id"]['country']["$"] + i["document-id"]['doc-number']["$"] + i["document-id"]['kind']["$"],
#                 }
#                 ls.append(data)
#     elif type(results) == dict:
#         data =   {
#             "header": dict(response.headers),
#             "country" : country,
#             "industry" : industry,
#             "division" : division,
#             "query" : query,
#             "total_results": response.json()["ops:world-patent-data"]["ops:biblio-search"]["@total-result-count"],
#             "range_begin" : range_begin,
#             "range_end" : range_end,
#             "family_id" : results['@family-id'],
#             "document_id_type" : results["document-id"]['@document-id-type'],
#             "document-id_country" : results["document-id"]['country']["$"],
#             "document-id_doc-number" : results["document-id"]['doc-number']["$"],
#             "document-id_kind" : results["document-id"]['kind']["$"],
#             "publication_number" : results["document-id"]['country']["$"] + results["document-id"]['doc-number']["$"] + results["document-id"]['kind']["$"],
#         }
#         ls.append(data)
#     else:
#          return None
#     return ls

# def extract_biblio(response):
#     ls = []
#     rjson = response.json()
#     for i in rjson["ops:world-patent-data"]["ops:biblio-search"]["ops:search-result"]["exchange-documents"]:
#         element = i["exchange-document"]
#         data = {
#             "document_system" : element["@system"],
#             "document_family_id" : element["@family-id"],
#             "document_country" : element["@country"],
#             "document_doc-number" : element["@doc-number"],
#             "document_kind" : element["@kind"],
#             "document_date" : element["bibliographic-data"]["publication-reference"]["document-id"][0]["date"]["$"],
#             "patent_classifications" : [{i["classification-scheme"]["@office"]:
#                                          [i["section"]["$"],
#                                           i["class"]["$"],
#                                           i["subclass"]["$"],
#                                           i["main-group"]["$"],
#                                           i["subgroup"]["$"],
#                                           i["classification-value"]["$"],
#                                           i["generating-office"]["$"]
#                                           ]} for i in element["bibliographic-data"]["patent-classifications"]["patent-classification"]],
#             "application-reference": element["bibliographic-data"]["application-reference"],
#             "priority-claims": element["bibliographic-data"]["priority-claims"],
#             "applicants": [i["applicant-name"]["name"]["$"] for i in element["bibliographic-data"]["parties"]["applicants"]["applicant"] if i["@data-format"] == "original"],
#             "inventors": [i["inventor-name"]["name"]["$"] for i in element["bibliographic-data"]["parties"]["inventors"]["inventor"] if i["@data-format"] == "original"],
#             "inventions-title": [{i["@lang"] : i["$"] } for i in element["bibliographic-data"]["invention-title"] if i["@lang"] == "en" or i["@lang"] == "de"],
#             "references_cited": element["bibliographic-data"]["references-cited"]["citation"],
#             "abstract": element["abstract"]["p"]["$"],
#         }

#         ls.append(data)
#     return ls


# Function to check the response for errors
# If the response is an error, the function will return False
def check_response(response, Sleeper, Access_token) -> bool:
    # check if access token has expired
    if "Access token has expired" in response.text:
        access_token = Access_token.renew_token()
        logger.debug("Access token expired. New token acquired.")
        sleep(2)
        return False
    # wait if robot was detected
    if response.status_code == 403:
        logger.warning(
            f"CLIENT.RobotDetected: sleep for {Sleeper.get_sleep()} seconds."
        )
        sleep(Sleeper.get_sleep())
        Sleeper.increase_sleep()
        return False
    else:
        Sleeper.default_sleep()
        return True


def make_request(
    query, range_begin, range_end, AccessToken, Sleeper, endpoint="biblio-search"
):
    ep = {
        "search": "https://ops.epo.org/3.2/rest-services/published-data/search",
        "biblio-search": "https://ops.epo.org/3.2/rest-services/published-data/search/biblio",
    }
    url = ep[endpoint]
    # define header
    headers = {
        "Accept": "application/json",
        "Content-Type": "text/plain",
        "Authorization": f"Bearer {AccessToken.access_token}",
    }
    params = {"Range": f"{range_begin}-{range_end}", "q": query}
    response = requests.get(url, params=params, headers=headers, timeout=20)

    # check if access token has expired
    if check_response(response=response, Sleeper=Sleeper, Access_token=AccessToken):
        return response
    else:
        return make_request(
            query=query,
            range_begin=range_begin,
            range_end=range_end,
            AccessToken=AccessToken,
            Sleeper=Sleeper,
        )


# class to handle sleep
class Sleeper:
    def __init__(self, start, end, steps):
        self.start = start
        self.end = end
        self.steps = steps
        self.sleep_array = np.linspace(self.start, self.end, self.steps)
        self.sleep_counter = 0

    def increase_sleep(self):
        self.sleep_counter += 1

    def default_sleep(self):
        self.sleep_counter = 0

    def get_sleep(self):
        return self.sleep_array[self.sleep_counter]


# class to handle access token
class AccessToken:
    def __init__(self):
        self.access_token = self.acquire_token()

    def acquire_token(self):
        headers = {
            "Authorization": "Basic {0}".format(
                b64encode(
                    "{0}:{1}".format(
                        os.getenv("ConsumerKey"), os.getenv("ConsumerSecretKey")
                    ).encode("ascii")
                ).decode("ascii")
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {"grant_type": "client_credentials"}
        response = requests.post(
            "https://ops.epo.org/3.2/auth/accesstoken",
            headers=headers,
            data=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def renew_token(self):
        self.access_token = self.acquire_token()
