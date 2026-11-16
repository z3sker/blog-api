from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.forms import UserCreationForm as UnfoldUserCreationForm

from apps.auths.models import User


class UserCreationForm(UnfoldUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class UserChangeForm(UnfoldUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
