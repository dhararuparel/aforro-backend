"""Search app URL routing."""

from django.urls import path

from .views import AutocompleteView, ProductSearchView

urlpatterns = [
    path("products/", ProductSearchView.as_view(), name="product-search"),
    path("suggest/", AutocompleteView.as_view(), name="autocomplete"),
]
