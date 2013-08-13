# Copyright 2012-2013 Florian Ludwig
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import sys
import os


PLUGS = {}


class InterfaceNotDefined(AttributeError):
    pass


class PlugInterfaceDict(dict):
    def load(self, module, org=None):
        """ Plugin Interfaces will put themself into this dict so all we
        need to do is to import the right python modules."""
        org = org if org else module
        if not module in self:
            try:
                imported_module = __import__(module + '.interfaces').interfaces
            except ImportError:
                if '.' in module:
                    return self.load(module[:module.rfind('.')], org)
                raise AttributeError('No interface definitions for module "%s"'
                                     % org)

            # load all interface definitions from module
            module_path = os.path.dirname(imported_module.__file__)
            for fname in os.listdir(module_path):
                if not fname[0] in ('.', '_') and fname.endswith('.py'):
                    __import__(module + '.interfaces.' + fname[:-3])
        try:
            return self[org]
        except:
            raise InterfaceNotDefined(org)
PLUG_INTERACES = PlugInterfaceDict()


class MetaPlug(type):
    def __new__(cls, name, bases, dct):
        is_interface = True
        is_interface = is_interface and name not in ('SinglePlug', 'MultiPlug')
        is_interface = is_interface and any(base in (SinglePlug, MultiPlug)
                                            for base in bases)
        if is_interface:
            if not 'rbus_path' in dct:
                mod_name = sys._getframe(1).f_locals['__name__'].split('.')
                if not 'rbus_module' in dct:
                    dct['rbus_module'] = mod_name[-3]
                if not 'rbus_plug' in dct:
                    dct['rbus_plug'] = mod_name[-1]
                dct['rbus_path'] = dct['rbus_module'] + '.' + dct['rbus_plug']
            else:
                path_split = dct['rbus_path'].split('.', 1)
                dct['rbus_module'], dct['rbus_plug'] = path_split

        ret = type.__new__(cls, name, bases, dct)
        if is_interface:
            PLUG_INTERACES[ret.rbus_module + '.' + ret.rbus_plug] = ret
        return ret


class SinglePlug(object):
    __metaclass__ = MetaPlug


class MultiPlug(object):
    __metaclass__ = MetaPlug


class Importer(object):
    def find_module(self, fullname, path=None):
        if fullname.startswith('rbus'):
            return BusLoader(fullname, path)

        if fullname.startswith('rplug'):
            return PlugLoader(fullname, path)


class Loader(object):
    __path__ = None

    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path
        self._cache = {}

    def load_module(self, fullname):
        return sys.modules.setdefault(fullname, self)


class PlugLoader(Loader):
    __path__ = None

    def __getattr__(self, attr):
        if not attr in self._cache:
            self._cache[attr] = PlugModule(attr)
        return self._cache[attr]


class MultiPlugModule(object):
    def __init__(self, interface):
        self._plugs = []
        self.interface = interface()

    def rbus_add_plug(self, plug):
        self._plugs.append(plug)

    def __getattr__(self, attr):
        interface_func = getattr(self.interface, attr)

        def caller(*args, **kwargs):
            results = [getattr(plug, attr)(*args, **kwargs)
                       for plug in self._plugs]
            if getattr(interface_func, 'post_process', False):
                kwargs['_results'] = results
                return interface_func(*args, **kwargs)
            return results
        return caller


class PlugModule(object):
    __path__ = None

    def __init__(self, module):
        self.__module = module
        self.__cache = {}

    def __getattr__(self, attr):
        module = self.__module
        if attr in self.__cache:
            return self.__cache[attr]
        interface = PLUG_INTERACES.load(module + '.' + attr)

        class BasePlug(interface):
            rbus_module = module
            rbus_plug = attr

            @classmethod
            def activate(cls):
                path = cls.rbus_module + '.' + cls.rbus_plug
                if issubclass(cls, SinglePlug):
                    PLUGS[path] = cls()
                elif issubclass(cls, MultiPlug):
                    PLUGS.setdefault(path, MultiPlugModule(interface))
                    PLUGS[path].rbus_add_plug(cls())
                else:
                    raise AttributeError('uhm o,O')
        self.__cache[attr] = BasePlug
        return BasePlug


class BusLoader(Loader):
    __path__ = None  # must be set so this class can be used like module

    def __init__(self, fullname, path):
        self.fullname = fullname
        self.path = path

    def load_module(self, fullname):
        assert fullname.startswith('rbus')
        if fullname == 'rbus':
            return self
        else:
            plug = self.fullname[len('rbus.'):]
            re = PLUGS.get(plug)
            if re is None:
                try:
                    interface = PLUG_INTERACES.load(plug)
                except InterfaceNotDefined:
                    return StubModule(fullname)
                return StubImplementation(interface)
            return re

    def __getattr__(self, attr):
        return BusModule(attr)


class StubModule(object):
    __path__ = None  # must be set so this class can be used like module

    def __init__(self, fullname):
        self.fullname = fullname


class StubImplementation(object):
    def __init__(self, interface):
        self._interface = interface

    def __getattr__(self, attr):
        if hasattr(self._interface, attr):
            if issubclass(self._interface, MultiPlug):
                def stub_function(*args, **kwargs):
                    """Stub function for interface: %s.%s""" % (
                        self._interface.rbus_path, attr)
                    return []
                return stub_function
            else:
                raise AttributeError('No implementation active for ' +
                                     self._interface.rbus_path)
        else:
            raise AttributeError('Interface for %s has no attribute %s' %
                                 (self._interface.rbus_path, attr))


class BusModule(object):
    def __init__(self, module):
        self.__rbus_module = module

    def __getattr__(self, attr):
        re = PLUGS.get(self.__rbus_module + '.' + attr)
        if re is None:
            interface = PLUG_INTERACES.load(self.__rbus_module + '.' + attr)
            return StubImplementation(interface)
        return re


class BusModuleSingle(BusModule):
    def __getattr__(self, attr):
        return getattr(attr, PLUGS[self.__rbus_module + '.' + self.rbus_plug])


def setup():
    if not any(isinstance(i, Importer) for i in sys.meta_path):
        sys.meta_path.append(Importer())


def post_process(func):
    func.post_process = True
    return func
