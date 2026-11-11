"""Kiểm tra request budget, không dùng key thật hoặc gọi mạng."""
import os
import unittest
from unittest.mock import patch

from providers import Provider


class ProviderBudgetTests(unittest.TestCase):
    def request_payload(self, limit):
        env = {'OPENROUTER_API_KEY': 'example-key'}
        if limit is not None:
            env['MAX_OUTPUT_TOKENS'] = limit
        reply = {'choices': [{'message': {'role': 'assistant', 'content': 'OK'},
                              'finish_reason': 'stop'}]}
        with patch.dict(os.environ, env, clear=True), patch('providers.post_json', return_value=reply) as post:
            Provider('openrouter', 'example/model').complete([{'role': 'user', 'content': 'Hi'}], [])
            return post.call_args.args[2]

    def test_default_request_preserves_original_provider_behavior(self):
        self.assertNotIn('max_tokens', self.request_payload(None))

    def test_explicit_output_budget_reaches_the_api(self):
        self.assertEqual(self.request_payload('2048')['max_tokens'], 2048)

    def test_invalid_budget_is_rejected_before_calling_the_api(self):
        for value in ['0', '-1', 'invalid']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.request_payload(value)
