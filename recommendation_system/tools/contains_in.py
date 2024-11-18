
import pydantic
import re
from agentc_core.tool import tool

@tool
def vector_search_compat(listA:list[str], listB:list[str]) -> str:
    """for given two list of words, select the one which is in both the list"""
    hashmap = {word: True for word in listA}
    
    for word in listB:
        if word in hashmap:
            return str(word)
    return listA[0]