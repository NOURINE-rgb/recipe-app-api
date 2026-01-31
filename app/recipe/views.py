"""
views for recipe APIs.
"""
from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from core.models import Ingredient, Recipe, Tag
from .serializers import(
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeSerializer,
    TagSerializer,
    RecipeImageSerializer,
)

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
        elif self.action == 'upload_image':
            return RecipeImageSerializer
        return self.serializer_class

    def get_queryset(self):
        """Retrieve recipes for authenticated user."""
        return self.queryset.filter(user = self.request.user).order_by('-id')

    def perform_create(self, serializer):
        """Create a new recipe."""
        serializer.save(user=self.request.user)
    @action(methods=['POST'], detail=True, url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to a recipe."""
        recipe = self.get_object()
        serializer = self.get_serializer(
            recipe,
            data=request.data
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class RecipeAttrViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        mixins.DestroyModelMixin,
                        mixins.UpdateModelMixin,
                        viewsets.GenericViewSet):
    """Base view for recipe attributes."""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve attributes for authenticated user."""
        return self.queryset.filter(user=self.request.user).order_by('-name')

class TagViewSet(RecipeAttrViewSet):
    """View for managing tags."""
    serializer_class = TagSerializer
    queryset = Tag.objects.all()

class IngredientViewSet(RecipeAttrViewSet):
    """View for managing ingredients."""
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()




