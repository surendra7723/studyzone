
class OwnedModel:
    owner_field = "user"

    @classmethod
    def get_owner_field(cls):
        return getattr(cls, "owner_field", "user")

    def get_owner(self):
        return getattr(self, self.get_owner_field())
