from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Recipe
from decimal import Decimal
from recipe.serializers import RecipeSerializer,RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')

def recipe_detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """Helper function to create a recipe."""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': Decimal('5.00'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeApiTests(TestCase):
    """"Test for unauthenticated recipe API access."""
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required to access the recipe API."""
        res = self.client.get(RECIPES_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeApiTests(TestCase):
    """Tests for authenticated recipe API access."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="test@example.com",
            password="testpass"
        )
        self.client.force_authenticate(self.user)
    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user, title='Another recipe')
        res = self.client.get(RECIPES_URL)
        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retrieving recipes for user."""
        other_user = create_user(
            email="other@example.com",
            password="testpass"
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)
        res = self.client.get(RECIPES_URL)
        recipe = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipe, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_view_recipe_detail(self):
        """Test viewing a recipe detail."""
        recipe = create_recipe(user=self.user)
        url = recipe_detail_url(recipe.id)
        res = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe."""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': Decimal('5.00'),
            'description': 'Delicious chocolate cheesecake recipe',
            'link': 'http://example.com/chocolate_cheesecake.pdf',
        }
        res = self.client.post(RECIPES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update_recipe(self):
        """Test updating a recipe with patch."""
        recipe = create_recipe(user=self.user, title='Original title', link='http://example.com/original.pdf')
        payload = {'title': 'Updated recipe title'}
        url = recipe_detail_url(recipe.id)
        res =  self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_full_update_recipe(self):
        """Test updating a recipe with put."""
        recipe = create_recipe(
            user=self.user,
            title='Original title',
            link='http://example.com/original.pdf',
            description='Original description',
            time_minutes=10,
            price=Decimal('3.00')
        )
        payload = {
            'title': 'Updated recipe title',
            'link': 'http://example.com/updated.pdf',
            'description': 'Updated description',
            'time_minutes': 20,
            'price': Decimal('6.00')
        }
        url = recipe_detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))
        self.assertEqual(recipe.user, self.user)

    def test_update_recipe_user_returns_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(
            email="newtest@example.com",
            password="testpass",
        )
        recipe = create_recipe(user=self.user)
        payload = {'user': new_user.id}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)
        url = recipe_detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = Recipe.objects.filter(id=recipe.id).exists()
        self.assertFalse(exists)

    def test_delete_other_user_recipe_error(self):
        """Test trying to delete another user's recipe gives error."""
        new_user = create_user(
            email="newtest@example.com",
            password="testpass",
        )
        recipe = create_recipe(user=new_user)
        url = recipe_detail_url(recipe.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = Recipe.objects.filter(id=recipe.id).exists()
        self.assertTrue(exists)