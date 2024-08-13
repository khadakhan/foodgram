import short_url
from django.shortcuts import redirect


def redirect_view(request, surl):
    decoded_id = short_url.decode_url(surl)
    url = f'https://foodgramdo.zapto.org/recipes/{decoded_id}/'
    return redirect(url)
