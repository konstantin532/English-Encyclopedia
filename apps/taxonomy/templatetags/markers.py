from django import template
from django.utils.safestring import mark_safe

from apps.taxonomy.markup import render_block, render_inline, strip_markup

register = template.Library()


@register.filter
def annotate(text):
    return mark_safe(render_inline(text or ""))


@register.filter
def annotate_block(text):
    return render_block(text or "")


@register.filter
def plain(text):
    return strip_markup(text or "")
