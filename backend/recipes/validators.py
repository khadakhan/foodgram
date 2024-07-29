from django.core.exceptions import ValidationError


def not_zero_validator(units):
    if units < 1:
        raise ValidationError(
            'Должно быть больше нуля!'
        )
