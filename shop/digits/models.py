from PIL import Image
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]


def get_product_url(obj, viewname):
    ct_model = obj.__class__._meta.model_name
    return reverse(viewname, kwargs={'ct_model': ct_model, 'slug': obj.slug})


class MinResolutonErrorException(Exception):
    pass


class MaxResolutonErrorException(Exception):
    pass


class LatestProductsManager:

    @staticmethod
    def get_products_for_models(*args, **kwargs):
        with_respect_to = kwargs.get('with_respect_to')
        products = []
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists():
                if with_respect_to in args:
                    return sorted(products, key=lambda x: x.__class__._meta.model_name.startswith(with_respect_to),
                                  reverse=True)
        return products


class LatestProducts:
    objects = LatestProductsManager()


class CategoryManager(models.Manager):
    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки': 'notebook__count',
        'Смартфоны': 'smartphone__count',
        'Холодильники': 'fridge__count',
        'Варочная панель': 'hob__count',
    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categories_for_left_sidebar(self):
        models = get_models_for_count('notebook', 'smartphone', 'fridge', 'hob')
        qs = list(self.get_queryset().annotate(*models))
        data = [
            dict(name=c.name, url=c.get_absolut_url(), count=getattr(c, self.CATEGORY_NAME_COUNT_NAME[c.name]))
            for c in qs
        ]

        return data


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name='Наименование товара')
    slug = models.SlugField(unique=True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolut_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})


class Product(models.Model):
    VALID_RESOLUTION_MIN = (300, 300)
    VALID_RESOLUTION_MAX = (1500, 1500)
    MAX_IMAGE_SIZE = 3145728

    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name='категория', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='наименование товара')
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='изображение')
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')
    description = models.TextField(null=True, verbose_name='описание товара')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        image = self.image
        img = Image.open(image)
        min_width, min_height = self.VALID_RESOLUTION_MIN
        max_width, max_height = self.VALID_RESOLUTION_MAX
        if img.width < min_width or img.height < min_height:
            raise MinResolutonErrorException(
                'Загружаемое изображение ({}*{}) меньше допустимого'.format(img.width, img.height))
        if img.width > max_width or img.height > max_height:
            raise MaxResolutonErrorException(
                'Загружаемое изображение ({}*{}) больше допустимого'.format(img.width, img.height))
        super().save(*args, **kwargs)

    def get_model_name(self):
        return self.__class__.__name__.lower()


class Notebook(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(max_length=255, verbose_name=' Тип дисплея')
    processor_frec = models.CharField(max_length=255, verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    video = models.CharField(max_length=255, verbose_name='Видеокарта')
    time_without_charge = models.CharField(max_length=255, verbose_name='Время работы акумулятора')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolut_url(self):
        return get_product_url(self, 'product_detail')


class Smartphone(Product):
    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(max_length=255, verbose_name=' Тип дисплея')
    resolution = models.CharField(max_length=255, verbose_name='Разрешение экрана')
    accum_volume = models.CharField(max_length=255, verbose_name='Емкость аккумулятора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    sd = models.BooleanField(default=True, verbose_name='Поддержка sd карты')
    sd_volume = models.CharField(max_length=255, blank=True, verbose_name='Максимальный объем sd карты')
    main_cam_mp = models.CharField(max_length=255, verbose_name='Основная камера')
    frontal_cam_mp = models.CharField(max_length=255, verbose_name='Фронтальная камера')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolut_url(self):
        return get_product_url(self, 'product_detail')


class Fridge(Product):
    height = models.CharField(max_length=255, verbose_name='Высота')
    width = models.CharField(max_length=255, verbose_name=' Ширина')
    depth = models.CharField(max_length=255, verbose_name='Глубина')
    volume_of_the_refrigerating_chamber = models.CharField(max_length=255, verbose_name='Объем холодильной камеры')
    freezer_capacity = models.CharField(max_length=255, verbose_name='Объем морозильной камеры')
    no_frost = models.CharField(max_length=255, verbose_name='Система No Frost')
    shelves_refrigerating = models.CharField(max_length=255, blank=True, verbose_name='Полок в холодильной камере')
    shelves_freezer = models.CharField(max_length=255, verbose_name='Полок на двери хол. камеры')
    weight = models.CharField(max_length=255, verbose_name='Вес')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolut_url(self):
        return get_product_url(self, 'product_detail')


class Hob(Product):
    height = models.CharField(max_length=255, verbose_name='Высота')
    width = models.CharField(max_length=255, verbose_name=' Ширина')
    depth = models.CharField(max_length=255, verbose_name='Глубина')
    burners = models.CharField(max_length=255, verbose_name='Количество конфорок')
    protection_from_children = models.CharField(max_length=255, verbose_name='Защита от детей')
    body = models.CharField(max_length=255, verbose_name='Материал варочной поверхности')
    weight = models.CharField(max_length=255, verbose_name='Вес')
    color = models.CharField(max_length=255, verbose_name='Цвет')

    def __str__(self):
        return '{} : {}'.format(self.category.name, self.title)

    def get_absolut_url(self):
        return get_product_url(self, 'product_detail')