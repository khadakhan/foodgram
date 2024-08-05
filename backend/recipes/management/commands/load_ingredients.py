import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load csv file to table'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            default='C:/Dev/foodgram/data/test_load.csv',
            nargs='?',
            type=str
        )

    def handle(self, *args, **options):
        self.file_path = options['file_path']
        try:
            with open(self.file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(
                    f,
                    fieldnames=['name', 'measurement_unit']
                )
                objs = [
                    Ingredient(
                        name=row['name'],
                        measurement_unit=row['measurement_unit']
                    )
                    for row in reader
                ]
                print('Загрузка началась.')
                Ingredient.objects.bulk_create(objs)
                print('Загрузка закончилась.')
        except FileNotFoundError as e:
            print(f'{e} Файл не найден, укажите другой путь поcле'
                  f' команды load_ingredients')
