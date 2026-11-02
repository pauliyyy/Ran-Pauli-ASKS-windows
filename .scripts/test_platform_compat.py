#!/usr/bin/env python3
"""Regressions for host selection without changing semantic workflows."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import platform_compat as platform


class PlatformTests(unittest.TestCase):
    def test_platform_font_defaults(self):
        self.assertEqual(platform.default_cjk_font(platform='linux', environ={}), 'Noto Sans CJK SC')
        self.assertEqual(platform.default_cjk_font(platform='darwin', environ={}), 'Heiti SC')
        self.assertEqual(platform.default_cjk_font(platform='win32', environ={}), 'Microsoft YaHei')

    def test_explicit_font_wins_without_silent_substitution(self):
        self.assertEqual(platform.default_cjk_font(platform='linux', environ={'ASKS_CJK_FONT': '  Missing Explicit Font  '}), 'Missing Explicit Font')

    def test_presentation_retains_its_macos_default(self):
        self.assertEqual(platform.default_cjk_font(platform='darwin', mac_default='PingFang SC', environ={}), 'PingFang SC')
        self.assertEqual(platform.default_cjk_font(platform='linux', mac_default='PingFang SC', environ={}), 'Noto Sans CJK SC')

    def test_empty_override_uses_platform_default(self):
        self.assertEqual(platform.default_cjk_font(platform='linux', environ={'ASKS_CJK_FONT': '   '}), 'Noto Sans CJK SC')

    def test_executable_keeps_launcher_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = root / 'dispatcher'
            executable.write_text('#!/bin/sh\nexit 0\n')
            executable.chmod(0o700)
            launcher = root / 'libreoffice'
            launcher.symlink_to(executable)
            self.assertEqual(platform.find_executable('libreoffice', which=lambda _: str(launcher)), launcher)
            self.assertNotEqual(platform.find_executable('libreoffice', which=lambda _: str(launcher)), executable)

    def test_non_executable_file_is_not_a_tool(self):
        with tempfile.TemporaryDirectory() as temporary:
            tool = Path(temporary) / 'tool'
            tool.write_text('not executable')
            tool.chmod(0o600)
            self.assertIsNone(platform.find_executable('tool', which=lambda _: str(tool)))

    def test_explicit_office_precedes_environment_and_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = [root / name for name in ('explicit', 'environment', 'path')]
            for tool in tools:
                tool.write_text('#!/bin/sh\nexit 0\n')
                tool.chmod(0o700)
            self.assertEqual(platform.find_soffice(tools[0], environ={'SOFFICE_BIN': str(tools[1])}, which=lambda _: str(tools[2]), home=root), tools[0])

    def test_environment_office_precedes_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool = root / 'configured-office'
            tool.write_text('#!/bin/sh\nexit 0\n')
            tool.chmod(0o700)
            self.assertEqual(platform.find_soffice(environ={'SOFFICE_BIN': str(tool)}, which=lambda _: None, home=root), tool)

    def test_configured_fontconfig_is_preserved_and_not_mutated(self):
        original = {'FONTCONFIG_FILE': '/caller/fonts.conf', 'PATH': '/caller/bin'}
        child = platform.soffice_environment('/any/office', environ=original)
        self.assertEqual(child, original)
        child['PATH'] = '/different'
        self.assertEqual(original['PATH'], '/caller/bin')

    def test_app_bundle_fontconfig_is_added_to_child_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            contents = Path(temporary) / 'LibreOffice.app' / 'Contents'
            executable = contents / 'MacOS' / 'soffice'
            executable.parent.mkdir(parents=True)
            executable.write_text('binary-placeholder')
            fontconfig = contents / 'Resources' / 'fontconfig' / 'fonts.conf'
            fontconfig.parent.mkdir(parents=True)
            fontconfig.write_text('<fontconfig/>')
            original = {'PATH': '/bin'}
            child = platform.soffice_environment(executable, environ=original)
            self.assertEqual(child['FONTCONFIG_FILE'], str(fontconfig))
            self.assertNotIn('FONTCONFIG_FILE', original)


if __name__ == '__main__':
    unittest.main()
