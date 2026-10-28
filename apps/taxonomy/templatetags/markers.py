from django import template
from django.utils.safestring import mark_safe

from apps.taxonomy.markup import render_block, render_inline, strip_markup

register = template.Library()


@register.filter
def annotate(text, plain_labels=False):
    return mark_safe(render_inline(text or "", plain_labels=plain_labels))


@register.filter
def annotate_block(text, plain_labels=False):
    return render_block(text or "", plain_labels=plain_labels)


@register.filter
def plain(text):
    return strip_markup(text or "")


@register.filter
def has_spoken(lines):
    return any(line.get("spoken") for line in lines or [])
