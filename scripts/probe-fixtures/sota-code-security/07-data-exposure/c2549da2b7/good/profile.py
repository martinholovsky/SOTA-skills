class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str

@app.patch("/me")
def update_me():
    data = ProfileUpdate.model_validate(request.get_json())
    current_user.display_name = data.display_name
