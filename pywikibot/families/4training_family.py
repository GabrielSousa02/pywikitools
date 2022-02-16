# -*- coding: utf-8 -*-
"""
This family file was auto-generated by generate_family_file.py script.

Configuration parameters:
  url = https://www.4training.net
  name = 4training

Please do not commit this to the Git repository!
"""
from __future__ import absolute_import, division, unicode_literals

from pywikibot import family
from pywikibot.tools import deprecated


class Family(family.Family):  # noqa: D101

    name = '4training'
    langs = {
        'en': 'www.4training.net',
    }

    def scriptpath(self, code):
        return {
            'en': '/mediawiki',
        }[code]

    @deprecated('APISite.version()', since='20141225')
    def version(self, code):
        return {
            'en': '1.35.1',
        }[code]

    def protocol(self, code):
        return {
            'en': 'https',
        }[code]