#!/usr/bin/env python3
"""Instruction/literal/provenance boundaries of compact query/ingest rendering."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import route_rendering as rendering

REPO = Path(__file__).resolve().parent.parent


class RouteRenderingTests(unittest.TestCase):
    def test_literal_blocks_escapes_links_emphasis_requests_and_math_are_exact(self):
        fixtures = [
            '```python\n**glob** = 2\n\n\n```python\n**still-literal** = 3\n```\n',
            '    **glob**\n\n\n    `path`\n',
            r'\**literal** and **not compressed on escaped line**' + '\n',
            '[**link**](https://example.test/a_(b)) **label**\n',
            '输出时用 **加粗内容**，其余 **格式** 保留。\n',
            '第一行  \n第二行\n',
            '> **quoted** `path`\n',
            '计算 power 2 ** 3 + 4 ** 5。\n',
            '计算 2**3 + 4**5。\n',
            '````python\n```\n**literal**\n\n\n````\n',
            '~~~python\n~~~fake\n**literal**\n~~~\n',
        ]
        for text in fixtures:
            with self.subTest(text=text):
                self.assertEqual(rendering.compact_markdown(text)[0], text)

    def test_inline_code_pipe_and_multiple_delimiters_are_exact(self):
        for text in [
            '执行 `rg --files`，保留 `a | b` 和 `**glob**`。\n',
            '| 文字 `a | b` | **必须** |\n|------|--------|\n',
            '执行 ``a ` **literal** b``，再检查。\n',
        ]:
            rendered, _ = rendering.compact_markdown(text)
            before = [value for protected, value in rendering.protected_inline_parts(text) if protected]
            after = [value for protected, value in rendering.protected_inline_parts(rendered) if protected]
            self.assertEqual(after, before)
        self.assertEqual(rendering.compact_markdown('**必须**执行 `rg --files`。\n')[0], '必须执行`rg --files`。\n')

    def test_literal_source_header_examples_are_not_metadata(self):
        example = '--- operations/QUERY.md#md:demo/child [L2-L3] ---\n## Child\n**原样** `a | b`\n'
        for text in ['```text\n' + example + '```\n', '~~~\n' + example + '~~~\n', ''.join('    ' + line for line in example.splitlines(True))]:
            self.assertEqual(rendering.compact_query_wrappers(text), text)
            self.assertEqual(rendering.deduplicate_contained_sections(text)[0], text)

    def test_dedup_requires_same_source_contained_range_and_exact_body(self):
        child = '## Child\n必须保留所有约束。\n'
        parent = '--- demo.md#md:parent [L1-L9] ---\n## Parent\n' + child + '\n'
        header = '--- demo.md#md:child [L3-L5] ---\n'
        text, records = rendering.deduplicate_contained_sections(parent + header + child)
        self.assertEqual(len(records), 1)
        self.assertIn(parent, text)
        self.assertIn(header, text)
        self.assertIn('此前同源 [L1-L9]', text)
        for other_header, body in [
            ('--- other.md#md:child [L3-L5] ---\n', child),
            ('--- demo.md#md:child [L30-L50] ---\n', child),
            (header, child + '新增独立约束。\n'),
        ]:
            original = parent + other_header + body
            self.assertEqual(rendering.deduplicate_contained_sections(original), (original, []))

    def test_query_source_ranges_remain_in_band(self):
        text = '--- operations/QUERY.md#md:query/one [L2-L4] ---\n## One\n原要求。\n'
        rendered = rendering.compact_query_wrappers(text)
        self.assertIn('operations/QUERY.md', rendered)
        self.assertIn('[L2-L4]', rendered)
        self.assertIn('## One\n原要求。', rendered)

    def test_multiline_inline_literal_paragraphs_are_exact(self):
        fixtures = [
            '开始`foo\n**中文**\nbar`结束',
            '开始``foo\n**中文**\nbar``结束',
            '开始``foo\n`不同长度` **中文**\nbar``结束',
            '开始`已闭合`再``foo\n**中文**\nbar``结束',
            '开始`foo\n**中文**\nbar\\`结束',
            '开始\\\\`foo\n**中文**\nbar`结束',
            '开始`foo\n    **缩进续行**\n**中文**\nbar`结束',
            '开始``未匹配\n**中文**\n`不同长度\n',
            '开始`foo\r\n**中文**\r\nbar`结束\r\n',
            '开始' + chr(92) + '``foo\n**中文**\nbar' + chr(92) + '`结束',
            '开始' + chr(92) + '```foo\n**中文**\nbar' + chr(92) + '``结束',
        ]
        for text in fixtures:
            with self.subTest(text=text):
                self.assertEqual(rendering.compact_markdown(text), (text, []))
                self.assertEqual(rendering.render_routed_text(text, shared_query_source=True), text)

    def test_multiline_code_source_headers_are_not_metadata(self):
        fake = '--- operations/QUERY.md#md:demo/child [L2-L3] ---\n## Child\n**中文**\n'
        for marker in ['`', '``', '````']:
            text = '开始' + marker + 'foo\n' + fake + 'bar' + marker + '结束'
            with self.subTest(marker=marker):
                self.assertEqual(rendering.compact_query_wrappers(text), text)
                self.assertEqual(rendering.deduplicate_contained_sections(text), (text, []))
                self.assertEqual(rendering.render_routed_text(text, shared_query_source=True), text)
        for size in [2, 3]:
            text = '开始' + chr(92) + '`' * size + 'foo\n' + fake + 'bar' + chr(92) + '`' * (size - 1) + '结束'
            self.assertEqual(rendering.compact_query_wrappers(text), text)
            self.assertEqual(rendering.deduplicate_contained_sections(text), (text, []))
            self.assertEqual(rendering.render_routed_text(text, shared_query_source=True), text)
        child = '## Child\n必须保留。\n'
        real = '--- demo.md#md:parent [L1-L9] ---\n## Parent\n' + child + '\n'
        embedded = '开始`foo\n--- demo.md#md:child [L3-L5] ---\n' + child + 'bar`结束'
        original = real + embedded
        self.assertEqual(rendering.deduplicate_contained_sections(original), (original, []))

    def test_multiline_escape_and_blank_block_boundaries(self):
        escaped = '开始\\`普通文本\n**中文**\n'
        self.assertEqual(rendering.compact_markdown(escaped)[0], '开始\\`普通文本\n中文\n')
        unmatched = '开始``未匹配\n**中文**\n\n**下一段**\n'
        self.assertEqual(rendering.compact_markdown(unmatched)[0], '开始``未匹配\n**中文**\n\n下一段\n')
        header = '--- operations/QUERY.md#md:demo/real [L10-L12] ---\n## Real\n原要求。\n'
        text = '开始`foo\n**中文**\nbar`结束\n\n' + header
        rendered = rendering.compact_query_wrappers(text)
        self.assertIn('开始`foo\n**中文**\nbar`结束', rendered)
        self.assertIn('operations/QUERY.md', rendered)
        self.assertIn('[L10-L12]', rendered)
        self.assertNotIn(header, rendered)

    def test_actual_route_preserves_json_metadata_and_verbatim_source(self):
        command = [sys.executable, '.scripts/route.py', '--task', 'query', '--query', '关系如何', '--format', 'json']
        compact = json.loads(subprocess.check_output(command, cwd=REPO, text=True))
        original = json.loads(subprocess.check_output(command + ['--verbatim'], cwd=REPO, text=True))
        for key in ['sections', 'profiles', 'stage', 'query_scope', 'query_topic', 'backend', 'warnings', 'backend_notice']:
            self.assertEqual(compact[key], original[key])
        self.assertLess(len(compact['prompt']), len(original['prompt']))
        self.assertEqual(compact['estimated_chars'], len(compact['prompt']))
        self.assertIn('--- operations/QUERY.md#md:', original['prompt'])
        self.assertIn('[来源 operations/QUERY.md', compact['prompt'])


if __name__ == '__main__':
    unittest.main()
