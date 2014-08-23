"""Rueckenwind tempating

Rueckenwind does not contain it's own templating engine
but is based on Jinja2.
"""
import jinja2


def create_template_env(pkgs):
    loaders = [jinja2.PackageLoader(pkg, 'templates') for pkg in pkgs]
    template_env = jinja2.Environment(
        loader=jinja2.ChoiceLoader(loaders),
        extensions=['jinja2.ext.loopcontrols',
                    'jinja2.ext.i18n'],
    )

    # some more default functions
    # template_env.globals['enumerate'] = enumerate
    # template_env.globals['isinstance'] = isinstance
    # template_env.globals['len'] = len
    # # default types
    # template_env.globals['int'] = int
    # template_env.globals['str'] = str
    # template_env.globals['unicode'] = unicode
    # template_env.globals['list'] = list
    # template_env.globals['tuple'] = tuple
    # template_env.globals['dict'] = dict
    # template_env.globals['set'] = set
    # template_env.globals['basestring'] = basestring
    # template_env.globals['urlencode'] = urlencode
    # filter
    # template_env.filters['json'] = dumps
    return template_env
    # scope['template_env'] = template_env