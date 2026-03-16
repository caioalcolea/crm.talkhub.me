from django.db.models import Count, Q


def filter_visible_pipelines(queryset, profile):
    """Filter pipelines by team/user visibility restrictions.

    Rules:
    - If both visible_to_teams and visible_to_users are empty → visible to all
    - If visible_to_teams is set → only users in those teams can see it
    - If visible_to_users is set → only those users can see it
    - Admins always see all pipelines
    """
    if profile.is_admin:
        return queryset

    user_teams = profile.user_teams.all()

    return queryset.annotate(
        _team_count=Count("visible_to_teams", distinct=True),
        _user_count=Count("visible_to_users", distinct=True),
    ).filter(
        Q(_team_count=0, _user_count=0)  # No restrictions
        | Q(visible_to_teams__in=user_teams)  # Team match
        | Q(visible_to_users=profile)  # Direct user match
    ).distinct()
