"""
views for recipe APIs.
"""
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from core.models import Recipe
from .serializers import RecipeDetailSerializer, RecipeSerializer

class RecipeViewSet(viewsets.ModelViewSet):
    """View for manage recipe APIs."""
    serializer_class = RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        if self.action == 'list':
            return RecipeSerializer
        return self.serializer_class

    def get_queryset(self):
        """Retrieve recipes for authenticated user."""
        return self.queryset.filter(user = self.request.user).order_by('-id')

    def perform_create(self, serializer):
        """Create a new recipe."""
        serializer.save(user=self.request.user)

