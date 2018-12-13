"""custom command to build doc.zip file"""
#=============================================================================
# imports
#=============================================================================
# core
import os
from distutils import dir_util
from distutils.cmd import Command
from distutils.errors import *
from distutils.spawn import spawn
# local
__all__ = [
    "docdist"
]
#=============================================================================
# command
#=============================================================================
class docdist(Command):

    description = "create zip file containing standalone html docs"

    user_options = [
        ('build-dir=', None, 'Build directory'),
        ('dist-dir=', 'd',
         "directory to put the source distribution archive(s) in "
         "[default: dist]"),
        ('format=', 'f',
         "archive format to create (tar, ztar, gztar, zip)"),
        ('sign', 's', 'sign files using gpg'),
        ('identity=', 'i', 'GPG identity used to sign files'),
    ]

    def initialize_options(self):
        self.build_dir = None
        self.dist_dir = None
        self.format = None
        self.keep_temp = False
        self.sign = False
        self.identity = None

    def finalize_options(self):
        if self.identity and not self.sign:
            raise DistutilsOptionError(
                "Must use --sign for --identity to have meaning"
            )
        if self.build_dir is None:
            cmd = self.get_finalized_command('build')
            self.build_dir = os.path.join(cmd.build_base, 'docdist')
        if not self.dist_dir:
            self.dist_dir = "dist"
        if not self.format:
            self.format = "zip"

    def run(self):
        # call build sphinx to build docs
        self.run_command("build_sphinx")
        cmd = self.get_finalized_command("build_sphinx")
        source_dir = cmd.builder_target_dir

        # copy to directory with appropriate name
        dist = self.distribution
        arc_name = "%s-docs-%s" % (dist.get_name(), dist.get_version())
        tmp_dir = os.path.join(self.build_dir, arc_name)
        if os.path.exists(tmp_dir):
            dir_util.remove_tree(tmp_dir, dry_run=self.dry_run)
        self.copy_tree(source_dir, tmp_dir, preserve_symlinks=True)

        # make archive from dir
        arc_base = os.path.join(self.dist_dir, arc_name)
        self.arc_filename = self.make_archive(arc_base, self.format,
                                              self.build_dir)

        # Sign if requested
        if self.sign:
            gpg_args = ["gpg", "--detach-sign", "-a", self.arc_filename]
            if self.identity:
                gpg_args[2:2] = ["--local-user", self.identity]
            spawn(gpg_args,
                  dry_run=self.dry_run)

        # cleanup
        if not self.keep_temp:
            dir_util.remove_tree(tmp_dir, dry_run=self.dry_run)

#=============================================================================
# eof
#=============================================================================
