from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Ingredient, Recipe, Tag
from decimal import Decimal
import tempfile
import os
from PIL import Image
from recipe.serializers import RecipeSerializer,RecipeDetailSerializer

RECIPES_URL = reverse('recipe:recipe-list')

def recipe_detail_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse('recipe:recipe-upload-image',args=[recipe_id])

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

    def test_create_recipe_with_new_tags(self):
        """Test creating a recipe with new tags."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 20,
            'price': Decimal('7.00'),
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        for tag in payload['tags']:
            exists = tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tag(self):
        """Test creating a recipe with an existing tag."""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        payload = {
            'title': 'Pancakes',
            'time_minutes': 5,
            'price': Decimal('3.00'),
            'tags': [{'name': 'Breakfast'}, {'name': 'Dessert'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        tags = recipe.tags.all()
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag, tags)
        for tag in payload['tags']:
            exists = tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating a tag when updating a recipe."""
        recipe = create_recipe(user=self.user)
        payload = {'tags': [{'name': 'Lunch'}]}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_assign_existing_tag_on_update(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_dinner = Tag.objects.create(user=self.user, name='Dinner')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_dinner)

        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        payload = {'tags': [{'name': 'Breakfast'}]}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag_dinner, recipe.tags.all())
        self.assertIn(tag_breakfast, recipe.tags.all())

    def test_clear_tags_on_update(self):
        """Test clearing tags from a recipe."""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        payload = {'tags': []}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with ingredients."""
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 30,
            'price': Decimal('4.00'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Taco Shells'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exists = ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a recipe with an existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        payload = {
            'title': 'Lemon Drizzle Cake',
            'time_minutes': 60,
            'price': Decimal('8.00'),
            'ingredients': [{'name': 'Lemon'}, {'name': 'Sugar'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        ingredients = recipe.ingredients.all()
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient, ingredients)
        for ingredient in payload['ingredients']:
            exists = ingredients.filter(
                name=ingredient['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """Test creating an ingredient when updating a recipe."""
        recipe = create_recipe(user=self.user)
        payload = {'ingredients': [{'name': 'Cilantro'}]}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Cilantro')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_assign_existing_ingredient_on_update(self):
        """Test assigning an existing ingredient when updating a recipe."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Feta Cheese')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)
        ingredient2 = Ingredient.objects.create(user=self.user, name='Olives')
        payload = {'ingredients': [{'name': 'Olives'}]}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient1, recipe.ingredients.all())
        self.assertIn(ingredient2, recipe.ingredients.all())

    def test_clear_ingredients_on_update(self):
        """Test clearing ingredients from a recipe."""
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)
        payload = {'ingredients': []}
        url = recipe_detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)

    def test_filter_recipes_by_tags(self):
        """Test returning recipes with specific tags."""
        r1 = create_recipe(user=self.user, title='Thai vegetable curry')
        r2 = create_recipe(user=self.user, title='Aubergine with tahini')
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Vegetarian')
        r1.tags.add(tag1)
        r2.tags.add(tag2)
        r3 = create_recipe(user=self.user, title='Fish and chips')
        params = {'tags':f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPES_URL, params)
        serializer1 = RecipeSerializer(r1)
        serializer2 = RecipeSerializer(r2)
        serializer3 = RecipeSerializer(r3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_recipes_by_ingredients(self):
        """Test returning recipes with specific ingredients."""
        r1 = create_recipe(user=self.user, title='Posh beans on toast')
        r2 = create_recipe(user=self.user, title='Chicken cacciatore')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Feta cheese')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Chicken')
        r1.ingredients.add(ingredient1)
        r2.ingredients.add(ingredient2)
        r3 = create_recipe(user=self.user, title='Steak and mushrooms')
        params = {'ingredients': f'{ingredient1.id},{ingredient2.id}'}
        res = self.client.get(RECIPES_URL, params)
        serializer1 = RecipeSerializer(r1)
        serializer2 = RecipeSerializer(r2)
        serializer3 = RecipeSerializer(r3)
        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for image upload API."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user(
            email="user@example.com",
            password="testpass123"
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        #for cleaning up after tests that upload images
        return self.recipe.image.delete()
    def test_upload_image_to_recipe(self):
        """Test uploading an image to recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10,10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            res = self.client.post(url, {'image': image_file}, format='multipart')
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
        self.assertTrue(self.recipe.image.path.endswith('.jpg'))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image."""
        url = image_upload_url(self.recipe.id)
        res = self.client.post(url, {'image': 'notanimage'}, format='multipart')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

