from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm

from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from apps.auths.forms import UserChangeForm, UserCreationForm
from apps.auths.models import User

ACTIVE_LABEL = "Active"
INACTIVE_LABEL = "Inactive"
STAFF_LABEL = "Staff"
REGULAR_LABEL = "Regular"
ACTIVE_LABEL_COLORS = {ACTIVE_LABEL: "success", INACTIVE_LABEL: "danger"}
STAFF_LABEL_COLORS = {STAFF_LABEL: "info", REGULAR_LABEL: "default"}

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ["email"]
    list_display = ["user_header", "active_label", "staff_label", "post_count"]
    list_filter = [
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    ]
    list_filter_submit = True
    search_fields = ["email", "first_name", "last_name"]
    readonly_fields = ["last_login", "date_joined"]
    actions = ["activate_users", "deactivate_users"]

    fieldsets = (
        (
            "Personal info",
            {"classes": ["tab"], "fields": ("email", "password", "first_name", "last_name")},
        ),
        (
            "Permissions",
            {
                "classes": ["tab"],
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Important dates", {"classes": ["tab"], "fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ["wide"],
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).annotate(post_count=Count("post"))

    @display(description="User", header=True, ordering="email")
    def user_header(self, obj: User) -> tuple[str, str, str]:
        initials = f"{obj.first_name[:1]}{obj.last_name[:1]}"
        return obj.full_name, obj.email, initials

    @display(description="Status", ordering="is_active", label=ACTIVE_LABEL_COLORS)
    def active_label(self, obj: User) -> str:
        return ACTIVE_LABEL if obj.is_active else INACTIVE_LABEL

    @display(description="Role", ordering="is_staff", label=STAFF_LABEL_COLORS)
    def staff_label(self, obj: User) -> str:
        return STAFF_LABEL if obj.is_staff else REGULAR_LABEL

    @display(description="Posts", ordering="post_count")
    def post_count(self, obj: User) -> int:
        return obj.post_count

    @action(description="Activate", permissions=["change"], icon="check_circle")
    def activate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users activated.")

    @action(description="Deactivate", permissions=["change"], icon="block")
    def deactivate_users(self, request: HttpRequest, queryset: QuerySet[User]) -> None:
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users deactivated.")


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
