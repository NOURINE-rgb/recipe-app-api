"""
URLs for the recipe app.
"""
from django.urls import include,path
from rest_framework.routers import DefaultRouter
from .views import RecipeViewSet

router = DefaultRouter()
router.register('recipes', RecipeViewSet)
app_name = 'recipe'
urlpatterns = [
    path('', include(router.urls))
]