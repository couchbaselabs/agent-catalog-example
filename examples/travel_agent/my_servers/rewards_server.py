import random
import uuid
import fastapi
import datetime

travel_server = fastapi.FastAPI()


@travel_server.post("/create")
def create_new_member(member_name: str):
    """ Create a new travel-rewards member. """
    return {
        'member_name': member_name,
        'member_id': uuid.uuid4().hex
    }


@travel_server.get("/rewards/{member_id}")
def get_member_rewards(member_id: str):
    """ Get the rewards associated with a member. """
    return {
        'member_id': member_id,
        'member_since': str((datetime.datetime.today() - datetime.timedelta(days=100)).isoformat()),
        'rewards': {
            'points': random.randint(1, 10000),
        }
    }
