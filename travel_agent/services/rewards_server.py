import datetime
import fastapi
import pydantic
import random
import uuid

travel_server = fastapi.FastAPI()


class NewMemberResponse(pydantic.BaseModel):
    member_name: str
    member_id: str


class GetMemberRewardsResponse(pydantic.BaseModel):
    class Rewards(pydantic.BaseModel):
        points: int

    member_id: str
    member_since: str
    rewards: Rewards


@travel_server.post("/create")
def create_new_member(member_name: str) -> NewMemberResponse:
    """Create a new travel-rewards member."""
    return NewMemberResponse(member_name=member_name, member_id=uuid.uuid4().hex)


@travel_server.get("/rewards/{member_id}")
def get_member_rewards(member_id: str) -> GetMemberRewardsResponse:
    """Get the rewards associated with a member."""
    return GetMemberRewardsResponse(
        member_id=member_id,
        member_since=str((datetime.datetime.today() - datetime.timedelta(days=100)).isoformat()),
        rewards=GetMemberRewardsResponse.Rewards(points=random.randint(1, 10000)),
    )
