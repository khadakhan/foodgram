import short_url
from django.shortcuts import redirect
from recipes.const import DOMAIN


def redirect_view(request, surl):
    decoded_id = short_url.decode_url(surl)
    url = f'https://{DOMAIN}/recipes/{decoded_id}/'
    return redirect(url)
