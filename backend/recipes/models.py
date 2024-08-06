from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator
)

from recipes.const import (
    TITLE_LENGTH,
    TAG_LENGTH,
    MEASUREMENT_UNIT_LENGTH,
    INGREDIENT_NAME_LENGTH,
    MIN_VALUE,
    MAX_VALUE
)
from users.models import FoodUser as User


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
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_unit'
            )
        ]

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
        max_length=TAG_LENGTH
    )

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
        validators=(
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE)
        ),
    )
    created_at = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredientsAmount',
        verbose_name='Ингридиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        # не удаляю промежточную сущность, так как явно использую её в admin,
        # serializers
        through='RecipeTag',
        verbose_name='Теги',
    )
    short_link = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name

# не удаляю промежточную сущность, так как явно использую её в admin,
# serializers


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
        validators=(
            MinValueValidator(MIN_VALUE),
            MaxValueValidator(MAX_VALUE)
        ),
    )

    class Meta:
        verbose_name = 'Кол-во ингредиента в рецепте'
        verbose_name_plural = 'Кол-во ингредиента в рецепте'
        constraints = (
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_ingredient_recipe'
            ),
        )

    def __str__(self):
        return (f'Ингредиент{self.ingredient.name} {self.amount}'
                f' {self.ingredient.measurement_unit}')


class BaseModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'{self.recipe} добавил себе {self.user.username}'


class Favorite(BaseModel):
    """Model for favorite recipe."""

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe'
            )
        ]


class ShopList(BaseModel):
    """Model for user shop list."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='recipe_add_shoplist'
    )
    # оставил тут поле чтобы для него было отдельное related_name
    # без этого ошибка в скачивании списка покупок
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='user_add_shoplist'
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe_shoplist'
            )
        ]
