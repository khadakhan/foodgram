import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Load csv file to table'

    def add_arguments(self, parser):
        parser.add_argument('file_path', nargs=1, type=str)

    def handle(self, *args, **options):
        self.file_path = options['file_path'][0]
        with open(self.file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(
                f,
                fieldnames=['name', 'measurement_unit']
            )
            for row in reader:
                Ingredient.objects.create(**row)
