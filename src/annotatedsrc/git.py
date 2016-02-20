# encoding: utf-8
from __future__ import absolute_import
from future.standard_library import install_aliases
install_aliases()

import os
import re
import tempfile
import shutil
import gitdb.exc
from urllib.parse import urlparse
from git import Repo
from zope.interface import implementer
from .interfaces import IGitFetcher

def sanitize_url_component_suitable_for_fs(c):
    return re.sub(ur'[:\\]|^\.+', lambda g: u'-' * len(g.group(0)), c)

class Symbolic(Exception):
    pass

@implementer(IGitFetcher)
class GitFetcher(object):
    origin_remote_name = 'origin'

    def __init__(self, basedir):
        self.basedir = basedir

    def build_path_from_repo_url(self, url, ref):
        components = urlparse(url)
        d = re.sub(ur'//+', u'/', u'/'.join(sanitize_url_component_suitable_for_fs(c) for c in components if c is not None and len(c) > 0))
        return os.path.join(d, sanitize_url_component_suitable_for_fs(ref)) if ref is not None else d

    def get_repo(self, url, ref):
        d = os.path.join(self.basedir, self.build_path_from_repo_url(url, ref))
        if not os.path.exists(d):
            raise IOError(2, 'No such file or directory: ' + d)
        return Repo(d)

    def get_fetched_refs_for_remote(self, url):
        d = os.path.join(self.basedir, self.build_path_from_repo_url(url, None))
        result = []
        if os.path.exists(d):
            def x(d1, d2):
                d = os.path.join(d1, d2)
                for cd in os.listdir(d):
                    rel_repodir = os.path.join(d2, cd)
                    abs_repodir = os.path.join(d1, rel_repodir)
                    if os.path.exists(os.path.join(abs_repodir, '.git')):
                        result.append((rel_repodir, abs_repodir))
                    else:
                        x(d1, rel_repodir)
            x(d, '')
        return result

    def find_repo_contains_specified_commit(self, url, ref):
        for rel_repodir, abs_repodir in self.get_fetched_refs_for_remote(url):
            r = Repo(abs_repodir)
            try:
                return r.commit(ref)
            except:
                pass
        else:
            return None

    def fetch_nonsymbolic_locally(self, orig_repo, ref):
        return r

    def fetch(self, url, ref):
        d = os.path.join(self.basedir, self.build_path_from_repo_url(url, ref))
        if not os.path.exists(d):
            c = self.find_repo_contains_specified_commit(url, ref)
            if c is not None:
                orig_repo = c.repo
                for remote_ref in orig_repo.remotes[self.origin_remote_name].refs:
                    orig_repo.create_head(remote_ref.name[len(self.origin_remote_name) + 1:], remote_ref, force=True)
                r = orig_repo.clone(d)
                o = r.create_remote(self.origin_remote_name, url=url, force=True)
            else:
                r = Repo.init(d)
                o = r.create_remote(self.origin_remote_name, url=url)
                o.fetch(depth=1)
            new = True
        else:
            r = Repo(d)
            o = r.remotes[self.origin_remote_name]
            new = False
        try:
            try:
                remote_ref = 'remotes/' + self.origin_remote_name + '/' + ref
                hexsha = r.commit(remote_ref).hexsha
            except gitdb.exc.BadName:
                remote_ref = ref
                hexsha = r.commit(ref).hexsha
            if hexsha != ref:
                # symbolic ref
                if not new:
                    o.fetch(depth=1)
                    hexsha = r.commit(remote_ref).hexsha
                raise Symbolic(hexsha)
                # d = os.path.join(self.basedir, self.build_path_from_repo_url(url, hexsha))
                # if os.path.exists(d):
                #     r = Repo(d)
                #     new = False
            if new:
                r.head.reference = hexsha
                r.head.reset(index=True, working_tree=True)
        except Exception as e:
            if new:
                shutil.rmtree(r.working_dir)
            raise
        return r
