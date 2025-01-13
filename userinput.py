from pydantic import BaseModel

class UserInput(BaseModel):
  gender: str
  desiredPrice: int
  desiredLocation_Long: float
  desiredLocation_Lat: float
class Response(BaseModel):
  recommend: list