"""Generate nginx configs on rueckenwind startup.

To use it add to your config:

    [rw.plugins]
    rw.plugins.nginx = True

    [example]
      [[ rw.plugins.nginx ]]
      path = /some/path.conf

This would work if your module is named "example".
"""
from __future__ import absolute_import

import os
import re
import logging
import subprocess
import time

import rw
import rplug


LOG = logging.getLogger(__name__)
SEPERATORS = re.compile('[ \t\r\n]*')


class NGINXManager(rplug.rw.module):
    def post_start(self):
        for module_name, config in rw.cfg['rw']['www']['modules'].items():
            nginx_config = rw.cfg[module_name].get('rw.plugins.nginx', {})
            nginx_path = nginx_config.get('path')

            if nginx_path:
                # XXX use the template env we already got
                template = config['root_handler'].template_env.get_template('rw:nginx')

                aliases_catch_all = nginx_config.get('aliases_catch_all')
                if aliases_catch_all:
                    nginx_config.setdefault('aliases', '')

                    aliases_catch_all = SEPERATORS.split(aliases_catch_all)
                    nginx_config['aliases'] += ' ' + ' '.join('{0} *.{0}'.format(a)
                                                              for a in aliases_catch_all)
                    nginx_config['aliases'] = nginx_config['aliases'].strip()

                if os.path.isdir(nginx_path):
                    nginx_path = os.path.join(nginx_path, module_name + '.conf')

                uname = module_name + str(time.time()).replace('.', '_')
                conf = template.render(name=uname,
                                       module=rw.cfg[module_name],
                                       nginx_config=nginx_config,
                                       cfg=rw.cfg,
                                       www=config)
                f = open(nginx_path, 'w')
                f.write(conf)
                f.close()
                LOG.info('wrote nginx config to %s', nginx_path)

                if os.path.exists('/usr/bin/chcon'):
                    subprocess.call(['chcon', '--reference', '/etc/nginx/conf.d/', nginx_path])


def activate():
    LOG.info('activated nginx plugin')
    NGINXManager.activate()
