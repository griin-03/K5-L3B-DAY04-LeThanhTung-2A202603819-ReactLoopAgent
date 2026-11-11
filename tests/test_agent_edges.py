"""Các nhánh lỗi của loop; không gọi API hay sửa fixture."""
import json
import unittest

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class AgentEdgeTests(unittest.TestCase):
    def test_provider_exception_does_not_leak_exception_body(self):
        class BrokenProvider:
            def complete(self, messages, schemas):
                raise RuntimeError('private-request-body')

        result = run_agent('Kiểm tra', BrokenProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['trace'][0]['event'], 'provider_error')
        self.assertNotIn('private-request-body', json.dumps(result))

    def test_tool_exception_becomes_an_observation(self):
        class BrokenTools:
            def execute(self, name, args):
                raise TimeoutError('temporary failure')

        model = FakeProvider([
            tool_call('t', 'get_status', '{"provider":"github"}'),
            final('Chưa xác nhận được trạng thái.'),
        ])
        result = run_agent('Kiểm tra', model, BrokenTools())
        observation = json.loads(model.histories[1][-1]['content'])
        self.assertEqual(observation['error'], 'TimeoutError')
        self.assertEqual(result['status'], 'completed')

    def test_array_arguments_are_rejected(self):
        model = FakeProvider([tool_call('t', 'get_status', '[]'), final('Thiếu tham số.')])
        run_agent('Kiểm tra', model, StatusTools())
        self.assertEqual(json.loads(model.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_bad_first_call_does_not_skip_the_second(self):
        response = tool_call('bad', 'get_status', '{')
        good = tool_call('good', 'get_status', '{"provider":"github"}')
        response['calls'] += good['calls']
        response['message']['tool_calls'] += good['message']['tool_calls']
        model = FakeProvider([response, final('Đã kiểm tra phần hợp lệ.')])
        result = run_agent('Kiểm tra', model, StatusTools())
        returned = model.histories[1][-2:]
        self.assertEqual([message['tool_call_id'] for message in returned], ['bad', 'good'])
        self.assertEqual(json.loads(returned[0]['content'])['error'], 'INVALID_ARGUMENTS')
        self.assertEqual(json.loads(returned[1]['content'])['provider'], 'github')
        self.assertEqual(result['status'], 'completed')

    def test_original_assistant_message_is_kept(self):
        response = tool_call('t', 'get_status', '{"provider":"github"}')
        response['message']['content'] = 'Tôi sẽ kiểm tra.'
        model = FakeProvider([response, final()])
        run_agent('Kiểm tra', model, StatusTools())
        self.assertEqual(model.histories[1][-2], response['message'])

    def test_empty_or_abnormal_final_is_not_completed(self):
        for response in [final(''), dict(final('Bị cắt.'), finish='length'),
                         dict(final(), finish='content_filter'), dict(final(), finish='tool_calls')]:
            with self.subTest(response=response):
                result = run_agent('Kiểm tra', FakeProvider([response]), StatusTools())
                self.assertEqual(result['status'], 'error')

    def test_invalid_budget_does_not_call_the_provider(self):
        for budget in [0, -1, True, 1.5]:
            with self.subTest(budget=budget):
                model = FakeProvider([])
                result = run_agent('Kiểm tra', model, StatusTools(), max_steps=budget)
                self.assertEqual(result['status'], 'error')
                self.assertEqual(model.histories, [])

    def test_usage_is_preserved_per_model_call(self):
        response = final()
        response['usage'] = {'prompt_tokens': 10, 'completion_tokens': 4, 'cost': 0.001}
        result = run_agent('Kiểm tra', FakeProvider([response]), StatusTools())
        self.assertEqual(result['usage'], [response['usage']])
