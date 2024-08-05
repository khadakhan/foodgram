from django.contrib.auth import get_user_model
from django.db import models

from recipes.const import (
    TITLE_LENGTH,
    TAG_LENGTH,
    MEASUREMENT_UNIT_LENGTH,
    INGREDIENT_NAME_LENGTH
)
from recipes.validators import not_zero_validator


User = get_user_model()


class Ingredient(models.Model):
    """Ingridients model."""

    name = models.CharField(
        max_length=INGREDIENT_NAME_LENGTH,
        verbose_name='Название ингридиента',
        unique=True,
    )
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_UNIT_LENGTH,
        verbose_name='Единица измерения',
    )

    class Meta:
        verbose_name = 'ингредиенты'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags model."""

    name = models.CharField(
        max_length=TAG_LENGTH,
        verbose_name='Название тега',
    )
    slug = models.SlugField(
        unique=True,
        null=True,
        blank=True,
        max_length=TAG_LENGTH)

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Recipes model."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=TITLE_LENGTH,
        verbose_name='Название рецепта',
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        verbose_name='Фото рецепта',
    )
    text = models.TextField(
        verbose_name='Текст рецепта',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=(not_zero_validator,),
    )
    created_at = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )
    modified_at = models.DateTimeField(
        verbose_name='Дата изменение',
        auto_now_add=False,
        auto_now=True,
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredientsAmount',
        verbose_name='Ингридиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        through='RecipeTag',
        verbose_name='Теги',
    )
    short_link = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('created_at',)

    def __str__(self):
        return self.name


class RecipeTag(models.Model):
    """Bridge model for tag and recipe."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_tags',
        verbose_name='Рецепт',
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='tag_recipes',
        verbose_name='Тег',
    )


class RecipeIngredientsAmount(models.Model):
    """Model for ingredient specification in recipe."""

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amount',
        verbose_name='Рецепт',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=(not_zero_validator,),
    )

    class Meta:
        verbose_name = 'спецификация'
        verbose_name_plural = 'Спецификации'
        constraints = [
            models.UniqueConstraint(
                fields=['ingredient', 'recipe'],
                name='unique_ingredient_recipe'
            )
        ]

    @property
    def measurement_unit(self):
        return self.ingredient.measurement_unit

    def __str__(self):
        return self.ingredient.measurement_unit


class Favorite(models.Model):
    """Model for favorite recipe."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes_in_favorites',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='who_add_in_favorites',
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe'
            )
        ]

    def __str__(self):
        return self.user.username


class ShopList(models.Model):
    """Model for user shop list."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='what_by_user',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='who_by_this',
        verbose_name='Рецепт',
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_user_recipe_shoplist'
            )
        ]

    def __str__(self):
        return self.user.username
