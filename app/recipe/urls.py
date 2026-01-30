"""
URLs for the recipe app.
"""
from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet, TagViewSet

router = DefaultRouter()
router.register('recipes', RecipeViewSet)
router.register('tags', TagViewSet)

app_name = 'recipe'
urlpatterns = [
    path('', include(router.urls))
]