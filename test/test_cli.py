import os
import sys
import tempfile
import imp
import shutil

import rw.testing
import rw.cli


class HTTPServerTest(rw.testing.AsyncHTTPTestCase):
    def get_app(self):
        self.tmp = tempfile.mkdtemp()
        rw.cli.create_skel('skel', self.tmp + '/rwtest', {'name': 'rwtest'})

        # check if essential files exist
        assert os.path.isdir(self.tmp + '/rwtest')
        assert os.path.isdir(self.tmp + '/rwtest/templates')
        assert os.path.isdir(self.tmp + '/rwtest/static')
        assert os.path.exists(self.tmp + '/rwtest/__init__.py')
        assert os.path.exists(self.tmp + '/rwtest/http.py')

        # load the new module and safe old interpreter state
        self.old_sys_path = sys.path[:]
        sys.path.append(self.tmp)
        import rwtest.http
        return rw.httpbase.Application(root=imp.reload(rwtest.http).root)

    def test_skel_basic_routing(self):
        response = self.fetch('/')
        body = response.body.decode('utf-8')
        assert response.code == 200
        assert u'<h1>Welcome</h1>' in body
        assert u'/static/Lzh47O/rwtest/logo.svg' in body

    def tearDown(self):
        super(HTTPServerTest, self).tearDown()
        shutil.rmtree(self.tmp)
        sys.path = self.old_sys_path

    def __del__(self):
        self.tearDown()
