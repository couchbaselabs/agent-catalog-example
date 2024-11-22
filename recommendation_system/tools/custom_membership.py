from agentc_core.tool import tool


@tool
def custom_membership_check(listA: list[str], listB: list[str]) -> str:
    """for given two list of words, select the one which is in both the list"""
    hashmap = {word: True for word in listA}

    for word in listB:
        if word in hashmap:
            return str(word)
    return listA[0]
