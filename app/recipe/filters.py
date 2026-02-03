import django_filters
from core.models import Ingredient, Tag, Recipe

class RecipeFilter(django_filters.FilterSet):
    """Filter for recipes."""
    ingredients = django_filters.BaseInFilter(
        field_name='ingredients__id',
        lookup_expr='in'
    )
    tags = django_filters.BaseInFilter(
        field_name='tags__id',
        lookup_expr='in'
    )
    class Meta:
        model = Recipe
        fields = ['ingredients', 'tags']