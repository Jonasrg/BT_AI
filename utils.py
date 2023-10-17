import json
import os 
import requests
import re



def write_to_file(retrieved_data_path, ls)-> None:
    """
    Write retrieved data to file.
    Parameters
    ----------
    retrieved_data_path : str
        Path to file where data is stored
    ls : list
        List of dictionaries containing retrieved data
    """
    if ls != None:
        try:
            with open(retrieved_data_path, 'r') as f:
                    json_file = json.load(f)
        except FileNotFoundError as e:
            json_file = []

        json_file.extend(ls)

        with open(retrieved_data_path, 'w') as f:
            json.dump(json_file, f, indent=4)
    else:
        pass


# Function to count the number of words between quotation marks
# This is used to count the number of words in the query
# This is necessary because the OPS API has a limit of 20 words per query
def count_words_between_quotes(request):
    word_count = 0
    # Regex to find all phrases between quotation marks
    phrases = re.findall(r'"(.*?)"', request)
    for phrase in phrases:
        # Splitting each phrase by space to count words
        word_count += len(phrase.split())
    return word_count